"""One-off, re-runnable migration of the legacy corpus into the engine tables.

    python3 -m engine.migrate_legacy --db data/radar.db [--dry]

Steps (SPEC §2, audit `reports/audit/02-data-inventory.md` §13–§14):

  a  apply `engine.schema`
  b  backfill `transcript_meta` for every row in `transcripts`
  c  set `frames.exists_ok` / `frames.sha256` from the files on disk
  d  set `deepdives.evidence_state = 'fixed9-v1'`
  e  import the never-migrated August 2026 archive (8 transcripts, 74 frames)
  f  initialise `video_state` for every distinct code in `reels`
  g  write the `providers` registry (presence of credentials only, never values)
  h  validate, print before/after counts, write `data/migration_log.md`
     and `reports/migration-validation.json`

Nothing is deleted and nothing is invented: codes that carry media analysis but
no `reels` row are recorded as UNRESOLVED in the migration log rather than
given a fabricated metrics row.
"""
import argparse
import base64
import hashlib
import json
import re
import sys

from engine import schema as engine_schema
from engine.db_util import (ROOT, canonical_json, connect, env_present, loads, now, row_counts,
                            table_names)
from engine.state import refresh_all_video_states

# --------------------------------------------------------------------------- #
# constants
# --------------------------------------------------------------------------- #

ASR_VERSION = 'faster-whisper-small-int8-v1'          # SPEC §1
ASR_PROVIDER = 'local'
ASR_MODEL = 'faster-whisper/small'
ASR_NOTE = ('deep.py: WhisperModel(small, device=cpu, compute_type=int8), '
            'language=en forced, vad_filter=True, word_timestamps=False')
TOKENS_PER_WORD = 1.3                                 # SPEC §6.3: tokens ≈ words * 1.3

EVIDENCE_STATE_LEGACY = 'fixed9-v1'
AUG_FRAMES_VERSION = 'aug2026'
AUG_NOTE = 'aug-2026-archive, provider unverified'

# The August pass predates the database. The JSON manifests live in `dataset/`,
# the jpgs they name live in the server mirror; both are checked.
AUG_JSON_DIRS = [
    ROOT / 'dataset' / '2026-08-niche-research',
    ROOT / 'data' / 'server-mirror' / 'archive' / '2026-08-niche-research',
]
AUG_FRAME_DIRS = [
    ROOT / 'dataset' / '2026-08-niche-research' / 'frames',
    ROOT / 'data' / 'server-mirror' / 'archive' / '2026-08-niche-research' / 'frames',
]
# `<code>_NNNN.jpg` — NNNN is deciseconds, verified against the pool durations:
# 0004/0012/0024 are deep.py's 0.4/1.2/2.4 s hook samples, the rest are dur*k/8.
AUG_FRAME_RX = re.compile(r'^(?P<code>[A-Za-z0-9_-]{5,30})_(?P<ds>\d{3,5})\.jpg$')

MIGRATION_LOG = ROOT / 'data' / 'migration_log.md'
VALIDATION_JSON = ROOT / 'reports' / 'migration-validation.json'

# name, kind, role, env_var, detail. `state` is decided from env-var presence only.
PROVIDERS = [
    ('hiker', 'social_data', 'DEFAULT', 'HIKER_KEY',
     'HikerAPI; the only working collection path. lib/hiker.py also falls back to the '
     'local MCP settings file, which this registry does not inspect: on a machine where '
     'only that third source holds the key, hiker still works while the row says '
     'NOT_CONFIGURED'),
    ('local-faster-whisper', 'transcription', 'DEFAULT', None,
     'local CPU ASR, small/int8; no credentials required'),
    ('local-ffmpeg-scenes', 'frames', 'DEFAULT', None,
     'ffmpeg via imageio_ffmpeg; scene detection and frame extraction, no credentials'),
    ('loore', 'transcription', 'OPTIONAL_PROVIDER', 'LOORE_KEY',
     'optional paid provider; DISABLED unless LOORE_KEY is set (SPEC §0.3)'),
    ('remotion', 'render', 'DEFAULT', None,
     'studio/remotion; needs Node and an existing Chrome binary — not verified here'),
    ('supabase', 'storage', 'OPTIONAL_PROVIDER', 'SUPABASE_KEY', 'not configured'),
    ('cloudflare', 'storage', 'OPTIONAL_PROVIDER', 'CLOUDFLARE_API_TOKEN', 'not configured'),
    ('higgsfield', 'image_gen', 'OPTIONAL_PROVIDER', 'HIGGSFIELD_API_KEY', 'not configured'),
    ('openai-images', 'image_gen', 'OPTIONAL_PROVIDER', 'OPENAI_API_KEY', 'not configured'),
]
# providers that must never report CONFIGURED without their credential
ALWAYS_UNCONFIGURED = {'supabase', 'cloudflare', 'higgsfield', 'openai-images', 'remotion'}


