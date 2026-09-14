#!/usr/bin/env python3
"""Shortlist adaptation (sa-v1): every reel of the weekly shortlist becomes a decision card —
what they shot and what it did, our version inside its block and our positioning, and the
shoot plan part by part in our production system (Misha, 13 Sep 2026 evening).

    python3 -m engine.shortlist_adapt export              # batch files for this week's 15 (cards.select)
    python3 -m engine.shortlist_adapt run --yes           # export + `claude -p` per batch (unattended)
    python3 -m engine.shortlist_adapt list                # concept files on disk, validated
    python3 -m engine.shortlist_adapt md [FILE]           # the shortlist as one markdown document

Batch input: `data/analysis/input/shortlist-<run_id>-N.json` (5 reels per batch: the output is
long). Output: `data/analysis/shortlist/<code>.json` (engine/prompts/shortlist-adapt.md).
Every run writes a runs row and one CONCEPT_GENERATION job per batch. The unattended
Claude call uses the configured account and budget. Valid adapted reels are skipped unless --all.
"""
import argparse, datetime, json, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import db_util, state, persona_adapt        # noqa: E402
import content_blocks as cb                              # noqa: E402

INPUT_DIR = ROOT / 'data' / 'analysis' / 'input'
OUT_DIR = ROOT / 'data' / 'analysis' / 'shortlist'
PROMPT_PATH = ROOT / 'engine' / 'prompts' / 'shortlist-adapt.md'
PROMPT_VERSION = 'sa-v1'
BATCH_SIZE = 5
AGENT_TIMEOUT_S = 40 * 60
SA_KEYS = {'code', 'analysis_version', 'model', 'block', 'original', 'ours', 'reject_reason', 'format',
           'format_reason', 'shoot', 'cta', 'claims', 'confidence', 'notes'}
PARTS = ('hook', 'explanation', 'proof', 'payoff', 'cta')
FORMATS = ('M2 Radar', 'M2 Builds', 'M2 Teardown')
BANNED_HOOK = ('llm', 'rag', 'agentic', 'workflow', 'api', 'ai-powered', 'mcp')


def load(code, out_dir=None):
    p = pathlib.Path(OUT_DIR if out_dir is None else out_dir) / f'{code}.json'
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    try:
        return d if isinstance(d, dict) and d.get("code") == code and not validate(d) else None
    except (TypeError, ValueError, AttributeError, KeyError):
        return None


def _items(con, picked):
    items = []
    for c in picked:
        it = persona_adapt._reel_item(con, c['code'], c['fmt'], c['why'])
        if not it:
            continue
        it.pop('routing_hint', None)
        it.update({'block': c['block'], 'block_label': cb.label(c['block']), 'stage': c['stage'],
                   'about': c.get('about'), 'block_evidence': (c.get('block_evidence') or {}).get('words', []),
                   'shot_default': c['shot']})
        items.append(it)
    return items


def export(con, run_id=None, everything=False, input_dir=INPUT_DIR, batch_size=BATCH_SIZE):
    import cards
    run_id = run_id or ('sa-' + db_util.new_id()[:8])
    picked, _, _ = cards.select(con)
    if not everything:
        picked = [c for c in picked if load(c['code']) is None]
    items = _items(con, picked)
    input_dir.mkdir(parents=True, exist_ok=True)
    batches = []
    for n in range(0, len(items), batch_size):
        chunk = items[n:n + batch_size]
        path = input_dir / f'shortlist-{run_id}-{n // batch_size + 1}.json'
        path.write_text(json.dumps(chunk, indent=1, ensure_ascii=False), encoding='utf-8')
        batches.append({'path': path, 'rel': str(path.relative_to(ROOT)), 'codes': [i['code'] for i in chunk]})
    return run_id, batches


def _prompt(batch_rel):
    return (PROMPT_PATH.read_text(encoding='utf-8')
            .replace('{batch_path}', batch_rel)
            .replace('{output_dir}', str(OUT_DIR.relative_to(ROOT))))


