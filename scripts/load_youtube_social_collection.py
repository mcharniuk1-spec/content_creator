#!/usr/bin/env python3
"""Load the bounded public YouTube calibration lane into North Hux PostgreSQL.

The loader is idempotent for the immutable run artifacts. It retains public comment
text and subtitle text locally as approved, pseudonymizes comment authors, preserves
unavailable metrics as null, and never promotes a candidate to qualified.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb


ROOT = Path(__file__).resolve().parents[1]
RUN_KEY = "20260825-north-hux-social-adapters-v1"
LANE = ROOT / "runs" / RUN_KEY / "agents" / "youtube_collection"
DSN = "host=127.0.0.1 port=55432 dbname=north_hux"


def jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parsed_at(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def published_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pseudonym(author: str | None) -> str | None:
    if not author:
        return None
    return "yt-author-" + hashlib.sha256(author.encode("utf-8")).hexdigest()[:16]


def relative_pointer(pointer: str) -> tuple[Path, str]:
    path = (LANE / pointer).resolve()
    if not path.is_relative_to(LANE.resolve()) or not path.is_file():
        raise ValueError(f"invalid raw pointer: {pointer}")
    return path, path.relative_to(ROOT).as_posix()


def raw_comment_details(video_id: str) -> dict[str, dict]:
    path = LANE / "raw" / "comments" / f"{video_id}.info.json"
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {row["id"]: row for row in payload.get("comments", []) if isinstance(row, dict) and row.get("id")}


def get_or_create_job(connection, run_id: int, adapter_id: int, job_type: str) -> int:
    row = connection.execute(
        """
        SELECT job_id FROM collection_job
        WHERE run_id = %s AND adapter_id = %s AND platform = 'youtube'
          AND job_type = %s AND target_stratum = 'bounded-public-calibration-v1'
        ORDER BY job_id LIMIT 1
        """,
        (run_id, adapter_id, job_type),
    ).fetchone()
    if row:
        return row[0]
    return connection.execute(
        """
        INSERT INTO collection_job (
            run_id, adapter_id, platform, job_type, target_stratum, status,
            cursor_state, started_at, ended_at
        ) VALUES (%s, %s, 'youtube', %s, 'bounded-public-calibration-v1',
                  'succeeded', '{}'::jsonb, now(), now())
        RETURNING job_id
        """,
        (run_id, adapter_id, job_type),
    ).fetchone()[0]


def main() -> None:
    observations = jsonl(LANE / "observations.jsonl")
    comments = jsonl(LANE / "comments.jsonl")
    transcripts = jsonl(LANE / "transcripts.jsonl")
    if not observations:
        raise SystemExit("no completed observations to load")

    comments_by_video: dict[str, list[dict]] = defaultdict(list)
    transcripts_by_video: dict[str, list[dict]] = defaultdict(list)
    for row in comments:
        comments_by_video[row["native_video_id"]].append(row)
    for row in transcripts:
        transcripts_by_video[row["native_video_id"]].append(row)

    counts: Counter[str] = Counter()
    with psycopg.connect(DSN) as connection:
        with connection.transaction():
            connection.execute("SET search_path = north_hux, public")
            run_id = connection.execute(
                """
                INSERT INTO research_run (
                    run_key, status, scope_json, admission_receipt_uri,
                    taxonomy_version, owner_gate, started_at
                ) VALUES (%s, 'calibration', %s, %s, 'north-hux-taxonomy-v1',
                          'owner_confirmed_public_collection', now())
                ON CONFLICT (run_key) DO UPDATE
                SET status = 'calibration', scope_json = EXCLUDED.scope_json,
                    admission_receipt_uri = EXCLUDED.admission_receipt_uri
                RETURNING run_id
                """,
                (
                    RUN_KEY,
                    Jsonb({
                        "platform": "youtube",
                        "route": "yt-dlp-public",
                        "max_unique_videos": 60,
                        "max_comments_per_video": 20,
                        "no_cookies": True,
                        "no_media_download": True,
                    }),
                    f"runs/{RUN_KEY}/admission-receipt.json",
                ),
            ).fetchone()[0]
            adapter_id = connection.execute(
                """
                INSERT INTO adapter (
                    platform, adapter_name, adapter_version, route_kind,
                    approval_state, terms_uri
                ) VALUES ('youtube', 'yt-dlp-public-calibration', '2026.07.04',
                          'public_metadata_subtitles_comments', 'approved',
                          'https://github.com/yt-dlp/yt-dlp')
                ON CONFLICT (platform, adapter_name, adapter_version) DO UPDATE
                SET approval_state = EXCLUDED.approval_state
                RETURNING adapter_id
                """
            ).fetchone()[0]
            jobs = {kind: get_or_create_job(connection, run_id, adapter_id, kind)
                    for kind in ("content", "metrics", "comments", "transcript")}

            metric_ids: dict[str, int] = {}
            for native, canonical in (
                ("view_count", "views"),
                ("like_count", "likes"),
                ("comment_count", "comments"),
                ("share_count", "shares"),
                ("repost_count", "reposts"),
                ("send_count", "sends"),
                ("save_count", "saves"),
            ):
                metric_ids[canonical] = connection.execute(
                    """
                    INSERT INTO metric_definition (
                        platform, native_name, canonical_name, visibility_class,
                        metric_definition_version, unit, denominator, notes
                    ) VALUES ('youtube', %s, %s, 'public', 'yt-dlp-2026.07.04',
                              'count', 'content_item', 'Null means not exposed by the bounded public route.')
                    ON CONFLICT (platform, native_name, metric_definition_version) DO UPDATE
                    SET notes = EXCLUDED.notes
                    RETURNING metric_definition_id
                    """,
                    (native, canonical),
                ).fetchone()[0]

            for observation in observations:
                video_id = observation["native_video_id"]
                observed_at = parsed_at(observation.get("observed_at"))
                raw_path, raw_uri = relative_pointer(observation["raw_pointer"])
                source_id = connection.execute(
                    """
                    INSERT INTO source_registry (
                        run_id, platform, source_type, native_id, canonical_url,
                        source_role, discovery_route, rights_state, last_seen_at
                    ) VALUES (%s, 'youtube', 'content', %s, %s, 'direct',
                              'yt-dlp-public-calibration', 'metadata_only', %s)
                    ON CONFLICT (platform, native_id) DO UPDATE
                    SET last_seen_at = EXCLUDED.last_seen_at
                    RETURNING source_id
                    """,
                    (run_id, video_id, observation["canonical_url"], observed_at),
                ).fetchone()[0]
                raw_object_id = connection.execute(
                    """
                    INSERT INTO raw_object (
                        run_id, job_id, source_id, platform, native_object_type,
                        native_object_id, payload_uri, payload_json, sha256,
                        captured_at, retention_class, redaction_state
                    ) VALUES (%s, %s, %s, 'youtube', 'video_metadata', %s, %s,
                              %s, %s, %s, 'metadata', 'approved')
                    ON CONFLICT (platform, native_object_type, native_object_id, captured_at)
                    DO UPDATE SET payload_uri = EXCLUDED.payload_uri
                    RETURNING raw_object_id
                    """,
                    (run_id, jobs["content"], source_id, video_id, raw_uri,
                     Jsonb(observation), file_hash(raw_path), observed_at),
                ).fetchone()[0]

                channel_id = observation.get("channel_id") or f"unknown:{video_id}"
                entity_id = connection.execute(
                    """
                    INSERT INTO creator_entity (entity_key, entity_kind, display_name)
                    VALUES (%s, 'unknown', %s)
                    ON CONFLICT (entity_key) DO UPDATE
                    SET display_name = COALESCE(EXCLUDED.display_name, creator_entity.display_name)
                    RETURNING creator_entity_id
                    """,
                    (f"youtube:{channel_id}", observation.get("channel")),
                ).fetchone()[0]
                account_id = connection.execute(
                    """
                    INSERT INTO platform_account (
                        creator_entity_id, source_id, platform, native_account_id,
                        handle, canonical_url, primary_archetype, language_code,
                        relevance_class, qualification_state
                    ) VALUES (%s, %s, 'youtube', %s, %s, %s, 'unknown', %s,
                              'unknown', 'candidate')
                    ON CONFLICT (platform, native_account_id) DO UPDATE
                    SET handle = COALESCE(EXCLUDED.handle, platform_account.handle),
                        language_code = COALESCE(EXCLUDED.language_code, platform_account.language_code)
                    RETURNING account_id
                    """,
                    (entity_id, source_id, channel_id, observation.get("channel"),
                     f"https://www.youtube.com/channel/{channel_id}", observation.get("language")),
                ).fetchone()[0]
                content_id = connection.execute(
                    """
                    INSERT INTO content_item (
                        account_id, source_id, platform, native_content_id,
                        canonical_url, content_kind, format_evidence_state, title,
                        caption, publish_at, duration_ms, language_code, rights_state
                    ) VALUES (%s, %s, 'youtube', %s, %s, %s, %s, %s, %s, %s,
                              %s, %s, 'metadata_only')
                    ON CONFLICT (platform, native_content_id) DO UPDATE
                    SET title = COALESCE(EXCLUDED.title, content_item.title),
                        caption = COALESCE(EXCLUDED.caption, content_item.caption),
                        duration_ms = COALESCE(EXCLUDED.duration_ms, content_item.duration_ms)
                    RETURNING content_id
                    """,
                    (
                        account_id, source_id, video_id, observation["canonical_url"],
                        "short" if observation.get("shorts_qualified") is True else "unknown",
                        "inferred" if observation.get("shorts_qualified") is not None else "unknown",
                        observation.get("title"), observation.get("description"),
                        published_at(observation.get("upload_date")),
                        round(observation["duration_seconds"] * 1000) if observation.get("duration_seconds") is not None else None,
                        observation.get("language"),
                    ),
                ).fetchone()[0]
                counts["observations"] += 1

                for canonical, field in (
                    ("views", "view_count"), ("likes", "like_count"),
                    ("comments", "comment_count"), ("shares", "share_count"),
                    ("reposts", "repost_count"), ("sends", "send_count"),
                    ("saves", "save_count"),
                ):
                    value = observation.get(field)
                    state = "observed" if value is not None else "not_exposed"
                    connection.execute(
                        """
                        INSERT INTO metric_snapshot (
                            content_id, metric_definition_id, raw_object_id,
                            observed_at, metric_value, availability_state, is_estimated
                        ) SELECT %s, %s, %s, %s, %s, %s, false
                        WHERE NOT EXISTS (
                            SELECT 1 FROM metric_snapshot
                            WHERE content_id = %s AND metric_definition_id = %s AND observed_at = %s
                        )
                        """,
                        (content_id, metric_ids[canonical], raw_object_id, observed_at, value,
                         state, content_id, metric_ids[canonical], observed_at),
                    )

                retrieved_comments = comments_by_video.get(video_id, [])
                reported_comments = observation.get("comment_count")
                comment_raw_object_id = None
                comment_details = raw_comment_details(video_id)
                if retrieved_comments:
                    comment_raw_path, comment_raw_uri = relative_pointer(retrieved_comments[0]["raw_pointer"])
                    comment_raw_object_id = connection.execute(
                        """
                        INSERT INTO raw_object (
                            run_id, job_id, source_id, platform, native_object_type,
                            native_object_id, payload_uri, payload_json, sha256,
                            captured_at, retention_class, redaction_state
                        ) VALUES (%s, %s, %s, 'youtube', 'video_comments', %s, %s,
                                  NULL, %s, %s, 'restricted', 'unreviewed')
                        ON CONFLICT (platform, native_object_type, native_object_id, captured_at)
                        DO UPDATE SET payload_uri = EXCLUDED.payload_uri
                        RETURNING raw_object_id
                        """,
                        (run_id, jobs["comments"], source_id, video_id, comment_raw_uri,
                         file_hash(comment_raw_path), observed_at),
                    ).fetchone()[0]
                connection.execute(
                    """
                    INSERT INTO interaction_coverage (
                        content_id, interaction_type, observed_at, reported_count,
                        retrieved_count, pagination_complete, sampling_method,
                        endpoint_limit, gap_reason, raw_object_id
                    ) SELECT %s, 'comment', %s, %s, %s, false,
                             'bounded_public_sample', 'max 20 comments per video', %s, %s
                    WHERE NOT EXISTS (
                        SELECT 1 FROM interaction_coverage
                        WHERE content_id = %s AND interaction_type = 'comment' AND observed_at = %s
                    )
                    """,
                    (content_id, observed_at, reported_comments, len(retrieved_comments),
                     "bounded sample; pagination not asserted complete", comment_raw_object_id or raw_object_id,
                     content_id, observed_at),
                )
                for interaction in ("like", "share", "repost", "send", "save"):
                    connection.execute(
                        """
                        INSERT INTO interaction_coverage (
                            content_id, interaction_type, observed_at, reported_count,
                            retrieved_count, pagination_complete, sampling_method,
                            gap_reason, raw_object_id
                        ) SELECT %s, %s, %s, NULL, 0, false, 'not_exposed',
                                 'actor-level event not exposed by this public route', %s
                        WHERE NOT EXISTS (
                            SELECT 1 FROM interaction_coverage
                            WHERE content_id = %s AND interaction_type = %s AND observed_at = %s
                        )
                        """,
                        (content_id, interaction, observed_at, raw_object_id,
                         content_id, interaction, observed_at),
                    )

                for comment_row in retrieved_comments:
                    if not comment_row.get("comment_id"):
                        continue
                    detail = comment_details.get(comment_row["comment_id"], {})
                    stored = connection.execute(
                        """
                        INSERT INTO comment (
                            content_id, native_comment_id, text_body, author_pseudonym,
                            created_at, like_count, reply_count, is_pinned, raw_object_id
                        ) VALUES (%s, %s, %s, %s, to_timestamp(%s), %s, %s, %s, %s)
                        ON CONFLICT (content_id, native_comment_id) DO NOTHING
                        RETURNING comment_id
                        """,
                        (
                            content_id, comment_row["comment_id"], comment_row.get("text"),
                            pseudonym(comment_row.get("author")), comment_row.get("timestamp"),
                            comment_row.get("like_count"), detail.get("reply_count"),
                            detail.get("is_pinned"), comment_raw_object_id or raw_object_id,
                        ),
                    ).fetchone()
                    stored_comment_id = stored[0] if stored else connection.execute(
                        "SELECT comment_id FROM comment WHERE content_id = %s AND native_comment_id = %s",
                        (content_id, comment_row["comment_id"]),
                    ).fetchone()[0]
                    native_parent = detail.get("parent")
                    event_type = "reply" if native_parent and native_parent != "root" else "comment"
                    connection.execute(
                        """
                        INSERT INTO interaction_event (
                            content_id, native_event_id, event_type, actor_pseudonym,
                            observed_at, raw_object_id, event_state
                        ) VALUES (%s, %s, %s, %s, to_timestamp(%s), %s, 'observed')
                        ON CONFLICT (content_id, native_event_id, event_type) DO NOTHING
                        """,
                        (content_id, comment_row["comment_id"], event_type,
                         pseudonym(comment_row.get("author")), comment_row.get("timestamp"),
                         comment_raw_object_id or raw_object_id),
                    )
                    if event_type == "reply":
                        connection.execute(
                            """
                            INSERT INTO comment_edge_observation (
                                comment_id, relationship_type, native_parent_comment_id,
                                observed_at, raw_object_id
                            ) VALUES (%s, 'reply', %s, %s, %s)
                            ON CONFLICT (comment_id, native_parent_comment_id, observed_at) DO NOTHING
                            """,
                            (stored_comment_id, native_parent, observed_at, comment_raw_object_id or raw_object_id),
                        )
                    counts["comments"] += 1

                for transcript_row in transcripts_by_video.get(video_id, []):
                    transcript_path, transcript_uri = relative_pointer(transcript_row["source_file"])
                    transcript_hash = file_hash(transcript_path)
                    transcript_observed_at = parsed_at(transcript_row.get("observed_at"))
                    transcript_raw_id = connection.execute(
                        """
                        INSERT INTO raw_object (
                            run_id, job_id, source_id, platform, native_object_type,
                            native_object_id, payload_uri, payload_json, sha256,
                            captured_at, retention_class, redaction_state
                        ) VALUES (%s, %s, %s, 'youtube', 'subtitle', %s, %s,
                                  NULL, %s, %s, 'restricted', 'unreviewed')
                        ON CONFLICT (platform, native_object_type, native_object_id, captured_at)
                        DO UPDATE SET payload_uri = EXCLUDED.payload_uri
                        RETURNING raw_object_id
                        """,
                        (run_id, jobs["transcript"], source_id,
                         f"{video_id}:{transcript_path.name}", transcript_uri,
                         transcript_hash, transcript_observed_at),
                    ).fetchone()[0]
                    existing = connection.execute(
                        """
                        SELECT transcript_id FROM transcript
                        WHERE content_id = %s AND source_kind = 'native_subtitle'
                          AND language_code IS NOT DISTINCT FROM %s
                          AND transcript_sha256 = %s
                        """,
                        (content_id, transcript_row.get("language"), transcript_hash),
                    ).fetchone()
                    transcript_id = existing[0] if existing else connection.execute(
                        """
                        INSERT INTO transcript (
                            content_id, source_kind, language_code, model_name,
                            model_version, quality_state, transcript_uri, transcript_sha256
                        ) VALUES (%s, 'native_subtitle', %s, 'youtube-native', NULL,
                                  'review', %s, %s)
                        RETURNING transcript_id
                        """,
                        (content_id, transcript_row.get("language"), transcript_uri, transcript_hash),
                    ).fetchone()[0]
                    segment_id = None
                    if not existing and transcript_row.get("text"):
                        segment_id = connection.execute(
                            """
                            INSERT INTO transcript_segment (
                                transcript_id, segment_index, start_ms, end_ms,
                                text_body, confidence, evidence_state
                            ) VALUES (%s, 0, 0, %s, %s, NULL, 'observed')
                            RETURNING transcript_segment_id
                            """,
                            (transcript_id,
                             round((observation.get("duration_seconds") or 0) * 1000),
                             transcript_row["text"]),
                        ).fetchone()[0]
                    elif existing:
                        segment = connection.execute(
                            "SELECT transcript_segment_id FROM transcript_segment WHERE transcript_id = %s AND segment_index = 0",
                            (transcript_id,),
                        ).fetchone()
                        segment_id = segment[0] if segment else None
                    if segment_id and not connection.execute(
                        "SELECT 1 FROM evidence_record WHERE run_id = %s AND transcript_segment_id = %s",
                        (run_id, segment_id),
                    ).fetchone():
                        connection.execute(
                            """
                            INSERT INTO evidence_record (
                                run_id, source_id, raw_object_id, transcript_segment_id,
                                evidence_class, locator, statement, confidence
                            ) VALUES (%s, %s, %s, %s, 'public_observation', %s,
                                      'Public native or automatic subtitle artifact retained for local analysis.', 1.0)
                            """,
                            (run_id, source_id, transcript_raw_id, segment_id, transcript_uri),
                        )
                    counts["transcripts"] += 1

                if not connection.execute(
                    "SELECT 1 FROM rights_decision WHERE run_id = %s AND content_id = %s AND allowed_use = 'metadata_only'",
                    (run_id, content_id),
                ).fetchone():
                    connection.execute(
                        """
                        INSERT INTO rights_decision (
                            run_id, source_id, content_id, allowed_use, decision, basis, reviewer
                        ) VALUES (%s, %s, %s, 'metadata_only', 'pass',
                                  'Public metadata/comment/subtitle retained locally; no source-media reuse authorized.',
                                  'codex-integrator')
                        """,
                        (run_id, source_id, content_id),
                    )
                if not connection.execute(
                    "SELECT 1 FROM evidence_record WHERE run_id = %s AND raw_object_id = %s",
                    (run_id, raw_object_id),
                ).fetchone():
                    connection.execute(
                        """
                        INSERT INTO evidence_record (
                            run_id, source_id, raw_object_id, evidence_class,
                            locator, statement, confidence
                        ) VALUES (%s, %s, %s, 'public_observation', %s,
                                  'Bounded public YouTube metadata observation captured through yt-dlp.', 1.0)
                        """,
                        (run_id, source_id, raw_object_id, raw_uri),
                    )

            totals = connection.execute(
                """
                SELECT
                    count(DISTINCT platform_account.account_id),
                    count(DISTINCT content_item.content_id),
                    count(DISTINCT metric_snapshot.metric_snapshot_id)
                FROM content_item
                JOIN platform_account ON platform_account.account_id = content_item.account_id
                LEFT JOIN metric_snapshot ON metric_snapshot.content_id = content_item.content_id
                WHERE content_item.platform = 'youtube'
                """
            ).fetchone()
            for category, target, admitted, completed in (
                ("accounts", 10000, totals[0], totals[0]),
                ("posts", 50000, totals[1], totals[1]),
                ("stats", 50000, totals[1], totals[1]),
                ("comments", 1000, len(comments), len(comments)),
                ("transcripts", 1000, len(transcripts), len(transcripts)),
            ):
                connection.execute(
                    """
                    INSERT INTO analysis_progress (
                        run_id, platform, category, target_count, eligible_count,
                        admitted_count, completed_count, reviewed_count
                    ) VALUES (%s, 'youtube', %s, %s, %s, %s, %s, 0)
                    ON CONFLICT (run_id, platform, category) DO UPDATE
                    SET target_count = EXCLUDED.target_count,
                        eligible_count = EXCLUDED.eligible_count,
                        admitted_count = EXCLUDED.admitted_count,
                        completed_count = EXCLUDED.completed_count,
                        last_updated_at = now()
                    """,
                    (run_id, category, target, admitted, admitted, completed),
                )

    print(json.dumps({
        "run_key": RUN_KEY,
        "observations_loaded": counts["observations"],
        "comment_rows_seen": counts["comments"],
        "transcript_rows_seen": counts["transcripts"],
        "author_storage": "deterministic_pseudonym",
        "qualification_promotions": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
