#!/usr/bin/env python3
"""Load the prior provider-disabled corpus into the local North Hux PostgreSQL layer.

This is an idempotent, metadata-only calibration loader. It never contacts a social
platform and never writes media bytes. Raw payload pointers remain run-local.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from psycopg.types.json import Jsonb


ROOT = Path(__file__).resolve().parents[1]
RUN_KEY = "20260825-north-hux-collection-v1"
CAPTURED_AT = datetime(2026, 8, 24, tzinfo=timezone.utc)
DSN = "host=127.0.0.1 port=55432 dbname=north_hux"


def digest(payload: object, declared: str | None = None) -> str:
    if declared:
        candidate = declared.removeprefix("sha256:")
        if re.fullmatch(r"[0-9a-f]{64}", candidate):
            return candidate
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(body).hexdigest()


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def video_id(url: str) -> str:
    match = re.search(r"[?&]v=([^&/]+)", url)
    return match.group(1) if match else url.rstrip("/").rsplit("/", 1)[-1]


def iso_or_none(value: object):
    if not value:
        return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def main() -> None:
    source_path = ROOT / "runs/20260824-m2-bootstrap-v1/burn-in/source-records.jsonl"
    seed_sources = jsonl(source_path)
    raw_files = sorted((ROOT / "runs/20260824-m2-bootstrap-v1/collection").glob("YT-M2-*.raw.jsonl"))
    raw_youtube = []
    seen_youtube = set()
    for path in raw_files:
        for row in jsonl(path):
            native = row.get("id")
            if native and native not in seen_youtube:
                seen_youtube.add(native)
                raw_youtube.append((path, row))

    with psycopg.connect(DSN) as conn:
        with conn.transaction():
            conn.execute("SET search_path = north_hux, public")

            run_row = conn.execute(
                """
                INSERT INTO research_run (run_key, status, scope_json, taxonomy_version, owner_gate)
                VALUES (%s, 'calibration', %s, 'north-hux-taxonomy-v1', 'owner_confirmed_scope')
                ON CONFLICT (run_key) DO UPDATE SET scope_json = EXCLUDED.scope_json
                RETURNING run_id
                """,
                (
                    RUN_KEY,
                    Jsonb(
                        {
                            "target_per_platform": {"minimum": 10000, "maximum": 12000},
                            "platforms": ["instagram", "tiktok", "youtube"],
                            "language_policy": "english_preferred_not_required",
                            "quota_policy": "none",
                            "eu_scope": "EU27",
                            "local_retention_approved": ["comments", "transcripts", "media", "frames"],
                        }
                    ),
                ),
            ).fetchone()[0]

            adapter_ids = {}
            for platform, name, version, route, approval in [
                ("instagram", "seed-registry", "v1", "user-supplied-seed", "blocked"),
                ("tiktok", "public-route-admission", "v1", "no-admitted-route", "blocked"),
                ("youtube", "yt-dlp-public-metadata", "v1", "public-metadata", "approved"),
            ]:
                row = conn.execute(
                    """
                    INSERT INTO adapter (platform, adapter_name, adapter_version, route_kind, approval_state)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (platform, adapter_name, adapter_version) DO UPDATE SET approval_state = EXCLUDED.approval_state
                    RETURNING adapter_id
                    """,
                    (platform, name, version, route, approval),
                ).fetchone()
                adapter_ids[platform] = row[0]

            job_ids = {}
            for platform, status in [("instagram", "blocked"), ("tiktok", "blocked"), ("youtube", "partial")]:
                job_ids[platform] = conn.execute(
                    """
                    INSERT INTO collection_job (run_id, adapter_id, platform, job_type, status, failure_code)
                    VALUES (%s, %s, %s, 'discovery', %s, %s)
                    RETURNING job_id
                    """,
                    (
                        run_row,
                        adapter_ids[platform],
                        platform,
                        status,
                        "route_unavailable" if status == "blocked" else None,
                    ),
                ).fetchone()[0]

            source_ids: dict[str, int] = {}
            raw_ids: dict[str, int] = {}

            def add_source(platform: str, source_type: str, native: str, url: str, role: str, rights: str, route: str):
                row = conn.execute(
                    """
                    INSERT INTO source_registry (run_id, platform, source_type, native_id, canonical_url, source_role, discovery_route, rights_state, last_seen_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (canonical_url) DO UPDATE SET last_seen_at = EXCLUDED.last_seen_at
                    RETURNING source_id
                    """,
                    (run_row, platform, source_type, native, url, role, route, rights, CAPTURED_AT),
                ).fetchone()[0]
                source_ids[url] = row
                return row

            for row in seed_sources:
                platform = row["platform"]
                url = row["canonical_url"]
                source_type = "seed"
                native = row.get("reference_id") or video_id(url)
                rights = "blocked" if row.get("evidence_status") == "seed_only" else "metadata_only"
                source_id = add_source(platform, source_type, native, url, "adjacent", rights, "prior-seed-registry")
                raw = conn.execute(
                    """
                    INSERT INTO raw_object (run_id, job_id, source_id, platform, native_object_type, native_object_id, payload_uri, payload_json, sha256, captured_at, retention_class, redaction_state)
                    VALUES (%s, %s, %s, %s, 'seed_record', %s, %s, %s, %s, %s, 'metadata', 'approved')
                    ON CONFLICT (platform, native_object_type, native_object_id, captured_at) DO UPDATE SET payload_uri = EXCLUDED.payload_uri
                    RETURNING raw_object_id
                    """,
                    (
                        run_row,
                        job_ids[platform],
                        source_id,
                        platform,
                        native,
                        str(source_path),
                        Jsonb(row),
                        digest(row, row.get("raw_hash")),
                        CAPTURED_AT,
                    ),
                ).fetchone()[0]
                raw_ids[native] = raw

            for path, row in raw_youtube:
                url = row.get("webpage_url") or row.get("original_url") or row.get("url")
                native = row["id"]
                source_id = source_ids.get(url) or add_source(
                    "youtube", "content", native, url, "adjacent", "metadata_only", "yt-dlp-public-metadata"
                )
                raw_ids[native] = conn.execute(
                    """
                    INSERT INTO raw_object (run_id, job_id, source_id, platform, native_object_type, native_object_id, payload_uri, payload_json, sha256, captured_at, retention_class, redaction_state)
                    VALUES (%s, %s, %s, 'youtube', 'video_metadata', %s, %s, %s, %s, %s, 'metadata', 'approved')
                    ON CONFLICT (platform, native_object_type, native_object_id, captured_at) DO UPDATE SET payload_uri = EXCLUDED.payload_uri
                    RETURNING raw_object_id
                    """,
                    (run_row, job_ids["youtube"], source_id, native, str(path), Jsonb(row), digest(row), CAPTURED_AT),
                ).fetchone()[0]

            entity_ids: dict[str, int] = {}
            account_ids: dict[tuple[str, str], int] = {}

            def add_entity(key: str, kind: str, name: str | None):
                row = conn.execute(
                    """
                    INSERT INTO creator_entity (entity_key, entity_kind, display_name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (entity_key) DO UPDATE SET display_name = COALESCE(EXCLUDED.display_name, creator_entity.display_name)
                    RETURNING creator_entity_id
                    """,
                    (key, kind, name),
                ).fetchone()[0]
                entity_ids[key] = row
                return row

            def add_account(platform: str, native: str, name: str | None, url: str, source_id: int | None, entity_key: str, qualification: str, relevance: str):
                entity_id = entity_ids.get(entity_key) or add_entity(entity_key, "unknown", name)
                row = conn.execute(
                    """
                    INSERT INTO platform_account (creator_entity_id, source_id, platform, native_account_id, handle, canonical_url, primary_archetype, qualification_state, relevance_class)
                    VALUES (%s, %s, %s, %s, %s, %s, 'unknown', %s, %s)
                    ON CONFLICT (platform, native_account_id) DO UPDATE SET source_id = COALESCE(EXCLUDED.source_id, platform_account.source_id)
                    RETURNING account_id
                    """,
                    (entity_id, source_id, platform, native, name, url, qualification, relevance),
                ).fetchone()[0]
                account_ids[(platform, native)] = row
                return row

            for row in seed_sources:
                if row["entity_type"] == "creator_reference":
                    ref = row["reference_id"]
                    add_entity(f"instagram:{ref}", "unknown", row.get("label"))
                    add_account("instagram", ref, row.get("label"), row["canonical_url"], source_ids[row["canonical_url"]], f"instagram:{ref}", "blocked", "unknown")
            unresolved = add_account("instagram", "unresolved", None, "https://www.instagram.com/", None, "instagram:unresolved", "blocked", "unknown")

            for path, row in raw_youtube:
                channel = row.get("channel_id") or row.get("uploader_id") or f"unknown:{row['id']}"
                channel_url = row.get("channel_url") or row.get("uploader_url") or "https://www.youtube.com/"
                entity_key = f"youtube:{channel}"
                add_entity(entity_key, "solo_creator" if row.get("uploader") else "unknown", row.get("uploader") or row.get("channel"))
                add_account("youtube", channel, row.get("uploader") or row.get("channel"), channel_url, source_ids.get(row.get("webpage_url")), entity_key, "candidate", "adjacent_topic")

            content_ids: dict[tuple[str, str], int] = {}

            def add_content(platform: str, native: str, account_id: int, source_id: int, url: str, kind: str, title: str | None, caption: str | None, duration_ms: int | None, rights: str, raw_id: int | None):
                row = conn.execute(
                    """
                    INSERT INTO content_item (account_id, source_id, platform, native_content_id, canonical_url, content_kind, format_evidence_state, title, caption, duration_ms, rights_state)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (platform, native_content_id) DO UPDATE SET title = COALESCE(EXCLUDED.title, content_item.title), caption = COALESCE(EXCLUDED.caption, content_item.caption)
                    RETURNING content_id
                    """,
                    (account_id, source_id, platform, native, url, kind, "inferred" if kind == "unknown" else "platform_declared", title, caption, duration_ms, rights),
                ).fetchone()[0]
                content_ids[(platform, native)] = row
                return row

            for row in seed_sources:
                if row["entity_type"] != "post_reference":
                    continue
                parent = row.get("parent_creator_reference_id")
                account_id = account_ids.get(("instagram", parent), unresolved)
                url = row["canonical_url"]
                kind = "reel" if "/reel/" in url else "unknown"
                add_content("instagram", row["reference_id"], account_id, source_ids[url], url, kind, None, None, None, "blocked", raw_ids[row["reference_id"]])

            for path, row in raw_youtube:
                url = row.get("webpage_url") or row.get("original_url") or row.get("url")
                channel = row.get("channel_id") or row.get("uploader_id") or f"unknown:{row['id']}"
                add_content("youtube", row["id"], account_ids[("youtube", channel)], source_ids[url], url, "unknown", row.get("title"), None, int(row["duration"] * 1000) if row.get("duration") else None, "metadata_only", raw_ids[row["id"]])

            metric_defs = {}
            for platform in ["instagram", "tiktok", "youtube"]:
                for native, canonical in [("view_count", "views"), ("like_count", "likes"), ("comment_count", "comments"), ("share_count", "shares"), ("repost_count", "reposts"), ("send_count", "sends")]:
                    metric_defs[(platform, canonical)] = conn.execute(
                        """
                        INSERT INTO metric_definition (platform, native_name, canonical_name, visibility_class, metric_definition_version, unit, notes)
                        VALUES (%s, %s, %s, 'public', 'north-hux-v1', 'count', 'Public value only; unavailable fields remain null')
                        ON CONFLICT (platform, native_name, metric_definition_version) DO UPDATE SET notes = EXCLUDED.notes
                        RETURNING metric_definition_id
                        """,
                        (platform, native, canonical),
                    ).fetchone()[0]

            yt_by_id = {row["id"]: row for _, row in raw_youtube}
            for (platform, native), content_id in content_ids.items():
                source_raw = raw_ids.get(native)
                observed = yt_by_id.get(native, {}) if platform == "youtube" else {}
                for canonical in ["views", "likes", "comments", "shares", "reposts", "sends"]:
                    value = observed.get("view_count") if canonical == "views" and observed.get("view_count") is not None else None
                    state = "observed" if value is not None else ("not_exposed" if platform == "youtube" else "not_requested")
                    conn.execute(
                        """
                        INSERT INTO metric_snapshot (content_id, metric_definition_id, raw_object_id, observed_at, metric_value, availability_state, is_estimated)
                        SELECT %s, %s, %s, %s, %s, %s, false
                        WHERE NOT EXISTS (SELECT 1 FROM metric_snapshot WHERE content_id = %s AND metric_definition_id = %s AND observed_at = %s)
                        """,
                        (content_id, metric_defs[(platform, canonical)], source_raw, CAPTURED_AT, value, state, content_id, metric_defs[(platform, canonical)], CAPTURED_AT),
                    )
                for interaction in ["comment", "like", "share", "repost", "send"]:
                    conn.execute(
                        """
                        INSERT INTO interaction_coverage (content_id, interaction_type, observed_at, reported_count, retrieved_count, pagination_complete, sampling_method, gap_reason, raw_object_id)
                        SELECT %s, %s, %s, NULL, 0, false, 'not_collected', %s, %s
                        WHERE NOT EXISTS (SELECT 1 FROM interaction_coverage WHERE content_id = %s AND interaction_type = %s AND observed_at = %s)
                        """,
                        (content_id, interaction, CAPTURED_AT, "route_not_admitted_or_field_not_returned", source_raw, content_id, interaction, CAPTURED_AT),
                    )
                conn.execute(
                    """
                    INSERT INTO rights_decision (run_id, source_id, content_id, allowed_use, decision, basis, reviewer)
                    SELECT %s, source_id, %s, %s, 'pass', %s, 'codex-loader'
                    FROM content_item WHERE content_id = %s
                    AND NOT EXISTS (SELECT 1 FROM rights_decision WHERE run_id = %s AND content_id = %s)
                    """,
                    (run_row, content_id, "metadata_only" if platform == "youtube" else "blocked", "prior provider-disabled metadata/seed state", content_id, run_row, content_id),
                )

            taxonomy = {
                "agentic_categories": ["agent_fundamentals", "workflow_automation", "orchestration", "knowledge_continuity", "pm_workflows", "engineering_productivity", "evaluation_observability", "security_governance", "integrations", "news_comparison", "build_in_public"],
                "video_types": ["talking_head", "screen_demo", "walkthrough", "case_study", "teardown", "tutorial", "reaction", "opinion", "interview_clip", "failure_report", "comparison", "community_reply"],
                "story_beats": ["hook", "tension", "promise", "mechanism", "proof", "caveat", "payoff", "cta"],
                "audience_activity": ["question", "pain", "objection", "confusion", "confirmation", "critique", "implementation_evidence", "tool_request", "intent", "noise"],
                "frame_tags": ["face", "screen", "b_roll", "on_screen_text", "proof", "caption_density", "cut", "cta", "source_receipt"],
            }
            taxonomy_id = conn.execute(
                """
                INSERT INTO taxonomy_version (taxonomy_key, version, definition_json)
                VALUES ('north-hux', 'v1', %s)
                ON CONFLICT (taxonomy_key, version) DO UPDATE SET definition_json = EXCLUDED.definition_json
                RETURNING taxonomy_version_id
                """,
                (Jsonb(taxonomy),),
            ).fetchone()[0]

            for platform in ["instagram", "tiktok", "youtube"]:
                for category in ["accounts", "posts", "stats", "captions", "comments", "transcripts", "video", "frames", "taxonomy", "review", "notion_projection", "obsidian_projection"]:
                    target = {"accounts": 10000, "posts": 50000, "stats": 50000, "captions": 1000, "comments": 1000, "transcripts": 1000, "video": 200, "frames": 200}.get(category, 1)
                    admitted = len([1 for (p, _), _id in account_ids.items() if p == platform]) if category == "accounts" else len([1 for (p, _), _id in content_ids.items() if p == platform]) if category in {"posts", "stats"} else 0
                    completed = admitted if category in {"accounts", "posts"} and platform == "youtube" else 0
                    blocked = target if platform in {"instagram", "tiktok"} and category in {"accounts", "posts", "stats", "comments", "transcripts", "video", "frames"} else 0
                    conn.execute(
                        """
                        INSERT INTO analysis_progress (run_id, platform, category, target_count, eligible_count, admitted_count, completed_count, reviewed_count, blocked_count)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 0, %s)
                        ON CONFLICT (run_id, platform, category) DO UPDATE SET target_count = EXCLUDED.target_count, eligible_count = EXCLUDED.eligible_count, admitted_count = EXCLUDED.admitted_count, completed_count = EXCLUDED.completed_count, blocked_count = EXCLUDED.blocked_count, last_updated_at = now()
                        """,
                        (run_row, platform, category, target, admitted, admitted, completed, blocked),
                    )

            print(json.dumps({
                "run_id": run_row,
                "seed_sources": len(seed_sources),
                "youtube_raw": len(raw_youtube),
                "platform_accounts": len(account_ids),
                "content_items": len(content_ids),
                "status": "loaded_metadata_only_and_seed_references",
            }, indent=2))


if __name__ == "__main__":
    main()
