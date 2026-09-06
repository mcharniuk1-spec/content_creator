from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from m2_orchestrator import corpus_media as c


def _model(tmp_path: Path) -> Path:
    root = tmp_path / "model"
    root.mkdir(parents=True, exist_ok=True)
    weights = root / "weights.bin"
    weights.write_bytes(b"model")
    checksum = hashlib.sha256(weights.read_bytes()).hexdigest()
    (root / "model-hash-manifest.json").write_text(json.dumps({"files": [{"path": "weights.bin", "sha256": checksum}]}))
    return root


def _manifest(size: int = 3) -> dict:
    return {
        "schema": "m2.media-manifest.v1",
        "entries": [
            {
                "reel_id": f"instagram:{code}",
                "code": code,
                "sources": [{"route": "explicit_url", "url": "https://cdninstagram.com/x"}],
                "quarantine_reasons": [],
            }
            for code in [f"CODE{i}" for i in range(size)]
        ],
    }


def _fake_acquired_record(run_root: Path, reel_id: str, code: str, attempt_id: int) -> tuple[Path, str, str, Path]:
    media = run_root / "media" / f"{code}.mp4"
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(f"{code}-{attempt_id}".encode())
    media_sha = hashlib.sha256(media.read_bytes()).hexdigest()
    record = {
        "schema": "m2.acquired-media.v1",
        "reel_id": reel_id,
        "media_id": code,
        "observation_state": "OBSERVED",
        "source_pointer": f"media/{code}.mp4",
        "sha256": media_sha,
        "duration_ms": 1000,
        "frame_pts_ms": [0, 500],
        "timebase_provenance": {"audio_offset_ms": 0},
        "has_audio": True,
    }
    record_path = run_root / f"{code}-attempt-{attempt_id}.media.json"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(record), encoding="utf-8")
    return media, media_sha, hashlib.sha256(record_path.read_bytes()).hexdigest(), record_path


def _insert_acquisition_item(
    db: sqlite3.Connection,
    root: Path,
    reel_id: str,
    code: str,
    state: str,
    media: Path,
    media_sha: str,
    record_path: Path,
    record_sha: str,
) -> None:
    db.execute(
        "INSERT OR REPLACE INTO items VALUES (?,?,?,?,?,?,?)",
            (
                reel_id,
                code,
                state,
                str(media.relative_to(root)),
                media_sha,
                record_path.name,
                record_sha,
            ),
        )


def _seed_observed(manifest: dict, root: Path, *, target_ids: list[str] | None = None) -> None:
    selected = set(target_ids) if target_ids is not None else {entry["reel_id"] for entry in manifest["entries"]}
    db = sqlite3.connect(root / "acquisition.sqlite")
    db.executescript(
        "CREATE TABLE IF NOT EXISTS items (reel_id TEXT PRIMARY KEY, code TEXT UNIQUE, state TEXT, artifact TEXT, sha256 TEXT, record_path TEXT, record_sha256 TEXT);"
    )
    for entry in manifest["entries"]:
        if entry["reel_id"] not in selected:
            continue
        media, media_sha, record_sha, record_path = _fake_acquired_record(root, entry["reel_id"], entry["code"], 1)
        _insert_acquisition_item(db, root, entry["reel_id"], entry["code"], "OBSERVED", media, media_sha, record_path, record_sha)
    db.commit()
    db.close()


def _fake_transcribe_factory(state: str, *, failure_code: str | None = None):
    def fake_transcribe(record, root, output, python_executable, model_dir):
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
        payload = {"observation_state": state, "source_media_hash": record["sha256"], "segments": []}
        if state in {"OBSERVED", "SUSPICIOUS_TIMINGS"}:
            payload["segments"] = [{"segment_id": "S001", "start_ms": 0, "end_ms": 500, "text": "fixture", "words": []}]
        if failure_code:
            payload["failure_code"] = failure_code
        payload["resource_receipt"] = {}
        (output / "transcription.json").write_text(json.dumps(payload), encoding="utf-8")
        return payload

    return fake_transcribe


