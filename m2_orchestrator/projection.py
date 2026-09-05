"""Provider-free projection outbox with conflict and readback handling.

The Codex operator executes staged actions using the connected Notion MCP.
The module never discovers credentials or silently falls back to a browser.
"""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .state import StateError, canonical, digest

OWNER_FIELDS = {"Status", "Lead", "Priority", "Owner note", "Decision", "Presenter"}


def equivalent(a, b):
    # Notion may serialize an integer NUMBER as 1.0. Preserve null/type semantics.
    # Notion stores an empty rich-text array as SQL NULL on readback.
    if a in (None, "") and b in (None, ""):
        return True
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(equivalent(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(equivalent(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b


def projection_key(release_id, object_id, projection_version="m2.notion.v1"):
    return digest([release_id, projection_version, object_id])


def plan(release_id, object_id, desired, existing=None, previous_engine_fields=None):
    """Update only engine-owned fields; preserve newer human edits as conflicts."""
    if not release_id or not object_id or not isinstance(desired, dict):
        raise StateError("PROJECTION_ID_OR_PROPERTIES_INVALID")
    # Initial cards may set Proposed; updates may never write owner fields.
    if existing is not None and set(desired) & OWNER_FIELDS:
        raise StateError("OWNER_FIELDS_PROTECTED")
    conflicts = []
    previous = previous_engine_fields or {}
    if existing is not None:
        for key in desired:
            if key not in previous and key in existing and existing[key] not in (None, ""):
                conflicts.append(key)
            elif key in previous and existing.get(key) != previous[key] and existing.get(key) != desired[key]:
                conflicts.append(key)
    return {"schema": "m2.projection-action.v1", "key": projection_key(release_id, object_id),
            "release_id": release_id, "object_id": object_id, "desired": desired,
            "desired_hash": digest(desired), "before_hash": digest(existing) if existing is not None else None,
            "operation": "create" if existing is None else "update", "state": "CONFLICT" if conflicts else "STAGED",
            "conflicts": conflicts}


class Outbox:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as c:
            c.execute("CREATE TABLE IF NOT EXISTS projection_jobs(key TEXT PRIMARY KEY,payload TEXT NOT NULL,state TEXT NOT NULL,target TEXT,readback_hash TEXT)")

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.path, timeout=10)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    def stage(self, action):
        with self.connect() as c:
            old = c.execute("SELECT * FROM projection_jobs WHERE key=?", (action["key"],)).fetchone()
            if old:
                if old["payload"] != canonical(action):
                    raise StateError("PROJECTION_KEY_PAYLOAD_CONFLICT")
                return old["state"]
            c.execute("INSERT INTO projection_jobs(key,payload,state) VALUES(?,?,?)", (action["key"], canonical(action), action["state"]))
            return action["state"]

    def dispatch(self, key, current=None):
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT * FROM projection_jobs WHERE key=?", (key,)).fetchone()
            if not row or row["state"] != "STAGED":
                raise StateError("PROJECTION_NOT_STAGED_RECONCILE_UNCERTAIN_FIRST")
            action = json.loads(row["payload"])
            if action["operation"] == "update" and digest(current) != action["before_hash"]:
                raise StateError("PROJECTION_TARGET_CHANGED")
            c.execute("UPDATE projection_jobs SET state='SENDING' WHERE key=?", (key,))
            return action

    def uncertain(self, key):
        with self.connect() as c:
            changed = c.execute("UPDATE projection_jobs SET state='UNCERTAIN' WHERE key=? AND state='SENDING'", (key,)).rowcount
            if changed != 1:
                raise StateError("PROJECTION_NOT_SENDING")

    def verify(self, key, target, properties):
        if not target:
            raise StateError("PROJECTION_TARGET_REQUIRED")
        with self.connect() as c:
            row = c.execute("SELECT * FROM projection_jobs WHERE key=?", (key,)).fetchone()
            if not row or row["state"] not in {"SENDING", "UNCERTAIN", "VERIFIED"}:
                raise StateError("PROJECTION_READBACK_STATE_INVALID")
            desired = json.loads(row["payload"])["desired"]
            actual = {k: properties.get(k) for k in desired}
            if not equivalent(actual, desired):
                raise StateError("PROJECTION_READBACK_MISMATCH")
            if row["target"] and row["target"] != target:
                raise StateError("PROJECTION_TARGET_ID_CHANGED")
            h = digest(actual)
            c.execute("UPDATE projection_jobs SET state='VERIFIED',target=?,readback_hash=? WHERE key=?", (target, h, key))
            return {"key": key, "state": "VERIFIED", "readback_hash": h}

    def summary(self):
        with self.connect() as c:
            counts = dict(c.execute("SELECT state,count(*) FROM projection_jobs GROUP BY state"))
        return {"counts": counts, "complete": bool(counts) and set(counts) == {"VERIFIED"}}

