"""Offline negative tests for scheduler/output and transcript gate repairs."""
import contextlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
from types import SimpleNamespace

import pytest
import cards
from engine import shortlist_adapt as sa


def transcript_db(segments, *, gate='ENGLISH_DETECTED'):
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript('''CREATE TABLE transcripts(code,lang,words,segments);
        CREATE TABLE reels(code,dur,snapshot_id); CREATE TABLE frames(code);
        CREATE TABLE language_gate(code,language,decision,observed_at);''')
    con.execute('INSERT INTO transcripts VALUES(?,?,?,?)', ('X', 'en', 30, json.dumps(segments)))
    con.execute('INSERT INTO reels VALUES(?,?,?)', ('X', 60, 1))
    con.execute('INSERT INTO frames VALUES(?)', ('X',))
    if gate:
        lang = 'hi' if gate == 'EXCLUDED_NON_ENGLISH' else 'en'
        con.execute('INSERT INTO language_gate VALUES(?,?,?,?)', ('X', lang, gate, '2026-09-14'))
    return con


@pytest.mark.parametrize('segments', [None, {}, [None], [{'s': 0, 'e': float('nan')}],
    [{'s': 0, 'e': float('inf')}], [{'s': 0, 'e': 61}], [{'s': -1, 'e': 60}],
    [{'s': 1, 'e': 0}], [{'s': True, 'e': 60}], [{'e': 60}],
    [{'s': 30, 'e': 40}, {'s': 0, 'e': 60}]])
def test_bad_timing_is_rejected(segments):
    con = transcript_db(segments)
    try:
        ev = cards.evidence(con, 'X')
        assert not ev['timing_valid'] and not ev['transcript']
        assert ev['transcript_end_ratio'] == 0
    finally:
        con.close()


def test_ratio_is_not_rounded_into_acceptance():
    con = transcript_db([{'s': 0, 'e': 53.8}])
    ev = cards.evidence(con, 'X')
    assert ev['coverage'] == 0.9  # compatibility display only
    assert ev['transcript_end_ratio'] < 0.9
    assert not ev['transcript']
    con.close()


@pytest.mark.parametrize('gate', [None, 'LANGUAGE_UNKNOWN', 'EXCLUDED_NON_ENGLISH'])
def test_old_english_text_does_not_certify_audio(gate):
    con = transcript_db([{'s': 0, 'e': 60}], gate=gate)
    ev = cards.evidence(con, 'X')
    assert not ev['language_verified'] and not ev['transcript']
    con.close()


def test_verified_english_can_pass_structural_gate():
    con = transcript_db([{'s': 0, 'e': 60}])
    ev = cards.evidence(con, 'X')
    assert ev['language_verified'] and ev['transcript']
    con.close()


def test_missing_language_table_fails_closed():
    con = transcript_db([{'s': 0, 'e': 60}])
    con.execute('DROP TABLE language_gate')
    assert not cards.evidence(con, 'X')['transcript']
    con.close()


class Job:
    def __init__(self):
        self.state = 'DONE'
    def set(self, **kw):
        self.fields = kw
    def skip(self, reason):
        self.state = 'SKIPPED'
    def retry_required(self, reason):
        self.state = 'RETRY_REQUIRED'


def setup_agent(monkeypatch, tmp_path, action):
    job = Job()
    @contextlib.contextmanager
    def fake_job(*args, **kwargs):
        yield job
    monkeypatch.setattr(sa.state, 'job', fake_job)
    monkeypatch.setattr(sa, 'OUT_DIR', tmp_path)
    monkeypatch.setattr(sa, '_prompt', lambda _: 'fixture')
    monkeypatch.setattr(sa.subprocess, 'run', action)
    return job


@pytest.mark.parametrize('payload', [None, '{', '{}', '{"code":"OTHER","analysis_version":"sa-v1"}'])
def test_exit_zero_without_valid_expected_card_fails(monkeypatch, tmp_path, payload):
    def action(*args, **kwargs):
        if payload is not None:
            (tmp_path / 'X.json').write_text(payload)
        return SimpleNamespace(returncode=0, stderr='')
    job = setup_agent(monkeypatch, tmp_path, action)
    rows = sa.run_agent(None, 'r', [{'rel': 'batch', 'codes': ['X']}], claude_path='fixture')
    assert job.state == 'RETRY_REQUIRED'
    assert rows[0]['status'] == 'FAILED' and rows[0]['valid_outputs'] == 0


def test_model_failure_and_missing_cli_are_not_success(monkeypatch, tmp_path):
    setup_agent(monkeypatch, tmp_path, lambda *a, **k: SimpleNamespace(returncode=2, stderr='fixture'))
    assert sa.run_agent(None, 'r', [{'rel': 'b', 'codes': ['X']}], claude_path='fixture')[0]['status'] == 'FAILED'
    monkeypatch.setattr(sa.shutil, 'which', lambda _: None)
    assert sa.run_agent(None, 'r', [{'rel': 'b', 'codes': ['X']}])[0]['status'] == 'BLOCKED'


