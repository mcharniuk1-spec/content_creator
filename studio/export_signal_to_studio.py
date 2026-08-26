#!/usr/bin/env python3
"""Aggregate immutable per-framework Signal exports into the current file-backed interface."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "studio" / "framework-library" / "v1"
OUT = ROOT / "outputs" / "signal-to-studio" / "v1"


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    library = load(LIB / "library-manifest.json")
    exports = []
    for item in library["records"]:
        record = load(LIB / item["path"] / "signal-export.json")
        if record["external_provider_state"] != "NOT_RUN":
            raise ValueError(f"provider state drift: {record['export_id']}")
        exports.append(record)
    exports.sort(key=lambda row: row["export_id"])
    records_path = OUT / "records.jsonl"
    records_path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in exports), encoding="utf-8")
    records_hash = hashlib.sha256(records_path.read_bytes()).hexdigest()
    manifest = {
        "schema": "signal-to-studio-export-manifest.v1",
        "interface_schema": "signal-to-studio.v1",
        "truth_state": "FILE_BACKED_SOURCE_OF_TRUTH",
        "database_state": "POSTGRESQL_NOT_EXECUTED",
        "record_count": len(exports),
        "records_path": "outputs/signal-to-studio/v1/records.jsonl",
        "records_sha256": "sha256:" + records_hash,
        "source_library_manifest": "studio/framework-library/v1/library-manifest.json",
        "rights_default": "metadata_commentary_only",
        "external_provider_state": "NOT_RUN",
    }
    dump(OUT / "manifest.json", manifest)
    (OUT / "sha256sums.txt").write_text(f"{records_hash}  records.jsonl\n", encoding="utf-8")
    (OUT / "README.md").write_text("""# Signal-to-Studio v1 export

This is the active file-backed integration boundary. `records.jsonl` contains immutable, canonical Signal export snapshots consumed by the local Studio framework library. PostgreSQL is not executed; the future read-only view/table mapping is documented in `studio/DATABASE-INTERFACE.md`.

All records are metadata/commentary abstractions with external provider state `NOT_RUN`. They do not authorize source-media reuse, final video, Figma mutation, publication, deployment, or external writeback.
""", encoding="utf-8")
    print(json.dumps({"records": len(exports), "sha256": records_hash, "output": OUT.relative_to(ROOT).as_posix()}, indent=2))


if __name__ == "__main__":
    main()
