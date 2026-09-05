#!/usr/bin/env python3
"""Run or resume a bounded M2 export analysis. No network, models or writeback."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from m2_orchestrator.execution import DETERMINISTIC_STAGES, execute_replay


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-dir", type=Path, required=True)
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--mode", choices=["replay", "incremental", "server"], default="replay")
    p.add_argument("--metric-config", type=Path)
    p.add_argument("--database", type=Path, help="Optional shared append-only Signal ledger for incremental snapshots")
    p.add_argument("--until", choices=DETERMINISTIC_STAGES)
    a = p.parse_args()
    config = json.loads(a.metric_config.read_text()) if a.metric_config else None
    result = execute_replay(a.source_dir, a.run_dir, a.run_id, a.mode, a.until, config, a.database)
    print(json.dumps({"run_id": result["run_id"], "completed_stages": sum(s["state"] in {"PASS", "PASS_WITH_LIMITATIONS"} for s in result["stages"]),
                      "next": "export role tasks; review observed text, scenes and strategy before release",
                      "hikerapi_calls": 0, "provider_calls": 0, "notion_writes": 0}, indent=2))


if __name__ == "__main__":
    main()
