import os
import json
import sqlite3
import time
import sys
from pathlib import Path

import pytest

from m2_orchestrator import media_acquisition as m
from m2_orchestrator import public_media
from m2_orchestrator.process_budget import bounded_process


def media_manifest(source):
    return {
        'entries': [
            {
                'reel_id': 'instagram:ABC12',
                'code': 'ABC12',
                'sources': [source],
                'quarantine_reasons': [],
            }
        ]
    }


def test_worker_lock_exclusion(tmp_path, monkeypatch):
    def locked(*_args, **_kwargs):
        raise BlockingIOError

    monkeypatch.setattr(m.fcntl, 'flock', locked)

    with pytest.raises(m.AcquisitionError, match='WORKER_ALREADY_RUNNING'):
        m.acquire({'entries': []}, tmp_path / 'run')


def test_interrupted_attempt_resume_and_retry_ceiling(tmp_path, monkeypatch):
    def fail_download(*_args, **_kwargs):
        raise m.AcquisitionError('NETWORK_FAILURE')

    source = {'route': 'explicit_url', 'url': 'https://cdninstagram.com/edge.mp4'}
    manifest = media_manifest(source)
    root = tmp_path / 'run'
    max_attempts = 2

    monkeypatch.setattr(m, 'download', fail_download)
    first = m.acquire(manifest, root, network=True, max_attempts=max_attempts, probe_fn=lambda _: {'has_audio': True})
    assert first['states']['RETRYABLE'] == 1

    route_hash = m.stable_hash(source)
    with sqlite3.connect(root / 'acquisition.sqlite') as db:
        first_attempt_id = db.execute("SELECT MIN(id) FROM attempts").fetchone()[0]
        db.execute("UPDATE attempts SET state='RUNNING' WHERE id=?", (first_attempt_id,))
        now = time.time()
        db.execute(
            "INSERT INTO attempts (reel_id, route_hash, route, attempt, state, error, started, finished) VALUES (?,?,?,?,?,?,?,?)",
            ('instagram:ABC12', route_hash, 'explicit_url', 2, 'FAILED', 'SIMULATED_INTERRUPT', now, now),
        )
        db.commit()

    blocked = []

    def blocked_download(*_args, **_kwargs):
        blocked.append(1)
        raise RuntimeError('should_not_run')

    monkeypatch.setattr(m, 'download', blocked_download)

    resumed = m.acquire(manifest, root, network=True, max_attempts=max_attempts, probe_fn=lambda _: {'has_audio': True})
    assert resumed['states']['UNAVAILABLE'] == 1
    assert blocked == []

    with sqlite3.connect(root / 'acquisition.sqlite') as db:
        failed = db.execute("SELECT state, error FROM attempts WHERE id=?", (first_attempt_id,)).fetchone()
        total = db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]

    assert total == 2
    assert failed == ('FAILED', 'WORKER_INTERRUPTED')


def test_symlinked_output_artifact_is_rejected(tmp_path):
    root = tmp_path / 'run'
    root.mkdir()
    (tmp_path / 'target.json').write_text('target', encoding='utf-8')
    os.symlink(tmp_path / 'target.json', root / 'summary.json')

    with pytest.raises(m.AcquisitionError, match='OUTPUT_SYMLINK'):
        m.acquire({'entries': []}, root)


def test_malformed_source_shape_records_key_error_and_continues(tmp_path):
    media = tmp_path / 'media.mp4'
    media.write_bytes(b'x')

    manifest = media_manifest({'route': 'existing_media', 'path': str(media)})
    result = m.acquire(manifest, tmp_path / 'run', media_roots=[tmp_path], probe_fn=lambda _: {'has_audio': True})

    assert result['states'] == {'UNAVAILABLE': 1}

    with sqlite3.connect(tmp_path / 'run' / 'acquisition.sqlite') as db:
        row = db.execute("SELECT state, error FROM attempts").fetchone()

    assert row[0] == 'FAILED'
    assert row[1] == 'KeyError'


def test_public_resolver_requires_bound_executable(tmp_path):
    manifest = media_manifest({'route': 'public_reel'})
    root = tmp_path / 'run'
    result = m.acquire(
        manifest,
        root,
        network=True,
        resolver_executable='yt-dlp',
        resolver_sha256='00' * 32,
        probe_fn=lambda _: {'has_audio': True},
    )

    assert result['states']['UNAVAILABLE'] == 1
    with sqlite3.connect(root / 'acquisition.sqlite') as db:
        error = db.execute("SELECT error FROM attempts").fetchone()[0]

    assert error == 'EXTRACTOR_IDENTITY_REQUIRED'


def test_public_resolver_executable_hash_must_bind(tmp_path):
    resolver = tmp_path / 'resolver'
    resolver.write_text('#!/usr/bin/env python', encoding='utf-8')

    with pytest.raises(m.AcquisitionError, match='EXTRACTOR_IDENTITY_CHANGED'):
        public_media.resolve_public(
            'ABC12',
            tmp_path / 'evidence',
            executable=str(resolver),
            expected_sha256='00' * 32,
        )


def test_bounded_process_preserves_fake_venv_executable_prefix(tmp_path):
    venv_root = tmp_path / 'fake_venv'
    bindir = venv_root / 'bin'
    bindir.mkdir(parents=True)
    (venv_root / 'pyvenv.cfg').write_text('home = ' + str(Path(sys.executable).parent) + '\n', encoding='utf-8')
    executable = bindir / 'python'
    executable.symlink_to(Path(sys.executable))

    probe = (
        'import json,sys; '
        "print(json.dumps({"
        '"executable": sys.executable, '
        '"prefix": sys.prefix, '
        '"base_prefix": sys.base_prefix} ))'
    )
    result = bounded_process([str(executable), '-c', probe], timeout=5, stdout_limit=64_000)

    decoded = result['stdout'].decode('utf-8').strip()
    data = json.loads(decoded)
    assert data['executable'] == str(executable)
    assert data['prefix'].startswith(str(venv_root))
    assert data['base_prefix'] != data['prefix']
