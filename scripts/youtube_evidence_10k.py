#!/usr/bin/env python3
"""Collect resumable public transcripts and compact storyboard frames for a 10K cohort."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any, Callable

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.youtube_evidence_300 import de_roll_caption_segments, parse_vtt_segments, transcript_source  # noqa: E402
from scripts.youtube_storyboard_fallback import TIMESTAMP, millis  # noqa: E402
from scripts.youtube_video_census_10k import validate_pinned_creator_cap  # noqa: E402


TERMINAL_GAPS = {"provider_auth_required", "rate_limited"}
COLLECTOR_VERSION = "youtube_evidence_10k.v2"


class DiskReserveError(RuntimeError):
    pass


class ConcurrentClaimError(ValueError):
    pass


def reusable_attempt(payload: dict[str, Any], success_field: str, success_value: str) -> bool:
    """Keep observed/permanent outcomes, but retry route-level terminal gaps on resume."""
    if payload.get(success_field) == success_value:
        return True
    return payload.get("collector_version") == COLLECTOR_VERSION and payload.get("gap_reason") not in TERMINAL_GAPS


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    atomic_write_text(path, "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows))


def write_json(path: Path, value: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


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


@contextmanager
def artifact_claim(run_dir: Path, stage: str, video_id: str, stale_seconds: int):
    claim_path = run_dir / "locks" / stage / f"{video_id}.lock"
    claim_path.parent.mkdir(parents=True, exist_ok=True)
    guard_path = claim_path.with_suffix(".guard")
    guard = os.open(guard_path, os.O_CREAT | os.O_RDWR, 0o600)
    owns_claim = False
    try:
        try:
            fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ConcurrentClaimError(f"active artifact claim: {stage}/{video_id}") from exc
        if claim_path.exists():
            age = time.time() - claim_path.stat().st_mtime
            pid = claim_pid(claim_path)
            if (pid is not None and not pid_alive(pid)) or (pid is None and age > stale_seconds):
                claim_path.unlink(missing_ok=True)
            else:
                raise ConcurrentClaimError(f"active artifact claim: {stage}/{video_id}")
        descriptor = os.open(claim_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        owns_claim = True
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"pid": os.getpid(), "created_at": datetime.now(UTC).isoformat()}))
            handle.flush()
            os.fsync(handle.fileno())
        yield
    finally:
        if owns_claim:
            claim_path.unlink(missing_ok=True)
        try:
            fcntl.flock(guard, fcntl.LOCK_UN)
        finally:
            os.close(guard)


def claim_pid(claim_path: Path) -> int | None:
    try:
        return int(json.loads(claim_path.read_text(encoding="utf-8")).get("pid"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def active_artifact_claims(run_dir: Path, stale_seconds: int = 900) -> tuple[list[Path], list[Path]]:
    active: list[Path] = []
    removed: list[Path] = []
    lock_root = run_dir / "locks"
    for claim_path in sorted(lock_root.rglob("*.lock")) if lock_root.exists() else []:
        guard_path = claim_path.with_suffix(".guard")
        guard = os.open(guard_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            try:
                fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                active.append(claim_path)
                continue
            if not claim_path.exists():
                continue
            age = time.time() - claim_path.stat().st_mtime
            pid = claim_pid(claim_path)
            if (pid is not None and not pid_alive(pid)) or (pid is None and age > stale_seconds):
                claim_path.unlink(missing_ok=True)
                removed.append(claim_path)
            else:
                active.append(claim_path)
        finally:
            try:
                fcntl.flock(guard, fcntl.LOCK_UN)
            finally:
                os.close(guard)
    return active, removed


@contextmanager
def stage_lock(run_dir: Path, stage: str, *, exclusive: bool):
    lock_path = run_dir / "locks" / f".{stage}.stage.lck"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def assert_run_mutable(run_dir: Path) -> None:
    freeze_marker = run_dir / "receipts" / "terminal-freeze.json"
    if freeze_marker.is_file():
        raise ValueError(f"run is terminally frozen: {freeze_marker}")


def next_wave_size(workers: int, terminal_streak: int) -> int:
    if workers < 1 or terminal_streak < 0 or terminal_streak >= 5:
        raise ValueError("workers must be positive and terminal streak must be between 0 and 4")
    return min(workers, 5 - terminal_streak)


def strike_receipt_path(run_dir: Path, stage: str) -> Path:
    return run_dir / "receipts" / f"{stage}-strike-state.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ensure_disk_reserve(path: Path, minimum_free_bytes: int, free_override: int | None = None) -> None:
    if minimum_free_bytes <= 0:
        raise ValueError("minimum disk reserve must be positive")
    free = free_override if free_override is not None else shutil.disk_usage(path).free
    if free < minimum_free_bytes:
        raise DiskReserveError(f"free disk {free} is below reserve {minimum_free_bytes}")


def run_local_artifact(run_dir: Path, uri: str | None) -> Path | None:
    if not uri:
        return None
    candidate = (run_dir / uri).resolve()
    return candidate if candidate.is_relative_to(run_dir.resolve()) else None


def command_receipt_valid(path: Path, video_id: str, state_key: str, state_value: str) -> bool:
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return payload.get("native_video_id") == video_id and payload.get(state_key) == state_value


def transcript_artifact_valid(run_dir: Path, path: Path, payload: dict[str, Any]) -> bool:
    if payload.get("native_video_id") != path.stem:
        return False
    availability = payload.get("availability")
    if payload.get("collector_version") == COLLECTOR_VERSION and not command_receipt_valid(
        run_dir / "receipts" / "subtitles" / f"{path.stem}.json", path.stem, "availability", availability
    ):
        return False
    if availability != "observed":
        return bool(payload.get("gap_reason")) and not payload.get("segments") and not payload.get("speech_segments")
    source = run_local_artifact(run_dir, payload.get("source_uri"))
    metadata = run_local_artifact(run_dir, payload.get("source_metadata_uri"))
    return bool(
        source and source.is_file() and sha256(source) == payload.get("source_sha256")
        and metadata and metadata.is_file() and sha256(metadata) == payload.get("source_metadata_sha256")
    )


def frame_artifact_valid(run_dir: Path, path: Path, payload: dict[str, Any]) -> bool:
    if payload.get("native_video_id") != path.stem:
        return False
    status = payload.get("status")
    if payload.get("collector_version") == COLLECTOR_VERSION and not command_receipt_valid(
        run_dir / "receipts" / "storyboards" / f"{path.stem}.json", path.stem, "status", status
    ):
        return False
    if status != "observed":
        return bool(payload.get("gap_reason")) and not payload.get("frames")
    media = payload.get("media") or {}
    if media.get("native_video_id") != path.stem:
        return False
    media_path = run_local_artifact(run_dir, media.get("asset_uri"))
    if not media_path or not media_path.is_file() or sha256(media_path) != media.get("sha256"):
        return False
    frames = payload.get("frames") or []
    if [frame.get("frame_index") for frame in frames] != list(range(len(frames))):
        return False
    timestamps = [frame.get("timestamp_ms") for frame in frames]
    if any(not isinstance(value, int) or value < 0 for value in timestamps) or timestamps != sorted(timestamps):
        return False
    for frame in frames:
        if frame.get("native_video_id") != path.stem:
            return False
        frame_path = run_local_artifact(run_dir, frame.get("frame_uri"))
        if not frame_path or not frame_path.is_file() or sha256(frame_path) != frame.get("sha256"):
            return False
    return bool(frames)


def canonical_attempt_valid(run_dir: Path, stage: str, video_id: str) -> bool:
    """Return whether a cohort identity already has a valid canonical attempt."""
    if stage == "transcripts":
        path = run_dir / "normalized" / "transcripts" / f"{video_id}.json"
        validator = transcript_artifact_valid
    else:
        path = run_dir / "normalized" / "frame-manifests" / f"{video_id}.json"
        validator = frame_artifact_valid
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    return validator(run_dir, path, payload)


def hardlink_or_copy(source: Path, target: Path) -> None:
    if not source.is_file():
        raise ValueError(f"reuse source is missing: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if sha256(source) != sha256(target):
            raise ValueError(f"existing reuse target hash mismatch: {target}")
        return
    try:
        os.link(source, target)
    except OSError:
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            shutil.copy2(source, temporary)
            with temporary.open("rb") as handle:
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)


def confined_reuse_paths(source_run: Path, run_dir: Path, uri: str | None) -> tuple[Path, Path]:
    source = run_local_artifact(source_run, uri)
    target = run_local_artifact(run_dir, uri)
    if source is None or target is None:
        raise ValueError(f"reuse URI escapes a run boundary: {uri}")
    return source, target


def atomic_promote(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as handle:
        os.fsync(handle.fileno())
    os.replace(source, target)


def storyboard_bundle_valid(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    except (OSError, ValueError):
        return False
    return any(part.get_content_type() == "text/html" for part in message.walk()) and any(
        part.get_content_maintype() == "image" for part in message.walk()
    )


def classify_gap(stderr: str) -> str:
    lowered = stderr.casefold()
    if "sign in to confirm" in lowered or "login required" in lowered:
        return "provider_auth_required"
    if "429" in lowered or "too many requests" in lowered:
        return "rate_limited"
    if "video unavailable" in lowered or "private video" in lowered:
        return "public_video_unavailable"
    return "no_public_english_subtitle"


def minimal_source_info(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": payload.get("id"),
        "duration": payload.get("duration"),
        "webpage_url": payload.get("webpage_url"),
        "subtitles": {key: [] for key in (payload.get("subtitles") or {})},
        "automatic_captions": {key: [] for key in (payload.get("automatic_captions") or {})},
    }


def transcript_result_from_vtt(
    run_dir: Path,
    row: dict[str, Any],
    info: dict[str, Any],
    started: str,
    exit_code: int,
    stderr: str,
    argv: list[str],
    source_files: list[Path],
) -> dict[str, Any]:
    video_id = row["native_video_id"]
    raw_dir = run_dir / "raw" / "subtitles" / video_id
    selected = transcript_source(sorted(source_files), info, video_id) if exit_code == 0 else None
    if selected:
        source_file, source_kind, language = selected
        segments = parse_vtt_segments(source_file)
        speech_segments = de_roll_caption_segments(segments)
        raw_words = sum(len(segment["text"].split()) for segment in segments)
        speech_words = sum(len(segment["text"].split()) for segment in speech_segments)
        result = {
            "schema": "north-hux.youtube-transcript-artifact.v3",
            "native_channel_id": row["native_channel_id"],
            "native_video_id": video_id,
            "canonical_url": row["canonical_url"],
            "source_kind": source_kind if source_kind in {"native_caption", "native_subtitle"} else "native_caption",
            "language": language,
            "quality_state": "usable" if speech_segments else "review",
            "source_uri": source_file.relative_to(run_dir).as_posix(),
            "source_sha256": sha256(source_file),
            "segments": segments,
            "segment_count": len(segments),
            "text": " ".join(segment["text"] for segment in segments),
            "speech_segments": speech_segments,
            "speech_segment_count": len(speech_segments),
            "speech_text": " ".join(segment["text"] for segment in speech_segments),
            "raw_word_count": raw_words,
            "speech_word_count": speech_words,
            "rolling_caption_expansion_ratio": round(raw_words / speech_words, 4) if speech_words else None,
            "normalization_method": "longest_exact_token_overlap_v1",
            "captured_at": datetime.now(UTC).isoformat(),
            "availability": "observed",
            "artifact_run_key": run_dir.name,
            "collector_version": COLLECTOR_VERSION,
        }
    else:
        result = {
            "schema": "north-hux.youtube-transcript-artifact.v3",
            "native_channel_id": row["native_channel_id"],
            "native_video_id": video_id,
            "canonical_url": row["canonical_url"],
            "source_kind": "none",
            "language": None,
            "quality_state": "blocked" if classify_gap(stderr) in TERMINAL_GAPS else "not_run",
            "segments": [],
            "segment_count": 0,
            "text": "",
            "speech_segments": [],
            "speech_segment_count": 0,
            "speech_text": "",
            "raw_word_count": 0,
            "speech_word_count": 0,
            "rolling_caption_expansion_ratio": None,
            "normalization_method": "longest_exact_token_overlap_v1",
            "captured_at": datetime.now(UTC).isoformat(),
            "availability": "unavailable",
            "gap_reason": classify_gap(stderr),
            "artifact_run_key": run_dir.name,
            "collector_version": COLLECTOR_VERSION,
        }
    receipt = {
        "schema": "archflow.command-receipt.v1",
        "label": "public_subtitle_collection",
        "native_video_id": video_id,
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "argv": argv,
        "exit_code": exit_code,
        "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
        "availability": result["availability"],
    }
    write_json(run_dir / "receipts" / "subtitles" / f"{video_id}.json", receipt)
    return result


def _collect_one_transcript(run_dir: Path, row: dict[str, Any], timeout: int, minimum_free_bytes: int) -> dict[str, Any]:
    video_id = row["native_video_id"]
    normalized = run_dir / "normalized" / "transcripts" / f"{video_id}.json"
    if normalized.is_file():
        existing = json.loads(normalized.read_text(encoding="utf-8"))
        if reusable_attempt(existing, "availability", "observed") and transcript_artifact_valid(run_dir, normalized, existing):
            return existing
    ensure_disk_reserve(run_dir, minimum_free_bytes)
    raw_dir = run_dir / "raw" / "subtitles" / video_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    inflight_root = run_dir / "raw" / "subtitles" / ".inflight"
    inflight_root.mkdir(parents=True, exist_ok=True)
    inflight = Path(tempfile.mkdtemp(prefix=f"{video_id}-", dir=inflight_root))
    argv = [
        "yt-dlp", "--no-cookies", "--no-cookies-from-browser", "--no-cache-dir", "--no-playlist",
        "--skip-download", "--write-subs", "--write-auto-subs", "--sub-langs", "en.*,en",
        "--sub-format", "vtt", "--write-info-json", "--socket-timeout", "20", "--retries", "1",
        "-o", str(inflight / f"{video_id}.%(ext)s"), row["canonical_url"],
    ]
    started = datetime.now(UTC).isoformat()
    promoted_files: list[Path] = []
    try:
        completed = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False, env={**os.environ, "PYTHONUNBUFFERED": "1"})
        exit_code, stderr = completed.returncode, completed.stderr or ""
        info_json = inflight / f"{video_id}.info.json"
        try:
            payload = json.loads(info_json.read_text(encoding="utf-8")) if info_json.is_file() else {}
        except json.JSONDecodeError:
            payload = {}
        if exit_code == 0:
            for source_file in sorted(inflight.glob(f"{video_id}*.vtt")):
                target = raw_dir / source_file.name
                atomic_promote(source_file, target)
                promoted_files.append(target)
    except subprocess.TimeoutExpired as exc:
        exit_code, stderr, payload = 124, str(exc), {}
    finally:
        shutil.rmtree(inflight, ignore_errors=True)
    info = minimal_source_info(payload)
    info_path = raw_dir / "source-metadata.json"
    write_json(info_path, info)
    result = transcript_result_from_vtt(run_dir, row, info, started, exit_code, stderr, argv, promoted_files)
    result["source_metadata_uri"] = info_path.relative_to(run_dir).as_posix()
    result["source_metadata_sha256"] = sha256(info_path)
    write_json(normalized, result)
    ensure_disk_reserve(run_dir, minimum_free_bytes)
    return result


def collect_claimed_transcript(run_dir: Path, row: dict[str, Any], timeout: int, minimum_free_bytes: int) -> dict[str, Any]:
    with artifact_claim(run_dir, "transcripts", row["native_video_id"], max(300, timeout * 2)):
        return _collect_one_transcript(run_dir, row, timeout, minimum_free_bytes)


def collect_one_transcript(run_dir: Path, row: dict[str, Any], timeout: int, minimum_free_bytes: int) -> dict[str, Any]:
    with stage_lock(run_dir, "run-data", exclusive=False):
        with stage_lock(run_dir, "transcripts", exclusive=False):
            assert_run_mutable(run_dir)
            return collect_claimed_transcript(run_dir, row, timeout, minimum_free_bytes)


def reuse_transcripts(run_dir: Path, source_run: Path, cohort_ids: set[str]) -> int:
    reused = 0
    for source_normalized in sorted((source_run / "normalized" / "transcripts").glob("*.json")):
        video_id = source_normalized.stem
        if video_id not in cohort_ids:
            continue
        with artifact_claim(run_dir, "transcripts", video_id, 600):
            target_normalized = run_dir / "normalized" / "transcripts" / source_normalized.name
            if target_normalized.is_file():
                existing = json.loads(target_normalized.read_text(encoding="utf-8"))
                if transcript_artifact_valid(run_dir, target_normalized, existing):
                    continue
                target_normalized.unlink()
            payload = json.loads(source_normalized.read_text(encoding="utf-8"))
            inflight_root = run_dir / "raw" / "subtitles" / ".reuse-inflight"
            inflight_root.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix=f"{video_id}-", dir=inflight_root))
            target_bundle = run_dir / "raw" / "subtitles" / video_id
            try:
                source_uri = payload.get("source_uri")
                if source_uri:
                    source_artifact, _ = confined_reuse_paths(source_run, run_dir, source_uri)
                    if sha256(source_artifact) != payload.get("source_sha256"):
                        raise ValueError(f"baseline transcript source mismatch: {video_id}")
                    staged_source = staging / source_artifact.name
                    hardlink_or_copy(source_artifact, staged_source)
                    payload["source_uri"] = (target_bundle / staged_source.name).relative_to(run_dir).as_posix()
                metadata_uri = payload.get("source_metadata_uri")
                if metadata_uri:
                    source_metadata, _ = confined_reuse_paths(source_run, run_dir, metadata_uri)
                    if sha256(source_metadata) != payload.get("source_metadata_sha256"):
                        raise ValueError(f"baseline transcript metadata mismatch: {video_id}")
                    staged_metadata = staging / "source-metadata.json"
                    hardlink_or_copy(source_metadata, staged_metadata)
                    payload["source_metadata_uri"] = (target_bundle / staged_metadata.name).relative_to(run_dir).as_posix()
                if target_bundle.exists():
                    shutil.rmtree(target_bundle)
                os.replace(staging, target_bundle)
                payload["schema"] = "north-hux.youtube-transcript-artifact.v3"
                payload["artifact_run_key"] = run_dir.name
                payload["reused_from_run_key"] = source_run.name
                payload["collector_version"] = "baseline_reuse_v2"
                write_json(target_normalized, payload)
                reused += 1
            finally:
                shutil.rmtree(staging, ignore_errors=True)
    return reused


def pick_indexes(size: int, limit: int) -> list[int]:
    if size <= 0:
        return []
    if size <= limit:
        return list(range(size))
    return sorted({round(index * (size - 1) / (limit - 1)) for index in range(limit)})


def compact_jpeg(payload: bytes, output: Path) -> tuple[int, int]:
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image = image.convert("RGB")
            image.thumbnail((480, 854), Image.Resampling.LANCZOS)
            width, height = image.size
            image.save(temporary, format="JPEG", quality=72, optimize=True)
        atomic_promote(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return width, height


def _collect_one_storyboard(run_dir: Path, row: dict[str, Any], timeout: int, minimum_free_bytes: int, max_frames: int) -> dict[str, Any]:
    video_id = row["native_video_id"]
    manifest_path = run_dir / "normalized" / "frame-manifests" / f"{video_id}.json"
    if manifest_path.is_file():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if reusable_attempt(existing, "status", "observed") and frame_artifact_valid(run_dir, manifest_path, existing):
            return existing
    ensure_disk_reserve(run_dir, minimum_free_bytes)
    raw_dir = run_dir / "raw" / "storyboards" / video_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    mhtml = raw_dir / f"{video_id}.mhtml"
    inflight_root = run_dir / "raw" / "storyboards" / ".inflight"
    inflight_root.mkdir(parents=True, exist_ok=True)
    inflight = Path(tempfile.mkdtemp(prefix=f"{video_id}-", dir=inflight_root))
    argv = [
        "yt-dlp", "--no-cookies", "--no-cookies-from-browser", "--no-cache-dir", "--no-playlist",
        "-f", "sb0", "--socket-timeout", "20", "--retries", "1",
        "-o", str(inflight / f"{video_id}.%(ext)s"), row["canonical_url"],
    ]
    started = datetime.now(UTC).isoformat()
    stderr = ""
    exit_code = 0
    if not storyboard_bundle_valid(mhtml):
        try:
            completed = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False, env={**os.environ, "PYTHONUNBUFFERED": "1"})
            exit_code, stderr = completed.returncode, completed.stderr or ""
            candidate = inflight / f"{video_id}.mhtml"
            if exit_code == 0 and storyboard_bundle_valid(candidate):
                atomic_promote(candidate, mhtml)
            elif exit_code == 0:
                exit_code, stderr = 1, "downloaded storyboard bundle failed structural validation"
        except subprocess.TimeoutExpired as exc:
            exit_code, stderr = 124, str(exc)
        finally:
            shutil.rmtree(inflight, ignore_errors=True)
    else:
        shutil.rmtree(inflight, ignore_errors=True)
    if exit_code != 0 or not mhtml.is_file():
        gap = classify_gap(stderr)
        if gap == "no_public_english_subtitle":
            gap = "public_storyboard_unavailable"
        result = {
            "schema": "north-hux.youtube-frame-manifest.v2",
            "native_channel_id": row["native_channel_id"],
            "native_video_id": video_id,
            "status": "gap",
            "gap_reason": gap,
            "terminal_class": gap if gap in TERMINAL_GAPS else None,
            "frames": [],
            "artifact_run_key": run_dir.name,
            "collector_version": COLLECTOR_VERSION,
        }
    else:
        message = BytesParser(policy=policy.default).parsebytes(mhtml.read_bytes())
        html_part = next((part for part in message.walk() if part.get_content_type() == "text/html"), None)
        html_text = html_part.get_content() if html_part else ""
        starts = [millis(value) for value in TIMESTAMP.findall(html_text)]
        images = [part for part in message.walk() if part.get_content_maintype() == "image"]
        frames = []
        width = height = None
        for frame_index, source_index in enumerate(pick_indexes(len(images), max_frames)):
            frame_path = run_dir / "derived" / "frames" / video_id / f"sb-{frame_index:02d}-{(starts[source_index] if source_index < len(starts) else 0):08d}.jpg"
            width, height = compact_jpeg(images[source_index].get_payload(decode=True), frame_path)
            frames.append({
                "schema": "north-hux.youtube-frame-artifact.v2",
                "native_channel_id": row["native_channel_id"],
                "native_video_id": video_id,
                "frame_index": frame_index,
                "timestamp_ms": starts[source_index] if source_index < len(starts) else 0,
                "frame_uri": frame_path.relative_to(run_dir).as_posix(),
                "sha256": sha256(frame_path),
                "selection_basis": "youtube_public_storyboard_even_temporal_fragment",
                "quality_tier": "storyboard_compact_local_reference",
                "public_display_allowed": False,
            })
        if frames:
            result = {
                "schema": "north-hux.youtube-frame-manifest.v2",
                "native_channel_id": row["native_channel_id"],
                "native_video_id": video_id,
                "status": "observed",
                "quality_tier": "storyboard_compact_local_reference",
                "media": {
                    "schema": "north-hux.youtube-media-asset.v2",
                    "native_channel_id": row["native_channel_id"],
                    "native_video_id": video_id,
                    "asset_kind": "preview",
                    "asset_uri": mhtml.relative_to(run_dir).as_posix(),
                    "sha256": sha256(mhtml),
                    "byte_size": mhtml.stat().st_size,
                    "duration_ms": round((row.get("duration_seconds") or 0) * 1000),
                    "width": width,
                    "height": height,
                    "rights_state": "local_reference_only_owner_approved",
                    "retention_until": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
                    "public_display_allowed": False,
                    "quality_tier": "storyboard_compact_local_reference",
                },
                "frames": frames,
                "artifact_run_key": run_dir.name,
                "collector_version": COLLECTOR_VERSION,
            }
        else:
            result = {
                "schema": "north-hux.youtube-frame-manifest.v2",
                "native_channel_id": row["native_channel_id"],
                "native_video_id": video_id,
                "status": "gap",
                "gap_reason": "storyboard_has_no_images",
                "frames": [],
                "artifact_run_key": run_dir.name,
                "collector_version": COLLECTOR_VERSION,
            }
    write_json(manifest_path, result)
    write_json(run_dir / "receipts" / "storyboards" / f"{video_id}.json", {
        "schema": "archflow.command-receipt.v1",
        "label": "public_storyboard_collection",
        "native_video_id": video_id,
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "argv": argv,
        "exit_code": exit_code,
        "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
        "status": result["status"],
    })
    ensure_disk_reserve(run_dir, minimum_free_bytes)
    return result


def collect_claimed_storyboard(
    run_dir: Path,
    row: dict[str, Any],
    timeout: int,
    minimum_free_bytes: int,
    max_frames: int,
) -> dict[str, Any]:
    with artifact_claim(run_dir, "frames", row["native_video_id"], max(300, timeout * 2)):
        return _collect_one_storyboard(run_dir, row, timeout, minimum_free_bytes, max_frames)


def collect_one_storyboard(run_dir: Path, row: dict[str, Any], timeout: int, minimum_free_bytes: int, max_frames: int) -> dict[str, Any]:
    with stage_lock(run_dir, "run-data", exclusive=False):
        with stage_lock(run_dir, "frames", exclusive=False):
            assert_run_mutable(run_dir)
            return collect_claimed_storyboard(run_dir, row, timeout, minimum_free_bytes, max_frames)


def reuse_frames(run_dir: Path, source_run: Path, cohort_ids: set[str]) -> int:
    media = {row["native_video_id"]: row for row in load_jsonl(source_run / "derived" / "media-assets.jsonl")}
    frames: dict[str, list[dict[str, Any]]] = {}
    for row in load_jsonl(source_run / "derived" / "frame-artifacts.jsonl"):
        frames.setdefault(row["native_video_id"], []).append(row)
    reused = 0
    for video_id in sorted(cohort_ids & media.keys() & frames.keys()):
        with artifact_claim(run_dir, "frames", video_id, 600):
            target_manifest = run_dir / "normalized" / "frame-manifests" / f"{video_id}.json"
            if target_manifest.is_file():
                existing = json.loads(target_manifest.read_text(encoding="utf-8"))
                if frame_artifact_valid(run_dir, target_manifest, existing):
                    continue
                target_manifest.unlink()
            media_row = dict(media[video_id])
            source_asset, _ = confined_reuse_paths(source_run, run_dir, media_row["asset_uri"])
            if sha256(source_asset) != media_row["sha256"]:
                raise ValueError(f"baseline media hash mismatch: {video_id}")
            inflight_root = run_dir / "raw" / "reused-frame-bundles" / ".inflight"
            inflight_root.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix=f"{video_id}-", dir=inflight_root))
            target_bundle = run_dir / "raw" / "reused-frame-bundles" / video_id
            try:
                staged_media = staging / f"media{source_asset.suffix or '.bin'}"
                hardlink_or_copy(source_asset, staged_media)
                media_row["asset_uri"] = (target_bundle / staged_media.name).relative_to(run_dir).as_posix()
                copied_frames = []
                for frame in sorted(frames[video_id], key=lambda item: item["frame_index"]):
                    item = dict(frame)
                    source_frame, _ = confined_reuse_paths(source_run, run_dir, item["frame_uri"])
                    if sha256(source_frame) != item["sha256"]:
                        raise ValueError(f"baseline frame hash mismatch: {video_id}/{item['frame_index']}")
                    staged_frame = staging / f"frame-{int(item['frame_index']):02d}{source_frame.suffix or '.jpg'}"
                    hardlink_or_copy(source_frame, staged_frame)
                    item["frame_uri"] = (target_bundle / staged_frame.name).relative_to(run_dir).as_posix()
                    item["reused_from_run_key"] = source_run.name
                    copied_frames.append(item)
                if target_bundle.exists():
                    shutil.rmtree(target_bundle)
                os.replace(staging, target_bundle)
                media_row["reused_from_run_key"] = source_run.name
                write_json(target_manifest, {
                    "schema": "north-hux.youtube-frame-manifest.v2",
                    "native_video_id": video_id,
                    "native_channel_id": media_row["native_channel_id"],
                    "status": "observed",
                    "quality_tier": media_row.get("quality_tier") or "full_public_media_reference",
                    "media": media_row,
                    "frames": copied_frames,
                    "artifact_run_key": run_dir.name,
                    "reused_from_run_key": source_run.name,
                })
                reused += 1
            finally:
                shutil.rmtree(staging, ignore_errors=True)
    return reused


def finalize_stage_snapshot(
    run_dir: Path,
    stage: str,
    requested_this_call: int,
    reused: int,
    timeout: int,
) -> dict[str, Any]:
    with stage_lock(run_dir, stage, exclusive=True):
        with artifact_claim(run_dir, f"{stage}-snapshot", "all", max(300, timeout * 2)):
            if stage == "transcripts":
                artifacts = []
                for path in sorted((run_dir / "normalized" / "transcripts").glob("*.json")):
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    if not transcript_artifact_valid(run_dir, path, payload):
                        raise ValueError(f"invalid transcript pointer/hash chain: {path}")
                    artifacts.append(payload)
                write_jsonl(run_dir / "derived" / "transcripts.jsonl", sorted(artifacts, key=lambda item: item["native_video_id"]))
                gaps = [row for row in artifacts if row.get("availability") != "observed"]
                write_jsonl(run_dir / "derived" / "transcript-gaps.jsonl", gaps)
                return {
                    "stage": stage, "requested_this_call": requested_this_call, "reused": reused,
                    "artifacts_total": len(artifacts), "observed": len(artifacts) - len(gaps), "gaps": len(gaps),
                    "raw_segments": sum(int(row.get("segment_count") or 0) for row in artifacts),
                    "speech_segments": sum(int(row.get("speech_segment_count") or 0) for row in artifacts),
                }
            manifests = []
            for path in sorted((run_dir / "normalized" / "frame-manifests").glob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not frame_artifact_valid(run_dir, path, payload):
                    raise ValueError(f"invalid frame pointer/hash chain: {path}")
                manifests.append(payload)
            media_rows = [row["media"] for row in manifests if row.get("status") == "observed"]
            frame_rows = [frame for row in manifests if row.get("status") == "observed" for frame in row.get("frames", [])]
            gaps = [row for row in manifests if row.get("status") != "observed"]
            write_jsonl(run_dir / "derived" / "media-assets.jsonl", sorted(media_rows, key=lambda item: item["native_video_id"]))
            write_jsonl(run_dir / "derived" / "frame-artifacts.jsonl", sorted(frame_rows, key=lambda item: (item["native_video_id"], item["frame_index"])))
            write_jsonl(run_dir / "derived" / "frame-gaps.jsonl", gaps)
            return {
                "stage": stage, "requested_this_call": requested_this_call, "reused": reused,
                "manifests_total": len(manifests), "observed": len(media_rows), "gaps": len(gaps), "frames": len(frame_rows),
            }


def run_stage_locked(
    run_dir: Path,
    source_run: Path,
    stage: str,
    workers: int,
    timeout: int,
    minimum_free_bytes: int,
    max_frames: int,
    offset: int,
    limit: int | None,
    reset_terminal_strikes: bool,
    missing_only: bool,
) -> dict[str, Any]:
    cohort = load_jsonl(run_dir / "derived" / "video-cohort.jsonl")
    if len(cohort) != 10000:
        raise ValueError(f"video cohort must contain exactly 10,000 rows, got {len(cohort)}")
    cohort_ids = {row["native_video_id"] for row in cohort}
    if len(cohort_ids) != len(cohort):
        raise ValueError("video cohort contains duplicate identities")
    creator_counts: dict[str, int] = {}
    for row in cohort:
        creator = row["native_channel_id"]
        creator_counts[creator] = creator_counts.get(creator, 0) + 1
    if max(creator_counts.values()) / len(cohort) > validate_pinned_creator_cap(run_dir):
        raise ValueError("video cohort violates the approved maximum creator contribution")
    with stage_lock(run_dir, stage, exclusive=False):
        assert_run_mutable(run_dir)
        reused = reuse_transcripts(run_dir, source_run, cohort_ids) if stage == "transcripts" else reuse_frames(run_dir, source_run, cohort_ids)
    pending = cohort[offset: offset + limit if limit is not None else None]
    if missing_only:
        pending = [
            row for row in pending
            if not canonical_attempt_valid(run_dir, stage, row["native_video_id"])
        ]
    function: Callable[..., dict[str, Any]] = collect_claimed_transcript if stage == "transcripts" else collect_claimed_storyboard
    processed = 0
    strike_receipt = strike_receipt_path(run_dir, stage)
    prior_strikes: dict[str, Any] = {}
    if strike_receipt.is_file():
        prior_strikes = json.loads(strike_receipt.read_text(encoding="utf-8"))
    terminal_streak = int(prior_strikes.get("terminal_streak") or 0)
    reset_count = int(prior_strikes.get("reset_count") or 0)
    if reset_terminal_strikes:
        reset_count += 1
        terminal_streak = 0
        write_json(strike_receipt, {
            **prior_strikes,
            "schema": "north-hux.youtube-evidence-strike-state.v1",
            "stage": stage,
            "offset": offset,
            "limit": limit,
            "terminal_streak": 0,
            "reset_count": reset_count,
            "reset_reason": "operator_approved_bounded_retry",
            "reset_at": datetime.now(UTC).isoformat(),
        })
    if terminal_streak >= 5:
        raise ValueError(f"persisted five-strike stop for {stage}; an explicit bounded reset is required")
    batch_start = 0
    while batch_start < len(pending):
        wave_size = next_wave_size(workers, terminal_streak)
        batch = pending[batch_start:batch_start + wave_size]
        with stage_lock(run_dir, stage, exclusive=False):
            assert_run_mutable(run_dir)
            with stage_lock(run_dir, "disk-wave", exclusive=True):
                ensure_disk_reserve(run_dir, minimum_free_bytes + wave_size * 256 * 1024 * 1024)
                with ThreadPoolExecutor(max_workers=wave_size) as executor:
                    futures = {
                        executor.submit(function, run_dir, row, timeout, minimum_free_bytes, max_frames)
                        if stage == "frames" else executor.submit(function, run_dir, row, timeout, minimum_free_bytes): row
                        for row in batch
                    }
                    completed: dict[str, dict[str, Any]] = {}
                    for future in as_completed(futures):
                        completed[futures[future]["native_video_id"]] = future.result()
                for row in batch:
                    result = completed[row["native_video_id"]]
                    processed += 1
                    gap = result.get("gap_reason")
                    terminal_streak = terminal_streak + 1 if gap in TERMINAL_GAPS else 0
                    write_json(strike_receipt, {
                        "schema": "north-hux.youtube-evidence-strike-state.v1",
                        "stage": stage,
                        "offset": offset,
                        "limit": limit,
                        "last_scope": {"offset": offset, "limit": limit},
                        "processed": processed,
                        "terminal_streak": terminal_streak,
                        "reset_count": reset_count,
                        "last_gap_reason": gap,
                        "updated_at": datetime.now(UTC).isoformat(),
                    })
                    if terminal_streak >= 5:
                        raise ValueError(f"five consecutive terminal {stage} failures: {gap}")
        batch_start += len(batch)
        if processed and processed % 100 == 0:
            print(json.dumps({"stage": stage, "processed": processed, "requested": len(pending)}), flush=True)

    return finalize_stage_snapshot(run_dir, stage, len(pending), reused, timeout)


def run_stage(
    run_dir: Path,
    source_run: Path,
    stage: str,
    workers: int,
    timeout: int,
    minimum_free_bytes: int,
    max_frames: int,
    offset: int,
    limit: int | None,
    reset_terminal_strikes: bool = False,
    missing_only: bool = False,
) -> dict[str, Any]:
    with stage_lock(run_dir, "run-data", exclusive=False):
        assert_run_mutable(run_dir)
        with stage_lock(run_dir, f"{stage}-strike-ledger", exclusive=True):
            return run_stage_locked(
                run_dir, source_run, stage, workers, timeout, minimum_free_bytes, max_frames,
                offset, limit, reset_terminal_strikes, missing_only,
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--source-run-dir", required=True, type=Path)
    parser.add_argument("--stage", choices=("transcripts", "frames"), required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument("--min-free-gib", type=float, default=15.0)
    parser.add_argument("--max-frames", type=int, default=6)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--reset-terminal-strikes", action="store_true")
    parser.add_argument(
        "--missing-only",
        action="store_true",
        help="process only identities without a valid canonical attempt inside the requested slice",
    )
    args = parser.parse_args()
    try:
        if args.workers < 1 or args.workers > 8 or args.max_frames < 1 or args.max_frames > 12:
            raise ValueError("workers must be 1-8 and max-frames 1-12")
        if args.min_free_gib <= 0 or args.offset < 0 or (args.limit is not None and args.limit <= 0):
            raise ValueError("min-free-gib must be positive; offset/limit must define a positive slice")
        summary = run_stage(
            args.run_dir.resolve(), args.source_run_dir.resolve(), args.stage, args.workers,
            args.timeout_seconds, round(args.min_free_gib * 1024 ** 3), args.max_frames, args.offset, args.limit,
            args.reset_terminal_strikes, args.missing_only,
        )
        total = summary.get("artifacts_total", summary.get("manifests_total", 0))
        status = "active_partial" if total != 10000 else ("pass_with_limitations" if summary.get("gaps") else "pass")
        print(json.dumps({"schema": "north-hux.youtube-evidence-10k-stage.v1", "status": status, **summary}, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError, DiskReserveError) as exc:
        print(json.dumps({"status": "error", "error_code": type(exc).__name__, "message": str(exc)[:500]}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
