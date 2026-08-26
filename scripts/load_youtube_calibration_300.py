#!/usr/bin/env python3
"""Idempotently load the approved 300-account YouTube calibration into PostgreSQL."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb


DSN = "host=127.0.0.1 port=55432 dbname=north_hux"


def jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def stamp(value: str | None) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else datetime.now(UTC)


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def path_from_pointer(run_dir: Path, pointer: str | None) -> Path | None:
    if not pointer:
        return None
    path = (run_dir / pointer).resolve()
    if not path.is_relative_to(run_dir.resolve()) or not path.is_file():
        raise ValueError(f"invalid evidence pointer: {pointer}")
    return path


def job(connection: psycopg.Connection, run_id: int, adapter_id: int, kind: str) -> int:
    row = connection.execute(
        """SELECT job_id FROM collection_job WHERE run_id=%s AND adapter_id=%s
           AND platform='youtube' AND job_type=%s AND target_stratum='qualified-300-videos-900'
           ORDER BY job_id LIMIT 1""", (run_id, adapter_id, kind),
    ).fetchone()
    if row:
        return row[0]
    return connection.execute(
        """INSERT INTO collection_job
           (run_id,adapter_id,platform,job_type,target_stratum,status,cursor_state,started_at,ended_at)
           VALUES (%s,%s,'youtube',%s,'qualified-300-videos-900','succeeded','{}'::jsonb,now(),now())
           RETURNING job_id""", (run_id, adapter_id, kind),
    ).fetchone()[0]


def source(connection: psycopg.Connection, run_id: int, source_type: str, native_id: str,
           url: str, role: str, rights: str) -> int:
    return connection.execute(
        """INSERT INTO source_registry
           (run_id,platform,source_type,native_id,canonical_url,source_role,discovery_route,rights_state,last_seen_at)
           VALUES (%s,'youtube',%s,%s,%s,%s,'official-api-plus-public-subtitles',%s,now())
           ON CONFLICT (platform,source_type,native_id) DO UPDATE SET last_seen_at=EXCLUDED.last_seen_at
           RETURNING source_id""", (run_id, source_type, native_id, url, role, rights),
    ).fetchone()[0]


def raw_object(connection: psycopg.Connection, run_id: int, job_id: int, source_id: int,
               object_type: str, native_id: str, pointer: str | None, sha: str,
               captured_at: datetime, payload: dict[str, Any], retention: str = "metadata") -> int:
    return connection.execute(
        """INSERT INTO raw_object
           (run_id,job_id,source_id,platform,native_object_type,native_object_id,payload_uri,
            payload_json,sha256,captured_at,retention_class,redaction_state)
           VALUES (%s,%s,%s,'youtube',%s,%s,%s,%s,%s,%s,%s,'approved')
           ON CONFLICT (platform,native_object_type,native_object_id,captured_at)
           DO UPDATE SET payload_uri=EXCLUDED.payload_uri RETURNING raw_object_id""",
        (run_id, job_id, source_id, object_type, native_id, pointer, Jsonb(payload), sha,
         captured_at, retention),
    ).fetchone()[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--dsn", default=DSN)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    run_key = run_dir.name
    accounts = jsonl(run_dir / "derived" / "qualified-accounts.jsonl")
    channels = {row["native_channel_id"]: row for row in jsonl(run_dir / "derived" / "channel-snapshots.jsonl")}
    videos = jsonl(run_dir / "derived" / "analyzed-content-cohort.jsonl")
    analyses = {row["native_video_id"]: row for row in jsonl(run_dir / "derived" / "video-analysis.jsonl")}
    account_analyses = {row["native_channel_id"]: row for row in jsonl(run_dir / "derived" / "account-analysis.jsonl")}
    relevance_reviews = jsonl(run_dir / "derived" / "independent-relevance-review.jsonl")
    comments = jsonl(run_dir / "derived" / "comments.jsonl")
    comment_gaps = jsonl(run_dir / "derived" / "comment-gaps.jsonl")
    comment_coverage = {row["native_video_id"]: row for row in jsonl(run_dir / "derived" / "comment-coverage.jsonl")}
    request_receipts = jsonl(run_dir / "ledgers" / "youtube-api-requests.jsonl")
    comment_receipts_by_uri = {
        row["raw_uri"]: row for row in request_receipts
        if row.get("operation") == "commentThreads.list" and row.get("status") == "success" and row.get("raw_uri")
    }
    media = {row["native_video_id"]: row for row in jsonl(run_dir / "derived" / "media-assets.jsonl")}
    frames_by_video: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in jsonl(run_dir / "derived" / "frame-artifacts.jsonl"):
        frames_by_video[row["native_video_id"]].append(row)
    transcripts = {}
    for path in sorted((run_dir / "normalized" / "transcripts").glob("*.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        transcripts[item["native_video_id"]] = item
    if len(accounts) != 300 or len(videos) != 900 or len(analyses) != 900:
        raise ValueError("database load requires complete exact 300-account/900-video analysis")

    comments_by_video: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in comments:
        comments_by_video[row["native_video_id"]].append(row)
    counts: Counter[str] = Counter()
    with psycopg.connect(args.dsn) as connection, connection.transaction():
        connection.execute("SET search_path=north_hux,public")
        run_id = connection.execute(
            """INSERT INTO research_run
               (run_key,status,scope_json,admission_receipt_uri,taxonomy_version,owner_gate,started_at)
               VALUES (%s,'calibration',%s,%s,'north-hux-youtube-taxonomy-v1',
                       'owner_approved_public_youtube_300_900',now())
               ON CONFLICT (run_key) DO UPDATE SET status=EXCLUDED.status,scope_json=EXCLUDED.scope_json
               RETURNING run_id""",
            (run_key, Jsonb({"platform": "youtube", "qualified_accounts": 300, "videos": 900,
                             "comments": "bounded first relevance page", "local_media_top_references": 100}),
             f"runs/{run_key}/admission-receipt.json"),
        ).fetchone()[0]
        adapter_id = connection.execute(
            """INSERT INTO adapter
               (platform,adapter_name,adapter_version,route_kind,approval_state,terms_uri)
               VALUES ('youtube','official-api-public-evidence','v1',
                       'official_metadata_comments_plus_public_subtitles_media','approved',
                       'https://developers.google.com/youtube/terms/developer-policies')
               ON CONFLICT (platform,adapter_name,adapter_version) DO UPDATE
               SET approval_state=EXCLUDED.approval_state RETURNING adapter_id"""
        ).fetchone()[0]
        jobs = {kind: job(connection, run_id, adapter_id, kind) for kind in
                ("account", "content", "metrics", "comments", "transcript", "media", "frames", "export")}
        metric_ids = {}
        for native, canonical, visibility in (
            ("subscriberCount", "followers", "public"), ("viewCount", "views", "public"),
            ("likeCount", "likes", "public"), ("commentCount", "comments", "public"),
            ("shareCount", "shares", "public"), ("repostCount", "reposts", "public"),
            ("sendCount", "sends", "public"), ("saveCount", "saves", "public"),
        ):
            metric_ids[canonical] = connection.execute(
                """INSERT INTO metric_definition
                   (platform,native_name,canonical_name,visibility_class,metric_definition_version,unit,denominator,notes)
                   VALUES ('youtube',%s,%s,%s,'youtube-data-api-v3-2026-08-25','count',
                           CASE WHEN %s='followers' THEN 'account' ELSE 'content_item' END,
                           'Null with not_exposed means unavailable through the approved public route.')
                   ON CONFLICT (platform,native_name,metric_definition_version) DO UPDATE SET notes=EXCLUDED.notes
                   RETURNING metric_definition_id""", (native, canonical, visibility, canonical),
            ).fetchone()[0]
        taxonomy_id = connection.execute(
            """INSERT INTO taxonomy_version (taxonomy_key,version,definition_json)
               VALUES ('north-hux-youtube-content','v1',%s)
               ON CONFLICT (taxonomy_key,version) DO UPDATE SET definition_json=EXCLUDED.definition_json
               RETURNING taxonomy_version_id""",
            (Jsonb({"dimensions": ["primary_topic", "video_type", "hook_type", "storytelling_style", "cta_type",
                                    "independent_relevance", "reviewer_language_fit"],
                    "method": "deterministic lexical v1 plus independent Sol relevance review"}),),
        ).fetchone()[0]

        account_ids: dict[str, int] = {}
        for account in accounts:
            channel_id = account["native_channel_id"]
            snap = channels[channel_id]
            source_id = source(connection, run_id, "account", channel_id, account["canonical_url"], "direct", "metadata_only")
            raw_path = path_from_pointer(run_dir, snap.get("raw_uri"))
            account_raw_id = raw_object(connection, run_id, jobs["account"], source_id, "channel_snapshot",
                                        channel_id, snap.get("raw_uri"), snap["raw_sha256"], stamp(snap.get("captured_at")), snap)
            entity_id = connection.execute(
                """INSERT INTO creator_entity (entity_key,entity_kind,display_name)
                   VALUES (%s,'unknown',%s) ON CONFLICT (entity_key) DO UPDATE
                   SET display_name=EXCLUDED.display_name RETURNING creator_entity_id""",
                (f"youtube:{channel_id}", account.get("title")),
            ).fetchone()[0]
            account_id = connection.execute(
                """INSERT INTO platform_account
                   (creator_entity_id,source_id,platform,native_account_id,handle,canonical_url,account_type,
                    primary_archetype,language_code,region_code,region_evidence_state,size_band,relevance_class,qualification_state)
                   VALUES (%s,%s,'youtube',%s,%s,%s,'creator_or_publisher','mixed','en',%s,
                           CASE WHEN %s::text IS NULL THEN 'unknown' ELSE 'self_declared' END,%s,'direct','qualified')
                   ON CONFLICT (platform,native_account_id) DO UPDATE SET qualification_state='qualified',
                    relevance_class='direct',region_code=EXCLUDED.region_code,source_id=EXCLUDED.source_id
                   RETURNING account_id""",
                (entity_id, source_id, channel_id, account.get("title"), account["canonical_url"],
                 account.get("country"), account.get("country"),
                 "large" if (account.get("subscriber_count") or 0) >= 100000 else
                 "mid" if (account.get("subscriber_count") or 0) >= 10000 else "small"),
            ).fetchone()[0]
            account_ids[channel_id] = account_id
            observed_at = stamp(snap.get("captured_at"))
            connection.execute(
                """INSERT INTO account_snapshot
                   (account_id,raw_object_id,observed_at,follower_count,content_count,bio_text,public_fields_state)
                   VALUES (%s,%s,%s,%s,%s,%s,'observed') ON CONFLICT DO NOTHING""",
                (account_id, account_raw_id, observed_at, account.get("subscriber_count"),
                 int(snap.get("video_count") or 0), account.get("description")),
            )
            connection.execute(
                """INSERT INTO metric_snapshot
                   (account_id,metric_definition_id,raw_object_id,observed_at,metric_value,availability_state,is_estimated)
                   SELECT %s,%s,%s,%s,%s,'observed',false WHERE NOT EXISTS
                   (SELECT 1 FROM metric_snapshot WHERE account_id=%s AND metric_definition_id=%s AND observed_at=%s)""",
                (account_id, metric_ids["followers"], account_raw_id, observed_at, account.get("subscriber_count"),
                 account_id, metric_ids["followers"], observed_at),
            )
            account_analysis = account_analyses[channel_id]
            for dimension in ("dominant_topic", "dominant_video_type"):
                connection.execute(
                    """INSERT INTO classification
                       (taxonomy_version_id,account_id,dimension,label,epistemic_state,method,confidence,evidence_locator)
                       SELECT %s,%s,%s,%s,'derived','deterministic_lexical_v1',0.65,%s WHERE NOT EXISTS
                       (SELECT 1 FROM classification WHERE taxonomy_version_id=%s AND account_id=%s AND dimension=%s)""",
                    (taxonomy_id, account_id, dimension, account_analysis[dimension],
                     f"runs/{run_key}/derived/account-analysis.jsonl", taxonomy_id, account_id, dimension),
                )
                connection.execute(
                    """UPDATE classification SET label=%s,epistemic_state='derived',
                       method='deterministic_lexical_v1',confidence=0.65,evidence_locator=%s
                       WHERE taxonomy_version_id=%s AND account_id=%s AND dimension=%s""",
                    (account_analysis[dimension], f"runs/{run_key}/derived/account-analysis.jsonl",
                     taxonomy_id, account_id, dimension),
                )
            counts["accounts"] += 1

        content_ids: dict[str, int] = {}
        raw_ids: dict[str, int] = {}
        comment_raw_ids: dict[str, int] = {}
        for video in videos:
            video_id = video["native_video_id"]
            analysis = analyses[video_id]
            source_id = source(connection, run_id, "content", video_id, video["canonical_url"], "direct",
                               "local_media_allowed" if video_id in media else "metadata_only")
            raw_id = raw_object(connection, run_id, jobs["content"], source_id, "video_snapshot", video_id,
                                video.get("raw_uri"), video["raw_sha256"], stamp(video.get("captured_at")), video)
            raw_ids[video_id] = raw_id
            content_id = connection.execute(
                """INSERT INTO content_item
                   (account_id,source_id,platform,native_content_id,canonical_url,content_kind,format_evidence_state,
                    title,caption,publish_at,duration_ms,language_code,rights_state)
                   VALUES (%s,%s,'youtube',%s,%s,%s,%s,%s,%s,%s,%s,'en',%s)
                   ON CONFLICT (platform,native_content_id) DO UPDATE SET title=EXCLUDED.title,caption=EXCLUDED.caption,
                    duration_ms=EXCLUDED.duration_ms,source_id=EXCLUDED.source_id RETURNING content_id""",
                (account_ids[video["native_channel_id"]], source_id, video_id, video["canonical_url"],
                 "short" if video.get("native_short_proved") else "unknown",
                 "platform_declared" if video.get("native_short_proved") else "inferred",
                 video.get("title"), video.get("description"), stamp(video.get("published_at")),
                 round((video.get("duration_seconds") or 0) * 1000),
                 "local_reference_only" if video_id in media else "metadata_only"),
            ).fetchone()[0]
            content_ids[video_id] = content_id
            observed_at = stamp(video.get("captured_at"))
            for canonical, value in (("views", video.get("view_count")), ("likes", video.get("like_count")),
                                     ("comments", video.get("comment_count")), ("shares", None),
                                     ("reposts", None), ("sends", None), ("saves", None)):
                state = "observed" if value is not None else "not_exposed"
                connection.execute(
                    """INSERT INTO metric_snapshot
                       (content_id,metric_definition_id,raw_object_id,observed_at,metric_value,availability_state,is_estimated)
                       SELECT %s,%s,%s,%s,%s,%s,false WHERE NOT EXISTS
                       (SELECT 1 FROM metric_snapshot WHERE content_id=%s AND metric_definition_id=%s AND observed_at=%s)""",
                    (content_id, metric_ids[canonical], raw_id, observed_at, value, state,
                     content_id, metric_ids[canonical], observed_at),
                )
            cov = comment_coverage.get(video_id, {})
            comment_pointer = cov.get("raw_uri")
            if comment_pointer:
                comment_path = path_from_pointer(run_dir, comment_pointer)
                receipt = comment_receipts_by_uri.get(comment_pointer, {})
                comment_sha = receipt.get("raw_sha256") or (file_sha(comment_path) if comment_path else None)
                if comment_path and comment_sha:
                    comment_raw_ids[video_id] = raw_object(
                        connection, run_id, jobs["comments"], source_id, "comment_page", video_id,
                        comment_pointer, comment_sha, stamp(receipt.get("captured_at")),
                        {"coverage": cov, "request_fingerprint": receipt.get("request_fingerprint")},
                        retention="restricted",
                    )
            for interaction in ("comment", "like", "share", "repost", "send", "save"):
                reported = video.get("comment_count") if interaction == "comment" else video.get("like_count") if interaction == "like" else None
                retrieved = cov.get("retrieved_count", 0) if interaction == "comment" else 0
                complete = bool(cov.get("pagination_complete")) if interaction == "comment" else False
                gap = cov.get("gap_reason") if interaction == "comment" else "actor_rows_not_exposed_by_public_route"
                connection.execute(
                    """INSERT INTO interaction_coverage
                       (content_id,interaction_type,observed_at,reported_count,retrieved_count,pagination_complete,
                        sampling_method,endpoint_limit,gap_reason,raw_object_id)
                       SELECT %s,%s,%s,%s,%s,%s,%s,%s,%s,%s WHERE NOT EXISTS
                       (SELECT 1 FROM interaction_coverage WHERE content_id=%s AND interaction_type=%s AND observed_at=%s)""",
                    (content_id, interaction, observed_at, reported, retrieved, complete,
                     cov.get("sampling_method") if interaction == "comment" else "public aggregate count only",
                     "maxResults=20 first page" if interaction == "comment" else "not exposed", gap,
                     comment_raw_ids.get(video_id, raw_id) if interaction == "comment" else raw_id,
                     content_id, interaction, observed_at),
                )
                if interaction == "comment" and video_id in comment_raw_ids:
                    connection.execute(
                        """UPDATE interaction_coverage SET raw_object_id=%s
                           WHERE content_id=%s AND interaction_type='comment' AND observed_at=%s""",
                        (comment_raw_ids[video_id], content_id, observed_at),
                    )
            for dimension in ("primary_topic", "video_type", "hook_type", "storytelling_style", "cta_type"):
                connection.execute(
                    """INSERT INTO classification
                       (taxonomy_version_id,content_id,dimension,label,epistemic_state,method,confidence,evidence_locator)
                       SELECT %s,%s,%s,%s,'derived','deterministic_lexical_v1',0.65,%s WHERE NOT EXISTS
                       (SELECT 1 FROM classification WHERE taxonomy_version_id=%s AND content_id=%s AND dimension=%s)""",
                    (taxonomy_id, content_id, dimension, analysis[dimension],
                     f"runs/{run_key}/derived/video-analysis.jsonl#{video_id}", taxonomy_id, content_id, dimension),
                )
                connection.execute(
                    """UPDATE classification SET label=%s,epistemic_state='derived',
                       method='deterministic_lexical_v1',confidence=0.65,evidence_locator=%s
                       WHERE taxonomy_version_id=%s AND content_id=%s AND dimension=%s""",
                    (analysis[dimension], f"runs/{run_key}/derived/video-analysis.jsonl#{video_id}",
                     taxonomy_id, content_id, dimension),
                )
            counts["content"] += 1

        for review in relevance_reviews:
            content_id = content_ids[review["native_video_id"]]
            for dimension, review_label in (
                ("independent_relevance", review["review_label"]),
                ("reviewer_language_fit", review["language_fit"]),
            ):
                locator = f"runs/{run_key}/derived/independent-relevance-review.jsonl#{review['native_video_id']}"
                connection.execute(
                    """INSERT INTO classification
                       (taxonomy_version_id,content_id,dimension,label,epistemic_state,method,confidence,evidence_locator)
                       SELECT %s,%s,%s,%s,'classified','independent_sol_review',0.90,%s WHERE NOT EXISTS
                       (SELECT 1 FROM classification WHERE taxonomy_version_id=%s AND content_id=%s AND dimension=%s)""",
                    (taxonomy_id, content_id, dimension, review_label, locator,
                     taxonomy_id, content_id, dimension),
                )
                connection.execute(
                    """UPDATE classification SET label=%s,epistemic_state='classified',
                       method='independent_sol_review',confidence=0.90,evidence_locator=%s
                       WHERE taxonomy_version_id=%s AND content_id=%s AND dimension=%s""",
                    (review_label, locator, taxonomy_id, content_id, dimension),
                )
            counts["relevance_reviews"] += 1

        for row in comments:
            content_id = content_ids[row["native_video_id"]]
            connection.execute(
                """INSERT INTO comment
                   (content_id,native_comment_id,native_parent_comment_id,text_body,author_pseudonym,created_at,like_count,raw_object_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (content_id,native_comment_id) DO UPDATE SET
                    raw_object_id=EXCLUDED.raw_object_id,text_body=EXCLUDED.text_body,
                    like_count=EXCLUDED.like_count""",
                (content_id, row["native_comment_id"], row.get("native_parent_comment_id"), row.get("text"),
                 row.get("author_pseudonym"), stamp(row.get("published_at")), row.get("like_count"),
                 comment_raw_ids.get(row["native_video_id"], raw_ids[row["native_video_id"]])),
            )
            counts["comments"] += 1

        for video_id, row in transcripts.items():
            if row.get("availability") != "observed" or video_id not in content_ids:
                counts["transcript_gaps"] += 1
                continue
            db_source_kind = "native_caption" if row["source_kind"] == "native_caption_source_unresolved" else row["source_kind"]
            raw_existing = connection.execute(
                """SELECT transcript_id FROM transcript WHERE content_id=%s AND source_kind=%s
                   AND transcript_sha256=%s AND model_name IS NULL ORDER BY transcript_id LIMIT 1""",
                (content_ids[video_id], db_source_kind, row.get("source_sha256")),
            ).fetchone()
            raw_transcript_id = raw_existing[0] if raw_existing else connection.execute(
                """INSERT INTO transcript
                   (content_id,source_kind,language_code,quality_state,transcript_uri,transcript_sha256)
                   VALUES (%s,%s,%s,%s,%s,%s) RETURNING transcript_id""",
                (content_ids[video_id], db_source_kind, row.get("language"), row.get("quality_state", "review"),
                 row.get("source_uri"), row.get("source_sha256")),
            ).fetchone()[0]
            for index, segment in enumerate(row.get("segments") or []):
                connection.execute(
                    """INSERT INTO transcript_segment
                       (transcript_id,segment_index,start_ms,end_ms,text_body,evidence_state)
                       VALUES (%s,%s,%s,%s,%s,'observed')
                       ON CONFLICT (transcript_id,segment_index) DO UPDATE SET
                        start_ms=EXCLUDED.start_ms,end_ms=EXCLUDED.end_ms,text_body=EXCLUDED.text_body""",
                    (raw_transcript_id, index, segment["start_ms"], segment["end_ms"], segment["text"]),
                )
            speech_text = row.get("speech_text") or row.get("text") or ""
            speech_sha = hashlib.sha256(speech_text.encode("utf-8")).hexdigest()
            speech_existing = connection.execute(
                """SELECT transcript_id FROM transcript WHERE content_id=%s AND source_kind=%s
                   AND model_name='north_hux_caption_deroll' AND model_version='longest_exact_token_overlap_v1'
                   ORDER BY transcript_id LIMIT 1""",
                (content_ids[video_id], db_source_kind),
            ).fetchone()
            speech_transcript_id = speech_existing[0] if speech_existing else connection.execute(
                """INSERT INTO transcript
                   (content_id,source_kind,language_code,model_name,model_version,quality_state,
                    transcript_uri,transcript_sha256)
                   VALUES (%s,%s,%s,'north_hux_caption_deroll','longest_exact_token_overlap_v1',%s,%s,%s)
                   RETURNING transcript_id""",
                (content_ids[video_id], db_source_kind, row.get("language"), row.get("quality_state", "review"),
                 f"normalized/transcripts/{video_id}.json#speech_text", speech_sha),
            ).fetchone()[0]
            connection.execute(
                """UPDATE transcript SET transcript_sha256=%s,quality_state=%s
                   WHERE transcript_id=%s""",
                (speech_sha, row.get("quality_state", "review"), speech_transcript_id),
            )
            speech_segments = row.get("speech_segments") or row.get("segments") or []
            connection.execute(
                "DELETE FROM transcript_segment WHERE transcript_id=%s AND segment_index >= %s",
                (speech_transcript_id, len(speech_segments)),
            )
            for index, segment in enumerate(speech_segments):
                connection.execute(
                    """INSERT INTO transcript_segment
                       (transcript_id,segment_index,start_ms,end_ms,text_body,evidence_state)
                       VALUES (%s,%s,%s,%s,%s,'derived')
                       ON CONFLICT (transcript_id,segment_index) DO UPDATE SET
                        start_ms=EXCLUDED.start_ms,end_ms=EXCLUDED.end_ms,text_body=EXCLUDED.text_body,
                        evidence_state=EXCLUDED.evidence_state""",
                    (speech_transcript_id, index, segment["start_ms"], segment["end_ms"], segment["text"]),
                )
                counts["transcript_segments"] += 1
            counts["transcripts"] += 1

        for video_id, row in media.items():
            asset_id = connection.execute(
                """INSERT INTO media_asset
                   (content_id,asset_kind,asset_uri,sha256,byte_size,duration_ms,width,height,rights_state,retention_until)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (content_id,asset_kind,sha256) DO UPDATE SET retention_until=EXCLUDED.retention_until
                   RETURNING media_asset_id""",
                (content_ids[video_id], row.get("asset_kind", "video"), row["asset_uri"], row["sha256"], row.get("byte_size"),
                 row.get("duration_ms"), row.get("width"), row.get("height"), row["rights_state"],
                 stamp(row.get("retention_until"))),
            ).fetchone()[0]
            for frame in frames_by_video[video_id]:
                connection.execute(
                    """INSERT INTO frame_artifact
                       (media_asset_id,frame_index,timestamp_ms,frame_uri,sha256,public_display_allowed)
                       VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (media_asset_id,frame_index) DO NOTHING""",
                    (asset_id, frame["frame_index"], frame["timestamp_ms"], frame["frame_uri"],
                     frame["sha256"], frame.get("public_display_allowed", False)),
                )
                counts["frames"] += 1
            counts["media"] += 1

        progress = {
            "accounts": (300, 300, 300, 300, 300, 0, 0),
            "posts": (900, 900, 900, 900, 900, 0, 0),
            "stats": (900, 900, 900, 900, 900, 0, 0),
            "comments": (900, 900, 900, 900-len(comment_gaps), len({row['native_video_id'] for row in comments}), len(comment_gaps), 0),
            "transcripts": (900, 900, 900, counts["transcripts"], counts["transcripts"], counts["transcript_gaps"], 0),
            "frames": (100, 100, 100, counts["media"], counts["media"], 100-counts["media"], 0),
            "taxonomy": (900, 900, 900, 900, 900, 0, 0),
            "review": (250, 250, 250, len(relevance_reviews), len(relevance_reviews), 0, 0),
        }
        for category, values in progress.items():
            connection.execute(
                """INSERT INTO analysis_progress
                   (run_id,platform,category,target_count,eligible_count,admitted_count,completed_count,reviewed_count,failed_count,blocked_count)
                   VALUES (%s,'youtube',%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (run_id,platform,category) DO UPDATE SET
                    target_count=EXCLUDED.target_count,eligible_count=EXCLUDED.eligible_count,
                    admitted_count=EXCLUDED.admitted_count,completed_count=EXCLUDED.completed_count,
                    reviewed_count=EXCLUDED.reviewed_count,failed_count=EXCLUDED.failed_count,
                    blocked_count=EXCLUDED.blocked_count,last_updated_at=now()""",
                (run_id, category, *values),
            )
    print(json.dumps({"run_key": run_key, **counts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
