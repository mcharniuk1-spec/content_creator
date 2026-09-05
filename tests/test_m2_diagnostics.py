import hashlib
import json
import sqlite3
from pathlib import Path

from m2_orchestrator.diagnostics import export_diagnostics
from m2_orchestrator.execution import default_actors
from m2_orchestrator.policy import STAGES
from m2_orchestrator.state import Controller, canonical, digest


def _controller(tmp_path: Path):
    root = tmp_path / "run"
    artifact = root / "products" / "admit.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("evidence\n", encoding="utf-8")
    source = tmp_path / "source.json"
    source.write_text("{}\n", encoding="utf-8")
    config = {
        "schema": "m2.run-config.v1",
        "platforms": ["instagram_reels"],
        "mode": "replay",
        "provider_execution": False,
        "hikerapi_execution": False,
        "source_manifest": [{"source_id": "source.json", "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}],
        "actors": default_actors(),
        "metric_config": {},
        "production": {"requires_generation": False},
    }
    controller = Controller(root)
    controller.init("diagnostics-fixture", config)
    started = controller.begin("admit", "integrator")
    controller.finish("admit", started["token"], ["products/admit.json"], "PASS")
    return root, artifact


def test_export_preserves_stage_snapshot_and_checks_artifacts(tmp_path):
    root, artifact = _controller(tmp_path)
    artifact.write_text("changed after receipt\n", encoding="utf-8")
    output = tmp_path / "diagnostics.sqlite"

    result = export_diagnostics(root / "state.sqlite", output)

    assert result["state_events_ok"] is True
    assert result["stages"] == len(STAGES)
    connection = sqlite3.connect(output)
    connection.row_factory = sqlite3.Row
    try:
        assert connection.execute("select state from diagnostic_stages where stage_id='admit'").fetchone()[0] == "PASS"
        assert connection.execute("select state from diagnostic_stages where stage_id='freeze_config'").fetchone()[0] == "NOT_STARTED"
        assert connection.execute("select validation from diagnostic_stage_artifacts where stage_id='admit'").fetchone()[0] == "HASH_MISMATCH"
        assert connection.execute("select error_code from diagnostic_issues where stage_id='admit'").fetchone()[0] == "ARTIFACT_HASH_MISMATCH"
        token_event = connection.execute("select payload from diagnostic_events where kind='STAGE_STARTED'").fetchone()[0]
        assert '"token":"[REDACTED]"' in token_event
    finally:
        connection.close()


def test_export_imports_actual_nullable_metrics_and_reports_units(tmp_path):
    root, _ = _controller(tmp_path)
    signal = tmp_path / "signal.sqlite"
    connection = sqlite3.connect(signal)
    connection.executescript("""
        create table releases(release_id text primary key);
        create table reel_metric_values(
          release_id text, reel_id text, metric_name text, value real, observed_n integer,
          denominator real, unit text, formula_version text
        );
        insert into releases values ('release-1');
        insert into reel_metric_values values ('release-1','reel-1','views',null,0,null,'count','fixture-v1');
        insert into reel_metric_values values ('release-1','reel-1','likes_per_1k_views',2.0,1,0,'events_per_1000_views','fixture-v1');
    """)
    connection.commit()
    connection.close()
    output = tmp_path / "diagnostics.sqlite"

    result = export_diagnostics(root / "state.sqlite", output, signal)

    assert result["metrics"] == 2
    connection = sqlite3.connect(output)
    connection.row_factory = sqlite3.Row
    try:
        missing = connection.execute("select value,is_missing,unit from diagnostic_metrics where metric_name='views'").fetchone()
        assert missing[0] is None and missing[1] == 1 and missing[2] == "count"
        invalid = connection.execute("select validation_state from diagnostic_metrics where metric_name='likes_per_1k_views'").fetchone()[0]
        assert invalid == "INVALID"
        assert connection.execute("select error_code from diagnostic_issues where kind='metric'").fetchone()[0] == "DENOMINATOR_MUST_BE_POSITIVE"
    finally:
        connection.close()


def test_export_is_idempotent_for_unchanged_source(tmp_path):
    root, _ = _controller(tmp_path)
    output = tmp_path / "diagnostics.sqlite"
    first = export_diagnostics(root / "state.sqlite", output)
    second = export_diagnostics(root / "state.sqlite", output)
    assert first["idempotent"] is False
    assert second["idempotent"] is True