def _fake_preview_factory(state: str):
    def fake_preview(root, record, output):
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
        if state == "DECODE_FAILED":
            result = {"frame_observation_state": state, "sampled_frames": [], "cut_candidates_ms": []}
        else:
            frame_path = output / "F001.jpg"
            frame_path.write_bytes(b"fixture-frame")
            frame_sha = hashlib.sha256(frame_path.read_bytes()).hexdigest()
            result = {
                "frame_observation_state": state,
                "source_media_hash": record["sha256"],
                "sampled_frames": [{"frame_id": "F001", "frame_index": 0, "decoded_frame_index": 0, "timestamp_ms": record["frame_pts_ms"][0], "source_pointer": frame_path.name, "sha256": frame_sha, "observation_state": "OBSERVED", "source_media_hash": record["sha256"]}],
                "frame_budget": {"requested_frames": 1 if state == "OBSERVED" else 2, "observed_frames": 1},
                "cut_candidates_ms": [],
            }
        (output / "receipt.json").write_text(json.dumps(result), encoding="utf-8")
        return result

    return fake_preview


def test_pilot_codes_preserve_full_population_but_attempt_only_pilot_batch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest()
    manifest["pilot_codes"] = ["CODE0"]
    run_root = tmp_path / "run"

    def fake_acquire(manifest, root, **kwargs):
        root = Path(root)
        db = sqlite3.connect(root / "acquisition.sqlite")
        db.executescript(
            "CREATE TABLE IF NOT EXISTS items (reel_id TEXT PRIMARY KEY, code TEXT UNIQUE, state TEXT, artifact TEXT, sha256 TEXT, record_path TEXT, record_sha256 TEXT);"
        )
        first = manifest["entries"][0]
        media, media_sha, record_sha, record_path = _fake_acquired_record(root, first["reel_id"], first["code"], 1)
        _insert_acquisition_item(db, root, first["reel_id"], first["code"], "OBSERVED", media, media_sha, record_path, record_sha)
        db.commit()
        db.close()
        return {
            "schema": "m2.acquisition-summary.v1",
            "states": {"OBSERVED": 1},
            "population": len(manifest["entries"]),
            "processed_this_invocation": 1,
            "hikerapi_calls": 0,
            "asr_executed": False,
            "network_enabled": True,
            "complete_media_coverage": False,
        }

    monkeypatch.setattr(c, "acquire", fake_acquire)
    monkeypatch.setattr(c, "transcribe", _fake_transcribe_factory("OBSERVED"))
    monkeypatch.setattr(c, "extract_preview", _fake_preview_factory("OBSERVED"))

    run = c.CorpusMediaDispatcher(
        manifest,
        run_root,
        model_dir=_model(tmp_path),
        rights_receipt="r",
        batch_size=1,
    )
    result = run.run(network=True)

    assert result["population"] == 3
    assert result["states"]["acquisition_state"] == {"OBSERVED": 1, "DEFERRED_PILOT": 2}
    with sqlite3.connect(run_root / "corpus-media.sqlite") as db:
        rows = db.execute("SELECT code,acquisition_state FROM reels ORDER BY identity_index").fetchall()
        attempted = db.execute("SELECT COUNT(*) FROM attempts WHERE stage='acquisition'").fetchone()[0]
    assert attempted == 1
    assert rows[0] == ("CODE0", "OBSERVED")
    assert rows[1] == ("CODE1", "DEFERRED_PILOT")
    assert rows[2] == ("CODE2", "DEFERRED_PILOT")


