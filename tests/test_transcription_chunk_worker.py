from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest

from m2_orchestrator.process_budget import ProcessBudgetError
from m2_orchestrator.transcription_chunk_worker import production_chunk_runner, worker
from m2_orchestrator.transcription_recovery import build_chunk_request, build_recovery_config, object_hash, plan_windows
from m2_orchestrator import transcription_chunk_worker as w
from scripts import run_m2_transcription_recovery as cli


SOURCE_HASH = "a" * 64
MODEL_HASH = "b" * 64


def model_fixture(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "model"
    root.mkdir()
    weights = root / "weights.bin"
    weights.write_bytes(b"chunk worker model")
    checksum = hashlib.sha256(weights.read_bytes()).hexdigest()
    manifest = root / "model-hash-manifest.json"
    manifest.write_text(json.dumps({"files": [{"path": weights.name, "sha256": checksum}]}))
    from m2_orchestrator.media_transcription import validate_model_bundle

    receipt = validate_model_bundle(root)
    return root, receipt["bundle_sha256"]


def request_fixture(tmp_path: Path) -> tuple[dict, Path, Path]:
    source_root = tmp_path / "source"
    source_root.mkdir()
    source = source_root / "media.mp4"
    source.write_bytes(b"retained source")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    model_dir, model_hash = model_fixture(tmp_path)
    plan = plan_windows(2_000)[0]
    config = build_recovery_config(source_media_hash=source_hash, duration_ms=2_000, model_bundle_sha256=model_hash)
    request = build_chunk_request(plan, source_media_hash=source_hash, model_bundle_sha256=model_hash, config_sha256=object_hash(config), source_pointer=source.name, config=config)
    output = tmp_path / "chunk"
    full = {**request, "source_root": str(source_root), "source_pointer": source.name, "model_dir": str(model_dir), "output": str(output)}
    full["request_sha256"] = object_hash({key: value for key, value in full.items() if key != "request_sha256"})
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(full))
    return full, request_path, output


def write_audio(path: Path) -> None:
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(16_000)
        stream.writeframes(b"\x01\x00" * 16_000)


def test_worker_extracts_bounded_window_and_runs_offline_model(monkeypatch, tmp_path):
    request, request_path, output = request_fixture(tmp_path)
    seen = {}

    def fake_process(args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        write_audio(Path(args[-1]))
        return {"returncode": 0, "stdout": b"", "stderr": b""}

    class FakeModel:
        def __init__(self, *args, **kwargs):
            seen["model"] = kwargs

        def transcribe(self, audio, **kwargs):
            word = SimpleNamespace(start=0.1, end=0.4, word=" hello", probability=0.9)
            segment = SimpleNamespace(start=0.0, end=0.8, text=" hello", words=[word])
            return iter([segment]), SimpleNamespace(language="en", language_probability=0.9)

    monkeypatch.setattr(w, "bounded_process", fake_process)
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=FakeModel))
    result = worker(request_path)
    assert result["observation_state"] == "OBSERVED"
    assert result["source_audio_sha256"]
    assert seen["args"][seen["args"].index("-ss") + 1] == "0.000"
    assert seen["args"][seen["args"].index("-t") + 1] == "2.000"
    assert seen["args"][seen["args"].index("-threads") + 1] == "2"
    assert seen["kwargs"]["rss_limit_bytes"] == 512 * 1024 * 1024
    assert seen["model"]["local_files_only"] is True
    assert (output / "chunk-audio.wav").is_file()
    assert (output / "chunk-raw.json").is_file()
    assert (output / "chunk-result.json").is_file()


def test_worker_hash_mismatch_writes_typed_partial_without_decode(monkeypatch, tmp_path):
    request, request_path, output = request_fixture(tmp_path)
    request["source_media_hash"] = "c" * 64
    request_path.write_text(json.dumps(request))
    monkeypatch.setattr(w, "bounded_process", lambda *args, **kwargs: pytest.fail("decode must not start"))
    result = worker(request_path)
    assert result["observation_state"] == "PARTIAL"
    assert result["failure_code"] == "CHUNK_REQUEST_HASH_MISMATCH"
    assert (output / "chunk-result.json").is_file()


def test_worker_rss_failure_is_explicit_partial(monkeypatch, tmp_path):
    request, request_path, _ = request_fixture(tmp_path)
    monkeypatch.setattr(w, "bounded_process", lambda *args, **kwargs: (_ for _ in ()).throw(ProcessBudgetError("PROCESS_RSS_LIMIT")))
    result = worker(request_path)
    assert result["observation_state"] == "PARTIAL"
    assert result["failure_code"] == "PROCESS_RSS_LIMIT"
    assert result["asr_execution"] is False


