#!/usr/bin/env python3
"""Catch-up worker: finds codes that are ingested but not analysis_ready and runs the
local pipeline on them, using only already-cached HikerAPI URLs. engine/SPEC.md §6.
Never calls HikerAPI, never pays — same "scan cache/**/*clips*.json" trick as
deep.py's `_urls()`.

    python3 -m engine.watchdog --limit 20 --yes [--codes a,b] [--dry]
"""
import argparse
import datetime
import glob
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db import connect  # noqa: E402
from engine.local_pipeline import (  # noqa: E402
    process_video, ensure_schema, start_run, DEFAULT_ASR_VERSION, DEFAULT_FRAMES_VERSION,
)

LOCK_PATH = ROOT / 'data' / 'watchdog.lock'
STALE_SECONDS = 3 * 3600
RATE_SLEEP_S = 1.0
OVERFETCH = 4  # not every candidate will have a live URL; scan a wider pool than --limit


def _now_iso():
    return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


def _acquire_lock():
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    if LOCK_PATH.exists():
        try:
            data = json.loads(LOCK_PATH.read_text())
            age = time.time() - float(data.get('ts', 0))
            if age < STALE_SECONDS:
                return False, data
        except (ValueError, OSError, TypeError):
            pass  # corrupt/unreadable lock file: treat as stale, take over
    LOCK_PATH.write_text(json.dumps({'pid': os.getpid(), 'ts': time.time()}))
    return True, None


def _release_lock():
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def _urls(cache_root, codes):
    """Same trick as deep.py:_urls() — scan already-cached clips*.json responses from
    the weekly collection, oldest file first so a newer cached URL wins (signed CDN
    URLs live only hours; an older file's URL would already 403)."""
    pattern = str(pathlib.Path(cache_root) / '**' / '*clips*.json')
    files = sorted(glob.glob(pattern, recursive=True), key=lambda f: pathlib.Path(f).stat().st_mtime)
    found = {}
    for f in files:
        try:
            d = json.load(open(f))
        except (OSError, ValueError):
            continue
        for m in (d.get('items') or d.get('response', {}).get('items') or []):
            if m.get('code') in codes:
                vv = m.get('video_versions') or []
                if vv:
                    found[m['code']] = vv[0]['url']
    return found


def links_alive(url):
    p = subprocess.run(['curl', '-sI', '--max-time', '20', url], capture_output=True, text=True)
    return ' 200' in p.stdout.split('\n')[0]


def _mark_expired(con, code):
    now = _now_iso()
    con.execute("UPDATE video_state SET media_state='EXPIRED', updated_at=? WHERE code=?", (now, code))
    if con.execute('SELECT changes()').fetchone()[0] == 0:
        con.execute("INSERT INTO video_state (code, media_state, updated_at) VALUES (?, 'EXPIRED', ?)",
                    (code, now))
    con.commit()


def _needs_processing_codes(con):
    """analysis_ready=0 (either explicitly, or never touched at all) — SPEC §6."""
    rows = con.execute("""
        SELECT vs.code FROM video_state vs
        WHERE vs.analysis_ready=0
          AND (vs.transcript_state != 'DONE' OR vs.frames_state != 'DONE_SCENE')
        UNION
        SELECT r.code FROM reels r LEFT JOIN video_state vs ON vs.code = r.code
        WHERE vs.code IS NULL
    """).fetchall()
    return [r[0] for r in rows]


def select_codes(con, limit=None, codes=None, cache_root=None):
    """Returns ([(code, url), ...], no_url_codes). Stops offering codes once the live
    check fails once (the whole cache generation is then presumed stale, matching
    deep.py's link-liveness behaviour) — checked lazily, on the first URL only."""
    ensure_schema(con)
    cache_root = cache_root or (ROOT / 'cache')
    candidates = list(codes) if codes else _needs_processing_codes(con)
    if limit:
        candidates = candidates[:limit * OVERFETCH]
    urls = _urls(cache_root, set(candidates))

    selected, no_url = [], []
    checked_live = False
    generation_dead = False
    for c in candidates:
        u = urls.get(c)
        if not u:
            no_url.append(c)
            continue
        if generation_dead:
            no_url.append(c)  # whole cache generation presumed dead — see below
            continue
        if not checked_live:
            checked_live = True
            if not links_alive(u):
                no_url.append(c)
                generation_dead = True  # rest of this generation's URLs are presumed dead too
                continue
        selected.append((c, u))
        if limit and len(selected) >= limit:
            break
    return selected, no_url


