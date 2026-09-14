import hashlib
import json
import os

import pytest

from m2_orchestrator.media_acquisition import AcquisitionError, stable_hash
import m2_orchestrator.media_recovery as recovery
from m2_orchestrator.media_recovery import classify_metadata, recover_video


URL_VIDEO = "https://cdninstagram.com/video.mp4"
URL_AUDIO = "https://cdninstagram.com/audio.mp4"
URL_MUXED = "https://cdninstagram.com/muxed.mp4"


def metadata(code="B-MYSMhHXy6", formats=None):
    return {"id": code, "display_id": code, "formats": formats or []}


def fmt(url, *, vcodec=None, acodec=None, format_id="1"):
    return {"url": url, "ext": "mp4", "vcodec": vcodec, "acodec": acodec, "format_id": format_id}


def test_identity_mismatch_is_rejected_before_format_classification():
    with pytest.raises(AcquisitionError, match="EXTRACTOR_IDENTITY_MISMATCH"):
        classify_metadata("B-MYSMhHXy6", metadata("different"))


def test_conflicting_extractor_identity_fields_are_rejected():
    with pytest.raises(AcquisitionError, match="EXTRACTOR_IDENTITY_MISMATCH"):
        classify_metadata(
            "B-MYSMhHXy6",
            {"id": "B-MYSMhHXy6", "display_id": "different", "formats": []},
        )


def test_audio_only_is_never_selected_as_video():
    result = classify_metadata(
        "B-MYSMhHXy6", metadata(formats=[fmt(URL_AUDIO, acodec="aac")])
    )
    assert result["classification"] == "no_supported_video"
    assert result["selected"] is None
    assert result["audio_only"][0]["route"] == "audio_only"


def test_non_mp4_audio_only_format_counts_for_split_detection():
    result = classify_metadata(
        "B-MYSMhHXy6",
        metadata(
            formats=[
                fmt(URL_VIDEO, vcodec="avc1", acodec="none"),
                {**fmt("https://cdninstagram.com/audio.m4a", vcodec="none", acodec="aac"), "ext": "m4a"},
            ]
        ),
    )
    assert result["classification"] == "split_streams_needing_merge"


def test_muxed_format_is_preferred_over_video_only():
    result = classify_metadata(
        "B-MYSMhHXy6",
        metadata(
            formats=[
                fmt(URL_VIDEO, vcodec="avc1", acodec="none"),
                fmt(URL_MUXED, vcodec="avc1", acodec="aac"),
            ]
        ),
    )
    assert result["classification"] == "muxed"
    assert result["selected"]["url"] == URL_MUXED


def test_codec_metadata_can_upgrade_a_duplicate_url_to_muxed():
    result = classify_metadata(
        "B-MYSMhHXy6",
        metadata(
            formats=[
                fmt(URL_MUXED, vcodec=None, acodec=None, format_id="placeholder"),
                fmt(URL_MUXED, vcodec="avc1", acodec="aac", format_id="muxed"),
            ]
        ),
    )
    assert result["classification"] == "muxed"
    assert result["selected"]["format_id"] == "muxed"


def test_empty_formats_is_typed_no_supported_video():
    result = classify_metadata("B-MYSMhHXy6", metadata())
    assert result["classification"] == "no_supported_video"
    assert result["audio_source_status"] == "UNKNOWN"


def test_video_only_recovery_retains_media_and_marks_original_audio_unknown(tmp_path):
    code = "B-MYSMhHXy6"
    data = metadata(formats=[fmt(URL_VIDEO, vcodec="avc1", acodec="none")])
    calls = []

    def fake_download(url, target, **kwargs):
        calls.append((url, kwargs))
        target.write_bytes(b"video-only-fixture")
        return {"http_status": 200, "bytes": target.stat().st_size}

    result = recover_video(
        code,
        data,
        tmp_path / "private-recovery",
        max_bytes=1024 * 1024,
        reserve_bytes=0,
        cache_bytes=1024 * 1024,
        download_fn=fake_download,
        probe_fn=lambda path: {"has_audio": False, "duration_ms": 1000},
    )

    assert result["state"] == "OBSERVED"
    assert result["original_audio_status"] == "UNKNOWN"
    assert result["audio_source_status"] == "NOT_ADVERTISED_UNKNOWN"
    assert result["original_audio_unknown"] is True
    assert result["source_completeness_flag"] == "VIDEO_RETAINED_AUDIO_ORIGINAL_UNKNOWN"
    assert result["speech_state"] == "UNKNOWN"
    assert calls[0][0] == URL_VIDEO

    record = json.loads((tmp_path / "private-recovery" / f"{code}.media.json").read_text())
    media = tmp_path / "private-recovery" / f"{code}.mp4"
    evidence = tmp_path / "private-recovery" / f"{code}.metadata.private.json"
    assert media.read_bytes() == b"video-only-fixture"
    assert record["sha256"] == hashlib.sha256(media.read_bytes()).hexdigest()
    assert record["acquisition_provenance"]["metadata_evidence"]["sha256"] == hashlib.sha256(evidence.read_bytes()).hexdigest()
    assert record["source_completeness"]["original_audio"] == "UNKNOWN"
    assert record["source_completeness"]["original_audio_unknown"] is True
    assert record["has_audio"] is None
    assert record["retained_media_has_audio"] is False
    assert record["transcription_eligibility"] == "UNKNOWN_ORIGINAL_AUDIO"
    assert "confirmed_no_speech" not in record