def test_worker_preserves_unknown_original_audio_without_claiming_no_speech(tmp_path):
    request, request_path, output = request_fixture(tmp_path)
    request["original_audio_unknown"] = True
    request["request_sha256"] = object_hash({key: value for key, value in request.items() if key != "request_sha256"})
    request_path.write_text(json.dumps(request))
    result = worker(request_path)
    assert result["observation_state"] == "PARTIAL"
    assert result["failure_code"] == "ORIGINAL_AUDIO_UNKNOWN_REQUIRES_AUDIO_SOURCE_PROOF"
    assert result["original_audio_unknown"] is True
    assert result["speech_state"] == "UNKNOWN"
    assert result["no_speech_confirmed"] is False
    assert (output / "chunk-result.json").is_file()


def test_production_runner_uses_real_worker_command_and_offline_environment(monkeypatch, tmp_path):
    request, _, _ = request_fixture(tmp_path)
    seen = {}

    def fake_process(args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return {"returncode": 1, "stdout": b"", "stderr": b"", "elapsed_seconds": 0.125, "sampled_peak_rss_bytes": 123456, "rss_watchdog_limit_bytes": kwargs["rss_limit_bytes"], "rss_poll_seconds": 0.2}

    monkeypatch.setattr(w, "bounded_process", fake_process)
    result = production_chunk_runner(request, output_root=tmp_path / "recovery", source_root=request["source_root"], model_dir=request["model_dir"], python_executable="python3")
    assert result["observation_state"] == "PARTIAL"
    assert "m2_orchestrator.transcription_chunk_worker" in seen["args"]
    assert seen["kwargs"]["env"]["HF_HUB_OFFLINE"] == "1"
    assert seen["kwargs"]["rss_limit_bytes"] == int(1.5 * 1024 * 1024 * 1024)
    assert result["parent_resource_receipt"]["elapsed_seconds"] == 0.125
    assert result["parent_resource_receipt"]["sampled_peak_rss_bytes"] == 123456
    assert (tmp_path / "recovery" / "C0001" / "parent-resource-receipt.json").is_file()


def test_production_runner_rejects_unbound_child_result(monkeypatch, tmp_path):
    request, _, _ = request_fixture(tmp_path)

    def fake_process(args, **kwargs):
        child_request = json.loads(Path(args[-1]).read_text())
        output = Path(child_request["output"])
        (output / "chunk-result.json").write_text(json.dumps({"schema": "wrong", "chunk_id": child_request["chunk_id"], "observation_state": "OBSERVED"}))
        return {"returncode": 0, "stdout": b"", "stderr": b""}

    monkeypatch.setattr(w, "bounded_process", fake_process)
    result = production_chunk_runner(request, output_root=tmp_path / "recovery", source_root=request["source_root"], model_dir=request["model_dir"], python_executable="python3")
    assert result["observation_state"] == "PARTIAL"
    assert result["failure_code"] == "CHUNK_RESULT_SCHEMA_INVALID"


def test_production_runner_persists_resource_receipt_on_timeout_failure(monkeypatch, tmp_path):
    request, _, _ = request_fixture(tmp_path)

    def timeout_process(*args, **kwargs):
        raise ProcessBudgetError("PROCESS_TIMEOUT")

    monkeypatch.setattr(w, "bounded_process", timeout_process)
    result = production_chunk_runner(request, output_root=tmp_path / "recovery", source_root=request["source_root"], model_dir=request["model_dir"], python_executable="python3")
    receipt = result["parent_resource_receipt"]
    assert result["failure_code"] == "PROCESS_TIMEOUT"
    assert receipt["measurement_state"] == "UNAVAILABLE_ON_EXCEPTION"
    assert receipt["elapsed_seconds"] >= 0
    assert receipt["sampled_peak_rss_bytes"] is None
    assert (tmp_path / "recovery" / "C0001" / "parent-resource-receipt.json").is_file()


def test_production_runner_resumes_only_when_all_cached_artifacts_bind(monkeypatch, tmp_path):
    request, _, _ = request_fixture(tmp_path)
    launches = []

    def fake_process(args, **kwargs):
        if args[0] == "ffmpeg":
            write_audio(Path(args[-1]))
            return {"returncode": 0, "stdout": b"", "stderr": b"", "elapsed_seconds": 0.01, "sampled_peak_rss_bytes": 1000, "rss_watchdog_limit_bytes": kwargs["rss_limit_bytes"], "rss_poll_seconds": 0.2}
        launches.append(args)
        original = w.bounded_process
        w.bounded_process = fake_process
        try:
            worker(Path(args[-1]))
        finally:
            w.bounded_process = original
        return {"returncode": 0, "stdout": b"", "stderr": b"", "elapsed_seconds": 0.25, "sampled_peak_rss_bytes": 456789, "rss_watchdog_limit_bytes": kwargs["rss_limit_bytes"], "rss_poll_seconds": 0.2}

    class FakeModel:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, audio, **kwargs):
            word = SimpleNamespace(start=0.1, end=0.4, word=" hello", probability=0.9)
            segment = SimpleNamespace(start=0.0, end=0.8, text=" hello", words=[word])
            return iter([segment]), SimpleNamespace(language="en", language_probability=0.9)

    monkeypatch.setattr(w, "bounded_process", fake_process)
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=FakeModel))
    root = tmp_path / "recovery"
    first = production_chunk_runner(request, output_root=root, source_root=request["source_root"], model_dir=request["model_dir"], python_executable="python3")
    assert first["observation_state"] == "OBSERVED"
    assert first["parent_resource_receipt"]["elapsed_seconds"] == 0.25
    assert first["parent_resource_receipt"]["sampled_peak_rss_bytes"] == 456789
    assert (root / "C0001" / "parent-resource-receipt.json").is_file()
    result_digest = hashlib.sha256((root / "C0001" / "chunk-result.json").read_bytes()).hexdigest()
    assert len(launches) == 1
    second = production_chunk_runner(request, output_root=root, source_root=request["source_root"], model_dir=request["model_dir"], python_executable="python3")
    assert second["observation_state"] == "OBSERVED"
    assert second["parent_resource_receipt"]["sampled_peak_rss_bytes"] == 456789
    assert hashlib.sha256((root / "C0001" / "chunk-result.json").read_bytes()).hexdigest() == result_digest
    assert len(launches) == 1
    raw_path = root / "C0001" / "chunk-raw.json"
    raw_path.write_text(raw_path.read_text() + " ")
    third = production_chunk_runner(request, output_root=root, source_root=request["source_root"], model_dir=request["model_dir"], python_executable="python3")
    assert third["observation_state"] == "OBSERVED"
    assert len(launches) == 2
    assert (root / "C0001" / "attempt-0002" / "chunk-result.json").is_file()


