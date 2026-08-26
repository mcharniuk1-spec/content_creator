#!/usr/bin/env python3
"""Build a deterministic, Shorts-first 10K-video cohort from admitted snapshots."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f"required JSONL is missing: {path}")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    temporary.replace(path)


def relevance_score(row: dict[str, Any]) -> tuple[int, int, int, int]:
    signals = row.get("relevance_signals") or {}
    return (
        int(bool(row.get("analysis_eligible"))),
        int(bool(signals.get("relevant"))),
        int(signals.get("agent_hits") or 0) + int(signals.get("business_hits") or 0),
        int(signals.get("proof_hits") or 0),
    )


def row_rank(row: dict[str, Any]) -> tuple[Any, ...]:
    short_rank = 1 if row.get("format_state") == "DURATION_CANDIDATE" else 0
    english_rank = 1 if row.get("english_evidenced") else 0
    relevant = relevance_score(row)
    return (
        short_rank,
        *relevant,
        english_rank,
        row.get("published_at") or "",
        int(row.get("view_count") or 0),
        row.get("native_video_id") or "",
    )


def channel_rank(rows: list[dict[str, Any]]) -> tuple[Any, ...]:
    return (
        sum(row.get("format_state") == "DURATION_CANDIDATE" for row in rows),
        sum(bool((row.get("relevance_signals") or {}).get("relevant")) for row in rows),
        sum(bool(row.get("analysis_eligible")) for row in rows),
        sum(sum(relevance_score(row)[2:]) for row in rows),
        max((row.get("published_at") or "" for row in rows), default=""),
        rows[0].get("native_channel_id") or "",
    )


def build_cohort(
    snapshots: list[dict[str, Any]],
    baseline: list[dict[str, Any]],
    target: int,
    minimum_per_creator: int = 3,
    maximum_per_creator: int = 10,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if target <= 0 or minimum_per_creator <= 0 or maximum_per_creator < minimum_per_creator:
        raise ValueError("invalid target or creator bounds")
    by_video: dict[str, dict[str, Any]] = {}
    for row in snapshots:
        video_id = row.get("native_video_id")
        channel_id = row.get("native_channel_id")
        if not video_id or not channel_id or not row.get("raw_uri") or not row.get("raw_sha256"):
            raise ValueError("every snapshot needs video/channel identity and raw evidence")
        if video_id in by_video:
            raise ValueError(f"duplicate source video: {video_id}")
        by_video[video_id] = row
    baseline_ids = {row.get("native_video_id") for row in baseline}
    if None in baseline_ids or not baseline_ids.issubset(by_video):
        raise ValueError("baseline must be a unique subset of source snapshots")
    if len(baseline_ids) != len(baseline):
        raise ValueError("duplicate baseline video")

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in snapshots:
        groups[row["native_channel_id"]].append(row)
    for channel_rows in groups.values():
        channel_rows.sort(key=row_rank, reverse=True)

    baseline_channels = {by_video[video_id]["native_channel_id"] for video_id in baseline_ids}
    allowed_channels = {
        channel_id for channel_id, rows in groups.items()
        if len(rows) >= minimum_per_creator or channel_id in baseline_channels
    }
    selected_channels = set(baseline_channels)
    capacity = sum(min(maximum_per_creator, len(groups[channel_id])) for channel_id in selected_channels)
    candidates = sorted(
        (channel_id for channel_id in allowed_channels if channel_id not in selected_channels),
        key=lambda channel_id: channel_rank(groups[channel_id]),
        reverse=True,
    )
    for channel_id in candidates:
        if capacity >= target:
            break
        selected_channels.add(channel_id)
        capacity += min(maximum_per_creator, len(groups[channel_id]))
    if capacity < target:
        raise ValueError(f"insufficient eligible capacity: {capacity} < {target}")

    selected: dict[str, dict[str, Any]] = {video_id: by_video[video_id] for video_id in baseline_ids}
    counts = Counter(row["native_channel_id"] for row in selected.values())
    for channel_id in sorted(selected_channels):
        required = min(minimum_per_creator, len(groups[channel_id]))
        for row in groups[channel_id]:
            if counts[channel_id] >= required:
                break
            if row["native_video_id"] not in selected:
                selected[row["native_video_id"]] = row
                counts[channel_id] += 1
    if len(selected) > target:
        raise ValueError("baseline and creator minimums exceed target")

    remaining = [
        row for channel_id in selected_channels for row in groups[channel_id]
        if row["native_video_id"] not in selected
    ]
    remaining.sort(key=row_rank, reverse=True)
    for row in remaining:
        if len(selected) >= target:
            break
        channel_id = row["native_channel_id"]
        if counts[channel_id] >= maximum_per_creator:
            continue
        selected[row["native_video_id"]] = row
        counts[channel_id] += 1
    if len(selected) != target:
        raise ValueError(f"cohort construction ended at {len(selected)} instead of {target}")
    if max(counts.values(), default=0) > maximum_per_creator:
        raise ValueError("creator maximum violated")
    if maximum_per_creator / target > 0.01:
        raise ValueError("configured creator maximum exceeds 1% of final denominator")

    ranked = sorted(selected.values(), key=row_rank, reverse=True)
    output = []
    for index, row in enumerate(ranked, 1):
        item = dict(row)
        item.update({
            "schema": "north-hux.youtube-video-census-item.v1",
            "cohort_rank": index,
            "source_run_key": "20260825-youtube-calibration-300-v1",
            "selection_state": "baseline_reuse" if row["native_video_id"] in baseline_ids else "broad_screen",
            "format_claim": (
                "native_short_proved" if row.get("native_short_proved")
                else "duration_candidate" if row.get("format_state") == "DURATION_CANDIDATE"
                else "non_short" if row.get("format_state") == "NON_SHORT"
                else "unknown"
            ),
        })
        output.append(item)

    format_counts = Counter(row["format_claim"] for row in output)
    selection_counts = Counter(row["selection_state"] for row in output)
    summary = {
        "schema": "north-hux.youtube-video-census-summary.v1",
        "status": "pass",
        "target_videos": target,
        "selected_videos": len(output),
        "selected_creators": len(counts),
        "videos_per_creator": dict(sorted(Counter(counts.values()).items())),
        "minimum_selected_per_creator": min(counts.values()),
        "maximum_selected_per_creator": max(counts.values()),
        "maximum_creator_fraction": round(max(counts.values()) / target, 6),
        "baseline_videos_reused": selection_counts["baseline_reuse"],
        "broad_screen_videos": selection_counts["broad_screen"],
        "format_claims": dict(sorted(format_counts.items())),
        "duration_candidate_fraction": round(format_counts["duration_candidate"] / target, 6),
        "metadata_relevance_positive": sum(bool((row.get("relevance_signals") or {}).get("relevant")) for row in output),
        "analysis_eligible": sum(bool(row.get("analysis_eligible")) for row in output),
        "evidence_boundary": "search-ranked broad screen; duration does not prove native Shorts; transcript and independent review define accepted analytical subsets",
    }
    return output, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run-dir", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--target", type=int, default=10000)
    parser.add_argument("--minimum-per-creator", type=int, default=3)
    parser.add_argument("--maximum-per-creator", type=int, default=10)
    args = parser.parse_args()
    try:
        source = args.source_run_dir.resolve()
        run_dir = args.run_dir.resolve()
        rows, summary = build_cohort(
            load_jsonl(source / "derived" / "video-snapshots.jsonl"),
            load_jsonl(source / "derived" / "analyzed-content-cohort.jsonl"),
            args.target,
            args.minimum_per_creator,
            args.maximum_per_creator,
        )
        write_jsonl(run_dir / "derived" / "video-cohort.jsonl", rows)
        summary_path = run_dir / "derived" / "cohort-summary.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(summary, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error_code": type(exc).__name__, "message": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
