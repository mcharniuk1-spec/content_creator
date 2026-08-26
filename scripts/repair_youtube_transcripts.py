#!/usr/bin/env python3
"""Add a de-rolled speech layer to existing YouTube transcript artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.youtube_evidence_300 import de_roll_caption_segments  # noqa: E402


def repair(item: dict[str, Any]) -> dict[str, Any]:
    segments = item.get("segments") or []
    speech = de_roll_caption_segments(segments)
    raw_words = sum(len(segment.get("text", "").split()) for segment in segments)
    speech_words = sum(len(segment.get("text", "").split()) for segment in speech)
    item.update({
        "schema": "north-hux.youtube-transcript-artifact.v2",
        "speech_segments": speech,
        "speech_segment_count": len(speech),
        "speech_text": " ".join(segment["text"] for segment in speech),
        "raw_word_count": raw_words,
        "speech_word_count": speech_words,
        "rolling_caption_expansion_ratio": round(raw_words / speech_words, 4) if speech_words else None,
        "normalization_method": "longest_exact_token_overlap_v1",
    })
    return item


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    paths = sorted((run_dir / "normalized" / "transcripts").glob("*.json"))
    rows: list[dict[str, Any]] = []
    for path in paths:
        item = repair(json.loads(path.read_text(encoding="utf-8")))
        path.write_text(json.dumps(item, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        rows.append(item)
    rows.sort(key=lambda row: row["native_video_id"])
    (run_dir / "derived" / "transcripts.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    observed = [row for row in rows if row.get("availability") == "observed"]
    print(json.dumps({
        "status": "pass",
        "transcripts": len(rows),
        "observed": len(observed),
        "raw_segments": sum(row.get("segment_count", 0) for row in observed),
        "speech_segments": sum(row.get("speech_segment_count", 0) for row in observed),
        "raw_words": sum(row.get("raw_word_count", 0) for row in observed),
        "speech_words": sum(row.get("speech_word_count", 0) for row in observed),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