# --------------------------------------------------------------------------- #
# dry-run support
# --------------------------------------------------------------------------- #

class _DryCon:
    """Proxy that swallows commits so a --dry run can be rolled back.

    DDL is not covered: sqlite3 runs CREATE/ALTER in autocommit, so step (a)
    persists even under --dry. That is stated in the output.
    """

    def __init__(self, con):
        self._con = con

    def commit(self):
        pass

    def rollback(self):
        self._con.rollback()

    def __getattr__(self, name):
        return getattr(self._con, name)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(chunk), b''):
            h.update(block)
    return h.hexdigest()


def _first_existing(paths):
    for p in paths:
        if p.exists():
            return p
    return None


def _segments_stats(raw_segments, text):
    """words / chars / speech_seconds / wps / segments_n from `transcripts.segments`."""
    segs = loads(raw_segments, None)
    if not isinstance(segs, list):
        segs = []
    spoken = ' '.join(str(s.get('t') or '') for s in segs if isinstance(s, dict)).strip()
    words = len(spoken.split()) if spoken else 0
    speech = 0.0
    for s in segs:
        if isinstance(s, dict):
            try:
                speech += max(0.0, float(s.get('e') or 0) - float(s.get('s') or 0))
            except (TypeError, ValueError):
                pass
    speech = round(speech, 2)
    return {
        'segments_n': len(segs),
        'words': words,
        'chars': len(text or ''),
        'speech_seconds': speech if speech > 0 else None,
        'words_per_second': round(words / speech, 3) if (speech > 0 and words) else None,
        'tokens': int(words * TOKENS_PER_WORD + 0.5) if words else 0,
    }


# --------------------------------------------------------------------------- #
# steps
# --------------------------------------------------------------------------- #

def step_a_schema(con, log):
    applied = engine_schema.migrate(con, verbose=True)
    log['schema'] = {'applied_now': applied,
                     'all_versions': engine_schema.applied_versions(con)}
    print(f'  migrations applied now: {applied or "none (already up to date)"}')


UNKNOWN_PROVENANCE_NOTE = 'provenance unverified: no deepdives row for this transcript'


def step_b_transcript_meta(con, log):
    """Backfill `transcript_meta` for every transcript.

    Provenance is claimed only where it is provable. `deep.py` writes the
    transcript and the `deepdives` row in the same pass, so a transcript with a
    deep dive came from local faster-whisper and its `done_at` is the ASR date.
    A transcript without one (the August 2026 archive) gets `provider='unknown'`
    and is never overwritten by a later run — which is also what makes this step
    re-runnable.
    """
    rows = con.execute('SELECT code, lang, words, text, segments FROM transcripts '
                       'ORDER BY code').fetchall()
    done_at = {r[0]: r[1] for r in con.execute('SELECT code, done_at FROM deepdives')}
    known_meta = {r[0] for r in con.execute('SELECT code FROM transcript_meta')}
    local, unknown, left_alone = 0, 0, 0
    for r in rows:
        code = r['code']
        st = _segments_stats(r['segments'], r['text'])
        if code in done_at:
            con.execute(
                'INSERT OR REPLACE INTO transcript_meta '
                '(code, provider, model, asr_version, language, lang_probability, media_sha256, '
                ' words, tokens, chars, speech_seconds, words_per_second, segments_n, '
                ' processing_seconds, created_at, version, note) '
                'VALUES (?,?,?,?,?,NULL,NULL,?,?,?,?,?,?,NULL,?,1,?)',
                (code, ASR_PROVIDER, ASR_MODEL, ASR_VERSION, r['lang'],
                 st['words'], st['tokens'], st['chars'], st['speech_seconds'],
                 st['words_per_second'], st['segments_n'], done_at[code], ASR_NOTE))
            local += 1
        elif code in known_meta:
            left_alone += 1                 # already described (e.g. the August archive)
        else:
            con.execute(
                'INSERT OR REPLACE INTO transcript_meta '
                '(code, provider, model, asr_version, language, lang_probability, media_sha256, '
                ' words, tokens, chars, speech_seconds, words_per_second, segments_n, '
                ' processing_seconds, created_at, version, note) '
                'VALUES (?,?,NULL,NULL,?,NULL,NULL,?,?,?,?,?,?,NULL,NULL,1,?)',
                (code, 'unknown', r['lang'], st['words'], st['tokens'], st['chars'],
                 st['speech_seconds'], st['words_per_second'], st['segments_n'],
                 UNKNOWN_PROVENANCE_NOTE))
            unknown += 1
    con.commit()
    mismatch = con.execute(
        'SELECT COUNT(*) FROM transcript_meta m JOIN transcripts t USING(code) '
        'WHERE COALESCE(m.words,0) <> COALESCE(t.words,0)').fetchone()[0]
    total = con.execute('SELECT COUNT(*) FROM transcript_meta').fetchone()[0]
    log['transcript_meta'] = {'rows': total, 'local_faster_whisper': local,
                              'unknown_provenance': unknown,
                              'left_untouched': left_alone,
                              'words_differ_from_transcripts': mismatch}
    print(f'  transcript_meta rows: {total}  (local faster-whisper {local}, '
          f'unknown provenance {unknown}, left untouched {left_alone}; '
          f'word count differs from transcripts.words on {mismatch})')


