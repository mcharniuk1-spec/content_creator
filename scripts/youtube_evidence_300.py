#!/usr/bin/env python3
"""Collect bounded public comments and subtitle transcripts for the 900-video cohort."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from m2_engine.secret_source import SecretSourceError, load_secret  # noqa: E402
from m2_engine.youtube_api import QuotaLedger, YouTubeAPIError, YouTubeDataAPIClient  # noqa: E402
from scripts.youtube_census import load_json, validate_config, validate_execution_authorization, write_jsonl  # noqa: E402


TIMECODE = re.compile(r"(?P<start>\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2}\.\d{3})")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def milliseconds(value: str) -> int:
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(".")
    return ((int(hours) * 60 + int(minutes)) * 60 + int(seconds)) * 1000 + int(millis)


def normalize_caption_text(lines: list[str]) -> str:
    value = " ".join(lines)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def parse_vtt_segments(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    segments: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        match = TIMECODE.search(lines[index])
        if not match:
            index += 1
            continue
        text_lines = []
        index += 1
        while index < len(lines) and lines[index].strip():
            text_lines.append(lines[index].strip())
            index += 1
        text = normalize_caption_text(text_lines)
        if text and (not segments or text != segments[-1]["text"]):
            segments.append({"start_ms": milliseconds(match.group("start")), "end_ms": milliseconds(match.group("end")), "text": text})
        index += 1
    return segments


def de_roll_caption_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Derive non-overlapping speech increments while retaining original cues."""
    emitted_normalized: list[str] = []
    speech: list[dict[str, Any]] = []
    for segment in segments:
        cue_tokens = segment.get("text", "").split()
        cue_normalized = [re.sub(r"(^\W+|\W+$)", "", token).casefold() for token in cue_tokens]
        overlap = 0
        for size in range(min(len(emitted_normalized), len(cue_normalized)), 0, -1):
            if emitted_normalized[-size:] == cue_normalized[:size]:
                overlap = size
                break
        new_tokens = cue_tokens[overlap:]
        new_normalized = cue_normalized[overlap:]
        if not any(new_normalized):
            continue
        emitted_normalized.extend(new_normalized)
        speech.append({
            "start_ms": segment["start_ms"],
            "end_ms": segment["end_ms"],
            "text": " ".join(new_tokens),
            "source_overlap_tokens": overlap,
        })
    return speech


def pseudonym(value: str | None) -> str | None:
    if not value:
        return None
    return "yt-author-" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def collect_comments(client: YouTubeDataAPIClient, run_dir: Path, max_comments: int) -> dict[str, int]:
    cohort = load_jsonl(run_dir / "derived" / "analyzed-content-cohort.jsonl")
    video_reported = {row["native_video_id"]: row.get("comment_count") for row in cohort}
    normalized_dir = run_dir / "normalized" / "comment-pages"
    coverage = []
    gap_rows = []
    new_requests = 0
    for index, row in enumerate(cohort, start=1):
        video_id = row["native_video_id"]
        try:
            result = client.get("commentThreads", "commentThreads.list", {
                "part": "snippet,replies",
                "videoId": video_id,
                "maxResults": str(max_comments),
                "order": "relevance",
                "textFormat": "plainText",
            }, estimated_units=1)
            if not result.resumed:
                new_requests += 1
            comments = []
            for thread in result.payload.get("items", []):
                top = thread.get("snippet", {}).get("topLevelComment", {})
                snippet = top.get("snippet", {})
                comment_id = top.get("id")
                if comment_id:
                    comments.append({
                        "schema": "north-hux.youtube-comment-observation.v1",
                        "native_video_id": video_id,
                        "native_comment_id": comment_id,
                        "native_parent_comment_id": None,
                        "text": snippet.get("textDisplay") or snippet.get("textOriginal"),
                        "author_pseudonym": pseudonym(snippet.get("authorChannelId", {}).get("value") or snippet.get("authorDisplayName")),
                        "like_count": snippet.get("likeCount"),
                        "published_at": snippet.get("publishedAt"),
                        "updated_at": snippet.get("updatedAt"),
                        "is_reply": False,
                        "source_request_fingerprint": result.fingerprint,
                        "raw_uri": result.raw_uri,
                        "raw_sha256": result.raw_sha256,
                    })
                for reply in thread.get("replies", {}).get("comments", []):
                    reply_snippet = reply.get("snippet", {})
                    reply_id = reply.get("id")
                    if not reply_id:
                        continue
                    comments.append({
                        "schema": "north-hux.youtube-comment-observation.v1",
                        "native_video_id": video_id,
                        "native_comment_id": reply_id,
                        "native_parent_comment_id": reply_snippet.get("parentId") or comment_id,
                        "text": reply_snippet.get("textDisplay") or reply_snippet.get("textOriginal"),
                        "author_pseudonym": pseudonym(reply_snippet.get("authorChannelId", {}).get("value") or reply_snippet.get("authorDisplayName")),
                        "like_count": reply_snippet.get("likeCount"),
                        "published_at": reply_snippet.get("publishedAt"),
                        "updated_at": reply_snippet.get("updatedAt"),
                        "is_reply": True,
                        "source_request_fingerprint": result.fingerprint,
                        "raw_uri": result.raw_uri,
                        "raw_sha256": result.raw_sha256,
                    })
            write_jsonl(normalized_dir / f"{video_id}.jsonl", comments)
            coverage.append({
                "native_video_id": video_id,
                "reported_count": video_reported.get(video_id),
                "retrieved_count": len(comments),
                "pagination_complete": not bool(result.payload.get("nextPageToken")),
                "sampling_method": f"official_commentThreads.list relevance first page maxResults={max_comments}; embedded replies only",
                "gap_reason": None if comments else "no_public_comment_rows_returned",
                "raw_uri": result.raw_uri,
            })
        except YouTubeAPIError as exc:
            if exc.global_stop:
                raise
            gap_rows.append({"native_video_id": video_id, "error_code": exc.code, "gap_reason": "comments_unavailable_or_disabled"})
            coverage.append({"native_video_id": video_id, "reported_count": video_reported.get(video_id), "retrieved_count": 0, "pagination_complete": False, "sampling_method": f"official_commentThreads.list relevance first page maxResults={max_comments}", "gap_reason": exc.code, "raw_uri": None})
        if index % 100 == 0:
            print(json.dumps({"progress": "comments", "videos": index, "new_requests": new_requests, "gaps": len(gap_rows)}), flush=True)
    all_comments = []
    for path in sorted(normalized_dir.glob("*.jsonl")):
        all_comments.extend(load_jsonl(path))
    write_jsonl(run_dir / "derived" / "comments.jsonl", sorted(all_comments, key=lambda item: (item["native_video_id"], item["native_parent_comment_id"] or "", item["native_comment_id"])))
    write_jsonl(run_dir / "derived" / "comment-coverage.jsonl", coverage)
    write_jsonl(run_dir / "derived" / "comment-gaps.jsonl", gap_rows)
    return {"cohort_videos": len(cohort), "new_requests": new_requests, "retrieved_comment_rows": len(all_comments), "videos_with_gaps": len(gap_rows), "videos_with_comments": len({row["native_video_id"] for row in all_comments})}


