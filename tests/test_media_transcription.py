from __future__ import annotations

import hashlib
import json
import sys
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest

from m2_orchestrator import media_transcription as m


def _model(tmp_path: Path) -> Path:
    root = tmp_path / "model"
    root.mkdir()
    weights = root / "weights.bin"
    weights.write_bytes(b"local model fixture")
    checksum = hashlib.sha256(weights.read_bytes()).hexdigest()
    (root / "model-hash-manifest.json").write_text(json.dumps({"files": [{"path": "weights.bin", "sha256": checksum}]}))
    return root


def _record(root: Path, *, audio: bool = True) -> dict:
    media = root / "media.mp4"
    media.write_bytes(b"observed fixture media")
    return {
        "schema": "m2.acquired-media.v1",
        "media_id": "ABCde1",
        "reel_id": "instagram:ABCde1",
        "observation_state": "OBSERVED",
        "source_pointer": "media.mp4",
        "sha256": hashlib.sha256(media.read_bytes()).hexdigest(),
        "has_audio": audio,
        "duration_ms": 2000,
        "timebase_provenance": {"audio_offset_ms": 0},
        "source_kind": "approved_research_copy",
        "rights": {"analysis_allowed": True, "receipt_id": "research-copy-r1"},
    }


def _wav(path: Path, *, silence: bool) -> None:
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(16000)
        stream.writeframes((b"\0\0" if silence else b"\x01\0") * 16000)


def test_model_bundle_requires_complete_hash_manifest(tmp_path: Path) -> None:
    model_dir = _model(tmp_path)
    receipt = m.validate_model_bundle(model_dir)
    assert len(receipt["manifest_sha256"]) == 64
    assert receipt["files"] == [{"path": "weights.bin", "sha256": hashlib.sha256(b"local model fixture").hexdigest()}]
    (model_dir / "weights.bin").write_bytes(b"tampered")
    with pytest.raises(m.TranscriptionError, match="MODEL_FILE_HASH_MISMATCH"):
        m.validate_model_bundle(model_dir)


def test_transcribe_requires_approved_research_copy_before_child(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    record = _record(root)
    record["source_kind"] = "synthetic_fixture"
    called = False

    def fail_process(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("child must not start")

    monkeypatch.setattr(m, "bounded_process", fail_process)
    result = m.transcribe(record, root, tmp_path / "output", sys.executable, _model(tmp_path))
    assert result["observation_state"] == "ASR_FAILED"
    assert result["failure_code"] == "APPROVED_RESEARCH_COPY_REQUIRED"
    assert not called


def test_worker_exact_pcm_silence_is_unverified_without_asr(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    record = _record(root)
    model_dir = _model(tmp_path)
    output = tmp_path / "output"
    request = output / "request.json"
    config = m._config(m.validate_model_bundle(model_dir), record["sha256"], record["duration_ms"])
    request.parent.mkdir()
    request.write_text(json.dumps({"root": str(root), "output": str(output), "record": record,
                                   "model_dir": str(model_dir), "config_sha256": m.object_hash(config)}))
    loaded = []

    def fake_process(args, **kwargs):
        assert args[0] == "ffmpeg"
        assert "-threads" in args and args[args.index("-threads") + 1] == "2"
        assert "-f" in args and args[args.index("-f") + 1] == "wav"
        assert "-fs" in args and args[args.index("-fs") + 1] == str(m.MAX_AUDIO_BYTES)
        assert "-t" in args and args[args.index("-t") + 1] == "2.000"
        assert kwargs["rss_limit_bytes"] == m.FFMPEG_RSS_WATCHDOG_BYTES
        _wav(Path(args[-1]), silence=True)
        return {"returncode": 0, "stdout": b"", "stderr": b""}

    class NeverLoad:
        def __init__(self, *args, **kwargs):
            loaded.append(True)

    monkeypatch.setattr(m, "bounded_process", fake_process)
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=NeverLoad))
    result = m._worker(request)
    assert result["observation_state"] == "EMPTY_OUTPUT_UNVERIFIED"
    assert result["failure_code"] == "DIGITAL_SILENCE_REVIEW_REQUIRED"
    assert result["asr_execution"] is False
    assert loaded == []
    assert len(result["source_audio_sha256"]) == 64
    assert (output / "normalized-audio.wav").is_file()


def test_worker_normalizes_word_timings_and_persists_hashes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    record = _record(root)
    model_dir = _model(tmp_path)
    output = tmp_path / "output"
    request = output / "request.json"
    config = m._config(m.validate_model_bundle(model_dir), record["sha256"], record["duration_ms"])
    request.parent.mkdir()
    request.write_text(json.dumps({"root": str(root), "output": str(output), "record": record,
                                   "model_dir": str(model_dir), "config_sha256": m.object_hash(config)}))

    def fake_process(args, **kwargs):
        _wav(Path(args[-1]), silence=False)
        return {"returncode": 0, "stdout": b"", "stderr": b""}

    class FakeModel:
        def __init__(self, *args, **kwargs):
            assert kwargs["device"] == "cpu"
            assert kwargs["compute_type"] == "int8"
            assert kwargs["cpu_threads"] == 2
            assert kwargs["num_workers"] == 1

        def transcribe(self, audio, **kwargs):
            assert kwargs == {"language": None, "word_timestamps": True, "beam_size": 5}
            word = SimpleNamespace(start=0.1, end=0.4, word=" hello", probability=0.91)
            segment = SimpleNamespace(start=0.0, end=0.8, text=" hello", words=[word])
            return iter([segment]), SimpleNamespace(language="en", language_probability=0.99)

    monkeypatch.setattr(m, "bounded_process", fake_process)
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=FakeModel))
    result = m._worker(request)
    assert result["observation_state"] == "OBSERVED"
    assert result["segments"][0]["start_ms"] == 0
    assert result["segments"][0]["words"][0]["end_ms"] == 400
    for key in ("source_media_hash", "source_audio_sha256", "model_sha256", "model_hash_manifest_sha256", "raw_transcript_sha256", "config_sha256"):
        assert len(result[key]) == 64
    assert (output / "raw-transcript.json").is_file()