def step_c_frames_files(con, log):
    rows = con.execute('SELECT code, idx, path FROM frames ORDER BY code, idx').fetchall()
    ok = broken = 0
    broken_codes = {}
    for r in rows:
        p = ROOT / (r['path'] or '')
        if r['path'] and p.is_file():
            con.execute('UPDATE frames SET exists_ok=1, sha256=? WHERE code=? AND idx=?',
                        (sha256_file(p), r['code'], r['idx']))
            ok += 1
        else:
            con.execute('UPDATE frames SET exists_ok=0, sha256=NULL WHERE code=? AND idx=?',
                        (r['code'], r['idx']))
            broken += 1
            broken_codes[r['code']] = broken_codes.get(r['code'], 0) + 1
    con.commit()
    log['frames_files'] = {'rows': len(rows), 'exists_ok': ok, 'broken': broken,
                           'broken_by_code': broken_codes}
    print(f'  frames checked: {len(rows)}  present {ok}  broken {broken} '
          f'{sorted(broken_codes) if broken_codes else ""}')


def step_d_evidence_state(con, log):
    n = con.execute('UPDATE deepdives SET evidence_state=?',
                    (EVIDENCE_STATE_LEGACY,)).rowcount
    con.commit()
    log['deepdives_evidence_state'] = {'rows': n, 'value': EVIDENCE_STATE_LEGACY}
    print(f'  deepdives.evidence_state = {EVIDENCE_STATE_LEGACY!r} on {n} rows')


def _load_aug_manifests():
    """Return (transcripts, frame_paths, frames_b64, source_dir) from the August pass."""
    src = None
    for d in AUG_JSON_DIRS:
        if (d / 'transcripts.json').exists():
            src = d
            break
    if src is None:
        return {}, {}, {}, None
    tr = json.loads((src / 'transcripts.json').read_text())
    fr = json.loads((src / 'frames.json').read_text()) if (src / 'frames.json').exists() else {}
    b64 = (json.loads((src / 'frames_b64.json').read_text())
           if (src / 'frames_b64.json').exists() else {})
    return tr, fr, b64, src


def _aug_frame_files():
    """{code: [(deciseconds, Path), ...]} for every jpg found on disk, sorted by time."""
    out = {}
    for d in AUG_FRAME_DIRS:
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            m = AUG_FRAME_RX.match(p.name)
            if not m:
                continue
            out.setdefault(m.group('code'), {})[int(m.group('ds'))] = p
    return {c: sorted(v.items()) for c, v in out.items()}


