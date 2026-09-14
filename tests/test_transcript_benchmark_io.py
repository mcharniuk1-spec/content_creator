"""Offline I/O boundary tests for the portable transcript benchmark."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest

import m2_signal.transcript_benchmark as benchmark
from tests.test_transcript_benchmark import _metric_vector, _transcript


def _fixture_inputs(tmp_path: Path, release_id: str = "release-test") -> dict[str, Path]:
    """Create the smallest local input set accepted by the benchmark."""
    db = tmp_path / "signal.sqlite"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE reel_analysis (release_id TEXT, reel_id TEXT, account_username TEXT, payload_json TEXT)"
    )
    payload = {
        "snapshot_date": "2026-09-01",
        "published_epoch_seconds": None,
        "duration_seconds": 10,
        "author_median_views": 1000,
        "author_baseline_n": 5,
        "eligibility_state": "PASS",
        "numeric_valid": True,
        "account_username": "acct-one",
        **_metric_vector(3),
    }
    conn.execute(
        "INSERT INTO reel_analysis VALUES (?, ?, ?, ?)",
        (release_id, "instagram:one", "acct-one", json.dumps(payload)),
    )
    conn.commit()
    conn.close()

    digest = "sha256:fixture"
    transcripts = tmp_path / "transcripts.jsonl"
    transcripts.write_text(
        json.dumps(_transcript("TR-001", digest, 3, words=5)) + "\n",
        encoding="utf-8",
    )
    source_map = tmp_path / "source-map.json"
    source_map.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "transcript_id": "TR-001",
                        "reel_id": "instagram:one",
                        "record_sha256": digest,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    summary = tmp_path / "summary.json"
    summary.write_text("{}\n", encoding="utf-8")
    return {
        "db": db,
        "transcripts": transcripts,
        "source_map": source_map,
        "summary": summary,
    }


def _run(paths: dict[str, Path], output: Path, release_id: str = "release-test", **kwargs):
    return benchmark.run_benchmark(
        paths["db"],
        paths["transcripts"],
        paths["source_map"],
        paths["summary"],
        output,
        release_id,
        **kwargs,
    )


def test_read_only_source_does_not_create_missing_sqlite_database(tmp_path: Path):
    paths = _fixture_inputs(tmp_path)
    paths["db"].unlink()

    with pytest.raises(sqlite3.OperationalError):
        benchmark.load_rows(
            paths["db"], paths["transcripts"], paths["source_map"], "release-test"
        )

    assert not paths["db"].exists()
    assert not list(tmp_path.glob("signal.sqlite-*"))


def test_existing_output_requires_explicit_overwrite_and_is_not_clobbered(tmp_path: Path):
    paths = _fixture_inputs(tmp_path)
    output = tmp_path / "output"
    output.mkdir()
    sentinel = output / "benchmark.json"
    sentinel.write_text("sentinel\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="output_exists_use_overwrite"):
        _run(paths, output)

    assert sentinel.read_text(encoding="utf-8") == "sentinel\n"
    assert not (output / "joined-transcript-metrics.jsonl").exists()
    assert not (output / "analytics.sqlite").exists()


@pytest.mark.parametrize("alias_kind", ["symlink", "hardlink"])
def test_output_file_aliases_and_hardlinks_to_input_are_rejected(
    tmp_path: Path, alias_kind: str
):
    paths = _fixture_inputs(tmp_path)
    output = tmp_path / f"output-{alias_kind}"
    output.mkdir()
    target = output / "benchmark.json"
    if alias_kind == "symlink":
        target.symlink_to(paths["summary"])
    else:
        os.link(paths["summary"], target)
    before = paths["summary"].read_bytes()

    with pytest.raises(ValueError, match="output_input_alias"):
        _run(paths, output)

    assert paths["summary"].read_bytes() == before
    assert os.path.samefile(target, paths["summary"])


def test_output_directory_overlapping_input_directory_is_rejected(tmp_path: Path):
    paths = _fixture_inputs(tmp_path)

    with pytest.raises(ValueError, match="output_directory_overlaps_input"):
        _run(paths, tmp_path)


def test_atomic_text_replace_failure_cleans_temp_and_preserves_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    target = tmp_path / "benchmark.json"
    target.write_text("before\n", encoding="utf-8")

    def fail_replace(_source, _destination):
        raise OSError("injected replace failure")

    monkeypatch.setattr(benchmark.os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected replace failure"):
        benchmark.atomic_write_text(target, "after\n")

    assert target.read_text(encoding="utf-8") == "before\n"
    assert not list(tmp_path.glob(".benchmark.json-*.tmp"))


def test_analytics_replace_failure_cleans_temp_and_preserves_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    paths = _fixture_inputs(tmp_path)
    output = tmp_path / "output"
    output.mkdir()
    destination = output / "analytics.sqlite"
    destination.write_bytes(b"previous analytics artifact")
    result = {
        "run_id": "io-test",
        "release_id": "release-test",
        "analysis_date": "",
        "policy": {"primary_outcome": "fixture"},
        "numeric_associations": [],
        "categorical_associations": [],
        "model_comparisons": [],
    }

    def fail_replace(_source, _destination):
        raise OSError("injected db replace failure")

    monkeypatch.setattr(benchmark.os, "replace", fail_replace)
    with pytest.raises(OSError, match="injected db replace failure"):
        benchmark.write_analytics_db(output, result, [], paths)

    assert destination.read_bytes() == b"previous analytics artifact"
    assert not list(output.glob(".analytics-*.sqlite.tmp"))


def test_unknown_release_fails_without_clobbering_existing_outputs(tmp_path: Path):
    paths = _fixture_inputs(tmp_path)
    output = tmp_path / "output"
    output.mkdir()
    existing = {
        name: output / name
        for name in ("benchmark.json", "joined-transcript-metrics.jsonl", "analytics.sqlite")
    }
    for path in existing.values():
        path.write_bytes(f"preserve:{path.name}".encode())
    before = {name: path.read_bytes() for name, path in existing.items()}

    with pytest.raises(ValueError, match="unknown release"):
        _run(paths, output, release_id="release-does-not-exist", overwrite=True)

    assert {name: path.read_bytes() for name, path in existing.items()} == before


def test_duplicate_transcript_ids_are_rejected(tmp_path: Path):
    paths = _fixture_inputs(tmp_path)
    line = paths["transcripts"].read_text(encoding="utf-8").strip()
    paths["transcripts"].write_text(f"{line}\n{line}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="transcript.*unique"):
        benchmark.load_rows(
            paths["db"], paths["transcripts"], paths["source_map"], "release-test"
        )


def test_source_map_with_extra_unmatched_entry_is_rejected(tmp_path: Path):
    paths = _fixture_inputs(tmp_path)
    source_map = json.loads(paths["source_map"].read_text(encoding="utf-8"))
    source_map["sources"].append(
        {
            "transcript_id": "TR-EXTRA",
            "reel_id": "instagram:extra",
            "record_sha256": "sha256:fixture",
        }
    )
    paths["source_map"].write_text(json.dumps(source_map), encoding="utf-8")

    with pytest.raises(ValueError):
        benchmark.load_rows(
            paths["db"], paths["transcripts"], paths["source_map"], "release-test"
        )


def test_transcript_without_source_map_entry_is_rejected(tmp_path: Path):
    paths = _fixture_inputs(tmp_path)
    transcript = _transcript("TR-MISSING", "sha256:fixture", 3, words=5)
    paths["transcripts"].write_text(json.dumps(transcript) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing_source_map_transcript_id"):
        benchmark.load_rows(
            paths["db"], paths["transcripts"], paths["source_map"], "release-test"
        )
