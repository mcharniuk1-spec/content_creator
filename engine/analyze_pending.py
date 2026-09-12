#!/usr/bin/env python3
"""Scheduled semantic-analysis stage (SPEC §5-§6, HANDOFF/architecture-doc §11 gap).

Turns the manual/session-driven ta-v1/fa-v1 pass into a cron step, the same shape as
`engine/watchdog.py` for local processing and `cron.sh`'s existing `prompts/angles.md`
step for an unattended `claude -p` call:

    python3 -m engine.analyze_pending [--dry] [--limit N] [--batch-size 30] [--yes] [--db PATH]

What it does, in order:

1. Selects **pending** codes straight from the database — no separate ledger to drift
   out of sync. ta-v1 pending: a `transcripts` row with `words>0` and non-empty timed
   `segments` (i.e. what `engine.state.compute_video_state` would call
   `transcript_state='DONE'`) but no `beats` row yet. fa-v1 pending: at least one
   `frames` row and a contact-sheet file on disk (`deepdives.sheet`, written by
   `engine.local_pipeline`/legacy `deep.py`) but no `frame_labels` row yet. A code whose
   analysis JSON already sits on disk (`data/analysis/{transcripts,frames}/<code>.json`)
   is not re-exported — it only needs `engine.ingest_analysis`, so it is ingested
   straight away regardless of `--yes`/agent availability.
2. Exports the rest as batch input files, byte-for-byte the same shape as the eight
   hand-run `data/analysis/input/{transcripts,frames}-batch-N.json` files from this
   week's backlog (field-for-field — see `_export_transcript_item`/`_export_frame_item`),
   at `data/analysis/input/pending-{transcripts,frames}-<run_id>-N.json`.
3. Unless `--dry`: when `--yes` is given and the `claude` CLI is on PATH, runs one
   unattended agent per batch (`claude -p "$(engine/prompts/analyze-pending.md, with
   the real paths substituted)" --allowed-tools "Read,Write,Bash"`, `subprocess.run`,
   1h timeout), recording one `jobs` row per batch (`entity_kind='corpus'`,
   `stage=TRANSCRIPT_ANALYSIS`/`FRAME_ANALYSIS`, `agent='claude -p'`,
   `prompt_version='ta-v1'`/`'fa-v1'`). Without `--yes` the batches are still exported
   (free, local, no network) but the agent is not launched. Without `claude` on PATH:
   prints `NOT_CONFIGURED: ...` and records the batch's job as SKIPPED — exit code is
   still 0, this is a normal "nothing to do yet" outcome, not a failure.
4. Loads whatever analysis JSON exists now (`engine.ingest_analysis`), then re-aligns
   (`engine.align.align`) and rebuilds `video_features` (`engine.features.build`) for
   every code this run actually landed a beats/frame_labels row for, then
   `engine.state.refresh_video_state` for those same codes. Prints a before/after
   summary table.

Idempotent and safe to rerun (every write is `INSERT OR REPLACE`/pure recomputation);
guarded by `data/analyze.lock` (pid+timestamp, stale after 3h) exactly like
`engine/watchdog.py`, so a cron overlap refuses to start a second worker rather than
racing it.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import align, corpus, features, ingest_analysis, state          # noqa: E402
from engine.db_util import connect as engine_connect                        # noqa: E402
from engine.db_util import loads                                            # noqa: E402

LOCK_PATH = ROOT / 'data' / 'analyze.lock'
STALE_SECONDS = 3 * 3600      # same staleness window as engine/watchdog.py

TA_DIR = pathlib.Path(ingest_analysis.TA_DIR)
FA_DIR = pathlib.Path(ingest_analysis.FA_DIR)
WARN_PATH = pathlib.Path(ingest_analysis.WARN_PATH)
INPUT_DIR = ROOT / 'data' / 'analysis' / 'input'
PROMPT_TEMPLATE_PATH = ROOT / 'engine' / 'prompts' / 'analyze-pending.md'

DEFAULT_BATCH_SIZE = 30
AGENT_TIMEOUT_S = 3600
CAPTION_TA_CHARS = 600
CAPTION_FA_CHARS = 300

KIND_TA = 'transcripts'
KIND_FA = 'frames'
_KIND_META = {
    KIND_TA: {'stage': 'TRANSCRIPT_ANALYSIS', 'prompt_version': 'ta-v1',
              'detail_prompt': 'engine/prompts/transcript-analysis.md',
              'output_dir': 'data/analysis/transcripts'},
    KIND_FA: {'stage': 'FRAME_ANALYSIS', 'prompt_version': 'fa-v1',
              'detail_prompt': 'engine/prompts/frame-analysis.md',
              'output_dir': 'data/analysis/frames'},
}


# --------------------------------------------------------------------------- #
# lock (same trick as engine/watchdog.py: pid+timestamp, stale after 3h)
# --------------------------------------------------------------------------- #

def _acquire_lock():
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    if LOCK_PATH.exists():
        try:
            data = json.loads(LOCK_PATH.read_text())
            age = time.time() - float(data.get('ts', 0))
            if age < STALE_SECONDS:
                return False, data
        except (ValueError, OSError, TypeError):
            pass
    LOCK_PATH.write_text(json.dumps({'pid': os.getpid(), 'ts': time.time()}))
    return True, None


def _release_lock():
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except OSError:
        pass


# --------------------------------------------------------------------------- #
# 1. pending selection
# --------------------------------------------------------------------------- #

def _transcript_usable(words, segments_raw):
    """Same test as engine.state.compute_video_state's transcript_state=='DONE'."""
    segs = loads(segments_raw, None)
    return (words or 0) > 0 and isinstance(segs, list) and len(segs) > 0


