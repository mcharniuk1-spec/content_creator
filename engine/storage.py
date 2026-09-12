#!/usr/bin/env python3
"""Storage layer for rendered/generated video artifacts (engine/SPEC.md Phase 3;
M2Radar_Content_Engine_Full_Execution_Prompt_v4.md §83-84). Owner: production
(see engine/production.py's module docstring for the full ownership list).

Three classes:

- `LocalStorage`   copies a file into `data/renders/objects/` — the default, always
                   configured, used by tests and local development.
- `SupabaseStorage` the canonical store per §83 (Supabase Storage REST). Raises
                   `StorageNotConfigured` with a clear message whenever
                   `SUPABASE_URL`/`SUPABASE_SERVICE_KEY` are missing. Never makes a
                   real network call unless a caller supplies its own `transport`
                   or lets it fall through to the real one — tests always inject a
                   fake transport, so no test ever touches the network.
- `CloudflareDelivery` a stub for the "public preview delivery" role §84 names as the
                   only role justified by this repo's needs — it builds a URL from
                   `CF_PUBLIC_BASE_URL` when that is set and reports NOT_CONFIGURED
                   otherwise. It never uploads anything: Supabase is the canonical
                   generated-video store (§84 explicitly forbids a second one).

`record_render(con, record)` writes `data/renders/<run_id>-<card_id>.json` and, guarded,
upserts one row into a `render_records` table this module creates (columns = the
render-record schema fields, `schemas/render-record.schema.json`).

    python3 -m engine.storage status
"""
from __future__ import annotations

import abc
import json
import os
import pathlib
import shutil
import sqlite3
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.db_util import canonical_json, now  # noqa: E402

DEFAULT_SUPABASE_BUCKET = 'm2-renders'
RENDERS_DIR = ROOT / 'data' / 'renders'
LOCAL_OBJECTS_DIR = RENDERS_DIR / 'objects'

RENDER_RECORD_REQUIRED_KEYS = [
    'run_id', 'card_id', 'script_version', 'storyboard_version', 'render_version',
    'source_take_ids', 'final_object_key', 'thumbnail_key', 'duration_s',
    'render_metadata', 'qa_status', 'storage_provider', 'created_at',
]
RENDER_METADATA_REQUIRED_KEYS = ['fps', 'width', 'height', 'codec', 'remotion_version', 'edl_sha256']

_RENDER_RECORDS_DDL = """
CREATE TABLE IF NOT EXISTS render_records (
  run_id TEXT NOT NULL,
  card_id TEXT NOT NULL,
  script_version INTEGER NOT NULL,
  storyboard_version INTEGER NOT NULL,
  render_version INTEGER NOT NULL,
  source_take_ids_json TEXT,
  final_object_key TEXT NOT NULL,
  thumbnail_key TEXT,
  duration_s REAL NOT NULL,
  render_metadata_json TEXT NOT NULL,
  qa_status TEXT NOT NULL,
  storage_provider TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (run_id, card_id, render_version)
);
"""


class StorageNotConfigured(Exception):
    """Raised by a Storage implementation whenever the credentials/config it needs
    are missing. Never raised for a transient network failure — that's a plain
    exception from the transport, left uncaught so it is visible."""


class Storage(abc.ABC):
    """Provider interface every storage backend implements."""

    @abc.abstractmethod
    def put(self, local_path, key: str) -> str:
        """Store the file at `local_path` under `key`. Returns the object_key a
        `render_records` row should keep (may differ from `key`, e.g. SupabaseStorage
        returns `'<bucket>/<key>'`)."""

    @abc.abstractmethod
    def get_url(self, key: str) -> str:
        """A URL/path a human can open to review the stored object at `key`."""

    def record_render(self, con, record: dict) -> pathlib.Path:
        """Validate `record` against the render-record shape, write it to
        `data/renders/<run_id>-<card_id>.json`, and upsert one row into the
        (guarded) `render_records` table. Shared by every Storage subclass — the
        provider only differs in how `put`/`get_url` move bytes, not in how a
        completed render is recorded.
        """
        return record_render(con, record)


