"""SQLite job escrow and side-effect seam. No live transport is wired by default.

The adapter protocol permits direct provider APIs after exact activation. Local
idempotency does not imply provider-side idempotency: uncertain submits require
reconciliation and can never be automatically re-posted.
"""
from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
import time
from copy import deepcopy
from pathlib import Path
from types import MappingProxyType
from typing import Protocol
from urllib.parse import urlparse

from .media import StudioError, object_hash


class Transport(Protocol):
    def submit(self, request: dict) -> str: ...
    def poll(self, provider_job_id: str) -> dict: ...


class DisabledTransport:
    def submit(self, request):
        raise StudioError("PROVIDER_TRANSPORT_DISABLED")

    def poll(self, provider_job_id):
        raise StudioError("PROVIDER_TRANSPORT_DISABLED")


class RunwayImageTransport:
    """Direct Runway SDK adapter; secret-bearing client is injected, never saved.

    Construct only after the activation packet is approved. All SDK submit
    retries are disabled because a timeout may already have incurred a charge.
    Reference resolver returns (bytes, mime_type) for an approved asset hash.
    This adapter supports image-conditioned video only, a deliberately bounded
    subset of the current public SDK. It never uploads creator reference reels.
    """
    def __init__(self, client, reference_resolver, *, enabled=False):
        self.enabled = enabled
        origin = urlparse(str(client.base_url))
        if origin.scheme != "https" or origin.hostname != "api.dev.runwayml.com" or origin.port not in {None, 443} or origin.username or origin.password:
            raise StudioError("UNAPPROVED_PROVIDER_ORIGIN")
        self.client = client.with_options(max_retries=0, timeout=60)
        self.references = reference_resolver

    def compile(self, request: dict) -> dict:
        validate_request(request)
        model = request["model"]
        capability = request["capability"]
        if request["provider"] != "runway" or model not in {"seedance2_5", "veo3.1", "veo3.1_fast", "gen4.5"}:
            raise StudioError("MODEL_NOT_ADMITTED")
        if capability not in {"image_to_video", "first_last_frame", "reference_to_video"}:
            raise StudioError("CAPABILITY_NOT_IMPLEMENTED")
        if model == "gen4.5" and capability != "image_to_video":
            raise StudioError("MODEL_HAS_NO_LAST_FRAME_SUPPORT")
        if capability == "reference_to_video" and (model != "seedance2_5" or not 1 <= len(request["reference_hashes"]) <= 3):
            raise StudioError("REFERENCE_MODE_NOT_ADMITTED")
        seconds = request["duration_seconds"]
        if type(seconds) is not int or (model.startswith("veo") and seconds not in {4, 6, 8}) or (model == "gen4.5" and not 2 <= seconds <= 10) or (model == "seedance2_5" and not 4 <= seconds <= 10):
            # Seedance's public model supports longer shots; this adapter
            # intentionally admits only 4–10 second inserts for bounded cost.
            raise StudioError("MODEL_DURATION_NOT_ADMITTED")
        if len(request["prompt"].encode("utf-16-le")) // 2 > 1000:
            raise StudioError("PROMPT_TOO_LONG")
        images = []
        for index, checksum in enumerate(request["reference_hashes"]):
            data, mime = self.references(checksum)
            if hashlib.sha256(data).hexdigest() != checksum or mime not in {"image/png", "image/jpeg", "image/webp"} or len(data) > 3_700_000:
                raise StudioError("REFERENCE_BYTES_NOT_APPROVED")
            image = {"uri": f"data:{mime};base64," + base64.b64encode(data).decode("ascii")}
            if capability != "reference_to_video":
                image["position"] = "first" if index == 0 else "last"
            images.append(image)
        payload = {"model": model, "prompt_image": images, "prompt_text": request["prompt"],
                   "duration": seconds, "ratio": "720:1280" if request["aspect_ratio"] == "9:16" else "1280:720"}
        if model != "gen4.5":
            payload["audio"] = False
        if "seed" in request:
            if type(request["seed"]) is not int or not 0 <= request["seed"] < 2 ** 32:
                raise StudioError("SEED_OUTSIDE_RANGE")
            payload["seed"] = request["seed"]
        return payload

    def submit(self, request: dict) -> str:
        if not self.enabled:
            raise StudioError("PROVIDER_TRANSPORT_DISABLED")
        return self.client.image_to_video.create(**self.compile(request)).id

    def poll(self, provider_job_id: str) -> dict:
        if not self.enabled:
            raise StudioError("PROVIDER_TRANSPORT_DISABLED")
        task = self.client.tasks.retrieve(provider_job_id)
        state = {"PENDING": "RUNNING", "THROTTLED": "RUNNING", "RUNNING": "RUNNING", "SUCCEEDED": "SUCCEEDED", "FAILED": "FAILED", "CANCELLED": "CANCELLED"}.get(task.status)
        if state is None:
            raise StudioError("UNKNOWN_PROVIDER_STATE")
        # Output URLs can be private/expiring. Download requires a separate
        # approved ingestion step with hash, codec and rights verification.
        return {"state": state}


