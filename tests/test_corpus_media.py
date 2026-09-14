from __future__ import annotations

import fcntl
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from m2_orchestrator import corpus_media as c


def _model(tmp_path: Path) -> Path:
    root = tmp_path / "model"
    root.mkdir(parents=True)
    weights = root / "weights.bin"
    weights.write_bytes(b"model")
    checksum = hashlib.sha256(weights.read_bytes()).hexdigest()
    (root / "model-hash-manifest.json").write_text(json.dumps({"files": [{"path": "weights.bin", "sha256": checksum}]}))
    return root


def _manifest() -> dict:
    return {"schema": "m2.media-manifest.v1", "entries": [{"reel_id": f"instagram:CODE{i}", "code": f"CODE{i}", "sources": [{"route": "explicit_url", "url": "https://cdninstagram.com/x"}], "quarantine_reasons": []} for i in range(3)]}


def _fake_acquire_factory(monkeypatch: pytest.MonkeyPatch, entries: list[dict], observed: set[str]):
    calls: list[dict] = []

    def fake_acquire(manifest, root, **kwargs):
        calls.append(kwargs)
        root = Path(root)
        (root / "media").mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(root / "acquisition.sqlite")
        db.executescript("CREATE TABLE IF NOT EXISTS items (reel_id TEXT PRIMARY KEY, code TEXT UNIQUE, state TEXT, artifact TEXT, sha256 TEXT, record_path TEXT, record_sha256 TEXT);")
        added = 0
        for entry in entries:
            if added >= kwargs["limit"]:
                break
            if entry["code"] in observed:
                continue
            media = root / "media" / (entry["code"] + ".mp4")
            media.write_bytes((entry["code"] + "-media").encode())
            media_hash = hashlib.sha256(media.read_bytes()).hexdigest()
            record = {"schema": "m2.acquired-media.v1", "reel_id": entry["reel_id"], "media_id": entry["code"], "observation_state": "OBSERVED", "source_pointer": f"media/{entry['code']}.mp4", "sha256": media_hash, "duration_ms": 1000, "frame_pts_ms": [0, 500], "timebase_provenance": {"audio_offset_ms": 0}, "has_audio": True}
            record_path = root / (entry["code"] + "-attempt-1.media.json")
            record_path.write_text(json.dumps(record))
            record_hash = hashlib.sha256(record_path.read_bytes()).hexdigest()
            db.execute("INSERT OR REPLACE INTO items VALUES (?,?,?,?,?,?,?)", (entry["reel_id"], entry["code"], "OBSERVED", str(media.relative_to(root)), media_hash, record_path.name, record_hash))
            observed.add(entry["code"])
            added += 1
        db.commit(); db.close()
        return {"schema": "m2.acquisition-summary.v1", "states": {"OBSERVED": len(observed)}, "population": len(entries), "processed_this_invocation": kwargs["limit"]}

    monkeypatch.setattr(c, "acquire", fake_acquire)
    return calls


def _valid_preview(root, media, output):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    frame = output / "F001.jpg"; frame.write_bytes(b"fixture-frame")
    frame_hash = hashlib.sha256(frame.read_bytes()).hexdigest()
    result = {"frame_observation_state": "OBSERVED", "source_media_hash": media["sha256"],
              "sampled_frames": [{"frame_id": "F001", "frame_index": 0, "decoded_frame_index": 0, "timestamp_ms": media["frame_pts_ms"][0], "source_pointer": frame.name, "sha256": frame_hash, "observation_state": "OBSERVED", "source_media_hash": media["sha256"]}],
              "frame_budget": {"requested_frames": 1, "observed_frames": 1}, "cut_candidates_ms": []}
    (output / "receipt.json").write_text(json.dumps(result))
    return result


