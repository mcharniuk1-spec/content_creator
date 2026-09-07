from __future__ import annotations

import hashlib
import json
import sys
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest

from m2_orchestrator.process_budget import ProcessBudgetError
from m2_orchestrator.transcription_chunk_worker import worker
from m2_orchestrator.transcription_recovery import (
    TranscriptionRecoveryError,
    build_chunk_request,
    build_recovery_config,
    completed_chunk_ids,
    object_hash,
    plan_windows,
    recover_chunks,
)
from m2_orchestrator import transcription_chunk_worker as worker_module
from scripts import run_m2_transcription_recovery as cli


SOURCE = "a" * 64
MODEL = "b" * 64


def _model_fixture(root: Path) -> tuple[Path, str]:
    model = root / "model"
    model.mkdir()
    weights = model / "weights.bin"
    weights.write_bytes(b"fixture model")
    checksum = hashlib.sha256(weights.read_bytes()).hexdigest()
    (model / "model-hash-manifest.json").write_text(
        json.dumps({"files": [{"path": weights.name, "sha256": checksum}]}),
        encoding="utf-8",
    )
    from m2_orchestrator.media_transcription import validate_model_bundle

    return model, validate_model_bundle(model)["bundle_sha256"]


def _request_fixture(root: Path, *, beam_size: int = 1) -> tuple[dict, Path, Path]:
    source_root = root / "source"
    source_root.mkdir()
    source = source_root / "media.mp4"
    source.write_bytes(b"fixture source")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    model_dir, model_hash = _model_fixture(root)
    config = build_recovery_config(
        source_media_hash=source_hash,
        duration_ms=2_000,
        model_bundle_sha256=model_hash,
        beam_size=beam_size,
    )
    request = build_chunk_request(
        plan_windows(2_000)[0],
        source_media_hash=source_hash,
        model_bundle_sha256=model_hash,
        config_sha256=object_hash(config),
        source_pointer=source.name,
        config=config,
    )
    output = root / "chunk"
    request.update({
        "source_root": str(source_root),
        "model_dir": str(model_dir),
        "output": str(output),
    })
    request["request_sha256"] = object_hash({k: v for k, v in request.items() if k != "request_sha256"})
    path = root / "chunk-request.json"
    path.write_text(json.dumps(request), encoding="utf-8")
    return request, path, output


def _write_audio(path: Path) -> None:
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(16_000)
        stream.writeframes(b"\x01\x00" * 16_000)


def test_beam_one_is_hash_bound_and_invalid_values_are_rejected():
    config5 = build_recovery_config(source_media_hash=SOURCE, duration_ms=2_000, model_bundle_sha256=MODEL)
    config1 = build_recovery_config(source_media_hash=SOURCE, duration_ms=2_000, model_bundle_sha256=MODEL, beam_size=1)
    assert config5["beam_size"] == 5
    assert config1["beam_size"] == 1
    assert object_hash(config1) != object_hash(config5)
    for value in (0, -1, 6, 1.0, True, False, None):
        with pytest.raises(TranscriptionRecoveryError):
            build_recovery_config(source_media_hash=SOURCE, duration_ms=2_000, model_bundle_sha256=MODEL, beam_size=value)


def test_request_requires_config_beam_agreement_before_child_work():
    config = build_recovery_config(source_media_hash=SOURCE, duration_ms=2_000, model_bundle_sha256=MODEL, beam_size=1)
    with pytest.raises(TranscriptionRecoveryError, match="BEAM_SIZE_MISMATCH"):
        build_chunk_request(
            plan_windows(2_000)[0],
            source_media_hash=SOURCE,
            model_bundle_sha256=MODEL,
            config_sha256=object_hash(config),
            config=config,
            beam_size=5,
        )


def test_fake_whisper_receives_beam_one_and_raw_receipt_preserves_it(monkeypatch, tmp_path):
    request, request_path, _ = _request_fixture(tmp_path, beam_size=1)
    seen: dict = {}

    def fake_process(args, **kwargs):
        seen["process"] = kwargs
        _write_audio(Path(args[-1]))
        return {"returncode": 0, "stdout": b"", "stderr": b"", "elapsed_seconds": 0.25, "sampled_peak_rss_bytes": 123}

    class FakeModel:
        def __init__(self, *args, **kwargs):
            seen["model"] = kwargs

        def transcribe(self, audio, **kwargs):
            seen["transcribe"] = kwargs
            word = SimpleNamespace(start=0.1, end=0.4, word=" hello", probability=0.9)
            segment = SimpleNamespace(start=0.0, end=0.8, text=" hello", words=[word])
            return iter([segment]), SimpleNamespace(language="en", language_probability=0.9)

    monkeypatch.setattr(worker_module, "bounded_process", fake_process)
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=FakeModel))
    result = worker(request_path)
    assert result["observation_state"] == "OBSERVED"
    assert result["beam_size"] == 1
    assert result["raw"]["parameters"]["beam_size"] == 1
    assert seen["transcribe"]["beam_size"] == 1


