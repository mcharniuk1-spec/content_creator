"""Tests for engine/cards_pipeline.py: finalize() and main().

`finalize()` chains CARD_GENERATION -> SCRIPT_GENERATION -> SCRIPT_REVIEW ->
FRAME_PLAN -> FRAME_GENERATION -> VIDEO_GENERATION_READY, one `jobs` row per
step, then renders frames, saves the card into the DB, and writes a Remotion EDL
+ its node-contract validation.

Every path it touches (`storyboard_render.render_card`'s `out_dir='cards/frames'`,
`cards_v2.save`'s `json_dir='cards'`, `edl.card_to_edl`'s hardcoded `cards/edl/`,
and `cards_pipeline`'s own `ROOT`-relative edl_dir) resolves relative paths against
each module's own `ROOT` constant (`engine.db_util.ROOT`, imported by name into
`cards_v2`/`storyboard_render`/`edl`; `cards_pipeline` has its own copy). So the
sandbox fixture below monkeypatches all four `ROOT` attributes to the same
`tmp_path`, which redirects every one of those writes away from the real `cards/`
tree without touching engine code. `engine.edl.CONTRACT_PATH` is computed once at
import time from the *real* ROOT and is deliberately left alone, so node-contract
validation still runs against the real `studio/remotion/contract.mjs`.

    python3 -m pytest tests/test_cards_pipeline.py -q
"""
import copy
import json
import pathlib
import shutil
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import cards_pipeline                # noqa: E402
from engine import cards_v2 as cv                # noqa: E402
from engine import edl as edl_mod                # noqa: E402
from engine import schema as engine_schema       # noqa: E402
from engine import state                         # noqa: E402
from engine import storyboard_render as sbr      # noqa: E402
from engine.db_util import connect               # noqa: E402

FIXTURE = ROOT / 'tests' / 'fixtures' / 'card-example.json'
NODE_ON_PATH = shutil.which('node') is not None


def _card():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    """Redirect every module's ROOT so nothing lands in the real cards/ tree."""
    monkeypatch.setattr(cards_pipeline, 'ROOT', tmp_path)
    monkeypatch.setattr(cv, 'ROOT', tmp_path)
    monkeypatch.setattr(sbr, 'ROOT', tmp_path)
    monkeypatch.setattr(edl_mod, 'ROOT', tmp_path)
    return tmp_path


@pytest.fixture()
def db(tmp_path):
    db_path = tmp_path / 'radar-test.db'
    con = connect(str(db_path))
    engine_schema.migrate(con)
    yield con, db_path
    con.close()


def _write_card(dirpath, card):
    dirpath.mkdir(parents=True, exist_ok=True)
    path = dirpath / f"{card['card_id']}.json"
    path.write_text(json.dumps(card), encoding='utf-8')
    return path


def _jobs_by_stage(con, run_id, card_id):
    return {r['stage']: r['state'] for r in con.execute(
        'SELECT stage, state FROM jobs WHERE run_id=? AND entity_kind=? AND entity_id=?',
        (run_id, 'card', card_id))}


# --------------------------------------------------------------------------- #
# 1. finalize() on a valid card: full job chain, frames, DB rows, EDL
# --------------------------------------------------------------------------- #

