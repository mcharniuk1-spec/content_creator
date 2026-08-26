#!/usr/bin/env python3
"""Register deterministic analysis artifacts and the human/Sol review queue."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
RUN_KEY = "20260825-north-hux-social-adapters-v1"
RUN = ROOT / "runs" / RUN_KEY
DSN = "host=127.0.0.1 port=55432 dbname=north_hux"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    observation_ids = [
        json.loads(line)["native_video_id"]
        for line in (RUN / "agents/youtube_collection/observations.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    artifacts = [
        ("json", RUN / "analysis/analysis-summary.json"),
        ("json", RUN / "analysis/top-references.json"),
        ("markdown", RUN / "analysis/analysis-report.md"),
        ("json", RUN / "agents/github_routes/route-catalog.json"),
        ("markdown", RUN / "agents/github_routes/recommendation.md"),
        ("markdown", RUN / "agents/sol_review/strategic-review.md"),
        ("markdown", RUN / "agents/sol_review/owner-decisions.md"),
        ("json", RUN / "agents/sol_review/codebook-v2.json"),
        ("markdown", RUN / "agents/sol_review/obsidian-notion-recommendations.md"),
        ("markdown", RUN / "integrated-review.md"),
        ("markdown", RUN / "owner-actions.md"),
        ("markdown", RUN / "agent-handout.md"),
        ("json", RUN / "verification-receipt-pre-integration.json"),
        ("json", RUN / "verification-receipt.json"),
    ]
    queued = 0
    with psycopg.connect(DSN) as connection:
        with connection.transaction():
            connection.execute("SET search_path = north_hux, public")
            run_id = connection.execute(
                "SELECT run_id FROM research_run WHERE run_key = %s", (RUN_KEY,)
            ).fetchone()[0]
            for kind, path in artifacts:
                connection.execute(
                    """
                    INSERT INTO export_artifact (
                        run_id, export_kind, artifact_uri, sha256, public_safe
                    ) VALUES (%s, %s, %s, %s, false)
                    ON CONFLICT (run_id, export_kind, artifact_uri) DO NOTHING
                    """,
                    (run_id, kind, path.relative_to(ROOT).as_posix(), digest(path)),
                )

            rows = connection.execute(
                "SELECT content_id FROM content_item WHERE platform = 'youtube' AND native_content_id = ANY(%s)",
                (observation_ids,),
            ).fetchall()
            for (content_id,) in rows:
                for review_type, reviewer in (
                    ("relevance", "sol-or-human-reviewer"),
                    ("taxonomy", "sol-or-human-reviewer"),
                    ("rights", "rights-reviewer"),
                    ("independent", "independent-reviewer"),
                ):
                    result = connection.execute(
                        """
                        INSERT INTO review_task (
                            run_id, platform, object_type, object_id, review_type,
                            assigned_reviewer, status, question_set_version
                        ) SELECT %s, 'youtube', 'content', %s, %s, %s, 'queued', 'north-hux-codebook-v2-draft'
                        WHERE NOT EXISTS (
                            SELECT 1 FROM review_task
                            WHERE run_id = %s AND object_type = 'content'
                              AND object_id = %s AND review_type = %s
                        )
                        RETURNING review_task_id
                        """,
                        (run_id, content_id, review_type, reviewer,
                         run_id, content_id, review_type),
                    ).fetchone()
                    queued += bool(result)

            for category, target, eligible, admitted, completed, reviewed, blocked in (
                ("captions", 1000, 41, 41, 41, 0, 0),
                ("video", 200, 0, 0, 0, 0, 200),
                ("frames", 200, 0, 0, 0, 0, 200),
                ("taxonomy", 41, 41, 41, 41, 0, 0),
                ("review", 41, 41, 41, 0, 0, 0),
                ("notion_projection", 1, 1, 1, 1, 1, 0),
                ("obsidian_projection", 1, 1, 1, 1, 1, 0),
            ):
                connection.execute(
                    """
                    INSERT INTO analysis_progress (
                        run_id, platform, category, target_count, eligible_count,
                        admitted_count, completed_count, reviewed_count, blocked_count
                    ) VALUES (%s, 'youtube', %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (run_id, platform, category) DO UPDATE
                    SET target_count = EXCLUDED.target_count,
                        eligible_count = EXCLUDED.eligible_count,
                        admitted_count = EXCLUDED.admitted_count,
                        completed_count = EXCLUDED.completed_count,
                        reviewed_count = EXCLUDED.reviewed_count,
                        blocked_count = EXCLUDED.blocked_count,
                        last_updated_at = now()
                    """,
                    (run_id, category, target, eligible, admitted, completed, reviewed, blocked),
                )
    print(json.dumps({"content_items": len(rows), "review_tasks_inserted": queued, "artifacts": len(artifacts)}, indent=2))


if __name__ == "__main__":
    main()
