"""Run / job tracing and the per-video processing contract (SPEC §3, §2.2).

Two things live here.

1. **Trace.** `start_run` opens a `runs` row, the `job(...)` context manager
   writes one `jobs` row per processing step (RUNNING → DONE/FAILED, with
   duration, error text and a retry counter), `finish_run` closes the run and
   `run_summary` counts what happened per stage.

2. **State.** `refresh_video_state` recomputes *every* column of `video_state`
   for one code straight from the underlying tables, and
   `refresh_all_video_states` does it for the whole corpus. Both are pure
   functions of the database: running them twice changes nothing but
   `updated_at`. No state is ever written by hand.
"""
import contextlib
import hashlib
import json
import pathlib
import random
import socket
import time
from datetime import datetime, timedelta, timezone

from engine.db_util import ROOT, canonical_json, git_commit, loads, new_id, now, table_exists

# --------------------------------------------------------------------------- #
# Canonical vocabularies (SPEC §3, §2.2)
# --------------------------------------------------------------------------- #

STAGES = [
    'DISCOVERED', 'PROFILE_FETCHED', 'VIDEO_METADATA_FETCHED', 'STATS_FETCHED', 'MEDIA_FETCHED',
    'TRANSCRIPTION', 'TRANSCRIPT_ANALYSIS', 'FRAME_EXTRACTION', 'FRAME_ANALYSIS', 'ALIGNMENT',
    'GENERAL_ANALYSIS', 'STATISTICAL_ANALYSIS', 'CATEGORIZATION', 'REFERENCE_SELECTION',
    'CONCEPT_GENERATION', 'CARD_GENERATION', 'SCRIPT_GENERATION', 'SCRIPT_REVIEW', 'FRAME_PLAN',
    'FRAME_GENERATION', 'VIDEO_GENERATION_READY', 'VIDEO_RENDER', 'QUALITY_REVIEW', 'NOTION_SYNC',
    'COMPLETED',
]
JOB_STATES = ['PENDING', 'RUNNING', 'DONE', 'FAILED', 'RETRY_REQUIRED', 'SKIPPED']
# states a step may ask for itself; RUNNING is deliberately absent so a body that
# never calls skip()/retry_required() always closes as DONE
TERMINAL_STATES = ('DONE', 'FAILED', 'RETRY_REQUIRED', 'SKIPPED')
ENTITY_KINDS = ['video', 'creator', 'corpus', 'hypothesis', 'card']
RUN_KINDS = ['weekly', 'watchdog', 'analysis', 'cards', 'manual']

FLAGS = [
    'MISSING_STATS', 'MISSING_MEDIA', 'MISSING_TRANSCRIPT', 'MISSING_FRAMES',
    'BROKEN_FRAME_REFERENCE', 'UNALIGNED_TRANSCRIPT', 'DUPLICATE_VIDEO', 'STALE_METRICS',
    'UNRESOLVED_CREATOR_ID',
]

CORPUS_TIERS = ['ANALYSIS_READY', 'FRAMES_ONLY', 'INGESTED_NOT_ANALYZED']

FRAMES_VERSION_FIXED9 = 'fixed9-v1'
FRAMES_VERSION_SCENE = 'scene-v1'
FRAMES_VERSION_AUG2026 = 'aug2026'

DUPLICATE_CAPTION_MIN_CHARS = 30      # audit §13: byte-identical caption over 30 chars


# --------------------------------------------------------------------------- #
# 1. Runs and jobs
# --------------------------------------------------------------------------- #

def make_run_id(when=None):
    """`YYYY-MM-DD_HHMM-<6 hex>` (SPEC §1)."""
    when = when or datetime.now(timezone.utc)
    return f"{when.strftime('%Y-%m-%d_%H%M')}-{random.getrandbits(24):06x}"


