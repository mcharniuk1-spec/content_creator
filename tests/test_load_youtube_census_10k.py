import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("loader", ROOT / "scripts" / "load_youtube_census_10k.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_artifact_ids_are_stable_and_typed():
    digest = "a" * 64
    assert MODULE.artifact_id("transcript", digest) == "art-transcript-" + "a" * 32


def test_row_hash_is_order_independent():
    assert MODULE.row_sha({"a": 1, "b": 2}) == MODULE.row_sha({"b": 2, "a": 1})


def test_collector_transcript_kinds_map_to_schema_vocabulary():
    assert MODULE.canonical_transcript_kind("native_subtitle") == "native_subtitle"
    assert MODULE.canonical_transcript_kind("native_caption_source_unresolved") == "native_caption"


def test_project_relative_paths_only(tmp_path):
    outside = tmp_path / "artifact.json"
    outside.write_text("{}")
    try:
        MODULE.relative(outside)
    except ValueError as error:
        assert "inside project root" in str(error)
    else:
        raise AssertionError("outside path accepted")


def test_loader_terminal_gate_requires_exact_identity_sets():
    cohort_ids = {"a", "b"}
    evidence = {"a": (Path("a.json"), {}), "b": (Path("b.json"), {})}
    MODULE.validate_evidence_identity(cohort_ids, evidence, evidence, allow_partial=False)
    try:
        MODULE.validate_evidence_identity(
            cohort_ids,
            {"a": (Path("a.json"), {})},
            evidence,
            allow_partial=False,
        )
    except ValueError as error:
        assert "identity sets incomplete" in str(error)
    else:
        raise AssertionError("incomplete evidence identity set passed")
