#!/usr/bin/env python3
"""Run the provider-disabled M2 vertical slice against frozen local inputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from m2_engine import M2Error, run_vertical_slice  # noqa: E402


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--input-dir", required=True, type=Path, help="Frozen run-input directory")
    value.add_argument("--output-dir", required=True, type=Path, help="Explicit local output directory")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        manifest = run_vertical_slice(args.input_dir, args.output_dir)
    except M2Error as exc:
        print(json.dumps({"status": "ERROR", "code": exc.code, "message": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    except OSError as exc:
        print(json.dumps({"status": "ERROR", "code": "OUTPUT_IO_ERROR", "message": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps({"status": "COMPLETE_WITH_EXPLICIT_GAPS", "content_hash": manifest["content_hash"], "output_dir": str(args.output_dir)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