def test_split_streams_fail_closed_without_download(tmp_path):
    data = metadata(
        formats=[
            fmt(URL_VIDEO, vcodec="avc1", acodec="none"),
            fmt(URL_AUDIO, vcodec="none", acodec="aac"),
        ]
    )
    called = []
    with pytest.raises(AcquisitionError, match="MERGE_REQUIRED_UNSUPPORTED"):
        recover_video(
            "B-MYSMhHXy6",
            data,
            tmp_path / "private-recovery",
            download_fn=lambda *args, **kwargs: called.append(args),
        )
    assert called == []
    assert not (tmp_path / "private-recovery").exists()


def test_metadata_hash_mismatch_is_rejected(tmp_path):
    data = metadata(formats=[fmt(URL_VIDEO, vcodec="avc1", acodec="none")])
    with pytest.raises(AcquisitionError, match="METADATA_HASH_MISMATCH"):
        recover_video(
            "B-MYSMhHXy6",
            data,
            tmp_path / "private-recovery",
            expected_metadata_sha256="00" * 32,
        )


def test_metadata_size_cap_is_enforced(tmp_path, monkeypatch):
    path = tmp_path / "metadata.json"
    path.write_bytes(b"{" + b" " * 128 + b"}")
    monkeypatch.setattr("m2_orchestrator.media_recovery.MAX_METADATA_BYTES", 16)
    with pytest.raises(AcquisitionError, match="METADATA_SIZE_LIMIT"):
        recover_video("B-MYSMhHXy6", path, tmp_path / "private-recovery")


def test_existing_output_directory_is_rejected(tmp_path):
    output = tmp_path / "private-recovery"
    output.mkdir()
    data = metadata(formats=[fmt(URL_VIDEO, vcodec="avc1", acodec="none")])
    with pytest.raises(AcquisitionError, match="OUTPUT_ALREADY_EXISTS"):
        recover_video("B-MYSMhHXy6", data, output)


def test_failed_probe_retains_downloaded_media_metadata_and_typed_failure(tmp_path):
    output = tmp_path / "private-recovery"
    data = metadata(formats=[fmt(URL_VIDEO, vcodec="avc1", acodec="none")])

    def fake_download(url, target, **kwargs):
        target.write_bytes(b"retained-after-probe-failure")
        return {"http_status": 200}

    with pytest.raises(AcquisitionError, match="PROBE_FAILED"):
        recover_video(
            "B-MYSMhHXy6",
            data,
            output,
            max_bytes=1024 * 1024,
            reserve_bytes=0,
            cache_bytes=1024 * 1024,
            download_fn=fake_download,
            probe_fn=lambda path: (_ for _ in ()).throw(AcquisitionError("PROBE_FAILED")),
        )
    assert (output / "B-MYSMhHXy6.mp4").read_bytes() == b"retained-after-probe-failure"
    failure = json.loads((output / "B-MYSMhHXy6.failure.json").read_text())
    assert failure["observation_state"] == "PARTIAL"
    assert failure["retained_media"] is True
    assert failure["source_bytes"] == len(b"retained-after-probe-failure")
    assert (output / "B-MYSMhHXy6.metadata.private.json").is_file()