def step_e_august_archive(con, log, dry=False):
    tr_json, fr_json, b64_json, src = _load_aug_manifests()
    if src is None:
        log['august_archive'] = {'source': None, 'note': 'archive not found; nothing imported'}
        print('  August 2026 archive not found — skipped')
        return
    on_disk = _aug_frame_files()

    have_tr = {r[0] for r in con.execute('SELECT code FROM transcripts')}
    have_fr = {r[0] for r in con.execute('SELECT DISTINCT code FROM frames')}
    in_reels = {r[0] for r in con.execute('SELECT DISTINCT code FROM reels')}

    rec = {'source_manifests': str(src.relative_to(ROOT)),
           'frame_files_dir': None, 'codes': {},
           'transcripts_imported': 0, 'transcripts_skipped_present': 0,
           'frames_imported': 0, 'frame_codes_imported': 0,
           'frames_from_base64': 0, 'unresolved_codes': [], 'missing_frame_files': []}
    fdir = _first_existing([d for d in AUG_FRAME_DIRS if d.is_dir()])
    if fdir:
        rec['frame_files_dir'] = str(fdir.relative_to(ROOT))

    all_codes = sorted(set(tr_json) | set(fr_json) | set(on_disk) | set(b64_json))
    for code in all_codes:
        entry = {'in_reels': code in in_reels, 'transcript': 'skipped', 'frames': 'skipped'}

        # --- transcript ------------------------------------------------- #
        t = tr_json.get(code)
        if t and code not in have_tr:
            segs = t.get('segments') or []
            text = ' '.join(str(s.get('t') or '') for s in segs).strip()
            words = len(text.split()) if text else 0
            payload = canonical_json(segs)
            if not dry:
                con.execute('INSERT OR REPLACE INTO transcripts (code, lang, words, text, segments)'
                            ' VALUES (?,?,?,?,?)',
                            (code, t.get('lang') or 'en', words, text, payload))
                st = _segments_stats(payload, text)
                con.execute(
                    'INSERT OR REPLACE INTO transcript_meta '
                    '(code, provider, model, asr_version, language, lang_probability, media_sha256,'
                    ' words, tokens, chars, speech_seconds, words_per_second, segments_n,'
                    ' processing_seconds, created_at, version, note) '
                    'VALUES (?,?,NULL,NULL,?,NULL,NULL,?,?,?,?,?,?,NULL,?,1,?)',
                    (code, 'unknown', t.get('lang') or 'en', st['words'], st['tokens'],
                     st['chars'], st['speech_seconds'], st['words_per_second'],
                     st['segments_n'], '2026-08', AUG_NOTE))
            rec['transcripts_imported'] += 1
            entry['transcript'] = f'imported ({words} words, {len(segs)} segments)'
        elif t:
            rec['transcripts_skipped_present'] += 1
            entry['transcript'] = 'already present, left untouched'

        # --- frames ------------------------------------------------------ #
        files = on_disk.get(code, [])
        if code in have_fr:
            entry['frames'] = 'already present, left untouched'
        elif files:
            dest_dir = ROOT / 'data' / 'frames' / code
            if not dry:
                dest_dir.mkdir(parents=True, exist_ok=True)
            n = 0
            for idx, (ds, srcp) in enumerate(files):
                rel = f'data/frames/{code}/legacy_{idx:02d}.jpg'
                dest = ROOT / rel
                if not dry:
                    if not dest.exists() or dest.stat().st_size != srcp.stat().st_size:
                        dest.write_bytes(srcp.read_bytes())
                    con.execute(
                        'INSERT OR REPLACE INTO frames (code, idx, t_sec, path, sha256, exists_ok)'
                        ' VALUES (?,?,?,?,?,1)',
                        (code, idx, round(ds / 10.0, 1), rel, sha256_file(dest)))
                n += 1
            rec['frames_imported'] += n
            rec['frame_codes_imported'] += 1
            entry['frames'] = f'imported {n} jpgs as legacy_NN.jpg ({AUG_FRAMES_VERSION})'
        elif b64_json.get(code):
            # no jpgs on disk: fall back to the base64 bundle, timing unknown
            blobs = b64_json[code]
            dest_dir = ROOT / 'data' / 'frames' / code
            if not dry:
                dest_dir.mkdir(parents=True, exist_ok=True)
            for idx, blob in enumerate(blobs):
                rel = f'data/frames/{code}/legacy_{idx:02d}.jpg'
                dest = ROOT / rel
                if not dry:
                    payload = blob.split(',', 1)[1] if ',' in blob else blob
                    dest.write_bytes(base64.b64decode(payload))
                    con.execute(
                        'INSERT OR REPLACE INTO frames (code, idx, t_sec, path, sha256, exists_ok)'
                        ' VALUES (?,?,NULL,?,?,1)', (code, idx, rel, sha256_file(dest)))
            rec['frames_imported'] += len(blobs)
            rec['frames_from_base64'] += len(blobs)
            rec['frame_codes_imported'] += 1
            entry['frames'] = f'imported {len(blobs)} frames from frames_b64.json, t_sec unknown'
        elif fr_json.get(code):
            rec['missing_frame_files'].append(code)
            entry['frames'] = 'manifest lists jpgs but no file found on disk'

        if code not in in_reels:
            rec['unresolved_codes'].append(code)
        rec['codes'][code] = entry

    if not dry:
        con.commit()
    log['august_archive'] = rec
    print(f'  August archive: {rec["transcripts_imported"]} transcripts, '
          f'{rec["frames_imported"]} frames over {rec["frame_codes_imported"]} codes; '
          f'UNRESOLVED (no reels row): {len(rec["unresolved_codes"])}')


