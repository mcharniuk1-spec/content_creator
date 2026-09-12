"""Tests for engine/cards_v2.py, engine/storyboard_render.py, engine/edl.py.

Uses `tests/fixtures/card-example.json` (a complete, valid, fictional card) plus
six broken variants derived from it in-memory (never written to disk).

The storyboard-render + EDL test renders the example card into the real
`cards/frames/` and `cards/edl/` locations on purpose (that is the one place the
EDL contract requires asset paths relative to the repo root) — this is also the
"render the example card once" deliverable, not just a test side effect.
"""
import copy
import json
import pathlib
import sys

import pytest
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import cards_v2 as cv                # noqa: E402
from engine import edl as edl_mod                # noqa: E402
from engine import schema as engine_schema       # noqa: E402
from engine import storyboard_render as sbr      # noqa: E402
from engine.db_util import connect               # noqa: E402

FIXTURE = ROOT / 'tests' / 'fixtures' / 'card-example.json'


@pytest.fixture
def card():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def _broken(card, mutate):
    c = copy.deepcopy(card)
    mutate(c)
    return c


# --------------------------------------------------------------------------- #
# validate()
# --------------------------------------------------------------------------- #

def test_validate_fixture_passes(card):
    errors = cv.validate(card)
    hard = [e for e in errors if not e.startswith('WARNING: ')]
    assert hard == [], hard
    assert cv.is_valid(errors)


def test_validate_fails_missing_mandatory_filter_field(card):
    broken = _broken(card, lambda c: c['strategy']['filter'].__setitem__('process', ''))
    errors = cv.validate(broken)
    assert not cv.is_valid(errors)
    assert any('filter' in e and 'process' in e for e in errors)


def test_validate_fails_bad_frame_type(card):
    def mutate(c):
        c['storyboard'][0]['frame_type'] = 'NOT_A_REAL_FRAME_TYPE'
    errors = cv.validate(_broken(card, mutate))
    assert not cv.is_valid(errors)
    assert any('frame_type' in e for e in errors)


def test_validate_fails_too_few_hooks(card):
    def mutate(c):
        c['hooks'] = c['hooks'][:1]
    errors = cv.validate(_broken(card, mutate))
    assert not cv.is_valid(errors)
    assert any('hooks' in e for e in errors)


def test_validate_fails_noncontiguous_storyboard(card):
    def mutate(c):
        c['storyboard'][3]['start_s'] = 21.5  # scene 2 ends at 20.0s -> gap before scene 3
    errors = cv.validate(_broken(card, mutate))
    assert not cv.is_valid(errors)
    assert any('contiguous' in e for e in errors)


def test_validate_fails_reference_missing_fields(card):
    def mutate(c):
        del c['references'][0]['reason']
        del c['references'][0]['share_rate']
    errors = cv.validate(_broken(card, mutate))
    assert not cv.is_valid(errors)
    assert any('reason' in e for e in errors)
    assert any('share_rate' in e for e in errors)


def test_validate_fails_total_s_out_of_hard_bounds(card):
    def mutate(c):
        c['script']['total_s'] = 150.0
    errors = cv.validate(_broken(card, mutate))
    assert not cv.is_valid(errors)
    assert any('total_s' in e and 'hard bound' in e for e in errors)


def test_validate_warns_outside_soft_band_but_does_not_fail(card):
    def mutate(c):
        c['script']['total_s'] = 100.0
        c['storyboard'][-1]['end_s'] = 100.0  # keep storyboard coverage consistent
    errors = cv.validate(_broken(card, mutate))
    warnings = [e for e in errors if e.startswith('WARNING: ')]
    assert any('50-70s' in w for w in warnings)
    assert cv.is_valid(errors)  # a warning alone must not fail validation


# --------------------------------------------------------------------------- #
# save(): idempotent, writes cards_v2 / card_scenes / script_versions
# --------------------------------------------------------------------------- #