def test_normalization_marks_overlap_suspicious_and_rejects_bad_timing(tmp_path: Path) -> None:
    record = _record(tmp_path)
    raw = {"language": "en", "segments": [{"start": 0.0, "end": 1.0, "text": "one", "words": []}, {"start": 0.5, "end": 1.5, "text": "two", "words": []}]}
    result = m._normalize_raw(raw, record)
    assert result["observation_state"] == "SUSPICIOUS_TIMINGS"
    assert result["failure_code"] == "TIMING_REVIEW_REQUIRED"
    assert "OVERLAPPING_SEGMENTS_REVIEW_REQUIRED" in result["timing_issues"]
    with pytest.raises(m.TranscriptionError, match="ASR_TIMINGS_INVALID"):
        m._normalize_raw({"segments": [{"start": 1.0, "end": 0.0, "text": "bad"}]}, record)


def test_real_shape_zero_duration_word_is_preserved_as_partial_alignment(tmp_path: Path) -> None:
    record = _record(tmp_path)
    raw_words = [{"start": 0.05 * i, "end": 0.05 * (i + 1), "word": f" w{i}", "probability": 0.9} for i in range(9)]
    raw_words[7]["end"] = raw_words[7]["start"]
    result = m._normalize_raw({"language": "en", "segments": [{"start": 0.0, "end": 1.0, "text": "nine words", "words": raw_words}]}, record)
    segment = result["segments"][0]
    assert result["observation_state"] == "OBSERVED"
    assert result["word_timing"] == "PARTIAL"
    assert result["lexical_word_count"] == 9
    assert result["aligned_word_count"] == 8
    assert result["unaligned_word_count"] == 1
    assert len(segment["words"]) == 8
    assert segment["unaligned_words"][0]["reason"] == "ZERO_DURATION_WORD"
    assert segment["unaligned_words"][0]["raw"]["word"] == " w7"


def test_out_of_bounds_word_is_retained_as_suspicious_unaligned_evidence(tmp_path: Path) -> None:
    record = _record(tmp_path)
    raw = {"language": "en", "segments": [{"start": 0.0, "end": 1.0, "text": "word", "words": [{"start": -0.2, "end": 0.3, "word": " word"}]}]}
    result = m._normalize_raw(raw, record)
    assert result["observation_state"] == "SUSPICIOUS_TIMINGS"
    assert result["word_timing"] == "UNAVAILABLE"
    assert "UNALIGNED_WORD_OUT_OF_BOUNDS" in result["timing_issues"]
    assert result["segments"][0]["unaligned_words"][0]["reason"] == "UNALIGNED_WORD_OUT_OF_BOUNDS"


def test_public_callable_records_sampled_resource_receipt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    record = _record(root)
    model_dir = _model(tmp_path)
    output = tmp_path / "output"

    def fake_process(args, **kwargs):
        request = json.loads(Path(args[-1]).read_text())
        Path(request["output"]).mkdir(exist_ok=True)
        (Path(request["output"]) / "transcription.json").write_text(json.dumps({"schema": m.SCHEMA, "observation_state": "EMPTY_OUTPUT_UNVERIFIED", "failure_code": "DIGITAL_SILENCE_REVIEW_REQUIRED"}))
        assert kwargs["rss_limit_bytes"] == m.RSS_WATCHDOG_BYTES
        assert kwargs["env"]["HF_HUB_OFFLINE"] == "1"
        return {"returncode": 0, "stdout": b"ok", "stderr": b"", "elapsed_seconds": 0.2, "sampled_peak_rss_bytes": 1234}

    monkeypatch.setattr(m, "bounded_process", fake_process)
    result = m.transcribe(record, root, output, sys.executable, model_dir)
    assert result["observation_state"] == "EMPTY_OUTPUT_UNVERIFIED"
    assert result["resource_receipt"]["sampled_peak_rss_bytes"] == 1234
    assert result["resource_receipt"]["rss_claim"] == "sampled_watchdog_only"
    assert (output / "resource-receipt.json").is_file()
