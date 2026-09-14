"""Bounded, scene-specific frame evidence for independently reviewed candidates.

Scene annotations are interpretations supplied by another lane.  This module
only validates their transcript/source binding, maps their 2/4/6 sample plans
to the retained decoded PTS list, and performs one bounded indexed decode for
the union of all requested frame indices.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from m2_studio.media import (
    StudioError,
    align_scenes,
    build_collage,
    digest,
    object_hash,
    sampling_pts,
    write_json,
)

from .media_visual import MAX_FRAMES, OUTPUT_FILE_LIMIT, _extract_indexed_frames


MAX_COLLAGE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_OUTPUT_BYTES = 64 * 1024 * 1024
ALLOWED_ALIAS_PATHS = {"/tmp", "/private/tmp", "/var", "/private/var"}
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class SceneMediaError(ValueError):
    """Stable, sanitized failure code for scene evidence preparation."""


def _reject_symlink_ancestors(path: Path, code: str = "OUTPUT_SYMLINK_UNSAFE") -> None:
    absolute = path.absolute()
    for ancestor in (absolute, *absolute.parents):
        if ancestor.is_symlink() and str(ancestor) not in ALLOWED_ALIAS_PATHS:
            raise SceneMediaError(code)


def _safe_output_dir(path: Path) -> Path:
    """Require a new output directory with a non-symlinked lexical ancestry."""

    if path.is_symlink() or path.exists():
        raise SceneMediaError("OUTPUT_ALREADY_EXISTS")
    _reject_symlink_ancestors(path)
    parent = path.parent.absolute()
    if not parent.is_dir():
        raise SceneMediaError("OUTPUT_PARENT_UNAVAILABLE")
    return path


def _safe_source_pointer(root: Path, pointer: Any) -> Path:
    if not isinstance(pointer, str) or not pointer or Path(pointer).is_absolute() or "\\" in pointer or ".." in Path(pointer).parts:
        raise SceneMediaError("SOURCE_POINTER_INVALID")
    lexical = root.absolute() / pointer
    _reject_symlink_ancestors(root, "SOURCE_SYMLINK_UNSAFE")
    _reject_symlink_ancestors(lexical, "SOURCE_SYMLINK_UNSAFE")
    if lexical.is_symlink():
        raise SceneMediaError("SOURCE_SYMLINK_UNSAFE")
    try:
        resolved_root = root.resolve(strict=True)
        source = lexical.resolve(strict=True)
        source.relative_to(resolved_root)
    except (OSError, ValueError):
        raise SceneMediaError("SOURCE_PATH_INVALID") from None
    if not source.is_file():
        raise SceneMediaError("SOURCE_UNAVAILABLE")
    return source


def _validate_media(root: Path, media: Mapping[str, Any]) -> tuple[Path, int, list[int], str]:
    if not isinstance(media, Mapping):
        raise SceneMediaError("MEDIA_RECORD_INVALID")
    if media.get("observation_state") != "OBSERVED":
        raise SceneMediaError("MEDIA_NOT_OBSERVED")
    rights = media.get("rights")
    if not isinstance(rights, Mapping) or rights.get("analysis_allowed") is not True or not rights.get("receipt_id"):
        raise SceneMediaError("RIGHTS_BLOCKED")
    source_hash = media.get("sha256")
    if not isinstance(source_hash, str) or not HEX64.fullmatch(source_hash):
        raise SceneMediaError("MEDIA_HASH_MISSING")
    try:
        duration_ms = media["duration_ms"]
        pts = media["frame_pts_ms"]
    except KeyError:
        raise SceneMediaError("FRAME_PTS_UNAVAILABLE") from None
    if type(duration_ms) is not int or duration_ms <= 0:
        raise SceneMediaError("MEDIA_DURATION_INVALID")
    if not isinstance(pts, list) or not pts or any(type(item) is not int for item in pts):
        raise SceneMediaError("FRAME_PTS_INVALID")
    if pts[0] != 0 or pts[-1] >= duration_ms or any(right <= left for left, right in zip(pts, pts[1:])):
        raise SceneMediaError("FRAME_PTS_INVALID")
    source = _safe_source_pointer(root, media.get("source_pointer"))
    if digest(source) != source_hash:
        raise SceneMediaError("MEDIA_HASH_MISMATCH")
    return source, duration_ms, pts, source_hash


def _frame_entry(scene: Mapping[str, Any], sample: Mapping[str, Any], ordinal: int, source_hash: str, pts_hash: str) -> dict[str, Any]:
    scene_id = scene["scene_id"]
    return {
        "frame_id": f"{scene_id}-F{ordinal:02}",
        "scene_id": scene_id,
        "sample_type": "scene_sample",
        "role": sample["role"],
        "frame_index": sample["frame_index"],
        "decoded_frame_index": sample["frame_index"],
        "timestamp_ms": sample["timestamp_ms"],
        "timestamp_source": "decoded_frame_pts_ms",
    "source_media_hash": source_hash,
        "source_frame_pts_sha256": pts_hash,
        "observation_state": "PENDING",
        "failure_code": None,
    }


def extract_scene_media(
    root: str | Path,
    media: Mapping[str, Any],
    transcript: Mapping[str, Any],
    annotations: list[Mapping[str, Any]],
    output: str | Path,
) -> dict[str, Any]:
    """Extract all planned scene frames in one bounded decode.

    The output is created only after source, rights, transcript, scene
    partition, sample counts, and the global decoded-index budget validate.
    Each annotation remains a candidate; no semantic scene or shot is
    accepted here.
    """

    root_path = Path(root)
    try:
        source, duration_ms, pts, source_hash = _validate_media(root_path, media)
        if not isinstance(transcript, Mapping) or not isinstance(annotations, list):
            raise SceneMediaError("SCENE_INPUT_INVALID")
        aligned = align_scenes(list(annotations), dict(transcript), duration_ms, source_media_hash=source_hash)
    except SceneMediaError:
        raise
    except StudioError as exc:
        raise SceneMediaError(str(exc)) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise SceneMediaError(str(exc) or "SCENE_INPUT_INVALID") from exc

    output_path = _safe_output_dir(Path(output))
    planned_frames: list[dict[str, Any]] = []
    scene_plans: list[dict[str, Any]] = []
    used_indices: set[int] = set()
    pts_hash = object_hash(pts)
    for scene in aligned:
        scene_id = scene["scene_id"]
        try:
            samples = sampling_pts(scene, pts)
        except StudioError as exc:
            raise SceneMediaError(str(exc)) from exc
        frames = []
        for ordinal, sample in enumerate(samples, start=1):
            index = sample["frame_index"]
            if index in used_indices:
                raise SceneMediaError("DUPLICATE_DECODED_FRAME_INDEX")
            used_indices.add(index)
            frame = _frame_entry(scene, sample, ordinal, source_hash, pts_hash)
            frames.append(frame)
            planned_frames.append(frame)
        scene_plans.append({"scene": scene, "frames": frames})
    if not planned_frames or len(planned_frames) > MAX_FRAMES:
        raise SceneMediaError("FRAME_BUDGET_EXCEEDED")

    output_path.mkdir(parents=True, exist_ok=False)
    resources: list[dict[str, Any]] = []
    try:
        extracted = _extract_indexed_frames(source, output_path, planned_frames, resources)
    except (OSError, SceneMediaError, ValueError) as exc:
        code = str(exc) if isinstance(exc, SceneMediaError) else "FRAME_DECODE_FAILED"
        for frame in planned_frames:
            frame.update({"observation_state": "UNAVAILABLE", "failure_code": code})
        extracted = planned_frames

    by_id = {frame["frame_id"]: frame for frame in extracted}
    scene_results: list[dict[str, Any]] = []
    for item in scene_plans:
        scene = item["scene"]
        frames = [by_id[frame["frame_id"]] for frame in item["frames"]]
        observed = [frame for frame in frames if frame.get("observation_state") == "OBSERVED"]
        frame_failures = [
            {"frame_id": frame["frame_id"], "frame_index": frame["frame_index"], "timestamp_ms": frame["timestamp_ms"],
             "failure_code": frame.get("failure_code") or "FRAME_NOT_EMITTED", "observation_state": frame.get("observation_state")}
            for frame in frames if frame.get("observation_state") != "OBSERVED"
        ]
        collage: dict[str, Any]
        if observed:
            try:
                collage = build_collage(observed, output_path, f"{scene['scene_id']}-collage.jpg")
                collage_path = output_path / f"{scene['scene_id']}-collage.jpg"
                if collage.get("observation_state") == "OBSERVED" and (not collage_path.is_file() or collage_path.is_symlink() or collage_path.stat().st_size > MAX_COLLAGE_BYTES):
                    collage = {"observation_state": "UNAVAILABLE", "failure_code": "COLLAGE_SIZE_LIMIT", "sample_count": len(observed)}
            except (OSError, StudioError, ValueError):
                collage = {"observation_state": "UNAVAILABLE", "failure_code": "COLLAGE_BUILD_FAILED", "sample_count": len(observed)}
        else:
            collage = {"observation_state": "UNAVAILABLE", "failure_code": "NO_OBSERVED_FRAMES", "sample_count": 0}
        if len(observed) == len(frames) and collage.get("observation_state") == "OBSERVED":
            state = "OBSERVED"
        elif observed:
            state = "PARTIAL"
        else:
            state = "UNAVAILABLE"
        scene_results.append({
            "scene_id": scene["scene_id"],
            "start_ms": scene["start_ms"],
            "end_ms": scene["end_ms"],
            "planned_sample_count": scene["sample_count"],
            "observed_frame_count": len(observed),
            "frame_observation_state": "OBSERVED" if len(observed) == len(frames) else "PARTIAL" if observed else "UNAVAILABLE",
            "frame_failures": frame_failures,
            "sampled_frames": observed,
            "frame_attempts": frames,
            "collage": collage,
            "observation_state": state,
            "review_state": "REVIEW_PENDING",
        })

    files = [path for path in output_path.iterdir() if path.is_file() and not path.is_symlink()]
    total_bytes = sum(path.stat().st_size for path in files)
    if total_bytes > MAX_TOTAL_OUTPUT_BYTES:
        for scene in scene_results:
            scene["observation_state"] = "PARTIAL"
            scene["failure_code"] = "OUTPUT_TOTAL_SIZE_LIMIT"
            scene.setdefault("limitations", []).append("OUTPUT_TOTAL_SIZE_LIMIT")
    observed_count = sum(scene["observed_frame_count"] for scene in scene_results)
    attempted_count = len(planned_frames)
    frame_state = "OBSERVED" if observed_count == attempted_count else "PARTIAL" if observed_count else "UNAVAILABLE"
    scene_state = "OBSERVED" if all(scene["observation_state"] == "OBSERVED" for scene in scene_results) else "PARTIAL" if any(scene["observation_state"] in {"OBSERVED", "PARTIAL"} for scene in scene_results) else "UNAVAILABLE"
    result: dict[str, Any] = {
        "schema": "m2.scene-media-evidence.v1",
        "source_media_hash": source_hash,
        "source_pointer": media["source_pointer"],
        "source_frame_pts_sha256": pts_hash,
        "duration_ms": duration_ms,
        "transcript_sha256": object_hash(dict(transcript)),
        "transcript_source_media_hash": transcript.get("source_media_hash"),
        "annotations_sha256": object_hash(list(annotations)),
        "scene_count": len(scene_results),
        "scene_units": scene_results,
        "observation_state": scene_state,
        "frame_observation_state": frame_state,
        "planned_frame_count": attempted_count,
        "observed_frame_count": observed_count,
        "frame_budget": {"max_frames": MAX_FRAMES, "planned_frames": attempted_count, "observed_frames": observed_count},
        "frame_index_policy": "exact_decoded_pts_indices_one_global_decode_no_duplicate_indices",
        "resources": resources,
        "output_bytes": {"total": total_bytes, "per_frame_limit": OUTPUT_FILE_LIMIT, "per_collage_limit": MAX_COLLAGE_BYTES, "total_limit": MAX_TOTAL_OUTPUT_BYTES},
        "rights": dict(media["rights"]),
        "public_display_allowed": False,
        "retention": {"source_video": "RETAINED", "source_media_hash": source_hash},
        "review_state": "REVIEW_PENDING",
        "semantic_scene_state": "CANDIDATE_NOT_ACCEPTED",
        "limitations": ["Scene annotations remain independent semantic candidates; this adapter emits technical frame evidence only.", "Planned and observed counts are reported separately.", "No audio or transcript accuracy claim is made by frame extraction."],
    }
    result["manifest_sha256"] = object_hash(result)
    write_json(output_path / "receipt.json", result)
    return result


__all__ = ["SceneMediaError", "extract_scene_media"]
