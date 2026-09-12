"""Tests for engine/ingest_analysis.py (SPEC.md §4, §5).

Self-contained: builds a fresh SQLite file from `db.SCHEMA` + `engine.schema.migrate`
(same recipe as `tests/test_engine_schema.py`) and writes synthetic ta-v1 / fa-v1
JSON files into a temp directory, then calls `ingest_analysis.run(..., ta_dir=...,
fa_dir=..., warn_path=...)` directly — `run()` already accepts those three paths as
parameters, so there is no need to monkeypatch the module-level TA_DIR/FA_DIR/
WARN_PATH constants; passing explicit overrides gets the same isolation with less
brittleness. Nothing here reads or writes the real `data/analysis/` tree.

    python3 -m pytest tests/test_ingest_analysis.py -q
"""
import json
import os
import pathlib
import sqlite3
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import db as legacy_db                       # noqa: E402
from engine import ingest_analysis, schema    # noqa: E402

CODE = 'SYN0000001'
EMPTY_CODE = 'EMPTYBEAT1'


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #

def _blank_db(tmp_path):
    """Legacy schema + engine tables, exactly like tests/test_engine_schema.py."""
    con = sqlite3.connect(tmp_path / 'test.db')
    con.row_factory = sqlite3.Row
    con.executescript(legacy_db.SCHEMA)
    con.commit()
    schema.migrate(con)
    return con


def _seed_reel_and_transcript(con, code, dur=5.0):
    con.execute("INSERT INTO snapshots (id, taken, done) VALUES (1,'2026-09-01',1)")
    con.execute(
        'INSERT INTO reels (snapshot_id, code, pk_user, username, ts, kind, play, likes, '
        'comm, resh, save, dur, cap, followers) VALUES (1,?,11,?,1760000000,?,1000,10,2,3,4,?,?,5000)',
        (code, 'alice', 'clip', dur, 'a synthetic reel for ingest_analysis tests'))
    segs = json.dumps([{'s': 0.0, 'e': 2.0, 't': 'hello there friend'},
                        {'s': 2.0, 'e': 5.0, 't': 'and now the point'}])
    con.execute(
        "INSERT INTO transcripts (code, lang, words, text, segments) "
        "VALUES (?,'en',7,'hello there friend and now the point',?)", (code, segs))
    # the fixed9-style samples used by ingest_frames_doc's t_by_idx fallback lookup
    for idx, t_sec in ((0, 0.4), (1, 1.2), (2, 2.4)):
        con.execute('INSERT INTO frames (code, idx, t_sec, path) VALUES (?,?,?,?)',
                    (code, idx, t_sec, f'data/frames/{code}/{idx:02d}.jpg'))
    con.commit()


@pytest.fixture()
def con(tmp_path):
    c = _blank_db(tmp_path)
    _seed_reel_and_transcript(c, CODE)
    yield c
    c.close()


@pytest.fixture()
def analysis_dirs(tmp_path):
    ta_dir = tmp_path / 'analysis' / 'transcripts'
    fa_dir = tmp_path / 'analysis' / 'frames'
    ta_dir.mkdir(parents=True)
    fa_dir.mkdir(parents=True)
    warn_path = tmp_path / 'analysis' / 'ingest_warnings.md'
    return ta_dir, fa_dir, warn_path


def _ta_doc(code=CODE):
    return {
        'code': code,
        'analysis_version': 'ta-v1',
        'model': 'test-model',
        'language': 'en',
        'beats': [
            {'idx': 0, 'role': 'hook', 'start_s': 0.0, 'end_s': 2.0,
             'text': 'hello there friend', 'segment_idx': [0]},
            # unknown role -> canon() must fall back to 'other' and log a warning
            {'idx': 1, 'role': 'TOTALLY_UNKNOWN_ROLE', 'start_s': 2.0, 'end_s': 5.0,
             'text': 'and now the point', 'segment_idx': [1]},
        ],
    }


