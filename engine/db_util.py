"""Connection and small value helpers shared by every engine module.

`connect()` deliberately reuses `db.connect` so that a single code path creates
the legacy schema, applies the legacy `ADDED` columns and sets the same
pragmas. The engine never opens the database any other way.
"""
import json
import os
import pathlib
import sqlite3
import sys
import uuid
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:                      # `python3 -m engine.x` from any cwd
    sys.path.insert(0, str(ROOT))

import db as legacy_db                             # noqa: E402  (path set above)

DB_PATH = legacy_db.DB_PATH


def connect(path=None, wal=False):
    """Open the radar database with the legacy semantics.

    row_factory = sqlite3.Row, foreign keys on, legacy schema ensured.
    `wal` is opt-in: switching the journal mode is a persistent change to the
    file, and the production database is left in whatever mode it already has.
    """
    path = str(path or DB_PATH)
    con = legacy_db.connect(path)                  # Row factory + SCHEMA + ADDED columns
    con.execute('PRAGMA foreign_keys = ON')        # re-assert: executescript may drop it
    if wal:
        con.execute('PRAGMA journal_mode = WAL')
    return con


def now():
    """ISO-8601 UTC, second resolution, no microseconds. Sortable as text."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def canonical_json(obj):
    """Canonical JSON for every `*_json` column: sorted keys, compact, unicode kept.

    None stays None so that a column can honestly be NULL rather than 'null'.
    """
    if obj is None:
        return None
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def loads(raw, default=None):
    """Forgiving JSON read for columns written by older code."""
    if raw is None or raw == '':
        return default
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return default


def new_id(prefix=''):
    """uuid4 hex, optionally prefixed (`job_id`, `insight_id`, …)."""
    return f'{prefix}{uuid.uuid4().hex}' if prefix else uuid.uuid4().hex


def table_exists(con, name):
    return con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def columns(con, table):
    """Column names of `table`, empty set when the table does not exist."""
    return {r[1] for r in con.execute(f'PRAGMA table_info({table})')}


def table_names(con):
    return [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name")]


def row_counts(con, tables=None):
    """{table: rows} for the given tables (default: all)."""
    out = {}
    for t in (tables if tables is not None else table_names(con)):
        try:
            out[t] = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        except sqlite3.Error:
            out[t] = None
    return out


def git_commit():
    """Short commit of the checkout, read straight from .git — never runs git."""
    try:
        head = (ROOT / '.git' / 'HEAD').read_text().strip()
        if head.startswith('ref:'):
            ref = head.split(' ', 1)[1].strip()
            p = ROOT / '.git' / ref
            if p.exists():
                return p.read_text().strip()[:12]
            packed = ROOT / '.git' / 'packed-refs'
            if packed.exists():
                for line in packed.read_text().splitlines():
                    if line.endswith(' ' + ref):
                        return line.split(' ', 1)[0][:12]
            return None
        return head[:12]
    except OSError:
        return None


def env_present(name):
    """True when a credential is configured — presence only, value never read out.

    Two sources, matching `lib/hiker.py`: the process environment and the
    project `.env`. The value is compared against the empty string and then
    dropped; it is never returned, logged or stored.
    """
    if os.environ.get(name):
        return True
    env = ROOT / '.env'
    try:
        for line in env.read_text().splitlines():
            if line.startswith(f'{name}=') and line.split('=', 1)[1].strip():
                return True
    except OSError:
        pass
    return False
