"""Tests for engine.ingest_insights: valid/invalid payloads, warnings, --dry, idempotency.

    python3 -m pytest tests/test_ingest_insights.py -q
"""
import json
import os
import sqlite3
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import db as legacy_db  # noqa: E402
from engine import ingest_insights as ii  # noqa: E402
from engine import schema  # noqa: E402


def _fresh_db(path):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(legacy_db.SCHEMA)
    schema.migrate(con)
    con.commit()
    return con


@pytest.fixture()
def con(tmp_path):
    c = _fresh_db(tmp_path / 'test.db')
    c.execute("INSERT INTO snapshots (id, taken, done) VALUES (1, '2026-09-10', 1)")
    # two real codes, one WITH a video_features row and one WITHOUT
    c.execute('INSERT INTO reels (snapshot_id, code, pk_user, username, ts, kind, play, likes, '
             'comm, resh, save, dur, cap, followers) VALUES (1,"CODEA",1,"alpha",1750000000,'
             '"clips",5000,200,10,30,40,20.0,"",10000)')
    c.execute('INSERT INTO reels (snapshot_id, code, pk_user, username, ts, kind, play, likes, '
             'comm, resh, save, dur, cap, followers) VALUES (1,"CODEB",1,"alpha",1750003000,'
             '"clips",6000,220,11,31,41,21.0,"",10000)')
    c.execute("INSERT INTO video_features (code, features_version, computed_at, features_json) "
             "VALUES ('CODEA','fv-1','2026-09-11T00:00:00Z','{}')")
    # CODEB has a reels row but no video_features row on purpose
    c.commit()
    yield c
    c.close()


def _write(tmp_path, name, obj):
    path = tmp_path / name
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh)
    return str(path)


VALID_INSIGHT = {
    'insight_id': 'I-1', 'statement': 'hooks with a number outperform', 'claim': 'x',
    'metric': 'view_lift', 'n': 12, 'comparison': 'numeric hook vs other',
    'evidence': {'rho': 0.4}, 'supporting_codes': ['CODEA', 'CODEB'],
    'supporting_creators': ['alpha'], 'confidence': 'PROBABLE',
    'interpretation': 'numbers read as concrete', 'implication': 'use numbers in hooks',
    'limitations': 'associational only',
}

VALID_HYPOTHESIS = {
    'hypothesis_id': 'H-1', 'title': 'Numbered hook builds', 'statement': 'use a number in the hook',
    'audience': 'beginners', 'positioning_fit': 'educator', 'pain': 'time_waste',
    'desired_outcome': 'save the video', 'hook': 'Three things...', 'thesis': '...',
    'mechanism': '...', 'proof': '...', 'cta': 'follow', 'visual_structure': 'a_roll',
    'format': 'M2 Radar', 'supporting_insights': ['I-1'], 'candidate_refs': ['CODEA'],
    'strengths': 'clear', 'risks': 'generic', 'novelty': 'medium', 'confidence': 'PROBABLE',
    'scores': {'evidence': 4}, 'total_score': 7.5, 'reviewer_comment': None,
}

VALID_REF = {
    'hypothesis_id': 'H-1', 'code': 'CODEA', 'function': 'hook', 'reason': 'strong hook example',
    'useful_beat_ids': ['b1'], 'useful_scene_ids': ['s1'],
    'performance': {'play': 5000, 'view_lift': 0.5}, 'transformation': 'kept the number, changed the topic',
}


# ---------------------------------------------------------------------------
# valid payloads
# ---------------------------------------------------------------------------

