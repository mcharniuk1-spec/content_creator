import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("report", ROOT / "scripts" / "build_youtube_census_10k_report.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_human_numbers_and_labels():
    assert MODULE.human(10000) == "10.0K"
    assert MODULE.label("governed_agent_operations") == "Governed Agent Operations"
    assert MODULE.percent(25, 100) == "25.0%"
