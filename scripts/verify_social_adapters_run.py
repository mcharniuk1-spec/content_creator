#!/usr/bin/env python3
"""Verify the North Hux social-adapter run and emit a durable receipt/manifest."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
RUN_KEY = "20260825-north-hux-social-adapters-v1"
RUN = ROOT / "runs" / RUN_KEY
DSN = "host=127.0.0.1 port=55432 dbname=north_hux"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    failures: list[str] = []
    worker = load(RUN / "agents/youtube_collection/validation.json")
    routes = load(RUN / "agents/github_routes/route-catalog.json")
    analysis = load(RUN / "analysis/analysis-summary.json")
    config = load(ROOT / "config/social-collection-adapters.json")

    expected = {"observations": 41, "comments": 660, "transcript_rows": 94, "errors": 4}
    for key, value in expected.items():
        if worker["counts"].get(key) != value:
            failures.append(f"worker count mismatch {key}")
    if worker["status"] != "PASS_WITH_GAPS":
        failures.append("worker validation did not pass with registered gaps")
    if len(routes.get("routes", [])) != 11:
        failures.append("route catalog does not contain 11 reviewed routes")
    if analysis["facts"]["observed_videos"] != 41:
        failures.append("analysis/collection video count mismatch")
    if config["target"]["qualified_accounts_per_platform"] != {"minimum": 10000, "maximum": 12000}:
        failures.append("target drift")

    with psycopg.connect(DSN) as connection:
        connection.execute("SET search_path = north_hux, public")
        run_id = connection.execute(
            "SELECT run_id FROM research_run WHERE run_key = %s", (RUN_KEY,)
        ).fetchone()[0]
        database = {
            "run_id": run_id,
            "run_raw_objects": connection.execute("SELECT count(*) FROM raw_object WHERE run_id = %s", (run_id,)).fetchone()[0],
            "run_evidence": connection.execute("SELECT count(*) FROM evidence_record WHERE run_id = %s", (run_id,)).fetchone()[0],
            "run_rights": connection.execute("SELECT count(*) FROM rights_decision WHERE run_id = %s", (run_id,)).fetchone()[0],
            "sources_total": connection.execute("SELECT count(*) FROM source_registry").fetchone()[0],
            "accounts_total": connection.execute("SELECT count(*) FROM platform_account").fetchone()[0],
            "content_total": connection.execute("SELECT count(*) FROM content_item").fetchone()[0],
            "comments_total": connection.execute("SELECT count(*) FROM comment").fetchone()[0],
            "reply_edges_total": connection.execute("SELECT count(*) FROM comment_edge_observation").fetchone()[0],
            "transcripts_total": connection.execute("SELECT count(*) FROM transcript").fetchone()[0],
            "studio_exports": connection.execute("SELECT count(*) FROM studio_signal_export").fetchone()[0],
            "studio_candidates": connection.execute("SELECT count(*) FROM v_social_studio_candidate_v1").fetchone()[0],
            "eligible_social_candidates": connection.execute("SELECT count(*) FROM v_social_studio_candidate_v1 WHERE studio_candidate_state = 'eligible'").fetchone()[0],
            "social_contracts": connection.execute("SELECT count(*) FROM social_studio_contract").fetchone()[0],
            "social_axis_reviews": connection.execute("SELECT count(*) FROM studio_axis_review").fetchone()[0],
            "social_release_reviews": connection.execute("SELECT count(*) FROM studio_content_release_review").fetchone()[0],
            "metric_null_violations": connection.execute("SELECT count(*) FROM metric_snapshot WHERE (availability_state = 'observed' AND metric_value IS NULL) OR (availability_state <> 'observed' AND metric_value IS NOT NULL)").fetchone()[0],
            "author_pseudonym_violations": connection.execute("SELECT count(*) FROM comment WHERE author_pseudonym IS NOT NULL AND author_pseudonym !~ '^yt-author-[0-9a-f]{16}$'").fetchone()[0],
            "run_raw_pointer_nulls": connection.execute("SELECT count(*) FROM raw_object WHERE run_id = %s AND payload_uri IS NULL", (run_id,)).fetchone()[0],
        }

    required_db = {
        "run_raw_objects": 174,
        "run_evidence": 135,
        "run_rights": 41,
        "comments_total": 660,
        "reply_edges_total": 111,
        "transcripts_total": 94,
        "studio_exports": 60,
        "studio_candidates": 64,
        "eligible_social_candidates": 0,
        "social_contracts": 0,
        "social_axis_reviews": 0,
        "social_release_reviews": 0,
        "metric_null_violations": 0,
        "author_pseudonym_violations": 0,
        "run_raw_pointer_nulls": 0,
    }
    for key, value in required_db.items():
        if database[key] != value:
            failures.append(f"database check {key}: expected {value}, observed {database[key]}")

    excluded = {"verification-receipt.json", "run-manifest.json"}
    manifest_rows = []
    for path in sorted(item for item in RUN.rglob("*") if item.is_file() and item.name not in excluded):
        manifest_rows.append({
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha(path),
        })
    manifest = {
        "schema": "archflow.run-manifest.v1",
        "run_id": RUN_KEY,
        "files": manifest_rows,
        "file_count": len(manifest_rows),
    }
    (RUN / "run-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    receipt = {
        "schema": "archflow.social-adapters-verification.v1",
        "run_id": RUN_KEY,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_WITH_LIMITATIONS" if not failures else "FAIL",
        "worker_validation": worker["status"],
        "route_count": len(routes["routes"]),
        "database": database,
        "manifest_file_count": len(manifest_rows),
        "failures": failures,
        "limitations": [
            "Calibration is not a representative census.",
            "Instagram and TikTok official routes are not admitted.",
            "No source media or frame analysis was performed.",
            "No social candidate is eligible for Studio export before content-bound 12-axis evidence review, maker/reviewer separation, rights review, an active v1.1 contract, and a public-safe release review.",
        ],
    }
    (RUN / "verification-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
