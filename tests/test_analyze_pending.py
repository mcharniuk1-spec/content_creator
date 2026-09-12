"""Tests for engine/analyze_pending.py.

Self-contained: every test builds a fresh SQLite file from `db.SCHEMA` +
`engine.schema.migrate` (same pattern as tests/test_engine_schema.py) and monkeypatches
`engine.analyze_pending.TA_DIR` / `FA_DIR` / `WARN_PATH` / `LOCK_PATH` to tmp_path, so
nothing here ever reads or writes the real `data/analysis/*` directories.

Nothing here calls the real `claude` CLI: the agent-launch branch is only exercised
with `shutil.which` monkeypatched to return `None` (the NOT_CONFIGURED path), which
never reaches `subprocess.run`.

    python3 -m pytest tests/test_analyze_pending.py -q
"""
import json
import pathlib
import sqlite3
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import db as legacy_db                                            # noqa: E402
from engine import analyze_pending as ap                          # noqa: E402
from engine import schema                                         # noqa: E402
from engine.db_util import canonical_json                         # noqa: E402

TA_ITEM_KEYS = {'code', 'username', 'url', 'dur', 'play', 'likes', 'comm', 'resh', 'save',
                'author_median_play', 'z', 'resh_1k', 'save_1k', 'caption', 'topics', 'words',
                'segments'}
FA_ITEM_KEYS = {'code', 'username', 'dur', 'play', 'caption', 'has_transcript', 'sheet', 'frames'}
FA_FRAME_KEYS = {'idx', 't', 'path', 'exists'}


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #

def _blank(tmp_path):
    con = sqlite3.connect(tmp_path / 'test.db')
    con.row_factory = sqlite3.Row
    con.executescript(legacy_db.SCHEMA)
    con.commit()
    schema.migrate(con)
    return con