def test_valid_output_completes_batch(monkeypatch, tmp_path):
    payload = dict.fromkeys(sa.SA_KEYS)
    payload.update(code='X', analysis_version='sa-v1', original={'topic': 't', 'result': {}},
                   ours=None, reject_reason='not applicable to our audience')
    assert sa.validate(payload) == []
    def action(*args, **kwargs):
        (tmp_path / 'X.json').write_text(json.dumps(payload))
        return SimpleNamespace(returncode=0, stderr='')
    job = setup_agent(monkeypatch, tmp_path, action)
    results = sa.run_agent(None, 'r', [{'rel': 'b', 'codes': ['X']}], claude_path='fixture')
    assert results[0]['status'] == 'DONE' and results[0]['valid_outputs'] == 1
    assert job.state == 'DONE'


def test_cli_propagates_incomplete_outputs(monkeypatch):
    finished = []
    monkeypatch.setattr(sa.db_util, 'connect', lambda: None)
    monkeypatch.setattr(sa.state, 'start_run', lambda *a, **k: 'r')
    monkeypatch.setattr(sa, 'export', lambda *a, **k: ('r', []))
    monkeypatch.setattr(sa, 'run_agent', lambda *a, **k: [{'status': 'FAILED', 'valid_outputs': 0}])
    monkeypatch.setattr(sa.state, 'finish_run', lambda *a: finished.append(a[2]))
    assert sa.main(['run', '--yes']) == 1
    assert finished == ['FAILED']


@pytest.mark.parametrize('mode, succeeds', [('failed', False), ('invalid', False), ('good', True)])
def test_pm_never_applies_stale_report(tmp_path, mode, succeeds):
    root = Path(__file__).resolve().parents[1]
    shutil.copy2(root / 'pm.sh', tmp_path / 'pm.sh')
    (tmp_path / 'prompts').mkdir()
    (tmp_path / 'prompts' / 'pm.md').write_text('fixture')
    (tmp_path / 'data' / 'pm').mkdir(parents=True)
    (tmp_path / 'data' / 'pm' / 'latest.md').write_text('old report')
    bin_dir = tmp_path / 'bin'; bin_dir.mkdir()
    timeout = bin_dir / 'timeout'; timeout.write_text('#!/bin/sh\nshift\nexec "$@"\n'); timeout.chmod(0o755)
    claude = bin_dir / 'claude'
    claude.write_text('''#!/usr/bin/env python3
import os,re,sys
assert sys.argv[sys.argv.index('--tools')+1] == 'Read'
assert sys.argv[sys.argv.index('--allowed-tools')+1] == 'Read'
mode=os.environ['PM_FIXTURE_MODE']
if mode=='failed': sys.exit(2)
if mode=='invalid': print('no current marker'); sys.exit(0)
prompt=sys.argv[sys.argv.index('-p')+1]
print(re.search(r'<!-- pm-run: [^ ]+ -->',prompt).group(0))
for section in ['State','Kanban drift','Rules compliance','Failures and retries','Open decisions','For Max']:
 print('## '+section)
'''); claude.chmod(0o755)
    (tmp_path / '.venv' / 'bin').mkdir(parents=True)
    apply = tmp_path / '.venv' / 'bin' / 'python'
    apply.write_text('#!/bin/sh\nprintf applied > applied-marker\n'); apply.chmod(0o755)
    env = dict(os.environ, PATH=str(bin_dir)+os.pathsep+os.environ['PATH'], PM_FIXTURE_MODE=mode)
    result = subprocess.run(['bash', str(tmp_path / 'pm.sh')], cwd=tmp_path, env=env, capture_output=True)
    assert (result.returncode == 0) is succeeds
    assert (tmp_path / 'applied-marker').exists() is succeeds
    if not succeeds:
        assert (tmp_path / 'data' / 'pm' / 'latest.md').read_text() == 'old report'
    assert not (tmp_path / 'data' / 'pm' / '.report-lock').exists()


def test_regeneration_cannot_reuse_prior_valid_bytes(monkeypatch, tmp_path):
    payload = dict.fromkeys(sa.SA_KEYS)
    payload.update(code='X', analysis_version='sa-v1', original={'topic': 't', 'result': {}},
                   ours=None, reject_reason='not applicable to our audience')
    old_bytes = json.dumps(payload).encode()
    (tmp_path / 'X.json').write_bytes(old_bytes)
    assert sa.load('X', tmp_path) is not None
    job = setup_agent(monkeypatch, tmp_path, lambda *a, **k: SimpleNamespace(returncode=0, stderr=''))
    rows = sa.run_agent(None, 'fresh-run', [{'rel': 'b', 'codes': ['X']}], claude_path='fixture')
    assert rows[0]['status'] == 'FAILED' and rows[0]['valid_outputs'] == 0
    assert job.state == 'RETRY_REQUIRED'
    assert not (tmp_path / 'X.json').exists()
    history = list((tmp_path / 'history' / 'fresh-run').glob('X-*.json'))
    assert len(history) == 1 and history[0].read_bytes() == old_bytes
