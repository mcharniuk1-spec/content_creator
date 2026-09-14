import hashlib
import json
import threading
import time
import unittest
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from m2_orchestrator import server_supervisor as module
from m2_orchestrator.server_supervisor import WorkerSupervisor, canonical_manifest_hash


class Cursor:
    def __init__(self, db): self.db = db
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def execute(self, sql, params): self.db.calls.append((sql, params)); self.sql = sql
    def fetchone(self):
        if "worker_claim" in self.sql: return self.db.job
        if "worker_bundle" in self.sql: return self.db.bundle
        if "heartbeat" in self.sql: return self.db.next_heartbeat()
        if "register_output" in self.sql: return self.db.register
        return self.db.finish


class DB:
    def __init__(self, job, bundle, *, heartbeat=True, register=True, finish=True):
        self.job, self.bundle, self.register, self.finish = job, bundle, register, finish
        self.heartbeats = [heartbeat]
        self.calls, self.commits, self.closed = [], 0, False
    def cursor(self): return Cursor(self)
    def commit(self): self.commits += 1
    def close(self): self.closed = True
    def next_heartbeat(self): return self.heartbeats.pop(0) if self.heartbeats else True


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(root: Path, stage="render_fixture"):
    contents = {"source.json": b"source", "code.py": Path(module.__file__).read_bytes(), "config.json": b"config", "policy.json": b"policy", "input.mov": b"input"}
    for name, data in contents.items(): (root / name).write_bytes(data)
    manifest = {"release_id": "release-1", "stage": stage, "output_path": "output/result.bin"}
    for label, name in (("source_manifest", "source.json"), ("code", "code.py"), ("config", "config.json"), ("policy", "policy.json"), ("input", "input.mov")):
        manifest[f"{label}_path"] = name
        manifest[f"{label}_sha256"] = digest(root / name)
    if stage == "asr":
        (root / "model.bin").write_bytes(b"model")
        manifest["model_path"], manifest["model_sha256"] = "model.bin", digest(root / "model.bin")
    bundle_hash = canonical_manifest_hash(manifest)
    job = {"id": "job-1", "attempt": 1, "stage": stage, "input_sha256": bundle_hash, "lease_token": uuid.uuid4(), "payload": {"execution_bundle_sha256": bundle_hash, "release_id": "release-1"}}
    return job, manifest


def handler(_job, manifest, staging, cancelled):
    assert not cancelled.is_set()
    output = staging / manifest["output_path"]
    output.parent.mkdir()
    output.write_bytes((staging / "input.bin").read_bytes())
    return output