def _reel(con, code, sid=1, pk=11, user='alice', play=1000, cap='caption text', dur=20.0):
    con.execute('INSERT INTO reels (snapshot_id, code, pk_user, username, ts, kind, play, likes, '
                'comm, resh, save, dur, cap, followers) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (sid, code, pk, user, 1760000000, 'clip', play, 20, 3, 5, 8, dur, cap, 4000))


def _segs():
    return canonical_json([{'s': 0.0, 'e': 2.0, 't': 'hello there'},
                           {'s': 2.0, 'e': 4.5, 't': 'and the point of this'}])


@pytest.fixture()
def con(tmp_path):
    c = _blank(tmp_path)
    c.execute("INSERT INTO snapshots (id, taken, done) VALUES (1,'2026-09-01',1)")
    c.execute("INSERT INTO accounts (pk, username, tag, status) VALUES (11,'alice','core','active')")

    # --- transcripts side ---------------------------------------------------
    # TAPEND01: usable transcript, no beats yet, no json on disk -> needs export
    _reel(c, 'TAPEND01')
    c.execute("INSERT INTO transcripts (code, lang, words, text, segments) "
              "VALUES ('TAPEND01','en',7,'hello there and the point of this',?)", (_segs(),))

    # TADONE01: usable transcript, already has a beats row -> not pending
    _reel(c, 'TADONE01')
    c.execute("INSERT INTO transcripts (code, lang, words, text, segments) "
              "VALUES ('TADONE01','en',7,'hello there and the point of this',?)", (_segs(),))
    c.execute("INSERT INTO beats (beat_id, code, idx, role, start_s, end_s, text, analysis_version) "
              "VALUES ('B-TADONE01','TADONE01',0,'hook',0.0,2.0,'hello there','ta-v1')")

    # TAEMPTY1: words=0 (no usable speech) -> never pending
    _reel(c, 'TAEMPTY1')
    c.execute("INSERT INTO transcripts (code, lang, words, text, segments) "
              "VALUES ('TAEMPTY1','en',0,'','[]')")

    # TAJSON01: usable transcript, no beats row, but a ta-v1 json already sits on
    # disk (placed directly in the monkeypatched TA_DIR by the ingest test below)
    _reel(c, 'TAJSON01')
    c.execute("INSERT INTO transcripts (code, lang, words, text, segments) "
              "VALUES ('TAJSON01','en',9,'hello there and the point of this now',?)", (_segs(),))

    # --- frames side ----------------------------------------------------------
    for code in ('FRPEND01', 'FRDONE01', 'FRNOSHEET1'):
        _reel(c, code)
        for i in range(3):
            c.execute('INSERT INTO frames (code, idx, t_sec, path, exists_ok) VALUES (?,?,?,?,1)',
                      (code, i, 0.4 * (i + 1), f'data/frames/{code}/{i:02d}.jpg'))

    c.execute("INSERT INTO topics (code, topic, source) VALUES ('TAPEND01','AI tools','sample')")
    c.commit()
    yield c
    c.close()


@pytest.fixture()
def paths(tmp_path, monkeypatch):
    """Redirects every path engine.analyze_pending touches to tmp_path, and returns
    the pieces a test needs (ta_dir, fa_dir, input_dir)."""
    ta_dir = tmp_path / 'analysis' / 'transcripts'
    fa_dir = tmp_path / 'analysis' / 'frames'
    ta_dir.mkdir(parents=True)
    fa_dir.mkdir(parents=True)
    monkeypatch.setattr(ap, 'TA_DIR', ta_dir)
    monkeypatch.setattr(ap, 'FA_DIR', fa_dir)
    monkeypatch.setattr(ap, 'WARN_PATH', tmp_path / 'ingest_warnings.md')
    monkeypatch.setattr(ap, 'LOCK_PATH', tmp_path / 'analyze.lock')
    input_dir = tmp_path / 'analysis' / 'input'
    return {'ta_dir': ta_dir, 'fa_dir': fa_dir, 'input_dir': input_dir}


def _make_sheet(con, code, tmp_path, exists=True):
    """Wires up a deepdives.sheet row for `code`, optionally pointing at a real file."""
    sheet_path = tmp_path / 'frames' / f'{code}_sheet.jpg'
    if exists:
        sheet_path.parent.mkdir(parents=True, exist_ok=True)
        sheet_path.write_bytes(b'\xff\xd8\xff')
    con.execute("INSERT INTO deepdives (code, snapshot_id, sheet, done_at) VALUES (?,1,?,'2026-09-10')",
                (code, str(sheet_path)))
    con.commit()
    return sheet_path


# --------------------------------------------------------------------------- #
# pending selection
# --------------------------------------------------------------------------- #

def test_select_transcript_pending(con):
    pending = ap.select_transcript_pending(con)
    assert 'TAPEND01' in pending
    assert 'TAJSON01' in pending
    assert 'TADONE01' not in pending      # already has beats
    assert 'TAEMPTY1' not in pending      # words=0, not usable


def test_select_frame_pending_requires_sheet_on_disk(con, tmp_path):
    _make_sheet(con, 'FRPEND01', tmp_path, exists=True)
    _make_sheet(con, 'FRNOSHEET1', tmp_path, exists=False)   # row exists, file does not
    con.execute("INSERT INTO frame_labels (code, idx, t_sec, frame_type, roll, analysis_version) "
                "VALUES ('FRDONE01',0,0.4,'A_ROLL_CLOSE_UP','A','fa-v1')")
    con.commit()

    pending = ap.select_frame_pending(con)
    assert 'FRPEND01' in pending
    assert 'FRDONE01' not in pending      # already labelled
    assert 'FRNOSHEET1' not in pending    # sheet row exists but file is missing


def test_select_pending_prints_counts(con, tmp_path, capsys):
    _make_sheet(con, 'FRPEND01', tmp_path, exists=True)
    ta, fa = ap.select_pending(con)
    assert set(ta) >= {'TAPEND01', 'TAJSON01'}
    assert 'FRPEND01' in fa


# --------------------------------------------------------------------------- #
# batch export format
# --------------------------------------------------------------------------- #

def test_transcript_export_item_matches_existing_batch_format(con):
    item = ap._export_transcript_item(con, 'TAPEND01')
    assert set(item.keys()) == TA_ITEM_KEYS

    existing = json.loads((ROOT / 'data' / 'analysis' / 'input' / 'transcripts-batch-1.json')
                          .read_text(encoding='utf-8'))
    assert set(existing[0].keys()) == TA_ITEM_KEYS
    assert item['code'] == 'TAPEND01'
    assert item['url'] == 'https://www.instagram.com/reel/TAPEND01/'
    assert item['words'] == 7
    assert isinstance(item['segments'], list) and item['segments'][0]['t'] == 'hello there'
    assert item['topics'] == ['AI tools']


def test_frame_export_item_matches_existing_batch_format(con, tmp_path):
    _make_sheet(con, 'FRPEND01', tmp_path, exists=True)
    item = ap._export_frame_item(con, 'FRPEND01')
    assert set(item.keys()) == FA_ITEM_KEYS
    assert len(item['frames']) == 3
    assert set(item['frames'][0].keys()) == FA_FRAME_KEYS
    assert item['frames'][0]['exists'] is False   # frames.path here points nowhere real
    assert item['has_transcript'] is False         # FRPEND01 has no transcripts row

    existing = json.loads((ROOT / 'data' / 'analysis' / 'input' / 'frames-batch-1.json')
                          .read_text(encoding='utf-8'))
    assert set(existing[0].keys()) == FA_ITEM_KEYS
    assert set(existing[0]['frames'][0].keys()) == FA_FRAME_KEYS


def test_export_batches_writes_files_and_chunks(con, paths):
    batches = ap.export_batches(con, ap.KIND_TA, ['TAPEND01', 'TAJSON01'], batch_size=1,
                                run_id='TESTRUN', input_dir=paths['input_dir'])
    assert len(batches) == 2   # batch_size=1 -> one file per code
    for b in batches:
        assert b['path'].exists()
        data = json.loads(b['path'].read_text(encoding='utf-8'))
        assert len(data) == 1
        assert set(data[0].keys()) == TA_ITEM_KEYS


# --------------------------------------------------------------------------- #
# --dry writes nothing
# --------------------------------------------------------------------------- #

def test_dry_run_writes_nothing(con, paths, tmp_path):
    _make_sheet(con, 'FRPEND01', tmp_path, exists=True)
    beats_before = con.execute('SELECT COUNT(*) FROM beats').fetchone()[0]
    jobs_before = con.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]

    summary = ap.run(con, dry=True, yes=True, input_dir=paths['input_dir'])

    assert summary['dry_run'] is True
    assert summary['ta_needs_export'] >= 2
    assert not paths['input_dir'].exists() or not list(paths['input_dir'].glob('*'))
    assert not ap.LOCK_PATH.exists()
    assert con.execute('SELECT COUNT(*) FROM beats').fetchone()[0] == beats_before
    assert con.execute('SELECT COUNT(*) FROM jobs').fetchone()[0] == jobs_before
    assert con.execute('SELECT COUNT(*) FROM runs').fetchone()[0] == 0


