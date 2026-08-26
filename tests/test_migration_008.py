from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL = (ROOT / "migrations" / "008_artifact_lineage_and_studio_current_state.sql").read_text()


def test_shared_lineage_and_versioned_contract_exist():
    for name in ("artifact", "artifact_edge", "social_studio_contract_version", "edit_decision_list", "edl_segment"):
        assert f"CREATE TABLE IF NOT EXISTS {name}" in SQL
    assert "CREATE OR REPLACE VIEW v_current_artifact" in SQL
    assert "CREATE OR REPLACE VIEW v_current_social_studio_contract" in SQL


def test_current_state_gate_replaces_historical_any_pass_logic():
    assert "CREATE OR REPLACE VIEW v_latest_studio_axis_review" in SQL
    assert "CREATE OR REPLACE VIEW v_latest_content_rights_decision" in SQL
    assert "nonpassing_axis_count" in SQL
    assert "v_social_studio_candidate_v2" in SQL
    assert "reject_timeline_overlap" in SQL
