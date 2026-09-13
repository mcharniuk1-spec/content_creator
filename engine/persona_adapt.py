#!/usr/bin/env python3
"""Persona adaptation stage: what the radar found this week -> a concept for one persona.

The chain Misha set on 2026-09-13: the radar collects what is popular (Hiker, cards.py
selection), the server agent adapts each found reel to one of the five personas
(`personas/*.json`), every concept ends with a comment call-to-action for a real artefact
(`artefacts/`). This module is the plumbing around the agent step:

    python3 -m engine.persona_adapt export [--codes a,b] [--week]   # write the batch file(s)
    python3 -m engine.persona_adapt run --yes                        # export + run `claude -p` (unattended)
    python3 -m engine.persona_adapt list                             # concepts on disk, validated

Batch input: `data/analysis/input/persona-<run_id>-N.json` — per reel: metrics, caption,
format slot from cards.py, routing hint from engine.personas.match, the ta-v1 / fa-v1
analyses when they exist, else the raw transcript segments. Output contract `pa-v1`:
`data/analysis/concepts/<code>.json` (engine/prompts/persona-adapt.md). Every run writes a
runs row and one CONCEPT_GENERATION job per batch, like engine/analyze_pending.py.
No money is spent here; the agent call is local `claude -p`.
"""
import argparse, json, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import db_util, state, personas as personas_mod      # noqa: E402

INPUT_DIR = ROOT / 'data' / 'analysis' / 'input'
TA_DIR = ROOT / 'data' / 'analysis' / 'transcripts'
FA_DIR = ROOT / 'data' / 'analysis' / 'frames'
OUT_DIR = ROOT / 'data' / 'analysis' / 'concepts'
PROMPT_PATH = ROOT / 'engine' / 'prompts' / 'persona-adapt.md'
PROMPT_VERSION = 'pa-v1'
BATCH_SIZE = 8
AGENT_TIMEOUT_S = 40 * 60
PA_KEYS = {'code', 'analysis_version', 'model', 'persona', 'reject_reason', 'why_this_persona', 'question',
           'format', 'borrow', 'change', 'hook', 'on_screen', 'cta', 'claims', 'confidence', 'notes'}
PERSONA_IDS = tuple(personas_mod.load_all().keys()) if personas_mod.PERSONA_DIR.exists() else ()