def test_valid_insight_hypothesis_ref_are_ingested(tmp_path, con):
    insights_path = _write(tmp_path, 'insights.json', [VALID_INSIGHT])
    hyp_path = _write(tmp_path, 'hypotheses.json', [VALID_HYPOTHESIS])
    refs_path = _write(tmp_path, 'hypothesis_refs.json', [VALID_REF])

    summary = ii.run(con, insights_path=insights_path, hypotheses_path=hyp_path, refs_path=refs_path)

    assert summary['insights'] == 1
    assert summary['hypotheses'] == 1
    assert summary['hypothesis_refs'] == 1
    assert not summary['rejected_insights']
    assert not summary['rejected_hypotheses']
    assert not summary['rejected_refs']

    row = con.execute('SELECT * FROM insights WHERE insight_id="I-1"').fetchone()
    assert row['confidence'] == 'PROBABLE'
    assert json.loads(row['supporting_codes_json']) == ['CODEA', 'CODEB']

    row = con.execute('SELECT * FROM hypotheses WHERE hypothesis_id="H-1"').fetchone()
    assert row['status'] == 'PROPOSED'  # defaulted, not present in the payload
    assert row['format'] == 'M2 Radar'

    row = con.execute('SELECT * FROM hypothesis_refs WHERE hypothesis_id="H-1" AND code="CODEA"').fetchone()
    assert row['function'] == 'hook'
    assert json.loads(row['performance_json'])['play'] == 5000

    # a run row was opened (no explicit run_id given) and jobs were traced
    assert summary['run_id'] is not None
    assert con.execute('SELECT COUNT(*) FROM runs WHERE run_id=?', (summary['run_id'],)).fetchone()[0] == 1
    assert con.execute('SELECT status FROM runs WHERE run_id=?', (summary['run_id'],)).fetchone()[0] == 'DONE'
    n_jobs = con.execute('SELECT COUNT(*) FROM jobs WHERE run_id=?', (summary['run_id'],)).fetchone()[0]
    assert n_jobs >= 3  # insights batch + hypothesis + refs-for-hypothesis


def test_soft_warning_for_supporting_code_not_in_reels(tmp_path, con):
    rec = dict(VALID_INSIGHT)
    rec['insight_id'] = 'I-2'
    rec['supporting_codes'] = ['CODEA', 'NOPE_NOT_A_CODE']
    insights_path = _write(tmp_path, 'insights.json', [rec])

    summary = ii.run(con, insights_path=insights_path,
                     hypotheses_path=str(tmp_path / 'nope_hyp.json'),
                     refs_path=str(tmp_path / 'nope_refs.json'))

    # still inserted -- a soft warning, not a rejection
    assert summary['insights'] == 1
    assert not summary['rejected_insights']
    assert summary['warnings'] >= 1
    assert os.path.exists(summary['warnings_path'])
    with open(summary['warnings_path']) as fh:
        text = fh.read()
    assert 'NOPE_NOT_A_CODE' in text
    # missing files (hypotheses/refs) are reported, not raised
    assert any('nope_hyp.json' in f for f in summary.get('missing_files', []))


# ---------------------------------------------------------------------------
# invalid payloads
# ---------------------------------------------------------------------------

def test_insight_missing_confidence_is_rejected(tmp_path, con):
    bad = dict(VALID_INSIGHT)
    bad['insight_id'] = 'I-BAD'
    bad['confidence'] = 'VERY_SURE'  # not in {RELIABLE, PROBABLE, INSUFFICIENT}
    insights_path = _write(tmp_path, 'insights.json', [bad])

    summary = ii.run(con, insights_path=insights_path,
                     hypotheses_path=str(tmp_path / 'x.json'), refs_path=str(tmp_path / 'y.json'))

    assert summary['insights'] == 0
    assert len(summary['rejected_insights']) == 1
    assert summary['rejected_insights'][0]['insight_id'] == 'I-BAD'
    assert con.execute('SELECT COUNT(*) FROM insights').fetchone()[0] == 0


def test_hypothesis_bad_status_is_coerced_with_warning(tmp_path, con):
    rec = dict(VALID_HYPOTHESIS)
    rec['status'] = 'WHATEVER'
    hyp_path = _write(tmp_path, 'hypotheses.json', [rec])

    summary = ii.run(con, insights_path=str(tmp_path / 'x.json'), hypotheses_path=hyp_path,
                     refs_path=str(tmp_path / 'y.json'))

    assert summary['hypotheses'] == 1  # coerced, not rejected
    row = con.execute('SELECT status FROM hypotheses WHERE hypothesis_id="H-1"').fetchone()
    assert row['status'] == 'PROPOSED'
    assert summary['warnings'] >= 1


def test_ref_bad_function_is_rejected(tmp_path, con):
    bad = dict(VALID_REF)
    bad['function'] = 'not_a_real_function'
    refs_path = _write(tmp_path, 'hypothesis_refs.json', [bad])

    summary = ii.run(con, insights_path=str(tmp_path / 'x.json'),
                     hypotheses_path=str(tmp_path / 'y.json'), refs_path=refs_path)

    assert summary['hypothesis_refs'] == 0
    assert len(summary['rejected_refs']) == 1
    assert con.execute('SELECT COUNT(*) FROM hypothesis_refs').fetchone()[0] == 0