@pytest.mark.parametrize("timeout", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_timeout_is_rejected(tmp_path, timeout):
    data = metadata(formats=[fmt(URL_VIDEO, vcodec="avc1", acodec="none")])
    with pytest.raises(AcquisitionError, match="INVALID_LIMITS"):
        recover_video("B-MYSMhHXy6", data, tmp_path / "private-recovery", timeout=timeout)


def test_dangling_symlink_output_is_rejected(tmp_path):
    output = tmp_path / "private-recovery"
    os.symlink(tmp_path / "missing", output)
    data = metadata(formats=[fmt(URL_VIDEO, vcodec="avc1", acodec="none")])
    with pytest.raises(AcquisitionError, match="OUTPUT_SYMLINK"):
        recover_video("B-MYSMhHXy6", data, output)


def test_partial_source_provenance_is_bound_to_media_and_metadata(tmp_path):
    code = "B-MYSMhHXy6"
    data = metadata(formats=[fmt(URL_VIDEO, vcodec="avc1", acodec="none")])

    def fake_download(url, target, **kwargs):
        target.write_bytes(b"partial-provenance-fixture")
        return {}  # The retained content hash is independent of downloader fields.

    result = recover_video(
        code,
        data,
        tmp_path / "private-recovery",
        max_bytes=1024 * 1024,
        reserve_bytes=0,
        cache_bytes=1024 * 1024,
        download_fn=fake_download,
        probe_fn=lambda path: {"has_audio": False},
    )
    record = json.loads((tmp_path / "private-recovery" / f"{code}.media.json").read_text())
    assert result["source_sha256"] == record["acquisition_provenance"]["source_sha256"]
    assert result["metadata_sha256"] == record["acquisition_provenance"]["metadata_sha256"]
    assert record["acquisition_provenance"]["download"] == {}


def test_probe_cannot_overwrite_recovery_owned_provenance(tmp_path):
    data = metadata(formats=[fmt(URL_VIDEO, vcodec="avc1", acodec="none")])

    def fake_download(url, target, **kwargs):
        target.write_bytes(b"probe-allowlist-fixture")
        return {"bytes": target.stat().st_size}

    output = tmp_path / "private-recovery"
    recover_video(
        "B-MYSMhHXy6",
        data,
        output,
        max_bytes=1024 * 1024,
        reserve_bytes=0,
        cache_bytes=1024 * 1024,
        download_fn=fake_download,
        probe_fn=lambda path: {
            "has_audio": False,
            "duration_ms": 1000,
            "sha256": "injected",
            "source_hash": "injected",
            "source_pointer": "injected",
            "acquisition_provenance": {"source_sha256": "injected"},
        },
    )
    record = json.loads((output / "B-MYSMhHXy6.media.json").read_text())
    media_hash = hashlib.sha256((output / "B-MYSMhHXy6.mp4").read_bytes()).hexdigest()
    assert record["sha256"] == media_hash
    assert record["source_hash"] == media_hash
    assert record["source_pointer"] == "B-MYSMhHXy6.mp4"
    assert record["acquisition_provenance"]["source_sha256"] == media_hash
    assert "acquisition_provenance" not in recovery._PROBE_FIELDS


def test_record_failure_after_promotion_retains_truthful_media_hash(tmp_path, monkeypatch):
    data = metadata(formats=[fmt(URL_VIDEO, vcodec="avc1", acodec="none")])

    def fake_download(url, target, **kwargs):
        target.write_bytes(b"record-failure-fixture")
        return {}

    original_dump = recovery.json.dump
    calls = {"count": 0}

    def fail_record_once(obj, handle, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("RECORD_WRITE_FAILED")
        return original_dump(obj, handle, **kwargs)

    monkeypatch.setattr(recovery.json, "dump", fail_record_once)
    output = tmp_path / "private-recovery"
    with pytest.raises(RuntimeError, match="RECORD_WRITE_FAILED"):
        recover_video(
            "B-MYSMhHXy6",
            data,
            output,
            max_bytes=1024 * 1024,
            reserve_bytes=0,
            cache_bytes=1024 * 1024,
            download_fn=fake_download,
            probe_fn=lambda path: {"has_audio": False},
        )
    media = output / "B-MYSMhHXy6.mp4"
    failure = json.loads((output / "B-MYSMhHXy6.failure.json").read_text())
    expected = hashlib.sha256(media.read_bytes()).hexdigest()
    assert media.is_file()
    assert failure["retained_media"] is True
    assert failure["source_sha256"] == expected
    assert failure["source_hash"] == expected
    assert failure["source_bytes"] == media.stat().st_size


def test_approved_rights_require_explicit_source_kind_and_are_hash_bound(tmp_path):
    data = metadata(formats=[fmt(URL_VIDEO, vcodec="avc1", acodec="none")])
    with pytest.raises(AcquisitionError, match="RIGHTS_BLOCKED"):
        recover_video(
            "B-MYSMhHXy6",
            data,
            tmp_path / "missing-source-kind",
            rights={"analysis_allowed": True, "receipt_id": "rights-r2"},
        )

    rights = {
        "analysis_allowed": True,
        "receipt_id": "rights-r2",
        "source_kind": "approved_research_copy",
        "public_display_allowed": False,
    }

    def fake_download(url, target, **kwargs):
        target.write_bytes(b"rights-fixture")
        return {}

    output = tmp_path / "approved-rights"
    recover_video(
        "B-MYSMhHXy6",
        data,
        output,
        rights=rights,
        max_bytes=1024 * 1024,
        reserve_bytes=0,
        cache_bytes=1024 * 1024,
        download_fn=fake_download,
        probe_fn=lambda path: {"has_audio": False},
    )
    record = json.loads((output / "B-MYSMhHXy6.media.json").read_text())
    assert record["rights_state"] == "APPROVED"
    assert record["analysis_ready"] is True
    assert record["source_kind"] == "approved_research_copy"
    assert record["rights_receipt"] == rights
    assert record["rights_receipt_sha256"] == stable_hash(rights)
