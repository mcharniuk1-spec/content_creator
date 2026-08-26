from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL = (ROOT / "migrations" / "007_content_engine_strategy_studio_backup.sql").read_text(encoding="utf-8")


def test_migration_adds_full_lineage_tables() -> None:
    for table in (
        "artifact_attempt",
        "content_analysis_artifact",
        "strategy_release",
        "script_package",
        "shot_plan",
        "studio_edit_plan",
        "backup_receipt",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in SQL


def test_ai_broll_cannot_be_evidence_proof() -> None:
    assert "capture_mode <> 'ai_generated_broll' OR evidence_role <> 'proof'" in SQL


def test_new_lineage_tables_are_append_only() -> None:
    assert SQL.count("FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();") == 7


def test_backup_restore_state_is_explicit() -> None:
    assert "restore_test_state" in SQL
    assert "'not_run','passed','failed','blocked'" in SQL
