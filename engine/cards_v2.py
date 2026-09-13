#!/usr/bin/env python3
"""Card v2: validate, persist and list `cards/<card_id>.json` (SPEC.md §8, §2.9).

A card is authored as a single JSON document (schema `m2radar.card.v2`) and this
module is the only place that (a) checks it against the SPEC §8 shape and the
SPEC §4 closed vocabularies, and (b) mirrors it into the `cards_v2`, `card_scenes`
and `script_versions` tables that `engine/schema.py` created.

    python3 -m engine.cards_v2 validate cards/C-2026-09-11-01.json
    python3 -m engine.cards_v2 save cards/C-2026-09-11-01.json
    python3 -m engine.cards_v2 list

`validate()` returns a flat list of strings. A string starting with ``WARNING: ``
is advisory (e.g. total_s outside the 50-70s sweet spot in PRODUCTION.md) and
never blocks `save()`; anything else is a hard error and `is_valid()` is False
whenever at least one is present. `save()` refuses to write a card with hard
errors.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from engine.db_util import ROOT, canonical_json, loads, now, table_exists

# --------------------------------------------------------------------------- #
# Closed vocabularies (SPEC §4)
# --------------------------------------------------------------------------- #

FRAME_TYPES = [
    'A_ROLL_TALKING_HEAD', 'A_ROLL_CLOSE_UP', 'A_ROLL_MEDIUM', 'A_ROLL_WIDE',
    'B_ROLL_CONTEXT', 'B_ROLL_PRODUCT', 'B_ROLL_PROCESS', 'SCREEN_RECORDING', 'SCREENSHOT',
    'UI_DEMO', 'SPLIT_SCREEN', 'TEXT_ONLY', 'DATA_VISUAL', 'MEME', 'PROOF_VISUAL',
    'HOOK_VISUAL', 'CTA_VISUAL', 'TRANSITION', 'MOTION_GRAPHIC', 'OVERLAY', 'UNKNOWN',
]
HOOK_TYPES = [
    'question', 'bold_claim', 'contrarian', 'curiosity_gap', 'number_stat', 'story_open',
    'problem_call_out', 'demo_first', 'result_first', 'warning_fear', 'identity_call',
    'list_promise', 'other',
]
CTA_TYPES = [
    'comment_keyword', 'follow', 'save_share', 'link_in_bio', 'dm', 'free_resource',
    'next_video', 'question_to_audience', 'none',
]
# Layouts a scene may carry in `card_scenes.layout` / the Remotion EDL (contract.mjs).
# storyboard_render.py additionally accepts 'text' as a rendering-time alias for
# 'motion_graphic'; that alias is intentionally NOT part of this closed set because
# the EDL contract only ever accepts these four (cards/README.md explains why).
LAYOUTS = ['a_roll', 'split_screen', 'demo', 'motion_graphic']
CLAIM_STATES = ['OBSERVED', 'PLANNED', 'TO_MEASURE', 'MISSING']
CARD_STATUSES = ['DRAFT', 'REVIEWED', 'APPROVED', 'SHOT', 'PUBLISHED', 'DROPPED']
CARD_SCHEMA = 'm2radar.card.v2'

REF_PERFORMANCE_FIELDS = ['play', 'creator_median_play', 'view_lift', 'share_rate', 'save_rate']
STRATEGY_FIELDS = ['concept', 'audience', 'objective', 'positioning', 'pain', 'promise', 'rationale']
FILTER_FIELDS = ['process', 'friction', 'ai_boundary', 'next_action']  # the four mandatory fields
SCRIPT_FIELDS = ['version', 'sections', 'total_words', 'total_s', 'target_wps', 'tone']
REVIEW_FIELDS = ['version', 'findings', 'revised']

TOTAL_S_HARD_MIN, TOTAL_S_HARD_MAX = 20.0, 120.0          # SPEC §8, hard bound
TOTAL_S_SOFT_MIN, TOTAL_S_SOFT_MAX = 50.0, 70.0           # PRODUCTION.md sweet spot -> warning only
SCENE_BOUNDARY_TOLERANCE_S = 0.05                          # adjacent scene start/end drift allowed
SCENE_TOTAL_TOLERANCE_S = 0.5                              # storyboard-vs-script total_s tolerance


# --------------------------------------------------------------------------- #
# validate()
# --------------------------------------------------------------------------- #

def _require(d, key, errors, where):
    if not isinstance(d, dict) or key not in d or d.get(key) in (None, ''):
        errors.append(f'{where}: missing required key {key!r}')
        return None
    return d[key]


def _non_empty_str(value, errors, where):
    if not isinstance(value, str) or not value.strip():
        errors.append(f'{where}: expected a non-empty string, got {value!r}')
        return False
    return True


def _check_enum(value, allowed, errors, where):
    if value not in allowed:
        errors.append(f'{where}: {value!r} is not one of the closed vocabulary {allowed}')
        return False
    return True


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate(card: dict) -> list[str]:
    """Validate a card-v2 dict against SPEC §8 / §4. Returns a list of messages.

    Entries starting with ``WARNING: `` are advisory. Use `is_valid(errors)` (or
    filter them out yourself) to decide pass/fail.
    """
    errors: list[str] = []
    if not isinstance(card, dict):
        return ['card: top-level JSON must be an object']

    # ---- top-level shape --------------------------------------------------
    if card.get('schema') != CARD_SCHEMA:
        errors.append(f"card.schema: expected {CARD_SCHEMA!r}, got {card.get('schema')!r}")
    _non_empty_str(card.get('card_id'), errors, 'card.card_id')
    _non_empty_str(card.get('format'), errors, 'card.format')
    _non_empty_str(card.get('title'), errors, 'card.title')
    if 'status' in card and card['status'] not in CARD_STATUSES:
        errors.append(f"card.status: {card.get('status')!r} is not one of {CARD_STATUSES}")

    for key in ('strategy', 'references', 'hooks', 'script', 'storyboard', 'editing',
                'claims', 'traceability', 'review'):
        if key not in card:
            errors.append(f'card: missing required top-level key {key!r}')

    # ---- strategy + the four mandatory filter fields ----------------------
    strategy = card.get('strategy') or {}
    if not isinstance(strategy, dict):
        errors.append('card.strategy: must be an object')
        strategy = {}
    for f in STRATEGY_FIELDS:
        _require(strategy, f, errors, 'card.strategy')
    filt = strategy.get('filter')
    if not isinstance(filt, dict):
        errors.append('card.strategy.filter: must be an object with process/friction/ai_boundary/next_action')
        filt = {}
    for f in FILTER_FIELDS:
        v = _require(filt, f, errors, 'card.strategy.filter')
        if v is not None:
            _non_empty_str(v, errors, f'card.strategy.filter.{f}')

    # ---- references ---------------------------------------------------------
    references = card.get('references')
    if isinstance(references, list):
        if not references:
            errors.append('card.references: must not be empty')
        for i, ref in enumerate(references):
            where = f'card.references[{i}]'
            if not isinstance(ref, dict):
                errors.append(f'{where}: must be an object')
                continue
            for f in ('code', 'url', 'function', 'reason'):
                v = _require(ref, f, errors, where)
                if v is not None:
                    _non_empty_str(v, errors, f'{where}.{f}')
            for f in REF_PERFORMANCE_FIELDS:
                # share_rate / save_rate may be null when the source never returned the count
                # (saves are NULL for some reels in every snapshot). Never fabricate a 0 there.
                if f in ('share_rate', 'save_rate') and f in ref and ref.get(f) is None:
                    continue
                if f not in ref or not _is_number(ref.get(f)):
                    errors.append(f'{where}.{f}: missing or not a number ({ref.get(f)!r})')
    elif references is not None:
        errors.append('card.references: must be a list')

    # ---- hooks: >=2, each with a closed-vocab type + is_question flag ------
    hooks = card.get('hooks')
    if isinstance(hooks, list):
        if len(hooks) < 2:
            errors.append(f'card.hooks: need >=2 candidate hooks, got {len(hooks)}')
        for i, h in enumerate(hooks):
            where = f'card.hooks[{i}]'
            if not isinstance(h, dict):
                errors.append(f'{where}: must be an object')
                continue
            _non_empty_str(h.get('text'), errors, f'{where}.text')
            if 'type' not in h:
                errors.append(f'{where}.type: missing')
            else:
                _check_enum(h['type'], HOOK_TYPES, errors, f'{where}.type')
            if not isinstance(h.get('is_question'), bool):
                errors.append(f'{where}.is_question: missing or not a boolean')
    elif hooks is not None:
        errors.append('card.hooks: must be a list')

    # ---- script -------------------------------------------------------------
    script = card.get('script')
    section_roles: set[str] = set()
    total_s = None
    if isinstance(script, dict):
        for f in SCRIPT_FIELDS:
            _require(script, f, errors, 'card.script')
        sections = script.get('sections')
        if isinstance(sections, list):
            if not sections:
                errors.append('card.script.sections: must not be empty')
            for i, sec in enumerate(sections):
                where = f'card.script.sections[{i}]'
                if not isinstance(sec, dict):
                    errors.append(f'{where}: must be an object')
                    continue
                _require(sec, 'role', errors, where)
                _require(sec, 'text', errors, where)
                if 'role' in sec:
                    section_roles.add(sec['role'])
        elif sections is not None:
            errors.append('card.script.sections: must be a list')
        total_s = script.get('total_s')
        if not _is_number(total_s):
            errors.append(f'card.script.total_s: missing or not a number ({total_s!r})')
        else:
            if not (TOTAL_S_HARD_MIN <= total_s <= TOTAL_S_HARD_MAX):
                errors.append(
                    f'card.script.total_s: {total_s} outside the hard bound '
                    f'[{TOTAL_S_HARD_MIN}, {TOTAL_S_HARD_MAX}]s')
            elif not (TOTAL_S_SOFT_MIN <= total_s <= TOTAL_S_SOFT_MAX):
                errors.append(
                    f'WARNING: card.script.total_s: {total_s}s is outside the 50-70s sweet '
                    f'spot (PRODUCTION.md: winners median 55s)')
    elif script is not None:
        errors.append('card.script: must be an object')

    # ---- storyboard: closed vocab, contiguity, section coverage -----------
    storyboard = card.get('storyboard')
    if isinstance(storyboard, list):
        if not storyboard:
            errors.append('card.storyboard: must not be empty')
        scenes = sorted(
            (s for s in storyboard if isinstance(s, dict) and 'idx' in s), key=lambda s: s['idx'])
        expected_idx = list(range(len(storyboard)))
        actual_idx = [s.get('idx') for s in storyboard if isinstance(s, dict)]
        if sorted(actual_idx) != expected_idx:
            errors.append(
                f'card.storyboard: idx values must be exactly 0..{len(storyboard)-1}, got {sorted(actual_idx)}')

        scene_roles: set[str] = set()
        prev_end = 0.0
        for i, s in enumerate(scenes):
            where = f'card.storyboard[idx={s.get("idx")}]'
            if not isinstance(s, dict):
                errors.append(f'{where}: must be an object')
                continue
            start_s, end_s = s.get('start_s'), s.get('end_s')
            if not _is_number(start_s) or not _is_number(end_s):
                errors.append(f'{where}: start_s/end_s missing or not numbers')
            else:
                if end_s <= start_s:
                    errors.append(f'{where}: end_s ({end_s}) must be greater than start_s ({start_s})')
                if abs(start_s - prev_end) > SCENE_BOUNDARY_TOLERANCE_S:
                    errors.append(
                        f'{where}: start_s ({start_s}) does not follow the previous scene\'s '
                        f'end_s ({prev_end}) within {SCENE_BOUNDARY_TOLERANCE_S}s -> not contiguous')
                prev_end = end_s
            if 'frame_type' not in s:
                errors.append(f'{where}.frame_type: missing')
            else:
                _check_enum(s['frame_type'], FRAME_TYPES, errors, f'{where}.frame_type')
            if 'layout' not in s:
                errors.append(f'{where}.layout: missing')
            else:
                _check_enum(s['layout'], LAYOUTS, errors, f'{where}.layout')
            if 'cta_type' in s and s['cta_type'] is not None:
                _check_enum(s['cta_type'], CTA_TYPES, errors, f'{where}.cta_type')
            if s.get('script_role'):
                scene_roles.add(s['script_role'])

        if total_s is not None and _is_number(total_s):
            if abs(prev_end - total_s) > SCENE_TOTAL_TOLERANCE_S:
                errors.append(
                    f'card.storyboard: scenes cover 0..{prev_end}s but script.total_s is '
                    f'{total_s}s (tolerance {SCENE_TOTAL_TOLERANCE_S}s)')

        missing_roles = section_roles - scene_roles
        if missing_roles:
            errors.append(
                f'card.storyboard: script section role(s) {sorted(missing_roles)} have no '
                f'matching storyboard scene (script_role)')
    elif storyboard is not None:
        errors.append('card.storyboard: must be a list')

    if 'cta_type' in card and card['cta_type'] is not None:
        _check_enum(card['cta_type'], CTA_TYPES, errors, 'card.cta_type')

    # ---- claims: each needs a closed-vocab state ---------------------------
    claims = card.get('claims')
    if isinstance(claims, list):
        for i, c in enumerate(claims):
            where = f'card.claims[{i}]'
            if not isinstance(c, dict):
                errors.append(f'{where}: must be an object')
                continue
            _require(c, 'text', errors, where)
            if 'state' not in c:
                errors.append(f'{where}.state: missing')
            else:
                _check_enum(c['state'], CLAIM_STATES, errors, f'{where}.state')
    elif claims is not None:
        errors.append('card.claims: must be a list')

    # ---- persona + CTA artefact (Misha, 13 Sep 2026): advisory here, hard finding for the reviewer
    persona = (card.get('strategy') or {}).get('persona') if isinstance(card.get('strategy'), dict) else None
    if not persona:
        errors.append('WARNING: card.strategy.persona: missing — every card is adapted to one persona (personas/*.json)')
    else:
        try:
            from engine import personas as _personas
            known = set(_personas.load_all())
            if known and persona not in known:
                errors.append(f'WARNING: card.strategy.persona: {persona!r} is not one of {sorted(known)}')
        except Exception:
            pass
    cta = card.get('cta')
    if not isinstance(cta, dict) or cta.get('type') != 'comment_keyword' or not cta.get('artefact'):
        errors.append('WARNING: card.cta: every video ends with a comment call-to-action for a real artefact '
                      '({"type":"comment_keyword","keyword":"WORD","artefact":"artefacts/<file>.md"})')
    elif not (ROOT / str(cta['artefact'])).exists():
        errors.append(f"WARNING: card.cta.artefact: {cta['artefact']} does not exist yet — produce it before publishing")

    # ---- review -------------------------------------------------------------
    review = card.get('review')
    if isinstance(review, dict):
        for f in REVIEW_FIELDS:
            _require(review, f, errors, 'card.review')
        if 'revised' in review and not isinstance(review['revised'], bool):
            errors.append('card.review.revised: must be a boolean')
    elif review is not None:
        errors.append('card.review: must be an object')

    return errors


def is_valid(errors: list[str]) -> bool:
    """True when `errors` (as returned by `validate()`) has no hard error."""
    return not any(not e.startswith('WARNING: ') for e in errors)


# --------------------------------------------------------------------------- #
# save() / load_all() / summary_table()
# --------------------------------------------------------------------------- #

def _card_path(card_id: str, json_dir) -> pathlib.Path:
    base = pathlib.Path(json_dir)
    if not base.is_absolute():
        base = ROOT / base
    base.mkdir(parents=True, exist_ok=True)
    return base / f'{card_id}.json'


def save(con, card: dict, json_dir='cards') -> pathlib.Path:
    """Validate, write `cards/<card_id>.json`, and mirror into the DB.

    Idempotent: calling it twice with the same card produces the same JSON file
    and the same `cards_v2` row (only `updated_at` changes); `card_scenes` rows
    are replaced wholesale from the current storyboard; `script_versions` rows
    are additive (one row per version, never rewritten).

    Raises ValueError when `validate(card)` reports a hard error.
    """
    errors = validate(card)
    if not is_valid(errors):
        hard = [e for e in errors if not e.startswith('WARNING: ')]
        raise ValueError('card failed validation:\n  ' + '\n  '.join(hard))

    card_id = card['card_id']
    path = _card_path(card_id, json_dir)
    path.write_text(json.dumps(card, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')
    rel_path = str(path.relative_to(ROOT)) if _is_relative_to(path, ROOT) else str(path)

    strategy = card.get('strategy', {}) or {}
    filt = strategy.get('filter', {}) or {}
    script = card.get('script', {}) or {}
    review = card.get('review', {}) or {}
    storyboard = card.get('storyboard', []) or []

    existing = con.execute('SELECT created_at FROM cards_v2 WHERE card_id=?', (card_id,)).fetchone()
    created_at = existing['created_at'] if existing else now()
    updated_at = now()

    assets = [
        {'idx': s.get('idx'), 'scene_id': s.get('scene_id'),
         'asset_status': s.get('asset_status', 'missing'), 'asset_path': s.get('asset_path')}
        for s in storyboard
    ]

    row = dict(
        card_id=card_id, run_id=card.get('run_id'), hypothesis_id=card.get('hypothesis_id'),
        title=card['title'], format=card['format'],
        concept=strategy.get('concept'), audience=strategy.get('audience'),
        objective=strategy.get('objective'), positioning=strategy.get('positioning'),
        pain=strategy.get('pain'), promise=strategy.get('promise'), rationale=strategy.get('rationale'),
        process=filt.get('process'), friction=filt.get('friction'),
        ai_boundary=filt.get('ai_boundary'), next_action=filt.get('next_action'),
        hooks_json=canonical_json(card.get('hooks')),
        script_version=script.get('version', 1), script_json=canonical_json(script),
        total_words=script.get('total_words'), total_s=script.get('total_s'),
        target_wps=script.get('target_wps'), tone=script.get('tone'),
        refs_json=canonical_json(card.get('references')),
        storyboard_version=card.get('storyboard_version', 1),
        editing_json=canonical_json(card.get('editing')),
        assets_json=canonical_json(assets),
        claims_json=canonical_json(card.get('claims')),
        review_json=canonical_json(review),
        status=card.get('status', 'DRAFT'),
        json_path=rel_path, pdf_page=card.get('pdf_page'),
        created_at=created_at, updated_at=updated_at,
    )
    cols = list(row)
    con.execute(
        f'INSERT INTO cards_v2 ({",".join(cols)}) VALUES ({",".join("?" for _ in cols)}) '
        f'ON CONFLICT(card_id) DO UPDATE SET '
        + ','.join(f'{c}=excluded.{c}' for c in cols if c not in ('card_id', 'created_at')),
        [row[c] for c in cols],
    )

    con.execute('DELETE FROM card_scenes WHERE card_id=?', (card_id,))
    for s in storyboard:
        con.execute(
            'INSERT INTO card_scenes (card_id, scene_id, idx, start_s, end_s, script_text, '
            'script_role, frame_type, layout, visual, overlay_text, transition, '
            'source_inspiration_json, asset_status, asset_path, editing_notes) '
            'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (card_id, s.get('scene_id'), s.get('idx'), s.get('start_s'), s.get('end_s'),
             s.get('script_text'), s.get('script_role'), s.get('frame_type'), s.get('layout'),
             s.get('visual'), s.get('overlay_text'), s.get('transition'),
             canonical_json(s.get('source_inspiration')), s.get('asset_status', 'missing'),
             s.get('asset_path'), s.get('editing')),
        )

    # script_versions: additive. `writer` at script.version; when review.revised is true,
    # also a `reviewer` row at script.version+1 carrying the review findings (the card
    # model keeps only the final script text, so both rows reference the same script_json;
    # see cards/README.md "script_versions" for the reasoning).
    writer_version = script.get('version', 1)
    con.execute(
        'INSERT OR IGNORE INTO script_versions (card_id, version, kind, script_json, findings, created_at) '
        'VALUES (?,?,?,?,?,?)',
        (card_id, writer_version, 'writer', canonical_json(script), None, now()))
    if review.get('revised'):
        con.execute(
            'INSERT OR IGNORE INTO script_versions (card_id, version, kind, script_json, findings, created_at) '
            'VALUES (?,?,?,?,?,?)',
            (card_id, writer_version + 1, 'reviewer', canonical_json(script),
             canonical_json(review.get('findings')), now()))

    con.commit()
    return path


def _is_relative_to(path: pathlib.Path, base: pathlib.Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def load_all(con) -> list[dict]:
    """Every `cards_v2` row, JSON columns decoded, with its `card_scenes` attached."""
    rows = con.execute('SELECT * FROM cards_v2 ORDER BY created_at').fetchall()
    out = []
    for r in rows:
        d = dict(r)
        for col in ('hooks_json', 'script_json', 'refs_json', 'editing_json', 'assets_json',
                    'claims_json', 'review_json'):
            key = col[:-5]  # strip _json
            d[key] = loads(d.pop(col))
        scenes = con.execute(
            'SELECT * FROM card_scenes WHERE card_id=? ORDER BY idx', (d['card_id'],)).fetchall()
        d['scenes'] = [dict(s) for s in scenes]
        for s in d['scenes']:
            s['source_inspiration'] = loads(s.pop('source_inspiration_json', None))
        out.append(d)
    return out


def summary_table(con) -> str:
    """id / title / format / total_s / words / status / refs count / scenes count."""
    cards = load_all(con)
    headers = ['card_id', 'title', 'format', 'total_s', 'words', 'status', 'refs', 'scenes']
    widths = [16, 34, 12, 8, 7, 9, 5, 6]
    lines = [''.join(h.ljust(w) for h, w in zip(headers, widths))]
    lines.append('-' * sum(widths))
    for c in cards:
        title = (c.get('title') or '')[:widths[1] - 1]
        n_refs = len(c.get('refs') or [])
        n_scenes = len(c.get('scenes') or [])
        row = [
            str(c.get('card_id') or ''), title, str(c.get('format') or ''),
            f"{c.get('total_s') or 0:.1f}", str(c.get('total_words') or 0),
            str(c.get('status') or ''), str(n_refs), str(n_scenes),
        ]
        lines.append(''.join(v.ljust(w) for v, w in zip(row, widths)))
    text = '\n'.join(lines)
    print(text)
    return text


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _cmd_validate(args):
    card = json.loads(pathlib.Path(args.file).read_text(encoding='utf-8'))
    errors = validate(card)
    if not errors:
        print(f'OK: {args.file} has no errors or warnings')
        return 0
    for e in errors:
        print(e)
    ok = is_valid(errors)
    print(f"\n{'OK' if ok else 'FAILED'}: {sum(1 for e in errors if not e.startswith('WARNING: '))} "
          f"error(s), {sum(1 for e in errors if e.startswith('WARNING: '))} warning(s)")
    return 0 if ok else 1


def _cmd_save(args):
    from engine import schema as engine_schema
    from engine.db_util import connect

    card = json.loads(pathlib.Path(args.file).read_text(encoding='utf-8'))
    con = connect(args.db)
    engine_schema.migrate(con)
    path = save(con, card)
    print(f"saved {card['card_id']} -> {path}")
    n_scenes = con.execute('SELECT COUNT(*) FROM card_scenes WHERE card_id=?', (card['card_id'],)).fetchone()[0]
    print(f'  cards_v2: 1 row, card_scenes: {n_scenes} row(s)')
    return 0


def _cmd_list(args):
    from engine import schema as engine_schema
    from engine.db_util import connect

    con = connect(args.db)
    if table_exists(con, 'cards_v2'):
        engine_schema.migrate(con)
    summary_table(con)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog='python3 -m engine.cards_v2', description=__doc__)
    ap.add_argument('--db', default=None, help='path to radar.db (default: data/radar.db)')
    sub = ap.add_subparsers(dest='cmd', required=True)

    p_val = sub.add_parser('validate', help='validate a card JSON file')
    p_val.add_argument('file')
    p_val.set_defaults(func=_cmd_validate)

    p_save = sub.add_parser('save', help='validate + persist a card JSON file')
    p_save.add_argument('file')
    p_save.set_defaults(func=_cmd_save)

    p_list = sub.add_parser('list', help='print the summary table of all saved cards')
    p_list.set_defaults(func=_cmd_list)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
