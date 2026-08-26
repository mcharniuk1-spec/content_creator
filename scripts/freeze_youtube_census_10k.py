#!/usr/bin/env python3
"""Validate and append a terminal freeze receipt for the 10K YouTube run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.youtube_evidence_10k import (
    active_artifact_claims,
    frame_artifact_valid,
    stage_lock,
    transcript_artifact_valid,
)
from scripts.youtube_video_census_10k import creator_cap_config_sha256, validate_pinned_creator_cap


DEFAULT_DSN = "host=127.0.0.1 port=55432 dbname=north_hux"
BACKUP_COUNT_TABLES = (
    "artifact",
    "artifact_edge",
    "content_analysis_artifact",
    "content_item",
    "edl_segment",
    "frame_artifact",
    "platform_account",
    "research_run",
    "script_package",
    "shot_plan",
    "transcript",
    "transcript_segment",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f"required JSONL is missing: {path}")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def row_sha(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True, default=str)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def project_relative(path: Path) -> str:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f"terminal artifact must remain in the project: {resolved}")
    return resolved.relative_to(ROOT).as_posix()


def validate_artifact_summary(run_dir: Path, summary_path: Path) -> dict[str, Any]:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("run_key") != run_dir.name:
        raise ValueError("artifact manifest summary run identity mismatch")
    manifest = (run_dir / str(summary.get("manifest_uri") or "")).resolve()
    if not manifest.is_relative_to(run_dir / "receipts") or not manifest.is_file():
        raise ValueError("artifact manifest is missing or outside the run receipts directory")
    if sha256(manifest) != summary.get("manifest_sha256"):
        raise ValueError("artifact manifest hash mismatch")
    rows = jsonl(manifest)
    uris = [row.get("uri") for row in rows]
    if len(rows) != summary.get("file_count") or len(set(uris)) != len(uris):
        raise ValueError("artifact manifest count or URI uniqueness mismatch")
    byte_size = 0
    allowed_roots = set(summary.get("roots") or [])
    for row in rows:
        uri = row.get("uri")
        root = row.get("root")
        if not isinstance(uri, str) or root not in allowed_roots:
            raise ValueError("artifact manifest row has an invalid URI or root")
        artifact_path = (run_dir / uri).resolve()
        root_path = (run_dir / root).resolve()
        if not artifact_path.is_relative_to(root_path) or not artifact_path.is_file():
            raise ValueError(f"artifact manifest entry is missing or escapes its root: {uri}")
        if artifact_path.stat().st_size != row.get("byte_size") or sha256(artifact_path) != row.get("sha256"):
            raise ValueError(f"artifact manifest entry changed after manifest creation: {uri}")
        byte_size += artifact_path.stat().st_size
    if byte_size != summary.get("byte_size"):
        raise ValueError("artifact manifest total byte size mismatch")
    return {**summary, "summary_uri": project_relative(summary_path), "summary_sha256": sha256(summary_path)}


def validate_backup(backup: Path, restore_receipt_path: Path) -> dict[str, Any]:
    if not backup.is_file() or not restore_receipt_path.is_file():
        raise ValueError("database backup and restore receipt are required")
    receipt = json.loads(restore_receipt_path.read_text(encoding="utf-8"))
    backup_hash = sha256(backup)
    if receipt.get("artifact_sha256") != backup_hash or receipt.get("restore_test_state") != "passed":
        raise ValueError("database backup hash or restore test receipt failed")
    critical = receipt.get("critical_count_match") or {}
    if int(critical.get("content_analysis_artifact") or 0) < 10000:
        raise ValueError("restore receipt does not prove the 10K analysis table")
    return {
        "backup_key": receipt.get("backup_key") or backup.stem,
        "artifact_uri": project_relative(backup),
        "artifact_sha256": backup_hash,
        "byte_size": backup.stat().st_size,
        "restore_receipt_uri": project_relative(restore_receipt_path),
        "restore_receipt_sha256": sha256(restore_receipt_path),
        "critical_count_match": critical,
    }


def validate_local_run(run_dir: Path) -> dict[str, Any]:
    cohort_path = run_dir / "derived" / "video-cohort.jsonl"
    analysis_path = run_dir / "derived" / "video-analysis-10k.jsonl"
    cohort = jsonl(cohort_path)
    analyses = jsonl(analysis_path)
    cohort_ids = [row.get("native_video_id") for row in cohort]
    analysis_ids = [row.get("native_video_id") for row in analyses]
    if len(cohort) != 10000 or len(set(cohort_ids)) != 10000:
        raise ValueError("terminal cohort must contain exactly 10,000 unique video identities")
    if len(analyses) != 10000 or len(set(analysis_ids)) != 10000 or set(analysis_ids) != set(cohort_ids):
        raise ValueError("terminal analysis must exactly match the 10,000-video cohort")
    creator_counts = Counter(row.get("native_channel_id") for row in cohort)
    maximum_creator_fraction = max(creator_counts.values()) / len(cohort)
    approved_cap = validate_pinned_creator_cap(run_dir)
    if maximum_creator_fraction > approved_cap:
        raise ValueError("terminal cohort violates the approved creator cap")

    transcript_paths = sorted((run_dir / "normalized" / "transcripts").glob("*.json"))
    frame_paths = sorted((run_dir / "normalized" / "frame-manifests").glob("*.json"))
    if len(transcript_paths) != 10000 or len(frame_paths) != 10000:
        raise ValueError(f"terminal evidence is incomplete: transcripts={len(transcript_paths)}, frames={len(frame_paths)}")
    transcript_ids: set[str] = set()
    frame_ids: set[str] = set()
    transcript_gaps = 0
    frame_gaps = 0
    for path in transcript_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not transcript_artifact_valid(run_dir, path, payload):
            raise ValueError(f"invalid terminal transcript pointer: {path}")
        transcript_ids.add(path.stem)
        transcript_gaps += payload.get("availability") != "observed"
    for path in frame_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not frame_artifact_valid(run_dir, path, payload):
            raise ValueError(f"invalid terminal frame pointer: {path}")
        frame_ids.add(path.stem)
        frame_gaps += payload.get("status") != "observed"
    if transcript_ids != set(cohort_ids) or frame_ids != set(cohort_ids):
        raise ValueError("terminal transcript/frame identity sets do not match the cohort")
    active_claims, removed_stale_claims = active_artifact_claims(run_dir)
    if active_claims:
        raise ValueError(f"terminal freeze found {len(active_claims)} active evidence claims")
    return {
        "cohort_count": len(cohort),
        "analysis_count": len(analyses),
        "creator_count": len(creator_counts),
        "maximum_creator_fraction": maximum_creator_fraction,
        "approved_creator_cap": approved_cap,
        "creator_cap_config_sha256": creator_cap_config_sha256(),
        "transcript_manifest_count": len(transcript_paths),
        "transcript_gap_count": transcript_gaps,
        "frame_manifest_count": len(frame_paths),
        "frame_gap_count": frame_gaps,
        "cohort_sha256": sha256(cohort_path),
        "stale_claims_removed": len(removed_stale_claims),
    }


def validate_database_analysis_identity(connection: psycopg.Connection, run_id: int, run_dir: Path) -> int:
    analysis_path = run_dir / "derived" / "video-analysis-10k.jsonl"
    local_rows = jsonl(analysis_path)
    local_hashes = {row["native_video_id"]: row_sha(row) for row in local_rows}
    if len(local_rows) != 10000 or len(local_hashes) != 10000:
        raise ValueError("local analysis identity is not exact before database comparison")
    analysis_file_hash = sha256(analysis_path)
    database_rows = connection.execute(
        """SELECT content.native_content_id, analysis.analyzer_key, analysis.analyzer_version,
                  analysis.input_bundle_sha256, analysis.analysis_uri, analysis.analysis_sha256,
                  array_remove(array_agg(DISTINCT edge.parent_artifact_id), NULL)
           FROM content_analysis_artifact analysis
           JOIN content_item content ON content.content_id=analysis.content_id
           LEFT JOIN artifact video_artifact
             ON video_artifact.run_id=analysis.run_id
            AND video_artifact.content_id=analysis.content_id
            AND video_artifact.artifact_type='video_analysis'
            AND video_artifact.artifact_sha256=analysis.analysis_sha256
           LEFT JOIN artifact_edge edge
             ON edge.child_artifact_id=video_artifact.artifact_id
            AND edge.edge_type='analyzes'
            AND edge.claim_locator='input:' || analysis.input_bundle_sha256
           WHERE analysis.run_id=%s
             AND NOT EXISTS (
                 SELECT 1 FROM content_analysis_artifact newer
                 WHERE newer.supersedes_analysis_id=analysis.content_analysis_artifact_id
             )
           GROUP BY content.native_content_id,analysis.analyzer_key,analysis.analyzer_version,
                    analysis.input_bundle_sha256,analysis.analysis_uri,analysis.analysis_sha256""",
        (run_id,),
    ).fetchall()
    if len(database_rows) != 10000:
        raise ValueError(f"database analysis row count is not exact: {len(database_rows)}")
    seen: set[str] = set()
    base_uri = f"{project_relative(analysis_path)}#video="
    for video_id, analyzer, version, input_hash, uri, analysis_hash, parents in database_rows:
        if video_id in seen or video_id not in local_hashes:
            raise ValueError(f"database analysis contains duplicate or foreign video identity: {video_id}")
        seen.add(video_id)
        parent_ids = sorted(parents or [])
        expected_input = hashlib.sha256(("|".join(parent_ids) + "|" + analysis_file_hash).encode()).hexdigest()
        if (
            analyzer != "youtube-census-lexical"
            or version != "v2"
            or uri != base_uri + video_id
            or analysis_hash != local_hashes[video_id]
            or input_hash != expected_input
            or len(parent_ids) != 3
        ):
            raise ValueError(f"database analysis lineage mismatch: {video_id}")
    if seen != set(local_hashes):
        raise ValueError("database analysis native-video identity set does not match local analysis")
    return len(seen)


def database_counts(connection: psycopg.Connection, run_id: int, run_dir: Path) -> dict[str, int]:
    analysis_total = connection.execute(
        "SELECT count(*) FROM content_analysis_artifact WHERE run_id=%s",
        (run_id,),
    ).fetchone()[0]
    analysis_current, analysis_distinct = connection.execute(
        """SELECT count(*),count(DISTINCT content_id)
           FROM content_analysis_artifact analysis
           WHERE run_id=%s AND NOT EXISTS (
               SELECT 1 FROM content_analysis_artifact newer
               WHERE newer.supersedes_analysis_id=analysis.content_analysis_artifact_id
           )""",
        (run_id,),
    ).fetchone()
    attempts: dict[str, int] = {}
    for stage in ("transcript", "frames"):
        analyzed_count, latest_count, matched_count = connection.execute(
            """WITH analyzed AS (
                   SELECT DISTINCT analysis.content_id FROM content_analysis_artifact analysis
                   WHERE run_id=%s AND NOT EXISTS (
                       SELECT 1 FROM content_analysis_artifact newer
                       WHERE newer.supersedes_analysis_id=analysis.content_analysis_artifact_id
                   )
               ), latest AS (
                   SELECT DISTINCT ON (content_id) content_id
                   FROM artifact_attempt WHERE run_id=%s AND stage=%s
                   ORDER BY content_id, attempt_number DESC
               )
               SELECT (SELECT count(*) FROM analyzed),
                      (SELECT count(*) FROM latest),
                      count(*)
               FROM latest JOIN analyzed USING (content_id)""",
            (run_id, run_id, stage),
        ).fetchone()
        if (int(analyzed_count), int(latest_count), int(matched_count)) != (10000, 10000, 10000):
            raise ValueError(f"database {stage} attempt identities do not exactly match the analysis set")
        attempts[stage] = int(latest_count)
    campaign = connection.execute(
        """SELECT count(DISTINCT package.script_package_id),
                  count(DISTINCT shot.shot_plan_id),
                  count(DISTINCT edit.studio_edit_plan_id)
           FROM strategy_release release
           JOIN script_package package ON package.strategy_release_id=release.strategy_release_id
           LEFT JOIN shot_plan shot ON shot.script_package_id=package.script_package_id
           LEFT JOIN studio_edit_plan edit ON edit.script_package_id=package.script_package_id
           WHERE release.run_id=%s""",
        (run_id,),
    ).fetchone()
    counts = {
        "content_analysis_artifact_history": int(analysis_total),
        "current_analysis_rows": int(analysis_current),
        "distinct_current_analysis_content": int(analysis_distinct),
        "latest_transcript_attempts": int(attempts["transcript"]),
        "latest_frame_attempts": int(attempts["frames"]),
        "script_packages": int(campaign[0]),
        "shot_plans": int(campaign[1]),
        "studio_edit_plans": int(campaign[2]),
        "exact_analysis_identity_matches": validate_database_analysis_identity(connection, run_id, run_dir),
    }
    expected = {
        "current_analysis_rows": 10000,
        "distinct_current_analysis_content": 10000,
        "latest_transcript_attempts": 10000,
        "latest_frame_attempts": 10000,
        "script_packages": 10,
        "shot_plans": 100,
        "studio_edit_plans": 10,
        "exact_analysis_identity_matches": 10000,
    }
    if any(counts[key] != value for key, value in expected.items()):
        raise ValueError(f"database terminal counts failed: expected={expected}, actual={counts}")
    return counts


def validate_backup_matches_live_database(connection: psycopg.Connection, backup: dict[str, Any]) -> int:
    critical = backup.get("critical_count_match") or {}
    missing = [table for table in BACKUP_COUNT_TABLES if table not in critical]
    if missing:
        raise ValueError(f"restore receipt is missing live-count comparisons: {missing}")
    for table in BACKUP_COUNT_TABLES:
        live_count = int(connection.execute(f'SELECT count(*) FROM north_hux."{table}"').fetchone()[0])
        if live_count != int(critical[table]):
            raise ValueError(
                f"database backup is stale for {table}: restored={critical[table]}, live={live_count}"
            )
    return len(BACKUP_COUNT_TABLES)


def terminal_payload(run_key: str, row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "schema": "north-hux.youtube-terminal-receipt.v1",
        "run_key": run_key,
        "run_terminal_receipt_id": int(row[0]),
        "version": int(row[1]),
        "status": row[2],
        "frozen_at": row[3].isoformat(),
        "maker": row[4],
        "reviewer": row[5],
        "verification": row[6],
    }


def matching_terminal_receipt(
    connection: psycopg.Connection,
    run_id: int,
    artifact_sha256: str,
    backup_sha256: str,
) -> tuple[Any, ...] | None:
    return connection.execute(
        """SELECT run_terminal_receipt_id,version,status,frozen_at,maker,reviewer,verification_json
           FROM run_terminal_receipt
           WHERE run_id=%s AND artifact_manifest_sha256=%s AND database_backup_sha256=%s
           ORDER BY version DESC LIMIT 1""",
        (run_id, artifact_sha256, backup_sha256),
    ).fetchone()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--artifact-summary", type=Path)
    parser.add_argument("--database-backup", required=True, type=Path)
    parser.add_argument("--restore-receipt", required=True, type=Path)
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    parser.add_argument("--maker", default="codex-integrator")
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--recover-pending-freeze", action="store_true")
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    if not run_dir.is_relative_to(ROOT / "runs") or not run_dir.is_dir():
        raise ValueError("run directory must be an existing project run")
    if args.maker == args.reviewer:
        raise ValueError("terminal maker and reviewer must be different")
    summary_path = (args.artifact_summary or run_dir / "receipts" / "terminal-artifact-manifest-summary.json").resolve()
    freeze_marker = run_dir / "receipts" / "terminal-freeze.json"
    terminal_path = run_dir / "terminal-receipt.json"

    with stage_lock(run_dir, "run-data", exclusive=True):
        with stage_lock(run_dir, "transcripts", exclusive=True):
            with stage_lock(run_dir, "frames", exclusive=True):
                with stage_lock(run_dir, "disk-wave", exclusive=True):
                    local = validate_local_run(run_dir)
                    artifact = validate_artifact_summary(run_dir, summary_path)
                    backup = validate_backup(args.database_backup.resolve(), args.restore_receipt.resolve())
                    prior_local_state = freeze_marker.exists() or terminal_path.exists()
                    pending = {
                        "schema": "north-hux.youtube-terminal-freeze-marker.v1",
                        "run_key": run_dir.name,
                        "status": "pending_database_commit",
                        "created_at": datetime.now(UTC).isoformat(),
                        "artifact_manifest_sha256": artifact["manifest_sha256"],
                        "database_backup_sha256": backup["artifact_sha256"],
                    }
                    with psycopg.connect(args.dsn) as connection, connection.transaction():
                        connection.execute("SET search_path=north_hux,public")
                        connection.execute(
                            "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                            (f"terminal-freeze:{run_dir.name}",),
                        )
                        run_row = connection.execute(
                            "SELECT run_id FROM research_run WHERE run_key=%s", (run_dir.name,)
                        ).fetchone()
                        if not run_row:
                            raise ValueError("database research_run is missing")
                        run_id = int(run_row[0])
                        existing = matching_terminal_receipt(
                            connection, run_id, artifact["manifest_sha256"], backup["artifact_sha256"]
                        )
                        if existing:
                            terminal = terminal_payload(run_dir.name, existing)
                        else:
                            if prior_local_state and not args.recover_pending_freeze:
                                raise ValueError(
                                    "local freeze state has no matching database receipt; rerun with --recover-pending-freeze after review"
                                )
                            atomic_json(freeze_marker, pending)
                            try:
                                db_counts = database_counts(connection, run_id, run_dir)
                                db_counts["backup_live_count_matches"] = validate_backup_matches_live_database(
                                    connection, backup
                                )
                                connection.execute(
                                    """INSERT INTO backup_receipt
                                       (run_id,backup_key,backup_kind,scope_json,artifact_uri,artifact_sha256,byte_size,
                                        encryption_state,restore_test_state,restore_receipt_uri)
                                       VALUES (%s,%s,'postgres_custom',%s,%s,%s,%s,'not_required_local','passed',%s)
                                       ON CONFLICT (backup_key) DO NOTHING""",
                                    (run_id, backup["backup_key"], Jsonb({"terminal_counts": db_counts}),
                                     backup["artifact_uri"], backup["artifact_sha256"], backup["byte_size"],
                                     backup["restore_receipt_uri"]),
                                )
                                previous = connection.execute(
                                    """SELECT run_terminal_receipt_id,version FROM run_terminal_receipt
                                       WHERE run_id=%s ORDER BY version DESC LIMIT 1""",
                                    (run_id,),
                                ).fetchone()
                                version = int(previous[1]) + 1 if previous else 1
                                status = (
                                    "pass_with_limitations"
                                    if local["transcript_gap_count"] or local["frame_gap_count"]
                                    else "pass"
                                )
                                verification = {
                                    "local": local,
                                    "artifact_manifest": artifact,
                                    "database": db_counts,
                                    "backup": backup,
                                }
                                receipt_row = connection.execute(
                                    """INSERT INTO run_terminal_receipt
                                       (run_id,version,status,cohort_count,transcript_manifest_count,frame_manifest_count,
                                        cohort_sha256,artifact_manifest_sha256,database_backup_sha256,verification_json,
                                        maker,reviewer,supersedes_terminal_receipt_id)
                                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                                       RETURNING run_terminal_receipt_id,version,status,frozen_at,maker,reviewer,verification_json""",
                                    (run_id, version, status, local["cohort_count"], local["transcript_manifest_count"],
                                     local["frame_manifest_count"], local["cohort_sha256"],
                                     artifact["manifest_sha256"], backup["artifact_sha256"], Jsonb(verification),
                                     args.maker, args.reviewer, previous[0] if previous else None),
                                ).fetchone()
                                connection.execute(
                                    "UPDATE research_run SET status='frozen', ended_at=now() WHERE run_id=%s",
                                    (run_id,),
                                )
                                terminal = terminal_payload(run_dir.name, receipt_row)
                            except Exception:
                                atomic_json(freeze_marker, {**pending, "status": "failed_closed"})
                                raise
                    atomic_json(terminal_path, terminal)
                    atomic_json(
                        freeze_marker,
                        {**pending, "status": terminal["status"], "terminal_receipt_uri": project_relative(terminal_path)},
                    )
    print(json.dumps(terminal, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
