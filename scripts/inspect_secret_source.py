#!/usr/bin/env python3
"""Print a zero-secret runtime inventory for a local credential source."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from m2_engine.secret_source import inventory  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("secret_file", type=Path)
    args = parser.parse_args()
    try:
        result = inventory(args.secret_file)
    except (OSError, UnicodeError) as exc:
        print(json.dumps({"source_readable": False, "error_type": type(exc).__name__}), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
