#!/usr/bin/env python3
"""Block routing by an agent: every reel of the weekly pool gets its content block read from
the caption and transcript, with quoted evidence and a one-line "about" (RULES.md §13.2).

Tags + regex (content_blocks.classify) stay the fallback: a reel without an agent file keeps
its regex block, and the card says which of the two routed it.

    python3 -m engine.block_route export [--all]        # batch files for pool reels not yet routed
    python3 -m engine.block_route run --yes [--all]     # export + run `claude -p` per batch (unattended)
    python3 -m engine.block_route list                  # routed files on disk, validated
    python3 -m engine.block_route stats                 # agent vs regex agreement over the pool

Batch input: `data/analysis/input/blocks-<run_id>-N.json`. Output contract `br-v1`:
`data/analysis/blocks/<code>.json` (engine/prompts/block-route.md). Every run writes a runs row
and one CATEGORIZATION job per batch. No money is spent here; the agent call is local `claude -p`.
"""
import argparse, datetime, json, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import db_util, state          # noqa: E402
import content_blocks as cb                 # noqa: E402

INPUT_DIR = ROOT / 'data' / 'analysis' / 'input'
OUT_DIR = cb.AGENT_DIR
PROMPT_PATH = ROOT / 'engine' / 'prompts' / 'block-route.md'
PROMPT_VERSION = 'br-v1'
BATCH_SIZE = 50
AGENT_TIMEOUT_S = 40 * 60
STAGE = 'CATEGORIZATION'     # engine.state.STAGES: routing a reel to a block is categorisation
BR_KEYS = {'code', 'analysis_version', 'model', 'block', 'secondary', 'reason_if_null', 'evidence',
           'about', 'confidence', 'disagrees_with_regex'}


def _pool(con):
    import cards
    return cards._pool(con, datetime.date.today())


def _item(con, r):
    text = cb.reel_text(con, r['code'], r['cap'])
    regex_block, ev = cb.classify(r['topics'], text)
    return {'code': r['code'], 'author': r['username'], 'caption': (r['cap'] or '')[:1500],
            'transcript': text[len(r['cap'] or ''):].strip()[:6000] or None,
            'topic_tags': [t for t in r['topics'] if t not in ('Темы в подписи нет', 'Только призыв, без темы в подписи')],
            'regex_block': None if regex_block == cb.UNASSIGNED else regex_block, 'regex_evidence': ev}


def export(con, run_id=None, everything=False, input_dir=INPUT_DIR, batch_size=BATCH_SIZE):
    run_id = run_id or ('br-' + db_util.new_id()[:8])
    pool = _pool(con)
    if not everything:
        pool = [r for r in pool if not (OUT_DIR / f"{r['code']}.json").exists()]
    items = [_item(con, r) for r in pool]
    input_dir.mkdir(parents=True, exist_ok=True)
    batches = []
    for n in range(0, len(items), batch_size):
        chunk = items[n:n + batch_size]
        path = input_dir / f'blocks-{run_id}-{n // batch_size + 1}.json'
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
    for b in batches:
        with state.job(con, run_id, 'corpus', 'corpus', STAGE, agent='claude -p',
                        prompt_version=PROMPT_VERSION,
                        input_refs_json={'batch': b['rel'], 'codes': b['codes']}) as j:
            if not claude_path:
                j.skip('claude CLI not found on PATH')
                continue
            try:
                res = subprocess.run([claude_path, '-p', _prompt(b['rel']), '--allowed-tools', 'Read,Write,Bash'],
                                     timeout=AGENT_TIMEOUT_S, capture_output=True, text=True)
                written = sum((OUT_DIR / f'{c}.json').exists() for c in b['codes'])
                j.set(output_refs_json={'returncode': res.returncode, 'written': written, 'of': len(b['codes'])})
                if res.returncode != 0:
                    j.retry_required('claude exited %d: %s' % (res.returncode, (res.stderr or '')[-500:]))
                elif written < len(b['codes']):
                    j.set(note=f'{len(b["codes"]) - written} reel(s) without a file')
            except subprocess.TimeoutExpired:
                j.retry_required('claude timed out after %ds' % AGENT_TIMEOUT_S)
            except OSError as exc:
                j.retry_required('failed to launch claude: %s' % exc)


