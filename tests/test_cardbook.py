"""Tests for engine/cardbook.py.

Builds the fictional example card (`tests/fixtures/card-example.json`) into a fresh
temp `cards/` dir, renders its storyboard into a temp `cards/frames/` dir via
`engine.storyboard_render.render_card` (never touching the real project's
`cards/frames/`), then exercises `card_markdown()`, `intro_markdown()` and `build()`
against that temp layout. A final test drives the CLI end to end and (when headless
Chrome is available) builds a real PDF via `engine.pdf_build`.

    python3 -m pytest tests/test_cardbook.py -q
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine import cardbook                      # noqa: E402
from engine import pdf_build                     # noqa: E402
from engine import storyboard_render as sbr       # noqa: E402

FIXTURE = os.path.join(ROOT, 'tests', 'fixtures', 'card-example.json')
CHROME_REASON = f'headless Chrome not found at {pdf_build.CHROME}'

SECTION_HEADINGS = [
    '## Strategy', '## Hooks', '## Reference reels', '## Script', '## Storyboard',
    '## Editing', '## Claims', '## Traceability', '## Review', '## Production state',
]


@pytest.fixture
def card():
    with open(FIXTURE, encoding='utf-8') as fh:
        return json.load(fh)


@pytest.fixture
def rendered(tmp_path, card):
    """The example card copied into a temp cards dir, with its storyboard rendered
    into a temp frames dir. Returns (cards_dir, frames_dir, card_id).
    """
    cards_dir = tmp_path / 'cards'
    frames_dir = tmp_path / 'cards' / 'frames'
    cards_dir.mkdir(parents=True)

    card_copy = json.loads(json.dumps(card))  # deep copy, keep the on-disk fixture pristine
    (cards_dir / f"{card_copy['card_id']}.json").write_text(
        json.dumps(card_copy), encoding='utf-8')

    written = sbr.render_card(card_copy, out_dir=str(frames_dir))
    assert written, 'render_card wrote no frames'

    return cards_dir, frames_dir, card_copy['card_id']


# --------------------------------------------------------------------------- #
# card_markdown()
# --------------------------------------------------------------------------- #

def test_card_markdown_has_all_sections(rendered):
    cards_dir, frames_dir, card_id = rendered
    card_obj = json.loads((cards_dir / f'{card_id}.json').read_text(encoding='utf-8'))

    md = cardbook.card_markdown(card_obj, frames_dir=str(frames_dir))

    assert md.startswith(f'# {card_id} — {card_obj["title"]}')
    for heading in SECTION_HEADINGS:
        assert heading in md, f'missing section {heading!r}'


def test_card_markdown_marks_the_hook_used_in_script(rendered):
    cards_dir, frames_dir, card_id = rendered
    card_obj = json.loads((cards_dir / f'{card_id}.json').read_text(encoding='utf-8'))

    md = cardbook.card_markdown(card_obj, frames_dir=str(frames_dir))

    # exactly one hook candidate is marked used, and it is the one whose text
    # matches the script's hook-role section
    assert md.count('USED IN SCRIPT') == 1
    hook_section = md.split('## Hooks', 1)[1].split('## Reference reels', 1)[0]
    used_line_idx = next(i for i, line in enumerate(hook_section.splitlines())
                          if 'USED IN SCRIPT' in line)
    quote_line = hook_section.splitlines()[used_line_idx + 1]
    script_hook_text = next(
        s['text'] for s in card_obj['script']['sections'] if s['role'] == 'hook')
    assert script_hook_text in quote_line


def test_card_markdown_truncates_long_storyboard_script_text(rendered):
    cards_dir, frames_dir, card_id = rendered
    card_obj = json.loads((cards_dir / f'{card_id}.json').read_text(encoding='utf-8'))
    long_scene = next(s for s in card_obj['storyboard'] if len(s['script_text']) > 90)

    md = cardbook.card_markdown(card_obj, frames_dir=str(frames_dir))
    storyboard_table = md.split('## Storyboard', 1)[1].split('::grid ', 1)[0]

    # the full line is legitimately repeated verbatim in the Script section's "full
    # text as spoken" — only the Storyboard table's own row must be truncated
    assert long_scene['script_text'] not in storyboard_table
    assert long_scene['script_text'][:80] in storyboard_table


def test_card_markdown_grid_lines_reference_existing_pngs(rendered):
    cards_dir, frames_dir, card_id = rendered
    card_obj = json.loads((cards_dir / f'{card_id}.json').read_text(encoding='utf-8'))

    md = cardbook.card_markdown(card_obj, frames_dir=str(frames_dir))

    grid_lines = [line for line in md.splitlines() if line.startswith('::grid ')]
    assert grid_lines, 'no ::grid:: lines found in storyboard section'

    n_scenes = len(card_obj['storyboard'])
    all_paths = []
    for line in grid_lines:
        inner = line[len('::grid '):-len('::')]
        paths = inner.split('|')
        assert 1 <= len(paths) <= 3, f'grid line has {len(paths)} images, expected 1-3: {line!r}'
        all_paths.extend(paths)
    assert len(all_paths) == n_scenes
    for p in all_paths:
        assert os.path.isabs(p), f'expected an absolute frame path, got {p!r}'
        assert os.path.exists(p), f'grid references a frame that does not exist: {p}'

    sheet_path = str(frames_dir / f'{card_id}_sheet.png')
    assert f'![Contact sheet]({sheet_path})' in md
    assert os.path.exists(sheet_path)


def test_card_markdown_production_state_validation_branch(rendered, monkeypatch):
    cards_dir, frames_dir, card_id = rendered
    card_obj = json.loads((cards_dir / f'{card_id}.json').read_text(encoding='utf-8'))

    # no validation file: explicit "not yet validated" state
    md = cardbook.card_markdown(card_obj, frames_dir=str(frames_dir))
    assert 'not yet validated' in md

    # redirect cardbook's notion of the repo root to a scratch tree and plant a
    # validation.json there, without touching the real project's cards/edl/
    fake_root = frames_dir.parent.parent  # tmp_path
    monkeypatch.setattr(cardbook, 'ROOT', fake_root)
    edl_dir = fake_root / 'cards' / 'edl'
    edl_dir.mkdir(parents=True, exist_ok=True)
    (edl_dir / f'{card_id}.validation.json').write_text(
        json.dumps({'ok': True, 'skipped': False, 'stdout': 'EDL_OK', 'stderr': ''}),
        encoding='utf-8')

    md2 = cardbook.card_markdown(card_obj, frames_dir=str(frames_dir))
    assert 'PASS' in md2.split('## Production state', 1)[1]


# --------------------------------------------------------------------------- #
# intro_markdown()
# --------------------------------------------------------------------------- #

def test_intro_markdown_lists_every_card(card):
    md = cardbook.intro_markdown([card], run_meta={'date': '2026-09-12', 'commit': 'abc123'})

    assert cardbook.BOOK_TITLE in md
    assert '2026-09-12' in md
    assert 'abc123' in md
    assert card['card_id'] in md
    assert card['title'] in md
    assert '## Cards in this book' in md
    assert '## Template and production rules' in md
    assert '## Asset legend' in md
    # the 5-line production-rules block
    rules_block = md.split('## Template and production rules', 1)[1].split('## Asset legend', 1)[0]
    rule_lines = [line for line in rules_block.splitlines() if line.startswith('- ')]
    assert len(rule_lines) == 5


def test_intro_markdown_handles_empty_card_list():
    md = cardbook.intro_markdown([], run_meta=None)
    assert '0 card(s)' in md
    assert '## Cards in this book' in md


# --------------------------------------------------------------------------- #
# build()
# --------------------------------------------------------------------------- #

def test_build_skips_example_card_by_default(rendered, tmp_path):
    cards_dir, frames_dir, card_id = rendered
    out_dir = tmp_path / 'out-default'

    written = cardbook.build(out_md_dir=str(out_dir), cards_dir=str(cards_dir),
                              include_example=False, frames_dir=str(frames_dir))

    assert len(written) == 1
    assert written[0].endswith('00-intro.md')
    intro_text = (out_dir / '00-intro.md').read_text(encoding='utf-8')
    assert card_id not in intro_text


def test_build_includes_example_card_when_flagged(rendered, tmp_path):
    cards_dir, frames_dir, card_id = rendered
    out_dir = tmp_path / 'out-included'

    written = cardbook.build(out_md_dir=str(out_dir), cards_dir=str(cards_dir),
                              include_example=True, frames_dir=str(frames_dir))

    assert len(written) == 2
    assert written[0].endswith('00-intro.md')
    assert written[1].endswith(f'01-{card_id}.md')
    for f in written:
        assert os.path.exists(f)

    card_md = open(written[1], encoding='utf-8').read()
    for heading in SECTION_HEADINGS:
        assert heading in card_md


def test_build_include_example_falls_back_to_fixture_when_cards_dir_empty(tmp_path):
    """--include-example must work even when `cards_dir` has no real cards yet (the
    state of this repo today) by loading tests/fixtures/card-example.json directly.
    """
    out_dir = tmp_path / 'out'
    empty_cards_dir = tmp_path / 'no-cards-here'

    written = cardbook.build(out_md_dir=str(out_dir), cards_dir=str(empty_cards_dir),
                              include_example=True)

    assert len(written) == 2
    assert cardbook.EXAMPLE_CARD_ID in written[1]


# --------------------------------------------------------------------------- #
# PDF build (skips with a reason if headless Chrome is not on this machine)
# --------------------------------------------------------------------------- #

@pytest.mark.skipif(not pdf_build.chrome_available(), reason=CHROME_REASON)
def test_full_book_builds_to_pdf(rendered, tmp_path):
    cards_dir, frames_dir, card_id = rendered
    out_dir = tmp_path / 'md'

    md_files = cardbook.build(out_md_dir=str(out_dir), cards_dir=str(cards_dir),
                               include_example=True, frames_dir=str(frames_dir))

    out_pdf = tmp_path / 'cardbook-test.pdf'
    result = pdf_build.build(
        md_files, out_pdf=str(out_pdf), title=cardbook.BOOK_TITLE,
        subtitle='1 card(s) — test run', date='12 September 2026',
    )

    assert result['ok'] is True
    assert os.path.exists(result['out'])
    assert result['pages'] >= 2, f"expected >=2 pages (intro + 1 card), got {result['pages']}"
    assert result['bytes'] > 20_000
