"""Finalize cards: validate → render storyboard frames → save to DB → EDL → node validation
→ state trace. One command turns a reviewed card JSON into every downstream artifact.

    python3 -m engine.cards_pipeline cards/C-2026-09-12-01.json [more.json ...]
    python3 -m engine.cards_pipeline --all            # every cards/C-*.json except the example

Each step is a `jobs` row under one `cards` run so the chain card → script → review →
frame plan → frames → video-ready is reconstructible from the database (spec §7, §95).
"""
import argparse
import glob
import json
import pathlib
import sys

from engine import cards_v2, db_util, edl as edl_mod, storyboard_render, state

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAMPLE_ID = 'C-2026-09-11-EX'


def finalize(con, path, run_id, *, render=True, node=True):
    card = json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
    cid = card['card_id']
    result = {'card_id': cid, 'path': str(path)}

    with state.job(con, run_id, 'card', cid, 'CARD_GENERATION', agent='orchestrator',
                   input_refs_json=json.dumps({'hypothesis_id': card.get('hypothesis_id')})) as j:
        errors = cards_v2.validate(card)
        hard = [e for e in errors if not e.startswith('WARNING')]
        result['validation_errors'] = hard
        result['validation_warnings'] = [e for e in errors if e.startswith('WARNING')]
        if hard:
            j.set(validation='FAILED', error='; '.join(hard)[:900])
            raise ValueError(f'{cid}: {len(hard)} validation error(s)')
        j.set(validation='OK')

    with state.job(con, run_id, 'card', cid, 'SCRIPT_GENERATION', agent='script-writer',
                   prompt_version='sw-v1') as j:
        j.set(output_refs_json=json.dumps({'script_version': card['script'].get('version', 1),
                                           'total_s': card['script'].get('total_s'),
                                           'total_words': card['script'].get('total_words')}))

    review = card.get('review') or {}
    with state.job(con, run_id, 'card', cid, 'SCRIPT_REVIEW', agent='script-reviewer') as j:
        if not review.get('findings'):
            j.skip('no reviewer findings recorded')
        else:
            j.set(output_refs_json=json.dumps({'review_version': review.get('version'),
                                               'revised': bool(review.get('revised')),
                                               'findings_n': len(review.get('findings') or [])}))

    with state.job(con, run_id, 'card', cid, 'FRAME_PLAN', agent='script-writer') as j:
        j.set(output_refs_json=json.dumps({'scenes_n': len(card.get('storyboard') or [])}))

    if render:
        with state.job(con, run_id, 'card', cid, 'FRAME_GENERATION', provider='template-pillow',
                       model='storyboard_render') as j:
            paths = storyboard_render.render_card(card, out_dir='cards/frames')
            result['frames'] = paths
            j.set(output_refs_json=json.dumps({'frames': paths}))

    # persist card + scenes + script versions (re-saves the JSON with asset paths filled)
    saved = cards_v2.save(con, card, json_dir='cards')
    result['saved'] = str(saved)

    with state.job(con, run_id, 'card', cid, 'VIDEO_GENERATION_READY', provider='remotion') as j:
        e = edl_mod.card_to_edl(card)
        edl_dir = ROOT / 'cards' / 'edl'
        edl_dir.mkdir(parents=True, exist_ok=True)
        edl_path = edl_dir / f'{cid}.json'
        edl_path.write_text(json.dumps(e, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
        result['edl'] = str(edl_path)
        val = edl_mod.validate_with_node(edl_path) if node else {'ok': None, 'skipped': True}
        (edl_dir / f'{cid}.validation.json').write_text(
            json.dumps({'card_id': cid, 'edl': str(edl_path.relative_to(ROOT)),
                        'contract': 'm2.remotion-edl.v1', 'render_mode': e.get('render_mode'),
                        'duration_frames': e.get('duration_frames'), 'fps': e.get('fps'),
                        'result': val, 'checked_at': db_util.now()}, indent=1) + '\n', encoding='utf-8')
        result['edl_validation'] = val
        j.set(validation='OK' if val.get('ok') else ('SKIPPED' if val.get('skipped') else 'FAILED'),
              output_refs_json=json.dumps({'edl': str(edl_path.relative_to(ROOT)),
                                           'duration_frames': e.get('duration_frames')}))
        if val.get('skipped'):
            j.skip('node or studio/remotion/contract.mjs not available — EDL written, not validated')
        elif val.get('ok') is False:
            raise RuntimeError(f'{cid}: EDL failed contract validation: {val}')
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('paths', nargs='*')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--db', default=None)
    ap.add_argument('--no-render', action='store_true')
    ap.add_argument('--no-node', action='store_true')
    a = ap.parse_args(argv)
    paths = list(a.paths)
    if a.all:
        paths += [p for p in sorted(glob.glob(str(ROOT / 'cards' / 'C-*.json'))) if EXAMPLE_ID not in p]
    if not paths:
        ap.error('no card files given')
    con = db_util.connect(a.db) if a.db else db_util.connect()
    run_id = state.start_run(con, 'cards', config={'cards': [str(p) for p in paths]})
    ok, failed = [], []
    for p in paths:
        try:
            r = finalize(con, p, run_id, render=not a.no_render, node=not a.no_node)
            con.commit()
            ok.append(r)
            print(f"{r['card_id']}: saved, {len(r.get('frames', []))} frames, EDL {'OK' if (r['edl_validation'] or {}).get('ok') else r['edl_validation']}"
                  + (f", warnings: {len(r['validation_warnings'])}" if r['validation_warnings'] else ''))
        except Exception as exc:  # noqa: BLE001 - report and continue with the next card
            con.commit()
            failed.append({'path': str(p), 'error': str(exc)})
            print(f'FAILED {p}: {exc}', file=sys.stderr)
    state.finish_run(con, run_id, 'DONE' if not failed else 'FAILED',
                     summary={'ok': [r['card_id'] for r in ok], 'failed': failed})
    con.commit()
    print(f'run {run_id}: {len(ok)} ok, {len(failed)} failed')
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
