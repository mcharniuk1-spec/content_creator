#!/usr/bin/env python3
"""Recover numbered transcript manifest conflicts into canonical cohort identities."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.youtube_evidence_10k import (
    assert_run_mutable,
    stage_lock,
    transcript_artifact_valid,
    write_json,
)


CONFLICT = re.compile(r"^(?P<video_id>[^ ]+) (?P<copy>(?:[2-9]|[1-9][0-9]+))\.json$")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quarantine_fingerprint(path: Path) -> str:
    """Fingerprint a non-canonical copy without forcing cloud hydration.

    Canonical transcript manifests are still byte-hashed and pointer-validated by
    ``transcript_artifact_valid``. Numbered conflict copies are excluded from the
    evidence claim and retained only for forensic review, so filename and stable
    filesystem metadata are sufficient to name their quarantine target.
    """
    stat = path.stat()
    material = f"{path.name}\0{stat.st_size}\0{stat.st_mtime_ns}".encode()
    return hashlib.sha256(material).hexdigest()


def conflict_video_id(path: Path) -> str | None:
    matched = CONFLICT.match(path.name)
    return matched.group("video_id") if matched else None


def quarantine(path: Path, quarantine_dir: Path) -> str:
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    digest = quarantine_fingerprint(path)[:12]
    target = quarantine_dir / f"{path.stem}-{digest}{path.suffix}"
    counter = 1
    while target.exists():
        target = quarantine_dir / f"{path.stem}-{digest}-{counter}{path.suffix}"
        counter += 1
    os.replace(path, target)
    return target.name


def recover(run_dir: Path) -> dict[str, Any]:
    normalized = run_dir / "normalized" / "transcripts"
    quarantine_dir = run_dir / "receipts" / "quarantine" / "transcript-conflict-manifests"
    cohort = load_jsonl(run_dir / "derived" / "video-cohort.jsonl")
    cohort_ids = {row["native_video_id"] for row in cohort}
    if len(cohort) != 10000 or len(cohort_ids) != 10000:
        raise ValueError("recovery requires the exact 10,000-video cohort")
    groups: dict[str, list[Path]] = {}
    moved: list[str] = []
    restored: list[str] = []
    for path in sorted(normalized.glob("*.json")):
        conflict_id = conflict_video_id(path)
        if conflict_id:
            groups.setdefault(conflict_id, []).append(path)
        elif path.stem not in cohort_ids:
            moved.append(quarantine(path, quarantine_dir))
    for video_id, conflicts in sorted(groups.items()):
        canonical = normalized / f"{video_id}.json"
        if video_id not in cohort_ids:
            moved.extend(quarantine(path, quarantine_dir) for path in conflicts)
            continue
        candidates = sorted(conflicts, key=lambda path: (path.stat().st_mtime_ns, path.name), reverse=True)
        if not canonical.exists():
            selected = candidates.pop(0)
            os.replace(selected, canonical)
            restored.append(video_id)
        moved.extend(quarantine(path, quarantine_dir) for path in candidates)
        payload = json.loads(canonical.read_text(encoding="utf-8"))
        if not transcript_artifact_valid(run_dir, canonical, payload):
            moved.append(quarantine(canonical, quarantine_dir))
            if video_id in restored:
                restored.remove(video_id)
    canonical_paths = list(normalized.glob("*.json"))
    canonical_ids = {path.stem for path in canonical_paths}
    outside = canonical_ids - cohort_ids
    if outside:
        raise ValueError(f"recovery left identities outside the cohort: {len(outside)}")
    receipt = {
        "schema": "north-hux.transcript-conflict-recovery.v1",
        "run_key": run_dir.name,
        "recovered_at": datetime.now(UTC).isoformat(),
        "cohort_count": len(cohort_ids),
        "canonical_manifest_count": len(canonical_paths),
        "missing_manifest_count": len(cohort_ids - canonical_ids),
        "restored_canonical_count": len(restored),
        "quarantined_copy_count": len(moved),
        "quarantine_fingerprint_basis": "filename_size_mtime_ns; canonical files remain byte-hash validated",
        "restored_video_ids_sha256": hashlib.sha256("\n".join(sorted(restored)).encode()).hexdigest(),
        "quarantined_names_sha256": hashlib.sha256("\n".join(sorted(moved)).encode()).hexdigest(),
    }
    write_json(run_dir / "receipts" / "transcript-conflict-recovery.json", receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    with stage_lock(run_dir, "run-data", exclusive=True):
        assert_run_mutable(run_dir)
        with stage_lock(run_dir, "transcripts", exclusive=True):
            receipt = recover(run_dir)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
