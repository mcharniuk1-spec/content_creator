"""Inventory checks against the real, committed `cards/` directory.

Unlike every other suite under `tests/`, this file deliberately reads the repo's
actual `cards/C-2026-09-12-NN.json` deliverables and their rendered frames/EDL —
it is a check on the shipped artifacts, not on the engine code. It is marked
`@pytest.mark.repo` for anyone who wants to select/deselect it explicitly.

That marker is not registered in `pytest.ini` (this task is not allowed to edit
that file), so pytest will print an unknown-mark warning when this file is
collected; `pytest.ini` has no `--strict-markers`/`filterwarnings=error`, so the
warning is harmless. Real self-skipping happens via a plain file-presence check
below (`allow_module_level=True`), so this file collects cleanly and skips itself
whenever it is not run from inside this repo checkout (e.g. copied elsewhere
without the generated `cards/` tree).

    python3 -m pytest tests/test_cards_inventory.py -q
    python3 -m pytest tests/test_cards_inventory.py -m repo -q
"""
import json
import pathlib
import re
import shutil
import sqlite3
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CARDS_DIR = ROOT / 'cards'
EDL_DIR = CARDS_DIR / 'edl'
DB_PATH = ROOT / 'data' / 'radar.db'
CARD_NAME_RX = re.compile(r'^C-2026-09-12-\d{2}\.json$')

pytestmark = pytest.mark.repo

if not CARDS_DIR.is_dir():
    pytest.skip(f'{CARDS_DIR} not present — this suite only runs inside the '
                f'm2-research/radar repo checkout, not a copy without generated cards',
                allow_module_level=True)

from engine import cards_v2 as cv  # noqa: E402

NODE_ON_PATH = shutil.which('node') is not None

CARD_FILES = sorted(
    p for p in CARDS_DIR.iterdir()
    if p.is_file() and CARD_NAME_RX.match(p.name))


def _load(path):
    return json.loads(path.read_text(encoding='utf-8'))


# --------------------------------------------------------------------------- #
# 1. exactly 10 dated cards
# --------------------------------------------------------------------------- #

def test_exactly_ten_dated_cards():
    assert len(CARD_FILES) == 10, [p.name for p in CARD_FILES]


# --------------------------------------------------------------------------- #
# 2. every one validates with 0 errors and is REVIEWED
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('path', CARD_FILES, ids=lambda p: p.name)
def test_card_validates_with_zero_errors(path):
    card = _load(path)
    errors = cv.validate(card)
    hard = [e for e in errors if not e.startswith('WARNING: ')]
    assert hard == [], f'{path.name}: {hard}'


@pytest.mark.parametrize('path', CARD_FILES, ids=lambda p: p.name)
def test_card_status_is_reviewed(path):
    card = _load(path)
    assert card.get('status') == 'REVIEWED', f'{path.name}: status={card.get("status")!r}'


# --------------------------------------------------------------------------- #
# 3. total_s within the 50-70s sweet spot
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('path', CARD_FILES, ids=lambda p: p.name)
def test_card_total_s_within_sweet_spot(path):
    card = _load(path)
    total_s = card['script']['total_s']
    assert 50 <= total_s <= 70, f'{path.name}: total_s={total_s}'


# --------------------------------------------------------------------------- #
# 4. at least 3 references, with real codes present in data/radar.db (if it exists)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('path', CARD_FILES, ids=lambda p: p.name)
def test_card_has_at_least_three_references(path):
    card = _load(path)
    refs = card.get('references') or []
    assert len(refs) >= 3, f'{path.name}: only {len(refs)} reference(s)'


@pytest.mark.skipif(not DB_PATH.exists(), reason='data/radar.db not present')
@pytest.mark.parametrize('path', CARD_FILES, ids=lambda p: p.name)
def test_card_reference_codes_are_real(path):
    card = _load(path)
    refs = card.get('references') or []
    # read-only URI connection: never create or modify the real database
    con = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True)
    try:
        found = sum(
            1 for ref in refs
            if con.execute('SELECT 1 FROM reels WHERE code=? LIMIT 1', (ref['code'],)).fetchone())
    finally:
        con.close()
    assert found >= 3, f'{path.name}: only {found}/{len(refs)} reference codes found in reels'


# --------------------------------------------------------------------------- #
# 5. every storyboard scene has an existing asset_path PNG
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('path', CARD_FILES, ids=lambda p: p.name)
def test_card_storyboard_assets_exist(path):
    card = _load(path)
    for scene in card['storyboard']:
        asset = scene.get('asset_path')
        assert asset, f'{path.name} scene idx={scene.get("idx")}: no asset_path'
        full = pathlib.Path(asset)
        if not full.is_absolute():
            full = ROOT / full
        assert full.exists(), full


# --------------------------------------------------------------------------- #
# 6. cards/edl/<id>.validation.json reports ok (skip if node is not on PATH)
# --------------------------------------------------------------------------- #

@pytest.mark.skipif(not NODE_ON_PATH, reason='node not on PATH')
@pytest.mark.parametrize('path', CARD_FILES, ids=lambda p: p.name)
def test_card_edl_validation_reports_ok(path):
    card = _load(path)
    val_path = EDL_DIR / f"{card['card_id']}.validation.json"
    assert val_path.exists(), val_path
    val = _load(val_path)
    result = val.get('result') or {}
    if result.get('skipped'):
        pytest.skip(f'validation.json itself recorded a skip: {result.get("reason")}')
    assert result.get('ok') is True, result