def test_finalize_valid_card_writes_jobs_frames_db_and_edl(sandbox, db):
    con, _ = db
    card = _card()
    card['card_id'] = 'C-2026-09-12-90'          # distinct from the EXAMPLE_ID
    src = _write_card(sandbox / 'src', card)

    run_id = state.start_run(con, 'cards', config={'test': 'finalize_valid'})
    result = cards_pipeline.finalize(con, src, run_id, node=NODE_ON_PATH)
    con.commit()

    jobs = _jobs_by_stage(con, run_id, card['card_id'])
    for stage in ('CARD_GENERATION', 'SCRIPT_GENERATION', 'SCRIPT_REVIEW', 'FRAME_PLAN',
                  'FRAME_GENERATION', 'VIDEO_GENERATION_READY'):
        assert stage in jobs, f'missing {stage} job row'
    for stage in ('CARD_GENERATION', 'SCRIPT_GENERATION', 'FRAME_PLAN', 'FRAME_GENERATION',
                  'VIDEO_GENERATION_READY'):
        assert jobs[stage] == 'DONE', f'{stage}: {jobs[stage]}'
    # the fixture's review.findings is non-empty -> SCRIPT_REVIEW must be DONE, not SKIPPED
    assert jobs['SCRIPT_REVIEW'] == 'DONE'

    # frames rendered under the sandboxed ROOT, never under the real cards/frames
    assert len(result['frames']) == len(card['storyboard'])
    for rel in result['frames']:
        full = pathlib.Path(rel)
        if not full.is_absolute():
            full = sandbox / rel
        assert full.exists(), full
        assert full.is_relative_to(sandbox)

    # cards_v2 / card_scenes / script_versions rows
    assert con.execute('SELECT COUNT(*) FROM cards_v2 WHERE card_id=?',
                       (card['card_id'],)).fetchone()[0] == 1
    assert con.execute('SELECT COUNT(*) FROM card_scenes WHERE card_id=?',
                       (card['card_id'],)).fetchone()[0] == len(card['storyboard'])
    assert con.execute('SELECT COUNT(*) FROM script_versions WHERE card_id=?',
                       (card['card_id'],)).fetchone()[0] >= 1

    # the finalized JSON was written under the sandbox, not the real cards/
    saved_path = pathlib.Path(result['saved'])
    if not saved_path.is_absolute():
        saved_path = sandbox / saved_path
    assert saved_path.exists()
    assert saved_path.is_relative_to(sandbox)

    # EDL + its validation JSON
    edl_path = sandbox / 'cards' / 'edl' / f"{card['card_id']}.json"
    val_path = sandbox / 'cards' / 'edl' / f"{card['card_id']}.validation.json"
    assert edl_path.exists()
    assert val_path.exists()
    val = json.loads(val_path.read_text(encoding='utf-8'))
    assert val['card_id'] == card['card_id']
    if NODE_ON_PATH and edl_mod.CONTRACT_PATH.exists():
        assert val['result'].get('ok') is True, val['result']
        assert jobs['VIDEO_GENERATION_READY'] == 'DONE'
    else:
        assert val['result'].get('skipped') is True


# --------------------------------------------------------------------------- #
# 2. an invalid card raises and leaves a FAILED CARD_GENERATION job, nothing else
# --------------------------------------------------------------------------- #

def test_finalize_invalid_card_raises_and_leaves_failed_job(sandbox, db):
    con, _ = db
    card = _card()
    card['card_id'] = 'C-2026-09-12-91'
    card['hooks'] = card['hooks'][:1]            # validate() requires >=2 hooks
    src = _write_card(sandbox / 'src', card)

    run_id = state.start_run(con, 'cards', config={'test': 'finalize_invalid'})
    with pytest.raises(ValueError):
        cards_pipeline.finalize(con, src, run_id, node=False)
    con.commit()

    jobs = con.execute(
        'SELECT stage, state, validation FROM jobs WHERE run_id=? AND entity_kind=? AND entity_id=?',
        (run_id, 'card', card['card_id'])).fetchall()
    assert len(jobs) == 1, jobs   # the chain must stop at CARD_GENERATION, nothing further runs
    assert jobs[0]['stage'] == 'CARD_GENERATION'
    assert jobs[0]['state'] == 'FAILED'
    assert jobs[0]['validation'] == 'FAILED'

    # nothing was persisted for the broken card
    assert con.execute('SELECT COUNT(*) FROM cards_v2 WHERE card_id=?',
                       (card['card_id'],)).fetchone()[0] == 0
    assert not (sandbox / 'cards' / f"{card['card_id']}.json").exists()


# --------------------------------------------------------------------------- #
# 3. main(['--all']) processes real cards but always skips the example card
# --------------------------------------------------------------------------- #

def test_main_all_skips_example_id(sandbox, db):
    con, db_path = db
    example = _card()                             # card_id is cards_pipeline.EXAMPLE_ID as-is
    assert example['card_id'] == cards_pipeline.EXAMPLE_ID
    other = _card()
    other['card_id'] = 'C-2026-09-12-92'

    cards_dir = sandbox / 'cards'
    _write_card(cards_dir, example)
    _write_card(cards_dir, other)
    con.close()  # main() opens its own connection onto the same file

    rc = cards_pipeline.main(['--all', '--db', str(db_path), '--no-node'])
    assert rc == 0

    con2 = connect(str(db_path))
    try:
        assert con2.execute('SELECT COUNT(*) FROM cards_v2 WHERE card_id=?',
                            (other['card_id'],)).fetchone()[0] == 1
        assert con2.execute('SELECT COUNT(*) FROM cards_v2 WHERE card_id=?',
                            (cards_pipeline.EXAMPLE_ID,)).fetchone()[0] == 0
        assert con2.execute('SELECT COUNT(*) FROM jobs WHERE entity_kind=? AND entity_id=?',
                            ('card', cards_pipeline.EXAMPLE_ID)).fetchone()[0] == 0
    finally:
        con2.close()
