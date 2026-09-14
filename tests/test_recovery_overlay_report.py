from __future__ import annotations

import hashlib
import json
import sqlite3

import pytest

from m2_orchestrator.recovery_overlay_report import (
    RecoveryOverlayError,
    build_recovery_overlay,
    load_primary_ledger,
    load_acquisition_records,
    load_recovery_records,
)


SNAPSHOT = "a" * 64
H1, H2 = "1" * 64, "2" * 64


def _canonical():
    return [
        {"reel_id": "instagram:R1", "code": "R1", "identity_index": 0, "source_snapshot_hash": SNAPSHOT},
        {"reel_id": "instagram:R2", "code": "R2", "identity_index": 1, "source_snapshot_hash": SNAPSHOT},
        {"reel_id": "instagram:R3", "code": "R3", "identity_index": 2, "source_snapshot_hash": SNAPSHOT},
    ]


def _primary():
    rows = []
    for index, code in enumerate(("R1", "R2", "R3")):
        observed = index < 2
        source = H1 if index == 0 else H2 if index == 1 else None
        rows.append({
            "reel_id": f"instagram:{code}", "code": code, "identity_index": index,
            "primary_states": {"acquisition": "OBSERVED" if observed else "NOT_ATTEMPTED", "transcript": "ASR_FAILED" if index == 0 else "NOT_ATTEMPTED", "frames": "NOT_ATTEMPTED", "scene_review": "NOT_ATTEMPTED"},
            "primary_artifacts": {"acquisition": {f"acquisition/media/{code}.mp4": source} if source else {}, "transcript": {}, "frames": {}},
            "primary_attempt_history": [{"stage": "transcript", "attempt": 1, "state": "ASR_FAILED", "error": "PROCESS_RSS_LIMIT", "artifacts": {}, "resources": {}}] if index == 0 else [],
        })
    return rows


def _acquisition():
    return [
        {"reel_id": "instagram:R1", "code": "R1", "identity_index": 0, "sha256": H1, "record_sha256": "a" * 64, "source_pointer": "private/R1.mp4", "observation_state": "OBSERVED"},
        {"reel_id": "instagram:R2", "code": "R2", "identity_index": 1, "sha256": H2, "record_sha256": "b" * 64, "source_pointer": "private/R2.mp4", "observation_state": "OBSERVED", "has_audio": False, "original_audio_unknown": True, "speech_state": "UNKNOWN"},
    ]


def _recovery():
    return [
        {"reel_id": "instagram:R1", "code": "R1", "identity_index": 0, "source_media_hash": H1, "artifact_path": "R1/transcription-recovery.json", "artifact_sha256": "f" * 64, "wrapper": {"schema": "m2.transcription-recovery-preflight.v1"}, "result": {
            "source_media_hash": H1, "observation_state": "SUSPICIOUS_TIMINGS", "machine_observed": True,
            "analysis_ready": True, "analysis_approved": True, "review_state": "REVIEW_REQUIRED",
            "owned_aligned_word_count": 22, "lexical_word_count": 33, "aligned_word_count": 22, "unaligned_word_count": 11, "raw_word_count": 33,
            "language": "hi", "language_probability": 0.975, "word_timing": "PARTIAL", "chunk_count": 1, "completed_chunk_count": 1,
        }},
        {"reel_id": "instagram:R2", "code": "R2", "identity_index": 1, "source_media_hash": H2, "artifact_path": "R2/transcription-recovery.json", "artifact_sha256": "e" * 64, "wrapper": {}, "result": {
            "source_media_hash": H2, "observation_state": "NOT_APPLICABLE", "machine_observed": False, "review_state": "REVIEW_REQUIRED",
            "original_audio_unknown": True, "original_audio_status": "UNKNOWN", "speech_state": "UNKNOWN", "analysis_ready": False,
        }},
    ]


