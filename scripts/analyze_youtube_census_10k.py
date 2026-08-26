#!/usr/bin/env python3
"""Deterministic, evidence-labeled analysis for the 10K YouTube broad screen."""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import tempfile
from collections import Counter, defaultdict, deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from analyze_youtube_calibration import (
    CTA_RULES,
    HOOK_RULES,
    STORY_RULES,
    TOPIC_RULES,
    VIDEO_TYPE_RULES,
    first_match,
    hook_text,
    story,
    topic,
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    atomic_write_text(
        path,
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
    )


def atomic_write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def median(values: list[float | int | None]) -> float | None:
    cleaned = [float(value) for value in values if value is not None]
    return round(statistics.median(cleaned), 4) if cleaned else None


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[round((len(ordered) - 1) * q)], 4)


def load_transcripts(run_dir: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted((run_dir / "normalized" / "transcripts").glob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise ValueError(f"invalid transcript manifest: {path}") from exc
        video_id = row.get("native_video_id")
        if not video_id or video_id != path.stem:
            raise ValueError(f"transcript filename/payload identity mismatch: {path}")
        if video_id in rows:
            raise ValueError(f"duplicate transcript identity: {video_id}")
        rows[video_id] = row
    return rows


def load_frame_manifests(run_dir: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted((run_dir / "normalized" / "frame-manifests").glob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise ValueError(f"invalid frame manifest: {path}") from exc
        video_id = row.get("native_video_id")
        if not video_id or video_id != path.stem:
            raise ValueError(f"frame filename/payload identity mismatch: {path}")
        if video_id in rows:
            raise ValueError(f"duplicate frame identity: {video_id}")
        rows[video_id] = row
    return rows


def validate_evidence_identity(
    cohort_ids: set[str],
    transcripts: dict[str, dict[str, Any]],
    frames: dict[str, dict[str, Any]],
    *,
    allow_partial: bool,
) -> None:
    transcript_ids = set(transcripts)
    frame_ids = set(frames)
    foreign_transcripts = transcript_ids - cohort_ids
    foreign_frames = frame_ids - cohort_ids
    if foreign_transcripts or foreign_frames:
        raise ValueError(
            "foreign evidence identities: "
            f"transcripts={sorted(foreign_transcripts)[:5]}, frames={sorted(foreign_frames)[:5]}"
        )
    if not allow_partial and (transcript_ids != cohort_ids or frame_ids != cohort_ids):
        raise ValueError(
            "evidence identity sets incomplete: "
            f"transcripts={len(transcript_ids)}/{len(cohort_ids)}, "
            f"frames={len(frame_ids)}/{len(cohort_ids)}"
        )


def classify_video(
    row: dict[str, Any],
    transcript: dict[str, Any],
    frame_manifest: dict[str, Any],
    creator_median_views: float,
) -> dict[str, Any]:
    transcript_text = transcript.get("speech_text") or transcript.get("text") or ""
    material = "\n".join([row.get("title") or "", row.get("description") or "", transcript_text[:16000]])
    primary_topic, secondary_topics = topic(material)
    hook, hook_basis = hook_text(transcript, row.get("title") or "")
    views = int(row.get("view_count") or 0)
    likes = int(row.get("like_count") or 0)
    reported_comments = int(row.get("comment_count") or 0)
    view_index = round(views / max(1, creator_median_views), 4)
    engagement_proxy = round((likes + reported_comments) / views, 6) if views else None
    relevance = row.get("relevance_signals") or {}
    reference_score = (
        min(8.0, math.log10(views + 1))
        + min(4.0, view_index)
        + min(2.0, (engagement_proxy or 0) * 50)
        + (1.5 if transcript.get("availability") == "observed" else 0)
        + (0.75 if row.get("format_state") == "DURATION_CANDIDATE" else 0)
        + min(2.0, float(relevance.get("agent_hits") or 0) / 4)
        + min(1.0, float(relevance.get("business_hits") or 0) / 4)
        + min(1.0, float(relevance.get("proof_hits") or 0) / 4)
    )
    frames = frame_manifest.get("frames") or []
    return {
        "schema": "north-hux.youtube-video-analysis.v2",
        "epistemic_state": "DERIVED_RULE_BASED_WITH_DIRECT_EVIDENCE_FIELDS",
        "native_channel_id": row["native_channel_id"],
        "native_video_id": row["native_video_id"],
        "canonical_url": row["canonical_url"],
        "title": row.get("title"),
        "published_at": row.get("published_at"),
        "duration_seconds": row.get("duration_seconds"),
        "format_state": row.get("format_state"),
        "native_short_proved": bool(row.get("native_short_proved")),
        "analysis_eligible": bool(row.get("analysis_eligible")),
        "selection_state": row.get("selection_state"),
        "views": views,
        "likes": likes,
        "reported_comments": reported_comments,
        "creator_median_views_in_sample": creator_median_views,
        "creator_view_index": view_index,
        "engagement_proxy": engagement_proxy,
        "primary_topic": primary_topic,
        "secondary_topics": secondary_topics,
        "video_type": first_match(material, VIDEO_TYPE_RULES),
        "storytelling_style": story(material),
        "hook_type": first_match(hook, HOOK_RULES),
        "hook_text": hook,
        "hook_evidence_basis": hook_basis,
        "cta_type": first_match(transcript_text[-2000:] + " " + (row.get("description") or ""), CTA_RULES),
        "transcript_availability": transcript.get("availability", "gap"),
        "transcript_source_kind": transcript.get("source_kind"),
        "transcript_language": transcript.get("language"),
        "transcript_segment_count": int(transcript.get("segment_count") or 0),
        "speech_segment_count": int(transcript.get("speech_segment_count") or 0),
        "rolling_caption_expansion_ratio": transcript.get("rolling_caption_expansion_ratio"),
        "frame_state": frame_manifest.get("status", "not_attempted"),
        "frame_count": len(frames),
        "frame_method": (frame_manifest.get("media") or {}).get("collection_method"),
        "reference_score": round(reference_score, 4),
    }


def select_top_references(rows: list[dict[str, Any]], target: int) -> list[dict[str, Any]]:
    per_creator: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["analysis_eligible"]:
            per_creator[row["native_channel_id"]].append(row)
    candidates = [
        max(
            creator_rows,
            key=lambda item: (
                item["transcript_availability"] == "observed",
                item["frame_state"] == "observed",
                item["format_state"] == "DURATION_CANDIDATE",
                item["reference_score"],
            ),
        )
        for creator_rows in per_creator.values()
    ]
    topic_order = [item[0] for item in TOPIC_RULES] + ["general_ai_or_unresolved"]
    queues = {
        label: deque(sorted(
            (row for row in candidates if row["primary_topic"] == label),
            key=lambda item: item["reference_score"],
            reverse=True,
        ))
        for label in topic_order
    }
    selected: list[dict[str, Any]] = []
    while len(selected) < target and any(queues.values()):
        for label in topic_order:
            if queues[label] and len(selected) < target:
                selected.append(queues[label].popleft())
    return [{**row, "reference_rank": index} for index, row in enumerate(selected, start=1)]


def build_summary(
    run_dir: Path,
    cohort: list[dict[str, Any]],
    analyzed: list[dict[str, Any]],
    transcripts: dict[str, dict[str, Any]],
    frames: dict[str, dict[str, Any]],
    source_comments: list[dict[str, Any]],
) -> dict[str, Any]:
    eligible = [row for row in analyzed if row["analysis_eligible"]]
    observed_transcripts = [row for row in transcripts.values() if row.get("availability") == "observed"]
    observed_frames = [row for row in frames.values() if row.get("status") == "observed"]
    format_counts = Counter(row.get("format_state") or "UNKNOWN" for row in cohort)
    creator_counts = Counter(row["native_channel_id"] for row in cohort)
    views = [float(row["views"]) for row in eligible]
    engagement = [float(row["engagement_proxy"]) for row in eligible if row["engagement_proxy"] is not None]
    complete = len(transcripts) == len(cohort) and len(frames) == len(cohort)
    return {
        "schema": "north-hux.youtube-census-analysis-summary.v1",
        "run_id": run_dir.name,
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "PASS_WITH_LIMITATIONS" if complete else "ACTIVE_PARTIAL",
        "claims_boundary": {
            "broad_screen_videos": len(cohort),
            "analysis_eligible_videos": len(eligible),
            "rule": "Strategic distributions use analysis_eligible_videos; collection completeness uses broad_screen_videos.",
        },
        "facts": {
            "creators": len(creator_counts),
            "videos": len(cohort),
            "min_videos_per_creator": min(creator_counts.values()) if creator_counts else 0,
            "max_videos_per_creator": max(creator_counts.values()) if creator_counts else 0,
            "max_creator_fraction": round(max(creator_counts.values()) / max(1, len(cohort)), 6),
            "format_states": dict(format_counts),
            "native_shorts_proved": sum(bool(row.get("native_short_proved")) for row in cohort),
            "transcript_attempts_observed_in_manifest": len(transcripts),
            "transcripts_observed": len(observed_transcripts),
            "transcript_gaps": sum(row.get("availability") != "observed" for row in transcripts.values()),
            "raw_transcript_segments": sum(int(row.get("segment_count") or 0) for row in observed_transcripts),
            "derolled_speech_segments": sum(int(row.get("speech_segment_count") or 0) for row in observed_transcripts),
            "frame_attempts_observed_in_manifest": len(frames),
            "frame_sets_observed": len(observed_frames),
            "frame_gaps": sum(row.get("status") != "observed" for row in frames.values()),
            "frames_observed": sum(len(row.get("frames") or []) for row in observed_frames),
            "baseline_comments_retrieved": len(source_comments),
        },
        "analysis_eligible_derived": {
            "topics": dict(Counter(row["primary_topic"] for row in eligible).most_common()),
            "video_types": dict(Counter(row["video_type"] for row in eligible).most_common()),
            "hook_types": dict(Counter(row["hook_type"] for row in eligible).most_common()),
            "hook_evidence_basis": dict(Counter(row["hook_evidence_basis"] for row in eligible).most_common()),
            "storytelling_styles": dict(Counter(row["storytelling_style"] for row in eligible).most_common()),
            "cta_types": dict(Counter(row["cta_type"] for row in eligible).most_common()),
            "median_views": median(views),
            "p90_views": percentile(views, 0.90),
            "median_engagement_proxy": median(engagement),
            "effective_coded_denominators": {
                "topics": sum(row["primary_topic"] != "general_ai_or_unresolved" for row in eligible),
                "video_types": sum(row["video_type"] != "unresolved" for row in eligible),
                "hooks": sum(row["hook_type"] != "unresolved" for row in eligible),
                "hooks_from_transcript": sum(row["hook_evidence_basis"] != "title_proxy" for row in eligible),
                "stories": sum(row["storytelling_style"] != "single_claim_or_unresolved" for row in eligible),
                "ctas": sum(row["cta_type"] != "unresolved" for row in eligible),
            },
        },
        "limitations": [
            "The 10,000-video corpus is a search-ranked broad screen, not 10,000 independently qualified competitors or a probability sample.",
            "Strategic distributions are restricted to the deterministic analysis-eligible subset and remain lexical classifications until independent review.",
            "YouTube short-duration metadata does not prove native Shorts placement; native Shorts proved remains a separate field.",
            "Transcript and frame denominators are reported independently; missing evidence is never converted to zero.",
            "Comments are inherited only from the bounded 300-account calibration and do not describe the full 10K audience.",
            "Public likes/comments are counts; viewer identities, shares, sends, saves, retention, impressions, and conversion remain unavailable.",
            "AI-generated visuals are excluded from source evidence and cannot validate observed video performance.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--source-run-dir", type=Path)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    cohort = load_jsonl(run_dir / "derived" / "video-cohort.jsonl")
    if len(cohort) != 10000:
        raise ValueError(f"expected exactly 10,000 cohort rows, got {len(cohort)}")
    cohort_ids = {row["native_video_id"] for row in cohort}
    if len(cohort_ids) != len(cohort):
        raise ValueError("cohort contains duplicate native_video_id values")
    creator_counts = Counter(row["native_channel_id"] for row in cohort)
    if max(creator_counts.values()) / len(cohort) > 0.01:
        raise ValueError("cohort violates the 1% maximum creator contribution")
    creator_views: dict[str, list[int]] = defaultdict(list)
    for row in cohort:
        if row.get("view_count") is not None:
            creator_views[row["native_channel_id"]].append(int(row["view_count"]))
    creator_medians = {
        creator_id: float(statistics.median(values)) if values else 0.0
        for creator_id, values in creator_views.items()
    }
    transcripts = load_transcripts(run_dir)
    frames = load_frame_manifests(run_dir)
    validate_evidence_identity(cohort_ids, transcripts, frames, allow_partial=args.allow_partial)
    analyzed = [
        classify_video(
            row,
            transcripts.get(row["native_video_id"], {}),
            frames.get(row["native_video_id"], {}),
            creator_medians.get(row["native_channel_id"], 0.0),
        )
        for row in cohort
    ]
    write_jsonl(run_dir / "derived" / "video-analysis-10k.jsonl", analyzed)
    per_creator: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in analyzed:
        per_creator[row["native_channel_id"]].append(row)
    account_rows = []
    for creator_id, rows in sorted(per_creator.items()):
        eligible = [row for row in rows if row["analysis_eligible"]]
        account_rows.append({
            "schema": "north-hux.youtube-account-analysis.v2",
            "native_channel_id": creator_id,
            "sample_video_count": len(rows),
            "analysis_eligible_video_count": len(eligible),
            "dominant_topic": Counter(row["primary_topic"] for row in eligible).most_common(1)[0][0] if eligible else "unresolved",
            "dominant_video_type": Counter(row["video_type"] for row in eligible).most_common(1)[0][0] if eligible else "unresolved",
            "median_views": median([row["views"] for row in eligible]),
            "median_engagement_proxy": median([row["engagement_proxy"] for row in eligible]),
            "transcript_coverage": round(sum(row["transcript_availability"] == "observed" for row in rows) / len(rows), 4),
            "frame_coverage": round(sum(row["frame_state"] == "observed" for row in rows) / len(rows), 4),
        })
    write_jsonl(run_dir / "derived" / "account-analysis-10k.jsonl", account_rows)
    top_references = select_top_references(analyzed, 100)
    write_jsonl(run_dir / "derived" / "top-reference-cohort-10k.jsonl", top_references)
    source_comments = load_jsonl(args.source_run_dir / "derived" / "comments.jsonl") if args.source_run_dir else []
    summary = build_summary(run_dir, cohort, analyzed, transcripts, frames, source_comments)
    atomic_write_text(
        run_dir / "derived" / "analysis-summary-10k.json",
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    print(json.dumps(summary["claims_boundary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
