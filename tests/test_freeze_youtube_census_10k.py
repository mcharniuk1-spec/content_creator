import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("freeze", ROOT / "scripts" / "freeze_youtube_census_10k.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_backup_validation_requires_matching_hash_and_passed_restore(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(MODULE, "ROOT", tmp_path)
    backup = tmp_path / "terminal.dump"
    receipt = tmp_path / "restore.json"
    backup.write_bytes(b"database")
    receipt.write_text(
        '{"backup_key":"terminal","artifact_sha256":"' + MODULE.sha256(backup)
        + '","restore_test_state":"passed","critical_count_match":{"content_analysis_artifact":10000}}',
        encoding="utf-8",
    )
    result = MODULE.validate_backup(backup, receipt)
    assert result["artifact_sha256"] == MODULE.sha256(backup)
    receipt.write_text(receipt.read_text(encoding="utf-8").replace('"passed"', '"failed"'), encoding="utf-8")
    with pytest.raises(ValueError, match="failed"):
        MODULE.validate_backup(backup, receipt)


def test_project_relative_rejects_paths_outside_project(tmp_path: Path):
    with pytest.raises(ValueError, match="remain in the project"):
        MODULE.project_relative(tmp_path / "outside")


def test_terminal_backup_requires_exact_live_table_comparison_contract():
    assert "content_analysis_artifact" in MODULE.BACKUP_COUNT_TABLES
    assert "transcript_segment" in MODULE.BACKUP_COUNT_TABLES
    assert len(MODULE.BACKUP_COUNT_TABLES) >= 10