def test_hard_stopped_acquisition_keeps_error_code_and_limits_observed_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest()
    run_root = tmp_path / "run"
    run_root.mkdir()

    def fake_acquire(manifest, root, **kwargs):
        root = Path(root)
        db = sqlite3.connect(root / "acquisition.sqlite")
        db.executescript(
            "CREATE TABLE IF NOT EXISTS items (reel_id TEXT PRIMARY KEY, code TEXT UNIQUE, state TEXT, artifact TEXT, sha256 TEXT, record_path TEXT, record_sha256 TEXT);"
        )
        first = manifest["entries"][0]
        media, media_sha, record_sha, record_path = _fake_acquired_record(root, first["reel_id"], first["code"], 1)
        _insert_acquisition_item(db, root, first["reel_id"], first["code"], "OBSERVED", media, media_sha, record_path, record_sha)
        db.commit()
        db.close()
        raise c.AcquisitionError("STORAGE_BUDGET_STOP")

    monkeypatch.setattr(c, "acquire", fake_acquire)
    monkeypatch.setattr(c, "transcribe", _fake_transcribe_factory("OBSERVED"))
    monkeypatch.setattr(c, "extract_preview", _fake_preview_factory("OBSERVED"))

    result = c.CorpusMediaDispatcher(
        manifest,
        run_root,
        model_dir=_model(tmp_path),
        rights_receipt="r",
        batch_size=3,
    ).run(network=True)

    assert result["states"]["acquisition_state"].get("OBSERVED") == 1
    assert result["states"]["acquisition_state"].get("ACQUISITION_FAILED", 0) == 2

    with sqlite3.connect(run_root / "corpus-media.sqlite") as db:
        attempts = db.execute("SELECT reel_id,state,error FROM attempts WHERE stage='acquisition' ORDER BY id").fetchall()
    assert len(attempts) == 3
    assert attempts[0] == ("instagram:CODE0", "OBSERVED", None)
    assert attempts[1][1:] == ("ACQUISITION_FAILED", "STORAGE_BUDGET_STOP")
    assert attempts[2][1:] == ("ACQUISITION_FAILED", "STORAGE_BUDGET_STOP")


def test_startup_recovers_running_attempt_to_interrupted_without_new_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(2)
    run_root = tmp_path / "run"

    def fake_acquire(manifest, root, **kwargs):
        root = Path(root)
        db = sqlite3.connect(root / "acquisition.sqlite")
        db.executescript(
            "CREATE TABLE IF NOT EXISTS items (reel_id TEXT PRIMARY KEY, code TEXT UNIQUE, state TEXT, artifact TEXT, sha256 TEXT, record_path TEXT, record_sha256 TEXT);"
        )
        for entry in manifest["entries"]:
            media, media_sha, record_sha, record_path = _fake_acquired_record(root, entry["reel_id"], entry["code"], 1)
            _insert_acquisition_item(db, root, entry["reel_id"], entry["code"], "OBSERVED", media, media_sha, record_path, record_sha)
        db.commit()
        db.close()
        return {
            "schema": "m2.acquisition-summary.v1",
            "states": {"OBSERVED": len(manifest["entries"])},
            "population": len(manifest["entries"]),
            "processed_this_invocation": len(manifest["entries"]),
            "hikerapi_calls": 0,
            "asr_executed": False,
            "network_enabled": True,
            "complete_media_coverage": True,
        }

    monkeypatch.setattr(c, "acquire", fake_acquire)
    monkeypatch.setattr(c, "transcribe", _fake_transcribe_factory("OBSERVED"))
    monkeypatch.setattr(c, "extract_preview", _fake_preview_factory("OBSERVED"))

    c.CorpusMediaDispatcher(
        manifest,
        run_root,
        model_dir=_model(tmp_path),
        rights_receipt="r",
    ).run(network=True)

    with sqlite3.connect(run_root / "corpus-media.sqlite") as db:
        before = db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
        target_id = db.execute("SELECT id FROM attempts WHERE stage='acquisition' LIMIT 1").fetchone()[0]
        db.execute("UPDATE attempts SET state='RUNNING' WHERE id=?", (target_id,))
        db.commit()

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("RUN should not execute stages after startup recovery")

    monkeypatch.setattr(c, "acquire", fail_if_called)
    monkeypatch.setattr(c, "transcribe", fail_if_called)
    monkeypatch.setattr(c, "extract_preview", fail_if_called)

    c.CorpusMediaDispatcher(
        manifest,
        run_root,
        model_dir=_model(tmp_path),
        rights_receipt="r",
    ).run(network=True)

    with sqlite3.connect(run_root / "corpus-media.sqlite") as db:
        after = db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
        recovered = db.execute("SELECT state FROM attempts WHERE id=?", (target_id,)).fetchone()[0]
    assert recovered == "INTERRUPTED"
    assert after == before


