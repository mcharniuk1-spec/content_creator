#!/usr/bin/env python3
"""Local, free, per-video processing: media fetch -> transcription -> scene/frame
extraction -> alignment. engine/SPEC.md §6. Никаких платных вызовов — media уже
известна (URL из кэша сбора или локальный путь), HikerAPI здесь не трогаем.

    python3 -m engine.local_pipeline --code CODE --media PATH_OR_URL [--keep-video] [--force]

Idempotent: a code already DONE for the same asr_version/frames_version is skipped
unless --force. Every stage is wrapped so one failure (bad download, ASR crash, ffmpeg
crash) doesn't take down the others — see PipelineError / typed failure codes below.
"""
import argparse
import contextlib
import datetime
import json
import pathlib
import re
import subprocess
import sys
import time
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db import connect  # noqa: E402
from engine import scenes  # noqa: E402

DATA_DIR = ROOT / 'data'
DEFAULT_ASR_VERSION = 'faster-whisper-small-int8-v1'
DEFAULT_FRAMES_VERSION = 'scene-v1'
CUT_THRESHOLD = 0.30
MIN_SCENE_LEN = 0.4
MEDIA_MIN_BYTES = 10_000
DOWNLOAD_TRIES = 3
DOWNLOAD_TIMEOUT = 150

# --- engine.schema / engine.state: owned by another wave-2 owner, may not exist yet ---
# (engine/SPEC.md §9). We always run our own idempotent DDL (_ensure_tables) so this
# module works standalone; if engine.schema.migrate shows up later we call it too, best
# effort, and the two converge on the same tables (same DDL, verbatim from SPEC §2).
try:
    from engine.schema import migrate as _schema_migrate
except ImportError:
    _schema_migrate = None

try:
    from engine.state import job as _real_job, start_run as _real_start_run, \
        refresh_video_state as _real_refresh_video_state
    _HAVE_ENGINE_STATE = True
except ImportError:
    _HAVE_ENGINE_STATE = False
    _real_job = _real_start_run = _real_refresh_video_state = None

# Note: the real engine.state.start_run/job take `con` as their first argument (not
# just `kind`/`run_id` as engine/SPEC.md §9's brief first described) — these wrappers
# normalize to that shape so call sites are correct regardless of which path is live.


def start_run(con, kind):
    """engine.state.start_run(con, kind) when available; otherwise a local run id with
    no persisted `runs` row (minimal fallback per engine/SPEC.md §9)."""
    if _HAVE_ENGINE_STATE:
        try:
            return _real_start_run(con, kind)
        except Exception as e:
            print(f'engine.state.start_run failed ({e}); using a local run id', file=sys.stderr)
    return f"{datetime.datetime.utcnow():%Y-%m-%d_%H%M}-{uuid.uuid4().hex[:6]}"


@contextlib.contextmanager
def job(con, run_id, entity_kind, entity_id, stage, **meta):
    """engine.state.job(con, ...) when available; otherwise a no-op context manager
    that still propagates exceptions (minimal fallback per engine/SPEC.md §9) — real
    job-row tracing starts automatically once engine/state.py is importable, no call
    site here needs to change."""
    if _HAVE_ENGINE_STATE:
        with _real_job(con, run_id, entity_kind, entity_id, stage, **meta) as handle:
            yield handle
    else:
        yield None


class PipelineError(Exception):
    """Typed failure: .code is one of MEDIA_DOWNLOAD_FAILED, MEDIA_TOO_SMALL,
    ASR_FAILED, FFMPEG_FAILED (engine/SPEC.md deliverable list)."""

    def __init__(self, code, message=''):
        super().__init__(f'{code}: {message}')
        self.code = code
        self.message = message


def _now_iso():
    return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


# --- schema: new tables from engine/SPEC.md §2, verbatim, idempotent -------------------
_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL, note TEXT);

CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, kind TEXT NOT NULL,
  git_commit TEXT, host TEXT, config_json TEXT, summary_json TEXT,
  status TEXT NOT NULL DEFAULT 'RUNNING');

CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY, run_id TEXT REFERENCES runs(run_id), parent_job_id TEXT,
  entity_kind TEXT NOT NULL, entity_id TEXT NOT NULL, stage TEXT NOT NULL, state TEXT NOT NULL,
  previous_state TEXT, started_at TEXT, finished_at TEXT, duration_s REAL,
  agent TEXT, provider TEXT, model TEXT, prompt_version TEXT, knowledge_version TEXT,
  input_refs_json TEXT, output_refs_json TEXT, data_version TEXT, retries INTEGER NOT NULL DEFAULT 0,
  error TEXT, validation TEXT, cost_json TEXT);
CREATE INDEX IF NOT EXISTS jobs_entity ON jobs(entity_kind, entity_id, stage);

CREATE TABLE IF NOT EXISTS video_state (
  code TEXT PRIMARY KEY,
  ingested_at TEXT, first_snapshot_id INTEGER, last_snapshot_id INTEGER,
  media_state TEXT NOT NULL DEFAULT 'UNKNOWN',
  media_sha256 TEXT, media_path TEXT, media_bytes INTEGER,
  transcript_state TEXT NOT NULL DEFAULT 'MISSING',
  frames_state TEXT NOT NULL DEFAULT 'MISSING',
  alignment_state TEXT NOT NULL DEFAULT 'MISSING',
  transcript_analysis_state TEXT NOT NULL DEFAULT 'MISSING',
  frame_analysis_state TEXT NOT NULL DEFAULT 'MISSING',
  features_state TEXT NOT NULL DEFAULT 'MISSING',
  analysis_ready INTEGER NOT NULL DEFAULT 0,
  corpus_tier TEXT NOT NULL DEFAULT 'INGESTED_NOT_ANALYZED',
  asr_version TEXT, frames_version TEXT, analysis_version TEXT, features_version TEXT,
  flags_json TEXT,
  updated_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS transcript_meta (
  code TEXT PRIMARY KEY REFERENCES transcripts(code),
  provider TEXT NOT NULL DEFAULT 'local', model TEXT, asr_version TEXT, language TEXT,
  lang_probability REAL, media_sha256 TEXT, words INTEGER, tokens INTEGER, chars INTEGER,
  speech_seconds REAL, words_per_second REAL, segments_n INTEGER, processing_seconds REAL,
  created_at TEXT, version INTEGER NOT NULL DEFAULT 1, note TEXT);

CREATE TABLE IF NOT EXISTS scenes (
  scene_id TEXT PRIMARY KEY, code TEXT NOT NULL, idx INTEGER NOT NULL,
  start_s REAL NOT NULL, end_s REAL, duration_s REAL, boundary_reason TEXT,
  scene_type TEXT, transition_in TEXT, frame_idx_json TEXT,
  keyframe_path TEXT, frames_version TEXT NOT NULL, detector_json TEXT);
CREATE INDEX IF NOT EXISTS scenes_code ON scenes(code, idx);
"""


def _ensure_tables(con):
    """Create the tables this module needs if `engine.schema` hasn't (yet). Idempotent;
    safe to call every time, including after the real migration exists — same DDL."""
    con.executescript(_SCHEMA_DDL)
    have = {r[1] for r in con.execute('PRAGMA table_info(deepdives)')}
    if 'evidence_state' not in have:
        con.execute('ALTER TABLE deepdives ADD COLUMN evidence_state TEXT')
    con.commit()


def ensure_schema(con):
    if _schema_migrate:
        try:
            _schema_migrate(con)
        except Exception as e:
            print(f'engine.schema.migrate skipped ({e}); falling back to local DDL', file=sys.stderr)
    _ensure_tables(con)


def refresh_video_state(con, code):
    """Recompute `video_state` from the underlying tables (SPEC §3). Delegates to
    engine.state.refresh_video_state when it exists; otherwise runs the same algorithm
    locally so tests and the CLI both get a populated video_state today."""
    if _HAVE_ENGINE_STATE:
        try:
            return _real_refresh_video_state(con, code)
        except Exception as e:
            print(f'engine.state.refresh_video_state failed ({e}); using local fallback', file=sys.stderr)
    _refresh_video_state_fallback(con, code)


def _refresh_video_state_fallback(con, code):
    tr = con.execute('SELECT segments FROM transcripts WHERE code=?', (code,)).fetchone()
    tm = con.execute('SELECT asr_version FROM transcript_meta WHERE code=?', (code,)).fetchone()
    dd = con.execute('SELECT evidence_state FROM deepdives WHERE code=?', (code,)).fetchone()
    n_scenes = con.execute('SELECT COUNT(*) FROM scenes WHERE code=?', (code,)).fetchone()[0]
    vs = con.execute('SELECT * FROM video_state WHERE code=?', (code,)).fetchone()

    if tr is None:
        transcript_state = 'MISSING'
    else:
        try:
            has_segments = bool(tr['segments'] and json.loads(tr['segments']))
        except (TypeError, ValueError):
            has_segments = bool(tr['segments'])
        transcript_state = 'DONE' if has_segments else 'EMPTY_NO_SPEECH'

    frames_state = 'DONE_SCENE' if n_scenes > 0 else 'MISSING'

    # SPEC §2.2: analysis_ready needs transcript DONE + frames DONE_* + BOTH semantic
    # analyses DONE (beats / frame_labels — owned by the features/stats module, not
    # this one). corpus_tier is looser (transcript + usable frames only) so this
    # fallback still reports ANALYSIS_READY for the corpus split even before those
    # analyses exist.
    def _has_rows(table, code_):
        try:
            return con.execute(
                f"SELECT 1 FROM {table} WHERE code=? LIMIT 1", (code_,)).fetchone() is not None
        except Exception:
            return False  # table doesn't exist yet on a half-migrated DB

    transcript_analysis_state = 'DONE' if _has_rows('beats', code) else 'MISSING'
    frame_analysis_state = 'DONE' if _has_rows('frame_labels', code) else 'MISSING'
    analysis_ready = 1 if (transcript_state == 'DONE' and frames_state == 'DONE_SCENE'
                            and transcript_analysis_state == 'DONE'
                            and frame_analysis_state == 'DONE') else 0
    if transcript_state == 'DONE' and frames_state == 'DONE_SCENE':
        corpus_tier = 'ANALYSIS_READY'
    elif frames_state == 'DONE_SCENE':
        corpus_tier = 'FRAMES_ONLY'
    else:
        corpus_tier = 'INGESTED_NOT_ANALYZED'

    asr_version = tm['asr_version'] if tm else (vs['asr_version'] if vs else None)
    frames_version = dd['evidence_state'] if dd and dd['evidence_state'] else (vs['frames_version'] if vs else None)
    alignment_state = vs['alignment_state'] if vs else 'MISSING'
    media_state = vs['media_state'] if vs else 'UNKNOWN'
    media_sha256 = vs['media_sha256'] if vs else None
    media_path = vs['media_path'] if vs else None
    media_bytes = vs['media_bytes'] if vs else None
    ingested_at = vs['ingested_at'] if vs else _now_iso()

    con.execute("""
        INSERT INTO video_state (code, ingested_at, media_state, media_sha256, media_path, media_bytes,
            transcript_state, frames_state, alignment_state, transcript_analysis_state,
            frame_analysis_state, analysis_ready, corpus_tier, asr_version, frames_version, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(code) DO UPDATE SET
            media_state=excluded.media_state, media_sha256=excluded.media_sha256,
            media_path=excluded.media_path, media_bytes=excluded.media_bytes,
            transcript_state=excluded.transcript_state, frames_state=excluded.frames_state,
            transcript_analysis_state=excluded.transcript_analysis_state,
            frame_analysis_state=excluded.frame_analysis_state,
            analysis_ready=excluded.analysis_ready, corpus_tier=excluded.corpus_tier,
            asr_version=excluded.asr_version, frames_version=excluded.frames_version,
            updated_at=excluded.updated_at
    """, (code, ingested_at, media_state, media_sha256, media_path, media_bytes,
          transcript_state, frames_state, alignment_state, transcript_analysis_state,
          frame_analysis_state, analysis_ready, corpus_tier,
          asr_version, frames_version, _now_iso()))
    con.commit()


def _upsert_media_state(con, code, media_state, sha256=None, path=None, nbytes=None):
    now = _now_iso()
    exists = con.execute('SELECT 1 FROM video_state WHERE code=?', (code,)).fetchone()
    if exists:
        con.execute("""UPDATE video_state SET media_state=?, media_sha256=?, media_path=?,
            media_bytes=?, updated_at=? WHERE code=?""",
            (media_state, sha256, path, nbytes, now, code))
    else:
        con.execute("""INSERT INTO video_state (code, ingested_at, media_state, media_sha256,
            media_path, media_bytes, updated_at) VALUES (?,?,?,?,?,?,?)""",
            (code, now, media_state, sha256, path, nbytes, now))
    con.commit()


# --- media -----------------------------------------------------------------------------

def _looks_like_url(media):
    return str(media).startswith('http://') or str(media).startswith('https://')


def _download(url, dest, tries=DOWNLOAD_TRIES, timeout=DOWNLOAD_TIMEOUT):
    last = ('MEDIA_DOWNLOAD_FAILED', 'unknown')
    for attempt in range(1, tries + 1):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.unlink(missing_ok=True)
        try:
            p = subprocess.run(['curl', '-sL', '--max-time', str(timeout), '-o', str(dest), url],
                                capture_output=True, text=True, timeout=timeout + 20)
        except Exception as e:
            last = ('MEDIA_DOWNLOAD_FAILED', str(e))
        else:
            if p.returncode != 0:
                last = ('MEDIA_DOWNLOAD_FAILED', f'curl exit {p.returncode}: {(p.stderr or "").strip()[-200:]}')
            elif not dest.exists() or dest.stat().st_size < MEDIA_MIN_BYTES:
                sz = dest.stat().st_size if dest.exists() else 0
                last = ('MEDIA_TOO_SMALL', f'{sz} bytes')
            else:
                return
        if attempt < tries:
            time.sleep(2 * attempt)
    dest.unlink(missing_ok=True)
    raise PipelineError(*last)


def _resolve_media(media, dest):
    """media_url_or_path -> dest (data/video/<code>.mp4). Raises PipelineError on
    failure; never partially leaves a too-small file behind."""
    if _looks_like_url(media):
        _download(media, dest)
        return
    src = pathlib.Path(media)
    if not src.exists():
        raise PipelineError('MEDIA_DOWNLOAD_FAILED', f'local media not found: {media}')
    size = src.stat().st_size
    if size < MEDIA_MIN_BYTES:
        raise PipelineError('MEDIA_TOO_SMALL', f'{size} bytes')
    if src.resolve() != dest.resolve():
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())


def _probe_duration(ff, mp4):
    p = subprocess.run([ff, '-i', str(mp4)], capture_output=True, text=True)
    m = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.\d+)', p.stderr or '')
    if not m:
        return None
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


# --- transcription -----------------------------------------------------------------------

_WHISPER_MODELS = {}


def _model_size_from_asr_version(asr_version):
    parts = (asr_version or '').split('-')
    return parts[2] if len(parts) > 2 and parts[0] == 'faster' else 'small'


def transcribe(mp4, model_size='small'):
    """faster-whisper, CPU, int8, forced English, VAD on (engine/SPEC.md §6 step 3).
    Returns (segments, meta); raises PipelineError('ASR_FAILED', ...) on failure so the
    caller gets a typed error instead of a silent None like deep.py's version."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise PipelineError('ASR_FAILED', f'faster_whisper not installed: {e}')
    try:
        model = _WHISPER_MODELS.get(model_size)
        if model is None:
            model = WhisperModel(model_size, device='cpu', compute_type='int8')
            _WHISPER_MODELS[model_size] = model
        started = time.monotonic()
        segs, info = model.transcribe(str(mp4), language='en', vad_filter=True, word_timestamps=False)
        segments = [{'s': round(s.start, 2), 'e': round(s.end, 2), 't': s.text.strip()} for s in segs]
        elapsed = round(time.monotonic() - started, 2)
    except PipelineError:
        raise
    except Exception as e:
        raise PipelineError('ASR_FAILED', str(e))
    meta = {
        'model': model_size,
        'asr_version': f'faster-whisper-{model_size}-int8-v1',
        'language': getattr(info, 'language', 'en') or 'en',
        'lang_probability': getattr(info, 'language_probability', None),
        'processing_seconds': elapsed,
    }
    return segments, meta


# --- process_video -----------------------------------------------------------------------

def _scene_index_for_time(t, intervals):
    for i, (s, e) in enumerate(intervals):
        if s <= t < e:
            return i
    return len(intervals) - 1 if intervals else None


def process_video(con, code, media, run_id=None, *, asr_version, frames_version=DEFAULT_FRAMES_VERSION,
                   keep_video=False, force=False):
    """engine/SPEC.md §6 step-by-step contract. Returns a result dict:
    {code, run_id, status: DONE|PARTIAL|FAILED, skipped, steps: {...}, errors: [...]}."""
    ensure_schema(con)
    if run_id is None:
        run_id = start_run(con, 'manual')

    result = {'code': code, 'run_id': run_id, 'skipped': False, 'status': 'DONE',
              'steps': {}, 'errors': []}

    existing = con.execute(
        'SELECT transcript_state, frames_state, asr_version, frames_version FROM video_state WHERE code=?',
        (code,)).fetchone()
    if not force and existing and existing['transcript_state'] == 'DONE' \
            and existing['frames_state'] == 'DONE_SCENE' \
            and existing['asr_version'] == asr_version and existing['frames_version'] == frames_version:
        result['skipped'] = True
        result['reason'] = 'already processed with these versions'
        return result

    video_dir = DATA_DIR / 'video'
    frames_dir = DATA_DIR / 'frames' / code
    mp4 = video_dir / f'{code}.mp4'

    # step 2: media fetch --------------------------------------------------------------
    try:
        with job(con, run_id, 'video', code, 'MEDIA_FETCHED'):
            _resolve_media(media, mp4)
            sha = scenes.sha256_file(mp4)
            nbytes = mp4.stat().st_size
            _upsert_media_state(con, code, 'DOWNLOADED', sha, str(mp4), nbytes)
        result['steps']['media'] = {'sha256': sha, 'bytes': nbytes, 'path': str(mp4)}
    except PipelineError as e:
        _upsert_media_state(con, code, 'MISSING' if e.code == 'MEDIA_DOWNLOAD_FAILED' else 'EXPIRED')
        result['errors'].append({'stage': 'MEDIA_FETCHED', 'code': e.code, 'message': e.message})
        result['status'] = 'FAILED'
        refresh_video_state(con, code)
        return result

    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    dur = _probe_duration(ff, mp4) or 0.0

    # step 3: transcription --------------------------------------------------------------
    try:
        with job(con, run_id, 'video', code, 'TRANSCRIPTION'):
            model_size = _model_size_from_asr_version(asr_version)
            segments, meta = transcribe(mp4, model_size=model_size)
            text = ' '.join(s['t'] for s in segments).strip()
            words = len(text.split())
            speech_seconds = round(sum(s['e'] - s['s'] for s in segments), 2)
            con.execute("""INSERT OR REPLACE INTO transcripts (code, lang, words, text, segments)
                VALUES (?,?,?,?,?)""",
                (code, meta['language'], words, text, json.dumps(segments, ensure_ascii=False)))
            con.execute("""INSERT OR REPLACE INTO transcript_meta
                (code, provider, model, asr_version, language, lang_probability, media_sha256,
                 words, tokens, chars, speech_seconds, words_per_second, segments_n,
                 processing_seconds, created_at, version)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                (code, 'local', meta['model'], meta['asr_version'], meta['language'],
                 meta.get('lang_probability'), sha, words, round(words * 1.3), len(text),
                 speech_seconds, (round(words / speech_seconds, 3) if speech_seconds else None),
                 len(segments), meta['processing_seconds'], _now_iso()))
            con.commit()
        result['steps']['transcript'] = {
            'words': words, 'segments': len(segments),
            'state': 'DONE' if segments else 'EMPTY_NO_SPEECH', 'asr_version': meta['asr_version']}
    except PipelineError as e:
        result['errors'].append({'stage': 'TRANSCRIPTION', 'code': e.code, 'message': e.message})
    except Exception as e:
        result['errors'].append({'stage': 'TRANSCRIPTION', 'code': 'ASR_FAILED', 'message': str(e)})

    # step 4: frames / scenes (scene-v1) --------------------------------------------------
    intervals = []
    try:
        with job(con, run_id, 'video', code, 'FRAME_EXTRACTION'):
            cuts = scenes.detect_cuts(ff, mp4, threshold=CUT_THRESHOLD)
            intervals = scenes.scene_intervals(cuts, dur, min_len=MIN_SCENE_LEN)
            times = scenes.keyframe_times(intervals)
            existing_max = con.execute(
                'SELECT COALESCE(MAX(idx), -1) FROM frames WHERE code=?', (code,)).fetchone()[0]
            extracted = scenes.extract_frames(ff, mp4, times, frames_dir, scale=540,
                                               start_idx=existing_max + 1)
            frame_cols = {r[1] for r in con.execute('PRAGMA table_info(frames)')}
            for idx, t, path in extracted:
                # every entry in `extracted` already passed the exists()+size>0 check in
                # scenes.extract_frames, so exists_ok=1 / sha256 are known-good here —
                # per engine/HANDOFF_NOTES.md §schema-owner/3, refresh_video_state treats
                # an unset exists_ok as merely "unchecked", not broken, but setting it
                # avoids that ambiguity for every frame this module writes.
                if 'sha256' in frame_cols and 'exists_ok' in frame_cols:
                    con.execute(
                        'INSERT OR REPLACE INTO frames (code, idx, t_sec, path, sha256, exists_ok) '
                        'VALUES (?,?,?,?,?,1)', (code, idx, t, path, scenes.sha256_file(path)))
                else:
                    con.execute('INSERT OR REPLACE INTO frames (code, idx, t_sec, path) VALUES (?,?,?,?)',
                                (code, idx, t, path))
            sheet_path = DATA_DIR / 'frames' / f'{code}_sheet.jpg'
            sheet = scenes.contact_sheet(ff, frames_dir, sheet_path, cols=3)

            by_scene = {}
            for idx, t, _p in extracted:
                si = _scene_index_for_time(t, intervals)
                if si is not None:
                    by_scene.setdefault(si, []).append(idx)
            for i, (s, e) in enumerate(intervals):
                con.execute("""INSERT OR REPLACE INTO scenes
                    (scene_id, code, idx, start_s, end_s, duration_s, boundary_reason,
                     frame_idx_json, frames_version, detector_json)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (f'{code}-S{i}', code, i, s, e, round(e - s, 2), 'detector',
                     json.dumps(by_scene.get(i, [])), frames_version,
                     json.dumps({'threshold': CUT_THRESHOLD, 'cuts': cuts})))
            mb = round(mp4.stat().st_size / 1048576, 2)
            con.execute("""INSERT INTO deepdives (code, cuts, cuts_ps, mp4_mb, sheet, done_at, evidence_state)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(code) DO UPDATE SET cuts=excluded.cuts, cuts_ps=excluded.cuts_ps,
                    mp4_mb=excluded.mp4_mb, sheet=excluded.sheet, done_at=excluded.done_at,
                    evidence_state=excluded.evidence_state""",
                (code, len(cuts), round(len(cuts) / max(dur, 1), 2), mb, sheet, _now_iso(), 'scene-v1'))
            con.commit()
        result['steps']['frames'] = {
            'cuts': len(cuts), 'scenes': len(intervals), 'frames_extracted': len(extracted),
            'sheet': sheet}
    except PipelineError as e:
        result['errors'].append({'stage': 'FRAME_EXTRACTION', 'code': e.code, 'message': e.message})
    except Exception as e:
        result['errors'].append({'stage': 'FRAME_EXTRACTION', 'code': 'FFMPEG_FAILED', 'message': str(e)})

    # step 5: alignment -------------------------------------------------------------------
    try:
        with job(con, run_id, 'video', code, 'ALIGNMENT'):
            from engine.align import align as _align
            result['steps']['alignment'] = _align(con, code)
    except Exception as e:
        result['errors'].append({'stage': 'ALIGNMENT', 'code': 'ALIGNMENT_FAILED', 'message': str(e)})

    # step 6: cleanup + refresh -------------------------------------------------------------
    if not keep_video:
        mp4.unlink(missing_ok=True)
    refresh_video_state(con, code)
    con.commit()

    result['status'] = 'DONE' if not result['errors'] else 'PARTIAL'
    return result


# --- CLI -----------------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--code', required=True)
    ap.add_argument('--media', required=True, help='URL or local path to the mp4')
    ap.add_argument('--keep-video', action='store_true')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--asr-version', default=DEFAULT_ASR_VERSION)
    ap.add_argument('--frames-version', default=DEFAULT_FRAMES_VERSION)
    args = ap.parse_args(argv)

    con = connect()
    ensure_schema(con)
    run_id = start_run(con, 'manual')
    result = process_video(con, args.code, args.media, run_id,
                            asr_version=args.asr_version, frames_version=args.frames_version,
                            keep_video=args.keep_video, force=args.force)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    con.close()
    return 1 if result.get('status') == 'FAILED' else 0


if __name__ == '__main__':
    sys.exit(main())