def transcript_source(files: list[Path], info: dict[str, Any], video_id: str) -> tuple[Path, str, str] | None:
    human = set(info.get("subtitles", {}))
    automatic = set(info.get("automatic_captions", {}))
    candidates = []
    for path in files:
        language = path.name[len(video_id):].lstrip(".").removesuffix(".vtt")
        base_language = language.split("-")[0]
        source_kind = "native_subtitle" if language in human or base_language in human else "native_caption" if language in automatic or base_language in automatic else "native_caption_source_unresolved"
        source_rank = 0 if source_kind == "native_subtitle" else 1 if source_kind == "native_caption" else 2
        language_rank = 0 if language == "en" else 1 if language.startswith("en-") else 2
        candidates.append((source_rank, language_rank, path.name, path, source_kind, language))
    if not candidates:
        return None
    _, _, _, path, source_kind, language = min(candidates)
    return path, source_kind, language


def collect_one_transcript(run_dir: Path, row: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    video_id = row["native_video_id"]
    normalized_path = run_dir / "normalized" / "transcripts" / f"{video_id}.json"
    if normalized_path.is_file():
        return json.loads(normalized_path.read_text(encoding="utf-8"))
    raw_dir = run_dir / "raw" / "subtitles" / video_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    output = raw_dir / f"{video_id}.%(ext)s"
    args = [
        "yt-dlp", "--no-cookies", "--no-cookies-from-browser", "--no-cache-dir", "--no-playlist",
        "--skip-download", "--write-subs", "--write-auto-subs", "--write-info-json",
        "--sub-langs", "en.*,en", "--sub-format", "vtt", "--socket-timeout", "20", "--retries", "1",
        "-o", str(output), row["canonical_url"],
    ]
    started = datetime.now(UTC).isoformat()
    try:
        completed = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout_seconds, check=False, env={**os.environ, "PYTHONUNBUFFERED": "1"})
        exit_code = completed.returncode
        stderr = completed.stderr or ""
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stderr = str(exc)
    info_path = raw_dir / f"{video_id}.info.json"
    info = json.loads(info_path.read_text(encoding="utf-8")) if info_path.is_file() else {}
    selected = transcript_source(sorted(raw_dir.glob(f"{video_id}*.vtt")), info, video_id)
    if selected:
        source_file, source_kind, language = selected
        segments = parse_vtt_segments(source_file)
        speech_segments = de_roll_caption_segments(segments)
        raw_word_count = sum(len(segment["text"].split()) for segment in segments)
        speech_word_count = sum(len(segment["text"].split()) for segment in speech_segments)
        quality = "usable" if speech_segments else "review"
        result = {
            "schema": "north-hux.youtube-transcript-artifact.v2",
            "native_channel_id": row["native_channel_id"],
            "native_video_id": video_id,
            "canonical_url": row["canonical_url"],
            "source_kind": source_kind,
            "language": language,
            "quality_state": quality,
            "source_uri": source_file.relative_to(run_dir).as_posix(),
            "source_sha256": hashlib.sha256(source_file.read_bytes()).hexdigest(),
            "segments": segments,
            "segment_count": len(segments),
            "text": " ".join(segment["text"] for segment in segments),
            "speech_segments": speech_segments,
            "speech_segment_count": len(speech_segments),
            "speech_text": " ".join(segment["text"] for segment in speech_segments),
            "raw_word_count": raw_word_count,
            "speech_word_count": speech_word_count,
            "rolling_caption_expansion_ratio": round(raw_word_count / speech_word_count, 4) if speech_word_count else None,
            "normalization_method": "longest_exact_token_overlap_v1",
            "captured_at": datetime.now(UTC).isoformat(),
            "availability": "observed",
        }
    else:
        lowered = stderr.lower()
        stop = "provider_auth_required" if "sign in to confirm" in lowered or "login required" in lowered else "rate_limited" if "429" in lowered or "too many requests" in lowered else None
        result = {
            "schema": "north-hux.youtube-transcript-artifact.v2",
            "native_channel_id": row["native_channel_id"],
            "native_video_id": video_id,
            "canonical_url": row["canonical_url"],
            "source_kind": "none",
            "language": None,
            "quality_state": "blocked" if stop else "not_run",
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
            "gap_reason": stop or "no_public_english_subtitle",
        }
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt = {
        "schema": "archflow.command-receipt.v1",
        "label": "public_subtitle_collection",
        "native_video_id": video_id,
        "started_at": started,
        "finished_at": datetime.now(UTC).isoformat(),
        "argv": args,
        "exit_code": exit_code,
        "stderr_sha256": hashlib.sha256(stderr.encode("utf-8")).hexdigest(),
        "availability": result["availability"],
    }
    receipt_path = run_dir / "receipts" / "subtitles" / f"{video_id}.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def collect_transcripts(run_dir: Path, workers: int, timeout_seconds: int) -> dict[str, int]:
    cohort = load_jsonl(run_dir / "derived" / "analyzed-content-cohort.jsonl")
    results = []
    consecutive_terminal = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(collect_one_transcript, run_dir, row, timeout_seconds): row["native_video_id"] for row in cohort}
        for index, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            if result.get("gap_reason") in {"provider_auth_required", "rate_limited"}:
                consecutive_terminal += 1
            else:
                consecutive_terminal = 0
            if consecutive_terminal >= 5:
                for pending in futures:
                    pending.cancel()
                raise ValueError("five consecutive terminal subtitle failures")
            if index % 100 == 0:
                print(json.dumps({"progress": "transcripts", "videos": index, "observed": sum(row["availability"] == "observed" for row in results)}), flush=True)
    write_jsonl(run_dir / "derived" / "transcripts.jsonl", sorted(results, key=lambda row: row["native_video_id"]))
    return {"cohort_videos": len(cohort), "transcripts_observed": sum(row["availability"] == "observed" for row in results), "transcript_gaps": sum(row["availability"] != "observed" for row in results), "segments": sum(int(row.get("segment_count") or 0) for row in results)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--config", default=ROOT / "config/youtube-census-v1.json", type=Path)
    parser.add_argument("--secret-file", required=True, type=Path)
    parser.add_argument("--authorization-receipt", required=True, type=Path)
    parser.add_argument("--stage", choices=("comments", "transcripts"), required=True)
    parser.add_argument("--max-comments", type=int, default=20)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    args = parser.parse_args()
    try:
        config = load_json(args.config)
        validate_config(config)
        validate_execution_authorization(args.authorization_receipt, args.run_dir)
        if args.stage == "transcripts":
            summary = collect_transcripts(args.run_dir, args.workers, args.timeout_seconds)
        else:
            key = load_secret("youtube", secret_file=args.secret_file)
            quota = QuotaLedger(args.run_dir / "ledgers" / "youtube-api-quota.jsonl", daily_unit_budget=int(config["daily_limits"]["api_units"]), daily_search_call_budget=int(config["daily_limits"]["local_search_call_budget"]))
            client = YouTubeDataAPIClient(api_key=key, run_dir=args.run_dir, quota=quota, timeout_seconds=float(config["request"]["timeout_seconds"]), max_attempts=int(config["request"]["max_attempts"]), min_interval_seconds=float(config["request"]["min_interval_seconds"]))
            summary = collect_comments(client, args.run_dir, args.max_comments)
            summary["quota_usage_today"] = quota.usage()
        print(json.dumps({"schema": "north-hux.youtube-evidence-stage.v1", "stage": args.stage, "status": "pass", **summary}, sort_keys=True))
        return 0
    except (OSError, ValueError, SecretSourceError, YouTubeAPIError) as exc:
        code = exc.code if isinstance(exc, YouTubeAPIError) else type(exc).__name__
        print(json.dumps({"status": "error", "error_code": code, "message": str(exc)[:500]}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
