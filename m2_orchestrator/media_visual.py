"""Bounded local visual evidence for later independent review.

This module deliberately stops at evidence collection. FFmpeg scene events are
cut *candidates*; they are not shots or semantic scenes. The source video is
never moved or deleted, and every emitted frame remains linked to the source
media hash, decoded frame index and normalized decoded timestamp.
"""
from __future__ import annotations

import bisect
import re
from pathlib import Path

from m2_studio.media import build_collage, digest, object_hash, observed_source, sampling_pts, write_json
from .process_budget import ProcessBudgetError, bounded_process

MAX_DURATION_MS = 180_000
MAX_FRAMES = 48
DEFAULT_MAX_FRAMES = 24
THUMB_WIDTH = 480
OUTPUT_FILE_LIMIT = 2 * 1024 * 1024
STDOUT_LIMIT = 64 * 1024
STDERR_LIMIT = 2 * 1024 * 1024
RSS_LIMIT_BYTES = 512 * 1024 * 1024
FFMPEG_TIMEOUT_SECONDS = 120
MIN_CUT_SEPARATION_MS = 120


class VisualExtractionError(ValueError):
    """Stable, sanitized visual-extraction failure code."""


def _safe_output_dir(output: Path) -> Path:
    """Refuse overwrite and symlinked output directories."""
    if output.is_symlink() or any(p.is_symlink() and str(p) not in {'/tmp', '/var'} for p in output.absolute().parents):
        raise VisualExtractionError("OUTPUT_SYMLINK_UNSAFE")
    if output.exists():
        raise VisualExtractionError("OUTPUT_ALREADY_EXISTS")
    parent = output.parent.resolve()
    if not parent.is_dir():
        raise VisualExtractionError("OUTPUT_PARENT_UNAVAILABLE")
    return parent / output.name


def _safe_target(output: Path, filename: str) -> Path:
    """Return a new file target confined to the freshly-created output dir."""
    if not isinstance(filename, str) or not filename or Path(filename).name != filename:
        raise VisualExtractionError("INVALID_OUTPUT_POINTER")
    target = output / filename
    if target.exists() or target.is_symlink():
        raise VisualExtractionError("OUTPUT_FILE_EXISTS")
    if target.resolve().parent != output.resolve():
        raise VisualExtractionError("OUTPUT_PATH_ESCAPE")
    return target


def _run_ffmpeg(args: list[str], receipts: list[dict], *, stage: str) -> dict:
    """Run exactly one bounded process and retain a public-safe resource receipt."""
    try:
        result = bounded_process(args, timeout=FFMPEG_TIMEOUT_SECONDS, stdout_limit=STDOUT_LIMIT,
                                 stderr_limit=STDERR_LIMIT, rss_limit_bytes=RSS_LIMIT_BYTES)
    except ProcessBudgetError as exc:
        receipts.append({"stage": stage, "failure_code": str(exc), "process_started": None})
        raise VisualExtractionError(str(exc)) from exc
    except OSError as exc:
        # A restricted runtime may be unable to invoke its RSS sampler. Keep
        # the per-stage failure typed and sanitized so the Reel is still
        # resumable and never gets an accidental success claim.
        receipts.append({"stage": stage, "failure_code": "PROCESS_BUDGET_RUNTIME_UNAVAILABLE", "process_started": None})
        raise VisualExtractionError("PROCESS_BUDGET_RUNTIME_UNAVAILABLE") from exc
    receipts.append({"stage": stage, "returncode": result["returncode"],
                     "elapsed_seconds": result.get("elapsed_seconds"),
                     "sampled_peak_rss_bytes": result.get("sampled_peak_rss_bytes"),
                     "rss_watchdog_limit_bytes": RSS_LIMIT_BYTES,
                     "rss_poll_seconds": result.get("rss_poll_seconds", 0.2),
                     "threads": 2, "timeout_seconds": FFMPEG_TIMEOUT_SECONDS})
    if result["returncode"]:
        raise VisualExtractionError("VISUAL_DECODE_FAILED")
    return result