def run_agent(con, run_id, batches, claude_path=None):
    claude_path = claude_path or shutil.which('claude')
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for b in batches:
        outcome = {'codes': b['codes'], 'status': 'FAILED', 'valid_outputs': 0}
        results.append(outcome)
        with state.job(con, run_id, 'corpus', 'corpus', 'CONCEPT_GENERATION', agent='claude -p',
                        prompt_version=PROMPT_VERSION,
                        input_refs_json={'batch': b['rel'], 'codes': b['codes']}) as j:
            if not claude_path:
                outcome['status'] = 'BLOCKED'
                j.skip('claude CLI not found on PATH')
                continue
            try:
                # A requested regeneration must not pass on a prior run's file.
                # Move bytes to unique history before launch; a fresh canonical
                # file must be emitted by this invocation to count as output.
                archived = []
                history = OUT_DIR / 'history' / run_id
                for code in b['codes']:
                    previous = OUT_DIR / f'{code}.json'
                    if previous.exists():
                        history.mkdir(parents=True, exist_ok=True)
                        target = history / f'{code}-{db_util.new_id()}.json'
                        previous.rename(target)
                        archived.append(str(target))
                j.set(output_refs_json={'archived_previous': archived})
                res = subprocess.run([claude_path, '-p', _prompt(b['rel']), '--allowed-tools', 'Read,Write,Bash'],
                                     timeout=AGENT_TIMEOUT_S, capture_output=True, text=True)
                valid = sum(load(c) is not None for c in b['codes'])
                outcome['valid_outputs'] = valid
                j.set(output_refs_json={'returncode': res.returncode, 'valid_outputs': valid, 'of': len(b['codes']), 'archived_previous': archived})
                if res.returncode != 0:
                    j.retry_required('claude exited %d: %s' % (res.returncode, (res.stderr or '')[-500:]))
                elif valid != len(b['codes']):
                    j.retry_required('valid outputs %d of %d' % (valid, len(b['codes'])))
                else:
                    outcome['status'] = 'DONE'
            except subprocess.TimeoutExpired:
                j.retry_required('claude timed out after %ds' % AGENT_TIMEOUT_S)
            except OSError as exc:
                j.retry_required('failed to launch claude: %s' % exc)
    return results


def validate(d):
    errs = []
    if not isinstance(d, dict):
        return ['not an object']
    missing = SA_KEYS - set(d)
    if missing:
        errs.append(f'missing keys: {sorted(missing)}')
    if d.get('analysis_version') != PROMPT_VERSION:
        errs.append(f'analysis_version must be {PROMPT_VERSION}')
    o = d.get('original') or {}
    if not isinstance(o, dict) or not (o.get('topic') and isinstance(o.get('result'), dict)):
        errs.append('original needs topic and result')
    ours = d.get('ours')
    if ours is None:
        if not d.get('reject_reason'):
            errs.append('rejected card needs reject_reason')
        return errs
    for k in ('topic', 'angle', 'for_whom', 'process', 'friction', 'ai_boundary', 'next_action', 'why_forward'):
        if not (isinstance(ours, dict) and ours.get(k)):
            errs.append(f'ours.{k} is required')
    if d.get('format') not in FORMATS:
        errs.append('format must be one of ' + ', '.join(FORMATS))
    sh = d.get('shoot') or {}
    parts = sh.get('parts') if isinstance(sh, dict) else None
    if not isinstance(parts, list) or not parts:
        errs.append('shoot.parts is required')
    else:
        names = [p.get('part') for p in parts]
        for need in ('hook', 'explanation', 'payoff'):
            if need not in names:
                errs.append(f'shoot.parts lacks {need}')
        for p in parts:
            if p.get('part') not in PARTS:
                errs.append(f"unknown part {p.get('part')!r}")
            for k in ('seconds', 'says', 'in_frame', 'on_screen'):
                if p.get(k) in (None, ''):
                    errs.append(f"part {p.get('part')}: {k} is required")
        hook = next((p for p in parts if p.get('part') == 'hook'), None)
        if hook:
            if (hook.get('seconds') or 0) > 8:
                errs.append('hook longer than 8 s')
            low = (hook.get('says') or '').lower().replace('-', ' ')
            for w in BANNED_HOOK:
                if w.replace('-', ' ') in low.split():
                    errs.append(f'hook uses banned word {w!r}')
        total = sum(float(p.get('seconds') or 0) for p in parts)
        if sh.get('duration_s') and abs(total - float(sh['duration_s'])) > 3:
            errs.append(f"parts add up to {total:.0f} s, duration_s says {sh['duration_s']}")
        if not sh.get('banner'):
            errs.append('shoot.banner is required')
    cta = d.get('cta')
    if cta is not None:
        if not isinstance(cta, dict) or cta.get('type') not in ('comment_keyword', 'save_share',
                                                                'question_to_audience', 'next_video'):
            errs.append('cta type unknown')
        elif cta['type'] == 'comment_keyword':
            if not (cta.get('keyword') and cta.get('artefact')):
                errs.append('comment_keyword needs keyword and artefact')
            elif not (ROOT / 'artefacts' / str(cta['artefact'])).exists() \
                    and not (ROOT / 'artefacts' / (str(cta['artefact']) + '.md')).exists():
                errs.append(f"artefact file not found: {cta['artefact']}")
    if not isinstance(d.get('claims'), list):
        errs.append('claims must be a list')
    return errs


