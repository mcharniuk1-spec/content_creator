#!/usr/bin/env python3
"""Build a deterministic, local-only hash manifest for one bounded run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.youtube_evidence_10k import (  # noqa: E402
    active_artifact_claims,
    assert_run_mutable,
    frame_artifact_valid,
    stage_lock,
    transcript_artifact_valid,
)


DEFAULT_ROOTS = ("raw", "normalized", "derived")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_sha256(path: Path) -> tuple[str, int]:
    for _ in range(2):
        before = path.stat()
        digest = sha256(path)
        after = path.stat()
        before_state = (before.st_ino, before.st_size, before.st_mtime_ns)
        after_state = (after.st_ino, after.st_size, after.st_mtime_ns)
        if before_state == after_state:
            return digest, after.st_size
    raise ValueError(f"artifact changed while hashing: {path}")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    atomic_write_text(
        path,
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows),
    )


def atomic_write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_evidence_pointers(run_dir: Path) -> None:
    active_claims, _removed_stale_claims = active_artifact_claims(run_dir)
    if active_claims:
        raise ValueError(f"evidence writers are active: {len(active_claims)} claim files")
    for path in sorted((run_dir / "normalized" / "transcripts").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not transcript_artifact_valid(run_dir, path, payload):
            raise ValueError(f"invalid transcript pointer/hash chain: {path}")
    for path in sorted((run_dir / "normalized" / "frame-manifests").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not frame_artifact_valid(run_dir, path, payload):
            raise ValueError(f"invalid frame pointer/hash chain: {path}")


def build_manifest(run_dir: Path, roots: tuple[str, ...]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    run_dir = run_dir.resolve()
    rows: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    bytes_by_root: dict[str, int] = {}

    resolved_roots: list[Path] = []
    for root_name in roots:
        if Path(root_name).is_absolute() or ".." in Path(root_name).parts:
            raise ValueError(f"root must be run-relative: {root_name}")
        root = run_dir / root_name
        resolved = root.resolve()
        if not resolved.is_relative_to(run_dir):
            raise ValueError(f"root escapes run directory: {root_name}")
        if any(resolved == prior or resolved.is_relative_to(prior) or prior.is_relative_to(resolved) for prior in resolved_roots):
            raise ValueError(f"artifact roots overlap: {root_name}")
        resolved_roots.append(resolved)
        counts[root_name] = 0
        bytes_by_root[root_name] = 0
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"symlink is not allowed in evidence roots: {path}")
            if not path.is_file():
                continue
            digest, size = stable_sha256(path)
            rows.append({
                "schema": "north-hux.run-artifact-entry.v1",
                "run_key": run_dir.name,
                "root": root_name,
                "uri": path.relative_to(run_dir).as_posix(),
                "byte_size": size,
                "sha256": digest,
            })
            counts[root_name] += 1
            bytes_by_root[root_name] += size

    rows.sort(key=lambda row: row["uri"])
    summary = {
        "schema": "north-hux.run-artifact-manifest-summary.v1",
        "run_key": run_dir.name,
        "created_at": datetime.now(UTC).isoformat(),
        "roots": list(roots),
        "file_count": len(rows),
        "byte_size": sum(row["byte_size"] for row in rows),
        "files_by_root": counts,
        "bytes_by_root": bytes_by_root,
        "state": "local_only",
        "public_projection_allowed": False,
    }
    return rows, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--root", action="append", dest="roots")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    roots = tuple(args.roots or DEFAULT_ROOTS)
    manifest_path = (args.manifest or run_dir / "receipts" / "terminal-artifact-manifest.jsonl").resolve()
    summary_path = (args.summary or run_dir / "receipts" / "terminal-artifact-manifest-summary.json").resolve()
    if not run_dir.is_dir():
        raise SystemExit(f"run directory does not exist: {run_dir}")
    assert_run_mutable(run_dir)
    for output_path in (manifest_path, summary_path):
        if not output_path.is_relative_to(run_dir / "receipts"):
            raise SystemExit(f"manifest outputs must stay under the run receipts directory: {output_path}")

    with stage_lock(run_dir, "run-data", exclusive=True):
        assert_run_mutable(run_dir)
        with stage_lock(run_dir, "transcripts", exclusive=True):
            with stage_lock(run_dir, "frames", exclusive=True):
                validate_evidence_pointers(run_dir)
                rows, summary = build_manifest(run_dir, roots)
                write_jsonl(manifest_path, rows)
                summary["manifest_uri"] = manifest_path.relative_to(run_dir).as_posix()
                summary["manifest_sha256"] = sha256(manifest_path)
                write_json(summary_path, summary)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