def _cut_times(log: bytes, duration_ms: int) -> list[int]:
    """Parse and deduplicate FFmpeg scene-score timestamps."""
    values = []
    for value in re.findall(rb"pts_time:([0-9.eE+-]+)", log):
        try:
            timestamp = round(float(value.decode("ascii")) * 1000)
        except (UnicodeDecodeError, ValueError, OverflowError):
            continue
        if 0 < timestamp < duration_ms:
            values.append(timestamp)
    kept: list[int] = []
    for timestamp in sorted(set(values)):
        if not kept or timestamp - kept[-1] >= MIN_CUT_SEPARATION_MS:
            kept.append(timestamp)
    return kept


def _frame_for_cut(pts: list[int], cut_ms: int) -> tuple[int | None, int | None]:
    """Map a cut event to the nearest decoded frame before and after it."""
    after_pos = bisect.bisect_left(pts, cut_ms)
    after = after_pos if after_pos < len(pts) else None
    before = after_pos - 1 if after_pos > 0 else None
    return before, after


def _sample_entry(*, frame_index: int, timestamp_ms: int, sample_type: str,
                  ordinal: int, source_media_hash: str) -> dict:
    if sample_type not in {"regular", "cut_before", "cut_after"}:
        raise VisualExtractionError("INVALID_SAMPLE_TYPE")
    return {"frame_id": f"F{ordinal:03}", "sample_type": sample_type,
            "frame_index": frame_index, "decoded_frame_index": frame_index,
            "timestamp_ms": timestamp_ms, "timestamp_source": "decoded_frame_pts_ms",
            "role": sample_type, "source_media_hash": source_media_hash,
            "observation_state": "PENDING", "failure_code": None}


def _extract_indexed_frames(source: Path, output: Path, frames: list[dict], receipts: list[dict]) -> list[dict]:
    """Decode all requested indices in one FFmpeg process and map outputs exactly."""
    if not frames:
        return []
    ordered = sorted(frames, key=lambda item: item["frame_index"])
    clauses = "+".join(f"eq(n\\,{item['frame_index']})" for item in ordered)
    args = ["ffmpeg", "-v", "error", "-nostdin", "-n", "-threads", "2", "-filter_threads", "2",
            "-protocol_whitelist", "file,pipe", "-i", str(source), "-an", "-vf",
            f"select='{clauses}',scale={THUMB_WIDTH}:-2", "-fps_mode", "vfr", "-q:v", "2",
            str(output / "decoded-%03d.jpg")]
    try:
        result = _run_ffmpeg(args, receipts, stage="frame_decode")
    except VisualExtractionError as exc:
        for frame in frames:
            frame["observation_state"] = "UNAVAILABLE"
            frame["failure_code"] = str(exc)
        return frames
    expected = {f"decoded-{position:03d}.jpg" for position in range(1, len(ordered)+1)}
    actual = {p.name for p in output.glob('decoded-*.jpg')}
    # A positional mapping is admissible only for an exact complete output
    # sequence. A missing middle output must never shift later frame identities.
    if actual != expected:
        for frame in frames:
            frame.update(observation_state="UNAVAILABLE", failure_code="DECODED_SEQUENCE_MISMATCH")
        return frames
    for position, frame in enumerate(ordered, start=1):
        target = output / f"decoded-{position:03d}.jpg"
        if not target.is_file() or target.is_symlink() or not 0 < target.stat().st_size <= OUTPUT_FILE_LIMIT:
            frame["observation_state"] = "UNAVAILABLE"
            frame["failure_code"] = "FRAME_OUTPUT_INVALID"
            continue
        final_name = f"{frame['frame_id']}.jpg"
        try:
            final_target = _safe_target(output, final_name)
            target.replace(final_target)
        except (OSError, VisualExtractionError) as exc:
            frame["observation_state"] = "UNAVAILABLE"
            frame["failure_code"] = str(exc) if isinstance(exc, VisualExtractionError) else "FRAME_RENAME_FAILED"
            continue
        frame.update({"observation_state": "OBSERVED", "failure_code": None,
                      "source_pointer": final_name, "sha256": digest(final_target),
                      "width_px": THUMB_WIDTH})
    return frames


