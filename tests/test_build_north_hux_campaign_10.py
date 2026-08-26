import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("campaign", ROOT / "scripts" / "build_north_hux_campaign_10.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_campaign_has_two_tracks_and_ten_original_scripts():
    assert len(MODULE.CAMPAIGN) == 10
    assert {row["track"] for row in MODULE.CAMPAIGN} == {"pm_integration", "governed_agent_operations"}
    assert len({row["key"] for row in MODULE.CAMPAIGN}) == 10


def test_shot_grammar_and_ai_evidence_boundary():
    evidence = {"claims_boundary": {"broad_screen_videos": 10000, "analysis_eligible_videos": 2949}}
    for sequence, script in enumerate(MODULE.CAMPAIGN, 1):
        package = {
            "script_key": script["key"],
            "target_duration_ms": 30000,
            "full_script": " ".join(script["lines"]),
            "shots": MODULE.make_shots(script),
            "evidence_boundary": evidence["claims_boundary"],
        }
        MODULE.validate_package(package)
        ai = [shot for shot in package["shots"] if shot["capture_mode"] == "ai_generated_broll"]
        assert len(ai) == 1
        assert ai[0]["evidence_role"] == "context"
        assert ai[0]["generation_state"] == "blocked_approval"


def test_public_manifest_uses_project_relative_evidence_uri(tmp_path):
    evidence = MODULE.ROOT / "tests" / "fixtures" / "content_engine_v3_smoke.sql"
    assert MODULE.project_uri(evidence).startswith("tests/fixtures/")