def validate_request(request: dict) -> None:
    required = {"run_id", "card_id", "shot_id", "provider", "model", "capability", "prompt", "duration_seconds", "aspect_ratio", "reference_hashes", "rights_receipt_id", "approval_id", "max_cost_microusd", "capability_receipt_id"}
    if not required <= request.keys() or any(not request[k] for k in required - {"reference_hashes"}):
        raise StudioError("PROVIDER_REQUEST_INCOMPLETE")
    if type(request["max_cost_microusd"]) is not int or request["max_cost_microusd"] <= 0:
        raise StudioError("BUDGET_REQUIRED")
    if request["capability"] not in {"text_to_video", "image_to_video", "first_last_frame", "reference_to_video"}:
        raise StudioError("CAPABILITY_NOT_ADMITTED")
    if request["capability"] == "first_last_frame" and len(request["reference_hashes"]) != 2:
        raise StudioError("TWO_REFERENCE_FRAMES_REQUIRED")
    if request["capability"] == "image_to_video" and len(request["reference_hashes"]) != 1:
        raise StudioError("ONE_REFERENCE_FRAME_REQUIRED")
    if any(not isinstance(h, str) or len(h) != 64 or any(c not in "0123456789abcdef" for c in h) for h in request["reference_hashes"]):
        raise StudioError("REFERENCE_HASH_INVALID")
    if request.get("real_person_likeness", False) or request.get("voice_clone", False):
        raise StudioError("IDENTITY_GENERATION_DISABLED")
    if request["aspect_ratio"] not in {"9:16", "16:9"} or not 0 < request["duration_seconds"] <= 30:
        raise StudioError("VIDEO_PARAMETERS_INVALID")
    for key in request:
        if any(part in key.lower() for part in ("api_key", "password", "token", "cookie", "authorization")):
            raise StudioError("SECRET_FIELD_FORBIDDEN")