def _abs_path(p):
    """Resolve a DB-stored path (seen both absolute and repo-relative in this
    corpus) against ROOT so an existence check works either way."""
    pp = pathlib.Path(p)
    return pp if pp.is_absolute() else (ROOT / pp)


def select_transcript_pending(con):
    """codes: usable transcript, no `beats` row yet."""
    beats_codes = {r[0] for r in con.execute('SELECT DISTINCT code FROM beats')}
    pending = []
    for r in con.execute('SELECT code, words, segments FROM transcripts'):
        code = r['code']
        if code in beats_codes:
            continue
        if not _transcript_usable(r['words'], r['segments']):
            continue
        # A ta-v1 file that exists with an empty `beats` list is a deliberate "no speech to
        # segment" verdict (music-only reels whose ASR output is lyrics). It is final, not pending.
        existing = TA_DIR / f'{code}.json'
        if existing.exists():
            try:
                if not json.loads(existing.read_text(encoding='utf-8')).get('beats'):
                    continue
            except (OSError, ValueError):
                pass
        pending.append(code)
    return sorted(pending)


def select_frame_pending(con):
    """codes: at least one `frames` row + a contact sheet on disk, no `frame_labels` yet."""
    labeled_codes = {r[0] for r in con.execute('SELECT DISTINCT code FROM frame_labels')}
    frame_codes = {r[0] for r in con.execute(
        'SELECT code FROM frames GROUP BY code HAVING COUNT(*) > 0')}
    sheets = {r['code']: r['sheet'] for r in con.execute(
        'SELECT code, sheet FROM deepdives WHERE sheet IS NOT NULL')}
    pending = []
    for code in sorted(frame_codes):
        if code in labeled_codes:
            continue
        sheet = sheets.get(code)
        if sheet and _abs_path(sheet).exists():
            pending.append(code)
    return pending


def select_pending(con):
    corpus.ensure_tables(con)
    return select_transcript_pending(con), select_frame_pending(con)


def _split_by_json_on_disk(codes, directory):
    """(ready_to_ingest, needs_export) — SPEC step 1's "skip codes already having an
    analysis JSON on disk (just ingest those)"."""
    ready, needs = [], []
    for c in codes:
        (ready if (directory / f'{c}.json').exists() else needs).append(c)
    return ready, needs


# --------------------------------------------------------------------------- #
# 2. batch export — exact shape of data/analysis/input/{transcripts,frames}-batch-N.json
# --------------------------------------------------------------------------- #

