"""Transactional checkpoints and append-only, hash-linked stage events.

Hashes attest integrity, not identity. Local operators are trusted; deployment
must enforce filesystem permissions and bind the actor roster to authentication.
"""

import hashlib
import json
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager, closing
from pathlib import Path

from .policy import BY_ID, STAGES, STATES, SUCCESS, dependencies, policy


class StateError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def implementation_manifest():
    root = Path(__file__).parent.parent
    paths = set()
    for directory in ["m2_orchestrator", "m2_signal", "m2_studio", "studio/remotion",
                      "skills/m2-stage-worker", "skills/m2-script-writer"]:
        for p in (root / directory).rglob("*"):
            if p.is_file() and not ({"__pycache__", "node_modules", ".cache"} & set(p.parts)) and p.suffix in {".py", ".sql", ".json", ".mjs", ".ts", ".tsx", ".md"}:
                paths.add(p)
    for name in ["config/m2-metrics.v1.json", "config/m2-stage-policy.v1.json", "agents/m2-roles.json",
                 "knowledge/m2-positioning.md", "knowledge/m2-operating-memory.md"]:
        p = root / name
        if p.is_file():
            paths.add(p)
    return {str(p.relative_to(root)): file_digest(p) for p in sorted(paths)}


def runtime_hash():
    # Own executable code is part of checkpoint identity, not only the DAG.
    return digest({p.name: file_digest(p) for p in sorted(Path(__file__).parent.glob("*.py"))})


def policy_hash():
    return digest({"policy": policy(), "runtime": runtime_hash()})


def relative_file(root, value):
    p = Path(value)
    if p.is_absolute() or ".." in p.parts:
        raise StateError("ARTIFACT_PATH_OUTSIDE_RUN")
    resolved = (root / p).resolve()
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise StateError("ARTIFACT_MISSING_OR_OUTSIDE_RUN")
    return resolved


def validate_config(config):
    if config.get("schema") != "m2.run-config.v1":
        raise StateError("CONFIG_SCHEMA")
    if config.get("platforms") != ["instagram_reels"]:
        raise StateError("ACTIVE_PLATFORM_REJECTED")
    if config.get("mode") not in {"replay", "incremental", "server"}:
        raise StateError("RUN_MODE_REJECTED")
    if config.get("provider_execution") is not False:
        raise StateError("PROVIDERS_REQUIRE_SEPARATE_JOB_APPROVAL")
    if config.get("hikerapi_execution") is not False:
        raise StateError("COLLECTION_REQUIRES_SEPARATE_SERVER_ADAPTER")
    if not isinstance(config.get("actors"), dict) or not config["actors"]:
        raise StateError("ACTOR_ROSTER_REQUIRED")
    for actor, roles in config["actors"].items():
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", actor) or not isinstance(roles, list) or not roles:
            raise StateError("ACTOR_ROSTER_INVALID")
        if not all(isinstance(r, str) for r in roles):
            raise StateError("ACTOR_ROLES_INVALID")
    selected = config.get("stages", [s.id for s in STAGES])
    if not isinstance(selected, list) or len(selected) != len(set(selected)) or any(s not in BY_ID for s in selected):
        raise StateError("STAGE_SELECTION_INVALID")
    if not isinstance(config.get("source_manifest"), list) or not config["source_manifest"]:
        raise StateError("SOURCE_MANIFEST_REQUIRED")
    for source in config["source_manifest"]:
        if set(source) != {"source_id", "sha256"} or not re.fullmatch(r"[a-f0-9]{64}", source["sha256"]):
            raise StateError("SOURCE_MANIFEST_INVALID")
    if len({s["source_id"] for s in config["source_manifest"]}) != len(config["source_manifest"]):
        raise StateError("SOURCE_ID_DUPLICATE")
    acquisition = config.get("media_acquisition")
    if acquisition is not None:
        if not isinstance(acquisition, dict) or acquisition.get("enabled") is not True or type(acquisition.get("network")) is not bool:
            raise StateError("MEDIA_CONFIG_INVALID")
        if not isinstance(acquisition.get("manifest_path"), str) or not re.fullmatch(r"[a-f0-9]{64}", acquisition.get("manifest_sha256", "")):
            raise StateError("MEDIA_MANIFEST_BINDING_REQUIRED")
        if not isinstance(acquisition.get("media_roots", []), list) or not all(isinstance(p,str) for p in acquisition.get("media_roots", [])):
            raise StateError("MEDIA_ROOTS_INVALID")
    canonical(config)


