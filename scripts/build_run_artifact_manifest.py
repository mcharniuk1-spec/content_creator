#!/usr/bin/env python3
"""Build a deterministic, local-only hash manifest for one bounded run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_ROOTS = ("raw", "normalized", "derived")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    os.replace(temporary, path)


def build_manifest(run_dir: Path, roots: tuple[str, ...]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    run_dir = run_dir.resolve()
    rows: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    bytes_by_root: dict[str, int] = {}

    for root_name in roots:
        if Path(root_name).is_absolute() or ".." in Path(root_name).parts:
            raise ValueError(f"root must be run-relative: {root_name}")
        root = run_dir / root_name
        counts[root_name] = 0
        bytes_by_root[root_name] = 0
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"symlink is not allowed in evidence roots: {path}")
            if not path.is_file():
                continue
            size = path.stat().st_size
            rows.append({
                "schema": "north-hux.run-artifact-entry.v1",
                "run_key": run_dir.name,
                "root": root_name,
                "uri": path.relative_to(run_dir).as_posix(),
                "byte_size": size,
                "sha256": sha256(path),
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

    rows, summary = build_manifest(run_dir, roots)
    write_jsonl(manifest_path, rows)
    summary["manifest_uri"] = manifest_path.relative_to(run_dir).as_posix()
    summary["manifest_sha256"] = sha256(manifest_path)
    write_json(summary_path, summary)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
