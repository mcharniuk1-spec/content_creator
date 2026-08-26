#!/usr/bin/env python3
"""Recover top-reference visual evidence from YouTube's public storyboard surface."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any

from PIL import Image


TIMESTAMP = re.compile(r"Slide #\d+: (\d{2}:\d{2}:\d{2},\d{3})")


def jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def millis(value: str) -> int:
    hours, minutes, rest = value.replace(",", ".").split(":")
    return round((int(hours) * 3600 + int(minutes) * 60 + float(rest)) * 1000)


def pick_indexes(size: int, limit: int = 12) -> list[int]:
    if size <= limit:
        return list(range(size))
    return sorted({round(index * (size - 1) / (limit - 1)) for index in range(limit)})


def process(run_dir: Path, row: dict[str, Any], timeout: int) -> dict[str, Any]:
    video_id = row["native_video_id"]
    raw_dir = run_dir / "raw" / "storyboards" / video_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    mhtml = raw_dir / f"{video_id}.mhtml"
    if not mhtml.is_file():
        command = [
            "yt-dlp", "--no-cookies", "--no-cookies-from-browser", "--no-cache-dir", "--no-playlist",
            "-f", "sb0", "--socket-timeout", "20", "--retries", "1", "-o", str(raw_dir / f"{video_id}.%(ext)s"),
            row["canonical_url"],
        ]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False,
                                       env={**os.environ, "PYTHONUNBUFFERED": "1"})
        except subprocess.TimeoutExpired as exc:
            return {"native_video_id": video_id, "status": "gap", "gap_reason": "storyboard_timeout",
                    "stderr_sha256": hashlib.sha256(str(exc).encode()).hexdigest()}
        if completed.returncode != 0 or not mhtml.is_file():
            stderr = completed.stderr or ""
            lowered = stderr.lower()
            terminal = "provider_auth_required" if "sign in to confirm" in lowered else "rate_limited" if "429" in lowered else None
            return {"native_video_id": video_id, "status": "gap", "gap_reason": terminal or "public_storyboard_unavailable",
                    "terminal_class": terminal, "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest()}
    message = BytesParser(policy=policy.default).parsebytes(mhtml.read_bytes())
    html_part = next((part for part in message.walk() if part.get_content_type() == "text/html"), None)
    html_text = html_part.get_content() if html_part else ""
    starts = [millis(value) for value in TIMESTAMP.findall(html_text)]
    images = [part for part in message.walk() if part.get_content_maintype() == "image"]
    indexes = pick_indexes(len(images))
    frames = []
    width = height = None
    for frame_index, source_index in enumerate(indexes):
        payload = images[source_index].get_payload(decode=True)
        frame_path = run_dir / "derived" / "frames" / video_id / f"sb-{frame_index:02d}-{(starts[source_index] if source_index < len(starts) else 0):08d}.jpg"
        frame_path.parent.mkdir(parents=True, exist_ok=True)
        frame_path.write_bytes(payload)
        with Image.open(frame_path) as image:
            width, height = image.size
        frames.append({
            "schema": "north-hux.youtube-frame-artifact.v1",
            "native_channel_id": row["native_channel_id"],
            "native_video_id": video_id,
            "frame_index": frame_index,
            "timestamp_ms": starts[source_index] if source_index < len(starts) else 0,
            "frame_uri": frame_path.relative_to(run_dir).as_posix(),
            "sha256": sha(frame_path),
            "selection_basis": "youtube_public_storyboard_sb0_interval_anchor",
            "quality_tier": "storyboard_low_resolution_fallback",
            "public_display_allowed": False,
        })
    if not frames:
        return {"native_video_id": video_id, "status": "gap", "gap_reason": "storyboard_has_no_images"}
    media = {
        "schema": "north-hux.youtube-media-asset.v1",
        "native_channel_id": row["native_channel_id"],
        "native_video_id": video_id,
        "asset_kind": "preview",
        "asset_uri": mhtml.relative_to(run_dir).as_posix(),
        "sha256": sha(mhtml),
        "byte_size": mhtml.stat().st_size,
        "duration_ms": round((row.get("duration_seconds") or 0) * 1000),
        "width": width,
        "height": height,
        "rights_state": "local_reference_only_owner_approved",
        "retention_until": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
        "public_display_allowed": False,
        "quality_tier": "storyboard_low_resolution_fallback",
    }
    return {"native_video_id": video_id, "status": "observed", "media": media, "frames": frames}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    top = {row["native_video_id"]: row for row in jsonl(run_dir / "derived" / "top-reference-cohort.jsonl")}
    gaps = jsonl(run_dir / "derived" / "frame-gaps.jsonl")
    rows = [top[item["native_video_id"]] for item in gaps if item["native_video_id"] in top]
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(process, run_dir, row, args.timeout_seconds) for row in rows]
        for index, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            if index % 10 == 0:
                print(json.dumps({"progress": "storyboards", "processed": index,
                                  "observed": sum(row.get("status") == "observed" for row in results)}), flush=True)
    existing_media = {row["native_video_id"]: row for row in jsonl(run_dir / "derived" / "media-assets.jsonl")}
    existing_frames: dict[str, list[dict[str, Any]]] = {}
    for row in jsonl(run_dir / "derived" / "frame-artifacts.jsonl"):
        existing_frames.setdefault(row["native_video_id"], []).append(row)
    for result in results:
        if result.get("status") == "observed":
            existing_media[result["native_video_id"]] = result["media"]
            existing_frames[result["native_video_id"]] = result["frames"]
    final_gaps = [row for row in results if row.get("status") != "observed"]
    write_jsonl(run_dir / "derived" / "media-assets.jsonl", sorted(existing_media.values(), key=lambda row: row["native_video_id"]))
    write_jsonl(run_dir / "derived" / "frame-artifacts.jsonl",
                sorted([frame for rows in existing_frames.values() for frame in rows], key=lambda row: (row["native_video_id"], row["frame_index"])))
    write_jsonl(run_dir / "derived" / "frame-gaps.jsonl", final_gaps)
    print(json.dumps({"status": "pass_with_limitations" if final_gaps else "pass", "requested_fallbacks": len(rows),
                      "storyboards_observed": sum(row.get("status") == "observed" for row in results),
                      "final_visual_sets": len(existing_media), "final_gaps": len(final_gaps)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
