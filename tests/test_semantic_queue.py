from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from m2_orchestrator.semantic_queue import SemanticQueue, SemanticQueueError, file_sha256


def _artifact(root: Path, relative: str, payload: bytes) -> dict[str, str]:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {relative: file_sha256(path)}


@pytest.fixture
def fixture_ledger(tmp_path: Path):
    root = tmp_path / "corpus"
    root.mkdir()
    corpus_db = root / "corpus-media.sqlite"
    context = tmp_path / "positioning.md"
    taxonomy = tmp_path / "taxonomy.md"
    context.write_text("founder positioning context\n")
    taxonomy.write_text("scene taxonomy context\n")
    columns = "reel_id TEXT PRIMARY KEY, code TEXT, identity_index INTEGER, acquisition_state TEXT, transcript_state TEXT, frames_state TEXT, scene_review_state TEXT, acquisition_artifact TEXT, transcript_artifact TEXT, frames_artifact TEXT"
    rows = []
    for index in range(10):
        reel_id = f"instagram:CODE{index}"
        media = _artifact(root, f"media/CODE{index}.mp4", f"media-{index}".encode())
        transcript = _artifact(root, f"transcripts/CODE{index}/transcription.json", json.dumps({"segments": [{"text": "untrusted hello", "start_ms": 0, "end_ms": 1000}]}).encode())
        frames = _artifact(root, f"frames/CODE{index}/F001.jpg", f"frame-{index}".encode())
        rows.append((reel_id, f"CODE{index}", index, "OBSERVED", "OBSERVED", "OBSERVED", "REVIEW_PENDING", json.dumps(media), json.dumps(transcript), json.dumps(frames)))
    # A blocked identity is part of the denominator and has two NOT_READY jobs.
    rows.append(("instagram:BLOCKED", "BLOCKED", 10, "UNAVAILABLE", "NOT_ATTEMPTED", "NOT_ATTEMPTED", "NOT_ATTEMPTED", None, None, None))
    with sqlite3.connect(corpus_db) as db:
        db.execute("CREATE TABLE binding (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.executemany("INSERT INTO binding VALUES (?,?)", [("config_sha256", "c" * 64), ("manifest_sha256", "m" * 64)])
        db.execute(f"CREATE TABLE reels ({columns})")
        db.executemany("INSERT INTO reels VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
        db.commit()
    return {"root": root, "db": corpus_db, "context": context, "taxonomy": taxonomy, "rows": rows, "tmp": tmp_path}


def _queue(fixture_ledger, **kwargs) -> SemanticQueue:
    return SemanticQueue(
        fixture_ledger["tmp"] / "semantic.sqlite",
        fixture_ledger["db"],
        corpus_root=fixture_ledger["root"],
        context_paths=[fixture_ledger["context"], fixture_ledger["taxonomy"]],
        output_root=fixture_ledger["tmp"] / "semantic-output",
        **kwargs,
    )


def _maker_payload(job: dict) -> dict:
    binding = json.loads(job["input_binding_json"])
    source_hashes = {}
    for group in ("media", "transcript", "frames"):
        for path, digest in binding["artifacts"][group].items():
            source_hashes[f"{group}:{path}"] = digest
    for path, digest in binding["artifacts"]["context"].items():
        source_hashes[f"context:{path}"] = digest
    return {
        "schema": "m2.semantic-maker-output.v1",
        "job_key": job["job_key"],
        "input_sha256": job["input_hash"],
        "source_hashes": dict(sorted(source_hashes.items())),
        "evidence_pointers": ["transcripts/CODE0/transcription.json", "T00001"],
        "state": "PENDING_REVIEW",
        "uncertainty": [],
    }


def _review_receipt(job: dict, output_hash: str, reviewer: str = "reviewer-1", model: str = "luna-high", verdict: str = "ACCEPTED") -> dict:
    return {"schema": "m2.semantic-review-receipt.v1", "job_key": job["job_key"], "input_sha256": job["input_hash"], "maker_output_sha256": output_hash, "reviewer_actor": reviewer, "reviewer_model": model, "scope": ["schema and source bindings"], "verdict": verdict, "limitations": ["fixture review only"]}


def test_refresh_is_idempotent_and_registers_full_population(fixture_ledger):
    with _queue(fixture_ledger) as queue:
        first = queue.refresh()
        second = queue.refresh()
        assert first["population"] == second["population"] == 11
        assert queue.db.execute("SELECT COUNT(*) FROM identities").fetchone()[0] == 11
        assert queue.db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 22
        assert queue.db.execute("SELECT COUNT(*) FROM jobs WHERE state='READY'").fetchone()[0] == 20
        assert queue.db.execute("SELECT COUNT(*) FROM jobs WHERE state='NOT_READY'").fetchone()[0] == 2
        assert queue.db.execute("SELECT disposition FROM identities WHERE code='BLOCKED'").fetchone()[0] == "BLOCKED"
        assert queue.summary()["corpus_population_count"] == 11
        assert queue.summary()["corpus_binding"] == {"config_sha256": "c" * 64, "manifest_sha256": "m" * 64}
        assert queue.db.execute("SELECT COUNT(*) FROM events WHERE event='job_created'").fetchone()[0] == 22


def test_unrelated_reel_progress_does_not_invalidate_claim(fixture_ledger):
    with _queue(fixture_ledger) as queue:
        queue.refresh()
        old = next(j for j in queue.jobs() if j['code']=='CODE0' and j['kind']=='transcript_structure')
        population = queue.summary()['corpus_population_hash']
        with sqlite3.connect(fixture_ledger['db']) as db:
            db.execute("UPDATE reels SET transcript_state='SUSPICIOUS_TIMINGS' WHERE code='CODE1'")
        queue.refresh()
        assert queue.summary()['corpus_population_hash']==population
        same = [j for j in queue.jobs() if j['code']=='CODE0' and j['kind']=='transcript_structure']
        assert len(same)==1 and same[0]['job_key']==old['job_key']
        assert queue.claim(old['job_key'],actor='maker',model='luna-high')['state']=='CLAIMED'


def test_membership_change_invalidates_existing_job(fixture_ledger):
    with _queue(fixture_ledger) as queue:
        queue.refresh()
        old = next(j for j in queue.jobs() if j['code']=='CODE0' and j['kind']=='transcript_structure')
        population = queue.summary()['corpus_population_hash']
        with sqlite3.connect(fixture_ledger['db']) as db:
            db.execute("UPDATE reels SET identity_index=99 WHERE code='CODE1'")
        queue.refresh()
        assert queue.summary()['corpus_population_hash']!=population
        with pytest.raises(SemanticQueueError):queue.claim(old['job_key'],actor='maker',model='luna-high')


def test_export_batch_limits_distinct_reels_and_excludes_raw_speech(fixture_ledger):
    with _queue(fixture_ledger) as queue:
        queue.refresh()
        exported = queue.export_batch(limit=8)
        assert len(exported) == 16  # two task kinds for eight Reels
        assert len({item["reel_id"] for item in exported}) == 8
        for item in exported:
            contract_path = Path(item["path"])
            contract = json.loads(contract_path.read_text())
            assert contract["job_key"] == item["job_key"]
            assert "untrusted hello" not in json.dumps(contract)
            assert str(fixture_ledger["tmp"]) not in contract_path.read_text()
            assert contract["review"]["maker_reviewer_separation"] is True
            assert contract["executor"]["maker_model"] == "luna-high"
            assert [item["id"] for item in contract["context_sources"]] == ["context-01", "context-02"]
            assert contract["corpus_population_count"] == 11
            assert contract["corpus_binding"] == {"config_sha256": "c" * 64, "manifest_sha256": "m" * 64}


def test_source_change_creates_new_job_and_preserves_old(fixture_ledger):
    with _queue(fixture_ledger) as queue:
        queue.refresh()
        old = next(job for job in queue.jobs() if job["code"] == "CODE0" and job["kind"] == "transcript_structure")
        transcript_path = fixture_ledger["root"] / "transcripts/CODE0/transcription.json"
        transcript_path.write_text(json.dumps({"segments": [{"text": "changed untrusted text", "start_ms": 0, "end_ms": 1200}]}))
        updated = {"transcripts/CODE0/transcription.json": file_sha256(transcript_path)}
        with sqlite3.connect(fixture_ledger["db"]) as db:
            db.execute("UPDATE reels SET transcript_artifact=? WHERE code='CODE0'", (json.dumps(updated),))
            db.commit()
        queue.refresh()
        current = [job for job in queue.jobs() if job["code"] == "CODE0" and job["kind"] == "transcript_structure"]
        assert len(current) == 2
        assert old["job_key"] in {job["job_key"] for job in current}
        assert len({job["input_hash"] for job in current}) == 2
        assert next(job for job in current if job["job_key"] == old["job_key"])["state"] == "SUPERSEDED"
        exported = queue.export_batch(limit=8, kinds=("transcript_structure",))
        assert old["job_key"] not in {item["job_key"] for item in exported}
        with pytest.raises(SemanticQueueError, match="JOB_NOT_READY_TO_CLAIM"):
            queue.claim(old["job_key"], actor="maker-old", model="luna-high")


def test_missing_or_hash_mismatched_artifact_is_not_ready(fixture_ledger):
    with _queue(fixture_ledger) as queue:
        queue.refresh()
        media = fixture_ledger["root"] / "media/CODE1.mp4"
        media.write_bytes(b"tampered")
        queue.refresh()
        jobs = [job for job in queue.jobs() if job["code"] == "CODE1"]
        # The prior hash-bound READY jobs remain immutable history; the new
        # source binding is admitted as NOT_READY rather than mutating history.
        assert {job["state"] for job in jobs} == {"SUPERSEDED", "NOT_READY"}
        assert any(not json.loads(job["input_binding_json"])["artifacts"]["media"] for job in jobs if job["state"] == "NOT_READY")
        assert queue.db.execute("SELECT disposition FROM identities WHERE code='CODE1'").fetchone()[0] == "NOT_READY"


def test_maker_review_requires_exact_bindings_and_separate_actor(fixture_ledger):
    with _queue(fixture_ledger) as queue:
        queue.refresh()
        job = next(job for job in queue.jobs() if job["code"] == "CODE0" and job["kind"] == "transcript_structure")
        queue.claim(job["job_key"], actor="maker-1", model="luna-high")
        output = fixture_ledger["tmp"] / "semantic-output" / "maker.json"
        output.parent.mkdir()
        output.write_text(json.dumps(_maker_payload(job)))
        with pytest.raises(SemanticQueueError, match="JOB_INPUT_CHANGED"):
            queue.submit_maker(job["job_key"], actor="maker-1", output_path=output, output_sha256=file_sha256(output), input_sha256="0" * 64)
        output_hash = file_sha256(output)
        queue.submit_maker(job["job_key"], actor="maker-1", output_path=output, output_sha256=output_hash, input_sha256=job["input_hash"])
        queue.request_review(job["job_key"], actor="coordinator")
        with pytest.raises(SemanticQueueError, match="SELF_REVIEW_FORBIDDEN"):
            receipt = fixture_ledger["tmp"] / "semantic-output" / "reviews" / "self.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_text(json.dumps(_review_receipt(job, output_hash, reviewer="maker-1")))
            queue.submit_review(job["job_key"], reviewer="maker-1", model="luna-high", verdict="ACCEPTED", maker_output_sha256=output_hash, review_receipt_path=receipt, review_receipt_sha256=file_sha256(receipt))
        with pytest.raises(SemanticQueueError, match="MAKER_OUTPUT_CHANGED"):
            receipt = fixture_ledger["tmp"] / "semantic-output" / "reviews" / "bad-output.json"
            receipt.write_text(json.dumps(_review_receipt(job, "1" * 64)))
            queue.submit_review(job["job_key"], reviewer="reviewer-1", model="luna-high", verdict="ACCEPTED", maker_output_sha256="1" * 64, review_receipt_path=receipt, review_receipt_sha256=file_sha256(receipt))
        receipt = fixture_ledger["tmp"] / "semantic-output" / "reviews" / "valid.json"
        receipt.write_text(json.dumps(_review_receipt(job, output_hash)))
        accepted = queue.submit_review(job["job_key"], reviewer="reviewer-1", model="luna-high", verdict="ACCEPTED", maker_output_sha256=output_hash, review_receipt_path=receipt, review_receipt_sha256=file_sha256(receipt))
        assert accepted["state"] == "ACCEPTED"
        assert queue.db.execute("SELECT COUNT(*) FROM attempts WHERE job_key=?", (job["job_key"],)).fetchone()[0] == 3
        assert queue.db.execute("SELECT COUNT(*) FROM events WHERE job_key=? AND event='review_submitted'", (job["job_key"],)).fetchone()[0] == 1


def test_maker_payload_is_strict_and_source_bound(fixture_ledger):
    with _queue(fixture_ledger) as queue:
        queue.refresh()
        job = next(job for job in queue.jobs() if job["code"] == "CODE0" and job["kind"] == "transcript_structure")
        queue.claim(job["job_key"], actor="maker-1", model="luna-high")
        output = fixture_ledger["tmp"] / "semantic-output" / "payload.json"
        output.parent.mkdir(parents=True)
        cases = [b"", b"not-json", json.dumps({"job_key": job["job_key"]}).encode()]
        for index, payload in enumerate(cases):
            path = output.with_name(f"bad-{index}.json")
            path.write_bytes(payload)
            with pytest.raises(SemanticQueueError):
                queue.submit_maker(job["job_key"], actor="maker-1", output_path=path, output_sha256=file_sha256(path), input_sha256=job["input_hash"])
        bad = _maker_payload(job)
        bad["job_key"] = "sjq-" + "0" * 64
        output.write_text(json.dumps(bad))
        with pytest.raises(SemanticQueueError, match="MAKER_PAYLOAD_BINDING_INVALID"):
            queue.submit_maker(job["job_key"], actor="maker-1", output_path=output, output_sha256=file_sha256(output), input_sha256=job["input_hash"])
        bad = _maker_payload(job)
        bad["evidence_pointers"] = ["../../outside"]
        output.write_text(json.dumps(bad))
        with pytest.raises(SemanticQueueError, match="MAKER_PAYLOAD_EVIDENCE_INVALID"):
            queue.submit_maker(job["job_key"], actor="maker-1", output_path=output, output_sha256=file_sha256(output), input_sha256=job["input_hash"])


def test_maker_rejects_source_changed_after_claim(fixture_ledger):
    with _queue(fixture_ledger) as queue:
        queue.refresh()
        job = next(job for job in queue.jobs() if job["code"] == "CODE0" and job["kind"] == "transcript_structure")
        queue.claim(job["job_key"], actor="maker-1", model="luna-high")
        transcript = fixture_ledger["root"] / "transcripts/CODE0/transcription.json"
        transcript.write_text("{\"changed\":true}")
        output = fixture_ledger["tmp"] / "semantic-output" / "changed-source.json"
        output.parent.mkdir(parents=True)
        output.write_text(json.dumps(_maker_payload(job)))
        with pytest.raises(SemanticQueueError, match="SOURCE_ARTIFACT_CHANGED"):
            queue.submit_maker(job["job_key"], actor="maker-1", output_path=output, output_sha256=file_sha256(output), input_sha256=job["input_hash"])


def test_maker_rejects_context_changed_after_claim(fixture_ledger):
    with _queue(fixture_ledger) as queue:
        queue.refresh()
        job = next(job for job in queue.jobs() if job["code"] == "CODE0" and job["kind"] == "transcript_structure")
        queue.claim(job["job_key"], actor="maker-1", model="luna-high")
        fixture_ledger["context"].write_text("changed positioning context\n")
        output = fixture_ledger["tmp"] / "semantic-output" / "changed-context.json"
        output.parent.mkdir(parents=True)
        output.write_text(json.dumps(_maker_payload(job)))
        with pytest.raises(SemanticQueueError, match="CONTEXT_ARTIFACT_CHANGED"):
            queue.submit_maker(job["job_key"], actor="maker-1", output_path=output, output_sha256=file_sha256(output), input_sha256=job["input_hash"])


def test_claim_lease_heartbeat_and_crash_recovery(fixture_ledger):
    with _queue(fixture_ledger, claim_lease_seconds=1) as queue:
        queue.refresh()
        job = next(job for job in queue.jobs() if job["code"] == "CODE0" and job["kind"] == "transcript_structure")
        queue.claim(job["job_key"], actor="maker-1", model="luna-high")
        expires = queue.heartbeat(job["job_key"], actor="maker-1", extend_seconds=2)
        assert expires > 0
        with pytest.raises(SemanticQueueError, match="CLAIM_LEASE_EXPIRED"):
            queue.heartbeat(job["job_key"], actor="other", extend_seconds=1)
        queue.db.execute("UPDATE jobs SET lease_expires_at=0 WHERE job_key=?", (job["job_key"],))
        queue.db.commit()
        queue.close()  # Simulate a crashed worker; the next opener recovers it.
        with _queue(fixture_ledger, claim_lease_seconds=1) as recovered:
            assert recovered.db.execute("SELECT state FROM jobs WHERE job_key=?", (job["job_key"],)).fetchone()[0] == "READY"
            assert recovered.db.execute("SELECT state FROM attempts WHERE job_key=? ORDER BY id DESC LIMIT 1", (job["job_key"],)).fetchone()[0] == "LEASE_EXPIRED"
            recovered.claim(job["job_key"], actor="maker-2", model="luna-high")


def test_review_receipt_fields_are_required(fixture_ledger):
    with _queue(fixture_ledger) as queue:
        queue.refresh()
        job = next(job for job in queue.jobs() if job["code"] == "CODE0" and job["kind"] == "transcript_structure")
        queue.claim(job["job_key"], actor="maker-1", model="luna-high")
        output = fixture_ledger["tmp"] / "semantic-output" / "review-payload.json"
        output.parent.mkdir(parents=True)
        output.write_text(json.dumps(_maker_payload(job)))
        output_hash = file_sha256(output)
        queue.submit_maker(job["job_key"], actor="maker-1", output_path=output, output_sha256=output_hash, input_sha256=job["input_hash"])
        queue.request_review(job["job_key"], actor="coordinator")
        receipt = fixture_ledger["tmp"] / "semantic-output" / "reviews" / "invalid.json"
        receipt.parent.mkdir(parents=True)
        receipt.write_text(json.dumps({"job_key": job["job_key"], "verdict": "ACCEPTED"}))
        with pytest.raises(SemanticQueueError, match="REVIEW_RECEIPT_FIELDS_MISSING"):
            queue.submit_review(job["job_key"], reviewer="reviewer-1", model="luna-high", verdict="ACCEPTED", maker_output_sha256=output_hash, review_receipt_path=receipt, review_receipt_sha256=file_sha256(receipt))


def test_lock_and_output_collision_guards(fixture_ledger):
    first = _queue(fixture_ledger)
    second = _queue(fixture_ledger)
    first.open()
    try:
        with pytest.raises(SemanticQueueError, match="QUEUE_ALREADY_RUNNING"):
            second.open()
    finally:
        first.close()


def test_output_path_is_unique_across_jobs(fixture_ledger):
    with _queue(fixture_ledger) as queue:
        queue.refresh()
        jobs = [job for job in queue.jobs() if job["code"] == "CODE0" and job["kind"] in {"transcript_structure", "scene_candidates"}]
        output = fixture_ledger["tmp"] / "semantic-output" / "shared.json"
        output.parent.mkdir(parents=True)
        output.write_text(json.dumps(_maker_payload(jobs[0])))
        output_hash = file_sha256(output)
        queue.claim(jobs[0]["job_key"], actor="maker-a", model="luna-high")
        queue.submit_maker(jobs[0]["job_key"], actor="maker-a", output_path=output, output_sha256=output_hash, input_sha256=jobs[0]["input_hash"])
        queue.claim(jobs[1]["job_key"], actor="maker-b", model="luna-high")
        output.write_text(json.dumps(_maker_payload(jobs[1])))
        with pytest.raises(SemanticQueueError, match="MAKER_OUTPUT_PATH_REUSED"):
            queue.submit_maker(jobs[1]["job_key"], actor="maker-b", output_path=output, output_sha256=file_sha256(output), input_sha256=jobs[1]["input_hash"])


def test_approved_path_guards_reject_symlinked_ancestors(fixture_ledger):
    linked_parent = fixture_ledger["tmp"] / "linked-parent"
    real_parent = fixture_ledger["tmp"] / "real-parent"
    real_parent.mkdir()
    linked_parent.symlink_to(real_parent, target_is_directory=True)
    with pytest.raises(SemanticQueueError, match="SYMLINKED_PATH_ANCESTOR"):
        SemanticQueue(linked_parent / "queue.sqlite", fixture_ledger["db"], corpus_root=fixture_ledger["root"], context_paths=[fixture_ledger["context"], fixture_ledger["taxonomy"]])

    linked_output = fixture_ledger["tmp"] / "linked-output"
    real_output = fixture_ledger["tmp"] / "real-output"
    real_output.mkdir()
    linked_output.symlink_to(real_output, target_is_directory=True)
    with pytest.raises(SemanticQueueError, match="SYMLINKED_PATH_ANCESTOR"):
        SemanticQueue(fixture_ledger["tmp"] / "other.sqlite", fixture_ledger["db"], corpus_root=fixture_ledger["root"], context_paths=[fixture_ledger["context"], fixture_ledger["taxonomy"]], output_root=linked_output)

    linked_context = fixture_ledger["tmp"] / "linked-context"
    real_context = fixture_ledger["tmp"] / "real-context"
    real_context.mkdir()
    (real_context / "positioning.md").write_text("positioning\n")
    linked_context.symlink_to(real_context, target_is_directory=True)
    with pytest.raises(SemanticQueueError, match="SYMLINKED_PATH_ANCESTOR"):
        SemanticQueue(fixture_ledger["tmp"] / "context.sqlite", fixture_ledger["db"], corpus_root=fixture_ledger["root"], context_paths=[linked_context / "positioning.md", fixture_ledger["taxonomy"]])

    queue = _queue(fixture_ledger)
    lock_target = fixture_ledger["tmp"] / "lock-target"
    lock_target.write_text("")
    lock_path = fixture_ledger["tmp"] / "semantic.sqlite.lock"
    lock_path.symlink_to(lock_target)
    with pytest.raises(SemanticQueueError, match="SYMLINKED_PATH_ANCESTOR"):
        queue.open()