def _transcript_result(record, state, failure_code=None):
    payload = {"observation_state": state, "source_media_hash": record["sha256"], "segments": []}
    if state in {"OBSERVED", "SUSPICIOUS_TIMINGS"}:
        payload["segments"] = [{"segment_id": "S001", "start_ms": 0, "end_ms": 500, "text": "fixture", "words": []}]
    if failure_code:
        payload["failure_code"] = failure_code
    payload["resource_receipt"] = {}
    return payload


def test_asr_failure_does_not_block_frames_and_denominator_is_full(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(); entries = manifest["entries"]; observed: set[str] = set()
    calls = _fake_acquire_factory(monkeypatch, entries, observed)

    def fake_transcribe(record, root, output, python_executable, model_dir):
        Path(output).mkdir(parents=True, exist_ok=True)
        result = _transcript_result(record, "ASR_FAILED", "ASR_EXECUTION_FAILED")
        result["resource_receipt"] = {"sampled_peak_rss_bytes": 1}
        (Path(output) / "transcription.json").write_text(json.dumps(result))
        return result

    def fake_preview(root, media, output):
        output = Path(output); output.mkdir(parents=True, exist_ok=True)
        frame = output / "F001.jpg"; frame.write_bytes(b"fixture-frame")
        frame_hash = hashlib.sha256(frame.read_bytes()).hexdigest()
        result = {"frame_observation_state": "OBSERVED", "source_media_hash": media["sha256"],
                  "sampled_frames": [{"frame_id": "F001", "frame_index": 0, "decoded_frame_index": 0, "timestamp_ms": media["frame_pts_ms"][0], "source_pointer": frame.name, "sha256": frame_hash, "observation_state": "OBSERVED", "source_media_hash": media["sha256"]}],
                  "frame_budget": {"requested_frames": 1, "observed_frames": 1}, "cut_candidates_ms": []}
        (output / "receipt.json").write_text(json.dumps(result))
        return result

    monkeypatch.setattr(c, "transcribe", fake_transcribe)
    monkeypatch.setattr(c, "extract_preview", fake_preview)
    result = c.CorpusMediaDispatcher(manifest, tmp_path / "run", model_dir=_model(tmp_path), rights_receipt="research-r1", batch_size=2).run(network=True)
    assert result["population"] == 3
    assert result["states"]["acquisition_state"]["OBSERVED"] == 3
    assert result["states"]["transcript_state"]["ASR_EXECUTION_FAILED"] == 3
    assert result["states"]["frames_state"]["OBSERVED"] == 3
    assert result["states"]["scene_review_state"]["REVIEW_PENDING"] == 3
    assert all(call["limit"] <= 2 and call["network"] is True for call in calls)
    assert sqlite3.connect(tmp_path / "run/corpus-media.sqlite").execute("SELECT COUNT(*) FROM reels").fetchone()[0] == 3


def test_resume_rehashes_completed_acquisition_and_rejects_changed_media(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(); entries = manifest["entries"]; observed: set[str] = set()
    _fake_acquire_factory(monkeypatch, entries, observed)
    monkeypatch.setattr(c, "transcribe", lambda *args: {"observation_state": "ASR_FAILED", "failure_code": "fixture"})
    monkeypatch.setattr(c, "extract_preview", lambda *args: (_ for _ in ()).throw(RuntimeError("frame fixture")))
    run = tmp_path / "run"
    model = _model(tmp_path)
    c.CorpusMediaDispatcher(manifest, run, model_dir=model, rights_receipt="research-r1").run(network=True, max_items=1)
    media = run / "acquisition/media/CODE0.mp4"
    media.write_bytes(b"tampered")
    with pytest.raises(c.CorpusMediaError, match="ACQUISITION_ARTIFACT_CHANGED"):
        c.CorpusMediaDispatcher(manifest, run, model_dir=model, rights_receipt="research-r1").run(network=True, max_items=1)


def test_lock_and_recovery_event_timeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(); entries = manifest["entries"]; observed: set[str] = set()
    _fake_acquire_factory(monkeypatch, entries, observed)
    model = _model(tmp_path); run = tmp_path / "run"
    (run).mkdir()
    lock_path = run / ".dispatcher.lock"
    handle = lock_path.open("a")
    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with pytest.raises(c.CorpusMediaError, match="DISPATCHER_ALREADY_RUNNING"):
            c.CorpusMediaDispatcher(manifest, run, model_dir=model, rights_receipt="research-r1").run(network=True)
    finally:
        fcntl.flock(handle, fcntl.LOCK_UN); handle.close()
    assert c.CorpusMediaDispatcher(manifest, run, model_dir=model, rights_receipt="research-r1").run(network=True, max_items=1)["population"] == 3


def test_batch_and_network_gates_are_explicit(tmp_path: Path) -> None:
    with pytest.raises(c.CorpusMediaError, match="BATCH_SIZE_LIMIT"):
        c.CorpusMediaDispatcher(_manifest(), tmp_path / "run", model_dir=_model(tmp_path), rights_receipt="r", batch_size=9)
    dispatcher = c.CorpusMediaDispatcher(_manifest(), tmp_path / "run2", model_dir=_model(tmp_path / "other"), rights_receipt="r")
    with pytest.raises(c.CorpusMediaError, match="EXPLICIT_NETWORK_TRUE_REQUIRED"):
        dispatcher.run(network=False)


def test_observation_states_are_preserved_and_not_promoted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(); entries = manifest["entries"]; observed: set[str] = set()
    _fake_acquire_factory(monkeypatch, entries, observed)
    def fake_transcribe(record, root, output, python_executable, model_dir):
        Path(output).mkdir(parents=True, exist_ok=True)
        state = "EMPTY_OUTPUT_UNVERIFIED" if record["media_id"] == "CODE0" else "SUSPICIOUS_TIMINGS"
        result = _transcript_result(record, state)
        (Path(output) / "transcription.json").write_text(json.dumps(result))
        return result
    def fake_preview(root, media, output):
        output = Path(output); output.mkdir(parents=True, exist_ok=True)
        frame = output / "F001.jpg"; frame.write_bytes(b"fixture-frame")
        frame_hash = hashlib.sha256(frame.read_bytes()).hexdigest()
        (output / "receipt.json").write_text("{}")
        state = "PARTIAL" if media["media_id"] == "CODE0" else "DECODE_FAILED"
        if state == "DECODE_FAILED":
            return {"frame_observation_state": state, "sampled_frames": [], "cut_candidates_ms": []}
        return {"frame_observation_state": state, "source_media_hash": media["sha256"],
                "sampled_frames": [{"frame_id": "F001", "frame_index": 0, "decoded_frame_index": 0, "timestamp_ms": media["frame_pts_ms"][0], "source_pointer": frame.name, "sha256": frame_hash, "observation_state": "OBSERVED", "source_media_hash": media["sha256"]}],
                "frame_budget": {"requested_frames": 2, "observed_frames": 1}, "cut_candidates_ms": []}
    monkeypatch.setattr(c, "transcribe", fake_transcribe)
    monkeypatch.setattr(c, "extract_preview", fake_preview)
    result = c.CorpusMediaDispatcher(manifest, tmp_path / "run", model_dir=_model(tmp_path), rights_receipt="r").run(network=True)
    assert result["states"]["transcript_state"] == {"EMPTY_OUTPUT_UNVERIFIED": 1, "SUSPICIOUS_TIMINGS": 2}
    assert result["states"]["frames_state"] == {"DECODE_FAILED": 2, "PARTIAL": 1}
    assert result["states"]["scene_review_state"] == {"NOT_REVIEWED": 2, "REVIEW_PENDING": 1}


def test_failed_acquisition_advances_to_remaining_identities(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(); entries = manifest["entries"]
    calls: list[int] = []
    def flaky_acquire(manifest, root, **kwargs):
        root = Path(root); (root / "media").mkdir(parents=True, exist_ok=True); calls.append(kwargs["limit"])
        db = sqlite3.connect(root / "acquisition.sqlite")
        db.executescript("CREATE TABLE IF NOT EXISTS items (reel_id TEXT PRIMARY KEY, code TEXT UNIQUE, state TEXT, artifact TEXT, sha256 TEXT, record_path TEXT, record_sha256 TEXT);")
        rows = {row[1]: row for row in db.execute("SELECT * FROM items")}
        processed = 0
        for entry in entries:
            if processed >= kwargs["limit"]: break
            row = rows.get(entry["code"])
            if row and row[2] in {"OBSERVED", "UNAVAILABLE"}: continue
            if row and row[2] not in {"NOT_ATTEMPTED", "RETRYABLE"}: continue
            processed += 1
            if entry["code"] == "CODE0":
                db.execute("INSERT OR REPLACE INTO items VALUES (?,?,?,?,?,?,?)", (entry["reel_id"], entry["code"], "UNAVAILABLE", None, None, None, None))
                continue
            media = root / "media" / (entry["code"] + ".mp4"); media.write_bytes(b"fixture")
            sha = hashlib.sha256(media.read_bytes()).hexdigest()
            record = {"schema":"m2.acquired-media.v1", "reel_id":entry["reel_id"], "media_id":entry["code"], "observation_state":"OBSERVED", "source_pointer":"media/" + entry["code"] + ".mp4", "sha256":sha, "duration_ms":1000, "frame_pts_ms":[0,500], "has_audio":True}
            rp = root / (entry["code"] + "-attempt-1.media.json"); rp.write_text(json.dumps(record)); rsha = hashlib.sha256(rp.read_bytes()).hexdigest()
            db.execute("INSERT OR REPLACE INTO items VALUES (?,?,?,?,?,?,?)", (entry["reel_id"], entry["code"], "OBSERVED", str(media.relative_to(root)), sha, rp.name, rsha))
        db.commit(); db.close()
        return {"processed_this_invocation": processed}
    monkeypatch.setattr(c, "acquire", flaky_acquire)
    monkeypatch.setattr(c, "transcribe", lambda record, root, output, python_executable, model_dir: (Path(output).mkdir(parents=True, exist_ok=True), _transcript_result(record, "ASR_FAILED"))[1])
    monkeypatch.setattr(c, "extract_preview", _valid_preview)
    result = c.CorpusMediaDispatcher(manifest, tmp_path / "run", model_dir=_model(tmp_path), rights_receipt="r", batch_size=2).run(network=True)
    assert result["states"]["acquisition_state"] == {"OBSERVED": 2, "UNAVAILABLE": 1}
    assert len(calls) >= 2


def test_retryable_transcript_uses_new_attempt_output_and_stops_at_terminal_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(); entries = manifest["entries"]; observed: set[str] = set()
    _fake_acquire_factory(monkeypatch, entries[:1], observed)
    manifest["entries"] = entries[:1]
    calls = {"count": 0}
    def flaky_transcribe(record, root, output, python_executable, model_dir):
        calls["count"] += 1; Path(output).mkdir(parents=True, exist_ok=True)
        state = "ASR_FAILED" if calls["count"] == 1 else "OBSERVED"
        result = _transcript_result(record, state, "ASR_EXECUTION_FAILED" if state == "ASR_FAILED" else None)
        (Path(output) / "transcription.json").write_text(json.dumps(result))
        return result
    monkeypatch.setattr(c, "transcribe", flaky_transcribe)
    monkeypatch.setattr(c, "extract_preview", _valid_preview)
    run = tmp_path / "run"
    result = c.CorpusMediaDispatcher(manifest, run, model_dir=_model(tmp_path), rights_receipt="r").run(network=True)
    assert result["states"]["transcript_state"] == {"OBSERVED": 1}
    db = sqlite3.connect(run / "corpus-media.sqlite")
    assert db.execute("SELECT COUNT(*) FROM attempts WHERE stage='transcript'").fetchone()[0] == 2
    assert (run / "transcripts/CODE0/attempt-1").is_dir() and (run / "transcripts/CODE0/attempt-2").is_dir()