def test_empty_output_unverified_transcript_is_not_promoted_and_failure_code_retained(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(1)
    run_root = tmp_path / "run"

    def fake_acquire(manifest, root, **kwargs):
        root = Path(root)
        db = sqlite3.connect(root / "acquisition.sqlite")
        db.executescript(
            "CREATE TABLE IF NOT EXISTS items (reel_id TEXT PRIMARY KEY, code TEXT UNIQUE, state TEXT, artifact TEXT, sha256 TEXT, record_path TEXT, record_sha256 TEXT);"
        )
        entry = manifest["entries"][0]
        media, media_sha, record_sha, record_path = _fake_acquired_record(root, entry["reel_id"], entry["code"], 1)
        _insert_acquisition_item(db, root, entry["reel_id"], entry["code"], "OBSERVED", media, media_sha, record_path, record_sha)
        db.commit()
        db.close()
        return {
            "schema": "m2.acquisition-summary.v1",
            "states": {"OBSERVED": 1},
            "population": 1,
            "processed_this_invocation": 1,
            "hikerapi_calls": 0,
            "asr_executed": False,
            "network_enabled": True,
            "complete_media_coverage": True,
        }

    monkeypatch.setattr(c, "acquire", fake_acquire)
    monkeypatch.setattr(
        c,
        "transcribe",
        _fake_transcribe_factory("EMPTY_OUTPUT_UNVERIFIED", failure_code="EMPTY_OUTPUT_UNVERIFIED"),
    )
    monkeypatch.setattr(c, "extract_preview", _fake_preview_factory("OBSERVED"))

    result = c.CorpusMediaDispatcher(
        manifest,
        run_root,
        model_dir=_model(tmp_path),
        rights_receipt="r",
    ).run(network=True)

    assert result["states"]["transcript_state"] == {"EMPTY_OUTPUT_UNVERIFIED": 1}
    with sqlite3.connect(run_root / "corpus-media.sqlite") as db:
        attempts = db.execute("SELECT error FROM attempts WHERE stage='transcript'").fetchall()
    assert attempts == [("EMPTY_OUTPUT_UNVERIFIED",)]


def test_empty_observed_frame_result_cannot_be_promoted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(1)
    run_root = tmp_path / "run"

    def fake_acquire(manifest, root, **kwargs):
        root = Path(root); root.mkdir(parents=True, exist_ok=True)
        _seed_observed(manifest, root, target_ids=kwargs.get("target_ids"))
        return {"schema": "m2.acquisition-summary.v1", "states": {"OBSERVED": 1}, "population": 1, "processed_this_invocation": 1}

    def empty_observed_preview(root, record, output):
        output = Path(output); output.mkdir(parents=True, exist_ok=True)
        return {"frame_observation_state": "OBSERVED", "source_media_hash": record["sha256"], "sampled_frames": [], "frame_budget": {"requested_frames": 0, "observed_frames": 0}, "cut_candidates_ms": []}

    monkeypatch.setattr(c, "acquire", fake_acquire)
    monkeypatch.setattr(c, "transcribe", _fake_transcribe_factory("ASR_FAILED"))
    monkeypatch.setattr(c, "extract_preview", empty_observed_preview)
    result = c.CorpusMediaDispatcher(manifest, run_root, model_dir=_model(tmp_path), rights_receipt="r").run(network=True)
    assert result["states"]["frames_state"] == {"VISUAL_FAILED": 1}


def test_forged_higher_attempt_glob_is_ignored_in_favour_of_sqlite_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(1)
    run_root = tmp_path / "run"
    seen_hashes: list[str] = []

    def fake_acquire(manifest, root, **kwargs):
        root = Path(root); root.mkdir(parents=True, exist_ok=True)
        _seed_observed(manifest, root, target_ids=kwargs.get("target_ids"))
        entry = manifest["entries"][0]
        (root / f"{entry['code']}-attempt-99.media.json").write_text(json.dumps({"reel_id": entry["reel_id"], "media_id": entry["code"], "sha256": "f" * 64, "observation_state": "OBSERVED"}), encoding="utf-8")
        return {"schema": "m2.acquisition-summary.v1", "states": {"OBSERVED": 1}, "population": 1, "processed_this_invocation": 1}

    def capture_transcribe(record, root, output, python_executable, model_dir):
        seen_hashes.append(record["sha256"])
        return _fake_transcribe_factory("ASR_FAILED")(record, root, output, python_executable, model_dir)

    monkeypatch.setattr(c, "acquire", fake_acquire)
    monkeypatch.setattr(c, "transcribe", capture_transcribe)
    monkeypatch.setattr(c, "extract_preview", _fake_preview_factory("OBSERVED"))
    c.CorpusMediaDispatcher(manifest, run_root, model_dir=_model(tmp_path), rights_receipt="r").run(network=True)
    with sqlite3.connect(run_root / "acquisition/acquisition.sqlite") as db:
        expected = db.execute("SELECT sha256 FROM items WHERE code='CODE0'").fetchone()[0]
    assert seen_hashes == [expected]


def test_first_batch_exception_falls_back_to_single_item_batches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(2)
    run_root = tmp_path / "run"
    calls: list[int] = []

    def flaky_acquire(manifest, root, **kwargs):
        calls.append(kwargs["limit"])
        if len(calls) == 1:
            raise RuntimeError("fixture batch failure")
        root = Path(root); root.mkdir(parents=True, exist_ok=True)
        _seed_observed(manifest, root, target_ids=kwargs.get("target_ids"))
        return {"schema": "m2.acquisition-summary.v1", "states": {"OBSERVED": 1}, "population": 2, "processed_this_invocation": 1}

    monkeypatch.setattr(c, "acquire", flaky_acquire)
    monkeypatch.setattr(c, "transcribe", _fake_transcribe_factory("ASR_FAILED"))
    monkeypatch.setattr(c, "extract_preview", _fake_preview_factory("OBSERVED"))
    result = c.CorpusMediaDispatcher(manifest, run_root, model_dir=_model(tmp_path), rights_receipt="r", batch_size=2).run(network=True)
    assert result["states"]["acquisition_state"] == {"OBSERVED": 2}
    assert calls[:3] == [2, 1, 1]


@pytest.mark.parametrize(
    ("state", "source_hash", "error"),
    [
        ("OBSERVED", "0" * 64, "TRANSCRIPT_MEDIA_HASH_MISMATCH"),
        ("INVALID_STATE", None, "TRANSCRIPT_STATE_INVALID"),
    ],
)
def test_transcript_result_invariants_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str, source_hash: str | None, error: str) -> None:
    manifest = _manifest(1)
    run_root = tmp_path / "run"

    def fake_acquire(manifest, root, **kwargs):
        root = Path(root); root.mkdir(parents=True, exist_ok=True); _seed_observed(manifest, root, target_ids=kwargs.get("target_ids"))
        return {"schema": "m2.acquisition-summary.v1", "states": {"OBSERVED": 1}, "population": 1, "processed_this_invocation": 1}

    def bad_transcribe(record, root, output, python_executable, model_dir):
        output = Path(output); output.mkdir(parents=True, exist_ok=True)
        payload = {"observation_state": state, "source_media_hash": source_hash, "segments": [{"segment_id": "S001", "start_ms": 0, "end_ms": 500, "text": "fixture", "words": []}]}
        (output / "transcription.json").write_text(json.dumps(payload), encoding="utf-8")
        return payload

    monkeypatch.setattr(c, "acquire", fake_acquire)
    monkeypatch.setattr(c, "transcribe", bad_transcribe)
    monkeypatch.setattr(c, "extract_preview", _fake_preview_factory("OBSERVED"))
    result = c.CorpusMediaDispatcher(manifest, run_root, model_dir=_model(tmp_path), rights_receipt="r").run(network=True)
    assert result["states"]["transcript_state"] == {"ASR_FAILED": 1}
    with sqlite3.connect(run_root / "corpus-media.sqlite") as db:
        assert db.execute("SELECT error FROM attempts WHERE stage='transcript'").fetchone()[0] == error


def test_acquisition_database_symlink_is_rejected_before_worker_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _manifest(1)
    run_root = tmp_path / "run"; acquisition = run_root / "acquisition"
    acquisition.mkdir(parents=True)
    target = tmp_path / "outside.sqlite"; target.write_bytes(b"fixture")
    (acquisition / "acquisition.sqlite").symlink_to(target)
    monkeypatch.setattr(c, "acquire", lambda *args, **kwargs: pytest.fail("worker must not run with symlinked acquisition DB"))
    with pytest.raises(c.CorpusMediaError, match="ACQUISITION_DB_SYMLINK"):
        c.CorpusMediaDispatcher(manifest, run_root, model_dir=_model(tmp_path), rights_receipt="r").run(network=True)
