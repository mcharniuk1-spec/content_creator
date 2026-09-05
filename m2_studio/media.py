"""Bounded local media evidence; cuts are candidates, scenes require annotation.

Canonical clock: integer milliseconds, half-open intervals, first decoded
video frame at zero. Raw PTS are retained. No acquisition or model downloads.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
import tempfile
import wave
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path


class StudioError(ValueError):
    """Stable error code; never include command stderr or private paths."""


def digest(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def object_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def write_json(path: str | Path, value) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", dir=target.parent, delete=False, encoding="utf-8") as stream:
        stream.write(payload)
        temporary = Path(stream.name)
    temporary.replace(target)


def safe_path(root: str | Path, relative: str, *, must_exist=True) -> Path:
    if not isinstance(relative, str) or not relative or ":" in relative or "\\" in relative:
        raise StudioError("INVALID_LOCAL_POINTER")
    base = Path(root).resolve()
    candidate = (base / relative).resolve()
    if Path(relative).is_absolute() or ".." in Path(relative).parts or not candidate.is_relative_to(base):
        raise StudioError("PATH_OUTSIDE_ALLOWLIST")
    if must_exist and not candidate.is_file():
        raise StudioError("MEDIA_UNAVAILABLE")
    return candidate


def safe_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", value):
        raise StudioError("INVALID_ID")
    return value


def run_tool(args: list[str], *, timeout=120) -> str:
    executable = shutil.which(args[0])
    if not executable:
        raise StudioError("TOOL_UNAVAILABLE")
    try:
        result = subprocess.run([executable, *args[1:]], capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise StudioError("TOOL_TIMEOUT") from exc
    except OSError as exc:
        raise StudioError("TOOL_UNAVAILABLE") from exc
    if result.returncode:
        raise StudioError("DECODE_FAILED")
    return result.stdout if result.stdout.strip() else result.stderr


def attempt(modality: str, state: str, *, failure_code=None, **data) -> dict:
    return {"schema": "m2.modality-attempt.v1", "modality": modality,
            "observation_state": state, "failure_code": failure_code,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "review_state": "NOT_REVIEWED", "provider_execution": False, **data}


def validate_rights(entry: dict) -> None:
    if entry.get("source_kind") not in {"owner_recording", "licensed_local", "synthetic_fixture", "approved_research_copy"}:
        raise StudioError("SOURCE_ROUTE_NOT_APPROVED")
    rights = entry.get("rights", {})
    if rights.get("analysis_allowed") is not True or not rights.get("receipt_id"):
        raise StudioError("RIGHTS_BLOCKED")
    if entry["source_kind"] == "owner_recording" and rights.get("owner_consent") is not True:
        raise StudioError("CONSENT_MISSING")


def observed_source(root: Path, media: dict) -> Path:
    if media.get("observation_state") != "OBSERVED":
        raise StudioError("MEDIA_NOT_OBSERVED")
    if media.get("rights", {}).get("analysis_allowed") is not True or not media.get("rights", {}).get("receipt_id"):
        raise StudioError("RIGHTS_BLOCKED")
    source = safe_path(root, media["source_pointer"])
    if digest(source) != media["sha256"]:
        raise StudioError("MEDIA_HASH_MISMATCH")
    return source


def probe(path: Path, *, max_duration_ms=600000) -> dict:
    metadata = json.loads(run_tool(["ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe", "-show_streams", "-show_format", "-of", "json", str(path)]))
    video = next((s for s in metadata.get("streams", []) if s.get("codec_type") == "video"), None)
    if not video:
        raise StudioError("NO_VIDEO_STREAM")
    raw_duration = video.get("duration", metadata.get("format", {}).get("duration"))
    try:
        duration_ms = round(float(raw_duration) * 1000)
        fps = float(Fraction(video.get("avg_frame_rate", "0/1")))
    except (TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
        raise StudioError("TIMEBASE_UNAVAILABLE") from exc
    if not 0 < duration_ms <= max_duration_ms or not 0 < fps <= 240:
        raise StudioError("MEDIA_LIMIT_EXCEEDED")
    frame_data = json.loads(run_tool(["ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe", "-select_streams", "v:0", "-show_frames", "-show_entries", "frame=best_effort_timestamp_time", "-of", "json", str(path)]))
    frames = frame_data.get("frames", [])
    if not frames or len(frames) > 144000:
        raise StudioError("FRAME_PTS_UNAVAILABLE")
    try:
        raw_pts = [float(f["best_effort_timestamp_time"]) for f in frames]
        first_pts = raw_pts[0]
        pts_ms = [round((p - first_pts) * 1000) for p in raw_pts]
    except (KeyError, ValueError, OverflowError) as exc:
        raise StudioError("FRAME_PTS_UNAVAILABLE") from exc
    if not all(math.isfinite(p) for p in raw_pts) or any(b <= a for a, b in zip(pts_ms, pts_ms[1:])):
        raise StudioError("NON_MONOTONIC_FRAME_PTS")
    if pts_ms[-1] >= duration_ms:
        raise StudioError("TIMEBASE_DURATION_MISMATCH")
    audio = next((s for s in metadata.get("streams", []) if s.get("codec_type") == "audio"), None)
    delta = [b - a for a, b in zip(pts_ms, pts_ms[1:])]
    audio_offset = round((float(audio.get("start_time", first_pts)) - first_pts) * 1000) if audio else None
    return {"duration_ms": duration_ms, "width": video["width"], "height": video["height"], "fps": fps,
            "has_audio": audio is not None, "frame_pts_ms": pts_ms,
            "timebase_provenance": {"source_time_base": video.get("time_base"), "source_start_time": video.get("start_time"),
                "first_decoded_pts_seconds": first_pts, "normalization_offset_ms": round(-first_pts * 1000),
                "trim_start_ms": 0, "trim_end_ms": 0, "audio_offset_ms": audio_offset,
                "variable_frame_rate": max(delta, default=0) - min(delta, default=0) > 1,
                "nominal_frame_rate": video.get("r_frame_rate"), "raw_frame_pts_seconds": raw_pts,
                "timestamp_rounding_rule": "nearest_integer_ms_python_round", "probe_tool_and_version": run_tool(["ffprobe", "-version"]).splitlines()[0],
                "source_media_hash": digest(path)}}


def inventory(root: Path, entries: list[dict], *, max_duration_ms=600000) -> list[dict]:
    seen = set()
    results = []
    for entry in entries:
        media_id = safe_id(entry["media_id"])
        if media_id in seen:
            raise StudioError("DUPLICATE_MEDIA_ID")
        seen.add(media_id)
        try:
            validate_rights(entry)
            source = safe_path(root, entry["path"])
            checksum = digest(source)
            if not re.fullmatch(r"[0-9a-f]{64}", entry.get("sha256", "")) or checksum != entry["sha256"]:
                raise StudioError("MEDIA_HASH_MISMATCH")
            data = probe(source, max_duration_ms=max_duration_ms)
            results.append(attempt("media", "OBSERVED", media_id=media_id, source_pointer=entry["path"], sha256=checksum, rights=entry["rights"], **data))
        except StudioError as exc:
            code = str(exc)
            state = "RIGHTS_BLOCKED" if code in {"RIGHTS_BLOCKED", "CONSENT_MISSING", "SOURCE_ROUTE_NOT_APPROVED"} else "DECODE_FAILED" if code == "DECODE_FAILED" else "UNAVAILABLE"
            results.append(attempt("media", state, failure_code=code, media_id=media_id))
    return results


def validate_transcript(segments: list[dict], duration_ms: int) -> None:
    ids = set()
    for seg in segments:
        if seg.get("segment_id") in ids:
            raise StudioError("DUPLICATE_TRANSCRIPT_ID")
        ids.add(safe_id(seg["segment_id"]))
        for obj in [seg, *seg.get("words", [])]:
            a, b = obj.get("start_ms"), obj.get("end_ms")
            if type(a) is not int or type(b) is not int or not 0 <= a < b <= duration_ms:
                raise StudioError("TRANSCRIPT_TIME_OUTSIDE_MEDIA")
        if not isinstance(seg.get("text"), str) or not seg["text"].strip():
            raise StudioError("EMPTY_TRANSCRIPT_SEGMENT")
        for word in seg.get("words", []):
            if not seg["start_ms"] <= word["start_ms"] < word["end_ms"] <= seg["end_ms"]:
                raise StudioError("WORD_OUTSIDE_SEGMENT")


def normalize_whisper(raw: dict, media: dict) -> dict:
    offset = media["timebase_provenance"]["audio_offset_ms"] or 0
    segments = []
    for n, seg in enumerate(raw.get("segments", [])):
        if not seg.get("text", "").strip():
            continue
        item = {"segment_id": f"T{n + 1:05}", "start_ms": round(float(seg["start"]) * 1000) + offset,
                "end_ms": round(float(seg["end"]) * 1000) + offset, "text": seg["text"].strip(),
                "raw_start_seconds": seg["start"], "raw_end_seconds": seg["end"], "words": []}
        for word in seg.get("words", []):
            item["words"].append({"start_ms": round(float(word["start"]) * 1000) + offset,
                                  "end_ms": round(float(word["end"]) * 1000) + offset,
                                  "text": word["word"], "confidence": word.get("probability")})
        segments.append(item)
    validate_transcript(segments, media["duration_ms"])
    return attempt("transcript", "OBSERVED" if segments else "EMPTY_OUTPUT_UNVERIFIED", segments=segments,
                   word_timing="OBSERVED" if any(s["words"] for s in segments) else "UNAVAILABLE",
                   language=raw.get("language"), source_media_hash=media["sha256"],
                   failure_code=None if segments else "EMPTY_ASR_NOT_PROOF_OF_SILENCE")


def transcribe_local(root: Path, media: dict, model_path: Path, output: Path, *, language=None, timeout=1800) -> dict:
    if media.get("observation_state") != "OBSERVED":
        return attempt("transcript", "UNAVAILABLE", failure_code="MEDIA_NOT_OBSERVED")
    if not media.get("has_audio"):
        return attempt("transcript", "NOT_APPLICABLE", failure_code="NO_AUDIO_STREAM", segments=[], source_media_hash=media["sha256"])
    if not model_path.is_file() or model_path.suffix != ".pt":
        return attempt("transcript", "UNAVAILABLE", failure_code="LOCAL_MODEL_UNAVAILABLE_NO_DOWNLOAD")
    output.mkdir(parents=True, exist_ok=True)
    try:
        source = observed_source(root, media)
        audio = output / "audio.wav"
        run_tool(["ffmpeg", "-v", "error", "-nostdin", "-n", "-protocol_whitelist", "file,pipe", "-i", str(source), "-map", "0:a:0", "-af", "asetpts=PTS-STARTPTS", "-ac", "1", "-ar", "16000", str(audio)])
        if digital_silence(audio):
            return attempt("transcript", "EMPTY_OUTPUT_UNVERIFIED", failure_code="DIGITAL_SILENCE_REVIEW_REQUIRED", segments=[],
                           method="pcm_silence_preflight", source_media_hash=media["sha256"], source_audio_sha256=digest(audio),
                           asr_execution=False, no_speech_confirmed=False)
        params = ["whisper", str(audio), "--model", str(model_path.resolve()), "--device", "cpu", "--fp16", "False", "--word_timestamps", "True", "--output_format", "json", "--output_dir", str(output), "--verbose", "False", "--threads", "4", "--temperature", "0"]
        if language:
            params += ["--language", language]
        run_tool(params, timeout=timeout)
        raw = json.loads((output / "audio.json").read_text())
        result = normalize_whisper(raw, media)
        result.update({"model_sha256": digest(model_path), "source_audio_sha256": digest(audio), "raw_transcript_sha256": digest(output / "audio.json"),
                       "method": "local_whisper", "parameters": {"cpu_threads": 4, "temperature": 0, "fp16": False, "language": language, "word_timestamps": True}})
        return result
    except (StudioError, ValueError, KeyError, OSError) as exc:
        return attempt("transcript", "ASR_FAILED", failure_code=str(exc) if isinstance(exc, StudioError) else "INVALID_ASR_OUTPUT")


def digital_silence(audio: Path) -> bool:
    """Only exact decoded PCM zeros qualify; quiet speech is never thresholded."""
    with wave.open(str(audio), "rb") as stream:
        if stream.getsampwidth() != 2 or stream.getnframes() == 0:
            return False
        while data := stream.readframes(8192):
            if any(data):
                return False
    return True


def cut_candidates(root: Path, media: dict, *, threshold=0.32, min_separation_ms=120) -> dict:
    if not 0 < threshold < 1 or not 0 <= min_separation_ms <= 10000:
        raise StudioError("INVALID_CUT_PARAMETERS")
    if media.get("observation_state") != "OBSERVED":
        return attempt("cuts", "UNAVAILABLE", failure_code="MEDIA_NOT_OBSERVED")
    try:
        source = observed_source(root, media)
        log = run_tool(["ffmpeg", "-hide_banner", "-nostdin", "-protocol_whitelist", "file,pipe", "-i", str(source), "-an", "-vf", f"setpts=PTS-STARTPTS,select='gt(scene,{threshold})',showinfo", "-f", "null", "-"], timeout=300)
        pts = sorted(set(round(float(p) * 1000) for p in re.findall(r"pts_time:([0-9.eE+-]+)", log)))
        kept = []
        for p in pts:
            if 0 < p < media["duration_ms"] and (not kept or p - kept[-1] >= min_separation_ms):
                kept.append(p)
        return attempt("cuts", "OBSERVED", candidates=[{"cut_id": f"C{i + 1:04}", "timestamp_ms": p, "candidate_type": "unknown_change", "review_state": "NOT_REVIEWED", "confirmed_type": None} for i, p in enumerate(kept)],
                       detector="ffmpeg_scene_score", threshold=threshold, min_separation_ms=min_separation_ms,
                       confirmed_shots=None, semantic_scenes=None, source_media_hash=media["sha256"])
    except StudioError as exc:
        return attempt("cuts", "DECODE_FAILED", failure_code=str(exc))


SEMANTIC_REASONS = {"goal_change", "action_change", "object_change", "location_change", "speaker_change", "proof", "argument_stage", "layout_change", "payoff", "cta", "audio_role_change", "screen_change", "focal_overlay", "a_b_roll_relationship"}


def transcript_source_digest(transcript: dict, source_media_hash: str) -> str:
    if not isinstance(source_media_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", source_media_hash) or transcript.get("source_media_hash") != source_media_hash:
        raise StudioError("TRANSCRIPT_SOURCE_MEDIA_MISMATCH")
    return object_hash(transcript)


def align_scenes(annotations: list[dict], transcript: dict, duration_ms: int, *, source_media_hash: str) -> list[dict]:
    """Validate agent-authored interpretations; do not derive scene meaning from cuts."""
    transcript_hash = transcript_source_digest(transcript, source_media_hash)
    segments = transcript.get("segments", [])
    validate_transcript(segments, duration_ms)
    previous = 0
    ids = set()
    result = []
    for annotation in annotations:
        sid = safe_id(annotation["scene_id"])
        a, b = annotation["start_ms"], annotation["end_ms"]
        if sid in ids or type(a) is not int or type(b) is not int or a != previous or not a < b <= duration_ms:
            raise StudioError("SCENE_PARTITION_INVALID")
        ids.add(sid)
        previous = b
        if not set(annotation.get("boundary_reasons", [])) & SEMANTIC_REASONS or not annotation.get("information_job"):
            raise StudioError("SEMANTIC_REASON_REQUIRED")
        if annotation.get("sample_count") not in {2, 4, 6}:
            raise StudioError("INVALID_SAMPLE_COUNT")
        if not annotation.get("maker"):
            raise StudioError("SCENE_MAKER_REQUIRED")
        linked = [s["segment_id"] for s in segments if s["start_ms"] < b and s["end_ms"] > a]
        if annotation.get("transcript_segment_ids") != linked:
            raise StudioError("TRANSCRIPT_SCENE_BINDING_MISMATCH")
        result.append({**annotation, "review_state": "REVIEW_PENDING", "reviewer": None,
                       "transcript_sha256": transcript_hash, "transcript_source_media_hash": source_media_hash,
                       "evidence_depth": "TRANSCRIPT_ALIGNED_CANDIDATE" if linked else "VISUAL_CANDIDATE_TRANSCRIPT_GAP",
                       "transcript_observation_state": transcript.get("observation_state", "NOT_ATTEMPTED")})
    if not annotations or previous != duration_ms:
        raise StudioError("SCENE_COVERAGE_INCOMPLETE")
    if sum(s["sample_count"] for s in result) > 48:
        raise StudioError("FRAME_BUDGET_EXCEEDED")
    return result


def sampling_pts(scene: dict, decoded_pts_ms: list[int]) -> list[dict]:
    indices = [i for i, p in enumerate(decoded_pts_ms) if scene["start_ms"] <= p < scene["end_ms"]]
    count = scene["sample_count"]
    if len(indices) < count:
        raise StudioError("INSUFFICIENT_DECODED_FRAMES")
    chosen = [indices[round(i * (len(indices) - 1) / (count - 1))] for i in range(count)]
    return [{"frame_index": index, "timestamp_ms": decoded_pts_ms[index], "role": "start" if n == 0 else "end" if n == count - 1 else f"progression_{n}"} for n, index in enumerate(chosen)]


def extract_scenes(root: Path, media: dict, scenes: list[dict], output: Path, *, transcript: dict) -> dict:
    if media.get("observation_state") != "OBSERVED":
        raise StudioError("MEDIA_NOT_OBSERVED")
    transcript_hash = transcript_source_digest(transcript, media["sha256"])
    # Validate bounds before creating artifacts, even when invoked without align_scenes.
    previous = 0
    seen = set()
    for scene in scenes:
        if scene.get("transcript_sha256") != transcript_hash or scene.get("transcript_source_media_hash") != media["sha256"]:
            raise StudioError("SCENE_TRANSCRIPT_DIGEST_MISMATCH")
        sid = safe_id(scene["scene_id"])
        if sid in seen or scene["start_ms"] != previous or not previous < scene["end_ms"] <= media["duration_ms"] or scene["sample_count"] not in {2, 4, 6}:
            raise StudioError("SCENE_PARTITION_INVALID")
        seen.add(sid)
        previous = scene["end_ms"]
    if not scenes or previous != media["duration_ms"] or sum(s["sample_count"] for s in scenes) > 48:
        raise StudioError("FRAME_BUDGET_OR_COVERAGE_INVALID")
    source = observed_source(root, media)
    output.mkdir(parents=True, exist_ok=True)
    collected = []
    for scene in scenes:
        frames = sampling_pts(scene, media["frame_pts_ms"])
        for n, frame in enumerate(frames):
            filename = f"{scene['scene_id']}-F{n + 1:02}.jpg"
            target = output / filename
            # Select decoded frame index, not input seek approximation. One decode per
            # bounded sample is slower but avoids VFR/seek timestamp drift.
            run_tool(["ffmpeg", "-v", "error", "-nostdin", "-n", "-protocol_whitelist", "file,pipe", "-i", str(source), "-vf", f"select=eq(n\\,{frame['frame_index']}),scale=480:-2", "-frames:v", "1", "-q:v", "2", str(target)], timeout=300)
            if not target.is_file() or target.stat().st_size == 0:
                raise StudioError("FRAME_EXTRACTION_EMPTY")
            frame.update({"frame_id": f"{scene['scene_id']}-F{n + 1:02}", "source_pointer": filename, "sha256": digest(target)})
        collage_receipt = build_collage(frames, output, f"{scene['scene_id']}-collage.jpg")
        collected.append({**scene, "sampled_frames": frames, "collage": collage_receipt})
    return {"schema": "m2.scene-evidence.v1", "duration_ms": media["duration_ms"], "source_media_hash": media["sha256"],
            "transcript_sha256": transcript_hash, "transcript_source_media_hash": media["sha256"], "transcript_digest_method": "canonical-json-sha256",
            "timebase": "milliseconds_half_open_first_decoded_pts_zero", "scene_units": collected,
            "frame_observation_state": "OBSERVED", "scene_observation_state": "PARTIAL", "review_state": "REVIEW_PENDING",
            "public_display_allowed": media["rights"].get("public_display_allowed") is True,
            "rights": media["rights"], "sample_count": sum(len(s["sampled_frames"]) for s in collected)}


def build_collage(frames: list[dict], root: Path, filename: str) -> dict:
    try:
        from PIL import Image, ImageDraw, ImageOps
    except ImportError:
        return {"observation_state": "UNAVAILABLE", "failure_code": "PILLOW_UNAVAILABLE", "sample_count": len(frames)}
    columns = 2 if len(frames) < 6 else 3
    tile_w, tile_h, label_h = 320, 568, 34
    sheet = Image.new("RGB", (columns * tile_w, math.ceil(len(frames) / columns) * (tile_h + label_h)), "#14181f")
    draw = ImageDraw.Draw(sheet)
    for i, frame in enumerate(frames):
        x, y = i % columns * tile_w, i // columns * (tile_h + label_h)
        with Image.open(safe_path(root, frame["source_pointer"])) as img:
            # Contain preserves source evidence; no center-crop removes proof.
            thumb = ImageOps.contain(img.convert("RGB"), (tile_w, tile_h))
            sheet.paste(thumb, (x + (tile_w - thumb.width) // 2, y + (tile_h - thumb.height) // 2))
        draw.text((x + 8, y + tile_h + 10), f"{frame['role']} | {frame['timestamp_ms']} ms", fill="white")
    target = safe_path(root, filename, must_exist=False)
    sheet.save(target, quality=88)
    return {"observation_state": "OBSERVED", "source_pointer": filename, "sha256": digest(target), "sample_count": len(frames)}