class Controller:
    def __init__(self, directory):
        self.root = Path(directory).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / "state.sqlite"
        with closing(self._connect()) as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS run(id TEXT PRIMARY KEY, config TEXT NOT NULL, hash TEXT NOT NULL, policy_hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS stages(id TEXT PRIMARY KEY, state TEXT NOT NULL, actor TEXT, attempt INTEGER NOT NULL DEFAULT 0, token TEXT, lease_until REAL, error TEXT, receipt TEXT);
                CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL, previous TEXT NOT NULL, hash TEXT NOT NULL UNIQUE);
                CREATE TABLE IF NOT EXISTS approvals(gate TEXT NOT NULL, subject_hash TEXT NOT NULL, actor TEXT NOT NULL, expires REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(gate, subject_hash));
                CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'immutable event'); END;
                CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'immutable event'); END;
            """)

    def _connect(self):
        c = sqlite3.connect(self.db, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA journal_mode=WAL")
        return c

    @contextmanager
    def transaction(self):
        c = self._connect()
        try:
            c.execute("BEGIN IMMEDIATE")
            yield c
            c.commit()
        except BaseException:
            c.rollback()
            raise
        finally:
            c.close()

    def _event(self, c, kind, data):
        row = c.execute("SELECT hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        previous = row[0] if row else "0" * 64
        payload = {"kind": kind, "at": time.time(), **data}
        h = digest({"previous": previous, "payload": payload})
        c.execute("INSERT INTO events(payload,previous,hash) VALUES(?,?,?)", (canonical(payload), previous, h))

    def _run(self, c):
        r = c.execute("SELECT * FROM run").fetchone()
        if r is None:
            raise StateError("RUN_NOT_INITIALIZED")
        if r["policy_hash"] != policy_hash():
            raise StateError("POLICY_OR_IMPLEMENTATION_CHANGED_NEW_RUN_REQUIRED")
        config = json.loads(r["config"])
        if digest(config) != r["hash"]:
            raise StateError("FROZEN_CONFIG_HASH_CHANGED")
        if "implementation_manifest" in config and config["implementation_manifest"] != implementation_manifest():
            raise StateError("DEPENDENCY_IMPLEMENTATION_CHANGED_NEW_RUN_REQUIRED")
        return r, config

    def init(self, run_id, config):
        validate_config(config)
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,95}", run_id):
            raise StateError("RUN_ID_INVALID")
        h = digest(config)
        with self.transaction() as c:
            old = c.execute("SELECT * FROM run").fetchone()
            if old:
                if old["id"] != run_id or old["hash"] != h or old["policy_hash"] != policy_hash():
                    raise StateError("FROZEN_RUN_MISMATCH_NEW_RUN_REQUIRED")
                return h
            c.execute("INSERT INTO run VALUES(?,?,?,?)", (run_id, canonical(config), h, policy_hash()))
            c.executemany("INSERT INTO stages(id,state) VALUES(?,?)", [(s.id, "NOT_STARTED") for s in STAGES])
            self._event(c, "RUN_FROZEN", {"run_id": run_id, "config_hash": h, "policy_hash": policy_hash()})
        return h

    def _actor(self, config, actor, stage_id):
        if BY_ID[stage_id].role not in config["actors"].get(actor, []):
            raise StateError("ACTOR_ROLE_DENIED")

    def approve(self, gate, subject_hash, actor, expires, revoke=False):
        if gate not in {s.gate for s in STAGES if s.gate}:
            raise StateError("UNKNOWN_GATE")
        if not re.fullmatch(r"[a-f0-9]{64}", subject_hash) or expires <= time.time():
            raise StateError("APPROVAL_SUBJECT_OR_EXPIRY_INVALID")
        with self.transaction() as c:
            _, config = self._run(c)
            if "owner" not in config["actors"].get(actor, []):
                raise StateError("OWNER_ROLE_REQUIRED")
            c.execute("INSERT INTO approvals VALUES(?,?,?,?,?) ON CONFLICT(gate,subject_hash) DO UPDATE SET actor=excluded.actor,expires=excluded.expires,revoked=excluded.revoked", (gate, subject_hash, actor, expires, int(revoke)))
            self._event(c, "APPROVAL_REVOKED" if revoke else "APPROVAL_RECORDED", {"gate": gate, "subject_hash": subject_hash, "actor": actor, "expires": expires})

    def _verify_outputs(self, receipt):
        for a in receipt.get("artifacts", []):
            if file_digest(relative_file(self.root, a["path"])) != a["sha256"]:
                raise StateError("ARTIFACT_HASH_CHANGED")

    def _ancestors(self, stage_id, config):
        found = set()
        def visit(current):
            for dep in dependencies(current, config):
                if dep not in found:
                    found.add(dep)
                    visit(dep)
        visit(stage_id)
        return found

    def begin(self, stage_id, actor, subject_hash=None, lease_seconds=900):
        if stage_id not in BY_ID or not 1 <= lease_seconds <= 10800:
            raise StateError("STAGE_OR_LEASE_INVALID")
        with self.transaction() as c:
            run, config = self._run(c)
            self._actor(config, actor, stage_id)
            if stage_id not in config.get("stages", BY_ID):
                raise StateError("STAGE_DISABLED_IN_RUN")
            row = c.execute("SELECT * FROM stages WHERE id=?", (stage_id,)).fetchone()
            for ancestor in self._ancestors(stage_id, config):
                existing = c.execute("SELECT state,receipt FROM stages WHERE id=?", (ancestor,)).fetchone()
                if existing["state"] in SUCCESS:
                    self._verify_outputs(json.loads(existing["receipt"]))
            if row["state"] in SUCCESS:
                self._verify_outputs(json.loads(row["receipt"]))
                return {"state": row["state"], "cached": True}
            if row["state"] == "RUNNING":
                raise StateError("STAGE_RUNNING_RECOVER_EXPIRED_LEASE_FIRST")
            if row["attempt"] >= 3:
                raise StateError("RETRY_CEILING")
            failures = [json.loads(r[0]) for r in c.execute("SELECT payload FROM events")]
            matching = [e for e in failures if e.get("stage") == stage_id and e.get("kind") == "STAGE_FAILED"]
            if len(matching) >= 2 and matching[-1].get("error") == matching[-2].get("error"):
                raise StateError("REPEATED_FAILURE_DIAGNOSE_NEW_RUN")
            parents = []
            for dep in dependencies(stage_id, config):
                d = c.execute("SELECT * FROM stages WHERE id=?", (dep,)).fetchone()
                if d["state"] not in SUCCESS:
                    raise StateError("DEPENDENCY_NOT_READY:" + dep)
                receipt = json.loads(d["receipt"])
                self._verify_outputs(receipt)
                parents.append({"stage": dep, "receipt_hash": digest(receipt), "actor": d["actor"]})
            if BY_ID[stage_id].reviewer:
                for dep in self._ancestors(stage_id, config):
                    # Reusing an independent reviewer in later reviews is valid;
                    # making any underlying evidence is not.
                    d = c.execute("SELECT actor FROM stages WHERE id=?", (dep,)).fetchone()
                    if not BY_ID[dep].reviewer and d["actor"] == actor:
                        raise StateError("MAKER_CANNOT_REVIEW_OWN_OUTPUT")
            gate = BY_ID[stage_id].gate
            if gate:
                a = c.execute("SELECT * FROM approvals WHERE gate=? AND subject_hash=?", (gate, subject_hash)).fetchone()
                if not a or a["revoked"] or a["expires"] <= time.time():
                    raise StateError("EXACT_OWNER_APPROVAL_REQUIRED:" + gate)
            token = uuid.uuid4().hex
            c.execute("UPDATE stages SET state='RUNNING',actor=?,attempt=attempt+1,token=?,lease_until=?,error=NULL WHERE id=?", (actor, token, time.time()+lease_seconds, stage_id))
            self._event(c, "STAGE_STARTED", {"stage": stage_id, "actor": actor, "token": token, "config_hash": run["hash"], "parents": parents, "subject_hash": subject_hash})
            return {"state": "RUNNING", "token": token, "cached": False, "parents": parents}

    def heartbeat(self, stage_id, token, *, lease_seconds=900, progress=None):
        if not 1 <= lease_seconds <= 10800:
            raise StateError("LEASE_INVALID")
        with self.transaction() as c:
            self._run(c)
            row = c.execute("SELECT * FROM stages WHERE id=?", (stage_id,)).fetchone()
            if not row or row["state"] != "RUNNING" or row["token"] != token or row["lease_until"] <= time.time():
                raise StateError("STALE_WORKER_TOKEN_OR_LEASE")
            c.execute("UPDATE stages SET lease_until=? WHERE id=?", (time.time()+lease_seconds, stage_id))
            self._event(c, "STAGE_PROGRESS", {"stage": stage_id, "progress": progress or {}})

    def finish(self, stage_id, token, artifact_paths, result, limitations=None):
        if result not in SUCCESS or not artifact_paths:
            raise StateError("SUCCESS_REQUIRES_ARTIFACTS")
        limits = limitations or []
        if result == "PASS_WITH_LIMITATIONS" and not limits:
            raise StateError("LIMITATIONS_REQUIRED")
        artifacts = [{"path": str(p), "sha256": file_digest(relative_file(self.root, p))} for p in artifact_paths]
        with self.transaction() as c:
            run, config = self._run(c)
            row = c.execute("SELECT * FROM stages WHERE id=?", (stage_id,)).fetchone()
            if not row or row["state"] != "RUNNING" or row["token"] != token or row["lease_until"] <= time.time():
                raise StateError("STALE_WORKER_TOKEN_OR_LEASE")
            starts = [json.loads(r[0]) for r in c.execute("SELECT payload FROM events")]
            started = next((e for e in reversed(starts) if e.get("kind") == "STAGE_STARTED" and e.get("token") == token), None)
            if not started:
                raise StateError("WORKER_START_EVENT_MISSING")
            for parent in started["parents"]:
                d = c.execute("SELECT state,receipt FROM stages WHERE id=?", (parent["stage"],)).fetchone()
                if d["state"] not in SUCCESS or digest(json.loads(d["receipt"])) != parent["receipt_hash"]:
                    raise StateError("DEPENDENCY_CHANGED_DURING_WORK")
                self._verify_outputs(json.loads(d["receipt"]))
            for ancestor in self._ancestors(stage_id, config):
                existing = c.execute("SELECT state,receipt FROM stages WHERE id=?", (ancestor,)).fetchone()
                if existing["state"] not in SUCCESS:
                    raise StateError("DEPENDENCY_NOT_READY:" + ancestor)
                self._verify_outputs(json.loads(existing["receipt"]))
            gate = BY_ID[stage_id].gate
            if gate:
                approval = c.execute("SELECT * FROM approvals WHERE gate=? AND subject_hash=?", (gate, started.get("subject_hash"))).fetchone()
                if not approval or approval["revoked"] or approval["expires"] <= time.time():
                    raise StateError("EXACT_OWNER_APPROVAL_REQUIRED:" + gate)
            if BY_ID[stage_id].reviewer:
                products = []
                for a in artifacts:
                    try:
                        value = json.loads(relative_file(self.root, a["path"]).read_text())
                        if isinstance(value, dict) and value.get("schema") == "m2.independent-review.v1":
                            products.append(value)
                    except (ValueError, UnicodeError):
                        continue
                if len(products) != 1:
                    raise StateError("ONE_STRUCTURED_REVIEW_REQUIRED")
                review = products[0]
                expected = {}
                for dep in dependencies(stage_id, config):
                    d = c.execute("SELECT receipt FROM stages WHERE id=?", (dep,)).fetchone()
                    expected[dep] = digest(json.loads(d[0]))
                if (review.get("run_id") != run["id"] or review.get("config_hash") != run["hash"]
                    or review.get("reviewer") != row["actor"] or review.get("stage") != stage_id
                    or review.get("subjects") != expected):
                    raise StateError("REVIEW_SUBJECT_MISMATCH")
                if review.get("verdict") not in {"APPROVED", "APPROVED_WITH_LIMITATIONS"} or not review.get("scope"):
                    raise StateError("REVIEW_NOT_APPROVED_OR_SCOPE_MISSING")
                if review.get("verdict") == "APPROVED_WITH_LIMITATIONS" and not review.get("limitations"):
                    raise StateError("REVIEW_LIMITATIONS_REQUIRED")
                if review.get("verdict") == "APPROVED_WITH_LIMITATIONS" and (result != "PASS_WITH_LIMITATIONS" or any(v not in limits for v in review["limitations"])):
                    raise StateError("REVIEW_LIMITATIONS_MUST_PROPAGATE")
            receipt = {"schema": "m2.stage-receipt.v1", "run_id": run["id"], "config_hash": run["hash"], "stage": stage_id, "actor": row["actor"], "attempt": row["attempt"], "state": result, "artifacts": artifacts, "limitations": limits, "parents": started["parents"], "approval_subject": started.get("subject_hash")}
            c.execute("UPDATE stages SET state=?,receipt=?,token=NULL,lease_until=NULL WHERE id=?", (result, canonical(receipt), stage_id))
            self._event(c, "STAGE_COMPLETED", {"stage": stage_id, "receipt": receipt})
        return receipt

    def fail(self, stage_id, token, error, blocked="FAIL"):
        if blocked not in {"FAIL", "BLOCKED_EVIDENCE", "BLOCKED_OWNER"} or not re.fullmatch(r"[A-Z0-9_:.-]{1,120}", error):
            raise StateError("FAILURE_CODE_INVALID")
        with self.transaction() as c:
            row = c.execute("SELECT * FROM stages WHERE id=?", (stage_id,)).fetchone()
            if not row or row["state"] != "RUNNING" or row["token"] != token:
                raise StateError("STALE_WORKER_TOKEN")
            c.execute("UPDATE stages SET state=?,error=?,token=NULL,lease_until=NULL WHERE id=?", (blocked, error, stage_id))
            self._event(c, "STAGE_FAILED", {"stage": stage_id, "error": error, "state": blocked})

    def recover(self, stage_id):
        with self.transaction() as c:
            row = c.execute("SELECT * FROM stages WHERE id=?", (stage_id,)).fetchone()
            if not row or row["state"] != "RUNNING" or row["lease_until"] > time.time():
                raise StateError("LEASE_NOT_EXPIRED")
            c.execute("UPDATE stages SET state='FAIL',token=NULL,lease_until=NULL,error='WORKER_INTERRUPTED' WHERE id=?", (stage_id,))
            self._event(c, "STAGE_FAILED", {"stage": stage_id, "error": "WORKER_INTERRUPTED", "state": "FAIL"})

    def status(self):
        with closing(self._connect()) as c:
            r, config = self._run(c)
            rows = [dict(x) for x in c.execute("SELECT id,state,actor,attempt,error FROM stages")]
            return {"schema": "m2.run-status.v1", "run_id": r["id"], "config_hash": r["hash"], "stages": rows, "provider_execution": False, "hikerapi_execution": False}

    def trace(self):
        with closing(self._connect()) as c:
            return [{"sequence": r["seq"], "previous": r["previous"], "hash": r["hash"], **json.loads(r["payload"])} for r in c.execute("SELECT * FROM events ORDER BY seq")]

    def verify(self):
        previous = "0" * 64
        count = 0
        with closing(self._connect()) as c:
            self._run(c)
            for row in c.execute("SELECT * FROM events ORDER BY seq"):
                if row["previous"] != previous or row["hash"] != digest({"previous": previous, "payload": json.loads(row["payload"])}):
                    raise StateError("EVENT_CHAIN_CORRUPT")
                previous = row["hash"]
                count += 1
            for row in c.execute("SELECT receipt FROM stages WHERE receipt IS NOT NULL"):
                self._verify_outputs(json.loads(row[0]))
        return {"state": "PASS", "events": count, "head": previous}