def _latest_reel(con, code):
    row = con.execute(
        'SELECT username, dur, play, likes, comm, resh, save, cap FROM reels '
        'WHERE code=? ORDER BY snapshot_id DESC LIMIT 1', (code,)).fetchone()
    return dict(row) if row else {}


def _scores_for_code(con, code):
    row = con.execute(
        "SELECT z, author_median_play, resh_1k, save_1k FROM scores WHERE code=? "
        "ORDER BY (weights='ig') DESC, snapshot_id DESC LIMIT 1", (code,)).fetchone()
    return dict(row) if row else {}


def _rel_path(p):
    """Batch files carry repo-relative paths (matching the existing hand-built
    batches), even though the DB may hold either form."""
    if not p:
        return p
    pp = pathlib.Path(p)
    if pp.is_absolute():
        try:
            return str(pp.relative_to(ROOT))
        except ValueError:
            return str(pp)
    return p


def _export_transcript_item(con, code):
    reel = _latest_reel(con, code)
    tr = con.execute('SELECT words, segments FROM transcripts WHERE code=?', (code,)).fetchone()
    segs = loads(tr['segments'], []) if tr else []
    sc = _scores_for_code(con, code)
    topics = [t for (t,) in con.execute('SELECT topic FROM topics WHERE code=?', (code,))]
    return {
        'code': code,
        'username': reel.get('username'),
        'url': f'https://www.instagram.com/reel/{code}/',
        'dur': reel.get('dur'),
        'play': reel.get('play'),
        'likes': reel.get('likes'),
        'comm': reel.get('comm'),
        'resh': reel.get('resh'),
        'save': reel.get('save'),
        'author_median_play': sc.get('author_median_play'),
        'z': sc.get('z'),
        'resh_1k': sc.get('resh_1k'),
        'save_1k': sc.get('save_1k'),
        'caption': (reel.get('cap') or '')[:CAPTION_TA_CHARS],
        'topics': topics,
        'words': (tr['words'] if tr else 0) or 0,
        'segments': segs,
    }


def _export_frame_item(con, code):
    reel = _latest_reel(con, code)
    tr = con.execute('SELECT words, segments FROM transcripts WHERE code=?', (code,)).fetchone()
    has_transcript = bool(tr) and _transcript_usable(tr['words'], tr['segments'])
    sheet_row = con.execute('SELECT sheet FROM deepdives WHERE code=?', (code,)).fetchone()
    sheet = sheet_row['sheet'] if sheet_row else None
    frames = []
    for r in con.execute('SELECT idx, t_sec, path FROM frames WHERE code=? ORDER BY idx', (code,)):
        path = r['path']
        frames.append({'idx': r['idx'], 't': r['t_sec'], 'path': _rel_path(path),
                       'exists': bool(path) and _abs_path(path).exists()})
    return {
        'code': code,
        'username': reel.get('username'),
        'dur': reel.get('dur'),
        'play': reel.get('play'),
        'caption': (reel.get('cap') or '')[:CAPTION_FA_CHARS],
        'has_transcript': has_transcript,
        'sheet': _rel_path(sheet),
        'frames': frames,
    }


def _safe_rel(path):
    """str(path), relative to ROOT when possible — tests may pass a tmp_path input_dir
    that lives outside the repo entirely."""
    try:
        return str(pathlib.Path(path).relative_to(ROOT))
    except ValueError:
        return str(path)


def _chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def export_batches(con, kind, codes, batch_size, run_id, input_dir=INPUT_DIR):
    """Writes `pending-<kind>-<run_id>-N.json`; returns [{'path','rel','codes'}, ...]."""
    if not codes:
        return []
    input_dir.mkdir(parents=True, exist_ok=True)
    item_fn = _export_transcript_item if kind == KIND_TA else _export_frame_item
    out = []
    for n, chunk in enumerate(_chunks(codes, batch_size), start=1):
        items = [item_fn(con, c) for c in chunk]
        path = input_dir / f'pending-{kind}-{run_id}-{n}.json'
        path.write_text(json.dumps(items, indent=1, ensure_ascii=False), encoding='utf-8')
        out.append({'path': path, 'rel': _safe_rel(path), 'codes': list(chunk)})
    return out


