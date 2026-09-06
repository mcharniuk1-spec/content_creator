#!/usr/bin/env python3
"""Run the bounded serial full-corpus media dispatcher."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from m2_orchestrator.corpus_media import CorpusMediaDispatcher
from m2_studio.media import digest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="serial resumable M2 corpus media dispatcher")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--python-executable", default=sys.executable)
    parser.add_argument("--media-root", action="append", type=Path, default=[])
    parser.add_argument("--rights-receipt", required=True)
    parser.add_argument("--resolver-executable", type=Path)
    parser.add_argument("--resolver-sha256")
    parser.add_argument("--allowed-host", action="append", default=["cdninstagram.com", "fbcdn.net"])
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--cache-bytes", type=int, default=8 * 1024**3)
    parser.add_argument("--reserve-bytes", type=int, default=5 * 1024**3)
    parser.add_argument("--max-items", type=int)
    parser.add_argument("--network", action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args(argv)

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    dispatcher = CorpusMediaDispatcher(
        manifest,
        args.run_root,
        model_dir=args.model_dir,
        manifest_sha256=digest(args.manifest),
        python_executable=args.python_executable,
        media_roots=tuple(args.media_root),
        rights_receipt=args.rights_receipt,
        resolver_executable=args.resolver_executable,
        resolver_sha256=args.resolver_sha256,
        batch_size=args.batch_size,
        cache_bytes=args.cache_bytes,
        reserve_bytes=args.reserve_bytes,
        allowed_hosts=tuple(dict.fromkeys(args.allowed_host)),
    )
    result = dispatcher.run(network=args.network, max_items=args.max_items)
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
