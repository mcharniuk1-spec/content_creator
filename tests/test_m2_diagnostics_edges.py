import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from m2_orchestrator.diagnostics import DiagnosticsError, _readonly, export_diagnostics
from m2_orchestrator.execution import default_actors
from m2_orchestrator.state import Controller


def _new_run(tmp_path: Path, run_id: str = "edge-fixture") -> tuple[Path, Path, Controller]:
    root = tmp_path / run_id
    source = tmp_path / f"{run_id}-source.json"
    source.write_text("{}\n", encoding="utf-8")
    config = {
        "schema": "m2.run-config.v1",
        "platforms": ["instagram_reels"],
        "mode": "replay",
        "provider_execution": False,
        "hikerapi_execution": False,
        "source_manifest": [{"source_id": source.name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}],
        "actors": default_actors(),
        "metric_config": {},
        "production": {"requires_generation": False},
    }
    controller = Controller(root)
    controller.init(run_id, config)
    return root, source, controller


def _complete_admit(root: Path, controller: Controller) -> Path:
    artifact = root / "products" / "admit.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("fixture\n", encoding="utf-8")
    begun = controller.begin("admit", "integrator")
    controller.finish("admit", begun["token"], ["products/admit.json"], "PASS")
    return artifact


def test_rejects_state_signal_and_hardlink_outputs_without_mutating_sources(tmp_path):
    root, _, controller = _new_run(tmp_path)
    _complete_admit(root, controller)
    state = root / "state.sqlite"
    before = state.read_bytes()

    with pytest.raises(DiagnosticsError, match="SEPARATE_FROM_SOURCE"):
        export_diagnostics(state, state)
    hardlink = tmp_path / "state-hardlink.sqlite"
    hardlink.hardlink_to(state)
    with pytest.raises(DiagnosticsError, match="SEPARATE_FROM_SOURCE"):
        export_diagnostics(state, hardlink)
    signal_hardlink = tmp_path / "signal-hardlink.sqlite"
    signal_hardlink.hardlink_to(state)
    output_signal_hardlink = tmp_path / "output-signal-hardlink.sqlite"
    output_signal_hardlink.hardlink_to(signal_hardlink)
    with pytest.raises(DiagnosticsError, match="SEPARATE_FROM_SOURCE"):
        export_diagnostics(state, output_signal_hardlink, signal_hardlink)

    assert state.read_bytes() == before


def test_source_connections_are_query_only(tmp_path):
    root, _, controller = _new_run(tmp_path)
    _complete_admit(root, controller)
    connection = _readonly(root / "state.sqlite")
    try:
        assert connection.execute("PRAGMA query_only").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("CREATE TABLE should_not_exist(value TEXT)")
    finally:
        connection.close()
    assert not (root / "state.sqlite-journal").exists()


def test_changed_artifact_is_rechecked_after_cached_export(tmp_path):
    root, _, controller = _new_run(tmp_path)
    artifact = _complete_admit(root, controller)
    output = tmp_path / "diagnostics.sqlite"
    first = export_diagnostics(root / "state.sqlite", output)
    artifact.write_text("changed\n", encoding="utf-8")

    second = export_diagnostics(root / "state.sqlite", output)

    assert first["idempotent"] is False
    assert second["idempotent"] is False
    connection = sqlite3.connect(output)
    try:
        assert connection.execute("SELECT validation FROM diagnostic_stage_artifacts WHERE stage_id='admit'").fetchone()[0] == "HASH_MISMATCH"
        assert connection.execute("SELECT error_code FROM diagnostic_issues WHERE error_code='ARTIFACT_HASH_MISMATCH'").fetchone() is not None
    finally:
        connection.close()


def test_committed_wal_event_changes_logical_signature_and_results(tmp_path):
    root, _, controller = _new_run(tmp_path)
    _complete_admit(root, controller)
    state = root / "state.sqlite"
    output = tmp_path / "diagnostics.sqlite"
    first = export_diagnostics(state, output)

    writer = sqlite3.connect(state)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("INSERT INTO events(payload,previous,hash) VALUES(?,?,?)",
                   (json.dumps({"kind": "TAMPERED_EVENT"}), "0" * 64, "f" * 64))
    writer.commit()
    try:
        second = export_diagnostics(state, output)
    finally:
        writer.close()

    assert second["source_signature"] != first["source_signature"]
    assert second["state_events_ok"] is False
    connection = sqlite3.connect(output)
    try:
        assert connection.execute("SELECT error_code FROM diagnostic_issues WHERE error_code IN ('EVENT_CHAIN_MISMATCH','EVENT_SEQUENCE_GAP')").fetchone() is not None
    finally:
        connection.close()


def test_unresolved_stage_failure_is_open_with_evidence(tmp_path):
    root, _, controller = _new_run(tmp_path)
    begun = controller.begin("admit", "integrator")
    controller.fail("admit", begun["token"], "WORKER_INTERRUPTED")
    output = tmp_path / "diagnostics.sqlite"

    export_diagnostics(root / "state.sqlite", output)

    connection = sqlite3.connect(output)
    connection.row_factory = sqlite3.Row
    try:
        issue = connection.execute("SELECT * FROM diagnostic_issues WHERE error_code='STAGE_FAILURE_UNRESOLVED'").fetchone()
        assert issue is not None
        assert issue["status"] == "OPEN"
        assert issue["opened_event_seq"] is not None
        assert issue["evidence_hash"]
    finally:
        connection.close()


def test_malformed_metric_denominator_is_flagged_without_crash(tmp_path):
    root, _, controller = _new_run(tmp_path)
    _complete_admit(root, controller)
    signal = tmp_path / "signal.sqlite"
    source = sqlite3.connect(signal)
    source.executescript("""
        CREATE TABLE releases(release_id TEXT PRIMARY KEY);
        CREATE TABLE reel_metric_values(
            release_id TEXT, reel_id TEXT, metric_name TEXT, value REAL,
            observed_n INTEGER, denominator REAL, unit TEXT, formula_version TEXT
        );
        INSERT INTO releases VALUES ('release-1');
        INSERT INTO reel_metric_values VALUES
            ('release-1','reel-1','likes_per_1k_views',1.0,1,'bad','events_per_1000_views','edge-v1');
    """)
    source.commit()
    source.close()
    output = tmp_path / "diagnostics.sqlite"

    result = export_diagnostics(root / "state.sqlite", output, signal)

    assert result["metrics"] == 1
    connection = sqlite3.connect(output)
    try:
        row = connection.execute("SELECT validation_state,validation_issues FROM diagnostic_metrics").fetchone()
        assert row[0] == "INVALID"
        assert "NON_FINITE_DENOMINATOR" in row[1]
    finally:
        connection.close()


def test_tampered_event_hash_is_flagged(tmp_path):
    root, _, controller = _new_run(tmp_path)
    _complete_admit(root, controller)
    state = root / "state.sqlite"
    connection = sqlite3.connect(state)
    connection.execute("DROP TRIGGER events_no_update")
    connection.execute("UPDATE events SET hash=? WHERE seq=2", ("0" * 64,))
    connection.commit()
    connection.close()

    output = tmp_path / "diagnostics.sqlite"
    result = export_diagnostics(state, output)

    assert result["state_events_ok"] is False
    connection = sqlite3.connect(output)
    try:
        assert connection.execute("SELECT error_code FROM diagnostic_issues WHERE error_code='EVENT_CHAIN_MISMATCH'").fetchone() is not None
    finally:
        connection.close()