# --------------------------------------------------------------------------- #
# 3. unattended agent step
# --------------------------------------------------------------------------- #

def _build_prompt(kind, batch_rel):
    meta = _KIND_META[kind]
    template = PROMPT_TEMPLATE_PATH.read_text(encoding='utf-8')
    return template.format(detail_prompt=meta['detail_prompt'], batch_path=batch_rel,
                            output_dir=meta['output_dir'])


def _run_agent_job(con, run_id, kind, batch, claude_path):
    meta = _KIND_META[kind]
    prompt_text = _build_prompt(kind, batch['rel'])
    with state.job(con, run_id, 'corpus', 'corpus', meta['stage'], agent='claude -p',
                    prompt_version=meta['prompt_version'],
                    input_refs_json={'batch': batch['rel'], 'codes': batch['codes']}) as j:
        try:
            result = subprocess.run(
                [claude_path, '-p', prompt_text, '--allowed-tools', 'Read,Write,Bash'],
                timeout=AGENT_TIMEOUT_S, capture_output=True, text=True)
            j.set(output_refs_json={'returncode': result.returncode})
            if result.returncode != 0:
                j.retry_required('claude exited %d: %s'
                                  % (result.returncode, (result.stderr or '')[-500:]))
        except subprocess.TimeoutExpired:
            j.retry_required('claude timed out after %ds' % AGENT_TIMEOUT_S)
        except OSError as exc:
            j.retry_required('failed to launch claude: %s' % exc)


def _skip_agent_job(con, run_id, kind, batch, reason):
    meta = _KIND_META[kind]
    with state.job(con, run_id, 'corpus', 'corpus', meta['stage'], agent='claude -p',
                    prompt_version=meta['prompt_version'],
                    input_refs_json={'batch': batch['rel'], 'codes': batch['codes']}) as j:
        j.skip(reason)


# --------------------------------------------------------------------------- #
# 4-5. driver
# --------------------------------------------------------------------------- #

def _print_pending(ta_pending, ta_ready, ta_export, fa_pending, fa_ready, fa_export):
    print('pending: transcripts %d (json on disk, ready to ingest %d | needs batch export %d) | '
          'frames %d (json on disk, ready to ingest %d | needs batch export %d)'
          % (len(ta_pending), len(ta_ready), len(ta_export),
             len(fa_pending), len(fa_ready), len(fa_export)))