def test_overlay_preserves_primary_failure_and_gates_machine_quality():
    report = build_recovery_overlay(_canonical(), _primary(), _acquisition(), _recovery(), source_snapshot_hash=SNAPSHOT, expected_population=3)
    row = report["rows"][0]
    assert row["primary"]["primary_states"]["transcript"] == "ASR_FAILED"
    assert row["recovery"]["state"] == "SUSPICIOUS_TIMINGS"
    assert row["recovery"]["machine_observed"] is True
    assert row["recovery"]["owned_aligned_words"] == {"count": 22, "state": "OBSERVED_COUNT_ONLY"}
    assert row["recovery"]["word_metrics"]["lexical_word_count"] == 33
    assert row["recovery"]["language"] == "hi"
    assert row["recovery"]["analysis_ready"] is False
    assert row["recovery"]["reported_analysis_ready"] is True
    assert row["recovery"]["acoustic_review_state"] == "NOT_REVIEWED"
    assert report["source_binding"]["primary_ledger_unchanged"] is True


def test_video_only_unknown_is_not_no_speech_and_nulls_stay_null():
    report = build_recovery_overlay(_canonical(), _primary(), _acquisition(), _recovery(), source_snapshot_hash=SNAPSHOT, expected_population=3)
    row = report["rows"][1]
    assert row["recovery"]["original_audio_unknown"] is True
    assert row["recovery"]["original_audio_status"] == "UNKNOWN"
    assert row["recovery"]["speech_state"] == "UNKNOWN"
    assert row["recovery"]["owned_aligned_words"]["count"] is None
    assert row["recovery"]["word_metrics"]["raw_word_count"] is None
    no_recovery = [item for item in _recovery() if item["code"] != "R2"]
    no_attempt = build_recovery_overlay(_canonical(), _primary(), _acquisition(), no_recovery, source_snapshot_hash=SNAPSHOT, expected_population=3)["rows"][1]["recovery"]
    assert no_attempt["state"] == "NOT_ATTEMPTED"
    assert no_attempt["original_audio_unknown"] is True
    assert no_attempt["speech_state"] == "UNKNOWN"


def test_conflicting_source_hashes_fail_closed():
    bad_acquisition = _acquisition() + [{**_acquisition()[0], "sha256": H2}]
    with pytest.raises(RecoveryOverlayError, match="ACQUISITION_SOURCE_HASH_CONFLICT"):
        build_recovery_overlay(_canonical(), _primary(), bad_acquisition, [], source_snapshot_hash=SNAPSHOT, expected_population=3)
    bad_recovery = _recovery()
    bad_recovery[0] = {**bad_recovery[0], "source_media_hash": H2, "result": {**bad_recovery[0]["result"], "source_media_hash": H2}}
    with pytest.raises(RecoveryOverlayError, match="RECOVERY_ACQUISITION_SOURCE_MISMATCH"):
        build_recovery_overlay(_canonical(), _primary(), _acquisition(), bad_recovery, source_snapshot_hash=SNAPSHOT, expected_population=3)
    nested_conflict = _recovery()[0]
    nested_conflict["wrapper"] = {"source_media_hash": H2}
    with pytest.raises(RecoveryOverlayError, match="RECOVERY_SOURCE_HASH_CONFLICT"):
        build_recovery_overlay(_canonical(), _primary(), _acquisition(), [nested_conflict], source_snapshot_hash=SNAPSHOT, expected_population=3)
    aggregate_conflict = _recovery()[0]
    aggregate_conflict["result"] = {**aggregate_conflict["result"], "aggregate_metrics": {"source_media_hash": H2}}
    with pytest.raises(RecoveryOverlayError, match="RECOVERY_SOURCE_HASH_CONFLICT"):
        build_recovery_overlay(_canonical(), _primary(), _acquisition(), [aggregate_conflict], source_snapshot_hash=SNAPSHOT, expected_population=3)


def test_identity_collision_and_missing_primary_fail_closed():
    collision = {**_recovery()[0], "reel_id": "instagram:R2"}
    with pytest.raises(RecoveryOverlayError, match="SOURCE_CODE_REEL_COLLISION"):
        build_recovery_overlay(_canonical(), _primary(), _acquisition(), [collision], source_snapshot_hash=SNAPSHOT, expected_population=3)
    with pytest.raises(RecoveryOverlayError, match="PRIMARY_IDENTITY_MISSING"):
        build_recovery_overlay(_canonical(), _primary()[:-1], _acquisition(), [], source_snapshot_hash=SNAPSHOT, expected_population=3)


