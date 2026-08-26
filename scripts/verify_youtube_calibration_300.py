#!/usr/bin/env python3
"""Verify the frozen 300-account YouTube calibration and emit a final receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg


DEFAULT_DSN = "host=127.0.0.1 port=55432 dbname=north_hux"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verify_pointer(run_dir: Path, pointer: str, expected_sha: str) -> None:
    path = (run_dir / pointer).resolve()
    require(path.is_relative_to(run_dir), f"pointer escapes run directory: {pointer}")
    require(path.is_file(), f"missing evidence pointer: {pointer}")
    require(digest(path) == expected_sha, f"hash mismatch: {pointer}")


def database_counts(dsn: str, account_ids: list[str], video_ids: list[str]) -> dict[str, int]:
    with psycopg.connect(dsn) as connection:
        connection.execute("SET search_path=north_hux,public")
        counts = {
            "accounts": connection.execute(
                "SELECT count(*) FROM platform_account WHERE platform='youtube' AND native_account_id=ANY(%s)",
                (account_ids,),
            ).fetchone()[0],
            "content": connection.execute(
                "SELECT count(*) FROM content_item WHERE platform='youtube' AND native_content_id=ANY(%s)",
                (video_ids,),
            ).fetchone()[0],
            "comments": connection.execute(
                """SELECT count(*) FROM comment c JOIN content_item i USING(content_id)
                   WHERE i.platform='youtube' AND i.native_content_id=ANY(%s)""",
                (video_ids,),
            ).fetchone()[0],
            "comment_page_raw_objects": connection.execute(
                """SELECT count(*) FROM raw_object
                   WHERE platform='youtube' AND native_object_type='comment_page'
                   AND native_object_id=ANY(%s)""",
                (video_ids,),
            ).fetchone()[0],
            "comments_with_comment_page_evidence": connection.execute(
                """SELECT count(*) FROM comment c JOIN content_item i USING(content_id)
                   JOIN raw_object r ON r.raw_object_id=c.raw_object_id
                   WHERE i.platform='youtube' AND i.native_content_id=ANY(%s)
                   AND r.native_object_type='comment_page'""",
                (video_ids,),
            ).fetchone()[0],
            "comment_coverage_with_comment_page_evidence": connection.execute(
                """SELECT count(*) FROM interaction_coverage x JOIN content_item i USING(content_id)
                   JOIN raw_object r ON r.raw_object_id=x.raw_object_id
                   WHERE i.platform='youtube' AND i.native_content_id=ANY(%s)
                   AND x.interaction_type='comment' AND r.native_object_type='comment_page'""",
                (video_ids,),
            ).fetchone()[0],
            "raw_transcripts": connection.execute(
                """SELECT count(*) FROM transcript t JOIN content_item i USING(content_id)
                   WHERE i.platform='youtube' AND i.native_content_id=ANY(%s) AND t.model_name IS NULL""",
                (video_ids,),
            ).fetchone()[0],
            "raw_segments": connection.execute(
                """SELECT count(*) FROM transcript_segment s JOIN transcript t USING(transcript_id)
                   JOIN content_item i USING(content_id)
                   WHERE i.platform='youtube' AND i.native_content_id=ANY(%s) AND t.model_name IS NULL""",
                (video_ids,),
            ).fetchone()[0],
            "speech_transcripts": connection.execute(
                """SELECT count(*) FROM transcript t JOIN content_item i USING(content_id)
                   WHERE i.platform='youtube' AND i.native_content_id=ANY(%s)
                   AND t.model_name='north_hux_caption_deroll'
                   AND t.model_version='longest_exact_token_overlap_v1'""",
                (video_ids,),
            ).fetchone()[0],
            "speech_segments": connection.execute(
                """SELECT count(*) FROM transcript_segment s JOIN transcript t USING(transcript_id)
                   JOIN content_item i USING(content_id)
                   WHERE i.platform='youtube' AND i.native_content_id=ANY(%s)
                   AND t.model_name='north_hux_caption_deroll'
                   AND t.model_version='longest_exact_token_overlap_v1'""",
                (video_ids,),
            ).fetchone()[0],
            "media": connection.execute(
                """SELECT count(*) FROM media_asset m JOIN content_item i USING(content_id)
                   WHERE i.platform='youtube' AND i.native_content_id=ANY(%s)""",
                (video_ids,),
            ).fetchone()[0],
            "frames": connection.execute(
                """SELECT count(*) FROM frame_artifact f JOIN media_asset m USING(media_asset_id)
                   JOIN content_item i USING(content_id)
                   WHERE i.platform='youtube' AND i.native_content_id=ANY(%s)""",
                (video_ids,),
            ).fetchone()[0],
            "content_classifications": connection.execute(
                """SELECT count(*) FROM classification c JOIN content_item i USING(content_id)
                   WHERE i.platform='youtube' AND i.native_content_id=ANY(%s)""",
                (video_ids,),
            ).fetchone()[0],
            "account_classifications": connection.execute(
                """SELECT count(*) FROM classification c JOIN platform_account a USING(account_id)
                   WHERE a.platform='youtube' AND a.native_account_id=ANY(%s)""",
                (account_ids,),
            ).fetchone()[0],
            "source_identity_duplicates": connection.execute(
                """SELECT count(*) FROM (
                   SELECT platform,source_type,native_id FROM source_registry
                   GROUP BY platform,source_type,native_id HAVING count(*) > 1
                   ) AS duplicates"""
            ).fetchone()[0],
        }
    return counts


def verify_pdf(path: Path) -> int:
    info = subprocess.run(["pdfinfo", str(path)], check=True, capture_output=True, text=True).stdout
    match = re.search(r"^Pages:\s+(\d+)$", info, flags=re.MULTILINE)
    require(match is not None, "PDF page count is unavailable")
    pages = int(match.group(1))
    extracted = subprocess.run(["pdftotext", "-layout", str(path), "-"], check=True,
                               capture_output=True, text=True).stdout
    page_text = extracted.split("\f")
    if page_text and not page_text[-1].strip():
        page_text.pop()
    require(len(page_text) == pages, "PDF text page count mismatch")
    require(all(page.strip() for page in page_text), "PDF contains an empty page")
    return pages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--dsn", default=DEFAULT_DSN)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    pdf = args.pdf.resolve()
    output = (args.output or run_dir / "verification-receipt.json").resolve()

    accounts = read_jsonl(run_dir / "derived" / "qualified-accounts.jsonl")
    videos = read_jsonl(run_dir / "derived" / "analyzed-content-cohort.jsonl")
    top = read_jsonl(run_dir / "derived" / "top-reference-cohort.jsonl")
    transcripts = read_jsonl(run_dir / "derived" / "transcripts.jsonl")
    comments = read_jsonl(run_dir / "derived" / "comments.jsonl")
    coverage = read_jsonl(run_dir / "derived" / "comment-coverage.jsonl")
    comment_gaps = read_jsonl(run_dir / "derived" / "comment-gaps.jsonl")
    media = read_jsonl(run_dir / "derived" / "media-assets.jsonl")
    frames = read_jsonl(run_dir / "derived" / "frame-artifacts.jsonl")
    frame_gaps = read_jsonl(run_dir / "derived" / "frame-gaps.jsonl")
    analysis = read_jsonl(run_dir / "derived" / "video-analysis.jsonl")
    account_analysis = read_jsonl(run_dir / "derived" / "account-analysis.jsonl")
    analysis_summary = json.loads((run_dir / "derived" / "analysis-summary.json").read_text(encoding="utf-8"))
    relevance_sample = read_jsonl(run_dir / "derived" / "relevance-audit-sample.jsonl")
    relevance_review = read_jsonl(run_dir / "derived" / "independent-relevance-review.jsonl")

    account_ids = [row["native_channel_id"] for row in accounts]
    video_ids = [row["native_video_id"] for row in videos]
    contribution = Counter(row["native_channel_id"] for row in videos)
    observed_transcripts = [row for row in transcripts if row.get("availability") == "observed"]
    segment_count = sum(len(row.get("segments") or []) for row in observed_transcripts)
    speech_segment_count = sum(len(row.get("speech_segments") or []) for row in observed_transcripts)

    require(len(accounts) == len(set(account_ids)) == 300, "qualified account denominator is not exact")
    require(len(videos) == len(set(video_ids)) == 900, "video denominator is not exact")
    require(set(contribution.values()) == {3}, "each creator must contribute exactly three videos")
    require(max(contribution.values()) / len(videos) <= 0.01, "creator contribution exceeds one percent")
    require(len(top) == 100, "top-reference denominator is not exact")
    require(len({row["native_channel_id"] for row in top}) == 100, "top references are not one per creator")
    require(len({row["native_video_id"] for row in top}) == 100, "top-reference videos are not unique")
    require({row["native_video_id"] for row in top}.issubset(set(video_ids)), "top reference outside analyzed cohort")
    require(len(transcripts) == 900 and len(observed_transcripts) == 772, "transcript denominator mismatch")
    require(segment_count == 73339, "transcript segment denominator mismatch")
    require(speech_segment_count == 38960, "de-rolled speech segment denominator mismatch")
    require(len(comments) == 898 and len(coverage) == 900 and len(comment_gaps) == 16,
            "comment denominator mismatch")
    require(len(media) == 100 and len(frames) == 943 and not frame_gaps, "visual denominator mismatch")
    require({row["native_video_id"] for row in media} == {row["native_video_id"] for row in top},
            "visual sets do not match the top-reference cohort")
    require(len(analysis) == 900 and len(account_analysis) == 300, "analysis denominator mismatch")
    require(len(relevance_sample) == len(relevance_review) == 250, "relevance review denominator mismatch")
    require({row["native_video_id"] for row in relevance_sample} ==
            {row["native_video_id"] for row in relevance_review}, "relevance review sample mismatch")
    require(sum(row.get("sample_stratum") == "top100" for row in relevance_review) == 100,
            "top-100 relevance review mismatch")
    accepted_labels = {"direct_agentic_business", "technical_agentic_authority", "adjacent_ai_business"}
    relevance_accepted = sum(row.get("review_label") in accepted_labels for row in relevance_review)
    require(relevance_accepted == analysis_summary["derived"]["independent_relevance_review"]["accepted_count"],
            "independent relevance acceptance denominator mismatch")

    pointer_checks = 0
    for name in ("channel-snapshots.jsonl", "analyzed-content-cohort.jsonl"):
        for row in read_jsonl(run_dir / "derived" / name):
            verify_pointer(run_dir, row["raw_uri"], row["raw_sha256"])
            pointer_checks += 1
    for row in observed_transcripts:
        verify_pointer(run_dir, row["source_uri"], row["source_sha256"])
        pointer_checks += 1
    request_receipts = read_jsonl(run_dir / "ledgers" / "youtube-api-requests.jsonl")
    receipts_by_uri = {
        row["raw_uri"]: row for row in request_receipts
        if row.get("operation") == "commentThreads.list" and row.get("status") == "success" and row.get("raw_uri")
    }
    for row in coverage:
        if row.get("raw_uri"):
            receipt = receipts_by_uri.get(row["raw_uri"])
            require(receipt is not None, f"missing comment request receipt: {row['raw_uri']}")
            verify_pointer(run_dir, row["raw_uri"], receipt["raw_sha256"])
            pointer_checks += 1
    for row in media:
        verify_pointer(run_dir, row["asset_uri"], row["sha256"])
        pointer_checks += 1
    for row in frames:
        verify_pointer(run_dir, row["frame_uri"], row["sha256"])
        pointer_checks += 1

    require(pdf.is_file(), "PDF report is missing")
    pdf_pages = verify_pdf(pdf)
    require(pdf_pages == 35, "PDF page count mismatch")
    db = database_counts(args.dsn, account_ids, video_ids)
    expected_db = {
        "accounts": 300,
        "content": 900,
        "comments": 898,
        "comment_page_raw_objects": 884,
        "comments_with_comment_page_evidence": 898,
        "comment_coverage_with_comment_page_evidence": 884,
        "raw_transcripts": 772,
        "raw_segments": 73339,
        "speech_transcripts": 772,
        "speech_segments": 38960,
        "media": 100,
        "frames": 943,
        "content_classifications": 5000,
        "account_classifications": 600,
        "source_identity_duplicates": 0,
    }
    require(db == expected_db, f"database readback mismatch: {db}")

    receipt = {
        "schema": "north-hux.youtube-calibration-verification.v1",
        "run_key": run_dir.name,
        "verified_at": datetime.now(UTC).isoformat(),
        "status": "PASS_WITH_LIMITATIONS",
        "limitations": [
            "duration candidates are not claimed as native Shorts",
            "comment retrieval is bounded and incomplete",
            "40 visual sets use low-resolution public storyboard fallbacks",
            "taxonomy labels remain deterministic and human-reviewable",
        ],
        "file_evidence": {
            "qualified_accounts": len(accounts),
            "analyzed_videos": len(videos),
            "top_references": len(top),
            "observed_transcripts": len(observed_transcripts),
            "transcript_gaps": len(transcripts) - len(observed_transcripts),
            "transcript_segments": segment_count,
            "speech_segments": speech_segment_count,
            "comments": len(comments),
            "comment_gaps": len(comment_gaps),
            "visual_sets": len(media),
            "frames": len(frames),
            "independent_relevance_reviews": len(relevance_review),
            "independent_relevance_accepted": relevance_accepted,
            "verified_file_pointers": pointer_checks,
        },
        "database_readback": db,
        "pdf": {"path": str(pdf), "pages": pdf_pages, "sha256": digest(pdf)},
    }
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "receipt": str(output), "pointer_checks": pointer_checks,
                      "pdf_sha256": receipt["pdf"]["sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