def list_concepts(out_dir=OUT_DIR):
    rows = []
    for p in sorted(pathlib.Path(out_dir).glob('*.json')):
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
        except ValueError:
            d = None
        rows.append({'file': p.name, 'topic': ((d or {}).get('ours') or {}).get('topic'),
                     'format': (d or {}).get('format'), 'errors': validate(d) if d is not None else ['invalid JSON']})
    return rows


# ------------------------------------------------------------------ rendering ----
def _num(n):
    return f'{n:,}'.replace(',', ' ') if isinstance(n, (int, float)) and n == int(n) else str(n)


def card_md(c, d=None):
    """One card as markdown: the selection facts, then (when adapted) original / ours / shoot."""
    d = d or load(c['code'])
    L = [f"## {c['n']}. {cb.label(c['block'])} · stage {c['stage']} · {(d or {}).get('format') or c['fmt']}", '']
    L += [f"**Reference:** [{c['author']}]({c['ref']}), {c['age']} days old · stage {c['stage']}, {c['stage_note']}"]
    if not d:
        L += [f"**About:** {c.get('about') or (c.get('cap') or '')[:160]}",
              '_Not adapted yet: run `python3 -m engine.shortlist_adapt run --yes`._', '']
        return '\n'.join(L)
    o = d['original']; r = o.get('result') or {}
    L += ['', '### What they shot and what it did', '',
          f"**Topic:** {o.get('topic')}",
          f"**What the reel shows:** {o.get('what_they_show')}",
          f"**Why it worked for them:** {o.get('why_it_worked')}",
          f"**Result:** {_num(r.get('plays'))} plays · {r.get('vs_author_norm')}× the author's own norm · "
          f"{r.get('shares_1k')} shares and {r.get('saves_1k')} saves per thousand",
          f"**Does not transfer:** {o.get('does_not_transfer')}"]
    if d.get('ours') is None:
        L += ['', f"### Rejected: {d.get('reject_reason')}", '']
        return '\n'.join(L)
    u = d['ours']
    L += ['', '### Our version', '',
          f"**Topic:** {u['topic']}",
          f"**Angle:** {u['angle']}",
          f"**For whom:** {u['for_whom']}",
          f"**Process:** {u['process']}",
          f"**Friction:** {u['friction']}",
          f"**AI does / human keeps:** {u['ai_boundary']}",
          f"**Next action for the viewer:** {u['next_action']}",
          f"**Why someone forwards it:** {u['why_forward']}",
          f"**Format:** {d['format']}: {d.get('format_reason')}"]
    sh = d['shoot']
    L += ['', f"### How we shoot it: {sh.get('duration_s')} s · {sh.get('location')} · presenter {sh.get('presenter')}", '',
          f"**Banner (held for the whole reel):** {sh.get('banner')}", '',
          '| Part | s | Says | In frame | On screen | Overlay |', '|---|---|---|---|---|---|']
    for p in sh.get('parts', []):
        cell = lambda s: str(s or '—').replace('|', '/').replace('\n', ' ')
        L.append(f"| {p.get('part')} | {p.get('seconds')} | {cell(p.get('says'))} | {cell(p.get('in_frame'))} | "
                 f"{cell(p.get('on_screen'))} | {cell(p.get('overlay'))} |")
    cta = d.get('cta')
    if cta:
        L += ['', f"**CTA:** {cta.get('type')}" + (f" · comment «{cta.get('keyword')}» → {cta.get('artefact')}" if cta.get('keyword') else '')
              + (f" · {cta.get('viewer_gets')}" if cta.get('viewer_gets') else '')]
    else:
        L += ['', '**CTA:** none (share reason above)']
    claims = d.get('claims') or []
    if claims:
        L += ['', '**Claims:** ' + '; '.join(f"{x.get('text')} [{x.get('state')}]" for x in claims[:6])]
    L += [f"**Confidence:** {d.get('confidence')}" + (f" · {d.get('notes')}" if d.get('notes') else ''), '']
    return '\n'.join(L)