def test_production_runner_rejects_traversal_and_symlinked_output_ancestry(tmp_path):
    request, _, _ = request_fixture(tmp_path)
    request["chunk_id"] = "../escape"
    with pytest.raises(w.TranscriptionError, match="CHUNK_ID_INVALID"):
        production_chunk_runner(request, output_root=tmp_path / "recovery", source_root=request["source_root"], model_dir=request["model_dir"])
    link = tmp_path / "linked"
    link.symlink_to(tmp_path / "real", target_is_directory=True)
    other = tmp_path / "other"
    other.mkdir()
    other_request = request_fixture(other)[0]
    with pytest.raises(w.TranscriptionError, match="OUTPUT_SYMLINK_ANCESTOR"):
        production_chunk_runner(other_request, output_root=link / "recovery", source_root=other_request["source_root"], model_dir=other_request["model_dir"])


def test_worker_rejects_lexical_source_model_and_pointer_symlinks_before_resolve(tmp_path):
    request, request_path, output = request_fixture(tmp_path)
    linked_source = tmp_path / "linked-source"
    linked_source.symlink_to(request["source_root"], target_is_directory=True)
    request["source_root"] = str(linked_source)
    request["request_sha256"] = object_hash({key: value for key, value in request.items() if key != "request_sha256"})
    request_path.write_text(json.dumps(request))
    source_result = worker(request_path)
    assert source_result["failure_code"] == "OUTPUT_SYMLINK_ANCESTOR"
    assert not (output / "chunk-audio.wav").exists()

    model_case = tmp_path / "model-case"
    model_case.mkdir()
    request, request_path, output = request_fixture(model_case)
    linked_model = tmp_path / "model-case-linked"
    linked_model.symlink_to(request["model_dir"], target_is_directory=True)
    request["model_dir"] = str(linked_model)
    request["request_sha256"] = object_hash({key: value for key, value in request.items() if key != "request_sha256"})
    request_path.write_text(json.dumps(request))
    model_result = worker(request_path)
    assert model_result["failure_code"] == "OUTPUT_SYMLINK_ANCESTOR"

    pointer_case = tmp_path / "pointer-case"
    pointer_case.mkdir()
    request, request_path, output = request_fixture(pointer_case)
    source = Path(request["source_root"]) / request["source_pointer"]
    pointer = Path(request["source_root"]) / "pointer.mp4"
    pointer.symlink_to(source)
    request["source_pointer"] = pointer.name
    request["request_sha256"] = object_hash({key: value for key, value in request.items() if key != "request_sha256"})
    request_path.write_text(json.dumps(request))
    pointer_result = worker(request_path)
    assert pointer_result["failure_code"] == "OUTPUT_SYMLINK_ANCESTOR"