def step_f_video_state(con, log):
    summary = refresh_all_video_states(con, progress=1000)
    log['video_state'] = summary
    print(f'  video_state rows: {summary["codes"]}')
    print(f'    corpus_tier: {summary["corpus_tier"]}')
    print(f'    flags: {summary["flags"]}')


def step_g_providers(con, log):
    rows = []
    for name, kind, role, env_var, detail in PROVIDERS:
        present = env_present(env_var) if env_var else False
        if name == 'loore':
            state = 'CONFIGURED' if present else 'DISABLED'
        elif env_var:
            state = 'CONFIGURED' if present else 'NOT_CONFIGURED'
        elif name in ALWAYS_UNCONFIGURED:
            state = 'NOT_CONFIGURED'
        else:
            state = 'CONFIGURED'            # local tools need no credential
        con.execute('INSERT OR REPLACE INTO providers '
                    '(name, kind, role, state, env_var, checked_at, detail) VALUES (?,?,?,?,?,?,?)',
                    (name, kind, role, state, env_var, now(), detail))
        rows.append({'name': name, 'kind': kind, 'role': role, 'state': state,
                     'env_var': env_var})
    con.commit()
    log['providers'] = rows
    for r in rows:
        print(f'  {r["name"]:<22}{r["kind"]:<14}{r["role"]:<18}{r["state"]}')


# --------------------------------------------------------------------------- #
# validation
# --------------------------------------------------------------------------- #

def _orphans(con):
    q = lambda s: con.execute(s).fetchone()[0]                      # noqa: E731
    return {
        'scores_without_reel': q('SELECT COUNT(*) FROM scores s LEFT JOIN reels r '
                                 'USING(snapshot_id, code) WHERE r.code IS NULL'),
        'reels_from_unknown_account': q('SELECT COUNT(DISTINCT r.pk_user) FROM reels r '
                                        'LEFT JOIN accounts a ON a.pk=r.pk_user '
                                        'WHERE a.pk IS NULL'),
        'cards_without_reel': q('SELECT COUNT(*) FROM cards c LEFT JOIN reels r ON r.code=c.code '
                                'WHERE r.code IS NULL'),
        'our_metrics_without_post': q('SELECT COUNT(*) FROM our_metrics m LEFT JOIN our_posts p '
                                      'ON p.id=m.post_id WHERE p.id IS NULL'),
        'topics_without_reel': q('SELECT COUNT(DISTINCT t.code) FROM topics t LEFT JOIN '
                                 '(SELECT DISTINCT code FROM reels) r ON r.code=t.code '
                                 'WHERE r.code IS NULL'),
        'transcripts_without_reel': q('SELECT COUNT(*) FROM transcripts t LEFT JOIN '
                                      '(SELECT DISTINCT code FROM reels) r ON r.code=t.code '
                                      'WHERE r.code IS NULL'),
        'frame_codes_without_reel': q('SELECT COUNT(DISTINCT f.code) FROM frames f LEFT JOIN '
                                      '(SELECT DISTINCT code FROM reels) r ON r.code=f.code '
                                      'WHERE r.code IS NULL'),
        'deepdives_without_reel': q('SELECT COUNT(*) FROM deepdives d LEFT JOIN '
                                    '(SELECT DISTINCT code FROM reels) r ON r.code=d.code '
                                    'WHERE r.code IS NULL'),
        'transcript_meta_without_transcript': q(
            'SELECT COUNT(*) FROM transcript_meta m LEFT JOIN transcripts t ON t.code=m.code '
            'WHERE t.code IS NULL'),
        'video_state_without_reel': q('SELECT COUNT(*) FROM video_state v LEFT JOIN '
                                      '(SELECT DISTINCT code FROM reels) r ON r.code=v.code '
                                      'WHERE r.code IS NULL'),
        'frames_broken_reference': q('SELECT COUNT(*) FROM frames WHERE exists_ok=0'),
        'frames_unchecked': q('SELECT COUNT(*) FROM frames WHERE exists_ok IS NULL'),
    }


