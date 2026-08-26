#!/usr/bin/env python3
"""Download bounded local reference media and extract meaningful-state frames for top 100."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.youtube_census import load_json, validate_execution_authorization, write_jsonl  # noqa: E402


PTS_TIME = re.compile(r"pts_time:(\d+(?:\.\d+)?)")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path: Path) -> dict[str, Any]:
    completed = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height:format=duration", "-of", "json", str(path),
    ], capture_output=True, text=True, timeout=30, check=True)
    payload = json.loads(completed.stdout)
    stream = (payload.get("streams") or [{}])[0]
    return {"duration_seconds": float(payload.get("format", {}).get("duration") or 0), "width": stream.get("width"), "height": stream.get("height")}


def scene_times(path: Path) -> list[float]:
    completed = subprocess.run([
        "ffmpeg", "-hide_banner", "-nostdin", "-i", str(path),
        "-vf", "select='gt(scene,0.30)',showinfo", "-an", "-f", "null", "-",
    ], capture_output=True, text=True, timeout=120, check=False)
    return [float(value) for value in PTS_TIME.findall(completed.stderr)]


def select_timestamps(duration: float, cuts: list[float], limit: int = 12) -> list[float]:
    if duration <= 0:
        return []
    anchors = [value for value in (0.4, 1.2, 2.4, duration * 0.25, duration * 0.5, duration * 0.75, max(0.0, duration - 0.4)) if value < duration]
    deduped = sorted(set(anchors))
    for value in sorted(set(value for value in cuts if 0 <= value < duration)):
        if all(abs(value - existing) >= 0.35 for existing in deduped):
            deduped.append(value)
    deduped.sort()
    if len(deduped) <= limit:
        return deduped
    mandatory = [value for value in deduped if value <= 2.4]
    remaining = [value for value in deduped if value > 2.4]
    slots = max(0, limit - len(mandatory))
    if slots and remaining:
        indexes = sorted({round(index * (len(remaining) - 1) / max(1, slots - 1)) for index in range(slots)})
        mandatory.extend(remaining[index] for index in indexes)
    return sorted(mandatory)[:limit]


def extract_frame(video: Path, timestamp: float, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-ss", f"{timestamp:.3f}",
        "-i", str(video), "-frames:v", "1", "-q:v", "2", "-y", str(output),
    ], capture_output=True, text=True, timeout=30, check=True)


def process_reference(run_dir: Path, row: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    video_id = row["native_video_id"]
    media_dir = run_dir / "raw" / "media" / video_id
    media_dir.mkdir(parents=True, exist_ok=True)
    output_template = media_dir / f"{video_id}.%(ext)s"
    existing = sorted(path for path in media_dir.glob(f"{video_id}.*") if path.suffix not in {".json", ".part", ".ytdl"})
    if not existing:
        args = [
            "yt-dlp", "--no-cookies", "--no-cookies-from-browser", "--no-cache-dir", "--no-playlist",
            "-f", "bestvideo[height<=720][ext=mp4]/best[height<=720]/bestvideo[height<=480]/best",
            "--socket-timeout", "20", "--retries", "1", "-o", str(output_template), row["canonical_url"],
        ]
        completed = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout_seconds, check=False, env={**os.environ, "PYTHONUNBUFFERED": "1"})
        existing = sorted(path for path in media_dir.glob(f"{video_id}.*") if path.suffix not in {".json", ".part", ".ytdl"})
        if completed.returncode != 0 or not existing:
            stderr = completed.stderr or ""
            lowered = stderr.lower()
            terminal_class = (
                "provider_auth_required" if "sign in to confirm" in lowered or "login required" in lowered
                else "rate_limited" if "429" in lowered or "too many requests" in lowered
                else None
            )
            return {
                "native_video_id": video_id,
                "status": "gap",
                "gap_reason": terminal_class or "public_media_download_unavailable",
                "terminal_class": terminal_class,
                "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
            }
    video = existing[0]
    try:
        details = probe(video)
        timestamps = select_timestamps(details["duration_seconds"], scene_times(video))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return {
            "native_video_id": video_id,
            "status": "gap",
            "gap_reason": "media_probe_or_scene_analysis_failed",
            "terminal_class": None,
            "error_class": type(exc).__name__,
        }
    frames = []
    frame_errors = 0
    for index, timestamp in enumerate(timestamps):
        frame_path = run_dir / "derived" / "frames" / video_id / f"{index:02d}-{round(timestamp * 1000):08d}.jpg"
        try:
            if not frame_path.is_file():
                extract_frame(video, timestamp, frame_path)
        except subprocess.SubprocessError:
            frame_errors += 1
            continue
        frames.append({
            "schema": "north-hux.youtube-frame-artifact.v1",
            "native_channel_id": row["native_channel_id"],
            "native_video_id": video_id,
            "frame_index": index,
            "timestamp_ms": round(timestamp * 1000),
            "frame_uri": frame_path.relative_to(run_dir).as_posix(),
            "sha256": sha256(frame_path),
            "selection_basis": "hook_anchor_or_scene_change_or_duration_anchor",
            "public_display_allowed": False,
        })
    if not frames:
        return {
            "native_video_id": video_id,
            "status": "gap",
            "gap_reason": "no_extractable_frames",
            "terminal_class": None,
            "frame_errors": frame_errors,
        }
    media = {
        "schema": "north-hux.youtube-media-asset.v1",
        "native_channel_id": row["native_channel_id"],
        "native_video_id": video_id,
        "asset_uri": video.relative_to(run_dir).as_posix(),
        "sha256": sha256(video),
        "byte_size": video.stat().st_size,
        "duration_ms": round(details["duration_seconds"] * 1000),
        "width": details["width"],
        "height": details["height"],
        "rights_state": "local_reference_only_owner_approved",
        "retention_until": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
        "public_display_allowed": False,
    }
    manifest = {"native_video_id": video_id, "status": "observed", "media": media, "frames": frames, "frame_errors": frame_errors}
    manifest_path = run_dir / "normalized" / "frame-manifests" / f"{video_id}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--authorization-receipt", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    args = parser.parse_args()
    try:
        validate_execution_authorization(args.authorization_receipt, args.run_dir)
        rows = load_jsonl(args.run_dir / "derived" / "top-reference-cohort.jsonl")
        if len(rows) != 100 or len({row["native_channel_id"] for row in rows}) != 100:
            raise ValueError("top-reference cohort must be 100 videos from 100 creators")
        results = []
        terminal_strikes: dict[str, int] = {}
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(process_reference, args.run_dir, row, args.timeout_seconds): row for row in rows}
            for index, future in enumerate(as_completed(futures), start=1):
                result = future.result()
                results.append(result)
                terminal_class = result.get("terminal_class")
                if terminal_class:
                    terminal_strikes[terminal_class] = terminal_strikes.get(terminal_class, 0) + 1
                if terminal_class and terminal_strikes[terminal_class] >= 5:
                    for pending in futures:
                        pending.cancel()
                    raise ValueError(f"five identical terminal media failures: {terminal_class}")
                if index % 10 == 0:
                    print(json.dumps({"progress": "frames", "videos": index, "observed": sum(item.get("status") == "observed" for item in results)}), flush=True)
        media_rows = [item["media"] for item in results if item.get("status") == "observed"]
        frame_rows = [frame for item in results if item.get("status") == "observed" for frame in item["frames"]]
        gap_rows = [item for item in results if item.get("status") != "observed"]
        write_jsonl(args.run_dir / "derived" / "media-assets.jsonl", sorted(media_rows, key=lambda item: item["native_video_id"]))
        write_jsonl(args.run_dir / "derived" / "frame-artifacts.jsonl", sorted(frame_rows, key=lambda item: (item["native_video_id"], item["frame_index"])))
        write_jsonl(args.run_dir / "derived" / "frame-gaps.jsonl", gap_rows)
        print(json.dumps({"schema": "north-hux.youtube-frame-stage.v1", "status": "pass", "requested_videos": 100, "media_observed": len(media_rows), "frame_artifacts": len(frame_rows), "gaps": len(gap_rows)}, sort_keys=True))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "error", "error_code": type(exc).__name__, "message": str(exc)[:500]}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