def test_ref_code_without_video_features_row_is_rejected(tmp_path, con):
    bad = dict(VALID_REF)
    bad['code'] = 'CODEB'  # real reel, but no video_features row (fixture)
    refs_path = _write(tmp_path, 'hypothesis_refs.json', [bad])

    summary = ii.run(con, insights_path=str(tmp_path / 'x.json'),
                     hypotheses_path=str(tmp_path / 'y.json'), refs_path=refs_path)

    assert summary['hypothesis_refs'] == 0
    assert len(summary['rejected_refs']) == 1
    assert 'video_features' in summary['rejected_refs'][0]['problems'][0]


def test_ref_code_not_in_reels_at_all_is_rejected(tmp_path, con):
    bad = dict(VALID_REF)
    bad['code'] = 'GHOST_CODE'
    refs_path = _write(tmp_path, 'hypothesis_refs.json', [bad])

    summary = ii.run(con, insights_path=str(tmp_path / 'x.json'),
                     hypotheses_path=str(tmp_path / 'y.json'), refs_path=refs_path)

    assert summary['hypothesis_refs'] == 0
    assert len(summary['rejected_refs']) == 1


def test_malformed_file_is_reported_not_raised(tmp_path, con):
    insights_path = _write(tmp_path, 'insights.json', {'not': 'a list'})
    summary = ii.run(con, insights_path=insights_path,
                     hypotheses_path=str(tmp_path / 'x.json'), refs_path=str(tmp_path / 'y.json'))
    assert summary['insights'] == 0
    assert summary.get('malformed_files')


# ---------------------------------------------------------------------------
# --dry
# ---------------------------------------------------------------------------

def test_dry_run_writes_nothing(tmp_path, con):
    insights_path = _write(tmp_path, 'insights.json', [VALID_INSIGHT])
    hyp_path = _write(tmp_path, 'hypotheses.json', [VALID_HYPOTHESIS])
    refs_path = _write(tmp_path, 'hypothesis_refs.json', [VALID_REF])

    summary = ii.run(con, dry=True, insights_path=insights_path, hypotheses_path=hyp_path,
                     refs_path=refs_path)

    assert summary['dry_run'] is True
    assert summary['insights'] == 1  # counted as "would insert"
    assert con.execute('SELECT COUNT(*) FROM insights').fetchone()[0] == 0
    assert con.execute('SELECT COUNT(*) FROM hypotheses').fetchone()[0] == 0
    assert con.execute('SELECT COUNT(*) FROM hypothesis_refs').fetchone()[0] == 0
    assert con.execute('SELECT COUNT(*) FROM runs').fetchone()[0] == 0
    assert summary['warnings_path'] is None


# ---------------------------------------------------------------------------
# idempotency
# ---------------------------------------------------------------------------

def test_rerun_replaces_not_duplicates(tmp_path, con):
    insights_path = _write(tmp_path, 'insights.json', [VALID_INSIGHT])
    hyp_path = _write(tmp_path, 'hypotheses.json', [VALID_HYPOTHESIS])
    refs_path = _write(tmp_path, 'hypothesis_refs.json', [VALID_REF])

    ii.run(con, insights_path=insights_path, hypotheses_path=hyp_path, refs_path=refs_path)
    ii.run(con, insights_path=insights_path, hypotheses_path=hyp_path, refs_path=refs_path)

    assert con.execute('SELECT COUNT(*) FROM insights').fetchone()[0] == 1
    assert con.execute('SELECT COUNT(*) FROM hypotheses').fetchone()[0] == 1
    assert con.execute('SELECT COUNT(*) FROM hypothesis_refs').fetchone()[0] == 1
    # but two separate runs/job batches were traced
    assert con.execute('SELECT COUNT(*) FROM runs').fetchone()[0] == 2


def test_explicit_run_id_is_reused_not_reopened(tmp_path, con):
    from engine import state as engine_state
    run_id = engine_state.start_run(con, 'analysis')
    insights_path = _write(tmp_path, 'insights.json', [VALID_INSIGHT])

    summary = ii.run(con, run_id=run_id, insights_path=insights_path,
                     hypotheses_path=str(tmp_path / 'x.json'), refs_path=str(tmp_path / 'y.json'))

    assert summary['run_id'] == run_id
    # only the one run this test opened -- ingest_insights did not start a second one
    assert con.execute('SELECT COUNT(*) FROM runs').fetchone()[0] == 1
    row = con.execute('SELECT * FROM insights WHERE insight_id="I-1"').fetchone()
    assert row['run_id'] == run_id