class Tests(unittest.TestCase):
    def supervisor(self, db, root, handlers=None, interval=0.01):
        return WorkerSupervisor(db, "m2_worker", handlers or {"render_fixture": handler}, root, lambda: DB(db.job, db.bundle, heartbeat=db.next_heartbeat()), interval)

    def test_registers_exact_output_receipt_before_done(self):
        with TemporaryDirectory() as temp:
            root = Path(temp); job, bundle = fixture(root); db = DB(job, bundle)
            result = self.supervisor(db, root).run_once()
            self.assertEqual(result["state"], "DONE")
            sqls = [sql for sql, _ in db.calls]
            self.assertLess(sqls.index(next(s for s in sqls if "register_output" in s)), sqls.index(next(s for s in sqls if "finish_job" in s)))
            receipt = next(params[2] for sql, params in db.calls if "register_output" in sql)
            parsed = json.loads(receipt)
            self.assertEqual(set(parsed), {"job_id", "attempt", "output_sha256", "byte_size", "kind", "private_path"})
            self.assertEqual(parsed["kind"], "fixture_bytes")
            self.assertGreaterEqual(db.commits, 2)
            self.assertEqual(next(params[1] for sql, params in db.calls if "register_output" in sql), str(job["lease_token"]))

    def test_periodic_independent_heartbeat_keeps_long_handler_alive(self):
        with TemporaryDirectory() as temp:
            root = Path(temp); job, bundle = fixture(root); db = DB(job, bundle)
            heartbeat_dbs = []
            def factory():
                item = DB(job, bundle, heartbeat=True); heartbeat_dbs.append(item); return item
            def slow_handler(_job, manifest, staging, cancelled):
                deadline = time.monotonic() + 0.06
                while time.monotonic() < deadline:
                    self.assertFalse(cancelled.is_set())
                    time.sleep(0.005)
                return handler(_job, manifest, staging, cancelled)
            result = WorkerSupervisor(db, "m2_worker", {"render_fixture": slow_handler}, root, factory, 0.01).run_once()
            self.assertEqual(result["state"], "DONE")
            self.assertGreaterEqual(len(heartbeat_dbs), 3)
            self.assertTrue(all(item.closed for item in heartbeat_dbs))

    def test_lease_loss_cancels_handler_and_never_marks_done(self):
        with TemporaryDirectory() as temp:
            root = Path(temp); job, bundle = fixture(root); db = DB(job, bundle)
            heartbeats = iter([True, False])
            def factory(): return DB(job, bundle, heartbeat=next(heartbeats))
            entered = threading.Event()
            def long_handler(_job, _manifest, _staging, cancelled):
                entered.set()
                self.assertTrue(cancelled.wait(0.5))
                raise RuntimeError("cancelled")
            result = WorkerSupervisor(db, "m2_worker", {"render_fixture": long_handler}, root, factory, 0.01).run_once()
            self.assertTrue(entered.is_set())
            self.assertEqual(result["state"], "LEASE_LOST")
            self.assertFalse(any("finish_job" in sql and params[2] == "done" for sql, params in db.calls))

    def test_actual_manifest_file_hash_mismatch_excludes_before_handler(self):
        with TemporaryDirectory() as temp:
            root = Path(temp); job, bundle = fixture(root); bundle["code_sha256"] = "0" * 64
            job["input_sha256"] = canonical_manifest_hash(bundle)
            job["payload"]["execution_bundle_sha256"] = job["input_sha256"]
            db = DB(job, bundle)
            result = self.supervisor(db, root).run_once()
            self.assertEqual(result["state"], "EXCLUDED")
            self.assertEqual(result["reason"], "ARTIFACT_BYTES_HASH_MISMATCH")

    def test_code_hash_must_bind_the_running_supervisor(self):
        with TemporaryDirectory() as temp:
            root = Path(temp); job, bundle = fixture(root)
            (root / "code.py").write_bytes(b"different valid local code")
            bundle["code_sha256"] = digest(root / "code.py")
            job["input_sha256"] = canonical_manifest_hash(bundle)
            job["payload"]["execution_bundle_sha256"] = job["input_sha256"]
            result = self.supervisor(DB(job, bundle), root).run_once()
            self.assertEqual(result["reason"], "EXECUTING_CODE_HASH_MISMATCH")

    def test_guard_starts_before_slow_local_hash_verification(self):
        with TemporaryDirectory() as temp:
            root = Path(temp); job, bundle = fixture(root); db = DB(job, bundle)
            guard_started = threading.Event()
            original = module._strict_manifest
            def factory():
                guard_started.set()
                return DB(job, bundle)
            def slow_strict(*args):
                self.assertTrue(guard_started.is_set())
                time.sleep(0.02)
                return original(*args)
            with mock.patch.object(module, "_strict_manifest", side_effect=slow_strict):
                result = WorkerSupervisor(db, "m2_worker", {"render_fixture": handler}, root, factory, 0.01).run_once()
            self.assertEqual(result["state"], "DONE")

    def test_asr_requires_existing_hashed_model_before_handler(self):
        with TemporaryDirectory() as temp:
            root = Path(temp); job, bundle = fixture(root, "asr"); (root / "model.bin").unlink()
            db = DB(job, bundle)
            result = WorkerSupervisor(db, "m2_worker", {"asr": handler}, root, lambda: DB(job, bundle), 0.01).run_once()
            self.assertEqual(result["state"], "EXCLUDED")
            self.assertEqual(result["reason"], "ASR_MODEL_MISSING")

    def test_asr_stages_authenticated_model_before_handler(self):
        with TemporaryDirectory() as temp:
            root = Path(temp); job, bundle = fixture(root, "asr"); db = DB(job, bundle)
            def asr_handler(_job, manifest, staging, _cancelled):
                self.assertEqual((staging / "model.bin").read_bytes(), b"model")
                output = staging / manifest["output_path"]
                output.parent.mkdir(); output.write_bytes(b"transcript")
                return output
            result = WorkerSupervisor(db, "m2_worker", {"asr": asr_handler}, root, lambda: DB(job, bundle), 0.01).run_once()
            self.assertEqual(result["state"], "DONE")

    def test_empty_output_is_excluded_before_receipt_registration(self):
        with TemporaryDirectory() as temp:
            root = Path(temp); job, bundle = fixture(root); db = DB(job, bundle)
            def empty_handler(_job, manifest, staging, _cancelled):
                output = staging / manifest["output_path"]
                output.parent.mkdir()
                output.write_bytes(b"")
                return output
            result = WorkerSupervisor(db, "m2_worker", {"render_fixture": empty_handler}, root, lambda: DB(job, bundle), 0.01).run_once()
            self.assertEqual(result["state"], "EXCLUDED")
            self.assertEqual(result["reason"], "LOCAL_OUTPUT_EMPTY")
            self.assertFalse(any("register_output" in sql for sql, _ in db.calls))

    def test_registration_rejection_prevents_done(self):
        with TemporaryDirectory() as temp:
            root = Path(temp); job, bundle = fixture(root); db = DB(job, bundle, register=False)
            result = self.supervisor(db, root).run_once()
            self.assertEqual(result["state"], "EXCLUDED")
            self.assertEqual(result["reason"], "OUTPUT_REGISTRATION_REJECTED")
            self.assertFalse(any("finish_job" in sql and params[2] == "done" for sql, params in db.calls))

    def test_failed_exclusion_wrapper_reports_lease_lost(self):
        with TemporaryDirectory() as temp:
            root = Path(temp); job, bundle = fixture(root); db = DB(job, bundle, finish=False)
            bundle["policy_sha256"] = "0" * 64
            job["input_sha256"] = canonical_manifest_hash(bundle)
            job["payload"]["execution_bundle_sha256"] = job["input_sha256"]
            result = self.supervisor(db, root).run_once()
            self.assertEqual(result["state"], "LEASE_LOST")


if __name__ == "__main__":
    unittest.main()