def _uniques(con):
    q = lambda s: con.execute(s).fetchone()[0]                      # noqa: E731
    return {
        'accounts': q('SELECT COUNT(*) FROM accounts'),
        'accounts_active': q("SELECT COUNT(*) FROM accounts WHERE status='active'"),
        'creators_with_reels': q('SELECT COUNT(DISTINCT pk_user) FROM reels'),
        'videos_unique_codes': q('SELECT COUNT(DISTINCT code) FROM reels'),
        'video_readings': q('SELECT COUNT(*) FROM reels'),
        'transcripts': q('SELECT COUNT(*) FROM transcripts'),
        'transcripts_usable': q('SELECT COUNT(*) FROM transcripts '
                                "WHERE words>0 AND segments NOT IN ('','[]')"),
        'transcript_meta': q('SELECT COUNT(*) FROM transcript_meta'),
        'frames_rows': q('SELECT COUNT(*) FROM frames'),
        'frames_codes': q('SELECT COUNT(DISTINCT code) FROM frames'),
        'deepdives': q('SELECT COUNT(*) FROM deepdives'),
        'cards': q('SELECT COUNT(*) FROM cards'),
        'video_state': q('SELECT COUNT(*) FROM video_state'),
    }


def _duplicates(con):
    q = lambda s: con.execute(s).fetchone()[0]                      # noqa: E731
    return {
        'reels_pk_violations': q('SELECT COUNT(*) FROM (SELECT snapshot_id, code FROM reels '
                                 'GROUP BY snapshot_id, code HAVING COUNT(*)>1)'),
        'codes_with_two_creator_ids': q(
            'SELECT COUNT(*) FROM (SELECT code FROM reels GROUP BY code HAVING '
            'COUNT(DISTINCT COALESCE(pk_user,-1) || "/" || COALESCE(username,""))>1)'),
        'duplicate_caption_groups': q(
            'SELECT COUNT(*) FROM (SELECT COALESCE(pk_user,-1) p, cap FROM reels '
            'WHERE cap IS NOT NULL AND LENGTH(cap)>30 GROUP BY p, cap '
            'HAVING COUNT(DISTINCT code)>1)'),
        'duplicate_caption_codes': q(
            'SELECT COUNT(DISTINCT code) FROM reels WHERE (COALESCE(pk_user,-1), cap) IN '
            '(SELECT COALESCE(pk_user,-1), cap FROM reels WHERE cap IS NOT NULL '
            ' AND LENGTH(cap)>30 GROUP BY COALESCE(pk_user,-1), cap '
            ' HAVING COUNT(DISTINCT code)>1)'),
        'frames_pk_violations': q('SELECT COUNT(*) FROM (SELECT code, idx FROM frames '
                                  'GROUP BY code, idx HAVING COUNT(*)>1)'),
    }


def step_h_validate(con, log, before, dry=False):
    after = row_counts(con)
    fk = [dict(zip(('table', 'rowid', 'parent', 'fkid'), r))
          for r in con.execute('PRAGMA foreign_key_check')]
    integrity = con.execute('PRAGMA integrity_check').fetchone()[0]
    tiers = {r[0]: r[1] for r in con.execute(
        'SELECT corpus_tier, COUNT(*) FROM video_state GROUP BY corpus_tier')}
    flags = {}
    for (raw,) in con.execute('SELECT flags_json FROM video_state'):
        for f in (loads(raw, []) or []):
            flags[f] = flags.get(f, 0) + 1

    validation = {
        'generated_at': now(),
        'db_path': log.get('db_path'),
        'dry_run': dry,
        'row_counts_before': before,
        'row_counts_after': after,
        'row_count_delta': {t: (after.get(t) or 0) - (before.get(t) or 0)
                            for t in sorted(set(before) | set(after))
                            if (after.get(t) or 0) != (before.get(t) or 0)},
        'uniques': _uniques(con),
        'orphans': _orphans(con),
        'duplicates': _duplicates(con),
        'foreign_key_violations': fk,
        'integrity_check': integrity,
        'corpus_tier': tiers,
        'flags': flags,
        'steps': log,
    }

    print('\n  before → after (changed tables only)')
    for t in sorted(validation['row_count_delta']):
        print(f'    {t:<22}{before.get(t, 0):>8} → {after.get(t, 0):>8}'
              f'   ({validation["row_count_delta"][t]:+d})')
    print('\n  uniques')
    for k, v in validation['uniques'].items():
        print(f'    {k:<34}{v:>8}')
    print('\n  orphans / broken references')
    for k, v in validation['orphans'].items():
        print(f'    {k:<34}{v:>8}')
    print('\n  duplicates')
    for k, v in validation['duplicates'].items():
        print(f'    {k:<34}{v:>8}')
    print(f'\n  foreign_key_check violations: {len(fk)}')
    print(f'  integrity_check: {integrity}')
    print(f'  corpus_tier: {tiers}')
    print(f'  flags: {flags}')

    if not dry:
        VALIDATION_JSON.parent.mkdir(parents=True, exist_ok=True)
        VALIDATION_JSON.write_text(json.dumps(validation, indent=2, ensure_ascii=False,
                                              sort_keys=True) + '\n')
        MIGRATION_LOG.parent.mkdir(parents=True, exist_ok=True)
        MIGRATION_LOG.write_text(_migration_log_md(validation))
        print(f'\n  wrote {VALIDATION_JSON.relative_to(ROOT)}')
        print(f'  wrote {MIGRATION_LOG.relative_to(ROOT)}')
    return validation


