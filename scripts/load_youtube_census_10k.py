#!/usr/bin/env python3
"""Idempotently load the 10K YouTube broad screen and Studio campaign into PostgreSQL.

The loader preserves the broad-screen/qualified distinction. Transcript speech
segments and frame pointers are stored when observed; missing manifests are not
invented. Re-running the loader only adds newly observed immutable artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DSN = "host=127.0.0.1 port=55432 dbname=north_hux"
ROW_BATCH_SIZE = 250
LOCK_BATCH_SIZE = 16
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.youtube_evidence_10k import assert_run_mutable, frame_artifact_valid, stage_lock, transcript_artifact_valid  # noqa: E402
from scripts.youtube_video_census_10k import creator_cap_config_sha256, validate_pinned_creator_cap  # noqa: E402


def jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def stamp(value: str | None) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else datetime.now(UTC)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row_sha(row: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def commit_if_due(connection: psycopg.Connection, index: int, batch_size: int) -> None:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    if index % batch_size == 0:
        connection.commit()


def transcript_semantic_sha(payload: dict[str, Any]) -> str:
    semantic = {
        "native_video_id": payload.get("native_video_id"),
        "source_kind": payload.get("source_kind"),
        "language": payload.get("language"),
        "normalization_method": payload.get("normalization_method"),
        "source_sha256": payload.get("source_sha256"),
        "speech_segments": payload.get("speech_segments") or payload.get("segments") or [],
    }
    return row_sha(semantic)


def artifact_id(kind: str, digest: str) -> str:
    return f"art-{kind}-{digest[:32]}"


def canonical_transcript_kind(value: str | None) -> str:
    if value in {"native_caption", "native_subtitle"}:
        return value
    if value in {"post_caption", "provider_transcript", "local_asr", "ocr"}:
        return value
    return "native_caption"


def get_or_create_transcript(
    connection: psycopg.Connection,
    *,
    content_id: int,
    payload: dict[str, Any],
    transcript_uri: str,
    transcript_sha256: str,
) -> int:
    lock_key = f"transcript:{content_id}:{transcript_sha256}"
    connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (lock_key,))
    existing = connection.execute(
        """SELECT transcript_id FROM transcript_identity
           WHERE content_id=%s AND transcript_sha256=%s""",
        (content_id, transcript_sha256),
    ).fetchone()
    if existing:
        return existing[0]
    existing = connection.execute(
        """SELECT transcript_id FROM transcript
           WHERE content_id=%s AND transcript_sha256=%s
           ORDER BY transcript_id LIMIT 1""",
        (content_id, transcript_sha256),
    ).fetchone()
    if existing:
        transcript_id = existing[0]
    else:
        transcript_id = connection.execute(
            """INSERT INTO transcript
               (content_id,source_kind,language_code,model_name,model_version,quality_state,
                transcript_uri,transcript_sha256)
               VALUES (%s,%s,%s,'public-subtitle-route',%s,'usable',%s,%s)
               RETURNING transcript_id""",
            (content_id, canonical_transcript_kind(payload.get("source_kind")), payload.get("language"),
             payload.get("normalization_method") or "v1", transcript_uri, transcript_sha256),
        ).fetchone()[0]
    connection.execute(
        """INSERT INTO transcript_identity (content_id,transcript_sha256,transcript_id)
           VALUES (%s,%s,%s) ON CONFLICT DO NOTHING""",
        (content_id, transcript_sha256, transcript_id),
    )
    return connection.execute(
        """SELECT transcript_id FROM transcript_identity
           WHERE content_id=%s AND transcript_sha256=%s""",
        (content_id, transcript_sha256),
    ).fetchone()[0]


def relative(path: Path) -> str:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f"artifact must stay inside project root: {resolved}")
    return resolved.relative_to(ROOT).as_posix()


def get_json_files(directory: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    result: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in sorted(directory.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        video_id = payload.get("native_video_id")
        if not video_id or video_id != path.stem:
            raise ValueError(f"evidence filename/payload identity mismatch: {path}")
        if video_id in result:
            raise ValueError(f"duplicate evidence identity: {video_id}")
        result[video_id] = (path, payload)
    return result


def validate_evidence_identity(
    cohort_ids: set[str],
    transcripts: dict[str, tuple[Path, dict[str, Any]]],
    frames: dict[str, tuple[Path, dict[str, Any]]],
    *,
    allow_partial: bool,
) -> None:
    transcript_ids = set(transcripts)
    frame_ids = set(frames)
    if transcript_ids - cohort_ids or frame_ids - cohort_ids:
        raise ValueError("evidence contains identities outside the frozen cohort")
    if not allow_partial and (transcript_ids != cohort_ids or frame_ids != cohort_ids):
        raise ValueError(
            "evidence identity sets incomplete: "
            f"transcripts={len(transcript_ids)}/{len(cohort_ids)}, "
            f"frames={len(frame_ids)}/{len(cohort_ids)}"
        )


def insert_artifact(connection: psycopg.Connection, *, run_id: int | None, content_id: int | None,
                    kind: str, schema_id: str, version: str, uri: str, digest: str,
                    epistemic: str, rights: str, maker: str, review: str,
                    public_safe: bool = False, source_hashes: list[str] | None = None,
                    tool_key: str = "content-engine", tool_version: str = "v1") -> str:
    key = artifact_id(kind.replace("_", "-"), digest)
    connection.execute(
        """INSERT INTO artifact
           (artifact_id,run_id,content_id,artifact_type,schema_id,schema_version,artifact_uri,
            artifact_sha256,source_hashes,tool_key,tool_version,epistemic_state,rights_state,
            maker_actor,review_state,public_safe)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
           ON CONFLICT DO NOTHING""",
        (key, run_id, content_id, kind, schema_id, version, uri, digest,
         Jsonb(source_hashes or []), tool_key, tool_version, epistemic, rights, maker, review, public_safe),
    )
    return key


def insert_edge(connection: psycopg.Connection, parent: str, child: str, edge: str, locator: str | None = None) -> None:
    connection.execute(
        """INSERT INTO artifact_edge (parent_artifact_id,child_artifact_id,edge_type,claim_locator)
           VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING""", (parent, child, edge, locator),
    )


def get_or_create_job(connection: psycopg.Connection, run_id: int, adapter_id: int, kind: str) -> int:
    connection.execute(
        """INSERT INTO collection_job
           (run_id,adapter_id,platform,job_type,target_stratum,status,cursor_state,started_at)
           VALUES (%s,%s,'youtube',%s,'10k-broad-screen-v1','running','{}'::jsonb,now())
           ON CONFLICT DO NOTHING""", (run_id, adapter_id, kind),
    )
    return connection.execute(
        """SELECT job_id FROM collection_job WHERE run_id=%s AND adapter_id=%s
           AND platform='youtube' AND job_type=%s AND target_stratum='10k-broad-screen-v1'
           ORDER BY job_id LIMIT 1""", (run_id, adapter_id, kind),
    ).fetchone()[0]


def source(connection: psycopg.Connection, run_id: int, source_type: str, native_id: str,
           url: str, role: str = "adjacent", rights: str = "metadata_only") -> int:
    connection.execute(
        """INSERT INTO source_registry
           (run_id,platform,source_type,native_id,canonical_url,source_role,discovery_route,rights_state,last_seen_at)
           VALUES (%s,'youtube',%s,%s,%s,%s,'official-api-public-evidence',%s,now())
           ON CONFLICT (platform,source_type,native_id) DO NOTHING""",
        (run_id, source_type, native_id, url, role, rights),
    )
    source_id = connection.execute(
        "SELECT source_id FROM source_registry WHERE platform='youtube' AND source_type=%s AND native_id=%s",
        (source_type, native_id),
    ).fetchone()[0]
    observe_source(connection, run_id, source_id, role, rights)
    return source_id


def observe_source(connection: psycopg.Connection, run_id: int, source_id: int, role: str, rights: str) -> None:
    connection.execute(
        """INSERT INTO run_source_observation
           (run_id,source_id,source_role,discovery_route,rights_state,observed_at)
           VALUES (%s,%s,%s,'official-api-public-evidence',%s,now())
           ON CONFLICT DO NOTHING""",
        (run_id, source_id, role, rights),
    )


def insert_artifact_attempt(
    connection: psycopg.Connection,
    *,
    run_id: int,
    content_id: int,
    stage: str,
    state: str,
    method: str,
    reason_code: str | None,
    artifact_uri: str,
    artifact_sha256: str,
    captured_at: datetime,
) -> int:
    lock_key = f"artifact-attempt:{run_id}:{content_id}:{stage}"
    connection.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (lock_key,))
    latest = connection.execute(
        """SELECT attempt_number,state,artifact_sha256 FROM artifact_attempt
           WHERE run_id=%s AND content_id=%s AND stage=%s
           ORDER BY attempt_number DESC LIMIT 1""",
        (run_id, content_id, stage),
    ).fetchone()
    if latest and latest[1] == state and latest[2] == artifact_sha256:
        return latest[0]
    attempt_number = (latest[0] + 1) if latest else 1
    connection.execute(
        """INSERT INTO artifact_attempt
           (run_id,content_id,stage,attempt_number,state,method,reason_code,artifact_uri,artifact_sha256,captured_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (run_id, content_id, stage, attempt_number, state, method, reason_code,
         artifact_uri, artifact_sha256, captured_at),
    )
    return attempt_number


