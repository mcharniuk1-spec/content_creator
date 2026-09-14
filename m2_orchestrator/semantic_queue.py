"""Hash-bound, resumable admission queue for bounded M2 semantic tasks.

This module only reads the corpus ledger and verifies already-produced local
artifacts. It never runs a model, decodes media, calls a provider, or writes
the corpus ledger. Queue state is kept in a separate SQLite database.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable, Mapping


MAX_EXPORT_REELS = 8
CONTRACT_VERSION = "m2.semantic-task-contract.v2"
CLAIM_LEASE_SECONDS = 900
MAX_CLAIM_LEASE_SECONDS = 3600
JOB_KINDS = ("transcript_structure", "scene_candidates")
STATES = ("READY", "CLAIMED", "MAKER_DONE", "REVIEW_REQUIRED", "ACCEPTED", "REJECTED", "NOT_READY", "SUPERSEDED")
READY_TRANSCRIPT_STATES = {"OBSERVED", "SUSPICIOUS_TIMINGS"}
READY_FRAME_STATES = {"OBSERVED", "PARTIAL"}
BLOCKED_ACQUISITION_STATES = {"UNAVAILABLE", "BLOCKED", "QUARANTINED", "ACQUISITION_FAILED", "STORAGE_BUDGET_STOP"}
_HEX64 = set("0123456789abcdef")


class SemanticQueueError(ValueError):
    pass


def stable_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX64


def _safe_error(value: Any) -> str:
    return str(value).replace("\n", " ")[:512]


def _default_context_paths() -> tuple[Path, ...]:
    root = Path(__file__).resolve().parents[1]
    return (root / "knowledge" / "m2-positioning.md", root / "knowledge" / "studio" / "classification-taxonomy.md")


def _read_context(paths: Iterable[Path]) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in paths:
        path = Path(raw).absolute()
        if _has_symlink_ancestor(path) or path.is_symlink():
            raise SemanticQueueError("SYMLINKED_PATH_ANCESTOR")
        if not path.is_file():
            raise SemanticQueueError("CONTEXT_FILE_UNAVAILABLE")
        result[str(path)] = file_sha256(path)
    if not result:
        raise SemanticQueueError("CONTEXT_REQUIRED")
    return result


def _has_symlink_ancestor(path: Path) -> bool:
    current = Path(path).absolute()
    while True:
        if current.is_symlink():
            return True
        if current == current.parent:
            return False
        current = current.parent


def _safe_relative(path: Path, root: Path) -> Path:
    absolute = path.absolute()
    root_abs = root.absolute()
    try:
        relative = absolute.relative_to(root_abs)
    except ValueError:
        raise SemanticQueueError("SOURCE_PATH_OUTSIDE_RUN") from None
    if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise SemanticQueueError("SOURCE_PATH_INVALID")
    return relative


def _safe_output(path: Path, root: Path) -> Path:
    root = root.absolute()
    path = path.absolute()
    try:
        path.relative_to(root)
    except ValueError:
        raise SemanticQueueError("OUTPUT_PATH_OUTSIDE_ROOT") from None
    current = path
    while current != root:
        if current.is_symlink():
            raise SemanticQueueError("OUTPUT_SYMLINK")
        current = current.parent
    if path.exists() and (path.is_symlink() or not path.is_file()):
        raise SemanticQueueError("OUTPUT_PATH_INVALID")
    return path


def _decode_artifacts(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, str):
        raise SemanticQueueError("ARTIFACT_INDEX_INVALID")
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        raise SemanticQueueError("ARTIFACT_INDEX_INVALID") from None
    if not isinstance(parsed, Mapping):
        raise SemanticQueueError("ARTIFACT_INDEX_INVALID")
    result: dict[str, str] = {}
    for relative, digest in parsed.items():
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or not _is_sha256(digest):
            raise SemanticQueueError("ARTIFACT_INDEX_INVALID")
        result[relative] = digest
    return dict(sorted(result.items()))


def _expected_source_hashes(binding: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    artifacts = binding.get("artifacts", {})
    for group in ("media", "transcript", "frames"):
        values = artifacts.get(group, {}) if isinstance(artifacts, Mapping) else {}
        for path, digest in values.items():
            result[f"{group}:{path}"] = digest
    context = artifacts.get("context", {}) if isinstance(artifacts, Mapping) else {}
    if isinstance(context, Mapping):
        for path, digest in context.items():
            result[f"context:{path}"] = digest
    return dict(sorted(result.items()))


def _valid_maker_payload(payload: Any, *, job: Mapping[str, Any], output_bytes: bytes) -> None:
    if len(output_bytes) > 2 * 1024 * 1024 or not isinstance(payload, Mapping):
        raise SemanticQueueError("MAKER_PAYLOAD_INVALID")
    required = {"schema", "job_key", "input_sha256", "source_hashes", "evidence_pointers", "state", "uncertainty"}
    if not required <= set(payload):
        raise SemanticQueueError("MAKER_PAYLOAD_FIELDS_MISSING")
    if payload["schema"] != "m2.semantic-maker-output.v1" or payload["job_key"] != job["job_key"] or payload["input_sha256"] != job["input_hash"]:
        raise SemanticQueueError("MAKER_PAYLOAD_BINDING_INVALID")
    if payload["state"] != "PENDING_REVIEW":
        raise SemanticQueueError("MAKER_PAYLOAD_STATE_INVALID")
    if not isinstance(payload["source_hashes"], Mapping) or dict(payload["source_hashes"]) != _expected_source_hashes(json.loads(job["input_binding_json"])):
        raise SemanticQueueError("MAKER_PAYLOAD_SOURCE_HASHES_INVALID")
    pointers = payload["evidence_pointers"]
    if not isinstance(pointers, list) or not pointers or len(pointers) > 256:
        raise SemanticQueueError("MAKER_PAYLOAD_EVIDENCE_INVALID")
    source_paths = set(json.loads(job["source_paths_json"]))
    for pointer in pointers:
        if not isinstance(pointer, str) or not pointer or len(pointer) > 512 or "\x00" in pointer or pointer.startswith("/") or ".." in pointer.split("/"):
            raise SemanticQueueError("MAKER_PAYLOAD_EVIDENCE_INVALID")
        if "/" in pointer and pointer not in source_paths:
            raise SemanticQueueError("MAKER_PAYLOAD_EVIDENCE_OUTSIDE_SOURCE")
    if not isinstance(payload["uncertainty"], list) or len(payload["uncertainty"]) > 128 or any(not isinstance(item, str) or len(item) > 512 for item in payload["uncertainty"]):
        raise SemanticQueueError("MAKER_PAYLOAD_UNCERTAINTY_INVALID")


def _read_json_object(path: Path, error: str) -> tuple[dict[str, Any], bytes]:
    try:
        payload_bytes = path.read_bytes()
        if len(payload_bytes) > 2 * 1024 * 1024:
            raise ValueError("payload too large")
        payload = json.loads(payload_bytes.decode("utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        raise SemanticQueueError(error) from None
    if not isinstance(payload, dict):
        raise SemanticQueueError(error)
    return payload, payload_bytes


def _valid_review_receipt(payload: Mapping[str, Any], *, job: Mapping[str, Any], reviewer: str, model: str, verdict: str, maker_output_sha256: str) -> None:
    required = {"schema", "job_key", "input_sha256", "maker_output_sha256", "reviewer_actor", "reviewer_model", "scope", "verdict", "limitations"}
    if not required <= set(payload):
        raise SemanticQueueError("REVIEW_RECEIPT_FIELDS_MISSING")
    if payload["schema"] != "m2.semantic-review-receipt.v1" or payload["job_key"] != job["job_key"] or payload["input_sha256"] != job["input_hash"] or payload["maker_output_sha256"] != maker_output_sha256:
        raise SemanticQueueError("REVIEW_RECEIPT_BINDING_INVALID")
    if payload["reviewer_actor"] != reviewer or payload["reviewer_model"] != model or payload["verdict"] != verdict:
        raise SemanticQueueError("REVIEW_RECEIPT_REVIEWER_INVALID")
    if not isinstance(payload["scope"], list) or not payload["scope"] or any(not isinstance(item, str) or not item or len(item) > 512 for item in payload["scope"]):
        raise SemanticQueueError("REVIEW_RECEIPT_SCOPE_INVALID")
    if not isinstance(payload["limitations"], list) or len(payload["limitations"]) > 128 or any(not isinstance(item, str) or len(item) > 512 for item in payload["limitations"]):
        raise SemanticQueueError("REVIEW_RECEIPT_LIMITATIONS_INVALID")


class SemanticQueue:
    """Separate queue DB over a consistent, read-only corpus ledger snapshot.

    Actor and model fields are coordination labels recorded in the audit log;
    this local queue does not authenticate identities or establish roster
    membership. A deployed executor must perform that binding separately.
    """

    def __init__(
        self,
        queue_db: Path,
        corpus_db: Path,
        *,
        corpus_root: Path | None = None,
        context_paths: Iterable[Path] | None = None,
        contract_version: str = CONTRACT_VERSION,
        output_root: Path | None = None,
        review_root: Path | None = None,
        maker_model: str = "luna-high",
        reviewer_model: str = "luna-high",
        claim_lease_seconds: int = CLAIM_LEASE_SECONDS,
    ) -> None:
        self.queue_db = Path(queue_db).absolute()
        self.corpus_db = Path(corpus_db).absolute()
        if self.corpus_db.is_symlink() or not self.corpus_db.is_file():
            raise SemanticQueueError("CORPUS_DB_UNAVAILABLE")
        if self.queue_db.exists() and self.queue_db.is_symlink():
            raise SemanticQueueError("QUEUE_DB_SYMLINK")
        self.corpus_root = Path(corpus_root or self.corpus_db.parent).absolute()
        self.output_root = Path(output_root or self.queue_db.parent / "semantic-tasks").absolute()
        self.review_root = Path(review_root or self.output_root / "reviews").absolute()
        self.context_paths = tuple(Path(path).absolute() for path in (context_paths or _default_context_paths()))
        if len(set(self.context_paths)) != len(self.context_paths):
            raise SemanticQueueError("CONTEXT_DUPLICATE")
        self.context_hashes = _read_context(self.context_paths)
        self.context_label_paths = {
            f"context-{index:02d}": path for index, path in enumerate(self.context_paths, start=1)
        }
        self.context_bindings = {
            label: self.context_hashes[str(path)] for label, path in self.context_label_paths.items()
        }
        self._guard_path_scope(self.queue_db, self.queue_db.parent)
        self._guard_path_scope(self.corpus_db, self.corpus_root)
        self._guard_path_scope(self.corpus_root, self.corpus_root)
        self._guard_path_scope(self.output_root, self.output_root)
        self._guard_path_scope(self.review_root, self.review_root)
        for path in self.context_paths:
            self._guard_path_scope(path, path.parent)
        if not isinstance(contract_version, str) or not contract_version:
            raise SemanticQueueError("CONTRACT_VERSION_REQUIRED")
        self.contract_version = contract_version
        self.maker_model = maker_model
        self.reviewer_model = reviewer_model
        if type(claim_lease_seconds) is not int or not 1 <= claim_lease_seconds <= MAX_CLAIM_LEASE_SECONDS:
            raise SemanticQueueError("CLAIM_LEASE_INVALID")
        self.claim_lease_seconds = claim_lease_seconds
        self._lock = None
        self._db: sqlite3.Connection | None = None

    @staticmethod
    def _guard_path_scope(path: Path, approved_root: Path) -> None:
        path = Path(path).absolute()
        root = Path(approved_root).absolute()
        if _has_symlink_ancestor(path) or _has_symlink_ancestor(root):
            raise SemanticQueueError("SYMLINKED_PATH_ANCESTOR")
        try:
            path.relative_to(root)
        except ValueError:
            raise SemanticQueueError("PATH_OUTSIDE_APPROVED_ROOT") from None

    def open(self) -> "SemanticQueue":
        self.queue_db.parent.mkdir(parents=True, exist_ok=True)
        if self.queue_db.is_symlink():
            raise SemanticQueueError("QUEUE_DB_SYMLINK")
        lock_path = self.queue_db.with_name(self.queue_db.name + ".lock")
        if lock_path.is_symlink() or _has_symlink_ancestor(lock_path):
            raise SemanticQueueError("SYMLINKED_PATH_ANCESTOR")
        self._lock = lock_path.open("a")
        try:
            fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._lock.close()
            self._lock = None
            raise SemanticQueueError("QUEUE_ALREADY_RUNNING") from None
        self._db = sqlite3.connect(self.queue_db, timeout=5)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.executescript(
            "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
            "CREATE TABLE IF NOT EXISTS identities (reel_id TEXT PRIMARY KEY, code TEXT UNIQUE NOT NULL, identity_index INTEGER NOT NULL, "
            "acquisition_state TEXT NOT NULL, transcript_state TEXT NOT NULL, frames_state TEXT NOT NULL, scene_review_state TEXT NOT NULL, "
            "disposition TEXT NOT NULL, disposition_reason TEXT NOT NULL, source_snapshot_hash TEXT NOT NULL, updated_at REAL NOT NULL);"
            "CREATE TABLE IF NOT EXISTS jobs (job_key TEXT PRIMARY KEY, reel_id TEXT NOT NULL, code TEXT NOT NULL, kind TEXT NOT NULL, "
            "contract_version TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('READY','CLAIMED','MAKER_DONE','REVIEW_REQUIRED','ACCEPTED','REJECTED','NOT_READY','SUPERSEDED')), "
            "input_hash TEXT NOT NULL, input_binding_json TEXT NOT NULL, source_paths_json TEXT NOT NULL, maker_actor TEXT, maker_model TEXT, "
            "maker_output_path TEXT, maker_output_sha256 TEXT, reviewer_actor TEXT, reviewer_model TEXT, review_verdict TEXT, review_receipt_path TEXT, review_receipt_sha256 TEXT, lease_expires_at REAL, claim_attempt INTEGER, created_at REAL NOT NULL, updated_at REAL NOT NULL, "
            "UNIQUE(reel_id, kind, job_key), FOREIGN KEY(reel_id) REFERENCES identities(reel_id));"
            "CREATE TABLE IF NOT EXISTS attempts (id INTEGER PRIMARY KEY, job_key TEXT NOT NULL, phase TEXT NOT NULL, attempt INTEGER NOT NULL, state TEXT NOT NULL, actor TEXT, model TEXT, input_hash TEXT NOT NULL, output_hash TEXT, error TEXT, started_at REAL NOT NULL, finished_at REAL, FOREIGN KEY(job_key) REFERENCES jobs(job_key));"
            "CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, job_key TEXT, reel_id TEXT, event TEXT NOT NULL, state TEXT, actor TEXT, model TEXT, payload_json TEXT NOT NULL, observed_at REAL NOT NULL);"
            "CREATE INDEX IF NOT EXISTS jobs_reel_kind ON jobs(reel_id, kind);"
        )
        columns = {row[1] for row in self._db.execute("PRAGMA table_info(jobs)")}
        for column, declaration in (("lease_expires_at", "REAL"), ("claim_attempt", "INTEGER"), ("review_receipt_path", "TEXT"), ("review_receipt_sha256", "TEXT")):
            if column not in columns:
                self._db.execute(f"ALTER TABLE jobs ADD COLUMN {column} {declaration}")
        self._db.commit()
        config = {"contract_version": self.contract_version, "context_hashes": self.context_bindings}
        existing = dict(self._db.execute("SELECT key,value FROM meta"))
        if existing and existing.get("contract_config_hash") not in (None, stable_hash(config)):
            self.close()
            raise SemanticQueueError("QUEUE_CONTRACT_CHANGED")
        self._db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('contract_config_hash',?)", (stable_hash(config),))
        self._db.commit()
        self._recover_stale_claims()
        return self

    def close(self) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None
        if self._lock is not None:
            fcntl.flock(self._lock, fcntl.LOCK_UN)
            self._lock.close()
            self._lock = None

    def __enter__(self) -> "SemanticQueue":
        return self.open()

    def __exit__(self, *_: Any) -> None:
        self.close()

    @property
    def db(self) -> sqlite3.Connection:
        if self._db is None:
            raise SemanticQueueError("QUEUE_NOT_OPEN")
        return self._db

    def _event(self, event: str, *, job_key: str | None = None, reel_id: str | None = None, state: str | None = None, actor: str | None = None, model: str | None = None, payload: Mapping[str, Any] | None = None) -> None:
        self.db.execute("INSERT INTO events(job_key,reel_id,event,state,actor,model,payload_json,observed_at) VALUES(?,?,?,?,?,?,?,?)", (job_key, reel_id, event, state, actor, model, json.dumps(dict(payload or {}), sort_keys=True, ensure_ascii=False), time.time()))

    def _recover_stale_claims(self, now: float | None = None) -> int:
        now = time.time() if now is None else now
        with self.db:
            rows = self.db.execute("SELECT job_key,reel_id FROM jobs WHERE state='CLAIMED' AND lease_expires_at IS NOT NULL AND lease_expires_at<=?", (now,)).fetchall()
            for row in rows:
                self.db.execute("UPDATE jobs SET state='READY',maker_actor=NULL,maker_model=NULL,lease_expires_at=NULL,claim_attempt=NULL,updated_at=? WHERE job_key=?", (now, row["job_key"]))
                attempt = self.db.execute("SELECT COALESCE(MAX(attempt),0)+1 FROM attempts WHERE job_key=? AND phase='maker'", (row["job_key"],)).fetchone()[0]
                input_hash = self.db.execute("SELECT input_hash FROM jobs WHERE job_key=?", (row["job_key"],)).fetchone()[0]
                self.db.execute("INSERT INTO attempts(job_key,phase,attempt,state,input_hash,error,started_at,finished_at) VALUES(?,?,?,?,?,?,?,?)", (row["job_key"], "maker", attempt, "LEASE_EXPIRED", input_hash, "CLAIM_LEASE_EXPIRED", now, now))
                self._event("claim_recovered", job_key=row["job_key"], reel_id=row["reel_id"], state="READY", payload={"reason": "CLAIM_LEASE_EXPIRED"})
        return len(rows)

    def reclaim_stale(self, *, now: float | None = None) -> int:
        return self._recover_stale_claims(now)

    def _snapshot_rows(self) -> tuple[list[sqlite3.Row], dict[str, str], str]:
        if self.corpus_db.is_symlink() or not self.corpus_db.is_file():
            raise SemanticQueueError("CORPUS_DB_UNAVAILABLE")
        uri = self.corpus_db.as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as source:
            source.row_factory = sqlite3.Row
            source.execute("PRAGMA query_only=ON")
            source.execute("BEGIN")
            try:
                rows = source.execute("SELECT reel_id,code,identity_index,acquisition_state,transcript_state,frames_state,scene_review_state,acquisition_artifact,transcript_artifact,frames_artifact FROM reels ORDER BY identity_index,reel_id").fetchall()
                bindings = dict(source.execute("SELECT key,value FROM binding ORDER BY key").fetchall())
            except sqlite3.Error:
                raise SemanticQueueError("CORPUS_LEDGER_SCHEMA_UNAVAILABLE") from None
            # Membership is immutable for a corpus run. Modality progress for
            # another Reel must not invalidate an unchanged evidence capsule.
            # This Reel's states/artifacts remain bound separately in _row_jobs.
            population_hash = stable_hash({"binding": bindings, "identities": [
                {key: row[key] for key in ('reel_id', 'code', 'identity_index')} for row in rows]})
            return rows, bindings, population_hash

    def _verified_artifacts(self, value: Any) -> dict[str, str] | None:
        try:
            artifacts = _decode_artifacts(value)
        except SemanticQueueError:
            return None
        if not artifacts:
            return None
        for relative, expected in artifacts.items():
            path = self.corpus_root / relative
            if path.is_symlink() or not path.is_file():
                return None
            try:
                if not path.resolve().is_relative_to(self.corpus_root.resolve()):
                    return None
            except AttributeError:
                if not str(path.resolve()).startswith(str(self.corpus_root.resolve()) + os.sep):
                    return None
            if file_sha256(path) != expected:
                return None
        return artifacts

    def _validate_job_input(self, job: Mapping[str, Any]) -> dict[str, Any]:
        try:
            binding = json.loads(job["input_binding_json"])
        except (TypeError, json.JSONDecodeError):
            raise SemanticQueueError("JOB_INPUT_BINDING_INVALID") from None
        if not isinstance(binding, Mapping) or stable_hash(binding) != job["input_hash"]:
            raise SemanticQueueError("JOB_INPUT_BINDING_INVALID")
        artifacts = binding.get("artifacts")
        if not isinstance(artifacts, Mapping):
            raise SemanticQueueError("JOB_INPUT_BINDING_INVALID")
        for group in ("media", "transcript", "frames"):
            values = artifacts.get(group, {})
            if values and self._verified_artifacts(json.dumps(values, sort_keys=True)) is None:
                raise SemanticQueueError("SOURCE_ARTIFACT_CHANGED")
        context = artifacts.get("context", {})
        if not isinstance(context, Mapping) or dict(context) != self.context_bindings:
            raise SemanticQueueError("JOB_INPUT_BINDING_INVALID")
        for label, expected in context.items():
            path = self.context_label_paths.get(label)
            if path is None or not _is_sha256(expected) or self.context_bindings[label] != expected:
                raise SemanticQueueError("CONTEXT_ARTIFACT_CHANGED")
            try:
                current = file_sha256(path) if not _has_symlink_ancestor(path) and path.is_file() else None
            except OSError:
                current = None
            if current != expected:
                raise SemanticQueueError("CONTEXT_ARTIFACT_CHANGED")
        return dict(binding)

    @staticmethod
    def _read_maker_json(path: Path) -> tuple[dict[str, Any], bytes]:
        try:
            payload_bytes = path.read_bytes()
            payload = json.loads(payload_bytes.decode("utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            raise SemanticQueueError("MAKER_PAYLOAD_INVALID") from None
        if not isinstance(payload, dict):
            raise SemanticQueueError("MAKER_PAYLOAD_INVALID")
        return payload, payload_bytes

    def _row_jobs(self, row: sqlite3.Row, corpus_binding: Mapping[str, str], population_hash: str, population_count: int) -> list[dict[str, Any]]:
        media = self._verified_artifacts(row["acquisition_artifact"])
        transcript = self._verified_artifacts(row["transcript_artifact"])
        frames = self._verified_artifacts(row["frames_artifact"])
        has_transcription = transcript is not None and any(path.endswith("transcription.json") for path in transcript)
        transcript_ready = media is not None and transcript is not None and has_transcription and row["transcript_state"] in READY_TRANSCRIPT_STATES
        frames_ready = media is not None and frames is not None and row["frames_state"] in READY_FRAME_STATES
        source_base = {"media": media or {}, "transcript": transcript or {}, "frames": frames or {}, "context": self.context_bindings}
        jobs = []
        for kind, ready in (("transcript_structure", transcript_ready), ("scene_candidates", frames_ready)):
            binding = {"reel_id": row["reel_id"], "code": row["code"], "kind": kind, "contract_version": self.contract_version, "corpus_binding": dict(corpus_binding), "corpus_population_hash": population_hash, "corpus_population_count": population_count, "artifacts": source_base, "states": {"acquisition": row["acquisition_state"], "transcript": row["transcript_state"], "frames": row["frames_state"]}}
            input_hash = stable_hash(binding)
            job_key = "sjq-" + input_hash
            missing = []
            if media is None:
                missing.append("verified_media")
            if kind == "transcript_structure" and not transcript_ready:
                missing.append("verified_completed_transcript")
            if kind == "scene_candidates" and not frames_ready:
                missing.append("verified_completed_frames")
            disposition = "READY" if ready else "NOT_READY"
            jobs.append({"job_key": job_key, "kind": kind, "input_hash": input_hash, "binding": binding, "state": disposition, "reason": "" if ready else ";".join(missing) or "stage_not_ready", "source_paths": sorted({path for group in ("media", "transcript", "frames") for path in source_base[group]})})
        return jobs

    def refresh(self) -> dict[str, Any]:
        rows, corpus_binding, population_hash = self._snapshot_rows()
        now = time.time()
        with self.db:
            for row in rows:
                snapshot_hash = stable_hash({key: row[key] for key in row.keys()})
                media_jobs = self._row_jobs(row, corpus_binding, population_hash, len(rows))
                # Every corpus identity is registered before job admission, even
                # when both semantic modalities are blocked or not ready.
                if row["acquisition_state"] in BLOCKED_ACQUISITION_STATES:
                    disposition = "BLOCKED"
                else:
                    disposition = "READY" if any(job["state"] == "READY" for job in media_jobs) else "NOT_READY"
                reasons = ";".join(sorted({job["reason"] for job in media_jobs if job["reason"]}))
                self.db.execute(
                    "INSERT INTO identities(reel_id,code,identity_index,acquisition_state,transcript_state,frames_state,scene_review_state,disposition,disposition_reason,source_snapshot_hash,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?) "
                    "ON CONFLICT(reel_id) DO UPDATE SET code=excluded.code,identity_index=excluded.identity_index,acquisition_state=excluded.acquisition_state,transcript_state=excluded.transcript_state,frames_state=excluded.frames_state,scene_review_state=excluded.scene_review_state,disposition=excluded.disposition,disposition_reason=excluded.disposition_reason,source_snapshot_hash=excluded.source_snapshot_hash,updated_at=excluded.updated_at",
                    (row["reel_id"], row["code"], row["identity_index"], row["acquisition_state"], row["transcript_state"], row["frames_state"], row["scene_review_state"], disposition, reasons, snapshot_hash, now),
                )
                for job in media_jobs:
                    stale = self.db.execute("SELECT job_key,state FROM jobs WHERE reel_id=? AND kind=? AND job_key<>?", (row["reel_id"], job["kind"], job["job_key"])).fetchall()
                    for old in stale:
                        if old["state"] not in {"ACCEPTED", "REJECTED", "SUPERSEDED"}:
                            self.db.execute("UPDATE jobs SET state='SUPERSEDED',updated_at=? WHERE job_key=?", (now, old["job_key"]))
                            self._event("job_superseded", job_key=old["job_key"], reel_id=row["reel_id"], state="SUPERSEDED", payload={"replacement_job_key": job["job_key"], "reason": "current_source_binding_changed"})
                    existing = self.db.execute("SELECT state FROM jobs WHERE job_key=?", (job["job_key"],)).fetchone()
                    if existing is None:
                        self.db.execute(
                            "INSERT INTO jobs(job_key,reel_id,code,kind,contract_version,state,input_hash,input_binding_json,source_paths_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                            (job["job_key"], row["reel_id"], row["code"], job["kind"], self.contract_version, job["state"], job["input_hash"], json.dumps(job["binding"], sort_keys=True, ensure_ascii=False), json.dumps(job["source_paths"], sort_keys=True), now, now),
                        )
                        self._event("job_created", job_key=job["job_key"], reel_id=row["reel_id"], state=job["state"], payload={"kind": job["kind"], "reason": job["reason"], "input_hash": job["input_hash"]})
                    elif existing["state"] == "NOT_READY" and job["state"] == "READY":
                        self.db.execute("UPDATE jobs SET state='READY',updated_at=? WHERE job_key=?", (now, job["job_key"]))
                        self._event("job_ready", job_key=job["job_key"], reel_id=row["reel_id"], state="READY", payload={"input_hash": job["input_hash"]})
            self._event("ledger_snapshot_refreshed", payload={"population": len(rows), "job_kinds": list(JOB_KINDS),
                        "population_hash": population_hash,
                        "modality_snapshot_hash": stable_hash([dict(row) for row in rows])})
            self.db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", ("corpus_binding_json", json.dumps(corpus_binding, sort_keys=True)))
            self.db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", ("corpus_population_hash", population_hash))
            self.db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", ("corpus_population_count", str(len(rows))))
        return self.summary()

    def _current_job_keys(self) -> set[str]:
        rows, corpus_binding, population_hash = self._snapshot_rows()
        keys: set[str] = set()
        for row in rows:
            for candidate in self._row_jobs(row, corpus_binding, population_hash, len(rows)):
                keys.add(candidate["job_key"])
        return keys

    def summary(self) -> dict[str, Any]:
        metadata = dict(self.db.execute("SELECT key,value FROM meta WHERE key IN ('corpus_binding_json','corpus_population_hash','corpus_population_count')"))
        identities = self.db.execute("SELECT disposition,COUNT(*) AS n FROM identities GROUP BY disposition ORDER BY disposition").fetchall()
        jobs = self.db.execute("SELECT state,kind,COUNT(*) AS n FROM jobs GROUP BY state,kind ORDER BY state,kind").fetchall()
        return {"schema": "m2.semantic-queue.v1", "population": self.db.execute("SELECT COUNT(*) FROM identities").fetchone()[0], "identity_dispositions": {row[0]: row[1] for row in identities}, "jobs": [{"state": row[0], "kind": row[1], "count": row[2]} for row in jobs], "max_export_reels": MAX_EXPORT_REELS, "provider_calls": 0, "review_state": "REVIEW_PENDING", "corpus_population_hash": metadata.get("corpus_population_hash"), "corpus_population_count": int(metadata["corpus_population_count"]) if metadata.get("corpus_population_count") else None, "corpus_binding": json.loads(metadata["corpus_binding_json"]) if metadata.get("corpus_binding_json") else {}}

    def export_batch(self, *, limit: int = MAX_EXPORT_REELS, output_dir: Path | None = None, kinds: Iterable[str] = JOB_KINDS) -> list[dict[str, Any]]:
        if type(limit) is not int or not 1 <= limit <= MAX_EXPORT_REELS:
            raise SemanticQueueError("EXPORT_LIMIT")
        kinds = tuple(kinds)
        if not kinds or any(kind not in JOB_KINDS for kind in kinds):
            raise SemanticQueueError("JOB_KIND_INVALID")
        root = Path(output_dir or self.output_root).absolute()
        self._guard_path_scope(root, self.output_root)
        root.mkdir(parents=True, exist_ok=True)
        if root.is_symlink():
            raise SemanticQueueError("OUTPUT_SYMLINK")
        current_keys = self._current_job_keys()
        rows = self.db.execute("SELECT j.*,i.identity_index,i.disposition,i.disposition_reason FROM jobs j JOIN identities i ON i.reel_id=j.reel_id WHERE j.state='READY' AND j.kind IN (%s) ORDER BY i.identity_index,j.kind" % ",".join("?" for _ in kinds), kinds).fetchall()
        rows = [row for row in rows if row["job_key"] in current_keys]
        selected_reels: list[str] = []
        selected = []
        for row in rows:
            if row["reel_id"] not in selected_reels:
                if len(selected_reels) >= limit:
                    continue
                selected_reels.append(row["reel_id"])
            selected.append(row)
        contracts = []
        for row in selected:
            binding = json.loads(row["input_binding_json"])
            contract = {"schema": "m2.semantic-task.v1", "contract_version": row["contract_version"], "job_key": row["job_key"], "kind": row["kind"], "reel_id": row["reel_id"], "code": row["code"], "identity_disposition": row["disposition"], "corpus_binding": binding["corpus_binding"], "corpus_population_hash": binding["corpus_population_hash"], "corpus_population_count": binding["corpus_population_count"], "input_binding": binding, "input_sha256": row["input_hash"], "source_paths": json.loads(row["source_paths_json"]), "context_sources": [{"id": label, "sha256": digest} for label, digest in sorted(self.context_bindings.items())], "executor": {"maker_model": self.maker_model, "reviewer_model": self.reviewer_model, "mode": "explicit_interactive_or_approved_server_executor", "provider_calls_by_queue": 0}, "output_schema": "maker artifact must carry job_key, input_sha256, source hashes, bounded evidence pointers, state and uncertainty; no raw speech in public task metadata", "review": {"maker_reviewer_separation": True, "review_binds_exact_maker_output_sha256": True}, "scope": {"max_reels_per_batch": MAX_EXPORT_REELS, "batch_reels": selected_reels}}
            path = _safe_output(root / f"{row['kind']}-{row['code']}-{row['job_key'][4:16]}.json", root)
            encoded = json.dumps(contract, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
            if path.exists():
                if path.read_text(encoding="utf-8") != encoded:
                    raise SemanticQueueError("OUTPUT_COLLISION")
            else:
                path.write_text(encoded, encoding="utf-8")
            contracts.append({"job_key": row["job_key"], "kind": row["kind"], "reel_id": row["reel_id"], "path": str(path), "sha256": file_sha256(path)})
        return contracts

    def claim(self, job_key: str, *, actor: str, model: str) -> dict[str, Any]:
        if not actor or not model:
            raise SemanticQueueError("ACTOR_MODEL_REQUIRED")
        self._recover_stale_claims()
        with self.db:
            row = self.db.execute("SELECT * FROM jobs WHERE job_key=?", (job_key,)).fetchone()
            if not row:
                raise SemanticQueueError("JOB_NOT_FOUND")
            if row["state"] != "READY":
                raise SemanticQueueError("JOB_NOT_READY_TO_CLAIM")
            if job_key not in self._current_job_keys():
                self.db.execute("UPDATE jobs SET state='SUPERSEDED',updated_at=? WHERE job_key=?", (time.time(), job_key))
                self.db.commit()
                raise SemanticQueueError("JOB_SUPERSEDED")
            attempt = self.db.execute("SELECT COALESCE(MAX(attempt),0)+1 FROM attempts WHERE job_key=? AND phase='maker'", (job_key,)).fetchone()[0]
            now = time.time()
            lease_expires = now + self.claim_lease_seconds
            self.db.execute("UPDATE jobs SET state='CLAIMED',maker_actor=?,maker_model=?,lease_expires_at=?,claim_attempt=?,updated_at=? WHERE job_key=?", (actor, model, lease_expires, attempt, now, job_key))
            self.db.execute("INSERT INTO attempts(job_key,phase,attempt,state,actor,model,input_hash,started_at) VALUES(?,?,?,?,?,?,?,?)", (job_key, "maker", attempt, "CLAIMED", actor, model, row["input_hash"], now))
            self._event("job_claimed", job_key=job_key, reel_id=row["reel_id"], state="CLAIMED", actor=actor, model=model, payload={"attempt": attempt, "input_hash": row["input_hash"], "lease_expires_at": lease_expires})
            return dict(row) | {"state": "CLAIMED", "maker_actor": actor, "maker_model": model, "lease_expires_at": lease_expires, "claim_attempt": attempt}

    def heartbeat(self, job_key: str, *, actor: str, extend_seconds: int | None = None) -> float:
        extension = self.claim_lease_seconds if extend_seconds is None else extend_seconds
        if type(extension) is not int or not 1 <= extension <= MAX_CLAIM_LEASE_SECONDS:
            raise SemanticQueueError("CLAIM_LEASE_INVALID")
        with self.db:
            row = self.db.execute("SELECT * FROM jobs WHERE job_key=?", (job_key,)).fetchone()
            now = time.time()
            if not row or row["state"] != "CLAIMED" or row["maker_actor"] != actor or row["lease_expires_at"] is None or row["lease_expires_at"] <= now:
                raise SemanticQueueError("CLAIM_LEASE_EXPIRED")
            expires = now + extension
            self.db.execute("UPDATE jobs SET lease_expires_at=?,updated_at=? WHERE job_key=?", (expires, now, job_key))
            self._event("claim_heartbeat", job_key=job_key, reel_id=row["reel_id"], state="CLAIMED", actor=actor, model=row["maker_model"], payload={"lease_expires_at": expires})
            return expires

    def submit_maker(self, job_key: str, *, actor: str, output_path: Path, output_sha256: str, input_sha256: str) -> dict[str, Any]:
        if not _is_sha256(output_sha256) or not _is_sha256(input_sha256):
            raise SemanticQueueError("HASH_REQUIRED")
        row = self.db.execute("SELECT * FROM jobs WHERE job_key=?", (job_key,)).fetchone()
        if not row:
            raise SemanticQueueError("JOB_NOT_FOUND")
        if row["state"] != "CLAIMED" or row["maker_actor"] != actor or row["lease_expires_at"] is None or row["lease_expires_at"] <= time.time():
            raise SemanticQueueError("MAKER_BINDING_INVALID")
        if input_sha256 != row["input_hash"]:
            raise SemanticQueueError("JOB_INPUT_CHANGED")
        self._validate_job_input(row)
        path = _safe_output(Path(output_path), self.output_root)
        if not path.is_file() or file_sha256(path) != output_sha256:
            raise SemanticQueueError("MAKER_OUTPUT_HASH_MISMATCH")
        if path.stat().st_size > 2 * 1024 * 1024:
            raise SemanticQueueError("MAKER_PAYLOAD_INVALID")
        payload, payload_bytes = self._read_maker_json(path)
        _valid_maker_payload(payload, job=row, output_bytes=payload_bytes)
        conflict = self.db.execute("SELECT job_key FROM jobs WHERE maker_output_path=? AND job_key<>?", (str(path), job_key)).fetchone()
        if conflict:
            raise SemanticQueueError("MAKER_OUTPUT_PATH_REUSED")
        with self.db:
            now = time.time()
            self.db.execute("UPDATE jobs SET state='MAKER_DONE',maker_output_path=?,maker_output_sha256=?,lease_expires_at=NULL,updated_at=? WHERE job_key=?", (str(path), output_sha256, now, job_key))
            self.db.execute("INSERT INTO attempts(job_key,phase,attempt,state,actor,model,input_hash,output_hash,started_at,finished_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (job_key, "maker", row["claim_attempt"], "MAKER_DONE", actor, row["maker_model"], row["input_hash"], output_sha256, now, now))
            self._event("maker_submitted", job_key=job_key, reel_id=row["reel_id"], state="MAKER_DONE", actor=actor, model=row["maker_model"], payload={"input_hash": input_sha256, "output_hash": output_sha256})
        return dict(row) | {"state": "MAKER_DONE", "maker_output_path": str(path), "maker_output_sha256": output_sha256}

    def request_review(self, job_key: str, *, actor: str) -> dict[str, Any]:
        with self.db:
            row = self.db.execute("SELECT * FROM jobs WHERE job_key=?", (job_key,)).fetchone()
            if not row or row["state"] != "MAKER_DONE":
                raise SemanticQueueError("JOB_NOT_READY_FOR_REVIEW")
            now = time.time()
            self.db.execute("UPDATE jobs SET state='REVIEW_REQUIRED',updated_at=? WHERE job_key=?", (now, job_key))
            self._event("review_requested", job_key=job_key, reel_id=row["reel_id"], state="REVIEW_REQUIRED", actor=actor, payload={"maker_output_sha256": row["maker_output_sha256"]})
            return dict(row) | {"state": "REVIEW_REQUIRED"}

    def submit_review(self, job_key: str, *, reviewer: str, model: str, verdict: str, maker_output_sha256: str, review_receipt_path: Path, review_receipt_sha256: str) -> dict[str, Any]:
        if verdict not in {"ACCEPTED", "REJECTED"}:
            raise SemanticQueueError("REVIEW_VERDICT_INVALID")
        if not reviewer or not model or not _is_sha256(maker_output_sha256):
            raise SemanticQueueError("REVIEW_BINDING_REQUIRED")
        if not _is_sha256(review_receipt_sha256):
            raise SemanticQueueError("REVIEW_RECEIPT_HASH_REQUIRED")
        with self.db:
            row = self.db.execute("SELECT * FROM jobs WHERE job_key=?", (job_key,)).fetchone()
            if not row or row["state"] != "REVIEW_REQUIRED":
                raise SemanticQueueError("JOB_NOT_REVIEWABLE")
            if reviewer == row["maker_actor"]:
                raise SemanticQueueError("SELF_REVIEW_FORBIDDEN")
            if maker_output_sha256 != row["maker_output_sha256"]:
                raise SemanticQueueError("MAKER_OUTPUT_CHANGED")
            receipt_path = _safe_output(Path(review_receipt_path), self.review_root)
            if not receipt_path.is_file() or file_sha256(receipt_path) != review_receipt_sha256:
                raise SemanticQueueError("REVIEW_RECEIPT_HASH_MISMATCH")
            receipt, _ = _read_json_object(receipt_path, "REVIEW_RECEIPT_INVALID")
            _valid_review_receipt(receipt, job=row, reviewer=reviewer, model=model, verdict=verdict, maker_output_sha256=maker_output_sha256)
            conflict = self.db.execute("SELECT job_key FROM jobs WHERE review_receipt_path=? AND job_key<>?", (str(receipt_path.relative_to(self.review_root)), job_key)).fetchone()
            if conflict:
                raise SemanticQueueError("REVIEW_RECEIPT_PATH_REUSED")
            now = time.time()
            receipt_relative = str(receipt_path.relative_to(self.review_root))
            self.db.execute("UPDATE jobs SET state=?,reviewer_actor=?,reviewer_model=?,review_verdict=?,review_receipt_path=?,review_receipt_sha256=?,updated_at=? WHERE job_key=?", (verdict, reviewer, model, verdict, receipt_relative, review_receipt_sha256, now, job_key))
            attempt = self.db.execute("SELECT COALESCE(MAX(attempt),0)+1 FROM attempts WHERE job_key=? AND phase='review'", (job_key,)).fetchone()[0]
            self.db.execute("INSERT INTO attempts(job_key,phase,attempt,state,actor,model,input_hash,output_hash,started_at,finished_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (job_key, "review", attempt, verdict, reviewer, model, row["input_hash"], maker_output_sha256, now, now))
            self._event("review_submitted", job_key=job_key, reel_id=row["reel_id"], state=verdict, actor=reviewer, model=model, payload={"maker_output_sha256": maker_output_sha256, "review_receipt_sha256": review_receipt_sha256})
            return dict(row) | {"state": verdict, "reviewer_actor": reviewer, "reviewer_model": model, "review_verdict": verdict, "review_receipt_path": receipt_relative, "review_receipt_sha256": review_receipt_sha256}

    def jobs(self, *, state: str | None = None) -> list[dict[str, Any]]:
        if state is not None and state not in STATES:
            raise SemanticQueueError("STATE_INVALID")
        query = "SELECT * FROM jobs" + (" WHERE state=?" if state else "") + " ORDER BY created_at,job_key"
        return [dict(row) for row in self.db.execute(query, (state,) if state else ())]


__all__ = ["CONTRACT_VERSION", "JOB_KINDS", "MAX_EXPORT_REELS", "SemanticQueue", "SemanticQueueError", "file_sha256", "stable_hash"]