def sweep_stale_runs(con, max_age_h=12):
    """Mark long-abandoned RUNNING rows as INTERRUPTED and return how many were swept.

    A run killed by a signal (`timeout` sends SIGTERM) never reaches `finish_run`, so its
    row stays RUNNING for ever. On 14 Sep 2026 the project-manager agent read one of those
    and reported a live run two hours after it had been killed. Anything still open after
    `max_age_h` is not running any more: the longest legitimate run is capped well below it.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_h)).strftime('%Y-%m-%dT%H:%M:%SZ')
    cur = con.execute(
        "UPDATE runs SET status='INTERRUPTED', finished_at=? "
        "WHERE status='RUNNING' AND finished_at IS NULL AND started_at < ?", (now(), cutoff))
    con.commit()
    return cur.rowcount


def start_run(con, kind, config=None):
    """Open a run and return its run_id."""
    if kind not in RUN_KINDS:
        raise ValueError(f'unknown run kind {kind!r}; expected one of {RUN_KINDS}')
    try:
        sweep_stale_runs(con)
    except Exception:
        pass      # уборка чужих строк не должна мешать начать свой прогон
    run_id = make_run_id()
    con.execute(
        'INSERT INTO runs (run_id, started_at, finished_at, kind, git_commit, host, '
        'config_json, summary_json, status) VALUES (?,?,NULL,?,?,?,?,NULL,?)',
        (run_id, now(), kind, git_commit(), socket.gethostname(),
         canonical_json(config), 'RUNNING'))
    con.commit()
    return run_id


def finish_run(con, run_id, status, summary=None):
    """Close a run. `status` is free text by contract but DONE/FAILED are the norm."""
    con.execute('UPDATE runs SET finished_at=?, status=?, summary_json=? WHERE run_id=?',
                (now(), status, canonical_json(summary), run_id))
    con.commit()


def latest_job(con, entity_kind, entity_id, stage):
    """Most recent job row for this entity/stage, or None."""
    return con.execute(
        'SELECT * FROM jobs WHERE entity_kind=? AND entity_id=? AND stage=? '
        'ORDER BY COALESCE(started_at, "") DESC, rowid DESC LIMIT 1',
        (entity_kind, str(entity_id), stage)).fetchone()


class JobHandle:
    """Handed to the `with job(...)` body so a step can annotate its own row."""

    __slots__ = ('job_id', 'run_id', 'entity_kind', 'entity_id', 'stage', 'fields', 'state')

    def __init__(self, job_id, run_id, entity_kind, entity_id, stage):
        self.job_id, self.run_id = job_id, run_id
        self.entity_kind, self.entity_id, self.stage = entity_kind, entity_id, stage
        self.fields = {}
        self.state = None            # set only by skip()/retry_required(); else DONE

    def set(self, **kw):
        """Record extra columns (provider, model, output_refs_json, cost_json, …)."""
        for k, v in kw.items():
            if k.endswith('_json') and not isinstance(v, (str, type(None))):
                v = canonical_json(v)
            self.fields[k] = v
        return self

    def skip(self, reason=None):
        """Mark the step SKIPPED instead of DONE (nothing to do for this entity)."""
        self.state = 'SKIPPED'
        if reason:
            self.fields['validation'] = reason
        return self

    def retry_required(self, reason=None):
        self.state = 'RETRY_REQUIRED'
        if reason:
            self.fields['validation'] = reason
        return self


_JOB_COLUMNS = {
    'parent_job_id', 'agent', 'provider', 'model', 'prompt_version', 'knowledge_version',
    'input_refs_json', 'output_refs_json', 'data_version', 'error', 'validation', 'cost_json',
    'retries', 'previous_state',
}


@contextlib.contextmanager
def job(con, run_id, entity_kind, entity_id, stage, **meta):
    """One processing step = one `jobs` row.

        with job(con, run_id, 'video', code, 'TRANSCRIPTION', provider='local') as j:
            j.set(model='small')

    Writes RUNNING on entry, then DONE (or SKIPPED / RETRY_REQUIRED if the body
    asked for it). On an exception: FAILED with the error text, duration and an
    incremented retry counter, and the exception is re-raised unchanged.
    """
    if stage not in STAGES:
        raise ValueError(f'unknown stage {stage!r}')
    if entity_kind not in ENTITY_KINDS:
        raise ValueError(f'unknown entity_kind {entity_kind!r}')
    entity_id = str(entity_id)

    prev = latest_job(con, entity_kind, entity_id, stage)
    previous_state = prev['state'] if prev else None
    # retries = how many times this entity/stage has already been attempted
    retries = con.execute(
        'SELECT COUNT(*) FROM jobs WHERE entity_kind=? AND entity_id=? AND stage=?',
        (entity_kind, entity_id, stage)).fetchone()[0]

    handle = JobHandle(new_id(), run_id, entity_kind, entity_id, stage)
    for k, v in meta.items():
        if k in _JOB_COLUMNS:
            handle.fields[k] = canonical_json(v) if (k.endswith('_json')
                                                     and not isinstance(v, (str, type(None)))) else v
        else:
            handle.fields.setdefault('input_refs_json', None)
            extra = loads(handle.fields.get('input_refs_json'), {}) or {}
            extra[k] = v
            handle.fields['input_refs_json'] = canonical_json(extra)
    handle.fields.setdefault('retries', retries)
    handle.fields['previous_state'] = previous_state

    started_at, t0 = now(), time.monotonic()
    con.execute(
        'INSERT INTO jobs (job_id, run_id, parent_job_id, entity_kind, entity_id, stage, state, '
        'previous_state, started_at, retries, agent, provider, model, prompt_version, '
        'knowledge_version, input_refs_json, data_version) '
        'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (handle.job_id, run_id, handle.fields.get('parent_job_id'), entity_kind, entity_id, stage,
         'RUNNING', previous_state, started_at, handle.fields.get('retries', retries),
         handle.fields.get('agent'), handle.fields.get('provider'), handle.fields.get('model'),
         handle.fields.get('prompt_version'), handle.fields.get('knowledge_version'),
         handle.fields.get('input_refs_json'), handle.fields.get('data_version')))
    con.commit()

    def _close(state, error=None):
        f = handle.fields
        con.execute(
            'UPDATE jobs SET state=?, finished_at=?, duration_s=?, error=?, validation=?, '
            'output_refs_json=?, cost_json=?, agent=?, provider=?, model=?, prompt_version=?, '
            'knowledge_version=?, data_version=?, retries=? WHERE job_id=?',
            (state, now(), round(time.monotonic() - t0, 3), error, f.get('validation'),
             f.get('output_refs_json'), f.get('cost_json'), f.get('agent'), f.get('provider'),
             f.get('model'), f.get('prompt_version'), f.get('knowledge_version'),
             f.get('data_version'), f.get('retries', retries), handle.job_id))
        con.commit()

    try:
        yield handle
    except BaseException as exc:                      # noqa: BLE001 — trace, then re-raise
        _close('FAILED', f'{type(exc).__name__}: {exc}'[:4000])
        raise
    _close(handle.state if handle.state in TERMINAL_STATES else 'DONE')


def run_summary(con, run_id):
    """Per-stage counts for one run: {stage: {state: n, ...}, ...} plus totals."""
    out = {}
    for stage, state, n in con.execute(
            'SELECT stage, state, COUNT(*) FROM jobs WHERE run_id=? GROUP BY stage, state '
            'ORDER BY stage, state', (run_id,)):
        out.setdefault(stage, {})[state] = n
    totals = {}
    for states in out.values():
        for state, n in states.items():
            totals[state] = totals.get(state, 0) + n
    dur = con.execute('SELECT COALESCE(SUM(duration_s),0) FROM jobs WHERE run_id=?',
                      (run_id,)).fetchone()[0]
    return {'run_id': run_id, 'stages': out, 'totals': totals,
            'jobs': sum(totals.values()), 'duration_s': round(dur or 0.0, 3)}


# --------------------------------------------------------------------------- #
# 2. video_state
# --------------------------------------------------------------------------- #

VIDEO_STATE_COLUMNS = [
    'code', 'ingested_at', 'first_snapshot_id', 'last_snapshot_id', 'media_state', 'media_sha256',
    'media_path', 'media_bytes', 'transcript_state', 'frames_state', 'alignment_state',
    'transcript_analysis_state', 'frame_analysis_state', 'features_state', 'analysis_ready',
    'corpus_tier', 'asr_version', 'frames_version', 'analysis_version', 'features_version',
    'flags_json', 'updated_at',
]


def _sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(chunk), b''):
            h.update(block)
    return h.hexdigest()


class _Context:
    """Everything `refresh_video_state` needs, loaded once for a set of codes.

    Refreshing 3 000 codes one query at a time is 40 000 queries; loading nine
    aggregates once and looking up dictionaries is two seconds.
    """

    def __init__(self, con, codes=None, root=None):
        self.con = con
        self.root = pathlib.Path(root or ROOT)
        self.codes = set(codes) if codes is not None else None
        self._load()

    def _has(self, table):
        return table_exists(self.con, table)

    # -- loading ---------------------------------------------------------- #
    def _load(self):
        con = self.con

        self.snapshot_taken = {r[0]: r[1] for r in con.execute('SELECT id, taken FROM snapshots')}
        row = con.execute('SELECT MAX(id) FROM snapshots WHERE done=1').fetchone()
        self.newest_snapshot = row[0] if row and row[0] is not None else None

        # reels aggregate per code
        self.reel = {}
        for r in con.execute(
                'SELECT code, MIN(snapshot_id) AS first_sid, MAX(snapshot_id) AS last_sid, '
                'COUNT(*) AS n, SUM(COALESCE(play,0)) AS play_sum, '
                'COUNT(DISTINCT COALESCE(pk_user,-1) || "/" || COALESCE(username,"")) AS ids '
                'FROM reels GROUP BY code'):
            self.reel[r['code']] = {'first_sid': r['first_sid'], 'last_sid': r['last_sid'],
                                    'n': r['n'], 'play_sum': r['play_sum'] or 0,
                                    'ids': r['ids']}

        self.in_newest = set()
        if self.newest_snapshot is not None:
            self.in_newest = {r[0] for r in con.execute(
                'SELECT DISTINCT code FROM reels WHERE snapshot_id=?', (self.newest_snapshot,))}

        # duplicate video: same author + byte-identical caption over N chars
        self.duplicate_codes = {r[0] for r in con.execute(
            'SELECT code FROM reels WHERE (COALESCE(pk_user,-1), cap) IN ('
            '  SELECT COALESCE(pk_user,-1), cap FROM reels '
            '  WHERE cap IS NOT NULL AND LENGTH(cap) > ? '
            '  GROUP BY COALESCE(pk_user,-1), cap HAVING COUNT(DISTINCT code) > 1)',
            (DUPLICATE_CAPTION_MIN_CHARS,))}

        # transcripts
        self.transcript = {}
        for r in con.execute('SELECT code, lang, words, segments FROM transcripts'):
            segs = loads(r['segments'], None)
            self.transcript[r['code']] = {
                'lang': r['lang'], 'words': r['words'] or 0,
                'segments_n': len(segs) if isinstance(segs, list) else 0,
                'segments_ok': isinstance(segs, list) and len(segs) > 0,
            }

        # frames: count, broken references, whether every path is an aug2026 import
        self.frames = {}
        for r in con.execute(
                'SELECT code, COUNT(*) AS n, '
                'SUM(CASE WHEN exists_ok = 0 THEN 1 ELSE 0 END) AS broken, '
                'SUM(CASE WHEN exists_ok IS NULL THEN 1 ELSE 0 END) AS unchecked, '
                'SUM(CASE WHEN path LIKE "%/legacy_%" THEN 1 ELSE 0 END) AS legacy_paths '
                'FROM frames GROUP BY code'):
            self.frames[r['code']] = {'n': r['n'], 'broken': r['broken'] or 0,
                                      'unchecked': r['unchecked'] or 0,
                                      'legacy_paths': r['legacy_paths'] or 0}

        self.deepdive = {r[0] for r in con.execute('SELECT code FROM deepdives')}

        # engine tables may not exist yet on a half-migrated database
        self.transcript_meta = {}
        if self._has('transcript_meta'):
            for r in con.execute('SELECT code, asr_version FROM transcript_meta'):
                self.transcript_meta[r['code']] = r['asr_version']

        self.scenes = {}
        if self._has('scenes'):
            for r in con.execute(
                    'SELECT code, COUNT(*) AS n, '
                    'SUM(CASE WHEN frames_version=? THEN 1 ELSE 0 END) AS scene_v1 '
                    'FROM scenes GROUP BY code', (FRAMES_VERSION_SCENE,)):
                self.scenes[r['code']] = {'n': r['n'], 'scene_v1': r['scene_v1'] or 0}

        self.beats = {}
        if self._has('beats'):
            for r in con.execute(
                    'SELECT code, COUNT(*) AS n, MAX(analysis_version) AS av, '
                    'SUM(CASE WHEN scene_ids_json IS NOT NULL AND scene_ids_json NOT IN ("","[]") '
                    '    THEN 1 ELSE 0 END) AS aligned '
                    'FROM beats GROUP BY code'):
                self.beats[r['code']] = {'n': r['n'], 'av': r['av'], 'aligned': r['aligned'] or 0}

        self.frame_labels = {}
        if self._has('frame_labels'):
            for r in con.execute('SELECT code, COUNT(*) AS n, MAX(analysis_version) AS av '
                                 'FROM frame_labels GROUP BY code'):
                self.frame_labels[r['code']] = {'n': r['n'], 'av': r['av']}

        self.features = {}
        if self._has('video_features'):
            for r in con.execute('SELECT code, features_version FROM video_features'):
                self.features[r['code']] = r['features_version']


def compute_video_state(ctx, code, asr_version=None, frames_version=None):
    """Pure computation: the full `video_state` row for `code` as a dict."""
    reel = ctx.reel.get(code)
    tr = ctx.transcript.get(code)
    fr = ctx.frames.get(code)
    sc = ctx.scenes.get(code)
    be = ctx.beats.get(code)
    fl = ctx.frame_labels.get(code)

    flags = set()

    # --- snapshots / ingestion ----------------------------------------- #
    first_sid = reel['first_sid'] if reel else None
    last_sid = reel['last_sid'] if reel else None
    ingested_at = ctx.snapshot_taken.get(first_sid) if first_sid is not None else None

    if reel is None:
        flags.add('MISSING_STATS')            # no metrics row at all
    else:
        if (reel['play_sum'] or 0) == 0:
            flags.add('MISSING_STATS')        # play NULL or 0 in every snapshot row
        if reel['ids'] and reel['ids'] > 1:
            flags.add('UNRESOLVED_CREATOR_ID')
        if ctx.newest_snapshot is not None and code not in ctx.in_newest:
            flags.add('STALE_METRICS')
    if code in ctx.duplicate_codes:
        flags.add('DUPLICATE_VIDEO')

    # --- transcript ------------------------------------------------------ #
    if tr is None:
        transcript_state = 'MISSING'
        flags.add('MISSING_TRANSCRIPT')
    elif tr['words'] > 0 and tr['segments_ok']:
        transcript_state = 'DONE'
    elif tr['words'] == 0:
        transcript_state = 'EMPTY_NO_SPEECH'
    else:
        transcript_state = 'FAILED'           # words but no timed segments
    if tr is not None and not tr['segments_ok']:
        flags.add('UNALIGNED_TRANSCRIPT')

    # --- frames ---------------------------------------------------------- #
    n_frames = fr['n'] if fr else 0
    scene_v1 = sc['scene_v1'] if sc else 0
    if n_frames == 0:
        frames_state = 'MISSING'
        flags.add('MISSING_FRAMES')
    elif scene_v1 > 0:
        frames_state = 'DONE_SCENE'
    else:
        frames_state = 'DONE_FIXED9'
    if fr and fr['broken']:
        frames_state = 'PARTIAL'
        flags.add('BROKEN_FRAME_REFERENCE')
    # MISSING_MEDIA (audit §13): a deep dive ran but no usable frame set landed —
    # either no frames row at all, or most of the files the run recorded are gone.
    # `DcxV37-CJOC` is the live example: a 0.3 MB download of a 61 s reel left one
    # frame of nine on disk.
    if code in ctx.deepdive and (n_frames == 0 or (fr and fr['broken'] * 2 >= n_frames)):
        flags.add('MISSING_MEDIA')

    # --- derived versions ------------------------------------------------ #
    derived_frames_version = None
    if scene_v1 > 0:
        derived_frames_version = FRAMES_VERSION_SCENE
    elif n_frames:
        derived_frames_version = (FRAMES_VERSION_AUG2026
                                  if fr and fr['legacy_paths'] == n_frames
                                  else FRAMES_VERSION_FIXED9)
    frames_version_out = frames_version or derived_frames_version
    asr_version_out = asr_version or ctx.transcript_meta.get(code)

    # --- analysis -------------------------------------------------------- #
    transcript_analysis_state = 'DONE' if (be and be['n']) else 'MISSING'
    frame_analysis_state = 'DONE' if (fl and fl['n']) else 'MISSING'
    features_state = 'DONE' if code in ctx.features else 'MISSING'

    if be and be['aligned']:
        alignment_state = 'DONE'
    elif transcript_state != 'DONE' or frames_state in ('MISSING', 'FAILED'):
        alignment_state = 'NOT_POSSIBLE'
    else:
        alignment_state = 'MISSING'

    analysis_ready = int(
        transcript_state == 'DONE'
        and frames_state in ('DONE_FIXED9', 'DONE_SCENE')
        and transcript_analysis_state == 'DONE'
        and frame_analysis_state == 'DONE')

    # --- corpus tier (SPEC §0.4) ---------------------------------------- #
    # ANALYSIS_READY = usable transcript (words>0, timed segments) AND frames.
    # FRAMES_ONLY    = frames present but the transcript is not usable.
    usable_frames = frames_state in ('DONE_FIXED9', 'DONE_SCENE', 'PARTIAL') and n_frames > 0
    if transcript_state == 'DONE' and usable_frames:
        corpus_tier = 'ANALYSIS_READY'
    elif usable_frames:
        corpus_tier = 'FRAMES_ONLY'
    else:
        corpus_tier = 'INGESTED_NOT_ANALYZED'

    # --- media ----------------------------------------------------------- #
    mp4 = ctx.root / 'data' / 'video' / f'{code}.mp4'
    media_state, media_path, media_bytes, media_sha = 'UNKNOWN', None, None, None
    if mp4.exists():
        media_state = 'DOWNLOADED'
        media_path = f'data/video/{code}.mp4'
        media_bytes = mp4.stat().st_size
        media_sha = _sha256_file(mp4)
    elif code in ctx.deepdive:
        # the deep dive ran and the mp4 was deleted afterwards (SPEC §4.4):
        # EXPIRED when frames survived, MISSING when nothing usable landed.
        media_state = 'MISSING' if 'MISSING_MEDIA' in flags else 'EXPIRED'

    return {
        'code': code,
        'ingested_at': ingested_at,
        'first_snapshot_id': first_sid,
        'last_snapshot_id': last_sid,
        'media_state': media_state,
        'media_sha256': media_sha,
        'media_path': media_path,
        'media_bytes': media_bytes,
        'transcript_state': transcript_state,
        'frames_state': frames_state,
        'alignment_state': alignment_state,
        'transcript_analysis_state': transcript_analysis_state,
        'frame_analysis_state': frame_analysis_state,
        'features_state': features_state,
        'analysis_ready': analysis_ready,
        'corpus_tier': corpus_tier,
        'asr_version': asr_version_out,
        'frames_version': frames_version_out,
        'analysis_version': (be or {}).get('av') or (fl or {}).get('av'),
        'features_version': ctx.features.get(code),
        'flags_json': canonical_json(sorted(flags)) if flags else canonical_json([]),
        'updated_at': now(),
    }


def _write(con, row):
    cols = ','.join(VIDEO_STATE_COLUMNS)
    marks = ','.join('?' * len(VIDEO_STATE_COLUMNS))
    con.execute(f'INSERT OR REPLACE INTO video_state ({cols}) VALUES ({marks})',
                tuple(row[c] for c in VIDEO_STATE_COLUMNS))


def refresh_video_state(con, code, *, asr_version=None, frames_version=None, ctx=None,
                        commit=True):
    """Recompute and store every column of `video_state` for one code."""
    ctx = ctx or _Context(con, codes={code})
    row = compute_video_state(ctx, code, asr_version=asr_version, frames_version=frames_version)
    _write(con, row)
    if commit:
        con.commit()
    return row


def refresh_all_video_states(con, codes=None, *, asr_version=None, frames_version=None,
                             progress=None):
    """Recompute `video_state` for every distinct code in `reels` (or a given list).

    Returns a summary dict with tier and flag counts.
    """
    if codes is None:
        codes = [r[0] for r in con.execute('SELECT DISTINCT code FROM reels ORDER BY code')]
    codes = list(codes)
    ctx = _Context(con, codes=codes)

    tiers, flag_counts, states = {}, {}, {}
    for i, code in enumerate(codes, 1):
        row = compute_video_state(ctx, code, asr_version=asr_version,
                                  frames_version=frames_version)
        _write(con, row)
        tiers[row['corpus_tier']] = tiers.get(row['corpus_tier'], 0) + 1
        for key in ('transcript_state', 'frames_state', 'media_state', 'alignment_state'):
            states.setdefault(key, {})
            states[key][row[key]] = states[key].get(row[key], 0) + 1
        for f in json.loads(row['flags_json']):
            flag_counts[f] = flag_counts.get(f, 0) + 1
        if progress and i % progress == 0:
            print(f'    video_state {i}/{len(codes)}', flush=True)
    con.commit()
    return {'codes': len(codes), 'corpus_tier': tiers, 'flags': flag_counts, 'states': states}


def corpus_codes(con, tier):
    """Codes in one corpus tier — the denominator any conclusion must name."""
    return [r[0] for r in con.execute(
        'SELECT code FROM video_state WHERE corpus_tier=? ORDER BY code', (tier,))]
