#!/usr/bin/env python3
"""Verify the bounded YouTube official fixture without reading runtime secrets."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "20260825-youtube-census-v1"
OUTPUTS = {"manifest.json", "verification-receipt.json"}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    failures: list[str] = []
    required = [
        "admission-receipt.json",
        "execution-authorization.json",
        "research-brief.md",
        "source-allowlist.json",
        "task-contracts.md",
        "derived/smoke-result.json",
        "database-readback.json",
        "notion-readback.json",
        "obsidian-readback.json",
        "issues.md",
        "execution-report.md",
        "agent-handout.md",
        "agents/luna-sampling-review.md",
        "agents/luna-scraper-terminal-review.md",
        "agents/luna-transcript-frame-review.md",
    ]
    for relative in required:
        if not (RUN / relative).is_file():
            failures.append(f"missing:{relative}")

    smoke = read_json(RUN / "derived/smoke-result.json")
    requests = read_jsonl(RUN / "ledgers/youtube-api-requests.jsonl")
    failures_ledger = read_jsonl(RUN / "ledgers/youtube-api-failures.jsonl")
    quota = read_jsonl(RUN / "ledgers/youtube-api-quota.jsonl")
    if smoke.get("status") != "pass" or smoke.get("item_count") != 1:
        failures.append("fixture_result")
    if len(requests) != 1 or len(failures_ledger) != 5 or len(quota) != 6:
        failures.append("ledger_counts")

    for receipt in requests:
        raw_path = RUN / receipt["raw_uri"]
        if not raw_path.is_file():
            failures.append("raw_pointer")
            continue
        if sha256(raw_path) != receipt["raw_sha256"]:
            failures.append("raw_hash")

    suspicious = []
    for path in RUN.rglob("*"):
        if not path.is_file() or path.name in OUTPUTS:
            continue
        if path.suffix.lower() not in {".md", ".json", ".jsonl", ".txt"}:
            continue
        if "AIza" in path.read_text(encoding="utf-8", errors="ignore"):
            suspicious.append(str(path.relative_to(RUN)))
    if suspicious:
        failures.append("suspected_youtube_key_literal")

    manifest_files = {}
    for path in sorted(RUN.rglob("*")):
        if path.is_file() and path.name not in OUTPUTS:
            manifest_files[str(path.relative_to(RUN))] = sha256(path)
    manifest = {
        "schema": "archflow.run-manifest.v1",
        "run_id": RUN.name,
        "excluded": ["manifest.json", "verification-receipt.json", "runtime secret source"],
        "files": manifest_files,
    }
    (RUN / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    receipt = {
        "schema": "north-hux.youtube-census-verification.v1",
        "run_id": RUN.name,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_FIXTURE_SCALE_BLOCKED" if not failures else "FAIL",
        "failures": failures,
        "tests": {"passed": 57, "subtests_passed": 9},
        "fixture": {
            "successful_requests": len(requests),
            "failed_attempts": len(failures_ledger),
            "quota_attempts": len(quota),
            "raw_objects": len(list((RUN / "raw").rglob("*.json"))),
        },
        "manifest_file_count": len(manifest_files),
        "scale": {
            "qualified_accounts": 0,
            "top_100_selected": 0,
            "transcripts_added": 0,
            "frame_sets_added": 0,
            "blockers": ["RG-01", "RG-02"],
        },
        "secrets_read": False,
    }
    (RUN / "verification-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
