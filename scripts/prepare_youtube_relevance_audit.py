#!/usr/bin/env python3
"""Prepare a reproducible top-100 plus stratified YouTube relevance audit sample."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--additional", type=int, default=150)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    cohort = {row["native_video_id"]: row for row in jsonl(run_dir / "derived" / "analyzed-content-cohort.jsonl")}
    analysis = {row["native_video_id"]: row for row in jsonl(run_dir / "derived" / "video-analysis.jsonl")}
    accounts = {row["native_channel_id"]: row for row in jsonl(run_dir / "derived" / "qualified-accounts.jsonl")}
    top = jsonl(run_dir / "derived" / "top-reference-cohort.jsonl")
    transcripts = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((run_dir / "normalized" / "transcripts").glob("*.json"))
    }
    chosen = [("top100", row["native_video_id"]) for row in top]
    used_creators = {row["native_channel_id"] for row in top}
    by_topic: dict[str, deque[dict[str, Any]]] = defaultdict(deque)
    remaining = [
        row for row in analysis.values()
        if row["native_channel_id"] not in used_creators
    ]
    remaining.sort(key=lambda row: (
        row["primary_topic"],
        accounts[row["native_channel_id"]].get("country") or "ZZ",
        -(accounts[row["native_channel_id"]].get("subscriber_count") or 0),
        row["native_video_id"],
    ))
    for row in remaining:
        by_topic[row["primary_topic"]].append(row)
    while len(chosen) < 100 + args.additional and any(by_topic.values()):
        for topic in sorted(by_topic):
            while by_topic[topic] and by_topic[topic][0]["native_channel_id"] in used_creators:
                by_topic[topic].popleft()
            if by_topic[topic] and len(chosen) < 100 + args.additional:
                row = by_topic[topic].popleft()
                used_creators.add(row["native_channel_id"])
                chosen.append(("stratified_non_top", row["native_video_id"]))
    if len(chosen) != 100 + args.additional or len(used_creators) != len(chosen):
        raise ValueError("relevance audit must contain one video per creator")
    rows = []
    for index, (sample_stratum, video_id) in enumerate(chosen, 1):
        item = cohort[video_id]
        coded = analysis[video_id]
        account = accounts[item["native_channel_id"]]
        transcript = transcripts.get(video_id, {})
        rows.append({
            "schema": "north-hux.youtube-relevance-audit-candidate.v1",
            "audit_index": index,
            "sample_stratum": sample_stratum,
            "native_channel_id": item["native_channel_id"],
            "native_video_id": video_id,
            "creator_title": account.get("title"),
            "creator_country": account.get("country"),
            "subscriber_count": account.get("subscriber_count"),
            "canonical_url": item["canonical_url"],
            "title": item.get("title"),
            "description_excerpt": (item.get("description") or "")[:1200],
            "speech_excerpt": (transcript.get("speech_text") or "")[:1800],
            "transcript_language": transcript.get("language"),
            "deterministic_primary_topic": coded["primary_topic"],
            "deterministic_video_type": coded["video_type"],
            "relevance_signals": item.get("relevance_signals"),
        })
    output = run_dir / "derived" / "relevance-audit-sample.jsonl"
    output.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    print(json.dumps({"status": "pass", "sample": len(rows), "top100": 100,
                      "stratified_non_top": args.additional, "unique_creators": len(used_creators)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