def _fa_doc(code=CODE):
    return {
        'code': code,
        'analysis_version': 'fa-v1',
        'model': 'test-model',
        'frames_version': 'fixed9-v1',
        'frames': {
            # idx 0/1 share a frame_type -> one scene run
            '0': {'frame_type': 'A_ROLL_CLOSE_UP', 'roll': 'A'},
            '1': {'frame_type': 'A_ROLL_CLOSE_UP', 'roll': 'A'},
            # idx 2 is an unknown label -> canon() falls back to UNKNOWN + a new run
            '2': {'frame_type': 'TOTALLY_MADE_UP_TYPE', 'roll': 'A'},
        },
        'transitions_observed': [
            {'from_idx': 1, 'to_idx': 2, 'kind': 'hard_cut'},
        ],
    }


def _write(d, doc):
    (d / f"{doc['code']}.json").write_text(json.dumps(doc), encoding='utf-8')


# --------------------------------------------------------------------------- #
# 1. beats: idx / role / start / end / share_of_speech
# --------------------------------------------------------------------------- #

def test_ingest_transcript_writes_beats_with_correct_fields(con, analysis_dirs):
    ta_dir, fa_dir, warn_path = analysis_dirs
    _write(ta_dir, _ta_doc())

    summary = ingest_analysis.run(con, transcripts=True, frames=False,
                                  ta_dir=ta_dir, fa_dir=fa_dir, warn_path=warn_path,
                                  verbose=False)

    assert summary['beat_codes'] == 1
    assert summary['beats'] == 2
    assert summary['rejected'] == []

    rows = con.execute(
        'SELECT idx, role, start_s, end_s, share_of_speech FROM beats WHERE code=? ORDER BY idx',
        (CODE,)).fetchall()
    assert len(rows) == 2

    assert rows[0]['idx'] == 0
    assert rows[0]['role'] == 'hook'
    assert rows[0]['start_s'] == pytest.approx(0.0)
    assert rows[0]['end_s'] == pytest.approx(2.0)
    assert rows[0]['share_of_speech'] == pytest.approx(2.0 / 5.0)

    assert rows[1]['idx'] == 1
    # unknown role -> canonical fallback
    assert rows[1]['role'] == 'other'
    assert rows[1]['start_s'] == pytest.approx(2.0)
    assert rows[1]['end_s'] == pytest.approx(5.0)
    assert rows[1]['share_of_speech'] == pytest.approx(3.0 / 5.0)


# --------------------------------------------------------------------------- #
# 2. frame_labels: canonical vocab + legacy scenes from runs of identical frame_type
# --------------------------------------------------------------------------- #

def test_ingest_frames_writes_frame_labels_and_legacy_scenes(con, analysis_dirs):
    ta_dir, fa_dir, warn_path = analysis_dirs
    _write(fa_dir, _fa_doc())

    summary = ingest_analysis.run(con, transcripts=False, frames=True,
                                  ta_dir=ta_dir, fa_dir=fa_dir, warn_path=warn_path,
                                  verbose=False)

    assert summary['frame_codes'] == 1
    assert summary['frame_labels'] == 3
    assert summary['scenes'] == 2

    labels = con.execute(
        'SELECT idx, frame_type, roll FROM frame_labels WHERE code=? ORDER BY idx', (CODE,)).fetchall()
    assert [r['frame_type'] for r in labels] == ['A_ROLL_CLOSE_UP', 'A_ROLL_CLOSE_UP', 'UNKNOWN']
    assert all(r['roll'] == 'A' for r in labels)

    scenes = con.execute(
        "SELECT idx, start_s, end_s, scene_type, transition_in, boundary_reason, frames_version "
        "FROM scenes WHERE code=? AND frames_version='fixed9-v1' ORDER BY idx", (CODE,)).fetchall()
    assert len(scenes) == 2

    run0, run1 = scenes
    assert run0['scene_type'] == 'A_ROLL_CLOSE_UP'
    assert run0['start_s'] == pytest.approx(0.4)
    assert run0['end_s'] == pytest.approx(2.4)          # next run's start
    assert run0['boundary_reason'] == 'sampled'
    assert run0['transition_in'] == 'unknown'            # nothing precedes the first sample

    assert run1['scene_type'] == 'UNKNOWN'
    assert run1['start_s'] == pytest.approx(2.4)
    assert run1['end_s'] == pytest.approx(5.0)           # reels.dur, the last run's end
    assert run1['transition_in'] == 'hard_cut'           # observed transitions_observed[1->2]