# --------------------------------------------------------------------------- #
# NOT_CONFIGURED when claude is absent
# --------------------------------------------------------------------------- #

def test_not_configured_when_claude_missing(con, paths, monkeypatch, capsys):
    monkeypatch.setattr(ap.shutil, 'which', lambda name: None)

    summary = ap.run(con, dry=False, yes=True, input_dir=paths['input_dir'])

    out = capsys.readouterr().out
    assert 'NOT_CONFIGURED' in out
    assert summary['ta_needs_export'] >= 1
    assert len(summary['ta_batches']) >= 1

    rows = con.execute("SELECT state, stage, agent, prompt_version FROM jobs "
                       "WHERE stage='TRANSCRIPT_ANALYSIS'").fetchall()
    assert rows, 'expected one jobs row per exported transcript batch'
    assert all(r['state'] == 'SKIPPED' for r in rows)
    assert all(r['agent'] == 'claude -p' for r in rows)
    assert all(r['prompt_version'] == 'ta-v1' for r in rows)


def test_no_yes_exports_but_does_not_touch_agent(con, paths, monkeypatch):
    """Without --yes the batches are still written (free, local) but no jobs row is
    recorded for the agent step at all — it was never attempted."""
    called = []
    monkeypatch.setattr(ap, '_run_agent_job', lambda *a, **k: called.append(a))
    monkeypatch.setattr(ap, '_skip_agent_job', lambda *a, **k: called.append(a))

    summary = ap.run(con, dry=False, yes=False, input_dir=paths['input_dir'])

    assert summary['ta_batches'], 'batches should still be exported without --yes'
    assert called == []
    assert con.execute("SELECT COUNT(*) FROM jobs WHERE stage='TRANSCRIPT_ANALYSIS'").fetchone()[0] == 0


