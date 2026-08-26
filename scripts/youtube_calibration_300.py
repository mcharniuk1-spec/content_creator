#!/usr/bin/env python3
"""Collect recent uploads and qualify the 300-account YouTube calibration."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from m2_engine.secret_source import SecretSourceError, load_secret  # noqa: E402
from m2_engine.youtube_api import QuotaLedger, YouTubeAPIError, YouTubeDataAPIClient  # noqa: E402
from scripts.youtube_census import load_json, validate_config, validate_execution_authorization, write_jsonl  # noqa: E402


AGENT_TERMS = re.compile(r"\b(ai agents?|agentic|multi[- ]agent|autonomous agents?|llm agents?|copilot|langgraph|crewai|autogen|mcp|model context protocol|rag|retrieval augmented|n8n|make\.com|zapier)\b", re.I)
BUSINESS_TERMS = re.compile(r"\b(business|company|enterprise|product management|product manager|operations|workflow|sales|marketing|customer|revenue|roi|cost|team|founder|agency|implementation|integration|automation)\b", re.I)
PROOF_TERMS = re.compile(r"\b(demo|tutorial|walkthrough|case study|step[- ]by[- ]step|build|tested|results?|before|after|hours?|cost|benchmark|production|real[- ]world)\b", re.I)


def parse_duration(value: str | None) -> int | None:
    if not value or not value.startswith("P"):
        return None
    match = re.fullmatch(r"P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value)
    if not match:
        return None
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def age_days(value: str | None, now: datetime | None = None) -> int | None:
    if not value:
        return None
    observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return max(0, int(((now or datetime.now(UTC)) - observed).total_seconds() // 86400))


def english_evidence(item: dict[str, Any]) -> tuple[bool, str]:
    snippet = item.get("snippet", {})
    for field in ("defaultAudioLanguage", "defaultLanguage"):
        language = snippet.get(field)
        if isinstance(language, str) and language.lower().startswith("en"):
            return True, f"official_{field}={language}"
    text = " ".join(str(snippet.get(field) or "") for field in ("title", "description"))
    letters = [character for character in text if character.isalpha()]
    if letters and sum("a" <= character.lower() <= "z" for character in letters) / len(letters) >= 0.9:
        return True, "metadata_latin_letter_ratio>=0.90"
    return False, "english_not_evidenced"


def relevance(item: dict[str, Any]) -> dict[str, Any]:
    snippet = item.get("snippet", {})
    text = "\n".join([str(snippet.get("title") or ""), str(snippet.get("description") or ""), " ".join(snippet.get("tags") or [])])
    agent_hits = len(AGENT_TERMS.findall(text))
    business_hits = len(BUSINESS_TERMS.findall(text))
    proof_hits = len(PROOF_TERMS.findall(text))
    relevant = agent_hits > 0 and (business_hits > 0 or proof_hits > 0)
    return {"relevant": relevant, "agent_hits": agent_hits, "business_hits": business_hits, "proof_hits": proof_hits}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def load_channels(run_dir: Path, max_channels: int | None) -> list[dict[str, Any]]:
    candidates = {row["native_channel_id"]: row for row in load_jsonl(run_dir / "derived" / "channel-candidates.jsonl")}
    snapshots = load_jsonl(run_dir / "derived" / "channel-snapshots.jsonl")
    rows = []
    for snapshot in snapshots:
        channel_id = snapshot.get("native_channel_id")
        if snapshot.get("availability_state") != "observed" or not snapshot.get("uploads_playlist_id"):
            continue
        candidate = candidates.get(channel_id, {})
        search_count = int(candidate.get("discovery_observation_count") or 0)
        text = " ".join(str(value or "") for value in (snapshot.get("title"), snapshot.get("description"), candidate.get("title"), candidate.get("description")))
        rows.append({**snapshot, "discovery_observation_count": search_count, "discovery_text_agent_hits": len(AGENT_TERMS.findall(text)), "discovery_text_business_hits": len(BUSINESS_TERMS.findall(text))})
    rows.sort(key=lambda row: (-int(row["discovery_text_agent_hits"] > 0), -int(row["discovery_text_business_hits"] > 0), -row["discovery_observation_count"], -int(row.get("subscriber_count") or 0), row["native_channel_id"]))
    return rows[:max_channels] if max_channels else rows


def collect_uploads(client: YouTubeDataAPIClient, run_dir: Path, config: dict[str, Any], max_channels: int | None) -> dict[str, int]:
    channels = load_channels(run_dir, max_channels)
    limit = int(config["qualification"]["recent_uploads_per_channel"])
    requests = 0
    observations = 0
    for index, channel in enumerate(channels, start=1):
        result = client.get("playlistItems", "playlistItems.list", {
            "part": "snippet,contentDetails,status",
            "playlistId": channel["uploads_playlist_id"],
            "maxResults": str(limit),
        }, estimated_units=1)
        if not result.resumed:
            requests += 1
        rows = []
        for item in result.payload.get("items", []):
            content = item.get("contentDetails", {})
            snippet = item.get("snippet", {})
            video_id = content.get("videoId") or snippet.get("resourceId", {}).get("videoId")
            if not video_id:
                continue
            rows.append({
                "schema": "north-hux.youtube-upload-reference.v1",
                "native_channel_id": channel["native_channel_id"],
                "uploads_playlist_id": channel["uploads_playlist_id"],
                "native_video_id": video_id,
                "canonical_url": f"https://www.youtube.com/watch?v={video_id}",
                "playlist_position": snippet.get("position"),
                "playlist_title": snippet.get("title"),
                "playlist_description": snippet.get("description"),
                "published_at": content.get("videoPublishedAt") or snippet.get("publishedAt"),
                "privacy_status": item.get("status", {}).get("privacyStatus"),
                "captured_at": result.captured_at,
                "refresh_or_delete_by": result.refresh_or_delete_by,
                "source_request_fingerprint": result.fingerprint,
                "raw_uri": result.raw_uri,
                "raw_sha256": result.raw_sha256,
            })
        path = run_dir / "normalized" / "upload-pages" / f"{result.fingerprint.removeprefix('sha256:')}.jsonl"
        write_jsonl(path, rows)
        observations += len(rows)
        if index % 100 == 0:
            print(json.dumps({"progress": "uploads", "channels": index, "rows": observations}), flush=True)
    aggregate: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted((run_dir / "normalized" / "upload-pages").glob("*.jsonl")):
        for row in load_jsonl(path):
            aggregate[(row["native_channel_id"], row["native_video_id"])] = row
    write_jsonl(run_dir / "derived" / "upload-references.jsonl", sorted(aggregate.values(), key=lambda row: (row["native_channel_id"], int(row.get("playlist_position") or 0), row["native_video_id"])))
    return {"channels": len(channels), "new_requests": requests, "distinct_upload_references": len(aggregate)}


def chunks(values: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index:index + size]


def collect_video_details(client: YouTubeDataAPIClient, run_dir: Path, config: dict[str, Any]) -> dict[str, int]:
    uploads = load_jsonl(run_dir / "derived" / "upload-references.jsonl")
    owner = {row["native_video_id"]: row["native_channel_id"] for row in uploads}
    ids = sorted(owner)
    requests = 0
    observed = 0
    for batch in chunks(ids, 50):
        result = client.get("videos", "videos.list", {
            "part": "id,snippet,contentDetails,statistics,status,topicDetails",
            "id": ",".join(batch),
            "maxResults": "50",
        }, estimated_units=1)
        if not result.resumed:
            requests += 1
        rows = []
        for item in result.payload.get("items", []):
            video_id = str(item.get("id") or "")
            if not video_id or video_id not in owner:
                continue
            snippet = item.get("snippet", {})
            duration_seconds = parse_duration(item.get("contentDetails", {}).get("duration"))
            english, english_basis = english_evidence(item)
            signals = relevance(item)
            days = age_days(snippet.get("publishedAt"))
            format_state = "DURATION_CANDIDATE" if duration_seconds is not None and duration_seconds <= 180 else "NON_SHORT" if duration_seconds is not None else "UNKNOWN"
            analysis_eligible = bool(signals["relevant"] and english and days is not None and days <= int(config["qualification"]["baseline_days"]))
            statistics = item.get("statistics", {})
            status = item.get("status", {})
            rows.append({
                "schema": "north-hux.youtube-video-snapshot.v1",
                "native_channel_id": owner[video_id],
                "native_video_id": video_id,
                "canonical_url": f"https://www.youtube.com/watch?v={video_id}",
                "title": snippet.get("title"),
                "description": snippet.get("description"),
                "published_at": snippet.get("publishedAt"),
                "age_days": days,
                "duration_seconds": duration_seconds,
                "format_state": format_state,
                "native_short_proved": False,
                "english_evidenced": english,
                "english_evidence_basis": english_basis,
                "analysis_eligible": analysis_eligible,
                "relevance_signals": signals,
                "view_count": int(statistics["viewCount"]) if statistics.get("viewCount") is not None else None,
                "like_count": int(statistics["likeCount"]) if statistics.get("likeCount") is not None else None,
                "comment_count": int(statistics["commentCount"]) if statistics.get("commentCount") is not None else None,
                "license": status.get("license"),
                "made_for_kids": status.get("madeForKids"),
                "privacy_status": status.get("privacyStatus"),
                "captured_at": result.captured_at,
                "refresh_or_delete_by": result.refresh_or_delete_by,
                "source_request_fingerprint": result.fingerprint,
                "raw_uri": result.raw_uri,
                "raw_sha256": result.raw_sha256,
            })
        path = run_dir / "normalized" / "video-pages" / f"{result.fingerprint.removeprefix('sha256:')}.jsonl"
        write_jsonl(path, rows)
        observed += len(rows)
    aggregate: dict[str, dict[str, Any]] = {}
    for path in sorted((run_dir / "normalized" / "video-pages").glob("*.jsonl")):
        for row in load_jsonl(path):
            current = aggregate.get(row["native_video_id"])
            if current is None or str(row.get("captured_at") or "") >= str(current.get("captured_at") or ""):
                aggregate[row["native_video_id"]] = row
    write_jsonl(run_dir / "derived" / "video-snapshots.jsonl", sorted(aggregate.values(), key=lambda row: (row["native_channel_id"], row["native_video_id"])))
    return {"requested_video_ids": len(ids), "new_requests": requests, "observed_video_snapshots": len(aggregate)}


def qualify(run_dir: Path, config: dict[str, Any]) -> dict[str, int]:
    channels = {row["native_channel_id"]: row for row in load_jsonl(run_dir / "derived" / "channel-snapshots.jsonl")}
    videos = load_jsonl(run_dir / "derived" / "video-snapshots.jsonl")
    by_channel: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in videos:
        by_channel[row["native_channel_id"]].append(row)
    q = config["qualification"]
    candidates = []
    for channel_id, channel in channels.items():
        rows = by_channel.get(channel_id, [])
        relevant = [row for row in rows if row.get("analysis_eligible") is True]
        short = [row for row in relevant if row.get("format_state") == "DURATION_CANDIDATE"]
        fresh = [row for row in relevant if row.get("age_days") is not None and row["age_days"] <= int(q["fresh_days"])]
        business_hits = sum(int(row.get("relevance_signals", {}).get("business_hits") or 0) for row in relevant)
        proof_hits = sum(int(row.get("relevance_signals", {}).get("proof_hits") or 0) for row in relevant)
        track = 3 if len(relevant) >= 5 else 2 if len(relevant) >= 3 else 0
        audience = 2 if business_hits >= 3 else 1 if business_hits else 0
        specificity = 2 if business_hits >= 5 else 1 if business_hits >= 2 else 0
        proof = 2 if proof_hits >= 3 else 1 if proof_hits else 0
        activity = 1 if fresh else 0
        source = 2
        score = track + audience + specificity + proof + activity + source
        gates = {
            "public_route": True,
            "stable_identity": bool(channel_id and channel.get("canonical_url")),
            "minimum_relevant_videos": len(relevant) >= int(q["minimum_relevant_videos"]),
            "minimum_short_candidates": len(short) >= int(q["minimum_short_candidates"]),
            "activity": bool(fresh),
            "english_evidence": sum(row.get("english_evidenced") is True for row in relevant) >= int(q["minimum_relevant_videos"]),
            "rights_retention": True,
        }
        eligible = all(gates.values()) and score >= int(q["minimum_score"]) and track >= 2
        candidates.append({
            "schema": "north-hux.youtube-account-qualification.v1",
            "native_channel_id": channel_id,
            "canonical_url": channel.get("canonical_url"),
            "title": channel.get("title"),
            "description": channel.get("description"),
            "subscriber_count": int(channel["subscriber_count"]) if channel.get("subscriber_count") is not None else None,
            "country": channel.get("country"),
            "language": channel.get("default_language"),
            "relevant_video_count": len(relevant),
            "short_candidate_count": len(short),
            "fresh_relevant_count": len(fresh),
            "score": score,
            "score_components": {"track_fit": track, "audience_fit": audience, "business_specificity": specificity, "proof_quality": proof, "activity": activity, "source_quality": source},
            "hard_gates": gates,
            "qualification_state": "candidate" if eligible else "rejected",
            "review_state": "deterministic_prequalification",
        })
    candidates.sort(key=lambda row: (-int(row["qualification_state"] == "candidate"), -row["score"], -row["short_candidate_count"], -row["relevant_video_count"], -int(row.get("subscriber_count") or 0), row["native_channel_id"]))
    eligible = [row for row in candidates if row["qualification_state"] == "candidate"]
    target = int(config["calibration_content"]["qualified_accounts"])
    if len(eligible) < target:
        write_jsonl(run_dir / "derived" / "account-qualification-all.jsonl", candidates)
        raise ValueError(f"qualification underfilled: need {target}, got {len(eligible)}")
    qualified_ids = {row["native_channel_id"] for row in eligible[:target]}
    for row in candidates:
        if row["native_channel_id"] in qualified_ids:
            row["qualification_state"] = "qualified"
            row["review_state"] = "deterministic_qualified_pending_independent_sample_review"
        elif row["qualification_state"] == "candidate":
            row["qualification_state"] = "needs_review"
    write_jsonl(run_dir / "derived" / "account-qualification-all.jsonl", candidates)
    qualified = [row for row in candidates if row["qualification_state"] == "qualified"]
    write_jsonl(run_dir / "derived" / "qualified-accounts.jsonl", qualified)
    return {"evaluated_accounts": len(candidates), "eligible_before_target_cut": len(eligible), "qualified_accounts": len(qualified), "qualified_video_rows": sum(len([video for video in by_channel[row["native_channel_id"]] if video.get("analysis_eligible") is True]) for row in qualified)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--config", default=ROOT / "config/youtube-census-v1.json", type=Path)
    parser.add_argument("--secret-file", required=True, type=Path)
    parser.add_argument("--authorization-receipt", required=True, type=Path)
    parser.add_argument("--stage", choices=("uploads", "videos", "qualify", "all"), default="all")
    parser.add_argument("--max-channels", type=int)
    args = parser.parse_args()
    try:
        config = load_json(args.config)
        validate_config(config)
        validate_execution_authorization(args.authorization_receipt, args.run_dir)
        if args.stage == "qualify":
            print(json.dumps({"status": "pass", "qualify": qualify(args.run_dir, config)}, sort_keys=True))
            return 0
        key = load_secret("youtube", secret_file=args.secret_file)
        quota = QuotaLedger(args.run_dir / "ledgers" / "youtube-api-quota.jsonl", daily_unit_budget=int(config["daily_limits"]["api_units"]), daily_search_call_budget=int(config["daily_limits"]["local_search_call_budget"]))
        client = YouTubeDataAPIClient(api_key=key, run_dir=args.run_dir, quota=quota, timeout_seconds=float(config["request"]["timeout_seconds"]), max_attempts=int(config["request"]["max_attempts"]), min_interval_seconds=float(config["request"]["min_interval_seconds"]))
        summary: dict[str, Any] = {"schema": "north-hux.youtube-calibration-stage.v1", "stage": args.stage}
        if args.stage in {"uploads", "all"}:
            summary["uploads"] = collect_uploads(client, args.run_dir, config, args.max_channels)
        if args.stage in {"videos", "all"}:
            summary["videos"] = collect_video_details(client, args.run_dir, config)
        if args.stage == "all":
            summary["qualify"] = qualify(args.run_dir, config)
        summary["quota_usage_today"] = quota.usage()
        summary["status"] = "pass"
        print(json.dumps(summary, sort_keys=True))
        return 0
    except (OSError, ValueError, SecretSourceError, YouTubeAPIError) as exc:
        code = exc.code if isinstance(exc, YouTubeAPIError) else type(exc).__name__
        print(json.dumps({"status": "error", "error_code": code, "message": str(exc)[:500]}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
