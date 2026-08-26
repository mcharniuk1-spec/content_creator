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


def test_transcript_semantic_hash_excludes_volatile_run_fields():
    base = {
        "native_video_id": "v1",
        "source_kind": "native_caption",
        "language": "en",
        "normalization_method": "v1",
        "source_sha256": "a" * 64,
        "speech_segments": [{"start_ms": 0, "end_ms": 1000, "text": "hello"}],
        "captured_at": "2026-01-01T00:00:00Z",
        "artifact_run_key": "run-a",
    }
    changed = {**base, "captured_at": "2027-01-01T00:00:00Z", "artifact_run_key": "run-b", "reused_from_run_key": "run-a"}
    assert MODULE.transcript_semantic_sha(base) == MODULE.transcript_semantic_sha(changed)


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


def test_exact_analysis_loader_has_conflict_readback_guard():
    source = (ROOT / "scripts" / "load_youtube_census_10k.py").read_text(encoding="utf-8")
    assert "analysis natural-key row conflicts with the exact analysis URI or hash" in source


def test_loader_batches_transactions_but_holds_one_session_lock():
    class Connection:
        commits = 0

        def commit(self):
            self.commits += 1

    connection = Connection()
    MODULE.commit_if_due(connection, 15, 16)
    assert connection.commits == 0
    MODULE.commit_if_due(connection, 16, 16)
    assert connection.commits == 1

    source = (ROOT / "scripts" / "load_youtube_census_10k.py").read_text(encoding="utf-8")
    assert "pg_advisory_lock(hashtextextended" in source
    assert "pg_advisory_xact_lock(hashtextextended(%s,0))\", (f\"terminal-freeze:" not in source