class ProviderJobs:
    def __init__(self, path: Path, *, budget_microusd: int, transport: Transport | None = None, activation: dict | None = None):
        if type(budget_microusd) is not int or budget_microusd < 0:
            raise StudioError("INVALID_RUN_BUDGET")
        self.db = sqlite3.connect(path, isolation_level=None, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, request TEXT NOT NULL, state TEXT NOT NULL, reserved INTEGER NOT NULL, actual INTEGER, provider_job TEXT, polls INTEGER NOT NULL DEFAULT 0, next_poll REAL, failure TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK(id=1), budget INTEGER NOT NULL)")
        self.db.execute("INSERT OR IGNORE INTO settings VALUES (1,?)", (budget_microusd,))
        if self.db.execute("SELECT budget FROM settings").fetchone()[0] != budget_microusd:
            raise StudioError("BUDGET_IMMUTABLE_NEW_LEDGER_REQUIRED")
        self.transport = transport or DisabledTransport()
        # Snapshot the approved envelope. A caller mutating the original list
        # after construction must not broaden a running worker's authorization.
        approved = deepcopy(activation or {})
        self.activation = MappingProxyType({key: tuple(value) if isinstance(value, list) else value for key, value in approved.items()})

    def close(self):
        self.db.close()

    def get(self, job_id):
        row = self.db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            raise StudioError("JOB_NOT_FOUND")
        return dict(row)

    def plan(self, request: dict) -> dict:
        validate_request(request)
        job_id = object_hash(request)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            existing = self.db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if existing:
                self.db.commit()
                return dict(existing)
            held = self.db.execute("SELECT COALESCE(SUM(COALESCE(actual,reserved)),0) FROM jobs").fetchone()[0]
            ceiling = self.db.execute("SELECT budget FROM settings").fetchone()[0]
            if held + request["max_cost_microusd"] > ceiling:
                raise StudioError("RUN_BUDGET_EXCEEDED")
            self.db.execute("INSERT INTO jobs(id,request,state,reserved) VALUES(?,?,?,?)", (job_id, json.dumps(request, sort_keys=True), "PLANNED", request["max_cost_microusd"]))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self.get(job_id)

    def _admit(self, request: dict, *, expected_job_id: str):
        a = self.activation
        if a.get("enabled") is not True or a.get("expires_at_epoch", 0) <= time.time() or isinstance(self.transport, DisabledTransport):
            raise StudioError("PROVIDER_EXECUTION_DISABLED")
        # Recompute from the stored full request at every side-effect boundary.
        # Never treat approval_id, model choice, or a caller-supplied job ID as
        # approval of new prompt/reference/rights/parameter values.
        request_digest = object_hash(request)
        if request_digest != expected_job_id:
            raise StudioError("JOB_REQUEST_HASH_MISMATCH")
        approved_digests = a.get("approved_request_hashes", ())
        if (not isinstance(approved_digests, tuple) or not approved_digests
                or any(not isinstance(h, str) or len(h) != 64 or any(c not in "0123456789abcdef" for c in h) for h in approved_digests)
                or request_digest not in approved_digests):
            raise StudioError("PROVIDER_REQUEST_NOT_APPROVED")
        if a.get("approval_id") != request["approval_id"] or request["model"] not in a.get("models", []) or request["provider"] != a.get("provider") or request["capability_receipt_id"] != a.get("capability_receipt_id"):
            raise StudioError("PROVIDER_APPROVAL_MISMATCH")
        if request["capability"] not in a.get("capabilities", []) or request["max_cost_microusd"] > a.get("max_job_cost_microusd", 0):
            raise StudioError("PROVIDER_CAPABILITY_OR_BUDGET_BLOCKED")

    def submit(self, job_id: str) -> dict:
        row = self.get(job_id)
        self._admit(json.loads(row["request"]), expected_job_id=row["id"])
        changed = self.db.execute("UPDATE jobs SET state='SUBMITTING' WHERE id=? AND state='PLANNED'", (job_id,)).rowcount
        if not changed:
            # A previous process can have crashed after provider acceptance but
            # before saving its ID. SUBMITTING is also an ambiguous state.
            if row["state"] in {"SUBMITTING", "SUBMIT_UNKNOWN"}:
                raise StudioError("AMBIGUOUS_SUBMIT_RECONCILIATION_REQUIRED")
            return self.get(job_id)
        try:
            provider_id = self.transport.submit(json.loads(row["request"]))
            if not isinstance(provider_id, str) or not provider_id:
                raise StudioError("MISSING_PROVIDER_JOB_ID")
        except Exception:
            self.db.execute("UPDATE jobs SET state='SUBMIT_UNKNOWN',failure='SUBMIT_OUTCOME_UNKNOWN' WHERE id=?", (job_id,))
            return self.get(job_id)
        self.db.execute("UPDATE jobs SET state='SUBMITTED',provider_job=?,next_poll=? WHERE id=?", (provider_id, time.time() + 10, job_id))
        return self.get(job_id)

    def poll(self, job_id: str, *, now: float | None = None, max_polls=120) -> dict:
        row = self.get(job_id)
        self._admit(json.loads(row["request"]), expected_job_id=row["id"])
        now = time.time() if now is None else now
        if row["state"] not in {"SUBMITTED", "RUNNING"}:
            return row
        if row["polls"] >= max_polls:
            self.db.execute("UPDATE jobs SET state='POLL_EXHAUSTED',failure='RECONCILIATION_REQUIRED' WHERE id=?", (job_id,))
            return self.get(job_id)
        if now < row["next_poll"]:
            raise StudioError("POLL_TOO_EARLY")
        # Claim poll before side effect; crashes cannot create rapid retry storms.
        next_poll = now + min(60, 10 * 2 ** min(row["polls"], 3))
        changed = self.db.execute("UPDATE jobs SET polls=polls+1,next_poll=? WHERE id=? AND polls=?", (next_poll, job_id, row["polls"])).rowcount
        if not changed:
            raise StudioError("POLL_ALREADY_CLAIMED")
        try:
            status = self.transport.poll(row["provider_job"]).get("state")
            if status not in {"RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"}:
                raise StudioError("UNKNOWN_PROVIDER_STATE")
            self.db.execute("UPDATE jobs SET state=? WHERE id=?", (status, job_id))
        except Exception:
            self.db.execute("UPDATE jobs SET failure='POLL_RETRYABLE' WHERE id=?", (job_id,))
        return self.get(job_id)

    def reconcile(self, job_id: str, *, provider_job_id: str, actual_microusd: int, outcome: str, receipt_id: str) -> dict:
        if type(actual_microusd) is not int or actual_microusd < 0 or outcome not in {"SUCCEEDED", "FAILED", "CANCELLED"} or not receipt_id or not provider_job_id:
            raise StudioError("RECONCILIATION_RECEIPT_REQUIRED")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.get(job_id)
            if row["state"] == "PLANNED":
                raise StudioError("UNSUBMITTED_JOB_CANNOT_RECONCILE")
            if row["provider_job"] and row["provider_job"] != provider_job_id:
                raise StudioError("PROVIDER_JOB_ID_MISMATCH")
            if row["actual"] is not None:
                if row["actual"] != actual_microusd or row["state"] != outcome:
                    raise StudioError("RECONCILIATION_CONFLICT")
                self.db.commit()
                return row
            # Record real overspend truthfully; subsequent plans fail budget checks.
            self.db.execute("UPDATE jobs SET actual=?,state=?,provider_job=?,failure=? WHERE id=? AND actual IS NULL", (actual_microusd, outcome, provider_job_id, "BUDGET_OVERRUN" if actual_microusd > row["reserved"] else None, job_id))
            self.db.execute("CREATE TABLE IF NOT EXISTS reconciliations (job_id TEXT PRIMARY KEY, receipt_id TEXT NOT NULL)")
            self.db.execute("INSERT OR IGNORE INTO reconciliations VALUES (?,?)", (job_id, receipt_id))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self.get(job_id)