# --------------------------------------------------------------------------- #
# 3. unknown labels are logged, never dropped
# --------------------------------------------------------------------------- #

def test_unknown_labels_are_logged_to_warnings_file(con, analysis_dirs):
    ta_dir, fa_dir, warn_path = analysis_dirs
    _write(ta_dir, _ta_doc())
    _write(fa_dir, _fa_doc())

    summary = ingest_analysis.run(con, transcripts=True, frames=True,
                                  ta_dir=ta_dir, fa_dir=fa_dir, warn_path=warn_path,
                                  verbose=False)

    assert summary['warnings'] == 2
    assert pathlib.Path(summary['warnings_path']) == warn_path
    assert warn_path.exists()
    text = warn_path.read_text(encoding='utf-8')
    assert CODE in text
    assert 'beat.role' in text and 'TOTALLY_UNKNOWN_ROLE' in text
    assert 'frame_type' in text and 'TOTALLY_MADE_UP_TYPE' in text

    # nothing was thrown away: the raw value survives in the row's *_json column
    raw_role_row = con.execute(
        'SELECT text FROM beats WHERE code=? AND idx=1', (CODE,)).fetchone()
    assert raw_role_row is not None  # the beat itself was still ingested (role only falls back)
    raw_frame_row = con.execute(
        'SELECT labels_json FROM frame_labels WHERE code=? AND idx=2', (CODE,)).fetchone()
    assert 'TOTALLY_MADE_UP_TYPE' in raw_frame_row['labels_json']


# --------------------------------------------------------------------------- #
# 4. a file with empty beats is rejected, never partially ingested
# --------------------------------------------------------------------------- #

def test_empty_beats_file_is_rejected_not_partially_ingested(con, analysis_dirs):
    ta_dir, fa_dir, warn_path = analysis_dirs
    _write(ta_dir, _ta_doc())  # the good file, so we can tell "rejected" from "nothing ran"
    _write(ta_dir, {'code': EMPTY_CODE, 'analysis_version': 'ta-v1', 'beats': []})

    summary = ingest_analysis.run(con, transcripts=True, frames=False,
                                  ta_dir=ta_dir, fa_dir=fa_dir, warn_path=warn_path,
                                  verbose=False)

    assert summary['beat_codes'] == 1          # only the good file counted
    assert summary['beats'] == 2
    rejected_files = {r['file'] for r in summary['rejected']}
    assert f'{EMPTY_CODE}.json' in rejected_files
    problems = next(r['problems'] for r in summary['rejected'] if r['file'] == f'{EMPTY_CODE}.json')
    assert any('beats' in p for p in problems)

    # nothing at all was written for the rejected code
    assert con.execute('SELECT COUNT(*) FROM beats WHERE code=?', (EMPTY_CODE,)).fetchone()[0] == 0


# --------------------------------------------------------------------------- #
# 5. re-ingest is idempotent
# --------------------------------------------------------------------------- #

def test_reingest_is_idempotent(con, analysis_dirs):
    ta_dir, fa_dir, warn_path = analysis_dirs
    _write(ta_dir, _ta_doc())
    _write(fa_dir, _fa_doc())

    ingest_analysis.run(con, transcripts=True, frames=True,
                        ta_dir=ta_dir, fa_dir=fa_dir, warn_path=warn_path, verbose=False)

    def counts():
        return {
            'beats': con.execute('SELECT COUNT(*) FROM beats WHERE code=?', (CODE,)).fetchone()[0],
            'frame_labels': con.execute(
                'SELECT COUNT(*) FROM frame_labels WHERE code=?', (CODE,)).fetchone()[0],
            'scenes': con.execute(
                "SELECT COUNT(*) FROM scenes WHERE code=? AND frames_version='fixed9-v1'",
                (CODE,)).fetchone()[0],
        }

    before = counts()
    assert before == {'beats': 2, 'frame_labels': 3, 'scenes': 2}

    # run again, same files, same db
    ingest_analysis.run(con, transcripts=True, frames=True,
                        ta_dir=ta_dir, fa_dir=fa_dir, warn_path=warn_path, verbose=False)

    after = counts()
    assert after == before