def test_worker_rejects_beam_mismatch_before_decode(monkeypatch, tmp_path):
    request, request_path, _ = _request_fixture(tmp_path, beam_size=1)
    request["beam_size"] = 5
    request["request_sha256"] = object_hash({k: v for k, v in request.items() if k != "request_sha256"})
    request_path.write_text(json.dumps(request), encoding="utf-8")
    monkeypatch.setattr(worker_module, "bounded_process", lambda *a, **k: pytest.fail("beam mismatch must stop before decode"))
    result = worker(request_path)
    assert result["observation_state"] == "PARTIAL"
    assert result["failure_code"] == "BEAM_SIZE_MISMATCH"


def test_beam_five_or_old_config_cache_cannot_resume_as_beam_one():
    plans = plan_windows(2_000)
    result = {
        "chunk_id": "C0001",
        "source_media_hash": SOURCE,
        "model_bundle_sha256": MODEL,
        "config_sha256": "c" * 64,
        "beam_size": 5,
        "global_offset_ms": plans[0]["global_offset_ms"],
        "core_interval_ms": plans[0]["core_interval_ms"],
        "window_interval_ms": plans[0]["window_interval_ms"],
        "observation_state": "OBSERVED",
        "source_audio_sha256": "d" * 64,
    }
    with pytest.raises(TranscriptionRecoveryError, match="BEAM_SIZE_MISMATCH"):
        completed_chunk_ids(plans, [result], source_media_hash=SOURCE, model_bundle_sha256=MODEL, config_sha256="c" * 64, beam_size=1)
    config5 = build_recovery_config(source_media_hash=SOURCE, duration_ms=2_000, model_bundle_sha256=MODEL, beam_size=5)
    config1 = build_recovery_config(source_media_hash=SOURCE, duration_ms=2_000, model_bundle_sha256=MODEL, beam_size=1)
    assert object_hash(config5) != object_hash(config1)


def test_run_manifest_and_aggregate_bind_beam_one():
    config = build_recovery_config(source_media_hash=SOURCE, duration_ms=2_000, model_bundle_sha256=MODEL, beam_size=1)
    prepared = {
        "record": {"sha256": SOURCE, "source_pointer": "media.mp4", "source_kind": "approved_research_copy", "rights": {"analysis_allowed": True, "receipt_id": "fixture"}},
        "model": {"bundle_sha256": MODEL},
        "config": config,
        "config_hash": object_hash(config),
        "plans": plan_windows(2_000),
        "input_paths": {},
        "runtime": {},
    }
    manifest = cli._run_manifest(prepared)
    assert manifest["beam_size"] == 1
    assert manifest["config"]["beam_size"] == 1
    result = recover_chunks(
        prepared["plans"],
        source_media_hash=SOURCE,
        model_bundle_sha256=MODEL,
        config_sha256=prepared["config_hash"],
        config=config,
        beam_size=1,
        chunk_runner=lambda request: {
            "chunk_id": request["chunk_id"],
            "source_media_hash": SOURCE,
            "model_bundle_sha256": MODEL,
            "config_sha256": prepared["config_hash"],
            "beam_size": 1,
            "observation_state": "PARTIAL",
            "failure_code": "FIXTURE_ONLY",
        },
    )
    assert result["beam_size"] == 1
    assert result["aggregate_metrics"]["beam_size"] == 1


def test_rss_limit_remains_typed_partial_under_beam_one():
    config = build_recovery_config(source_media_hash=SOURCE, duration_ms=2_000, model_bundle_sha256=MODEL, beam_size=1)
    result = recover_chunks(
        plan_windows(2_000),
        source_media_hash=SOURCE,
        model_bundle_sha256=MODEL,
        config_sha256=object_hash(config),
        config=config,
        beam_size=1,
        chunk_runner=lambda request: (_ for _ in ()).throw(ProcessBudgetError("PROCESS_RSS_LIMIT")),
    )
    assert result["observation_state"] == "PARTIAL"
    assert result["incomplete_chunks"] == ["C0001"]
    assert result["chunks"][0]["failure_code"] == "PROCESS_RSS_LIMIT"
    assert result["beam_size"] == 1