def test_save_idempotent_and_writes_db_rows(tmp_path, card):
    db_path = tmp_path / 'test.db'
    con = connect(str(db_path))
    engine_schema.migrate(con)
    json_dir = tmp_path / 'cards'

    path1 = cv.save(con, card, json_dir=json_dir)
    path2 = cv.save(con, json.loads(FIXTURE.read_text(encoding='utf-8')), json_dir=json_dir)
    assert path1 == path2
    assert path1.exists()
    assert json.loads(path1.read_text(encoding='utf-8'))['card_id'] == card['card_id']

    rows = con.execute('SELECT * FROM cards_v2 WHERE card_id=?', (card['card_id'],)).fetchall()
    assert len(rows) == 1
    assert rows[0]['title'] == card['title']
    assert rows[0]['total_s'] == card['script']['total_s']

    scenes = con.execute(
        'SELECT * FROM card_scenes WHERE card_id=? ORDER BY idx', (card['card_id'],)).fetchall()
    assert len(scenes) == len(card['storyboard']) == 7

    versions = con.execute(
        'SELECT version, kind FROM script_versions WHERE card_id=? ORDER BY version', (card['card_id'],)
    ).fetchall()
    # writer at script.version (2) + reviewer at version+1 (3), since review.revised is true
    assert [(v['version'], v['kind']) for v in versions] == [(2, 'writer'), (3, 'reviewer')]

    loaded = cv.load_all(con)
    assert len(loaded) == 1
    assert loaded[0]['card_id'] == card['card_id']
    assert len(loaded[0]['scenes']) == 7

    # saving again must not duplicate rows
    cv.save(con, card, json_dir=json_dir)
    assert con.execute('SELECT COUNT(*) FROM cards_v2 WHERE card_id=?',
                        (card['card_id'],)).fetchone()[0] == 1
    assert con.execute('SELECT COUNT(*) FROM card_scenes WHERE card_id=?',
                        (card['card_id'],)).fetchone()[0] == 7
    assert con.execute('SELECT COUNT(*) FROM script_versions WHERE card_id=?',
                        (card['card_id'],)).fetchone()[0] == 2
    con.close()


def test_save_refuses_invalid_card(tmp_path, card):
    db_path = tmp_path / 'test.db'
    con = connect(str(db_path))
    engine_schema.migrate(con)
    broken = _broken(card, lambda c: c['hooks'].__setitem__(slice(1, None), []))  # 1 hook only
    with pytest.raises(ValueError):
        cv.save(con, broken, json_dir=tmp_path / 'cards')
    con.close()


# --------------------------------------------------------------------------- #
# storyboard_render.render_card()
# --------------------------------------------------------------------------- #

def test_render_card_produces_pngs_and_sheet(tmp_path, card):
    c = copy.deepcopy(card)
    out_dir = tmp_path / 'frames'
    paths = sbr.render_card(c, out_dir=out_dir)

    assert len(paths) == len(card['storyboard']) == 7
    for p in paths:
        full = pathlib.Path(p)
        if not full.is_absolute():
            full = ROOT / p
        assert full.exists(), full
        with Image.open(full) as im:
            assert im.size == (1080, 1920)

    sheet = out_dir / f"{card['card_id']}_sheet.png"
    assert sheet.exists()
    with Image.open(sheet) as im:
        assert im.size[0] > 0 and im.size[1] > 0

    for scene in c['storyboard']:
        assert scene['asset_status'] == 'template'
        assert scene['asset_path']


# --------------------------------------------------------------------------- #
# engine/edl.py: partition sums + Node contract validation
# --------------------------------------------------------------------------- #

def test_edl_partition_and_node_contract(card):
    # Renders into the real cards/frames + cards/edl locations: the EDL contract
    # requires asset paths relative to the repo root, and this doubles as the
    # "render the example card once" deliverable.
    c = json.loads(FIXTURE.read_text(encoding='utf-8'))
    sbr.render_card(c)  # default out_dir='cards/frames'
    edl = edl_mod.card_to_edl(c)

    assert edl['schema'] == 'm2.remotion-edl.v1'
    assert edl['card_id'] == c['card_id']

    prev = 0
    for scene in edl['scenes']:
        assert scene['from_frame'] == prev, f'scene {scene["scene_id"]} does not follow contiguously'
        assert scene['duration_frames'] > 0
        prev += scene['duration_frames']
    assert prev == edl['duration_frames']

    edl_path = ROOT / 'cards' / 'edl' / f"{c['card_id']}.json"
    assert edl_path.exists()

    result = edl_mod.validate_with_node(edl_path)
    if result['skipped']:
        pytest.skip(f"node contract validation skipped: {result.get('reason')}")
    assert result['ok'], f"stdout={result['stdout']!r} stderr={result['stderr']!r}"
