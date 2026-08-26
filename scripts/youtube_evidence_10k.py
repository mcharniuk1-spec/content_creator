#!/usr/bin/env python3
"""Collect resumable public transcripts and compact storyboard frames for a 10K cohort."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
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


TERMINAL_GAPS = {"provider_auth_required", "rate_limited"}
COLLECTOR_VERSION = "youtube_evidence_10k.v2"


class DiskReserveError(RuntimeError):
    pass


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    temporary.replace(path)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ensure_disk_reserve(path: Path, minimum_free_bytes: int, free_override: int | None = None) -> None:
    free = free_override if free_override is not None else shutil.disk_usage(path).free
    if free < minimum_free_bytes:
        raise DiskReserveError(f"free disk {free} is below reserve {minimum_free_bytes}")


def hardlink_or_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if sha256(source) != sha256(target):
            raise ValueError(f"existing reuse target hash mismatch: {target}")
        return
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


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


def transcript_result_from_vtt(run_dir: Path, row: dict[str, Any], info: dict[str, Any], started: str, exit_code: int, stderr: str, argv: list[str]) -> dict[str, Any]:
    video_id = row["native_video_id"]
    raw_dir = run_dir / "raw" / "subtitles" / video_id
    selected = transcript_source(sorted(raw_dir.glob(f"{video_id}*.vtt")), info, video_id)
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
    normalized = run_dir / "normalized" / "transcripts" / f"{video_id}.json"
    write_json(normalized, result)
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


def collect_one_transcript(run_dir: Path, row: dict[str, Any], timeout: int, minimum_free_bytes: int) -> dict[str, Any]:
    video_id = row["native_video_id"]
    normalized = run_dir / "normalized" / "transcripts" / f"{video_id}.json"
    if normalized.is_file():
        existing = json.loads(normalized.read_text(encoding="utf-8"))
        if existing.get("availability") == "observed" or existing.get("collector_version") == COLLECTOR_VERSION:
            return existing
    ensure_disk_reserve(run_dir, minimum_free_bytes)
    raw_dir = run_dir / "raw" / "subtitles" / video_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    argv = [
        "yt-dlp", "--no-cookies", "--no-cookies-from-browser", "--no-cache-dir", "--no-playlist",
        "--skip-download", "--write-subs", "--write-auto-subs", "--sub-langs", "en.*,en",
        "--sub-format", "vtt", "--write-info-json", "--socket-timeout", "20", "--retries", "1",
        "-o", str(raw_dir / f"{video_id}.%(ext)s"), row["canonical_url"],
    ]
    started = datetime.now(UTC).isoformat()
    try:
        completed = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False, env={**os.environ, "PYTHONUNBUFFERED": "1"})
        exit_code, stderr = completed.returncode, completed.stderr or ""
        info_json = raw_dir / f"{video_id}.info.json"
        try:
            payload = json.loads(info_json.read_text(encoding="utf-8")) if info_json.is_file() else {}
        except json.JSONDecodeError:
            payload = {}
        if info_json.is_file():
            info_json.unlink()
    except subprocess.TimeoutExpired as exc:
        exit_code, stderr, payload = 124, str(exc), {}
    info = minimal_source_info(payload)
    info_path = raw_dir / "source-metadata.json"
    write_json(info_path, info)
    result = transcript_result_from_vtt(run_dir, row, info, started, exit_code, stderr, argv)
    result["source_metadata_uri"] = info_path.relative_to(run_dir).as_posix()
    result["source_metadata_sha256"] = sha256(info_path)
    write_json(normalized, result)
    return result


def reuse_transcripts(run_dir: Path, source_run: Path, cohort_ids: set[str]) -> int:
    reused = 0
    for source_normalized in sorted((source_run / "normalized" / "transcripts").glob("*.json")):
        video_id = source_normalized.stem
        if video_id not in cohort_ids:
            continue
        target_normalized = run_dir / "normalized" / "transcripts" / source_normalized.name
        if target_normalized.is_file():
            continue
        payload = json.loads(source_normalized.read_text(encoding="utf-8"))
        source_uri = payload.get("source_uri")
        if source_uri:
            source_artifact = source_run / source_uri
            if not source_artifact.is_file() or sha256(source_artifact) != payload.get("source_sha256"):
                raise ValueError(f"baseline transcript source mismatch: {video_id}")
            hardlink_or_copy(source_artifact, run_dir / source_uri)
        payload["schema"] = "north-hux.youtube-transcript-artifact.v3"
        payload["artifact_run_key"] = run_dir.name
        payload["reused_from_run_key"] = source_run.name
        payload.setdefault("collector_version", "baseline_reuse_v1")
        write_json(target_normalized, payload)
        reused += 1
    return reused


def pick_indexes(size: int, limit: int) -> list[int]:
    if size <= 0:
        return []
    if size <= limit:
        return list(range(size))
    return sorted({round(index * (size - 1) / (limit - 1)) for index in range(limit)})


def compact_jpeg(payload: bytes, output: Path) -> tuple[int, int]:
    output.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(io.BytesIO(payload)) as image:
        image = image.convert("RGB")
        image.thumbnail((480, 854), Image.Resampling.LANCZOS)
        width, height = image.size
        image.save(output, format="JPEG", quality=72, optimize=True)
    return width, height


def collect_one_storyboard(run_dir: Path, row: dict[str, Any], timeout: int, minimum_free_bytes: int, max_frames: int) -> dict[str, Any]:
    video_id = row["native_video_id"]
    manifest_path = run_dir / "normalized" / "frame-manifests" / f"{video_id}.json"
    if manifest_path.is_file():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    ensure_disk_reserve(run_dir, minimum_free_bytes)
    raw_dir = run_dir / "raw" / "storyboards" / video_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    mhtml = raw_dir / f"{video_id}.mhtml"
    argv = [
        "yt-dlp", "--no-cookies", "--no-cookies-from-browser", "--no-cache-dir", "--no-playlist",
        "-f", "sb0", "--socket-timeout", "20", "--retries", "1",
        "-o", str(raw_dir / f"{video_id}.%(ext)s"), row["canonical_url"],
    ]
    started = datetime.now(UTC).isoformat()
    stderr = ""
    exit_code = 0
    if not mhtml.is_file():
        try:
            completed = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False, env={**os.environ, "PYTHONUNBUFFERED": "1"})
            exit_code, stderr = completed.returncode, completed.stderr or ""
        except subprocess.TimeoutExpired as exc:
            exit_code, stderr = 124, str(exc)
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
    return result


def reuse_frames(run_dir: Path, source_run: Path, cohort_ids: set[str]) -> int:
    media = {row["native_video_id"]: row for row in load_jsonl(source_run / "derived" / "media-assets.jsonl")}
    frames: dict[str, list[dict[str, Any]]] = {}
    for row in load_jsonl(source_run / "derived" / "frame-artifacts.jsonl"):
        frames.setdefault(row["native_video_id"], []).append(row)
    reused = 0
    for video_id in sorted(cohort_ids & media.keys() & frames.keys()):
        target_manifest = run_dir / "normalized" / "frame-manifests" / f"{video_id}.json"
        if target_manifest.is_file():
            continue
        media_row = dict(media[video_id])
        source_asset = source_run / media_row["asset_uri"]
        if not source_asset.is_file() or sha256(source_asset) != media_row["sha256"]:
            raise ValueError(f"baseline media hash mismatch: {video_id}")
        hardlink_or_copy(source_asset, run_dir / media_row["asset_uri"])
        copied_frames = []
        for frame in sorted(frames[video_id], key=lambda item: item["frame_index"]):
            item = dict(frame)
            source_frame = source_run / item["frame_uri"]
            if not source_frame.is_file() or sha256(source_frame) != item["sha256"]:
                raise ValueError(f"baseline frame hash mismatch: {video_id}/{item['frame_index']}")
            hardlink_or_copy(source_frame, run_dir / item["frame_uri"])
            item["reused_from_run_key"] = source_run.name
            copied_frames.append(item)
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
    return reused


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
) -> dict[str, Any]:
    cohort = load_jsonl(run_dir / "derived" / "video-cohort.jsonl")
    if not cohort:
        raise ValueError("video cohort is missing")
    cohort_ids = {row["native_video_id"] for row in cohort}
    reused = reuse_transcripts(run_dir, source_run, cohort_ids) if stage == "transcripts" else reuse_frames(run_dir, source_run, cohort_ids)
    pending = cohort[offset: offset + limit if limit is not None else None]
    function: Callable[..., dict[str, Any]] = collect_one_transcript if stage == "transcripts" else collect_one_storyboard
    terminal_streak = 0
    processed = 0
    batch_size = max(workers, workers * 10)
    for batch_start in range(0, len(pending), batch_size):
        batch = pending[batch_start:batch_start + batch_size]
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(function, run_dir, row, timeout, minimum_free_bytes, max_frames)
                if stage == "frames" else executor.submit(function, run_dir, row, timeout, minimum_free_bytes): row
                for row in batch
            }
            for future in as_completed(futures):
                result = future.result()
                processed += 1
                gap = result.get("gap_reason")
                terminal_streak = terminal_streak + 1 if gap in TERMINAL_GAPS else 0
                if terminal_streak >= 5:
                    raise ValueError(f"five consecutive terminal {stage} failures: {gap}")
        if processed and processed % 100 == 0:
            print(json.dumps({"stage": stage, "processed": processed, "requested": len(pending)}), flush=True)

    if stage == "transcripts":
        artifacts = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((run_dir / "normalized" / "transcripts").glob("*.json"))]
        write_jsonl(run_dir / "derived" / "transcripts.jsonl", sorted(artifacts, key=lambda item: item["native_video_id"]))
        gaps = [row for row in artifacts if row.get("availability") != "observed"]
        write_jsonl(run_dir / "derived" / "transcript-gaps.jsonl", gaps)
        return {
            "stage": stage, "requested_this_call": len(pending), "reused": reused,
            "artifacts_total": len(artifacts), "observed": len(artifacts) - len(gaps), "gaps": len(gaps),
            "raw_segments": sum(int(row.get("segment_count") or 0) for row in artifacts),
            "speech_segments": sum(int(row.get("speech_segment_count") or 0) for row in artifacts),
        }
    manifests = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((run_dir / "normalized" / "frame-manifests").glob("*.json"))]
    media_rows = [row["media"] for row in manifests if row.get("status") == "observed"]
    frame_rows = [frame for row in manifests if row.get("status") == "observed" for frame in row.get("frames", [])]
    gaps = [row for row in manifests if row.get("status") != "observed"]
    write_jsonl(run_dir / "derived" / "media-assets.jsonl", sorted(media_rows, key=lambda item: item["native_video_id"]))
    write_jsonl(run_dir / "derived" / "frame-artifacts.jsonl", sorted(frame_rows, key=lambda item: (item["native_video_id"], item["frame_index"])))
    write_jsonl(run_dir / "derived" / "frame-gaps.jsonl", gaps)
    return {
        "stage": stage, "requested_this_call": len(pending), "reused": reused,
        "manifests_total": len(manifests), "observed": len(media_rows), "gaps": len(gaps), "frames": len(frame_rows),
    }


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
    args = parser.parse_args()
    try:
        if args.workers < 1 or args.workers > 8 or args.max_frames < 1 or args.max_frames > 12:
            raise ValueError("workers must be 1-8 and max-frames 1-12")
        summary = run_stage(
            args.run_dir.resolve(), args.source_run_dir.resolve(), args.stage, args.workers,
            args.timeout_seconds, round(args.min_free_gib * 1024 ** 3), args.max_frames, args.offset, args.limit,
        )
        print(json.dumps({"schema": "north-hux.youtube-evidence-10k-stage.v1", "status": "pass_with_limitations" if summary.get("gaps") else "pass", **summary}, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError, DiskReserveError) as exc:
        print(json.dumps({"status": "error", "error_code": type(exc).__name__, "message": str(exc)[:500]}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