def run(con, limit=20, codes=None, dry=False, cache_root=None):
    ensure_schema(con)
    selected, no_url = select_codes(con, limit=limit, codes=codes, cache_root=cache_root)
    for c in no_url:
        _mark_expired(con, c)

    run_id = start_run(con, 'watchdog')
    con.execute("""INSERT INTO runs (run_id, started_at, kind, status) VALUES (?,?,?,?)
                   ON CONFLICT(run_id) DO NOTHING""", (run_id, _now_iso(), 'watchdog', 'RUNNING'))
    con.commit()

    results = []
    for i, (code, url) in enumerate(selected):
        if dry:
            results.append({'code': code, 'status': 'DRY_RUN'})
            continue
        try:
            r = process_video(con, code, url, run_id, asr_version=DEFAULT_ASR_VERSION,
                               frames_version=DEFAULT_FRAMES_VERSION)
        except Exception as e:
            r = {'code': code, 'status': 'FAILED',
                 'errors': [{'stage': 'WATCHDOG', 'code': 'UNEXPECTED', 'message': str(e)}]}
        results.append(r)
        if not dry and i < len(selected) - 1:
            time.sleep(RATE_SLEEP_S)

    summary = {
        'run_id': run_id, 'selected': len(selected), 'no_url': len(no_url),
        'done': sum(1 for r in results if r.get('status') == 'DONE'),
        'partial': sum(1 for r in results if r.get('status') == 'PARTIAL'),
        'failed': sum(1 for r in results if r.get('status') == 'FAILED'),
        'skipped': sum(1 for r in results if r.get('skipped')),
        'dry_run': dry, 'expired': no_url, 'results': results,
    }
    con.execute("UPDATE runs SET finished_at=?, status='DONE', summary_json=? WHERE run_id=?",
                (_now_iso(), json.dumps(summary, default=str), run_id))
    con.commit()

    out_dir = ROOT / 'data' / 'runs'
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f'watchdog-{run_id}.json').write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    return summary


def _print_summary(summary):
    print(f"watchdog run {summary['run_id']}: selected {summary['selected']}, no_url {summary['no_url']}")
    print(f"  done {summary['done']}  partial {summary['partial']}  failed {summary['failed']}  "
          f"skipped {summary['skipped']}{'  [dry-run]' if summary['dry_run'] else ''}")
    for r in summary['results'][:40]:
        status = r.get('status') or ('SKIPPED' if r.get('skipped') else r.get('reason', '?'))
        print(f"  {r.get('code'):<14} {status}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--limit', type=int, default=20)
    ap.add_argument('--yes', action='store_true', help='required unless --dry (costs no money, but writes to disk/DB)')
    ap.add_argument('--codes', help='comma-separated codes to force-select instead of scanning video_state')
    ap.add_argument('--dry', action='store_true')
    args = ap.parse_args(argv)

    if not args.yes and not args.dry:
        print('watchdog spends no money, but needs --yes to process videos (or --dry to preview selection).')
        return 1

    got, holder = _acquire_lock()
    if not got:
        age = int(time.time() - float(holder.get('ts', 0))) if holder else -1
        print(f"another watchdog worker holds the lock (pid {holder.get('pid') if holder else '?'}, "
              f"age {age}s) — refusing to start")
        return 1
    try:
        con = connect()
        codes = [c.strip() for c in args.codes.split(',') if c.strip()] if args.codes else None
        summary = run(con, limit=args.limit, codes=codes, dry=args.dry)
        _print_summary(summary)
        con.close()
        return 0
    finally:
        _release_lock()


if __name__ == '__main__':
    sys.exit(main())