def _migration_log_md(v):
    """Reviewable migration log. Unmatched records are listed, never dropped."""
    steps = v['steps']
    aug = steps.get('august_archive', {}) or {}
    out = []
    w = out.append
    w('# M2Radar — legacy migration log\n')
    w(f'Generated {v["generated_at"]} by `python3 -m engine.migrate_legacy`. '
      f'Database: `{v.get("db_path")}`.\n')
    w('This file is rewritten on every run; it always describes the current database.\n')

    w('\n## Row counts, before → after\n')
    w('| table | before | after | delta |')
    w('|---|---:|---:|---:|')
    before, after = v['row_counts_before'], v['row_counts_after']
    for t in sorted(set(before) | set(after)):
        b, a = before.get(t), after.get(t)
        d = (a or 0) - (b or 0)
        w(f'| `{t}` | {"—" if b is None else b} | {"—" if a is None else a} '
          f'| {d:+d} |')

    w('\n## Identity counts\n')
    w('| what | n |')
    w('|---|---:|')
    for k, val in v['uniques'].items():
        w(f'| {k.replace("_", " ")} | {val} |')

    w('\n## Integrity\n')
    w('| check | result |')
    w('|---|---:|')
    for k, val in v['orphans'].items():
        w(f'| {k.replace("_", " ")} | {val} |')
    for k, val in v['duplicates'].items():
        w(f'| {k.replace("_", " ")} | {val} |')
    w(f'| foreign key violations | {len(v["foreign_key_violations"])} |')
    w(f'| sqlite integrity_check | {v["integrity_check"]} |')

    w('\n## Corpus tiers and flags\n')
    w('| corpus_tier | codes |')
    w('|---|---:|')
    for k, val in sorted(v['corpus_tier'].items()):
        w(f'| {k} | {val} |')
    w('')
    w('| flag | codes |')
    w('|---|---:|')
    for k, val in sorted(v['flags'].items()):
        w(f'| {k} | {val} |')

    w('\n## August 2026 archive import\n')
    if not aug.get('codes'):
        w('_Archive not found; nothing imported._\n')
    else:
        w(f'Manifests: `{aug.get("source_manifests")}`. '
          f'Frame files: `{aug.get("frame_files_dir")}`.\n')
        w(f'- transcripts imported: **{aug.get("transcripts_imported", 0)}** '
          f'(already present, untouched: {aug.get("transcripts_skipped_present", 0)})')
        w(f'- frames imported: **{aug.get("frames_imported", 0)}** over '
          f'{aug.get("frame_codes_imported", 0)} codes, written as '
          f'`data/frames/<code>/legacy_NN.jpg`, frames_version `{AUG_FRAMES_VERSION}`')
        if aug.get('frames_from_base64'):
            w(f'- of those, {aug["frames_from_base64"]} decoded from `frames_b64.json` '
              f'(timing unknown, `t_sec` left NULL)')
        if aug.get('missing_frame_files'):
            w(f'- manifest lists jpgs that are not on disk for: '
              f'{", ".join("`" + c + "`" for c in aug["missing_frame_files"])}')
        w('')
        w('| code | in `reels` | transcript | frames |')
        w('|---|---|---|---|')
        for code, e in sorted(aug['codes'].items()):
            w(f'| `{code}` | {"yes" if e["in_reels"] else "**no**"} '
              f'| {e["transcript"]} | {e["frames"]} |')

    w('\n## UNRESOLVED records — kept, not dropped, not invented\n')
    unresolved = aug.get('unresolved_codes') or []
    if not unresolved:
        w('_None._\n')
    else:
        w(f'{len(unresolved)} codes carry media analysis (transcript and/or frames) but have no '
          f'row in `reels`, so they have no metrics, no author and no `video_state` row. '
          f'Their transcripts and frames are imported and kept; **no `reels` row was '
          f'fabricated for them**. They are excluded from every denominator until a paid '
          f'HikerAPI lookup resolves them.\n')
        w('| code | why unresolved | what was kept |')
        w('|---|---|---|')
        for code in unresolved:
            e = aug['codes'][code]
            kept = []
            if e['transcript'].startswith('imported'):
                kept.append('transcript')
            if e['frames'].startswith('imported'):
                kept.append('frames')
            w(f'| `{code}` | no row in `reels` (August 2026 pass predates the database) '
              f'| {", ".join(kept) or "nothing"} |')

    w('\n## Provider registry\n')
    w('State is derived from the presence of an environment variable only. '
      'No credential value is read, printed or stored.\n')
    w('| provider | kind | role | state | env var |')
    w('|---|---|---|---|---|')
    for p in steps.get('providers', []):
        w(f'| `{p["name"]}` | {p["kind"]} | {p["role"]} | {p["state"]} '
          f'| {"`" + p["env_var"] + "`" if p["env_var"] else "—"} |')

    w('\n## Notes\n')
    tm = steps.get('transcript_meta', {})
    w(f'- `transcript_meta` now describes {tm.get("rows", 0)} transcripts. '
      f'{tm.get("local_faster_whisper", 0)} of them have a `deepdives` row, so they were '
      f'produced by `deep.py`: provider `{ASR_PROVIDER}`, model `{ASR_MODEL}`, '
      f'`asr_version` `{ASR_VERSION}`, `created_at` from `deepdives.done_at`. '
      f'{tm.get("unknown_provenance", 0)} have no deep dive and are recorded as '
      f'`provider = unknown` rather than given a provenance we cannot prove; '
      f'{tm.get("left_untouched", 0)} were already described and left untouched.')
    ff = steps.get('frames_files', {})
    w(f'- `frames.exists_ok` / `frames.sha256` set from disk: {ff.get("exists_ok", 0)} present, '
      f'{ff.get("broken", 0)} broken references '
      f'({", ".join("`" + c + "`" for c in sorted(ff.get("broken_by_code", {}))) or "none"}).')
    w(f'- `deepdives.evidence_state` set to `{EVIDENCE_STATE_LEGACY}` on '
      f'{steps.get("deepdives_evidence_state", {}).get("rows", 0)} rows.')
    w('- The migration is re-runnable: every write is `INSERT OR REPLACE` / `UPDATE` on a '
      'deterministic key, so a second run produces the same rows. Only `checked_at`, '
      '`updated_at` and this file\'s timestamp change.')
    return '\n'.join(out) + '\n'


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv=None):
    ap = argparse.ArgumentParser(description='Migrate the legacy corpus into the engine tables.')
    ap.add_argument('--db', default=None, help='path to radar.db (default: data/radar.db)')
    ap.add_argument('--dry', action='store_true',
                    help='write no data rows and no files; the schema migration still applies')
    args = ap.parse_args(argv)

    real = connect(args.db)
    con = _DryCon(real) if args.dry else real
    log = {'db_path': str(args.db or 'data/radar.db'), 'dry_run': args.dry}
    before = row_counts(real, table_names(real))

    try:
        if args.dry:
            print('DRY RUN — no data rows and no files are written.')
            print('          (the schema migration still applies: sqlite runs DDL in '
                  'autocommit)\n')
        print('a) schema')
        step_a_schema(con, log)
        before = {**before, **{t: before.get(t, 0) for t in engine_schema.ENGINE_TABLES}}

        print('\nb) transcript_meta backfill')
        step_b_transcript_meta(con, log)

        print('\nc) frames on disk (exists_ok, sha256)')
        step_c_frames_files(con, log)

        print('\nd) deepdives.evidence_state')
        step_d_evidence_state(con, log)

        print('\ne) August 2026 archive')
        step_e_august_archive(con, log, dry=args.dry)

        print('\nf) video_state')
        step_f_video_state(con, log)

        print('\ng) providers')
        step_g_providers(con, log)

        print('\nh) validation')
        step_h_validate(con, log, before, dry=args.dry)
    finally:
        if args.dry:
            real.rollback()
        real.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