def _json_or_none(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def _week_selection(con):
    """This week's radar picks (cards.py), with format slot and pool facts."""
    import cards
    picked, _, _ = cards.select(con)
    return picked


def _reel_item(con, code, fmt=None, why=None):
    r = con.execute("""SELECT r.code, r.username, r.play, r.resh, r.save, r.comm, r.dur, r.ts, r.cap,
                              s.resh_1k, s.save_1k, s.author_median_play, s.z
                         FROM reels r LEFT JOIN scores s ON s.code = r.code AND s.snapshot_id = r.snapshot_id
                                                        AND s.weights = 'ig'
                        WHERE r.code = ? ORDER BY r.snapshot_id DESC LIMIT 1""", (code,)).fetchone()
    if not r:
        return None
    topics = [t[0] for t in con.execute('SELECT topic FROM topics WHERE code=?', (code,))]
    ta = _json_or_none(TA_DIR / f'{code}.json')
    fa = _json_or_none(FA_DIR / f'{code}.json')
    segments = None
    if not ta:
        row = con.execute('SELECT segments FROM transcripts WHERE code=?', (code,)).fetchone()
        segments = db_util.loads(row[0], None) if row and row[0] else None
    text = ' '.join(filter(None, [r['cap'] or '', ' '.join(b.get('text', '') for b in (ta or {}).get('beats', []))]))
    routing = personas_mod.match(text, topics)[:2]
    return {
        'code': code, 'url': f'https://www.instagram.com/reel/{code}/', 'username': r['username'],
        'format_slot': fmt, 'radar_facts': why,
        'metrics': {'play': r['play'], 'reshares': r['resh'], 'saves': r['save'], 'comments': r['comm'],
                    'duration_s': r['dur'], 'resh_1k': r['resh_1k'], 'save_1k': r['save_1k'],
                    'author_median_play': r['author_median_play'], 'robust_z': r['z']},
        'topics': topics, 'caption': (r['cap'] or '')[:1500],
        'routing_hint': [{'persona': p, 'score': s, 'hits': h[:6]} for p, s, h in routing],
        'transcript_analysis': ta, 'frame_analysis': fa,
        'transcript_segments': segments[:80] if isinstance(segments, list) else None,
    }


def export(con, codes=None, run_id=None, input_dir=INPUT_DIR, batch_size=BATCH_SIZE):
    run_id = run_id or ('pa-' + db_util.new_id()[:8])
    if codes:
        items = [_reel_item(con, c) for c in codes]
    else:
        items = [_reel_item(con, c['code'], c['fmt'], c['why']) for c in _week_selection(con)]
    items = [i for i in items if i]
    input_dir.mkdir(parents=True, exist_ok=True)
    batches = []
    for n in range(0, len(items), batch_size):
        chunk = items[n:n + batch_size]
        path = input_dir / f'persona-{run_id}-{n // batch_size + 1}.json'
        path.write_text(json.dumps(chunk, indent=1, ensure_ascii=False), encoding='utf-8')
        batches.append({'path': path, 'rel': str(path.relative_to(ROOT)), 'codes': [i['code'] for i in chunk]})
    return run_id, batches


def _prompt(batch_rel):
    # str.replace, not str.format: the prompt contains the pa-v1 JSON example with braces
    return (PROMPT_PATH.read_text(encoding='utf-8')
            .replace('{batch_path}', batch_rel)
            .replace('{output_dir}', str(OUT_DIR.relative_to(ROOT))))


def run_agent(con, run_id, batches, claude_path=None):
    claude_path = claude_path or shutil.which('claude')
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for b in batches:
        with state.job(con, run_id, 'corpus', 'corpus', 'CONCEPT_GENERATION', agent='claude -p',
                        prompt_version=PROMPT_VERSION,
                        input_refs_json={'batch': b['rel'], 'codes': b['codes']}) as j:
            if not claude_path:
                j.skip('claude CLI not found on PATH')
                continue
            try:
                res = subprocess.run([claude_path, '-p', _prompt(b['rel']), '--allowed-tools', 'Read,Write,Bash'],
                                     timeout=AGENT_TIMEOUT_S, capture_output=True, text=True)
                j.set(output_refs_json={'returncode': res.returncode})
                if res.returncode != 0:
                    j.retry_required('claude exited %d: %s' % (res.returncode, (res.stderr or '')[-500:]))
            except subprocess.TimeoutExpired:
                j.retry_required('claude timed out after %ds' % AGENT_TIMEOUT_S)
            except OSError as exc:
                j.retry_required('failed to launch claude: %s' % exc)


def validate_concept(d):
    errs = []
    if not isinstance(d, dict):
        return ['not an object']
    missing = PA_KEYS - set(d)
    if missing:
        errs.append(f'missing keys: {sorted(missing)}')
    if d.get('analysis_version') != PROMPT_VERSION:
        errs.append(f"analysis_version must be {PROMPT_VERSION}")
    p = d.get('persona')
    if p is not None and PERSONA_IDS and p not in PERSONA_IDS:
        errs.append(f'unknown persona {p!r}')
    if p is None and not d.get('reject_reason'):
        errs.append('rejected concept needs reject_reason')
    if p is not None:
        cta = d.get('cta') or {}
        if cta.get('type') != 'comment_keyword' or not cta.get('keyword') or not cta.get('artefact'):
            errs.append('cta must be comment_keyword with keyword and artefact')
        hook = d.get('hook') or ''
        if len(hook.split()) > 25:
            errs.append('hook longer than 25 words')
        low = hook.lower()
        for banned in ('llm', 'rag', 'agentic', 'workflow', 'api', 'ai-powered', 'mcp'):
            if banned in low.split() or banned in low.replace('-', ' ').split():
                errs.append(f'hook uses banned word {banned!r}')
        if not (d.get('question') and d.get('why_this_persona')):
            errs.append('question and why_this_persona are required')
    return errs


def list_concepts(out_dir=OUT_DIR):
    rows = []
    for p in sorted(pathlib.Path(out_dir).glob('*.json')):
        d = _json_or_none(p)
        errs = validate_concept(d) if d is not None else ['invalid JSON']
        rows.append({'file': p.name, 'persona': (d or {}).get('persona'), 'format': (d or {}).get('format'),
                     'hook': (d or {}).get('hook'), 'cta': ((d or {}).get('cta') or {}).get('artefact'),
                     'errors': errs})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('export'); e.add_argument('--codes', default='')
    r = sub.add_parser('run'); r.add_argument('--codes', default=''); r.add_argument('--yes', action='store_true')
    sub.add_parser('list')
    args = ap.parse_args(argv)
    if args.cmd == 'list':
        rows = list_concepts()
        for row in rows:
            flag = 'OK ' if not row['errors'] else 'ERR'
            print(f"{flag} {row['file']:<22} {str(row['persona']):<6} {str(row['format']):<12} {row['hook'] or ''}")
            for err in row['errors']:
                print(f'      - {err}')
        print(f'{len(rows)} concept(s)')
        return 0
    con = db_util.connect()
    codes = [c for c in args.codes.split(',') if c] or None
    if args.cmd == 'export':
        run_id, batches = export(con, codes)
        for b in batches:
            print(f"wrote {b['rel']}  ({len(b['codes'])} reels)")
        print(f'run_id {run_id}; next: python3 -m engine.persona_adapt run --yes')
        return 0
    if not args.yes:
        print('run needs --yes: it launches an unattended claude -p per batch (no money, local CLI).')
        return 2
    run_id = state.start_run(con, 'analysis', config={'note': 'persona adaptation pa-v1', 'prompt_version': PROMPT_VERSION})
    _, batches = export(con, codes, run_id=run_id)
    run_agent(con, run_id, batches)
    state.finish_run(con, run_id, 'DONE')
    rows = list_concepts()
    print(f'run {run_id}: {len(batches)} batch(es), {len(rows)} concept file(s) on disk')
    return 0


if __name__ == '__main__':
    sys.exit(main())
