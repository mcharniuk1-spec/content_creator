import multiprocessing
import threading
from pathlib import Path

import pytest

from scripts.youtube_evidence_10k import (
    COLLECTOR_VERSION,
    ConcurrentClaimError,
    DiskReserveError,
    artifact_claim,
    active_artifact_claims,
    assert_run_mutable,
    confined_reuse_paths,
    ensure_disk_reserve,
    next_wave_size,
    pick_indexes,
    reusable_attempt,
    sha256,
    frame_artifact_valid,
    stage_lock,
    strike_receipt_path,
    transcript_artifact_valid,
    write_json,
)


def _hold_shared_stage_lock(run_path: str, ready, release):
    with stage_lock(Path(run_path), "run-data", exclusive=False):
        ready.set()
        release.wait(5)


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


def test_next_wave_never_schedules_past_fifth_terminal_strike():
    assert next_wave_size(8, 0) == 5
    assert next_wave_size(8, 4) == 1
    with pytest.raises(ValueError):
        next_wave_size(8, 5)


def test_five_strike_ledger_is_global_per_stage_not_slice(tmp_path: Path):
    assert strike_receipt_path(tmp_path, "transcripts") == tmp_path / "receipts" / "transcripts-strike-state.json"


def test_terminal_freeze_blocks_new_writers(tmp_path: Path):
    marker = tmp_path / "receipts" / "terminal-freeze.json"
    write_json(marker, {"status": "pass_with_limitations"})
    with pytest.raises(ValueError, match="terminally frozen"):
        assert_run_mutable(tmp_path)


def test_exclusive_stage_lock_waits_for_cross_process_shared_writer(tmp_path: Path):
    context = multiprocessing.get_context("fork")
    ready = context.Event()
    release = context.Event()
    process = context.Process(target=_hold_shared_stage_lock, args=(str(tmp_path), ready, release))
    process.start()
    assert ready.wait(2)
    acquired = threading.Event()

    def take_exclusive():
        with stage_lock(tmp_path, "run-data", exclusive=True):
            acquired.set()

    thread = threading.Thread(target=take_exclusive)
    thread.start()
    assert not acquired.wait(0.15)
    release.set()
    assert acquired.wait(2)
    thread.join(2)
    process.join(2)
    assert process.exitcode == 0


def test_reuse_uri_cannot_escape_either_run(tmp_path: Path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    with pytest.raises(ValueError, match="escapes"):
        confined_reuse_paths(source, target, "../outside.bin")


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
    write_json(
        run / "receipts" / "subtitles" / "v1.json",
        {"native_video_id": "v1", "availability": "observed"},
    )
    write_json(manifest, payload)
    assert transcript_artifact_valid(run, manifest, payload) is True
    source.write_text("changed\n", encoding="utf-8")
    assert transcript_artifact_valid(run, manifest, payload) is False


def test_frame_validation_requires_media_identity_contiguous_indexes_and_hashes(tmp_path: Path):
    run = tmp_path / "run"
    media = run / "raw" / "storyboards" / "v1" / "v1.mhtml"
    frame = run / "derived" / "frames" / "v1" / "sb-00.jpg"
    media.parent.mkdir(parents=True)
    frame.parent.mkdir(parents=True)
    media.write_bytes(b"media")
    frame.write_bytes(b"frame")
    manifest = run / "normalized" / "frame-manifests" / "v1.json"
    payload = {
        "native_video_id": "v1",
        "status": "observed",
        "collector_version": COLLECTOR_VERSION,
        "media": {
            "native_video_id": "v1",
            "asset_uri": media.relative_to(run).as_posix(),
            "sha256": sha256(media),
        },
        "frames": [{
            "native_video_id": "v1",
            "frame_index": 0,
            "timestamp_ms": 0,
            "frame_uri": frame.relative_to(run).as_posix(),
            "sha256": sha256(frame),
        }],
    }
    write_json(run / "receipts" / "storyboards" / "v1.json", {"native_video_id": "v1", "status": "observed"})
    write_json(manifest, payload)
    assert frame_artifact_valid(run, manifest, payload) is True
    payload["frames"][0]["frame_index"] = 1
    assert frame_artifact_valid(run, manifest, payload) is False


def test_artifact_claim_blocks_a_second_live_writer(tmp_path: Path):
    with artifact_claim(tmp_path, "transcripts", "v1", stale_seconds=300):
        with pytest.raises(ConcurrentClaimError):
            with artifact_claim(tmp_path, "transcripts", "v1", stale_seconds=300):
                pass


def test_reuse_and_live_collection_share_the_same_logical_claim_namespace(tmp_path: Path):
    with artifact_claim(tmp_path, "transcripts", "v1", stale_seconds=300):
        with pytest.raises(ConcurrentClaimError):
            with artifact_claim(tmp_path, "transcripts", "v1", stale_seconds=600):
                pass


def test_stale_or_dead_claim_is_recovered_for_terminal_freeze(tmp_path: Path):
    claim = tmp_path / "locks" / "frames" / "v1.lock"
    write_json(claim, {"pid": 99999999, "created_at": "2020-01-01T00:00:00Z"})
    active, removed = active_artifact_claims(tmp_path, stale_seconds=900)
    assert active == []
    assert removed == [claim]
    assert not claim.exists()
