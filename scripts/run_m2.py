#!/usr/bin/env python3
"""Run or resume a bounded M2 export analysis. Network media recovery requires explicit manifest and flag; no HikerAPI/models/writeback."""
import argparse
import json
import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from m2_orchestrator.state import file_digest
from m2_orchestrator.execution import DETERMINISTIC_STAGES, execute_replay


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-dir", type=Path, required=True)
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--mode", choices=["replay", "incremental", "server"], default="replay")
    p.add_argument("--metric-config", type=Path)
    p.add_argument("--database", type=Path, help="Optional shared append-only Signal ledger for incremental snapshots")
    p.add_argument("--until", choices=(*DETERMINISTIC_STAGES, "media_manifest", "media_acquire"))
    p.add_argument("--media-manifest", type=Path, help="Private complete corpus manifest; enables explicit acquisition stages")
    p.add_argument("--network-media", action="store_true", help="Authorize public media downloads, never HikerAPI")
    p.add_argument("--public-resolver", action="store_true", help="Use the installed, hash-pinned anonymous yt-dlp adapter through its allowlisted proxy")
    p.add_argument("--media-root", action="append", default=[], help="Explicit local source media root")
    a = p.parse_args()
    config = json.loads(a.metric_config.read_text()) if a.metric_config else None
    media_config = None
    if a.network_media and not a.media_manifest:
        p.error("--network-media requires --media-manifest")
    if a.media_manifest:
        media_config = {"enabled": True, "manifest_path": str(a.media_manifest.resolve()), "manifest_sha256": file_digest(a.media_manifest), "network": a.network_media, "media_roots": [str(Path(x).resolve()) for x in a.media_root]}
    if a.public_resolver:
        if not media_config or not a.network_media:
            p.error("--public-resolver requires --media-manifest and --network-media")
        executable=shutil.which("yt-dlp")
        if not executable:p.error("Installed yt-dlp required; no automatic installation")
        media_config.update(resolver_executable=str(Path(executable).resolve()),resolver_sha256=file_digest(Path(executable).resolve()))
    result = execute_replay(a.source_dir, a.run_dir, a.run_id, a.mode, a.until, config, a.database, media_config)
    print(json.dumps({"run_id": result["run_id"], "completed_stages": sum(s["state"] in {"PASS", "PASS_WITH_LIMITATIONS"} for s in result["stages"]),
                      "next": "export role tasks; review observed text, scenes and strategy before release",
                      "hikerapi_calls": 0, "provider_calls": 0, "notion_writes": 0}, indent=2))


if __name__ == "__main__":
    main()