class LocalStorage(Storage):
    """Copies files into `data/renders/objects/`. Always CONFIGURED — no credentials,
    the default for tests and local development, and the fallback `storage_provider`
    value in a render_records row when Supabase isn't set up yet."""

    def __init__(self, root: pathlib.Path | None = None):
        self.objects_dir = (root / 'objects') if root is not None else LOCAL_OBJECTS_DIR

    def put(self, local_path, key: str) -> str:
        src = pathlib.Path(local_path)
        if not src.exists():
            raise FileNotFoundError(str(src))
        dest = self.objects_dir / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return key

    def get_url(self, key: str) -> str:
        return (self.objects_dir / key).resolve().as_uri()

    def status(self):
        return 'CONFIGURED', f'{self.objects_dir}'


def _default_supabase_transport(url: str, service_key: str, data: bytes):
    """Real network path — never invoked by tests, which always inject their own
    `transport`. Returns (http_status, body_text)."""
    req = urllib.request.Request(
        url, data=data, method='POST',
        headers={'Authorization': f'Bearer {service_key}', 'Content-Type': 'application/octet-stream'})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as exc:                       # pragma: no cover - real network only
        return exc.code, exc.read().decode('utf-8', 'replace')


class SupabaseStorage(Storage):
    """Canonical generated-video store (§83): `POST {SUPABASE_URL}/storage/v1/object/
    {bucket}/{key}` with `Authorization: Bearer {SUPABASE_SERVICE_KEY}`. Bucket
    defaults to `m2-renders` (`SUPABASE_BUCKET` overrides it). No Supabase or R2 code
    existed anywhere in this repo or in `origin/Latest` before this module — verified
    with `git grep -il "supabase\\|cloudflare\\|r2\\b" main` / `origin/Latest`: every
    hit was either documentation/config (SPEC.md, .env.example, HANDOFF_NOTES.md,
    data-lifecycle.md) or a false positive from case-insensitive matching on binary
    files (fonts, .db/.png/.pdf) and unrelated identifiers (`r2` as a local variable
    holding an R²/regression result in score.py and m2_signal/transcript_benchmark.py,
    and a test-fixture reel literally named `"R2"` in origin/Latest's recovery tests)
    — confirmed by reading each text hit directly, not just the filename list.

    `transport(url, service_key, data) -> (http_status, body_text)` is injectable so
    tests never touch the network; the default is a real (but never test-invoked)
    `urllib` POST.
    """

    def __init__(self, *, env=None, transport=None, bucket=None):
        self.env = os.environ if env is None else env
        self.transport = transport or _default_supabase_transport
        self._bucket_override = bucket

    def _config(self):
        url = self.env.get('SUPABASE_URL')
        service_key = self.env.get('SUPABASE_SERVICE_KEY')
        bucket = self._bucket_override or self.env.get('SUPABASE_BUCKET') or DEFAULT_SUPABASE_BUCKET
        missing = [name for name, val in (('SUPABASE_URL', url), ('SUPABASE_SERVICE_KEY', service_key)) if not val]
        if missing:
            raise StorageNotConfigured(
                f"Supabase storage not configured: missing {', '.join(missing)} "
                f"(set them in .env — see .env.example)")
        return url.rstrip('/'), service_key, bucket

    def status(self):
        try:
            url, _, bucket = self._config()
            return 'CONFIGURED', f'{url}/storage/v1/object/{bucket}'
        except StorageNotConfigured as exc:
            return 'NOT_CONFIGURED', str(exc)

    def put(self, local_path, key: str) -> str:
        url, service_key, bucket = self._config()
        data = pathlib.Path(local_path).read_bytes()
        endpoint = f'{url}/storage/v1/object/{bucket}/{key}'
        status, body = self.transport(endpoint, service_key, data)
        if status not in (200, 201):
            raise RuntimeError(f'Supabase upload failed: HTTP {status}: {body}')
        return f'{bucket}/{key}'

    def get_url(self, key: str) -> str:
        url, _, bucket = self._config()
        return f'{url}/storage/v1/object/public/{bucket}/{key}'