def test_empty_unreviewed_overlay_writes_all_rows_without_raw_words(tmp_path):
    empty = [{"reel_id": "instagram:R3", "code": "R3", "identity_index": 2, "source_media_hash": H2, "artifact_path": "R3/transcription-recovery.json", "artifact_sha256": "d" * 64, "wrapper": {}, "result": {"source_media_hash": H2, "observation_state": "EMPTY_OUTPUT_UNVERIFIED", "machine_observed": False, "review_state": "REVIEW_REQUIRED", "analysis_ready": False}}]
    output = tmp_path / "overlay"
    report = build_recovery_overlay(_canonical(), _primary(), _acquisition(), empty, source_snapshot_hash=SNAPSHOT, output_dir=output, expected_population=3)
    assert len(report["rows"]) == 3
    lines = (output / "recovery-overlay.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    header = (output / "recovery-overlay.csv").read_text(encoding="utf-8").splitlines()[0].split(",")
    assert all(name not in header for name in ("primary", "acquisition", "recovery"))
    assert len(header) > 30
    assert json.loads(lines[-1])["recovery"]["state"] == "EMPTY_OUTPUT_UNVERIFIED"
    assert "words" not in json.loads(lines[-1])["recovery"]
    fields = json.loads((output / "field-dictionary.json").read_text(encoding="utf-8"))
    assert all(column in fields for column in header)
    assert "recovery.acoustic_review_state" in fields
    with pytest.raises(RecoveryOverlayError, match="OUTPUT_DIRECTORY_MUST_BE_NEW"):
        build_recovery_overlay(_canonical(), _primary(), _acquisition(), [], source_snapshot_hash=SNAPSHOT, output_dir=output, expected_population=3)


def test_primary_reader_hashes_one_transaction_snapshot_and_binds_events(tmp_path):
    path = tmp_path / "ledger.sqlite"
    db = sqlite3.connect(path)
    db.executescript("""
        create table binding(key text primary key, value text not null);
        create table reels(reel_id text primary key, code text not null, identity_index integer not null, acquisition_state text not null, transcript_state text not null, frames_state text not null, scene_review_state text not null, acquisition_artifact text, transcript_artifact text, frames_artifact text);
        create table attempts(reel_id text, stage text, attempt integer, state text, error text, started real, finished real, artifacts_json text, resources_json text);
        create table events(id integer primary key, event text, stage text, reel_id text, observed_at real, payload_json text);
    """)
    db.execute("insert into binding values ('manifest_sha256', ?)", (SNAPSHOT,))
    db.execute("insert into reels values ('instagram:R1','R1',0,'OBSERVED','ASR_FAILED','NOT_ATTEMPTED','NOT_ATTEMPTED',?,?,?)", (json.dumps({"a": H1}), "{}", "{}"))
    db.execute("insert into attempts values ('instagram:R1','transcript',1,'ASR_FAILED','PROCESS_RSS_LIMIT',1.0,2.0,'{}','{}')")
    db.execute("insert into events values (1,'stage_finished','transcript','instagram:R1',2.0,'{}')")
    db.commit(); db.close()
    rows, binding = load_primary_ledger(path, expected_snapshot_hash=SNAPSHOT)
    assert len(rows) == 1
    assert binding["ledger_snapshot_event_count"] == 1
    assert len(binding["ledger_snapshot_hash"]) == 64
    first_hash = binding["ledger_snapshot_hash"]
    db = sqlite3.connect(path); db.execute("update events set payload_json='{""changed"":true}'"); db.commit(); db.close()
    with pytest.raises(RecoveryOverlayError, match="PRIMARY_LEDGER_SNAPSHOT_MISMATCH"):
        load_primary_ledger(path, expected_snapshot_hash=SNAPSHOT, expected_ledger_snapshot_hash=first_hash)


def test_primary_reader_requires_snapshot_binding_and_string_hashes(tmp_path):
    def make(path, binding_rows):
        db = sqlite3.connect(path)
        db.executescript("""
            create table binding(key text primary key, value);
            create table reels(reel_id text primary key, code text not null, identity_index integer not null, acquisition_state text not null, transcript_state text not null, frames_state text not null, scene_review_state text not null, acquisition_artifact text, transcript_artifact text, frames_artifact text);
            create table attempts(reel_id text, stage text, attempt integer, state text, error text, started real, finished real, artifacts_json text, resources_json text);
        """)
        db.executemany("insert into binding values (?,?)", binding_rows)
        db.execute("insert into reels values ('instagram:R1','R1',0,'NOT_ATTEMPTED','NOT_ATTEMPTED','NOT_ATTEMPTED','NOT_ATTEMPTED',NULL,NULL,NULL)")
        db.commit(); db.close()

    missing = tmp_path / "missing-binding.sqlite"
    make(missing, [])
    with pytest.raises(RecoveryOverlayError, match="PRIMARY_SNAPSHOT_BINDING_MISSING"):
        load_primary_ledger(missing, expected_snapshot_hash=SNAPSHOT)

    non_string = tmp_path / "non-string-binding.sqlite"
    make(non_string, [("manifest_sha256", 7)])
    with pytest.raises(RecoveryOverlayError, match="PRIMARY_SNAPSHOT_BINDING_INVALID"):
        load_primary_ledger(non_string, expected_snapshot_hash=SNAPSHOT)


def test_claimed_review_flags_without_hash_bound_receipt_stay_unapproved():
    attempted = _recovery()[0]
    attempted["result"] = {**attempted["result"], "review_state": "APPROVED_WITH_SCOPE", "analysis_approved": True, "analysis_ready": True}
    report = build_recovery_overlay(_canonical(), _primary(), _acquisition(), [attempted], source_snapshot_hash=SNAPSHOT, expected_population=3)
    recovery = report["rows"][0]["recovery"]
    assert recovery["reported_review_state"] == "APPROVED_WITH_SCOPE"
    assert recovery["review_receipt_state"] == "MISSING_OR_INVALID"
    assert recovery["analysis_approved"] is False
    assert recovery["analysis_ready"] is False


def test_declared_exact_distinct_hash_bound_scoped_receipt_can_approve():
    attempted = _recovery()[0]
    result = {**attempted["result"], "config_sha256": "c" * 64, "model_bundle_sha256": "b" * 64, "output_sha256": "d" * 64, "review_state": "APPROVED_WITH_SCOPE", "analysis_approved": True, "analysis_ready": True}
    result["review_receipt"] = {"status": "APPROVED_WITH_SCOPE", "maker_actor": "maker", "reviewer_actor": "reviewer", "source_media_hash": H1, "config_sha256": "c" * 64, "model_bundle_sha256": "b" * 64, "output_sha256": "d" * 64, "scope": "acoustic_review_of_selected_attempt"}
    attempted["result"] = result
    report = build_recovery_overlay(_canonical(), _primary(), _acquisition(), [attempted], source_snapshot_hash=SNAPSHOT, expected_population=3)
    recovery = report["rows"][0]["recovery"]
    assert recovery["review_receipt_state"] == "DECLARED_UNVERIFIED"
    assert recovery["analysis_approved"] is False
    assert recovery["analysis_ready"] is False


def test_latest_attempt_is_selected_without_cross_attempt_metric_mixing():
    first, second = _recovery()[0], _recovery()[0].copy()
    first["result"] = {**first["result"], "attempt": 1}
    second["artifact_sha256"] = "a" * 64
    second["result"] = {"source_media_hash": H1, "attempt": 2, "observation_state": "PROCESS_RSS_LIMIT", "machine_observed": False, "review_state": "REVIEW_REQUIRED", "failure_code": "PROCESS_RSS_LIMIT"}
    report = build_recovery_overlay(_canonical(), _primary(), _acquisition(), [first, second], source_snapshot_hash=SNAPSHOT, expected_population=3)
    recovery = report["rows"][0]["recovery"]
    assert recovery["state"] == "PROCESS_RSS_LIMIT"
    assert recovery["machine_observed"] is False
    assert recovery["prior_attempt_machine_observed"] is True
    assert recovery["owned_aligned_words"]["count"] is None
    assert recovery["word_metrics"]["raw_word_count"] is None
    assert recovery["selected_attempt_number"] == 2
    duplicate = second.copy()
    with pytest.raises(RecoveryOverlayError, match="RECOVERY_ATTEMPT_DUPLICATE"):
        build_recovery_overlay(_canonical(), _primary(), _acquisition(), [first, second, duplicate], source_snapshot_hash=SNAPSHOT, expected_population=3)


def test_canonical_snapshot_binding_cannot_be_omitted_or_conflated_with_media_hash():
    missing = _canonical()
    del missing[0]["source_snapshot_hash"]
    missing[0]["source_media_hash"] = H1
    with pytest.raises(RecoveryOverlayError, match="CANONICAL_SNAPSHOT_BINDING_MISSING"):
        build_recovery_overlay(missing, _primary(), _acquisition(), [], source_snapshot_hash=SNAPSHOT, expected_population=3)
    distinct = _canonical()
    distinct[0]["source_media_hash"] = H1
    report = build_recovery_overlay(distinct, _primary(), _acquisition(), [], source_snapshot_hash=SNAPSHOT, expected_population=3)
    assert report["rows"][0]["source_snapshot_hash"] == SNAPSHOT
    assert report["rows"][0]["canonical_source_media_hash"] == H1


def test_acquisition_and_recovery_loaders_bind_record_and_media_bytes(tmp_path):
    corpus = tmp_path / "corpus"
    acquisition_root = corpus / "acquisition"
    media_root = corpus / "media"
    (acquisition_root / "nested").mkdir(parents=True)
    media_root.mkdir()
    media = b"retained-video"
    (media_root / "R1.mp4").write_bytes(media)
    record = {"reel_id": "instagram:R1", "source_pointer": "media/R1.mp4", "sha256": hashlib.sha256(media).hexdigest(), "observation_state": "OBSERVED"}
    (acquisition_root / "nested" / "R1.media.json").write_text(json.dumps(record), encoding="utf-8")
    loaded = load_acquisition_records(acquisition_root)
    assert loaded[0]["media_sha256_verified"] is True
    assert len(loaded[0]["record_sha256"]) == 64
    recovery_root = tmp_path / "recovery"
    (recovery_root / "R1").mkdir(parents=True)
    receipt = {"code": "R1", "reel_id": "instagram:R1", "identity_index": 0, "source_media_hash": H1, "result": {"source_media_hash": H1, "observation_state": "EMPTY_OUTPUT_UNVERIFIED"}}
    (recovery_root / "R1" / "transcription-recovery.json").write_text(json.dumps(receipt), encoding="utf-8")
    loaded_recovery = load_recovery_records([recovery_root], _canonical())
    assert len(loaded_recovery[0]["artifact_sha256"]) == 64


def test_loaders_reject_media_hash_mismatch_and_symlinked_ancestor(tmp_path):
    root = tmp_path / "acquisition"
    root.mkdir()
    media = tmp_path / "media"
    media.mkdir()
    (media / "R1.mp4").write_bytes(b"different")
    record = {"reel_id": "instagram:R1", "source_pointer": "media/R1.mp4", "sha256": H1, "observation_state": "OBSERVED"}
    (root / "R1.media.json").write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(RecoveryOverlayError, match="ACQUISITION_MEDIA_HASH_MISMATCH"):
        load_acquisition_records(root)
    indexed = {**record, "identity_index": 9}
    (root / "R1.media.json").write_text(json.dumps(indexed), encoding="utf-8")
    (media / "R1.mp4").write_bytes(bytes.fromhex("00"))
    with pytest.raises(RecoveryOverlayError, match="ACQUISITION_IDENTITY_INDEX_MISMATCH"):
        # The index check occurs before byte verification.
        from m2_orchestrator.recovery_overlay_report import normalize_acquisition_records
        normalize_acquisition_records([indexed], _canonical())
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(RecoveryOverlayError, match="ACQUISITION_ROOT_INVALID"):
        load_acquisition_records(link)


def test_embedded_acoustic_claim_never_grants_acoustic_review():
    attempted = _recovery()[0]
    attempted["result"] = {**attempted["result"], "acoustic_review_state": "APPROVED"}
    report = build_recovery_overlay(_canonical(), _primary(), _acquisition(), [attempted], source_snapshot_hash=SNAPSHOT, expected_population=3)
    recovery = report["rows"][0]["recovery"]
    assert recovery["acoustic_review_state"] == "NOT_REVIEWED"
    assert recovery["attempts"][0]["reported_acoustic_review_state"] == "APPROVED"
    assert recovery["analysis_ready"] is False