# --------------------------------------------------------------------------- #
# ingest path: a fixture ta-v1 JSON already on disk -> beats rows present
# --------------------------------------------------------------------------- #

TA_FIXTURE = {
    'code': 'TAJSON01', 'analysis_version': 'ta-v1', 'model': 'test-model', 'language': 'en',
    'beats': [
        {'idx': 0, 'role': 'hook', 'start_s': 0.0, 'end_s': 2.0, 'text': 'hello there',
         'segment_idx': [0], 'audience_function': 'grab attention', 'emotion': 'neutral',
         'intention': 'hook', 'persuasion': 'curiosity', 'key_phrases': ['hello there']},
        {'idx': 1, 'role': 'cta', 'start_s': 2.0, 'end_s': 4.5, 'text': 'and the point of this',
         'segment_idx': [1], 'audience_function': 'close', 'emotion': 'neutral',
         'intention': 'cta', 'persuasion': 'direct', 'key_phrases': []},
    ],
    'semantics': {'topic': 'AI tools', 'hook_type': 'question', 'pain': 'other',
                  'solution_type': 'other', 'proof_type': 'none', 'cta_type': 'none',
                  'narrative': 'other', 'funnel_role': 'awareness', 'positioning_type': 'educator'},
    'interpretation': {}, 'quality': {}, 'confidence': 'PROBABLE', 'notes': 'fixture for tests',
}


def test_ingest_path_lands_beats_rows(con, paths):
    (paths['ta_dir'] / 'TAJSON01.json').write_text(
        json.dumps(TA_FIXTURE, ensure_ascii=False), encoding='utf-8')

    assert 'TAJSON01' in ap.select_transcript_pending(con)   # pending before the run

    summary = ap.run(con, dry=False, yes=False, input_dir=paths['input_dir'])

    beats = con.execute('SELECT * FROM beats WHERE code=? ORDER BY idx', ('TAJSON01',)).fetchall()
    assert len(beats) == 2
    assert beats[0]['role'] == 'hook'
    assert beats[1]['role'] == 'cta'

    assert 'TAJSON01' not in ap.select_transcript_pending(con)   # resolved
    assert summary['beats_added'] >= 2
    assert summary['files_ingested'] >= 1

    vs = con.execute('SELECT transcript_analysis_state FROM video_state WHERE code=?',
                     ('TAJSON01',)).fetchone()
    assert vs is not None and vs['transcript_analysis_state'] == 'DONE'


def test_run_is_idempotent(con, paths):
    (paths['ta_dir'] / 'TAJSON01.json').write_text(
        json.dumps(TA_FIXTURE, ensure_ascii=False), encoding='utf-8')

    ap.run(con, dry=False, yes=False, input_dir=paths['input_dir'])
    beats_after_1 = con.execute('SELECT COUNT(*) FROM beats WHERE code=?', ('TAJSON01',)).fetchone()[0]

    ap.run(con, dry=False, yes=False, input_dir=paths['input_dir'])
    beats_after_2 = con.execute('SELECT COUNT(*) FROM beats WHERE code=?', ('TAJSON01',)).fetchone()[0]

    assert beats_after_1 == beats_after_2 == 2
