from pathlib import Path

import pytest

from scripts.youtube_evidence_10k import (
    COLLECTOR_VERSION,
    ConcurrentClaimError,
    DiskReserveError,
    artifact_claim,
    ensure_disk_reserve,
    pick_indexes,
    reusable_attempt,
    sha256,
    transcript_artifact_valid,
    write_json,
)


def test_pick_indexes_is_bounded_and_keeps_endpoints():
    indexes = pick_indexes(100, 6)
    assert len(indexes) == 6
    assert indexes[0] == 0
    assert indexes[-1] == 99
    assert indexes == sorted(set(indexes))


def test_pick_indexes_keeps_small_storyboard():
    assert pick_indexes(3, 6) == [0, 1, 2]
    assert pick_indexes(0, 6) == []


def test_disk_reserve_stops_before_write(tmp_path: Path):
    with pytest.raises(DiskReserveError):
        ensure_disk_reserve(tmp_path, minimum_free_bytes=100, free_override=99)
    ensure_disk_reserve(tmp_path, minimum_free_bytes=100, free_override=100)
    with pytest.raises(ValueError, match="positive"):
        ensure_disk_reserve(tmp_path, minimum_free_bytes=0, free_override=100)


def test_resume_retries_route_terminal_gaps_but_reuses_permanent_outcomes():
    assert reusable_attempt({"availability": "observed"}, "availability", "observed") is True
    assert reusable_attempt(
        {"collector_version": "youtube_evidence_10k.v2", "gap_reason": "no_public_english_subtitle"},
        "availability",
        "observed",
    ) is True
    assert reusable_attempt(
        {"collector_version": "youtube_evidence_10k.v2", "gap_reason": "rate_limited"},
        "availability",
        "observed",
    ) is False


def test_transcript_restart_requires_valid_source_and_metadata_hashes(tmp_path: Path):
    run = tmp_path / "run"
    source = run / "raw" / "subtitles" / "v1" / "v1.en.vtt"
    metadata = source.parent / "source-metadata.json"
    source.parent.mkdir(parents=True)
    source.write_text("WEBVTT\n", encoding="utf-8")
    write_json(metadata, {"id": "v1"})
    manifest = run / "normalized" / "transcripts" / "v1.json"
    payload = {
        "native_video_id": "v1",
        "availability": "observed",
        "collector_version": COLLECTOR_VERSION,
        "source_uri": source.relative_to(run).as_posix(),
        "source_sha256": sha256(source),
        "source_metadata_uri": metadata.relative_to(run).as_posix(),
        "source_metadata_sha256": sha256(metadata),
    }
    write_json(manifest, payload)
    assert transcript_artifact_valid(run, manifest, payload) is True
    source.write_text("changed\n", encoding="utf-8")
    assert transcript_artifact_valid(run, manifest, payload) is False


def test_artifact_claim_blocks_a_second_live_writer(tmp_path: Path):
    with artifact_claim(tmp_path, "transcripts", "v1", stale_seconds=300):
        with pytest.raises(ConcurrentClaimError):
            with artifact_claim(tmp_path, "transcripts", "v1", stale_seconds=300):
                pass