def insert_analysis_exact(
    connection: psycopg.Connection,
    *,
    run_id: int,
    content_id: int,
    input_bundle_sha256: str,
    analysis_uri: str,
    analysis_sha256: str,
) -> int:
    previous = connection.execute(
        """SELECT content_analysis_artifact_id FROM content_analysis_artifact
           WHERE run_id=%s AND content_id=%s AND analyzer_key='youtube-census-lexical'
             AND analyzer_version='v2'
           ORDER BY content_analysis_artifact_id DESC LIMIT 1""",
        (run_id, content_id),
    ).fetchone()
    inserted = connection.execute(
        """INSERT INTO content_analysis_artifact
           (run_id,content_id,analyzer_key,analyzer_version,input_bundle_sha256,analysis_uri,
            analysis_sha256,epistemic_state,review_state,supersedes_analysis_id)
           VALUES (%s,%s,'youtube-census-lexical','v2',%s,%s,%s,'classified','passed_with_limitations',%s)
           ON CONFLICT DO NOTHING RETURNING content_analysis_artifact_id""",
        (run_id, content_id, input_bundle_sha256, analysis_uri, analysis_sha256, previous[0] if previous else None),
    ).fetchone()
    if inserted:
        return int(inserted[0])
    existing = connection.execute(
        """SELECT content_analysis_artifact_id,analysis_uri,analysis_sha256
           FROM content_analysis_artifact
           WHERE run_id=%s AND content_id=%s AND analyzer_key='youtube-census-lexical'
             AND analyzer_version='v2' AND input_bundle_sha256=%s""",
        (run_id, content_id, input_bundle_sha256),
    ).fetchone()
    if not existing:
        raise ValueError("analysis natural-key conflict belongs to a different run or identity")
    if existing[1] != analysis_uri or existing[2] != analysis_sha256:
        raise ValueError("analysis natural-key row conflicts with the exact analysis URI or hash")
    return int(existing[0])