def run(con, *, dry=False, yes=False, limit=None, batch_size=DEFAULT_BATCH_SIZE,
        input_dir=INPUT_DIR):
    corpus.ensure_tables(con)
    ta_pending, fa_pending = select_pending(con)
    ta_ready, ta_export = _split_by_json_on_disk(ta_pending, TA_DIR)
    fa_ready, fa_export = _split_by_json_on_disk(fa_pending, FA_DIR)
    _print_pending(ta_pending, ta_ready, ta_export, fa_pending, fa_ready, fa_export)

    summary = {
        'ta_pending_before': len(ta_pending), 'fa_pending_before': len(fa_pending),
        'ta_ready_to_ingest': len(ta_ready), 'fa_ready_to_ingest': len(fa_ready),
        'ta_needs_export': len(ta_export), 'fa_needs_export': len(fa_export),
        'dry_run': dry,
    }

    if dry:
        print('[dry run] nothing written')
        return summary

    if limit:
        ta_export, fa_export = ta_export[:limit], fa_export[:limit]

    got, holder = _acquire_lock()
    if not got:
        age = int(time.time() - float(holder.get('ts', 0))) if holder else -1
        msg = ('another analyze_pending worker holds the lock (pid %s, age %ss) — refusing to start'
               % (holder.get('pid') if holder else '?', age))
        print(msg)
        summary['error'] = msg
        return summary

    try:
        run_id = state.start_run(con, 'analysis',
                                 config={'limit': limit, 'batch_size': batch_size, 'yes': yes})

        ta_batches = export_batches(con, KIND_TA, ta_export, batch_size, run_id, input_dir)
        fa_batches = export_batches(con, KIND_FA, fa_export, batch_size, run_id, input_dir)
        summary['ta_batches'] = [b['rel'] for b in ta_batches]
        summary['fa_batches'] = [b['rel'] for b in fa_batches]

        claude_path = shutil.which('claude')
        if not (ta_batches or fa_batches):
            pass
        elif not yes:
            print('agent not launched: pass --yes to run claude on the exported batches '
                  '(%d transcript, %d frame batch(es) written to %s)'
                  % (len(ta_batches), len(fa_batches), _safe_rel(input_dir)))
        elif not claude_path:
            msg = ('NOT_CONFIGURED: claude CLI not on PATH; batches exported to %s'
                   % _safe_rel(input_dir))
            print(msg)
            for kind, batches in ((KIND_TA, ta_batches), (KIND_FA, fa_batches)):
                for b in batches:
                    _skip_agent_job(con, run_id, kind, b, 'claude CLI not on PATH')
        else:
            for kind, batches in ((KIND_TA, ta_batches), (KIND_FA, fa_batches)):
                for b in batches:
                    _run_agent_job(con, run_id, kind, b, claude_path)

        # --- ingest + align + features + state, for whatever landed a row this run ---
        # ta_dir/fa_dir/warn_path forwarded from this module's own globals (not
        # ingest_analysis's) so tests can monkeypatch engine.analyze_pending.TA_DIR/
        # FA_DIR/WARN_PATH to a tmp dir without ever touching the real data/analysis/*.
        ingest_summary = ingest_analysis.run(con, transcripts=True, frames=True,
                                             ta_dir=str(TA_DIR), fa_dir=str(FA_DIR),
                                             warn_path=str(WARN_PATH), verbose=False)
        touch_codes = set(ta_ready) | set(fa_ready) | set(ta_export) | set(fa_export)
        beats_now = {r[0] for r in con.execute('SELECT DISTINCT code FROM beats')}
        fl_now = {r[0] for r in con.execute('SELECT DISTINCT code FROM frame_labels')}
        affected = sorted(touch_codes & (beats_now | fl_now))
        for code in affected:
            align.align(con, code)
            features.build(con, code)
            state.refresh_video_state(con, code)
        con.commit()

        ta_pending_after, fa_pending_after = select_pending(con)
        ready_now = con.execute(
            'SELECT COUNT(*) FROM video_state WHERE code IN (%s) AND analysis_ready=1'
            % ','.join('?' * len(affected)), affected).fetchone()[0] if affected else 0

        summary.update({
            'beats_added': ingest_summary['beats'], 'frame_labels_added': ingest_summary['frame_labels'],
            'files_ingested': ingest_summary['beat_codes'] + ingest_summary['frame_codes'],
            'affected_codes': affected,
            'ta_pending_after': len(ta_pending_after), 'fa_pending_after': len(fa_pending_after),
            'analysis_ready_now': ready_now,
        })
        state.finish_run(con, run_id, 'DONE', {k: v for k, v in summary.items()
                                                if k not in ('ta_batches', 'fa_batches', 'affected_codes')})
        _print_summary(summary)
        return summary
    finally:
        _release_lock()


def _print_summary(summary):
    print('pending before -> after: transcripts %d -> %d | frames %d -> %d'
          % (summary['ta_pending_before'], summary['ta_pending_after'],
             summary['fa_pending_before'], summary['fa_pending_after']))
    print('files ingested %d | beats added %d | frame_labels added %d | analysis_ready now %d'
          % (summary['files_ingested'], summary['beats_added'], summary['frame_labels_added'],
             summary['analysis_ready_now']))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--dry', action='store_true', help='print pending counts only, write nothing')
    ap.add_argument('--limit', type=int, default=None,
                    help='cap codes newly batched (per kind) this run; already-ingestable codes are unlimited')
    ap.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE)
    ap.add_argument('--yes', action='store_true',
                    help='launch the claude agent on exported batches (batches export either way)')
    ap.add_argument('--db', default=None)
    args = ap.parse_args(argv)

    con = engine_connect(args.db) if args.db else engine_connect()
    try:
        summary = run(con, dry=args.dry, yes=args.yes, limit=args.limit, batch_size=args.batch_size)
    finally:
        con.close()
    return 1 if summary.get('error') else 0


if __name__ == '__main__':
    sys.exit(main())