def extract_preview(root, media, output, *, count=6, threshold=0.32, max_frames=DEFAULT_MAX_FRAMES):
    """Extract regular and visual-change evidence for one retained local Reel.

    ``count`` controls the regular whole-clip preview (2, 4 or 6 frames).
    Scene-score events produce optional adjacent ``cut_before``/``cut_after``
    candidates until ``max_frames`` is reached. Every candidate remains
    review-pending; this function never labels a shot or semantic scene.
    """
    if count not in {2, 4, 6} or not 0 < threshold < 1:
        raise VisualExtractionError("INVALID_VISUAL_PARAMETERS")
    if type(max_frames) is not int or not count <= max_frames <= MAX_FRAMES:
        raise VisualExtractionError("INVALID_FRAME_BUDGET")
    output = _safe_output_dir(Path(output))
    source = observed_source(Path(root), media)
    duration_ms, pts = media.get("duration_ms"), media.get("frame_pts_ms")
    if not isinstance(duration_ms, int) or not 0 < duration_ms <= MAX_DURATION_MS:
        raise VisualExtractionError("MEDIA_DURATION_LIMIT")
    if not isinstance(pts, list) or not pts or any(type(item) is not int for item in pts):
        raise VisualExtractionError("FRAME_PTS_UNAVAILABLE")
    if pts[0] != 0 or pts[-1] >= duration_ms or any(b <= a for a,b in zip(pts,pts[1:])):
        raise VisualExtractionError("FRAME_PTS_INVALID")

    output.mkdir(parents=True)
    receipts: list[dict] = []
    regular = sampling_pts({"start_ms": 0, "end_ms": duration_ms, "sample_count": count}, pts)
    frames: list[dict] = []
    used_indices: set[int] = set()
    for item in regular:
        used_indices.add(item["frame_index"])
        frames.append(_sample_entry(frame_index=item["frame_index"], timestamp_ms=item["timestamp_ms"],
                                    sample_type="regular", ordinal=len(frames) + 1,
                                    source_media_hash=media["sha256"]))

    cut_candidates: list[int] = []
    cut_failure: str | None = None
    cut_args = ["ffmpeg", "-v", "info", "-nostdin", "-threads", "2", "-filter_threads", "2",
                "-protocol_whitelist", "file,pipe", "-i", str(source), "-an", "-vf",
                f"setpts=PTS-STARTPTS,select='gt(scene,{threshold})',showinfo", "-f", "null", "-"]
    try:
        cut_result = _run_ffmpeg(cut_args, receipts, stage="cut_detection")
        cut_candidates = _cut_times(cut_result["stderr"], duration_ms)
    except VisualExtractionError as exc:
        cut_failure = str(exc)

    cut_pairs: list[dict] = []
    truncated = False
    for cut_number, cut_ms in enumerate(cut_candidates, start=1):
        before, after = _frame_for_cut(pts, cut_ms)
        pair = {"cut_id": f"C{cut_number:04}", "timestamp_ms": cut_ms,
                "candidate_type": "unknown_change", "review_state": "REVIEW_PENDING",
                "confirmed_type": None, "before_frame_index": before, "after_frame_index": after,
                "sample_types_emitted": [], "sample_types_omitted": [], "omission_reasons": {}}
        for index, sample_type in ((before, "cut_before"), (after, "cut_after")):
            if index is None:
                pair["sample_types_omitted"].append(sample_type)
                pair["omission_reasons"][sample_type] = "NO_ADJACENT_DECODED_FRAME"
                continue
            if index in used_indices:
                pair["sample_types_omitted"].append(sample_type)
                pair["omission_reasons"][sample_type] = "DUPLICATE_DECODED_FRAME"
                continue
            if len(frames) >= max_frames:
                truncated = True
                pair["sample_types_omitted"].append(sample_type)
                pair["omission_reasons"][sample_type] = "FRAME_BUDGET_EXHAUSTED"
                continue
            used_indices.add(index)
            frames.append(_sample_entry(frame_index=index, timestamp_ms=pts[index], sample_type=sample_type,
                                        ordinal=len(frames) + 1, source_media_hash=media["sha256"]))
            pair["sample_types_emitted"].append(sample_type)
        cut_pairs.append(pair)

    frames = _extract_indexed_frames(source, output, frames, receipts)
    observed_frames = [frame for frame in frames if frame["observation_state"] == "OBSERVED"]
    failures = [{"frame_id": frame["frame_id"], "sample_type": frame["sample_type"],
                 "frame_index": frame["frame_index"], "timestamp_ms": frame["timestamp_ms"],
                 "failure_code": frame["failure_code"] or "FRAME_NOT_EMITTED",
                 "observation_state": frame["observation_state"]}
                for frame in frames if frame["observation_state"] != "OBSERVED"]
    frame_state = "OBSERVED" if len(observed_frames) == len(frames) else "PARTIAL" if observed_frames else "DECODE_FAILED"
    cut_state = "DECODE_FAILED" if cut_failure else "OBSERVED"
    limitations = ["Cut candidates are technical events, not confirmed shots or semantic scenes.",
                   "Semantic scene interpretation and review remain pending.",
                   "Visual-change sampling is capped by the declared frame budget."]
    if truncated:
        limitations.append("Visual-change candidates were truncated after the frame budget was reached.")
    if cut_failure:
        limitations.append("Cut detection failed; regular whole-clip frames were attempted independently.")
    if failures:
        limitations.append("One or more requested frame files were unavailable; see frame_failures.")

    emitted_bytes = sum(
        item.stat().st_size for item in output.iterdir()
        if item.is_file() and not item.is_symlink() and item.name != "receipt.json"
    )
    result = {"schema": "m2.visual-preview.v2", "source_media_hash": media["sha256"],
              "reel_id": media.get("reel_id"), "duration_ms": duration_ms,
              "frame_observation_state": frame_state, "cut_observation_state": cut_state,
              "semantic_scene_state": "NOT_REVIEWED", "confirmed_shot_count": None,
              "cut_candidates_ms": cut_candidates, "cut_candidates": cut_pairs,
              "cut_detector": {"name": "ffmpeg_scene_score", "threshold": threshold,
                               "min_separation_ms": MIN_CUT_SEPARATION_MS, "failure_code": cut_failure},
              "sampled_frames": observed_frames, "frame_attempts": frames, "frame_failures": failures,
              "sampling_policy": "whole_clip_regular_2_4_6_plus_visual_change_adjacent_frames",
              "frame_budget": {"max_frames": max_frames, "requested_frames": len(frames),
                               "observed_frames": len(observed_frames), "truncated": truncated},
              "cut_sampling_disclosure": {
                  "detected_cut_candidates": len(cut_candidates),
                  "candidates_with_emitted_change_frames": sum(bool(item["sample_types_emitted"]) for item in cut_pairs),
                  "unsampled_cut_ids": [item["cut_id"] for item in cut_pairs if not item["sample_types_emitted"]],
                  "truncated": truncated,
              },
              "collage": build_collage(observed_frames, output, "preview-collage.jpg") if observed_frames else
                         {"observation_state": "UNAVAILABLE", "failure_code": "NO_OBSERVED_FRAMES", "sample_count": 0},
              "resources": receipts,
              "output_bytes": {"evidence_files_total": emitted_bytes, "per_file_limit": OUTPUT_FILE_LIMIT},
              "retention": {"source_video": "RETAINED", "source_media_hash": media["sha256"]},
              "rights": media.get("rights", {}), "public_display_allowed": False,
              "review_state": "REVIEW_PENDING", "limitations": limitations}
    collage = output/'preview-collage.jpg'
    if collage.is_file() and collage.stat().st_size > 16*1024**2:
        result['collage'] = {'observation_state':'UNAVAILABLE','failure_code':'COLLAGE_SIZE_LIMIT','sample_count':len(observed_frames)}
        result['limitations'].append('Collage exceeds the 16 MiB acceptance limit; retained individual frames remain available.')
    result['output_bytes']['evidence_files_total'] = sum(p.stat().st_size for p in output.iterdir() if p.is_file() and not p.is_symlink() and p.name != 'receipt.json')
    result['output_bytes']['collage_limit'] = 16*1024**2
    result["manifest_sha256"] = object_hash(result)
    write_json(output / "receipt.json", result)
    return result


__all__ = ["VisualExtractionError", "extract_preview"]
