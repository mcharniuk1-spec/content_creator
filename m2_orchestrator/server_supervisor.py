"""Fail-closed supervisor for the authenticated M2 local worker.

The database grants only the worker functions used below. This module never
collects, downloads a model, or writes directly to evidence tables. A bundle
must name and hash every local input it uses, and a job becomes ``done`` only
after its immutable output receipt has been registered for its claimed attempt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

LOCAL_STAGES = frozenset({"asr", "frames", "render_fixture"})
OUTPUT_KINDS = {"asr": "asr_json", "frames": "frame_image", "render_fixture": "fixture_bytes"}
HEX = re.compile(r"^[0-9a-f]{64}$")
SAFE_JOB_ID = re.compile(r"^[A-Za-z0-9_.-]{1,160}$")
COMMON_MANIFEST_FIELDS = frozenset({
    "release_id", "stage", "source_manifest_path", "source_manifest_sha256",
    "code_path", "code_sha256", "config_path", "config_sha256", "policy_path",
    "policy_sha256", "input_path", "input_sha256", "output_path",
})
STAGE_MANIFEST_FIELDS = {
    "asr": COMMON_MANIFEST_FIELDS | {"model_path", "model_sha256"},
    "frames": COMMON_MANIFEST_FIELDS,
    "render_fixture": COMMON_MANIFEST_FIELDS,
}


class SupervisorError(ValueError):
    """A short, safe code suitable for ``jobs.error_code``."""


def _hex(value: Any, label: str) -> str:
    if not isinstance(value, str) or not HEX.fullmatch(value):
        raise SupervisorError(f"INVALID_{label}")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError) as exc:
            raise SupervisorError(f"INVALID_{label}") from exc
    if not isinstance(value, Mapping):
        raise SupervisorError(f"INVALID_{label}")
    return value


def _scalar(value: Any) -> Any:
    if isinstance(value, Mapping) and len(value) == 1:
        return next(iter(value.values()))
    if isinstance(value, tuple) and len(value) == 1:
        return value[0]
    return value


def _lease_token(value: Any) -> str:
    """psycopg decodes PostgreSQL uuid columns as ``uuid.UUID`` objects."""
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, str) and value:
        return value
    raise SupervisorError("MISSING_LEASE_TOKEN")


def canonical_manifest_hash(manifest: Mapping[str, Any]) -> str:
    """Match migration 012's canonical JSON hash."""
    encoded = json.dumps(dict(manifest), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _rooted_path(root: Path, relative: Any, code: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise SupervisorError(code)
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise SupervisorError(code)
    return path


def verified_bytes(path: str, root: str | Path, expected_sha256: str) -> bytes:
    """Read an allowlisted regular file once and authenticate those bytes."""
    base = Path(root).resolve()
    candidate = _rooted_path(base, path, "ARTIFACT_PATH_OUTSIDE_ALLOWLIST")
    if not candidate.is_file() or candidate.is_symlink():
        raise SupervisorError("ARTIFACT_PATH_OUTSIDE_ALLOWLIST")
    try:
        data = candidate.read_bytes()
    except OSError as exc:
        raise SupervisorError("ARTIFACT_READ_FAILED") from exc
    if hashlib.sha256(data).hexdigest() != _hex(expected_sha256, "ARTIFACT_SHA256"):
        raise SupervisorError("ARTIFACT_BYTES_HASH_MISMATCH")
    return data


def _strict_manifest(manifest: Mapping[str, Any], stage: str, root: Path) -> bytes | None:
    required = STAGE_MANIFEST_FIELDS[stage]
    if set(manifest) != required or manifest.get("stage") != stage or not isinstance(manifest.get("release_id"), str) or not manifest["release_id"]:
        raise SupervisorError("BUNDLE_MANIFEST_SCHEMA_MISMATCH")
    if not isinstance(manifest["output_path"], str) or not manifest["output_path"]:
        raise SupervisorError("BUNDLE_MANIFEST_SCHEMA_MISMATCH")
    for label in ("source_manifest", "code", "config", "policy"):
        verified_bytes(manifest[f"{label}_path"], root, manifest[f"{label}_sha256"])
    executing_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if manifest["code_sha256"] != executing_hash:
        raise SupervisorError("EXECUTING_CODE_HASH_MISMATCH")
    if stage == "asr":
        model = _rooted_path(root, manifest["model_path"], "ASR_MODEL_PATH_INVALID")
        if not model.is_file() or model.is_symlink():
            raise SupervisorError("ASR_MODEL_MISSING")
        return verified_bytes(manifest["model_path"], root, manifest["model_sha256"])
    return None


def _terminate(process: subprocess.Popen[bytes]) -> None:
    try:
        process.terminate()
        process.wait(timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        try:
            process.kill()
        except OSError:
            pass


def _run_bounded(argv: list[str], timeout_seconds: int, cancelled: threading.Event) -> None:
    """Run a fixed argv process while responding promptly to lost leases."""
    try:
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError as exc:
        raise SupervisorError("LOCAL_EXECUTABLE_MISSING") from exc
    except OSError as exc:
        raise SupervisorError("LOCAL_SUBPROCESS_START_FAILED") from exc
    deadline = time.monotonic() + timeout_seconds
    while process.poll() is None:
        if cancelled.wait(0.1):
            _terminate(process)
            raise SupervisorError("STALE_LEASE_OR_AUTHORIZATION")
        if time.monotonic() >= deadline:
            _terminate(process)
            raise SupervisorError("LOCAL_SUBPROCESS_TIMEOUT")
    if process.returncode != 0:
        raise SupervisorError("LOCAL_SUBPROCESS_FAILED")


def local_handler(root: str | Path, job: Mapping[str, Any], manifest: Mapping[str, Any], staging: Path, cancelled: threading.Event) -> Path:
    """Execute a fixed local stage within the attempt's exclusive staging root."""
    stage = job["stage"]
    output = _rooted_path(staging, manifest["output_path"], "OUTPUT_PATH_OUTSIDE_ALLOWLIST")
    if output.exists() or output.is_symlink():
        raise SupervisorError("OUTPUT_OVERWRITE_FORBIDDEN")
    output.parent.mkdir(parents=True, exist_ok=True)
    staged_input = staging / "input.bin"
    if not staged_input.is_file():
        raise SupervisorError("INPUT_STAGING_MISSING")
    if stage == "render_fixture":
        try:
            shutil.copyfile(staged_input, output)
        except OSError as exc:
            raise SupervisorError("OUTPUT_WRITE_FAILED") from exc
    elif stage == "frames":
        _run_bounded(["ffmpeg", "-nostdin", "-v", "error", "-i", str(staged_input), "-frames:v", "1", str(output)], 120, cancelled)
    elif stage == "asr":
        # Only an existing checkpoint path is admitted; no model name is accepted.
        model = staging / "model.bin"
        if not model.is_file() or model.is_symlink():
            raise SupervisorError("ASR_MODEL_STAGING_MISSING")
        program = (
            "import sys, whisper; model=whisper.load_model(sys.argv[1], download_root=sys.argv[2]); "
            "result=model.transcribe(sys.argv[3]); open(sys.argv[4], 'w', encoding='utf-8').write(__import__('json').dumps(result, sort_keys=True))"
        )
        _run_bounded([sys.executable, "-c", program, str(model), str(model.parent), str(staged_input), str(output)], 1800, cancelled)
    else:
        raise SupervisorError("LOCAL_STAGE_EXECUTOR_UNCONFIGURED")
    if not output.is_file() or output.is_symlink():
        raise SupervisorError("LOCAL_OUTPUT_MISSING")
    return output


class _LeaseGuard:
    def __init__(self, factory: Callable[[], Any], job_id: str, token: str, seconds: int, interval: float):
        self.factory, self.job_id, self.token, self.seconds, self.interval = factory, job_id, token, seconds, interval
        self.cancelled = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _heartbeat(self) -> bool:
        connection = None
        try:
            connection = self.factory()
            with connection.cursor() as cursor:
                cursor.execute("SELECT m2_shared.worker_heartbeat_job(%s,%s,%s)", (self.job_id, self.token, self.seconds))
                value = cursor.fetchone()
            if hasattr(connection, "commit"):
                connection.commit()
            return _scalar(value) is True
        except Exception:
            return False
        finally:
            close = getattr(connection, "close", None)
            if callable(close):
                close()

    def start(self) -> None:
        if not self._heartbeat():
            self.cancelled.set()
            return
        self._thread = threading.Thread(target=self._run, name="m2-worker-lease-guard", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            if not self._heartbeat():
                self.cancelled.set()
                return

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self.interval * 2))


class WorkerSupervisor:
    """Claim one job and complete it only through immutable worker functions."""

    def __init__(self, connection: Any, worker_id: str, handlers: Mapping[str, Callable[[Mapping[str, Any], Mapping[str, Any], Path, threading.Event], Path]], artifact_root: str | Path, heartbeat_connection_factory: Callable[[], Any], heartbeat_interval: float | None = None):
        if not isinstance(worker_id, str) or not re.fullmatch(r"[a-z0-9_-]{1,80}", worker_id):
            raise SupervisorError("INVALID_WORKER_ID")
        if set(handlers) - LOCAL_STAGES:
            raise SupervisorError("UNSUPPORTED_HANDLER")
        self.connection, self.worker_id, self.handlers = connection, worker_id, handlers
        self.artifact_root = Path(artifact_root).resolve()
        if not self.artifact_root.is_dir():
            raise SupervisorError("ARTIFACT_ROOT_MISSING")
        self.heartbeat_connection_factory = heartbeat_connection_factory
        self.heartbeat_interval = heartbeat_interval

    def _one(self, sql: str, params: tuple[Any, ...]) -> Any:
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    def _finish_excluded(self, job: Mapping[str, Any], code: str) -> dict[str, Any]:
        finished = self._one("SELECT m2_shared.worker_finish_job(%s,%s,%s,%s,%s)", (job["id"], _lease_token(job.get("lease_token")), "excluded", None, code))
        self.connection.commit()
        if _scalar(finished) is not True:
            return {"state": "LEASE_LOST", "job_id": job.get("id"), "reason": "STALE_LEASE_OR_AUTHORIZATION"}
        return {"state": "EXCLUDED", "job_id": job.get("id"), "reason": code}

    def _staging(self, job: Mapping[str, Any], input_bytes: bytes, model_bytes: bytes | None) -> Path:
        job_id, attempt = job["id"], job["attempt"]
        if not isinstance(job_id, str) or not SAFE_JOB_ID.fullmatch(job_id) or not isinstance(attempt, int) or isinstance(attempt, bool) or not 1 <= attempt <= 3:
            raise SupervisorError("INVALID_JOB_ATTEMPT")
        private = self.artifact_root / ".m2-worker-private" / hashlib.sha256(job_id.encode()).hexdigest() / str(attempt)
        try:
            private.mkdir(parents=True, exist_ok=False)
            (private / "input.bin").write_bytes(input_bytes)
            if model_bytes is not None:
                (private / "model.bin").write_bytes(model_bytes)
        except FileExistsError as exc:
            raise SupervisorError("PRIVATE_STAGING_EXISTS") from exc
        except OSError as exc:
            raise SupervisorError("PRIVATE_STAGING_FAILED") from exc
        return private

    def _register_output(self, job: Mapping[str, Any], output: Path) -> str:
        root = self.artifact_root
        if not output.is_file() or output.is_symlink() or not output.resolve().is_relative_to(root):
            raise SupervisorError("LOCAL_OUTPUT_MISSING")
        data = output.read_bytes()
        if not data:
            raise SupervisorError("LOCAL_OUTPUT_EMPTY")
        digest = hashlib.sha256(data).hexdigest()
        receipt = {
            "attempt": job["attempt"], "byte_size": len(data), "job_id": job["id"],
            "kind": OUTPUT_KINDS[job["stage"]], "output_sha256": digest,
            "private_path": output.resolve().relative_to(root).as_posix(),
        }
        canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        registered = self._one("SELECT m2_shared.worker_register_output(%s,%s,%s)", (job["id"], _lease_token(job["lease_token"]), canonical))
        if _scalar(registered) is not True:
            raise SupervisorError("OUTPUT_REGISTRATION_REJECTED")
        return digest

    def run_once(self, lease_seconds: int = 300) -> dict[str, Any]:
        job = self._one("SELECT * FROM m2_shared.worker_claim_job(%s,%s)", (self.worker_id, lease_seconds))
        if not job:
            return {"state": "IDLE"}
        job = _mapping(job, "JOB")
        self.connection.commit()  # durable claim before local bytes or an executable are touched
        guard: _LeaseGuard | None = None
        try:
            stage = job.get("stage")
            if stage not in LOCAL_STAGES or stage not in self.handlers:
                raise SupervisorError("LOCAL_STAGE_EXECUTOR_UNCONFIGURED")
            token = _lease_token(job.get("lease_token"))
            input_hash = _hex(job.get("input_sha256"), "INPUT_SHA256")
            payload = _mapping(job.get("payload"), "JOB_PAYLOAD")
            if payload.get("execution_bundle_sha256") != input_hash or not isinstance(payload.get("release_id"), str) or not payload["release_id"]:
                raise SupervisorError("JOB_BUNDLE_BINDING_MISMATCH")
            raw_manifest = self._one("SELECT m2_shared.worker_bundle(%s)", (input_hash,))
            if isinstance(raw_manifest, Mapping) and set(raw_manifest) == {"worker_bundle"}:
                raw_manifest = raw_manifest["worker_bundle"]
            manifest = _mapping(raw_manifest, "BUNDLE_MANIFEST")
            if canonical_manifest_hash(manifest) != input_hash or manifest.get("release_id") != payload["release_id"]:
                raise SupervisorError("BUNDLE_MANIFEST_MISMATCH")
            interval = self.heartbeat_interval if self.heartbeat_interval is not None else max(1.0, lease_seconds / 3)
            guard = _LeaseGuard(self.heartbeat_connection_factory, job["id"], token, lease_seconds, interval)
            guard.start()
            try:
                if guard.cancelled.is_set():
                    return {"state": "LEASE_LOST", "job_id": job["id"], "reason": "STALE_LEASE_OR_AUTHORIZATION"}
                model_bytes = _strict_manifest(manifest, stage, self.artifact_root)
                input_bytes = verified_bytes(manifest["input_path"], self.artifact_root, manifest["input_sha256"])
                staging = self._staging(job, input_bytes, model_bytes)
                output = self.handlers[stage](job, manifest, staging, guard.cancelled)
            finally:
                guard.close()
            if guard.cancelled.is_set():
                return {"state": "LEASE_LOST", "job_id": job["id"], "reason": "STALE_LEASE_OR_AUTHORIZATION"}
            if not isinstance(output, Path):
                raise SupervisorError("LOCAL_HANDLER_CONTRACT_INVALID")
            output_hash = self._register_output(job, output)
            finished = self._one("SELECT m2_shared.worker_finish_job(%s,%s,%s,%s,%s)", (job["id"], token, "done", output_hash, None))
            if _scalar(finished) is not True:
                raise SupervisorError("STALE_LEASE_OR_AUTHORIZATION")
            self.connection.commit()
            return {"state": "DONE", "job_id": job["id"], "stage": stage, "output_sha256": output_hash}
        except SupervisorError as exc:
            if guard is not None and guard.cancelled.is_set() and str(exc) == "STALE_LEASE_OR_AUTHORIZATION":
                return {"state": "LEASE_LOST", "job_id": job["id"], "reason": "STALE_LEASE_OR_AUTHORIZATION"}
            return self._finish_excluded(job, str(exc))
        except Exception:
            if guard is not None and guard.cancelled.is_set():
                return {"state": "LEASE_LOST", "job_id": job["id"], "reason": "STALE_LEASE_OR_AUTHORIZATION"}
            return self._finish_excluded(job, "LOCAL_HANDLER_FAILED")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--worker-id", default=os.environ.get("M2_WORKER_ID"))
    parser.add_argument("--artifact-root", default=os.environ.get("M2_ARTIFACT_ROOT"))
    args = parser.parse_args(argv)
    if not args.once or not args.worker_id or not args.artifact_root:
        raise SupervisorError("WORKER_CONFIGURATION_REQUIRED")
    import psycopg
    from psycopg.rows import dict_row
    dsn = os.environ["M2_DATABASE_DSN"]
    def heartbeat_connection() -> Any:
        connection = psycopg.connect(dsn, autocommit=False, row_factory=dict_row)
        connection.execute("SET ROLE m2_worker")
        connection.commit()
        return connection
    with psycopg.connect(dsn, autocommit=False, row_factory=dict_row) as connection:
        connection.execute("SET ROLE m2_worker")
        connection.commit()
        supervisor = WorkerSupervisor(connection, args.worker_id, {
            stage: (lambda job, manifest, staging, cancelled, stage=stage: local_handler(args.artifact_root, job, manifest, staging, cancelled))
            for stage in LOCAL_STAGES
        }, args.artifact_root, heartbeat_connection)
        print(json.dumps(supervisor.run_once()))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SupervisorError:
        print(json.dumps({"state": "FAIL", "reason": "WORKER_FAILED"}), file=sys.stderr)
        raise SystemExit(2)
