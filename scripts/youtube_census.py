#!/usr/bin/env python3
"""Run a resumable official YouTube channel-discovery and enrichment tranche."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from m2_engine.engine import canonical_hash  # noqa: E402
from m2_engine.secret_source import SecretSourceError, load_secret  # noqa: E402
from m2_engine.youtube_api import QuotaLedger, YouTubeAPIError, YouTubeDataAPIClient  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema") != "north-hux.youtube-census-config.v1":
        raise ValueError("unsupported YouTube census config schema")
    target = config.get("target_accounts", {})
    if target.get("minimum") != 10000 or target.get("maximum") != 12000:
        raise ValueError("target_accounts must remain 10000-12000")
    fraction = config.get("maximum_creator_contribution_fraction")
    if fraction != 0.01:
        raise ValueError("maximum creator contribution must be 0.01")
    daily = config.get("daily_limits", {})
    if not (0 < int(daily.get("local_search_call_budget", 0)) <= int(daily.get("search_calls", 0)) <= 100):
        raise ValueError("search call limits are invalid")
    discovery = config.get("discovery", {})
    if not (1 <= int(discovery.get("pages_per_cell", 0)) <= 20):
        raise ValueError("pages_per_cell must be between 1 and 20")
    if not (1 <= int(discovery.get("max_results_per_page", 0)) <= 50):
        raise ValueError("max_results_per_page must be between 1 and 50")
    if discovery.get("resource_type") != "video" or discovery.get("video_duration") != "short":
        raise ValueError("calibration discovery must use public short-video search")
    if int(config.get("request", {}).get("max_attempts", 0)) != 5:
        raise ValueError("five-strike policy requires exactly five attempts")
    calibration = config.get("calibration_content", {})
    accounts = int(calibration.get("qualified_accounts", 0))
    videos_per_account = int(calibration.get("videos_per_account", 0))
    minimum_videos = int(calibration.get("minimum_videos_per_account", 0))
    maximum_videos = int(calibration.get("maximum_videos_per_account", 0))
    target_rows = int(calibration.get("target_rows", 0))
    if accounts != 300 or not 3 <= videos_per_account <= 10:
        raise ValueError("calibration must contain 300 accounts and 3-10 videos per account")
    if minimum_videos != 3 or maximum_videos != 10:
        raise ValueError("calibration video bounds must remain 3-10")
    if target_rows != accounts * videos_per_account:
        raise ValueError("calibration target_rows must equal accounts multiplied by videos_per_account")
    top_references = config.get("top_references", {})
    if int(top_references.get("target_rows", 0)) != 100 or int(top_references.get("videos_per_creator", 0)) != 1:
        raise ValueError("top_references must remain 100 rows and one video per creator")
    if len(config.get("markets", [])) != len(set(config.get("markets", []))):
        raise ValueError("markets must be unique")
    if not set(config.get("orders", [])).issubset({"relevance", "date", "title", "videoCount", "viewCount"}):
        raise ValueError("unsupported search order")


def validate_execution_authorization(path: Path, run_dir: Path) -> None:
    receipt = load_json(path)
    if receipt.get("schema") != "north-hux.owner-execution-authorization.v1":
        raise ValueError("execution authorization schema is invalid")
    if receipt.get("run_id") != run_dir.name:
        raise ValueError("execution authorization run does not match")
    approved = receipt.get("approved", {})
    if approved.get("platform") != "youtube" or approved.get("official_youtube_data_api_public_read_only") is not True:
        raise ValueError("official YouTube public-read execution is not approved")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(body, encoding="utf-8")
    temporary.replace(path)


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def checkpoint_index(run_dir: Path, stage: str) -> dict[tuple[str, int], dict[str, Any]]:
    path = run_dir / "ledgers" / "youtube-stage-checkpoints.jsonl"
    if not path.exists():
        return {}
    candidates: dict[str, dict[int, dict[str, Any]]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("stage") == stage and row.get("status") == "page_committed":
            normalized_uri = row.get("normalized_uri")
            raw_uri = row.get("raw_uri")
            if not isinstance(normalized_uri, str) or not isinstance(raw_uri, str):
                continue
            normalized_path = run_dir / normalized_uri
            raw_path = run_dir / raw_uri
            if not normalized_path.exists() or not raw_path.exists():
                continue
            if hashlib.sha256(normalized_path.read_bytes()).hexdigest() != row.get("normalized_sha256"):
                continue
            if hashlib.sha256(raw_path.read_bytes()).hexdigest() != row.get("raw_sha256"):
                continue
            candidates.setdefault(str(row["target_id"]), {})[int(row["page_index"])] = row
    index: dict[tuple[str, int], dict[str, Any]] = {}
    for target_id, pages in candidates.items():
        expected_token: str | None = None
        for page_index in sorted(pages):
            row = pages[page_index]
            if page_index != len([key for key in index if key[0] == target_id]):
                break
            if row.get("page_token_used") != expected_token:
                break
            index[(target_id, page_index)] = row
            expected_token = row.get("next_page_token")
            if not expected_token:
                break
    return index


def select_with_creator_cap(
    rows: list[dict[str, Any]],
    *,
    creator_field: str,
    fraction: float,
    target_size: int,
) -> list[dict[str, Any]]:
    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in (0, 1]")
    if target_size <= 0:
        raise ValueError("target_size must be positive")
    per_creator = max(1, math.floor(target_size * fraction))
    counts: dict[str, int] = {}
    selected: list[dict[str, Any]] = []
    for row in rows:
        creator_id = str(row[creator_field])
        if counts.get(creator_id, 0) >= per_creator:
            continue
        counts[creator_id] = counts.get(creator_id, 0) + 1
        selected.append(row)
        if len(selected) >= target_size:
            break
    if len(selected) != target_size:
        raise ValueError(f"creator-capped selection underfilled: expected {target_size}, got {len(selected)}")
    validate_creator_contribution(selected, creator_field=creator_field, fraction=fraction)
    return selected


def validate_creator_contribution(rows: list[dict[str, Any]], *, creator_field: str, fraction: float) -> None:
    if not rows:
        raise ValueError("analyzed-content cohort must not be empty")
    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in (0, 1]")
    counts = Counter(str(row[creator_field]) for row in rows)
    violations = {creator: count for creator, count in counts.items() if count / len(rows) > fraction}
    if violations:
        raise ValueError(f"creator contribution exceeds {fraction:.4f}: {sorted(violations.items())}")


def _content_rank(row: dict[str, Any]) -> tuple[int, str, int, str]:
    format_state = str(row.get("format_state") or "UNKNOWN")
    shorts_rank = 0 if format_state == "NATIVE_SHORT" else 1 if format_state == "DURATION_CANDIDATE" else 2
    published = str(row.get("published_at") or "")
    views = int(row.get("view_count") or 0)
    return (shorts_rank, "".join(chr(255 - ord(char)) for char in published if ord(char) < 256), -views, str(row.get("native_video_id") or ""))


def build_analyzed_content_cohort(
    account_rows: list[dict[str, Any]],
    video_rows: list[dict[str, Any]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    calibration = config["calibration_content"]
    account_target = int(calibration["qualified_accounts"])
    videos_per_account = int(calibration["videos_per_account"])
    target_rows = int(calibration["target_rows"])
    fraction = float(config["maximum_creator_contribution_fraction"])
    qualified_ids = sorted({
        str(row["native_channel_id"])
        for row in account_rows
        if row.get("qualification_state") == "qualified" and row.get("native_channel_id")
    })
    by_creator: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    video_owner: dict[str, str] = {}
    for row in video_rows:
        creator_id = str(row.get("native_channel_id") or "")
        video_id = str(row.get("native_video_id") or "")
        if creator_id not in qualified_ids or row.get("analysis_eligible") is not True:
            continue
        if not video_id:
            raise ValueError(f"analysis-eligible row for {creator_id} has no native_video_id")
        prior_owner = video_owner.setdefault(video_id, creator_id)
        if prior_owner != creator_id:
            raise ValueError(f"native_video_id {video_id} is assigned to conflicting creators")
        current = by_creator[creator_id].get(video_id)
        if current is None or str(row.get("captured_at") or "") > str(current.get("captured_at") or ""):
            by_creator[creator_id][video_id] = row
    eligible_creators = [creator for creator in qualified_ids if len(by_creator[creator]) >= videos_per_account]
    if len(eligible_creators) < account_target:
        raise ValueError(f"qualified content cohort underfilled: need {account_target} creators, got {len(eligible_creators)}")
    selected: list[dict[str, Any]] = []
    for creator_id in eligible_creators[:account_target]:
        selected.extend(sorted(by_creator[creator_id].values(), key=_content_rank)[:videos_per_account])
    if len(selected) != target_rows:
        raise ValueError(f"analyzed-content cohort underfilled: expected {target_rows}, got {len(selected)}")
    validate_creator_contribution(selected, creator_field="native_channel_id", fraction=fraction)
    return selected


def construct_content_cohort(run_dir: Path, config: dict[str, Any]) -> dict[str, int]:
    accounts_path = run_dir / "derived" / "qualified-accounts.jsonl"
    videos_path = run_dir / "derived" / "video-snapshots.jsonl"
    if not accounts_path.is_file() or not videos_path.is_file():
        raise ValueError("qualified-accounts.jsonl and video-snapshots.jsonl are required")
    accounts = [json.loads(line) for line in accounts_path.read_text(encoding="utf-8").splitlines() if line]
    videos = [json.loads(line) for line in videos_path.read_text(encoding="utf-8").splitlines() if line]
    selected = build_analyzed_content_cohort(accounts, videos, config)
    write_jsonl(run_dir / "derived" / "analyzed-content-cohort.jsonl", selected)
    return {
        "qualified_accounts": len({row["native_channel_id"] for row in selected}),
        "analyzed_content_rows": len(selected),
        "maximum_creator_rows": max(Counter(row["native_channel_id"] for row in selected).values()),
    }


def construct_top_references(run_dir: Path, config: dict[str, Any]) -> dict[str, int]:
    cohort_path = run_dir / "derived" / "analyzed-content-cohort.jsonl"
    if not cohort_path.is_file():
        raise ValueError("analyzed-content-cohort.jsonl is required")
    rows = [json.loads(line) for line in cohort_path.read_text(encoding="utf-8").splitlines() if line]
    validate_creator_contribution(
        rows,
        creator_field="native_channel_id",
        fraction=float(config["maximum_creator_contribution_fraction"]),
    )
    ranked = sorted(rows, key=_content_rank)
    selected = select_with_creator_cap(
        ranked,
        creator_field="native_channel_id",
        fraction=float(config["maximum_creator_contribution_fraction"]),
        target_size=int(config["top_references"]["target_rows"]),
    )
    write_jsonl(run_dir / "derived" / "top-reference-cohort.jsonl", selected)
    return {
        "top_reference_rows": len(selected),
        "distinct_creators": len({row["native_channel_id"] for row in selected}),
        "maximum_creator_rows": max(Counter(row["native_channel_id"] for row in selected).values()),
    }


def build_cells(config: dict[str, Any]) -> list[dict[str, str]]:
    cells: list[dict[str, str]] = []
    for group in config["query_groups"]:
        for query in group["queries"]:
            for market in config["markets"]:
                for order in config["orders"]:
                    value = {
                        "track": group["track"],
                        "intent": group["intent"],
                        "query": query,
                        "discovery_market": market,
                        "order": order,
                    }
                    value["cell_id"] = canonical_hash(value)
                    cells.append(value)
    return sorted(cells, key=lambda row: hashlib.sha256(row["cell_id"].encode()).hexdigest())


def _search_record(item: dict[str, Any], cell: dict[str, str], result: Any) -> dict[str, Any] | None:
    snippet = item.get("snippet", {})
    channel_id = item.get("id", {}).get("channelId") or snippet.get("channelId")
    if not isinstance(channel_id, str) or not channel_id:
        return None
    video_id = item.get("id", {}).get("videoId")
    return {
        "schema": "north-hux.youtube-channel-discovery.v1",
        "platform": "youtube",
        "native_channel_id": channel_id,
        "canonical_url": f"https://www.youtube.com/channel/{channel_id}",
        "title": snippet.get("title"),
        "description": snippet.get("description"),
        "seed_video_id": video_id,
        "seed_video_url": f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
        "published_at": snippet.get("publishedAt"),
        "track": cell["track"],
        "intent": cell["intent"],
        "query_id": canonical_hash(cell["query"]),
        "discovery_market": cell["discovery_market"],
        "region_evidence_state": "discovery_market_only_not_creator_region",
        "order": cell["order"],
        "source_request_fingerprint": result.fingerprint,
        "raw_sha256": result.raw_sha256,
        "raw_uri": result.raw_uri,
        "captured_at": result.captured_at,
        "refresh_or_delete_by": result.refresh_or_delete_by,
        "epistemic_state": "observed_public_api",
    }


def aggregate_discovery(run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((run_dir / "normalized" / "search-pages").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        channel_id = row["native_channel_id"]
        current = grouped.setdefault(channel_id, {
            "schema": "north-hux.youtube-channel-candidate.v1",
            "platform": "youtube",
            "native_channel_id": channel_id,
            "canonical_url": row["canonical_url"],
            "title": row.get("title"),
            "description": row.get("description"),
            "discovery_observation_count": 0,
            "tracks": set(),
            "intents": set(),
            "discovery_markets": set(),
            "orders": set(),
            "source_request_fingerprints": set(),
            "refresh_or_delete_by": row["refresh_or_delete_by"],
        })
        current["discovery_observation_count"] += 1
        current["tracks"].add(row["track"])
        current["intents"].add(row["intent"])
        current["discovery_markets"].add(row["discovery_market"])
        current["orders"].add(row["order"])
        current["source_request_fingerprints"].add(row["source_request_fingerprint"])
    output: list[dict[str, Any]] = []
    for row in grouped.values():
        for field in ("tracks", "intents", "discovery_markets", "orders", "source_request_fingerprints"):
            row[field] = sorted(row[field])
        output.append(row)
    return sorted(output, key=lambda row: row["native_channel_id"])


def discover(client: YouTubeDataAPIClient, config: dict[str, Any], run_dir: Path, max_new_calls: int) -> dict[str, int]:
    calls = 0
    pages = 0
    observed = 0
    max_pages = int(config["discovery"]["pages_per_cell"])
    max_results = int(config["discovery"]["max_results_per_page"])
    checkpoints = checkpoint_index(run_dir, "search_discovery")
    checkpoint_path = run_dir / "ledgers" / "youtube-stage-checkpoints.jsonl"
    for cell in build_cells(config):
        next_page_token: str | None = None
        for page_index in range(max_pages):
            checkpoint = checkpoints.get((cell["cell_id"], page_index))
            if checkpoint:
                next_page_token = checkpoint.get("next_page_token")
                pages += 1
                if not next_page_token:
                    break
                continue
            if calls >= max_new_calls:
                break
            params = {
                "part": "snippet",
                "type": config["discovery"]["resource_type"],
                "maxResults": str(max_results),
                "q": cell["query"],
                "regionCode": cell["discovery_market"],
                "relevanceLanguage": "en",
                "order": cell["order"],
                "videoDuration": config["discovery"]["video_duration"],
                "safeSearch": "moderate",
            }
            if next_page_token:
                params["pageToken"] = next_page_token
            result = client.get("search", "search.list", params, estimated_units=1)
            if not result.resumed:
                calls += 1
            rows = [record for item in result.payload.get("items", []) if (record := _search_record(item, cell, result))]
            page_path = run_dir / "normalized" / "search-pages" / f"{result.fingerprint.removeprefix('sha256:')}.jsonl"
            write_jsonl(page_path, rows)
            next_page_token = result.payload.get("nextPageToken")
            append_jsonl(checkpoint_path, {
                "schema": "north-hux.youtube-stage-checkpoint.v1",
                "stage": "search_discovery",
                "target_id": cell["cell_id"],
                "page_index": page_index,
                "page_token_used": params.get("pageToken"),
                "next_page_token": next_page_token,
                "request_fingerprint": result.fingerprint,
                "raw_sha256": result.raw_sha256,
                "raw_uri": result.raw_uri,
                "normalized_uri": page_path.relative_to(run_dir).as_posix(),
                "normalized_sha256": hashlib.sha256(page_path.read_bytes()).hexdigest(),
                "status": "page_committed",
                "committed_at": result.captured_at,
            })
            pages += 1
            observed += len(rows)
            if not next_page_token:
                break
        if calls >= max_new_calls:
            break
    candidates = aggregate_discovery(run_dir)
    write_jsonl(run_dir / "derived" / "channel-candidates.jsonl", candidates)
    return {"new_search_calls": calls, "search_pages": pages, "observations": observed, "unique_candidates": len(candidates)}


def aggregate_enrichment(run_dir: Path) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for path in sorted((run_dir / "normalized" / "channel-pages").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            channel_id = str(row["native_channel_id"])
            if channel_id not in latest or str(row.get("captured_at", "")) >= str(latest[channel_id].get("captured_at", "")):
                latest[channel_id] = row
    return sorted(latest.values(), key=lambda row: row["native_channel_id"])


def enrich(client: YouTubeDataAPIClient, run_dir: Path, *, batch_limit: int | None = None) -> dict[str, int]:
    candidates = aggregate_discovery(run_dir)
    batches = [candidates[index:index + 50] for index in range(0, len(candidates), 50)]
    if batch_limit is not None:
        batches = batches[:batch_limit]
    requests = 0
    checkpoint_path = run_dir / "ledgers" / "youtube-stage-checkpoints.jsonl"
    for batch in batches:
        ids = [row["native_channel_id"] for row in batch]
        result = client.get("channels", "channels.list", {
            "part": "id,snippet,contentDetails,statistics,topicDetails,status",
            "id": ",".join(ids),
            "maxResults": "50",
        }, estimated_units=1)
        if not result.resumed:
            requests += 1
        rows: list[dict[str, Any]] = []
        returned_ids: set[str] = set()
        for item in result.payload.get("items", []):
            snippet = item.get("snippet", {})
            statistics = item.get("statistics", {})
            returned_ids.add(str(item.get("id")))
            rows.append({
                "schema": "north-hux.youtube-channel-snapshot.v1",
                "platform": "youtube",
                "native_channel_id": item.get("id"),
                "canonical_url": f"https://www.youtube.com/channel/{item.get('id')}",
                "title": snippet.get("title"),
                "description": snippet.get("description"),
                "custom_url": snippet.get("customUrl"),
                "published_at": snippet.get("publishedAt"),
                "country": snippet.get("country"),
                "default_language": snippet.get("defaultLanguage"),
                "subscriber_count": statistics.get("subscriberCount"),
                "hidden_subscriber_count": statistics.get("hiddenSubscriberCount"),
                "video_count": statistics.get("videoCount"),
                "view_count": statistics.get("viewCount"),
                "uploads_playlist_id": item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads"),
                "topic_categories": item.get("topicDetails", {}).get("topicCategories", []),
                "privacy_status": item.get("status", {}).get("privacyStatus"),
                "captured_at": result.captured_at,
                "refresh_or_delete_by": result.refresh_or_delete_by,
                "source_request_fingerprint": result.fingerprint,
                "raw_sha256": result.raw_sha256,
                "raw_uri": result.raw_uri,
                "metrics_semantics": "youtube-public-api-snapshot; Shorts viewCount includes starts/replays since 2025-03-31",
                "availability_state": "observed",
            })
        for channel_id in sorted(set(ids) - returned_ids):
            rows.append({
                "schema": "north-hux.youtube-channel-snapshot.v1",
                "platform": "youtube",
                "native_channel_id": channel_id,
                "canonical_url": f"https://www.youtube.com/channel/{channel_id}",
                "captured_at": result.captured_at,
                "refresh_or_delete_by": result.refresh_or_delete_by,
                "source_request_fingerprint": result.fingerprint,
                "raw_sha256": result.raw_sha256,
                "raw_uri": result.raw_uri,
                "availability_state": "not_returned_by_channels_list",
            })
        page_path = run_dir / "normalized" / "channel-pages" / f"{result.fingerprint.removeprefix('sha256:')}.jsonl"
        write_jsonl(page_path, rows)
        append_jsonl(checkpoint_path, {
            "schema": "north-hux.youtube-stage-checkpoint.v1",
            "stage": "channel_enrichment",
            "target_id": canonical_hash(ids),
            "page_index": 0,
            "request_fingerprint": result.fingerprint,
            "raw_sha256": result.raw_sha256,
            "raw_uri": result.raw_uri,
            "normalized_uri": page_path.relative_to(run_dir).as_posix(),
            "normalized_sha256": hashlib.sha256(page_path.read_bytes()).hexdigest(),
            "status": "page_committed",
            "committed_at": result.captured_at,
        })
    aggregate = aggregate_enrichment(run_dir)
    write_jsonl(run_dir / "derived" / "channel-snapshots.jsonl", aggregate)
    observed_accounts = [row for row in aggregate if row.get("availability_state") == "observed"]
    write_jsonl(run_dir / "derived" / "account-census-cohort.jsonl", observed_accounts)
    return {"new_channel_requests": requests, "requested_candidates": sum(len(batch) for batch in batches), "returned_snapshots": sum(1 for row in aggregate if row.get("availability_state") == "observed"), "unavailable_snapshots": sum(1 for row in aggregate if row.get("availability_state") != "observed")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--config", default=PROJECT_ROOT / "config/youtube-census-v1.json", type=Path)
    parser.add_argument("--secret-file", required=True, type=Path)
    parser.add_argument("--authorization-receipt", required=True, type=Path)
    parser.add_argument("--stage", choices=("smoke", "discover", "enrich", "cohort", "top100", "all"), default="smoke")
    parser.add_argument("--max-new-search-calls", type=int, default=1)
    parser.add_argument("--enrich-batch-limit", type=int)
    args = parser.parse_args()
    try:
        config = load_json(args.config)
        validate_config(config)
        validate_execution_authorization(args.authorization_receipt, args.run_dir)
        if args.max_new_search_calls < 0:
            raise ValueError("max-new-search-calls must be non-negative")
        if args.stage == "cohort":
            summary = {
                "schema": "north-hux.youtube-census-stage.v1",
                "stage": "cohort",
                "cohort": construct_content_cohort(args.run_dir, config),
                "status": "pass",
            }
            print(json.dumps(summary, sort_keys=True))
            return 0
        if args.stage == "top100":
            summary = {
                "schema": "north-hux.youtube-census-stage.v1",
                "stage": "top100",
                "top100": construct_top_references(args.run_dir, config),
                "status": "pass",
            }
            print(json.dumps(summary, sort_keys=True))
            return 0
        api_key = load_secret("youtube", secret_file=args.secret_file)
        quota = QuotaLedger(
            args.run_dir / "ledgers" / "youtube-api-quota.jsonl",
            daily_unit_budget=int(config["daily_limits"]["api_units"]),
            daily_search_call_budget=int(config["daily_limits"]["local_search_call_budget"]),
        )
        client = YouTubeDataAPIClient(
            api_key=api_key,
            run_dir=args.run_dir,
            quota=quota,
            timeout_seconds=float(config["request"]["timeout_seconds"]),
            max_attempts=int(config["request"]["max_attempts"]),
            min_interval_seconds=float(config["request"]["min_interval_seconds"]),
        )
        summary: dict[str, Any] = {"schema": "north-hux.youtube-census-stage.v1", "stage": args.stage}
        if args.stage == "smoke":
            result = client.get("search", "search.list", {"part": "snippet", "type": "channel", "maxResults": "1", "q": "AI agents business", "relevanceLanguage": "en"}, estimated_units=1)
            summary.update({"status": "pass", "item_count": len(result.payload.get("items", [])), "resumed": result.resumed})
        else:
            if args.stage in {"discover", "all"}:
                summary["discover"] = discover(client, config, args.run_dir, args.max_new_search_calls)
            if args.stage in {"enrich", "all"}:
                summary["enrich"] = enrich(client, args.run_dir, batch_limit=args.enrich_batch_limit)
            summary["status"] = "pass"
        summary["quota_usage_today"] = quota.usage()
        print(json.dumps(summary, sort_keys=True))
        return 0
    except (OSError, ValueError, SecretSourceError, YouTubeAPIError) as exc:
        code = exc.code if isinstance(exc, YouTubeAPIError) else type(exc).__name__
        print(json.dumps({"status": "error", "error_code": code}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
