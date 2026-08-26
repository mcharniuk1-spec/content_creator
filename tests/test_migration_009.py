from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL = (ROOT / "migrations" / "009_terminal_integrity_and_idempotency.sql").read_text(encoding="utf-8")


def test_terminal_integrity_tables_and_unique_indexes_exist() -> None:
    assert "CREATE TABLE IF NOT EXISTS run_source_observation" in SQL
    assert "CREATE TABLE IF NOT EXISTS run_terminal_receipt" in SQL
    for name in (
        "uq_artifact_edge_normalized",
        "uq_collection_job_run_stage",
        "uq_metric_snapshot_content_observation",
        "uq_content_analysis_run_natural",
    ):
        assert name in SQL
    assert "CREATE TABLE IF NOT EXISTS transcript_identity" in SQL
    assert "PRIMARY KEY (content_id, transcript_sha256)" in SQL


def test_release_gate_repeats_separation_and_expiry_in_final_case() -> None:
    assert SQL.count("latest_release.maker_actor <> latest_release.reviewer_actor") >= 2
    assert SQL.count("latest_release.valid_until IS NULL OR latest_release.valid_until > now()") >= 2
    assert SQL.count("rights.allowed_use IN ('metadata_only','commentary','transcript','public_projection')") >= 2
    assert "rights.allowed_use NOT IN ('metadata_only','commentary','transcript','public_projection')" in SQL


def test_terminal_receipt_requires_exact_10k_and_maker_reviewer_separation() -> None:
    assert "cohort_count = 10000" in SQL
    assert "transcript_manifest_count = cohort_count" in SQL
    assert "frame_manifest_count = cohort_count" in SQL
    assert "CHECK (maker <> reviewer)" in SQL