def render_md(picked, pool_n, today=None):
    import cards
    today = today or datetime.date.today()
    L = [f'# Shortlist {today.isoformat()}: {len(picked)} of {cards.SHORTLIST}', '',
         f'Pool in the {cards.FRESH_DAYS}-day window: {pool_n} reels. Stage 1 = best reel of each block above its '
         f'author norm; stage 2 = by shares + saves, at most {cards.MAX_PER_BLOCK} per block. '
         f'Pick {cards.PICK}, at most {cards.PICK_PER_BLOCK} from one block. Each card: what they shot and '
         f'what it did · our version · how we shoot it.', '']
    by_block = {}
    for c in picked:
        by_block.setdefault(c['block'], []).append(c['n'])
    L += ['| Block | Cards |', '|---|---|'] + [f"| {cb.label(b)} | {', '.join(map(str, ns))} |" for b, ns in by_block.items()] + ['']
    for c in picked:
        L.append(card_md(c))
    return '\n'.join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('export'); e.add_argument('--all', action='store_true')
    r = sub.add_parser('run'); r.add_argument('--all', action='store_true'); r.add_argument('--yes', action='store_true')
    sub.add_parser('list')
    m = sub.add_parser('md'); m.add_argument('file', nargs='?')
    args = ap.parse_args(argv)
    if args.cmd == 'list':
        rows = list_concepts(); bad = 0
        for row in rows:
            bad += bool(row['errors'])
            print(f"{'OK ' if not row['errors'] else 'ERR'} {row['file']:<22} {str(row['format']):<12} {row['topic'] or ''}")
            for err in row['errors']:
                print(f'      - {err}')
        print(f'{len(rows)} concept(s), {bad} with errors')
        return 1 if bad else 0
    con = db_util.connect()
    if args.cmd == 'md':
        import cards
        picked, pool_n, _ = cards.select(con)
        text = render_md(picked, pool_n)
        if args.file:
            pathlib.Path(args.file).parent.mkdir(parents=True, exist_ok=True)
            pathlib.Path(args.file).write_text(text, encoding='utf-8')
            print(f'written {args.file} ({len(picked)} cards)')
        else:
            print(text)
        return 0
    if args.cmd == 'export':
        run_id, batches = export(con, everything=args.all)
        for b in batches:
            print(f"wrote {b['rel']}  ({len(b['codes'])} reels)")
        print(f'run_id {run_id}; next: python3 -m engine.shortlist_adapt run --yes')
        return 0
    if not args.yes:
        print('run needs --yes: it launches an unattended claude -p per batch (configured model account/budget).')
        return 2
    run_id = state.start_run(con, 'analysis', config={'note': 'shortlist adaptation sa-v1', 'prompt_version': PROMPT_VERSION})
    try:
        _, batches = export(con, run_id=run_id, everything=args.all)
        results = run_agent(con, run_id, batches)
        failed = [r for r in results if r['status'] != 'DONE']
        status = ('PARTIAL' if failed and any(r['valid_outputs'] for r in results)
                  else 'FAILED' if failed else 'DONE')
        state.finish_run(con, run_id, status, {'batches': results})
    except Exception:
        state.finish_run(con, run_id, 'FAILED')
        raise
    print(f'run {run_id}: {status}; {len(results)} batch(es), {len(failed)} incomplete')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