def validate(d):
    errs = []
    if not isinstance(d, dict):
        return ['not an object']
    missing = BR_KEYS - set(d)
    if missing:
        errs.append(f'missing keys: {sorted(missing)}')
    if d.get('analysis_version') != PROMPT_VERSION:
        errs.append(f'analysis_version must be {PROMPT_VERSION}')
    b = d.get('block')
    if b is not None and b not in cb.BLOCKS:
        errs.append(f'unknown block {b!r}')
    if b is None and not d.get('reason_if_null'):
        errs.append('null block needs reason_if_null')
    if b is not None and not d.get('evidence'):
        errs.append('a block needs evidence')
    if d.get('confidence') not in ('HIGH', 'MEDIUM', 'LOW'):
        errs.append('confidence must be HIGH|MEDIUM|LOW')
    about = d.get('about') or ''
    if not about or len(about.split()) > 24:
        errs.append('about must be one sentence of at most ~20 words')
    return errs


def list_routed(out_dir=OUT_DIR):
    rows = []
    for p in sorted(pathlib.Path(out_dir).glob('*.json')):
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
        except ValueError:
            d = None
        rows.append({'file': p.name, 'block': (d or {}).get('block'), 'about': (d or {}).get('about'),
                     'errors': validate(d) if d is not None else ['invalid JSON']})
    return rows


def stats(con):
    pool = _pool(con)
    agent = regex = agree = 0
    for r in pool:
        if r.get('block_source') == 'agent':
            agent += 1
            if r.get('block') == r.get('regex_block'):
                agree += 1
        else:
            regex += 1
    return {'pool': len(pool), 'agent': agent, 'regex_only': regex, 'agent_agrees_with_regex': agree}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('export'); e.add_argument('--all', action='store_true')
    r = sub.add_parser('run'); r.add_argument('--all', action='store_true'); r.add_argument('--yes', action='store_true')
    sub.add_parser('list'); sub.add_parser('stats')
    args = ap.parse_args(argv)
    if args.cmd == 'list':
        rows = list_routed()
        bad = 0
        for row in rows:
            flag = 'OK ' if not row['errors'] else 'ERR'
            bad += bool(row['errors'])
            print(f"{flag} {row['file']:<22} {str(row['block']):<9} {row['about'] or ''}")
            for err in row['errors']:
                print(f'      - {err}')
        print(f'{len(rows)} routed file(s), {bad} with errors')
        return 1 if bad else 0
    con = db_util.connect()
    if args.cmd == 'stats':
        print(json.dumps(stats(con), indent=1))
        return 0
    if args.cmd == 'export':
        run_id, batches = export(con, everything=args.all)
        for b in batches:
            print(f"wrote {b['rel']}  ({len(b['codes'])} reels)")
        print(f'run_id {run_id}; next: python3 -m engine.block_route run --yes')
        return 0
    if not args.yes:
        print('run needs --yes: it launches an unattended claude -p per batch (no money, local CLI).')
        return 2
    run_id = state.start_run(con, 'analysis', config={'note': 'block routing br-v1', 'prompt_version': PROMPT_VERSION})
    _, batches = export(con, run_id=run_id, everything=args.all)
    run_agent(con, run_id, batches)
    state.finish_run(con, run_id, 'DONE')
    rows = list_routed()
    print(f"run {run_id}: {len(batches)} batch(es), {len(rows)} routed file(s), "
          f"{sum(bool(r['errors']) for r in rows)} with errors")
    return 0


if __name__ == '__main__':
    sys.exit(main())