class CloudflareDelivery:
    """Stub for the one Cloudflare role this architecture actually needs (§84):
    public preview delivery of an already-Supabase-stored render, via R2/Workers or a
    CDN in front of R2 — never a second canonical video store. This class never
    uploads anything; it only turns an already-stored `key` into a public URL, and
    only once `CF_PUBLIC_BASE_URL` is configured.

    Inspected before writing this: no Cloudflare/R2 code exists anywhere in this repo
    or in `origin/Latest` today (same `git grep` check noted on SupabaseStorage) —
    this is a fresh, minimal stub, not wired to any prior implementation.
    `.env.example` currently defines `CLOUDFLARE_API_TOKEN`/`CF_R2_BUCKET` (for a
    possible future R2-API upload path) but not `CF_PUBLIC_BASE_URL`; adding it is
    noted in docs/PRODUCTION_PIPELINE.md for whoever owns `.env.example` next.
    """

    def __init__(self, env=None):
        self.env = os.environ if env is None else env

    def status(self):
        base = self.env.get('CF_PUBLIC_BASE_URL')
        if not base:
            return 'NOT_CONFIGURED', 'CF_PUBLIC_BASE_URL not set; no public delivery role configured'
        return 'CONFIGURED', base

    def public_url(self, key: str) -> str:
        base = self.env.get('CF_PUBLIC_BASE_URL')
        if not base:
            raise StorageNotConfigured('Cloudflare public delivery not configured: CF_PUBLIC_BASE_URL missing')
        return f"{base.rstrip('/')}/{key}"


# --------------------------------------------------------------------------------- #
# record_render — shared by every Storage backend
# --------------------------------------------------------------------------------- #

def _validate_render_record(record: dict) -> list[str]:
    errors = []
    for key in RENDER_RECORD_REQUIRED_KEYS:
        if key not in record:
            errors.append(f"missing required key '{key}'")
    if errors:
        return errors
    if record['storage_provider'] not in ('supabase', 'local'):
        errors.append(f"storage_provider must be 'supabase' or 'local', got {record['storage_provider']!r}")
    if record['qa_status'] not in ('PENDING', 'OK', 'FAILED'):
        errors.append(f"qa_status must be PENDING/OK/FAILED, got {record['qa_status']!r}")
    if not isinstance(record['render_metadata'], dict):
        errors.append('render_metadata must be an object')
    else:
        for key in RENDER_METADATA_REQUIRED_KEYS:
            if key not in record['render_metadata']:
                errors.append(f"render_metadata missing required key '{key}'")
    if not isinstance(record['source_take_ids'], list):
        errors.append('source_take_ids must be an array')
    return errors


def _table_exists(con, name):
    return con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _ensure_render_records_table(con):
    con.executescript(_RENDER_RECORDS_DDL)
    con.commit()


def record_render(con, record: dict) -> pathlib.Path:
    """Write `record` (schemas/render-record.schema.json shape) to
    `data/renders/<run_id>-<card_id>.json` and upsert it into the guarded
    `render_records` table (created by this function if missing — this module owns
    that table, unlike the other engine/schema.py-owned tables). Raises ValueError
    if `record` is missing a required key or has an invalid enum value; never writes
    a record it knows to be malformed.
    """
    errors = _validate_render_record(record)
    if errors:
        raise ValueError(f'invalid render record: {"; ".join(errors)}')

    RENDERS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RENDERS_DIR / f"{record['run_id']}-{record['card_id']}.json"
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')

    if con is not None:
        _ensure_render_records_table(con)
        con.execute(
            """INSERT INTO render_records
                (run_id, card_id, script_version, storyboard_version, render_version,
                 source_take_ids_json, final_object_key, thumbnail_key, duration_s,
                 render_metadata_json, qa_status, storage_provider, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(run_id, card_id, render_version) DO UPDATE SET
                 final_object_key=excluded.final_object_key, thumbnail_key=excluded.thumbnail_key,
                 duration_s=excluded.duration_s, render_metadata_json=excluded.render_metadata_json,
                 qa_status=excluded.qa_status, storage_provider=excluded.storage_provider""",
            (record['run_id'], record['card_id'], record['script_version'], record['storyboard_version'],
             record['render_version'], canonical_json(record['source_take_ids']), record['final_object_key'],
             record['thumbnail_key'], record['duration_s'], canonical_json(record['render_metadata']),
             record['qa_status'], record['storage_provider'], record['created_at']))
        con.commit()
    return out_path


# --------------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------------- #

def status(env=None) -> str:
    rows = [
        ('local', *LocalStorage().status()),
        ('supabase', *SupabaseStorage(env=env).status()),
        ('cloudflare', *CloudflareDelivery(env=env).status()),
    ]
    name_w = max(len(r[0]) for r in rows)
    state_w = max(len(r[1]) for r in rows)
    return '\n'.join(f'{name:<{name_w}}  {state:<{state_w}}  {detail}' for name, state, detail in rows)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else 'status'
    if cmd != 'status':
        print(f'usage: python3 -m engine.storage status', file=sys.stderr)
        return 2
    print(status())
    return 0


if __name__ == '__main__':
    sys.exit(main())
