#!/usr/bin/env python3
"""Card book: turn `cards/<card_id>.json` documents (schema `m2radar.card.v2`, see
`engine/SPEC.md` §8 and `cards/README.md`) into production-ready creative-brief
markdown chapters, and — optionally — a single PDF via `engine.pdf_build` /
`tools/pdf/md2pdf.mjs`.

Each card becomes one markdown chapter (`card_markdown`): a full creative brief with
Strategy, Hooks, Reference reels, Script, Storyboard (table + rendered frame grid +
contact sheet), Editing, Claims, Traceability, Review and Production state sections —
everything a producer needs to shoot the card without asking anyone a question. A
front chapter (`intro_markdown`) explains how to read a card, lists every card in one
table, restates the house shooting rules (`PRODUCTION.md`) in five lines, and defines
the `asset_status` legend. `build()` writes `00-intro.md` plus one `.md` file per card
to `out_md_dir`; the CLI additionally drives `engine.pdf_build` when `--pdf` is given.

Storyboard frame images are referenced by absolute filesystem path (not relative to
the chapter file), because `out_md_dir` and the rendered-frames directory
(`cards/frames` by default, see `engine/storyboard_render.py`) are not generally
siblings — `tools/pdf/md2pdf.mjs`'s image/grid embedding accepts an absolute path
unchanged (`path.isAbsolute(imgPath) ? imgPath : path.resolve(baseDir, imgPath)`), so
this is the robust choice regardless of where the two directories sit relative to
each other. A card whose frames have not been rendered yet still builds cleanly: a
missing PNG renders a visible `[MISSING: ...]` / `[MISSING IMAGE: ...]` placeholder
per `tools/pdf/README.md` instead of breaking the build.

    python3 -m engine.cardbook
    python3 -m engine.cardbook --pdf reports/final/M2RADAR_CARD_BOOK.pdf
    python3 -m engine.cardbook --include-example --pdf /tmp/cardbook-sample.pdf

By default the fictional example card (`C-2026-09-11-EX`, `tests/fixtures/card-example.json`)
is excluded from the book — pass `--include-example` (CLI) / `include_example=True`
(`build()`) to include it, e.g. to demo the pipeline before any real card exists.
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import sys

from engine.db_util import ROOT, git_commit

EXAMPLE_CARD_ID = 'C-2026-09-11-EX'
EXAMPLE_CARD_PATH = ROOT / 'tests' / 'fixtures' / 'card-example.json'

DEFAULT_OUT_DIR = 'reports/final/cardbook'
DEFAULT_CARDS_DIR = 'cards'
DEFAULT_FRAMES_DIR = 'cards/frames'
DEFAULT_PDF_PATH = 'reports/final/M2RADAR_CARD_BOOK.pdf'
BOOK_TITLE = 'M2 Lab — Ten Content Cards'


def _resolve_dir(path_like) -> pathlib.Path:
    """`path_like` as an absolute `pathlib.Path`, resolved against the repo ROOT when
    relative — the same convention `engine.storyboard_render._out_dir_path` uses, so a
    caller can pass either a project-relative string (`'cards/frames'`) or an already
    absolute path (a test's `tmp_path`) and get the right directory either way.
    """
    p = pathlib.Path(path_like)
    return p if p.is_absolute() else ROOT / p


# --------------------------------------------------------------------------- #
# small formatting helpers (markdown-table-safe, tools/pdf/md2pdf.mjs's table
# parser splits a row on literal '|' with no escaping and stops at the first
# line without one, so every cell must be a single line with no bare '|')
# --------------------------------------------------------------------------- #

def _flat(value) -> str:
    if value is None:
        return ''
    return str(value).replace('\r', ' ').replace('\n', ' ').replace('|', '/').strip()


def _md_table(headers: list, rows: list) -> str:
    lines = [
        '| ' + ' | '.join(_flat(h) for h in headers) + ' |',
        '|' + '|'.join(['---'] * len(headers)) + '|',
    ]
    for row in rows:
        lines.append('| ' + ' | '.join(_flat(c) for c in row) + ' |')
    return '\n'.join(lines)


def _fmt_int(n) -> str:
    try:
        return f'{int(round(float(n))):,}'
    except (TypeError, ValueError):
        return _flat(n)


def _fmt_pct(x) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return _flat(x)
    if v < 0:
        return 'n/a'  # -1.0 is the "not measured" sentinel used in references (source returned no count)
    return f'{v * 100:.1f}%'


def _fmt_x(x) -> str:
    try:
        return f'{float(x):.1f}x'
    except (TypeError, ValueError):
        return _flat(x)


def _truncate(text, n: int = 90) -> str:
    text = _flat(text)
    return text if len(text) <= n else text[: n - 1].rstrip() + '…'


# --------------------------------------------------------------------------- #
# card_markdown() — one production-ready creative brief per card
# --------------------------------------------------------------------------- #

def _strategy_section(card: dict) -> str:
    strat = card.get('strategy') or {}
    filt = strat.get('filter') or {}
    lines = [
        '## Strategy', '',
        f"**Format:** {strat.get('format') or card.get('format', '')}", '',
        f"**Concept.** {strat.get('concept', '')}", '',
        f"**Audience.** {strat.get('audience', '')}", '',
        f"**Objective.** {strat.get('objective', '')}", '',
        f"**Positioning.** {strat.get('positioning', '')}", '',
        f"**Pain.** {strat.get('pain', '')}", '',
        f"**Promise.** {strat.get('promise', '')}", '',
        f"**Rationale.** {strat.get('rationale', '')}", '',
        _md_table(['Filter', 'Answer'], [
            ['Process', filt.get('process', '')],
            ['Friction', filt.get('friction', '')],
            ['AI boundary', filt.get('ai_boundary', '')],
            ['Next action', filt.get('next_action', '')],
        ]), '',
    ]
    return '\n'.join(lines)


def _used_hook_text(card: dict):
    """The hook actually carried into the script: the text of the script section
    whose role is 'hook' — matched against `hooks[].text` verbatim, since the card
    format keeps no separate 'chosen hook' pointer (SPEC §8).
    """
    for sec in (card.get('script') or {}).get('sections') or []:
        if sec.get('role') == 'hook':
            return sec.get('text')
    return None


def _hooks_section(card: dict) -> str:
    used_text = _used_hook_text(card)
    lines = ['## Hooks', '']
    for i, h in enumerate(card.get('hooks') or [], start=1):
        used = bool(used_text) and h.get('text') == used_text
        kind = 'question' if h.get('is_question') else 'statement'
        marker = ' — **USED IN SCRIPT**' if used else ''
        lines.append(f"{i}. **[{h.get('type', 'other')}]** ({kind}){marker}")
        lines.append(f"   {h.get('text', '')}")
        lines.append('')
    return '\n'.join(lines)


def _ref_row(r: dict) -> list:
    code = r.get('code', '')
    url = r.get('url') or (f'https://www.instagram.com/reel/{code}/' if code else '')
    link = f'[{code}]({url})' if code else ''
    return [
        link, r.get('username', ''), r.get('function', ''),
        _fmt_int(r.get('play')), _fmt_int(r.get('creator_median_play')),
        _fmt_x(r.get('view_lift')), _fmt_pct(r.get('share_rate')), _fmt_pct(r.get('save_rate')),
        r.get('reason', ''),
    ]


def _references_section(card: dict) -> str:
    refs = card.get('references') or []
    headers = ['Reel', 'Creator', 'Function', 'Plays', 'Creator median', 'View lift',
               'Share rate', 'Save rate', 'Reason']
    lines = ['## Reference reels', '', _md_table(headers, [_ref_row(r) for r in refs]), '']
    for r in refs:
        code = r.get('code', '')
        lines.append(f"**{code}** ({r.get('username', '')}, {r.get('function', '')})")
        ut = r.get('useful_transcript') or {}
        uf = r.get('useful_frame') or {}
        if ut.get('quote'):
            lines.append(f"- Transcript ({ut.get('beat_id', '')}): “{ut.get('quote', '')}”")
        if uf.get('what'):
            lines.append(f"- Frame ({uf.get('scene_id', '')}): {uf.get('what', '')}")
        lines.append(f"- Transformed: {r.get('transformed_how', '')}")
        lines.append('')
    return '\n'.join(lines)


def _script_section(card: dict) -> str:
    script = card.get('script') or {}
    sections = script.get('sections') or []
    full_text = ' '.join(s.get('text', '') for s in sections)
    rows = []
    cum = 0.0
    for s in sections:
        cum += float(s.get('seconds') or 0)
        rows.append([s.get('role', ''), s.get('words', ''), s.get('seconds', ''), f'{cum:.1f}s'])
    lines = [
        '## Script', '',
        full_text, '',
        f"*{script.get('total_words', 0)} words / {script.get('total_s', 0)}s "
        f"({script.get('target_wps', '')} wps target) — tone: {script.get('tone', '')}; "
        f"emotional effect: {script.get('emotional_effect', '')}*", '',
        _md_table(['Role', 'Words', 'Seconds', 'Cumulative'], rows), '',
    ]
    return '\n'.join(lines)


def _source_inspiration(items) -> str:
    items = items or []
    if not items:
        return '—'
    return '; '.join(f"{it.get('code', '')} ({it.get('why', '')})" for it in items)


def _storyboard_table(card: dict) -> str:
    headers = ['Time', 'Script (truncated)', 'Role', 'Frame type', 'Layout', 'Visual',
               'Overlay text', 'Transition', 'Source inspiration', 'Asset status']
    rows = []
    for sc in sorted(card.get('storyboard') or [], key=lambda s: s.get('idx', 0)):
        rows.append([
            f"{float(sc.get('start_s') or 0):.1f}-{float(sc.get('end_s') or 0):.1f}s",
            _truncate(sc.get('script_text'), 90),
            sc.get('script_role', ''), sc.get('frame_type', ''), sc.get('layout', ''),
            sc.get('visual', ''), sc.get('overlay_text', ''), sc.get('transition', ''),
            _source_inspiration(sc.get('source_inspiration')),
            sc.get('asset_status', ''),
        ])
    return _md_table(headers, rows)


def _frame_path(frames_path: pathlib.Path, card_id: str, scene: dict, idx: int) -> str:
    scene_id = scene.get('scene_id') or f'S{idx:02d}'
    return str(frames_path / f'{card_id}_{scene_id}.png')


def _storyboard_grid(card: dict, frames_path: pathlib.Path) -> str:
    scenes = sorted(card.get('storyboard') or [], key=lambda s: s.get('idx', 0))
    card_id = card['card_id']
    paths = [_frame_path(frames_path, card_id, sc, sc.get('idx', i)) for i, sc in enumerate(scenes)]
    lines = []
    for i in range(0, len(paths), 3):
        chunk = paths[i:i + 3]
        lines.append(f"::grid {'|'.join(chunk)}::")
    return '\n'.join(lines)


def _storyboard_section(card: dict, frames_dir) -> str:
    frames_path = _resolve_dir(frames_dir)
    sheet_path = frames_path / f"{card['card_id']}_sheet.png"
    lines = [
        '## Storyboard', '',
        _storyboard_table(card), '',
        _storyboard_grid(card, frames_path), '',
        f'![Contact sheet]({sheet_path})', '',
    ]
    return '\n'.join(lines)


def _editing_section(card: dict) -> str:
    ed = card.get('editing') or {}
    lines = ['## Editing', '']
    for label, key in [
        ('Cut timing', 'cut_timing'), ('Captions', 'captions'), ('Emphasis', 'emphasis'),
        ('Zooms', 'zooms'), ('Motion', 'motion'),
    ]:
        lines.append(f"- **{label}:** {ed.get(key, '')}")
    reqs = ed.get('assets_required') or []
    if reqs:
        lines.append('- **Assets required:**')
        for r in reqs:
            lines.append(f'  - {r}')
    lines.append('')
    return '\n'.join(lines)


def _claims_section(card: dict) -> str:
    headers = ['Claim', 'State', 'Source']
    rows = [[c.get('text', ''), c.get('state', ''), c.get('source', '')] for c in card.get('claims') or []]
    return '\n'.join(['## Claims', '', _md_table(headers, rows), ''])


def _traceability_section(card: dict) -> str:
    tr = card.get('traceability') or {}
    insights = ', '.join(tr.get('insights') or [])
    lines = [
        '## Traceability', '',
        f"- **Insights:** {insights}",
        f"- **Hypothesis:** {tr.get('hypothesis', '')}",
        f"- **Evidence summary:** {tr.get('evidence_summary', '')}",
        f"- **Original synthesis:** {tr.get('original_synthesis', '')}",
        f"- **Why better than generic:** {tr.get('why_better_than_generic', '')}",
        '',
    ]
    return '\n'.join(lines)


def _review_section(card: dict) -> str:
    rv = card.get('review') or {}
    findings = rv.get('findings') or []
    lines = [
        '## Review', '',
        f"- **Version:** {rv.get('version', '')}",
        f"- **Revised:** {'yes' if rv.get('revised') else 'no'}",
    ]
    if findings:
        lines.append('- **Findings:**')
        for f in findings:
            lines.append(f'  - {f}')
    lines.append('')
    return '\n'.join(lines)


def _validation_path(card_id: str) -> pathlib.Path:
    # Fixed, repo-relative location — the one `engine.edl` writes its EDL to
    # (`cards/edl/<card_id>.json`); a sibling `<card_id>.validation.json` is where a
    # future `validate_with_node()`-shaped result would be persisted (not written by
    # any owner's module yet, see cards/README.md's `engine.edl.validate_with_node`).
    return ROOT / 'cards' / 'edl' / f'{card_id}.validation.json'


def _validation_summary(card_id: str) -> str:
    p = _validation_path(card_id)
    if not p.exists():
        return f'not yet validated (no {p.name} next to the EDL)'
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        return f'validation file unreadable: {exc}'
    if isinstance(data, dict) and 'ok' in data:
        status = 'PASS' if data.get('ok') else ('SKIPPED' if data.get('skipped') else 'FAIL')
        extra = data.get('reason') or data.get('stderr') or ''
        return f"{status}{' — ' + _flat(extra) if extra else ''}"
    return _flat(json.dumps(data, sort_keys=True))


def _production_section(card: dict) -> str:
    lines = [
        '## Production state', '',
        f"- **Status:** {card.get('status', '')}",
        f"- **EDL path:** {card.get('remotion_edl_path') or '—'}",
        f"- **Remotion validation:** {_validation_summary(card['card_id'])}",
        '',
    ]
    return '\n'.join(lines)


def card_markdown(card: dict, frames_dir='cards/frames') -> str:
    """One production-ready creative-brief chapter for `card` (SPEC §8 shape).

    A single leading `# <card_id> — <title>` heading (so `tools/pdf/md2pdf.mjs`
    starts this card on a new page, per `tools/pdf/README.md`'s "`# ` starts a new
    page"); every section below it is `##` and stays on the same page run.
    `frames_dir` is where `engine.storyboard_render.render_card()` wrote this card's
    frames (relative to the repo root, or already absolute) — image references are
    built from `<frames_dir>/<card_id>_<scene_id>.png`, independent of whatever
    `asset_path` happens to be recorded on each scene in the JSON.
    """
    parts = [
        f"# {card['card_id']} — {card.get('title', '')}", '',
        _strategy_section(card),
        _hooks_section(card),
        _references_section(card),
        _script_section(card),
        _storyboard_section(card, frames_dir),
        _editing_section(card),
        _claims_section(card),
        _traceability_section(card),
        _review_section(card),
        _production_section(card),
    ]
    return '\n'.join(parts).rstrip() + '\n'


# --------------------------------------------------------------------------- #
# intro_markdown() — front chapter
# --------------------------------------------------------------------------- #

def _card_row(card: dict) -> list:
    script = card.get('script') or {}
    tr = card.get('traceability') or {}
    return [
        card.get('card_id', ''), card.get('title', ''), card.get('format', ''),
        f"{float(script.get('total_s') or 0):.1f}",
        str(script.get('total_words', 0)),
        str(len(card.get('references') or [])),
        tr.get('hypothesis') or card.get('hypothesis_id', ''),
        card.get('status', ''),
    ]


def intro_markdown(cards: list, run_meta: dict = None) -> str:
    """Front chapter: how to read a card, the full card table, the house shooting
    rules from `PRODUCTION.md` in five lines, and the `asset_status` legend.
    `run_meta` is an optional `{'date', 'commit'}` (or similar) dict identifying this
    build; missing keys fall back to today's date / an 'unknown' commit.
    """
    run_meta = run_meta or {}
    date = run_meta.get('date') or datetime.date.today().isoformat()
    commit = run_meta.get('commit') or 'unknown'
    n = len(cards)

    lines = [
        f'# {BOOK_TITLE}', '',
        f'Generated {date} (commit {commit}). {n} card(s) in this book.', '',
        '## How to read a card', '',
        'Each chapter after this one is one shooting card, in the order of the table below, '
        'and is a production-ready creative brief, not a summary. Strategy states why this '
        'exact reel over any other, including the four-question filter it had to pass. Hooks '
        'lists the three candidates considered and marks the one actually carried into the '
        'script. Reference reels names the outside reels whose shape was borrowed and exactly '
        'what was taken from each — the transcript quote and frame that earned it a place, '
        'and how it was transformed rather than copied. Script is the full spoken text plus '
        'per-section timing. Storyboard is the frame-by-frame shot list, the rendered '
        'placeholder frames in scene order, and the contact sheet. Editing, Claims, '
        'Traceability and Review record how the card is cut, what it may claim on screen, why '
        'it exists, and what the review pass changed. Production state is the current '
        'shoot/render status.', '',
        '## Cards in this book', '',
        _md_table(
            ['ID', 'Title', 'Format', 'Total s', 'Words', 'Refs', 'Hypothesis', 'Status'],
            [_card_row(c) for c in cards],
        ), '',
        '## Template and production rules (PRODUCTION.md)', '',
        '- Fixed: one location and light, one banner position and typeface held for the whole '
        'reel, one caption style, the screen shown full-frame, 50–70 seconds, one closing line.',
        '- Variable: who is on camera and how many — one, both, or one after the other.',
        '- The only cut allowed is a change of speaker; everything else is shot in one take.',
        "- Target length is 50–70s (winners' median 55s vs 47s for the rest); under 20s or "
        'over 90s tracks with the losing side of the corpus.',
        '- A card is not shoot-ready until every reference and claim is checked and the '
        "storyboard is reviewed — see each card's Review and Production state sections.", '',
        '## Asset legend', '',
        '`asset_status: "template"` on a storyboard frame is a rendered placeholder from '
        '`engine.storyboard_render` (dashed box, `[SHOT: ...]` / `[SCREEN: ...]` label — '
        'never a stock photo, never an AI-generated image) — replace it with the owner\'s '
        'real footage per `cards/README.md` before this card is shot for real. `missing` = '
        'nothing rendered yet; `ready` = real footage bound in; `generated` = an AI-generated '
        'visual (not used anywhere in this codebase).', '',
    ]
    return '\n'.join(lines)


# --------------------------------------------------------------------------- #
# build() — write the whole book to disk
# --------------------------------------------------------------------------- #

def _load_card_file(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def _load_cards(cards_dir=DEFAULT_CARDS_DIR, include_example: bool = False) -> list:
    """Every card JSON directly under `cards_dir` (non-recursive — `cards/frames` and
    `cards/edl` are subdirectories, not cards), keyed and de-duplicated by `card_id`,
    sorted by `card_id`. The example fixture (`C-2026-09-11-EX`) is added from
    `tests/fixtures/card-example.json` when `include_example=True` and not already
    present in `cards_dir`, and is otherwise always excluded — even if some copy of
    it happens to sit in `cards_dir` (e.g. a test fixture copy).
    """
    cards_path = _resolve_dir(cards_dir)
    cards = {}
    if cards_path.exists():
        for p in sorted(cards_path.glob('*.json')):
            try:
                card = _load_card_file(p)
            except (OSError, ValueError):
                continue
            cid = card.get('card_id')
            if cid:
                cards[cid] = card

    if include_example:
        if EXAMPLE_CARD_ID not in cards and EXAMPLE_CARD_PATH.exists():
            cards[EXAMPLE_CARD_ID] = _load_card_file(EXAMPLE_CARD_PATH)
    else:
        cards.pop(EXAMPLE_CARD_ID, None)

    return [cards[cid] for cid in sorted(cards)]


def build(out_md_dir=DEFAULT_OUT_DIR, cards_dir=DEFAULT_CARDS_DIR, include_example: bool = False,
          frames_dir=DEFAULT_FRAMES_DIR, run_meta: dict = None) -> list:
    """Write `00-intro.md` plus one `NN-<card_id>.md` chapter per card (sorted by
    `card_id`) under `out_md_dir`. Returns the list of file paths written, in chapter
    order — this is exactly the `md_files` list `engine.pdf_build.build()` expects.
    """
    out_path = _resolve_dir(out_md_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    cards = _load_cards(cards_dir=cards_dir, include_example=include_example)

    written = []
    intro_path = out_path / '00-intro.md'
    intro_path.write_text(intro_markdown(cards, run_meta), encoding='utf-8')
    written.append(str(intro_path))

    for i, card in enumerate(cards, start=1):
        fpath = out_path / f"{i:02d}-{card['card_id']}.md"
        fpath.write_text(card_markdown(card, frames_dir=frames_dir), encoding='utf-8')
        written.append(str(fpath))

    return written


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        description='Build the M2 Lab card book (one creative-brief markdown chapter per card).')
    parser.add_argument('--out-dir', default=DEFAULT_OUT_DIR, help='markdown output directory')
    parser.add_argument('--cards-dir', default=DEFAULT_CARDS_DIR, help='directory of card-v2 JSON files')
    parser.add_argument('--frames-dir', default=DEFAULT_FRAMES_DIR,
                         help='rendered storyboard frames directory (engine.storyboard_render)')
    parser.add_argument('--include-example', action='store_true',
                         help=f'include the fictional example card ({EXAMPLE_CARD_ID})')
    parser.add_argument('--pdf', nargs='?', const=DEFAULT_PDF_PATH, default=None,
                         help=f'also build a PDF via engine.pdf_build (default path: {DEFAULT_PDF_PATH})')
    args = parser.parse_args(argv)

    run_meta = {'date': datetime.date.today().isoformat(), 'commit': git_commit() or 'unknown'}
    md_files = build(
        out_md_dir=args.out_dir, cards_dir=args.cards_dir, include_example=args.include_example,
        frames_dir=args.frames_dir, run_meta=run_meta,
    )
    n_cards = max(len(md_files) - 1, 0)
    print(f'{len(md_files)} markdown file(s) written under {args.out_dir} ({n_cards} card(s))')

    if args.pdf:
        from engine.pdf_build import build as pdf_build_fn
        result = pdf_build_fn(
            md_files, out_pdf=args.pdf, title=BOOK_TITLE,
            subtitle=f"{n_cards} card(s) — {run_meta['date']} — run {run_meta['commit']}",
            date=run_meta['date'],
        )
        print(json.dumps(result, indent=2))

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
