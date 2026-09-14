"""Deterministic media pipeline primitives.

This module intentionally does not call an AI provider. An AI/Codex analysis
is represented as a JSON analysis artifact, reviewed, and converted to the
canonical EDL before any FFmpeg process is allowed to run.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class PipelineError(RuntimeError):
    """A typed, fail-closed pipeline error."""


SCHEMA_EDL = "archflow.edit-decision-list.v1"
SCHEMA_CASE = "archflow.edit-pipeline-case.v1"
APPROVED_RIGHTS = {"owner_owned_approved", "licensed_approved"}
COLOR_PRESETS = {"none", "neutral", "warm", "cool"}
AUDIO_PRESETS = {"none", "loudnorm", "dynaudnorm"}


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)


def write_json(path: str | Path, value: Mapping[str, Any]) -> Path:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_json(value) + "\n", encoding="utf-8")
    return target


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _run(command: Sequence[str], *, timeout: float = 180.0) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PipelineError(f"MEDIA_TOOL_FAILED: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown media-tool error").strip()
        raise PipelineError(f"MEDIA_TOOL_FAILED: {detail[-1600:]}")
    return result


def _require_file(path: str | Path, label: str) -> Path:
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise PipelineError(f"{label}_NOT_FOUND: {target}")
    return target


def _within(path: Path, roots: Iterable[str | Path]) -> bool:
    candidate = path.resolve()
    for root in roots:
        try:
            candidate.relative_to(Path(root).expanduser().resolve())
            return True
        except ValueError:
            continue
    return False


def _fps(value: str | None) -> float:
    if not value or value in {"0/0", "N/A"}:
        return 30.0
    try:
        parsed = float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        return 30.0
    return round(parsed, 6) if parsed > 0 else 30.0


def probe_media(path: str | Path, *, ffprobe_bin: str = "ffprobe") -> dict[str, Any]:
    """Return stream metadata and a content hash without modifying media."""

    source = _require_file(path, "SOURCE")
    result = _run(
        [
            ffprobe_bin,
            "-v",
            "error",
            "-show_entries",
            "format=format_name,duration,size:stream=index,codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels,duration",
            "-of",
            "json",
            str(source),
        ]
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise PipelineError("FFPROBE_INVALID_JSON") from exc
    streams = payload.get("streams") or []
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    if not video:
        raise PipelineError("SOURCE_HAS_NO_VIDEO_STREAM")
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    format_info = payload.get("format") or {}
    duration_raw = format_info.get("duration") or video.get("duration")
    try:
        duration = float(duration_raw)
    except (TypeError, ValueError) as exc:
        raise PipelineError("SOURCE_DURATION_UNKNOWN") from exc
    if duration <= 0:
        raise PipelineError("SOURCE_DURATION_INVALID")
    return {
        "path": str(source),
        "sha256": sha256_file(source),
        "duration_seconds": round(duration, 6),
        "format_name": format_info.get("format_name"),
        "size_bytes": int(format_info.get("size") or source.stat().st_size),
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "fps": _fps(video.get("avg_frame_rate")),
        "video_codec": video.get("codec_name"),
        "has_audio": audio is not None,
        "audio_codec": audio.get("codec_name") if audio else None,
        "audio_sample_rate": int(audio.get("sample_rate") or 0) if audio else None,
        "audio_channels": int(audio.get("channels") or 0) if audio else None,
    }


def _require_roots(case: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    execution = case.get("execution") or {}
    media_roots = [str(x) for x in execution.get("allowed_media_roots") or []]
    output_roots = [str(x) for x in execution.get("allowed_output_roots") or []]
    if not media_roots or not output_roots:
        raise PipelineError("PATH_POLICY_MISSING_ROOTS")
    return media_roots, output_roots


def validate_case(
    case: Mapping[str, Any],
    *,
    source_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> None:
    """Validate rights, path, provider, and execution gates before rendering."""

    if case.get("schema") != SCHEMA_CASE:
        raise PipelineError("CASE_SCHEMA_UNSUPPORTED")
    if not case.get("case_id"):
        raise PipelineError("CASE_ID_MISSING")
    rights = case.get("rights") or {}
    status = rights.get("status")
    if status not in APPROVED_RIGHTS | {"synthetic_fixture"}:
        raise PipelineError("RIGHTS_NOT_APPROVED")
    if status == "owner_owned_approved" and rights.get("consent") != "approved":
        raise PipelineError("CONSENT_MISSING")
    if status == "licensed_approved" and rights.get("consent") not in {"approved", "not_required"}:
        raise PipelineError("CONSENT_MISSING")
    execution = case.get("execution") or {}
    if execution.get("allow_local_render") is not True:
        raise PipelineError("LOCAL_RENDER_NOT_APPROVED")
    policy = case.get("policy") or {}
    if policy.get("provider_execution") is not False:
        raise PipelineError("PROVIDER_EXECUTION_MUST_BE_DISABLED")
    if policy.get("generative_repair") not in {"disabled", "approved_exception"}:
        raise PipelineError("GENERATIVE_REPAIR_POLICY_INVALID")
    if policy.get("resolve_finishing") not in {"optional", "approved"}:
        raise PipelineError("RESOLVE_FINISHING_POLICY_INVALID")
    media_roots, output_roots = _require_roots(case)
    if source_path is not None:
        source = Path(source_path).expanduser().resolve()
        if not _within(source, media_roots):
            raise PipelineError("SOURCE_PATH_OUTSIDE_ALLOWLIST")
    if output_path is not None:
        output = Path(output_path).expanduser().resolve()
        if not _within(output, output_roots):
            raise PipelineError("OUTPUT_PATH_OUTSIDE_ALLOWLIST")


def _number(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise PipelineError(f"EDL_{name.upper()}_INVALID") from exc
    if result < 0:
        raise PipelineError(f"EDL_{name.upper()}_NEGATIVE")
    return result


def validate_edl(edl: Mapping[str, Any], *, verify_source_hash: bool = True) -> None:
    """Fail closed on malformed timecodes, policies, captions, or source drift."""

    if edl.get("schema") != SCHEMA_EDL:
        raise PipelineError("EDL_SCHEMA_UNSUPPORTED")
    source = edl.get("source") or {}
    source_path = _require_file(source.get("path", ""), "SOURCE")
    expected_hash = str(source.get("sha256") or "")
    if verify_source_hash and expected_hash and sha256_file(source_path) != expected_hash:
        raise PipelineError("SOURCE_HASH_MISMATCH")
    duration = _number(source.get("duration_seconds"), "source_duration")
    segments = edl.get("segments") or []
    if not segments:
        raise PipelineError("EDL_HAS_NO_SEGMENTS")
    cursor = 0.0
    source_seen: set[str] = set()
    for segment in segments:
        segment_id = str(segment.get("id") or "")
        if not segment_id or segment_id in source_seen:
            raise PipelineError("EDL_SEGMENT_ID_INVALID_OR_DUPLICATE")
        source_seen.add(segment_id)
        start = _number(segment.get("source_start"), "source_start")
        end = _number(segment.get("source_end"), "source_end")
        timeline_start = _number(segment.get("timeline_start"), "timeline_start")
        timeline_duration = _number(segment.get("timeline_duration"), "timeline_duration")
        if end <= start or end > duration + 0.02:
            raise PipelineError("EDL_SOURCE_TIME_RANGE_INVALID")
        if abs(timeline_start - cursor) > 0.02:
            raise PipelineError("EDL_TIMELINE_NOT_CONTIGUOUS")
        if abs(timeline_duration - (end - start)) > 0.02:
            raise PipelineError("EDL_DURATION_MISMATCH")
        cursor = timeline_start + timeline_duration
        repair = segment.get("repair")
        if repair:
            policy = edl.get("policy") or {}
            if policy.get("generative_repair") != "approved_exception" or repair.get("approval") != "approved":
                raise PipelineError("GENERATIVE_REPAIR_NOT_APPROVED")
            if repair.get("provider_execution") is not False:
                raise PipelineError("REPAIR_PROVIDER_EXECUTION_NOT_DISABLED")
    timeline = edl.get("timeline") or {}
    if abs(_number(timeline.get("duration_seconds"), "timeline_duration") - cursor) > 0.02:
        raise PipelineError("EDL_TIMELINE_DURATION_MISMATCH")
    if _number(timeline.get("fps"), "fps") <= 0:
        raise PipelineError("EDL_FPS_INVALID")
    style = edl.get("style") or {}
    if style.get("color_preset") not in COLOR_PRESETS:
        raise PipelineError("COLOR_PRESET_INVALID")
    if style.get("audio_leveling") not in AUDIO_PRESETS:
        raise PipelineError("AUDIO_LEVELING_INVALID")
    captions = edl.get("captions") or {}
    if captions.get("mode") not in {"none", "embedded_text_track", "sidecar_srt"}:
        raise PipelineError("CAPTION_MODE_INVALID")
    for cue in captions.get("cues") or []:
        start = _number(cue.get("start"), "caption_start")
        end = _number(cue.get("end"), "caption_end")
        if not cue.get("text") or end <= start or end > cursor + 0.02:
            raise PipelineError("CAPTION_CUE_INVALID")
    policy = edl.get("policy") or {}
    if policy.get("provider_execution") is not False:
        raise PipelineError("EDL_PROVIDER_EXECUTION_MUST_BE_DISABLED")


def analyze_video(
    path: str | Path,
    *,
    segment_seconds: float = 3.0,
    ffprobe_bin: str = "ffprobe",
) -> dict[str, Any]:
    """Create a deterministic candidate map for Codex/AI review.

    This is deliberately a baseline analyzer, not a claim of semantic AI
    understanding. Codex may replace the candidate notes and select ranges in
    a reviewed analysis artifact before EDL creation.
    """

    if segment_seconds <= 0:
        raise PipelineError("ANALYSIS_SEGMENT_SECONDS_INVALID")
    probe = probe_media(path, ffprobe_bin=ffprobe_bin)
    candidates = []
    start = 0.0
    index = 1
    while start < probe["duration_seconds"] - 0.001:
        end = min(probe["duration_seconds"], start + segment_seconds)
        candidates.append(
            {
                "id": f"shot-{index:03d}",
                "source_start": round(start, 6),
                "source_end": round(end, 6),
                "duration_seconds": round(end - start, 6),
                "visual_observation": "candidate interval requires Codex/AI review",
                "speech_transcript": None,
                "confidence": "baseline",
            }
        )
        start = end
        index += 1
    return {
        "schema": "archflow.video-analysis.v1",
        "analysis_mode": "deterministic_baseline_for_codex_review",
        "source": probe,
        "candidates": candidates,
        "semantic_status": "PENDING_CODEX_REVIEW",
        "provider_execution": False,
    }


def build_edl(
    *,
    case: Mapping[str, Any],
    source_probe: Mapping[str, Any],
    selections: Sequence[Mapping[str, Any]],
    captions: Sequence[Mapping[str, Any]] = (),
    width: int | None = None,
    height: int | None = None,
    color_preset: str = "neutral",
    audio_leveling: str = "loudnorm",
    caption_mode: str = "embedded_text_track",
) -> dict[str, Any]:
    """Convert reviewed timecoded selections into the canonical EDL."""

    if not selections:
        raise PipelineError("EDL_SELECTIONS_EMPTY")
    source_path = _require_file(source_probe.get("path", ""), "SOURCE")
    validate_case(case, source_path=source_path)
    segments = []
    cursor = 0.0
    for index, item in enumerate(selections, start=1):
        start = _number(item.get("source_start"), "selection_start")
        end = _number(item.get("source_end"), "selection_end")
        if end <= start or end > float(source_probe["duration_seconds"]) + 0.02:
            raise PipelineError("EDL_SELECTION_OUT_OF_RANGE")
        length = round(end - start, 6)
        segment = {
            "id": str(item.get("id") or f"segment-{index:03d}"),
            "source_start": round(start, 6),
            "source_end": round(end, 6),
            "timeline_start": round(cursor, 6),
            "timeline_duration": length,
            "label": str(item.get("label") or item.get("visual_observation") or "selected shot"),
            "notes": str(item.get("notes") or "Codex/AI selected; deterministic render only"),
        }
        if item.get("repair"):
            segment["repair"] = item["repair"]
        segments.append(segment)
        cursor += length
    timeline_width = int(width or source_probe.get("width") or 1920)
    timeline_height = int(height or source_probe.get("height") or 1080)
    edl = {
        "schema": SCHEMA_EDL,
        "case_id": str(case["case_id"]),
        "source": {
            "path": str(source_path),
            "sha256": str(source_probe["sha256"]),
            "duration_seconds": float(source_probe["duration_seconds"]),
            "width": int(source_probe.get("width") or 0),
            "height": int(source_probe.get("height") or 0),
            "has_audio": bool(source_probe.get("has_audio")),
        },
        "segments": segments,
        "timeline": {
            "duration_seconds": round(cursor, 6),
            "fps": float(source_probe.get("fps") or 30.0),
            "width": timeline_width,
            "height": timeline_height,
            "aspect_ratio": f"{timeline_width}:{timeline_height}",
        },
        "style": {"color_preset": color_preset, "audio_leveling": audio_leveling},
        "captions": {
            "mode": caption_mode if captions else "none",
            "language": "en",
            "cues": [
                {"start": round(float(c["start"]), 6), "end": round(float(c["end"]), 6), "text": str(c["text"])}
                for c in captions
            ],
        },
        "policy": {
            "provider_execution": False,
            "generative_repair": str((case.get("policy") or {}).get("generative_repair", "disabled")),
            "resolve_finishing": str((case.get("policy") or {}).get("resolve_finishing", "optional")),
        },
        "provenance": {
            "analysis_mode": "codex_reviewed_timecoded_selection",
            "source_hash": str(source_probe["sha256"]),
            "provider_state": "NOT_RUN",
        },
    }
    validate_edl(edl)
    return edl


def _srt_time(seconds: float) -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole:02d},{millis:03d}" if minutes < 60 else f"{hours:02d}:{minutes:02d}:{whole:02d},{millis:03d}"


def _write_srt(path: Path, cues: Sequence[Mapping[str, Any]]) -> None:
    lines: list[str] = []
    for index, cue in enumerate(cues, start=1):
        lines.extend(
            [
                str(index),
                f"{_srt_time(float(cue['start']))} --> {_srt_time(float(cue['end']))}",
                str(cue["text"]).replace("\n", " "),
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def _color_filter(preset: str) -> str:
    return {
        "none": "null",
        "neutral": "eq=contrast=1.03:brightness=0.01:saturation=1.03",
        "warm": "colorchannelmixer=rr=1.02:gg=1.0:bb=0.97",
        "cool": "colorchannelmixer=rr=0.97:gg=1.0:bb=1.03",
    }[preset]


def _aspect_filter(width: int, height: int) -> str:
    return f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}:(iw-{width})/2:(ih-{height})/2,setsar=1"


def render_edl(
    edl: Mapping[str, Any],
    output_path: str | Path,
    *,
    case: Mapping[str, Any],
    ffmpeg_bin: str = "ffmpeg",
    ffprobe_bin: str = "ffprobe",
    work_dir: str | Path | None = None,
    timeout: float = 300.0,
) -> dict[str, Any]:
    """Render a validated EDL with FFmpeg and return a masked manifest."""

    validate_edl(edl)
    output = Path(output_path).expanduser().resolve()
    validate_case(case, source_path=edl["source"]["path"], output_path=output)
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(work_dir).expanduser().resolve() if work_dir else output.parent / f".{output.stem}.work"
    work.mkdir(parents=True, exist_ok=True)
    captions = (edl.get("captions") or {}).get("cues") or []
    srt_path = work / "captions.srt"
    if captions:
        _write_srt(srt_path, captions)
    source = str(edl["source"]["path"])
    segments = list(edl["segments"])
    timeline = edl["timeline"]
    style = edl["style"]
    video_parts: list[str] = []
    audio_parts: list[str] = []
    has_audio = bool(edl["source"].get("has_audio"))
    for index, segment in enumerate(segments):
        start = float(segment["source_start"])
        end = float(segment["source_end"])
        duration = end - start
        video_parts.append(
            f"[0:v]trim=start={start:.6f}:end={end:.6f},setpts=PTS-STARTPTS[v{index}]"
        )
        if has_audio:
            audio_parts.append(
                f"[0:a]atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS[a{index}]"
            )
        else:
            audio_parts.append(
                f"anullsrc=r=48000:cl=stereo,atrim=duration={duration:.6f},asetpts=PTS-STARTPTS[a{index}]"
            )
    concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(len(segments)))
    filter_parts = video_parts + audio_parts
    filter_parts.append(f"{concat_inputs}concat=n={len(segments)}:v=1:a=1[vcat][acat]")
    video_filters = [
        _aspect_filter(int(timeline["width"]), int(timeline["height"])),
        _color_filter(str(style["color_preset"])),
        "format=yuv420p",
    ]
    video_filters = [item for item in video_filters if item != "null"]
    filter_parts.append(f"[vcat]{','.join(video_filters) if video_filters else 'null'}[vout]")
    audio_filter = "aresample=48000"
    if style["audio_leveling"] == "loudnorm":
        audio_filter += ",loudnorm=I=-16:TP=-1.5:LRA=11"
    elif style["audio_leveling"] == "dynaudnorm":
        audio_filter += ",dynaudnorm=f=150:g=15"
    filter_parts.append(f"[acat]{audio_filter}[aout]")
    filter_complex = ";".join(filter_parts)
    command = [ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error", "-i", source]
    if captions:
        command.extend(["-f", "srt", "-i", str(srt_path)])
    command.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-r",
            str(float(timeline.get("fps") or 30.0)),
            "-movflags",
            "+faststart",
        ]
    )
    if captions:
        command.extend(
            [
                "-map",
                "1:0",
                "-c:s",
                "mov_text",
                "-metadata:s:s:0",
                f"language={(edl.get('captions') or {}).get('language', 'en')}",
                "-metadata:s:s:0",
                "title=Captions",
            ]
        )
    command.append(str(output))
    _run(command, timeout=timeout)
    result_probe = probe_media(output, ffprobe_bin=ffprobe_bin)
    expected_duration = float(timeline["duration_seconds"])
    if abs(result_probe["duration_seconds"] - expected_duration) > 0.15:
        raise PipelineError("RENDER_DURATION_OUT_OF_BOUNDS")
    manifest = {
        "schema": "archflow.render-manifest.v1",
        "status": "PASS",
        "output_path": str(output),
        "output_sha256": sha256_file(output),
        "duration_seconds": result_probe["duration_seconds"],
        "expected_duration_seconds": expected_duration,
        "video_codec": result_probe.get("video_codec"),
        "audio_codec": result_probe.get("audio_codec"),
        "caption_mode": "embedded_text_track" if captions else "none",
        "ffmpeg": ffmpeg_bin,
        "ffprobe": ffprobe_bin,
        "command": command,
        "provider_execution": False,
        "resolve_finishing": "optional",
    }
    write_json(output.with_suffix(".render-manifest.json"), manifest)
    return manifest


def export_otio(edl: Mapping[str, Any], output_path: str | Path) -> dict[str, Any]:
    """Export OTIO when already installed; never install it implicitly."""

    validate_edl(edl)
    target = Path(output_path).expanduser().resolve()
    try:
        import opentimelineio as otio  # type: ignore
    except ImportError:
        result = {
            "schema": "archflow.otio-export-receipt.v1",
            "status": "NOT_AVAILABLE",
            "reason": "OpenTimelineIO is not installed; canonical JSON EDL retained",
            "output_path": str(target),
            "provider_execution": False,
        }
        write_json(target.with_suffix(".otio-receipt.json"), result)
        return result
    timeline = otio.schema.Timeline(name=str(edl["case_id"]))
    track = otio.schema.Track(name="V1", kind=otio.schema.TrackKind.Video)
    fps = float(edl["timeline"]["fps"])
    reference = otio.schema.ExternalReference(target_url=Path(edl["source"]["path"]).resolve().as_uri())
    for segment in edl["segments"]:
        duration = float(segment["timeline_duration"])
        source_start = float(segment["source_start"])
        clip = otio.schema.Clip(
            name=str(segment["id"]),
            media_reference=reference,
            source_range=otio.opentime.TimeRange(
                start_time=otio.opentime.RationalTime(source_start * fps, fps),
                duration=otio.opentime.RationalTime(duration * fps, fps),
            ),
        )
        track.append(clip)
    timeline.tracks.append(track)
    target.parent.mkdir(parents=True, exist_ok=True)
    otio.adapters.write_to_file(timeline, str(target))
    result = {
        "schema": "archflow.otio-export-receipt.v1",
        "status": "PASS",
        "output_path": str(target),
        "provider_execution": False,
    }
    write_json(target.with_suffix(".otio-receipt.json"), result)
    return result


def build_fixture_case(root: str | Path, *, ffmpeg_bin: str = "ffmpeg", ffprobe_bin: str = "ffprobe") -> dict[str, Any]:
    """Create a synthetic, rights-safe 4-second audio/video fixture and EDL."""

    base = Path(root).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    source = base / "fixture-source.mp4"
    command = [
        ffmpeg_bin,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "testsrc2=size=320x180:rate=30",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:sample_rate=48000",
        "-t",
        "4",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(source),
    ]
    _run(command, timeout=120.0)
    probe = probe_media(source, ffprobe_bin=ffprobe_bin)
    case = {
        "schema": SCHEMA_CASE,
        "case_id": "fixture-hybrid-edit-v1",
        "rights": {"status": "synthetic_fixture", "consent": "not_required", "source_note": "Generated locally by FFmpeg."},
        "execution": {
            "allow_local_render": True,
            "allowed_media_roots": [str(base)],
            "allowed_output_roots": [str(base)],
        },
        "policy": {"provider_execution": False, "generative_repair": "disabled", "resolve_finishing": "optional"},
    }
    selections = [
        {"id": "shot-001", "source_start": 0.0, "source_end": 1.4, "label": "opening fixture signal"},
        {"id": "shot-003", "source_start": 2.0, "source_end": 3.8, "label": "closing fixture signal"},
    ]
    captions = [
        {"start": 0.0, "end": 1.0, "text": "Fixture opening"},
        {"start": 1.4, "end": 2.7, "text": "Deterministic cut and finish"},
    ]
    edl = build_edl(
        case=case,
        source_probe=probe,
        selections=selections,
        captions=captions,
        width=320,
        height=180,
        color_preset="neutral",
        audio_leveling="loudnorm",
    )
    return {"case": case, "probe": probe, "analysis": analyze_video(source, segment_seconds=1.0, ffprobe_bin=ffprobe_bin), "edl": edl, "source": str(source)}
