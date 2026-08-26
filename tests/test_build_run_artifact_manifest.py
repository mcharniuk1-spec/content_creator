from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_run_artifact_manifest import build_manifest, sha256, write_jsonl


def test_build_manifest_hashes_bounded_roots_deterministically(tmp_path: Path) -> None:
    run = tmp_path / "run-1"
    (run / "raw").mkdir(parents=True)
    (run / "normalized").mkdir()
    (run / "derived").mkdir()
    (run / "raw" / "source.txt").write_text("source\n", encoding="utf-8")
    (run / "normalized" / "speech.json").write_text('{"text":"hello"}\n', encoding="utf-8")
    (run / "derived" / "summary.json").write_text('{"count":1}\n', encoding="utf-8")

    rows, summary = build_manifest(run, ("raw", "normalized", "derived"))

    assert [row["uri"] for row in rows] == [
        "derived/summary.json",
        "normalized/speech.json",
        "raw/source.txt",
    ]
    assert summary["file_count"] == 3
    assert summary["files_by_root"] == {"raw": 1, "normalized": 1, "derived": 1}
    manifest = run / "receipts" / "manifest.jsonl"
    write_jsonl(manifest, rows)
    assert sha256(manifest)
    assert [json.loads(line)["uri"] for line in manifest.read_text(encoding="utf-8").splitlines()] == [
        "derived/summary.json",
        "normalized/speech.json",
        "raw/source.txt",
    ]


def test_build_manifest_rejects_unbounded_parent_root(tmp_path: Path) -> None:
    run = tmp_path / "run-1"
    run.mkdir()
    with pytest.raises(ValueError, match="run-relative"):
        build_manifest(run, ("../outside",))