def test_standalone_cli_bootstraps_repository_import():
    completed = subprocess.run([sys.executable, "scripts/run_m2_transcription_recovery.py", "--help"], cwd=Path(__file__).parents[1], capture_output=True, text=True, check=False)
    assert completed.returncode == 0
    assert "--record-json" in completed.stdout


def test_cli_run_manifest_is_resumable_but_binding_mismatch_blocks(tmp_path):
    config = build_recovery_config(source_media_hash=SOURCE_HASH, duration_ms=2_000, model_bundle_sha256=MODEL_HASH)
    prepared = {
        "record": {"sha256": SOURCE_HASH, "source_pointer": "media.mp4"},
        "model": {"bundle_sha256": MODEL_HASH},
        "config": config,
        "config_hash": object_hash(config),
        "plans": plan_windows(2_000),
        "input_paths": {"source_root_lexical": str(tmp_path), "source_root_resolved": str(tmp_path.resolve())},
        "runtime": {"schema": "m2.transcription-recovery-runtime-receipt.v1", "executable_lexical": "python3", "executable_resolved": "python3", "executable_sha256": "e" * 64, "python_version": "3.12", "implementation": "cpython", "packages": {}, "module_hashes": {}},
    }
    output = tmp_path / "run"
    first = cli._open_or_create_run(output, prepared)
    second = cli._open_or_create_run(output, prepared)
    assert first == second
    prepared["config"] = build_recovery_config(source_media_hash=SOURCE_HASH, duration_ms=2_000, model_bundle_sha256=MODEL_HASH, beam_size=1)
    prepared["config_hash"] = object_hash(prepared["config"])
    with pytest.raises(ValueError, match="RUN_MANIFEST_BINDING_MISMATCH"):
        cli._open_or_create_run(output, prepared)
    prepared["config"] = config
    prepared["config_hash"] = object_hash(config)
    prepared["runtime"]["executable_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="RUN_MANIFEST_BINDING_MISMATCH"):
        cli._open_or_create_run(output, prepared)


def test_cli_dry_preflight_validates_rights_source_and_model_without_running(monkeypatch, tmp_path, capsys):
    request, _, _ = request_fixture(tmp_path)
    source = Path(request["source_root"]) / request["source_pointer"]
    record = {
        "observation_state": "OBSERVED",
        "source_kind": "approved_research_copy",
        "rights": {"analysis_allowed": True, "receipt_id": "fixture"},
        "source_pointer": request["source_pointer"],
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "duration_ms": 2_000,
        "has_audio": True,
    }
    record_path = tmp_path / "record.json"
    record_path.write_text(json.dumps(record))
    monkeypatch.setattr(w, "bounded_process", lambda *args, **kwargs: pytest.fail("dry preflight must not launch a child"))
    model_dir = request["model_dir"]
    code = cli.main(["--record-json", str(record_path), "--source-root", request["source_root"], "--model-dir", model_dir, "--output-dir", str(tmp_path / "recovery")])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["state"] == "PREFLIGHT_ONLY"
    assert payload["chunk_count"] == 1

@pytest.mark.parametrize('target', ['source_root', 'record', 'model_dir', 'source_pointer'])
def test_cli_rejects_lexical_input_symlinks_before_resolution(tmp_path, monkeypatch, target):
    request, _, _ = request_fixture(tmp_path)
    source_root = Path(request['source_root'])
    record = {'source_pointer': request['source_pointer']}
    record_path = tmp_path / 'record.json'
    if target == 'source_pointer':
        (source_root / 'alias.mp4').symlink_to(source_root / request['source_pointer'])
        record['source_pointer'] = 'alias.mp4'
    record_path.write_text(json.dumps(record))
    args = SimpleNamespace(record_json=str(record_path), source_root=str(source_root), model_dir=request['model_dir'])
    if target != 'source_pointer':
        attr = {'source_root': 'source_root', 'record': 'record_json', 'model_dir': 'model_dir'}[target]
        alias = tmp_path / 'alias'
        alias.symlink_to(getattr(args, attr), target_is_directory=target != 'record')
        setattr(args, attr, str(alias))
    monkeypatch.setattr(cli, '_rights_and_source', lambda *a: pytest.fail('must reject alias before source reads'))
    with pytest.raises(ValueError, match='INPUT_SYMLINK_ANCESTOR'):
        cli._prepare(args)

@pytest.mark.parametrize('field,value', [('global_offset_ms', 1), ('core_interval_ms', [1, 2000]), ('window_interval_ms', [1, 2000])])
def test_public_cached_request_timing_must_match_result(tmp_path, field, value):
    from m2_orchestrator.transcription_recovery import validate_completed_chunk_artifacts, TranscriptionRecoveryError
    request, _, output = request_fixture(tmp_path)
    output.mkdir()
    raw = {'segments': []}
    artifacts = {'audio': 'audio.wav', 'raw': 'raw.json', 'request': 'request.json'}
    (output / artifacts['audio']).write_bytes(b'audio fixture')
    (output / artifacts['raw']).write_text(json.dumps(raw))
    result = {key: request[key] for key in ('chunk_id', 'source_media_hash', 'model_bundle_sha256', 'config_sha256', 'global_offset_ms', 'core_interval_ms', 'window_interval_ms')}
    # A coherently rehashed request still cannot describe a different time window.
    request[field] = value
    request['request_sha256'] = object_hash({k:v for k,v in request.items() if k != 'request_sha256'})
    (output / artifacts['request']).write_text(json.dumps(request))
    hashes = {k:hashlib.sha256((output/v).read_bytes()).hexdigest() for k,v in artifacts.items()}
    result.update(artifacts=artifacts, artifact_hashes=hashes, source_audio_sha256=hashes['audio'], raw_transcript_sha256=hashes['raw'], raw=raw, request_sha256=request['request_sha256'])
    rp=output/'chunk-result.json';rp.write_text(json.dumps(result))
    (output/'chunk-result.sha256').write_text(hashlib.sha256(rp.read_bytes()).hexdigest())
    with pytest.raises(TranscriptionRecoveryError, match='CHUNK_REQUEST_BINDING_MISMATCH'):
        validate_completed_chunk_artifacts(result, output, result['source_media_hash'], result['model_bundle_sha256'], result['config_sha256'])


@pytest.mark.parametrize('key', ['chunk_id','request_file_sha256','source_media_hash','child_result_sha256'])
def test_resource_receipt_rejects_foreign_attempt_bindings(tmp_path, key):
    request, _, output = request_fixture(tmp_path);output.mkdir()
    (output/'chunk-request.json').write_text(json.dumps(request))
    (output/'chunk-result.json').write_text(json.dumps({'observation_state':'OBSERVED'}))
    bound, checksum = w._persist_parent_resource_receipt(output, w._resource_receipt({'returncode':0,'elapsed_seconds':1,'sampled_peak_rss_bytes':123}, phase='child'))
    assert w._load_parent_resource_receipt(output)[1] == checksum
    bound['binding'][key]='foreign'
    (output/'parent-resource-receipt.json').write_text(json.dumps(bound))
    with pytest.raises(w.TranscriptionError, match='RESOURCE_RECEIPT_BINDING_MISMATCH'):
        w._load_parent_resource_receipt(output)


def test_runtime_probe_uses_lexical_virtual_environment_executable(monkeypatch, tmp_path):
    launcher=tmp_path/'venv-python';launcher.symlink_to(sys.executable)
    seen=[]
    def probe(argv, **kwargs):
        seen.append(argv)
        return SimpleNamespace(returncode=0, stdout=json.dumps({'python_version':'fixture','implementation':'cpython','packages':{'av':'fixture-version'}}))
    monkeypatch.setattr(cli.subprocess,'run',probe)
    receipt=cli._runtime_receipt(launcher)
    assert seen[0][0] == str(launcher)
    assert "'av'" in seen[0][2]
    assert receipt['executable_resolved'] == str(Path(sys.executable).resolve())
    assert receipt['packages']['av'] == 'fixture-version'


def test_run_manifest_binds_rights_and_source_record(tmp_path):
    config = build_recovery_config(source_media_hash=SOURCE_HASH, duration_ms=2_000, model_bundle_sha256=MODEL_HASH)
    prepared={'record':{'sha256':SOURCE_HASH,'source_pointer':'media.mp4','source_kind':'approved_research_copy','rights':{'analysis_allowed':True,'receipt_id':'first'}},'model':{'bundle_sha256':MODEL_HASH},'config':config,'config_hash':object_hash(config),'plans':plan_windows(2000),'input_paths':{},'runtime':{}}
    output=tmp_path/'recovery';cli._open_or_create_run(output,prepared)
    prepared['record']['rights']['receipt_id']='different-authority'
    with pytest.raises(ValueError,match='RUN_MANIFEST_BINDING_MISMATCH'):
        cli._open_or_create_run(output,prepared)