def load_campaign(connection: psycopg.Connection, run_id: int, campaign_dir: Path, evidence_artifact: str) -> Counter:
    counts: Counter[str] = Counter()
    manifest_path = campaign_dir / "campaign-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_hash = sha(manifest_path)
    strategy_artifact = insert_artifact(
        connection, run_id=run_id, content_id=None, kind="strategy_release",
        schema_id=manifest["schema"], version="1", uri=relative(manifest_path), digest=manifest_hash,
        epistemic="planned", rights="original_plan", maker="codex-integrator",
        review="passed_with_limitations", public_safe=True,
        source_hashes=[manifest["evidence_summary_sha256"]], tool_key="build_north_hux_campaign_10", tool_version="v1",
    )
    insert_edge(connection, evidence_artifact, strategy_artifact, "derived_from")
    strategy_row = connection.execute(
        "SELECT strategy_release_id,version FROM strategy_release WHERE release_key=%s AND strategy_sha256=%s",
        (manifest["campaign_key"], manifest_hash),
    ).fetchone()
    if strategy_row:
        strategy_id, strategy_version = strategy_row
    else:
        previous = connection.execute(
            """SELECT strategy_release_id,version FROM strategy_release WHERE release_key=%s
               ORDER BY version DESC LIMIT 1""", (manifest["campaign_key"],),
        ).fetchone()
        strategy_version = (previous[1] + 1) if previous else 1
        strategy_id = connection.execute(
            """INSERT INTO strategy_release
               (run_id,release_key,version,audience_json,pillar_json,evidence_bundle_sha256,
                strategy_uri,strategy_sha256,state,maker,reviewer,review_verdict,supersedes_strategy_release_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'owner_review','codex-integrator',
                       'sol-strategic-review','pass_with_limitations',%s)
               RETURNING strategy_release_id""",
            (run_id, manifest["campaign_key"], strategy_version,
             Jsonb({"description": manifest["audience"]}),
             Jsonb({"position": manifest["market_position"]}), manifest["evidence_summary_sha256"],
             relative(manifest_path), manifest_hash, previous[0] if previous else None),
        ).fetchone()[0]
    for item in manifest["scripts"]:
        package_path = campaign_dir / item["package_uri"]
        package = json.loads(package_path.read_text(encoding="utf-8"))
        package_hash = sha(package_path)
        package_artifact = insert_artifact(
            connection, run_id=run_id, content_id=None, kind="script_package",
            schema_id=package["schema"], version="1", uri=relative(package_path), digest=package_hash,
            epistemic="planned", rights="original_plan", maker="codex-integrator",
            review="owner_review_pending", public_safe=True, source_hashes=[manifest_hash],
            tool_key="build_north_hux_campaign_10", tool_version="v1",
        )
        insert_edge(connection, strategy_artifact, package_artifact, "plans", f"script:{package['script_key']}")
        existing_script = connection.execute(
            """SELECT script_package_id,version FROM script_package
               WHERE script_key=%s AND package_sha256=%s AND strategy_release_id=%s""",
            (package["script_key"], package_hash, strategy_id),
        ).fetchone()
        if existing_script:
            script_id, script_version = existing_script
        else:
            previous_script = connection.execute(
                """SELECT script_package_id,version FROM script_package WHERE script_key=%s
                   ORDER BY version DESC LIMIT 1""", (package["script_key"],),
            ).fetchone()
            script_version = (previous_script[1] + 1) if previous_script else 1
            script_id = connection.execute(
                """INSERT INTO script_package
                   (strategy_release_id,script_key,version,sequence_position,creator_track,primary_platform,
                    target_duration_ms,schema_version,package_uri,package_sha256,candidate_set_sha256,
                    claim_state,owner_state,supersedes_script_package_id)
                   VALUES (%s,%s,%s,%s,%s,'youtube_shorts',%s,%s,%s,%s,%s,
                           'evidence_bound','owner_review_pending',%s)
                   RETURNING script_package_id""",
                (strategy_id, package["script_key"], script_version, package["sequence_position"],
                 package["creator_track"], package["target_duration_ms"], package["schema"],
                 relative(package_path), package_hash, manifest["evidence_summary_sha256"],
                 previous_script[0] if previous_script else None),
            ).fetchone()[0]
        shot_ids = []
        for shot in package["shots"]:
            connection.execute(
                """INSERT INTO shot_plan
                   (script_package_id,shot_index,start_ms,end_ms,capture_mode,evidence_role,narration,
                    on_screen_text,visual_spec_json,transition_json,audio_json,source_evidence_ids,
                    asset_requirement_json,generation_state,rights_state,acceptance_checks)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT DO NOTHING""",
                (script_id, shot["shot_index"], shot["start_ms"], shot["end_ms"], shot["capture_mode"],
                 shot["evidence_role"], shot.get("narration"), shot.get("on_screen_text"),
                 Jsonb(shot["visual_spec"]), Jsonb(shot["transition"]), Jsonb(shot["audio"]),
                 Jsonb(shot["source_evidence_ids"]), Jsonb(shot["asset_requirement"]),
                 shot["generation_state"], shot["rights_state"], Jsonb(shot["acceptance_checks"])),
            )
            shot_id = connection.execute(
                "SELECT shot_plan_id FROM shot_plan WHERE script_package_id=%s AND shot_index=%s",
                (script_id, shot["shot_index"]),
            ).fetchone()[0]
            shot_ids.append((shot_id, shot))
            frame_path = campaign_dir / shot["frame_uri"]
            frame_artifact = insert_artifact(
                connection, run_id=run_id, content_id=None, kind="planned_frame",
                schema_id="north-hux.frame-plan.svg", version="1", uri=relative(frame_path),
                digest=shot["frame_sha256"], epistemic="planned", rights=shot["rights_state"],
                maker="codex-integrator", review="owner_review_pending", public_safe=True,
                source_hashes=[package_hash], tool_key="build_north_hux_campaign_10", tool_version="v1",
            )
            insert_edge(connection, package_artifact, frame_artifact, "renders", f"shot:{shot['shot_index']}")
        edit_path = campaign_dir / item["edit_plan_uri"]
        edit_payload = json.loads(edit_path.read_text(encoding="utf-8"))
        edit_hash = sha(edit_path)
        connection.execute(
            """INSERT INTO studio_edit_plan
               (script_package_id,version,edl_uri,edl_sha256,timeline_json,provider_generation_state,
                creator_media_state,resolve_mutation_state,final_video_state,publication_state)
               VALUES (%s,1,%s,%s,%s,'blocked_approval','not_received','blocked_approval','not_run','blocked_approval')
               ON CONFLICT DO NOTHING""",
            (script_id, relative(edit_path), edit_hash, Jsonb(edit_payload["timeline"])),
        )
        connection.execute(
            """INSERT INTO edit_decision_list
               (script_package_id,version,edl_uri,edl_sha256,timeline_duration_ms,state)
               VALUES (%s,1,%s,%s,%s,'validated') ON CONFLICT DO NOTHING""",
            (script_id, relative(edit_path), edit_hash, package["target_duration_ms"]),
        )
        edl_id = connection.execute(
            "SELECT edit_decision_list_id FROM edit_decision_list WHERE script_package_id=%s AND version=1",
            (script_id,),
        ).fetchone()[0]
        for shot_id, shot in shot_ids:
            connection.execute(
                """INSERT INTO edl_segment
                   (edit_decision_list_id,shot_plan_id,segment_index,timeline_start_ms,timeline_end_ms,transition_json)
                   VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                (edl_id, shot_id, shot["shot_index"], shot["start_ms"], shot["end_ms"], Jsonb(shot["transition"])),
            )
        counts["scripts"] += 1
        counts["shots"] += len(package["shots"])
    return counts


def execute(args: argparse.Namespace, run_dir: Path) -> int:
    cohort_path = run_dir / "derived" / "video-cohort.jsonl"
    analysis_path = run_dir / "derived" / "video-analysis-10k.jsonl"
    summary_path = run_dir / "derived" / "analysis-summary-10k.json"
    cohort = jsonl(cohort_path)
    analysis_rows = jsonl(analysis_path)
    if len(analysis_rows) != 10000:
        raise ValueError(f"loader requires exactly 10,000 analysis rows, got {len(analysis_rows)}")
    analyses = {row["native_video_id"]: row for row in analysis_rows}
    if len(analyses) != len(analysis_rows):
        raise ValueError("analysis JSONL contains duplicate native_video_id rows")
    transcripts = get_json_files(run_dir / "normalized" / "transcripts")
    frames = get_json_files(run_dir / "normalized" / "frame-manifests")
    if len(cohort) != 10000 or len(analyses) != 10000:
        raise ValueError("loader requires exactly 10,000 cohort and analysis rows")
    cohort_ids = {row["native_video_id"] for row in cohort}
    if len(cohort_ids) != len(cohort):
        raise ValueError("cohort contains duplicate native_video_id values")
    creator_counts = Counter(row["native_channel_id"] for row in cohort)
    approved_cap = validate_pinned_creator_cap(run_dir)
    if max(creator_counts.values()) / len(cohort) > approved_cap:
        raise ValueError("cohort violates the approved maximum creator contribution")
    for _, (path, payload) in transcripts.items():
        if not transcript_artifact_valid(run_dir, path, payload):
            raise ValueError(f"invalid transcript pointer/hash chain: {path}")
    for _, (path, payload) in frames.items():
        if not frame_artifact_valid(run_dir, path, payload):
            raise ValueError(f"invalid frame pointer/hash chain: {path}")
    if set(analyses) != cohort_ids:
        raise ValueError("analysis identity set does not exactly match the frozen cohort")
    validate_evidence_identity(cohort_ids, transcripts, frames, allow_partial=args.allow_partial)
    counts: Counter[str] = Counter()
    with psycopg.connect(args.dsn) as connection:
        connection.execute("SET search_path=north_hux,public")
        # The session lock protects the full idempotent load across bounded
        # commits and conflicts with the freezer's transaction lock.
        connection.execute("SELECT pg_advisory_lock(hashtextextended(%s,0))", (f"terminal-freeze:{run_dir.name}",))
        assert_run_mutable(run_dir)
        connection.execute(
            """INSERT INTO research_run
               (run_key,status,scope_json,admission_receipt_uri,taxonomy_version,owner_gate,started_at)
               VALUES (%s,'scale',%s,%s,'north-hux-youtube-taxonomy-v2',
                       'owner_approved_public_youtube_10k',now())
               ON CONFLICT (run_key) DO NOTHING""",
            (run_dir.name, Jsonb({"platform": "youtube", "broad_screen_videos": 10000,
                                  "creator_cap": approved_cap,
                                  "creator_cap_config_sha256": creator_cap_config_sha256(),
                                  "strategic_denominator": 2949}),
             f"runs/{run_dir.name}/admission-receipt.json"),
        )
        run_id = connection.execute("SELECT run_id FROM research_run WHERE run_key=%s", (run_dir.name,)).fetchone()[0]
        connection.execute(
            """INSERT INTO adapter (platform,adapter_name,adapter_version,route_kind,approval_state,terms_uri)
               VALUES ('youtube','official-api-plus-public-evidence','v2',
                       'official_metadata_plus_public_subtitles_storyboards','approved',
                       'https://developers.google.com/youtube/terms/developer-policies')
               ON CONFLICT DO NOTHING"""
        )
        adapter_id = connection.execute(
            """SELECT adapter_id FROM adapter WHERE platform='youtube'
               AND adapter_name='official-api-plus-public-evidence' AND adapter_version='v2'"""
        ).fetchone()[0]
        jobs = {kind: get_or_create_job(connection, run_id, adapter_id, kind)
                for kind in ("account", "content", "metrics", "transcript", "media", "frames", "export")}
        metric_ids = {}
        for native, canonical in (("viewCount", "views"), ("likeCount", "likes"), ("commentCount", "comments")):
            connection.execute(
                """INSERT INTO metric_definition
                   (platform,native_name,canonical_name,visibility_class,metric_definition_version,unit,denominator,notes)
                   VALUES ('youtube',%s,%s,'public','youtube-data-api-v3-2026-08-26','count','content_item',
                           'Public point-in-time count; null means unavailable, not zero.')
                   ON CONFLICT DO NOTHING""", (native, canonical),
            )
            metric_ids[canonical] = connection.execute(
                """SELECT metric_definition_id FROM metric_definition
                   WHERE platform='youtube' AND native_name=%s AND metric_definition_version='youtube-data-api-v3-2026-08-26'""",
                (native,),
            ).fetchone()[0]
        evidence_summary_artifact = insert_artifact(
            connection, run_id=run_id, content_id=None, kind="analysis_summary",
            schema_id="north-hux.youtube-census-analysis-summary.v1", version="1",
            uri=relative(summary_path), digest=sha(summary_path), epistemic="derived",
            rights="aggregate_public_safe", maker="codex-integrator", review="passed_with_limitations",
            public_safe=True, source_hashes=[sha(cohort_path)], tool_key="analyze_youtube_census_10k", tool_version="v1",
        )
        account_ids: dict[str, int] = {}
        content_ids: dict[str, int] = {}
        metadata_artifacts: dict[str, str] = {}
        transcript_artifacts: dict[str, str] = {}
        frame_artifacts: dict[str, str] = {}
        for row_index, row in enumerate(cohort, 1):
            channel_id = row["native_channel_id"]
            if channel_id not in account_ids:
                channel_url = f"https://www.youtube.com/channel/{channel_id}"
                account_source = source(connection, run_id, "account", channel_id, channel_url)
                connection.execute(
                    """INSERT INTO creator_entity (entity_key,entity_kind,display_name)
                       VALUES (%s,'unknown',%s) ON CONFLICT DO NOTHING""",
                    (f"youtube:{channel_id}", channel_id),
                )
                entity_id = connection.execute(
                    "SELECT creator_entity_id FROM creator_entity WHERE entity_key=%s", (f"youtube:{channel_id}",),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO platform_account
                       (creator_entity_id,source_id,platform,native_account_id,handle,canonical_url,
                        primary_archetype,language_code,relevance_class,qualification_state)
                       VALUES (%s,%s,'youtube',%s,%s,%s,'unknown','en','unknown','candidate')
                       ON CONFLICT DO NOTHING""",
                    (entity_id, account_source, channel_id, channel_id, channel_url),
                )
                account_ids[channel_id] = connection.execute(
                    "SELECT account_id FROM platform_account WHERE platform='youtube' AND native_account_id=%s",
                    (channel_id,),
                ).fetchone()[0]
                counts["accounts"] += 1
            video_id = row["native_video_id"]
            content_source = source(connection, run_id, "content", video_id, row["canonical_url"],
                                    "direct" if row.get("analysis_eligible") else "adjacent",
                                    "local_media_allowed" if video_id in frames else "metadata_only")
            connection.execute(
                """INSERT INTO content_item
                   (account_id,source_id,platform,native_content_id,canonical_url,content_kind,
                    format_evidence_state,title,caption,publish_at,duration_ms,language_code,rights_state)
                   VALUES (%s,%s,'youtube',%s,%s,%s,%s,%s,%s,%s,%s,'en',%s)
                   ON CONFLICT DO NOTHING""",
                (account_ids[channel_id], content_source, video_id, row["canonical_url"],
                 "short" if row.get("native_short_proved") else "unknown",
                 "platform_declared" if row.get("native_short_proved") else "inferred",
                 row.get("title"), row.get("description"), stamp(row.get("published_at")),
                 int((row.get("duration_seconds") or 0) * 1000),
                 "local_reference_only" if video_id in frames else "metadata_only"),
            )
            content_id = connection.execute(
                "SELECT content_id FROM content_item WHERE platform='youtube' AND native_content_id=%s", (video_id,),
            ).fetchone()[0]
            content_ids[video_id] = content_id
            observed_at = stamp(row.get("captured_at"))
            for key, field in (("views", "view_count"), ("likes", "like_count"), ("comments", "comment_count")):
                value = row.get(field)
                connection.execute(
                    """INSERT INTO metric_snapshot
                       (content_id,metric_definition_id,observed_at,metric_value,availability_state,is_estimated)
                       VALUES (%s,%s,%s,%s,%s,false) ON CONFLICT DO NOTHING""",
                    (content_id, metric_ids[key], observed_at, value,
                     "observed" if value is not None else "not_exposed"),
                )
            metadata_hash = row_sha(row)
            metadata_artifacts[video_id] = insert_artifact(
                connection, run_id=run_id, content_id=content_id, kind="youtube_metadata",
                schema_id=row["schema"], version="1", uri=f"{relative(cohort_path)}#video={video_id}",
                digest=metadata_hash, epistemic="observed", rights="metadata_only",
                maker="youtube-census-collector", review="unreviewed", public_safe=False,
                source_hashes=[row.get("raw_sha256", "")], tool_key="youtube_video_census_10k", tool_version="v1",
            )
            counts["content"] += 1
            commit_if_due(connection, row_index, ROW_BATCH_SIZE)
        connection.commit()
        for transcript_index, (video_id, (path, payload)) in enumerate(transcripts.items(), 1):
            content_id = content_ids[video_id]
            path_hash = sha(path)
            semantic_hash = transcript_semantic_sha(payload)
            state = "observed" if payload.get("availability") == "observed" else "gap"
            insert_artifact_attempt(
                connection,
                run_id=run_id,
                content_id=content_id,
                stage="transcript",
                state=state,
                method=payload.get("normalization_method") or "public_subtitle_route",
                reason_code=payload.get("gap_reason") if state == "gap" else None,
                artifact_uri=relative(path),
                artifact_sha256=path_hash,
                captured_at=stamp(payload.get("captured_at")),
            )
            transcript_artifact = insert_artifact(
                connection, run_id=run_id, content_id=content_id, kind="transcript",
                schema_id=payload["schema"], version="3", uri=relative(path), digest=path_hash,
                epistemic="observed" if state == "observed" else "gap",
                rights="local_research_only", maker="youtube-evidence-collector", review="unreviewed",
                public_safe=False, source_hashes=[payload.get("source_sha256", "")],
                tool_key="youtube_evidence_10k", tool_version="v2",
            )
            transcript_artifacts[video_id] = transcript_artifact
            insert_edge(connection, metadata_artifacts[video_id], transcript_artifact, "normalizes")
            if state == "observed":
                transcript_id = get_or_create_transcript(
                    connection,
                    content_id=content_id,
                    payload=payload,
                    transcript_uri=relative(path),
                    transcript_sha256=semantic_hash,
                )
                for idx, segment in enumerate(payload.get("speech_segments") or payload.get("segments") or []):
                    connection.execute(
                        """INSERT INTO transcript_segment
                           (transcript_id,segment_index,start_ms,end_ms,text_body,evidence_state)
                           VALUES (%s,%s,%s,%s,%s,'observed') ON CONFLICT DO NOTHING""",
                        (transcript_id, idx, int(segment["start_ms"]), int(segment["end_ms"]), segment["text"]),
                    )
                    counts["transcript_segments"] += 1
                counts["transcripts"] += 1
            else:
                counts["transcript_gaps"] += 1
            commit_if_due(connection, transcript_index, LOCK_BATCH_SIZE)
        connection.commit()
        for frame_index, (video_id, (path, payload)) in enumerate(frames.items(), 1):
            content_id = content_ids[video_id]
            path_hash = sha(path)
            state = "observed" if payload.get("status") == "observed" else "gap"
            insert_artifact_attempt(
                connection,
                run_id=run_id,
                content_id=content_id,
                stage="frames",
                state=state,
                method="youtube_public_storyboard",
                reason_code=payload.get("gap_reason") if state == "gap" else None,
                artifact_uri=relative(path),
                artifact_sha256=path_hash,
                captured_at=datetime.now(UTC),
            )
            frame_artifact = insert_artifact(
                connection, run_id=run_id, content_id=content_id, kind="frame_manifest",
                schema_id=payload["schema"], version="2", uri=relative(path), digest=path_hash,
                epistemic="observed" if state == "observed" else "gap", rights="local_reference_only",
                maker="youtube-evidence-collector", review="unreviewed", public_safe=False,
                source_hashes=[(payload.get("media") or {}).get("sha256", "")],
                tool_key="youtube_evidence_10k", tool_version="v2",
            )
            frame_artifacts[video_id] = frame_artifact
            insert_edge(connection, metadata_artifacts[video_id], frame_artifact, "derived_from")
            if state == "observed":
                media = payload["media"]
                media_kind = media.get("asset_kind") or "preview"
                connection.execute(
                    """INSERT INTO media_asset
                       (content_id,asset_kind,asset_uri,sha256,byte_size,duration_ms,width,height,rights_state,retention_until)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                    (content_id, media_kind, f"runs/{run_dir.name}/{media['asset_uri']}", media["sha256"],
                     media.get("byte_size"), media.get("duration_ms"), media.get("width"), media.get("height"),
                     media["rights_state"], stamp(media.get("retention_until")) if media.get("retention_until") else None),
                )
                media_id = connection.execute(
                    "SELECT media_asset_id FROM media_asset WHERE content_id=%s AND asset_kind=%s AND sha256=%s",
                    (content_id, media_kind, media["sha256"]),
                ).fetchone()[0]
                for frame in payload.get("frames") or []:
                    connection.execute(
                        """INSERT INTO frame_artifact
                           (media_asset_id,frame_index,timestamp_ms,frame_uri,sha256,public_display_allowed)
                           VALUES (%s,%s,%s,%s,%s,false) ON CONFLICT DO NOTHING""",
                        (media_id, frame["frame_index"], frame["timestamp_ms"],
                         f"runs/{run_dir.name}/{frame['frame_uri']}", frame["sha256"]),
                    )
                    counts["frames"] += 1
                counts["frame_sets"] += 1
            else:
                counts["frame_gaps"] += 1
            commit_if_due(connection, frame_index, LOCK_BATCH_SIZE)
        connection.commit()
        analysis_file_hash = sha(analysis_path)
        for analysis_index, (video_id, analysis) in enumerate(analyses.items(), 1):
            content_id = content_ids[video_id]
            analysis_hash = row_sha(analysis)
            parent_artifacts = [metadata_artifacts[video_id]]
            if video_id in transcript_artifacts:
                parent_artifacts.append(transcript_artifacts[video_id])
            if video_id in frame_artifacts:
                parent_artifacts.append(frame_artifacts[video_id])
            input_hash = hashlib.sha256(("|".join(sorted(parent_artifacts)) + "|" + analysis_file_hash).encode()).hexdigest()
            insert_analysis_exact(
                connection,
                run_id=run_id,
                content_id=content_id,
                input_bundle_sha256=input_hash,
                analysis_uri=f"{relative(analysis_path)}#video={video_id}",
                analysis_sha256=analysis_hash,
            )
            analysis_artifact = insert_artifact(
                connection, run_id=run_id, content_id=content_id, kind="video_analysis",
                schema_id=analysis["schema"], version="2", uri=f"{relative(analysis_path)}#video={video_id}",
                digest=analysis_hash, epistemic="classified", rights="aggregate_public_safe",
                maker="youtube-census-lexical", review="passed_with_limitations", public_safe=False,
                source_hashes=[analysis_file_hash], tool_key="analyze_youtube_census_10k", tool_version="v2",
            )
            for parent_artifact in parent_artifacts:
                insert_edge(connection, parent_artifact, analysis_artifact, "analyzes", f"input:{input_hash}")
            counts["analyses"] += 1
            commit_if_due(connection, analysis_index, ROW_BATCH_SIZE)
        connection.commit()
        if args.campaign_dir:
            counts.update(load_campaign(connection, run_id, args.campaign_dir.resolve(), evidence_summary_artifact))
        connection.commit()
    print(json.dumps(dict(counts), indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--campaign-dir", type=Path)
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    with stage_lock(run_dir, "run-data", exclusive=True):
        assert_run_mutable(run_dir)
        return execute(args, run_dir)


if __name__ == "__main__":
    raise SystemExit(main())
