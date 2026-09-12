"""Tests for engine.schema / engine.state / engine.migrate_legacy.

Self-contained: every test builds a fresh SQLite file from `db.SCHEMA` plus a
handful of synthetic rows. Nothing here reads `data/radar.db`, so the suite
keeps passing whatever the live corpus looks like.

    python3 -m pytest tests/test_engine_schema.py -q
"""
import json
import os
import pathlib
import sqlite3
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import db as legacy_db                                              # noqa: E402
from engine import migrate_legacy, schema, state                    # noqa: E402
from engine.db_util import canonical_json, loads                    # noqa: E402


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #

def _blank(tmp_path):
    """Legacy schema only — no engine tables yet."""
    con = sqlite3.connect(tmp_path / 'test.db')
    con.row_factory = sqlite3.Row
    con.executescript(legacy_db.SCHEMA)
    con.commit()
    return con


def _seed(con):
    """A miniature corpus that exercises every tier and every flag.

    snapshot 1 (old) and snapshot 2 (newest, `done=1`).

      READY0001  transcript + frames + beats + labels -> ANALYSIS_READY, analysis_ready=1
      READY0002  transcript + frames, no analysis     -> ANALYSIS_READY, analysis_ready=0
      FRAMESONLY frames, no transcript row            -> FRAMES_ONLY + MISSING_TRANSCRIPT
      NOSPEECH01 frames + words=0, segments '[]'      -> FRAMES_ONLY + EMPTY_NO_SPEECH
      BROKEN0001 frames present but files missing     -> PARTIAL + BROKEN/MISSING_MEDIA
      STALE00001 only in snapshot 1                   -> STALE_METRICS
      DUPE00001 / DUPE00002 same author + caption     -> DUPLICATE_VIDEO
      NOSTATS001 play NULL in every row               -> MISSING_STATS
      TWOIDS0001 two pk/username pairs                -> UNRESOLVED_CREATOR_ID
    """
    con.execute("INSERT INTO snapshots (id, taken, done) VALUES (1,'2026-09-01',1)")
    con.execute("INSERT INTO snapshots (id, taken, done) VALUES (2,'2026-09-10',1)")
    con.execute("INSERT INTO accounts (pk, username, tag, status) VALUES (11,'alice','core','active')")
    con.execute("INSERT INTO accounts (pk, username, tag, status) VALUES (22,'bob','core','active')")

    long_cap = 'the very same caption reposted under a different code'   # > 30 chars

    def reel(sid, code, pk=11, user='alice', play=1000, cap='cap', dur=30.0):
        con.execute('INSERT INTO reels (snapshot_id, code, pk_user, username, ts, kind, play, '
                    'likes, comm, resh, save, dur, cap, followers) '
                    'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (sid, code, pk, user, 1760000000, 'clip', play, 10, 2, 3, 4, dur, cap, 5000))

    for code in ('READY0001', 'READY0002', 'FRAMESONLY', 'NOSPEECH01', 'BROKEN0001',
                 'NOSTATS001', 'TWOIDS0001'):
        reel(1, code)
        reel(2, code)
    reel(1, 'STALE00001')                                   # never refreshed in snapshot 2
    reel(1, 'DUPE00001', cap=long_cap); reel(2, 'DUPE00001', cap=long_cap)
    reel(1, 'DUPE00002', cap=long_cap); reel(2, 'DUPE00002', cap=long_cap)

    con.execute("UPDATE reels SET play=NULL WHERE code='NOSTATS001'")
    con.execute("UPDATE reels SET pk_user=22, username='bob' "
                "WHERE code='TWOIDS0001' AND snapshot_id=2")

    segs = canonical_json([{'s': 0.0, 'e': 2.0, 't': 'hello there friend'},
                           {'s': 2.0, 'e': 5.0, 't': 'and now the point'}])
    for code in ('READY0001', 'READY0002', 'BROKEN0001'):
        con.execute("INSERT INTO transcripts (code, lang, words, text, segments) "
                    "VALUES (?,'en',7,'hello there friend and now the point',?)", (code, segs))
    con.execute("INSERT INTO transcripts (code, lang, words, text, segments) "
                "VALUES ('NOSPEECH01','en',0,'','[]')")

    for code in ('READY0001', 'READY0002', 'FRAMESONLY', 'NOSPEECH01', 'BROKEN0001'):
        con.execute("INSERT INTO deepdives (code, snapshot_id, cuts, cuts_ps, mp4_mb, sheet, "
                    "done_at) VALUES (?,2,3,0.1,1.5,?, '2026-09-10')",
                    (code, f'data/frames/{code}_sheet.jpg'))
        for i in range(3):
            con.execute('INSERT INTO frames (code, idx, t_sec, path, exists_ok) VALUES (?,?,?,?,1)',
                        (code, i, 0.4 * (i + 1), f'data/frames/{code}/{i:02d}.jpg'))
    con.execute("UPDATE frames SET exists_ok=0 WHERE code='BROKEN0001' AND idx IN (1,2)")
    con.commit()


def _add_analysis(con, code):
    """Beats + frame labels, so the code can reach analysis_ready=1."""
    con.execute("INSERT INTO beats (beat_id, code, idx, role, start_s, end_s, text, "
                "scene_ids_json, analysis_version) VALUES (?,?,0,'hook',0.0,2.0,'hi',?,'ta-v1')",
                (f'B-{code}', code, canonical_json(['S1'])))
    con.execute("INSERT INTO frame_labels (code, idx, t_sec, frame_type, roll, analysis_version) "
                "VALUES (?,0,0.4,'A_ROLL_CLOSE_UP','A','fa-v1')", (code,))
    con.commit()


@pytest.fixture()
def con(tmp_path):
    c = _blank(tmp_path)
    schema.migrate(c)
    _seed(c)
    yield c
    c.close()


@pytest.fixture()
def ctx_root(tmp_path):
    """Root used for media/frame file lookups inside the tests."""
    return tmp_path


def _state(con, code, root):
    ctx = state._Context(con, root=root)
    return state.compute_video_state(ctx, code)


def _flags(row):
    return set(loads(row['flags_json'], []))


# --------------------------------------------------------------------------- #
# 1. migration
# --------------------------------------------------------------------------- #

def test_migration_creates_every_engine_table(tmp_path):
    c = _blank(tmp_path)
    assert schema.migrate(c) == [v for v, _, _ in schema.MIGRATIONS]
    names = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for t in schema.ENGINE_TABLES:
        assert t in names, f'{t} missing after migrate()'
    for t in schema.LEGACY_TABLES:
        assert t in names, f'legacy table {t} was lost'
    c.close()


def test_migration_is_idempotent(tmp_path):
    c = _blank(tmp_path)
    schema.migrate(c)
    before = sorted(r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'"))
    assert schema.migrate(c) == []                  # nothing left to do
    assert schema.migrate(c) == []                  # and again
    after = sorted(r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'"))
    assert before == after
    assert schema.applied_versions(c) == [v for v, _, _ in schema.MIGRATIONS]
    assert c.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()[0] == len(
        schema.MIGRATIONS)
    assert schema.pending_versions(c) == []
    c.close()


def test_migration_adds_guarded_columns(tmp_path):
    c = _blank(tmp_path)
    schema.migrate(c)
    for table, col, _ in schema.ADDED_COLUMNS:
        cols = {r[1] for r in c.execute(f'PRAGMA table_info({table})')}
        assert col in cols, f'{table}.{col} missing'
    schema._add_columns(c)                          # running the step twice must not raise
    c.close()


def test_migration_keeps_existing_legacy_data(tmp_path):
    """Legacy rows written before the migration survive it untouched."""
    c = _blank(tmp_path)
    c.execute("INSERT INTO snapshots (id, taken, done) VALUES (1,'2026-09-01',1)")
    c.execute("INSERT INTO accounts (pk, username, tag, status) "
              "VALUES (11,'alice','core','active')")
    c.execute("INSERT INTO reels (snapshot_id, code, pk_user, username, play, dur, cap) "
              "VALUES (1,'LEGACY0001',11,'alice',4242,30.0,'hello')")
    c.execute("INSERT INTO frames (code, idx, t_sec, path) "
              "VALUES ('LEGACY0001',0,0.4,'data/frames/LEGACY0001/00.jpg')")
    c.commit()
    schema.migrate(c)                               # data first, migration after
    row = c.execute("SELECT * FROM reels WHERE code='LEGACY0001'").fetchone()
    assert row['play'] == 4242 and row['cap'] == 'hello'
    assert row['fetch_id'] is None                  # new column, empty, nothing overwritten
    frame = c.execute("SELECT * FROM frames WHERE code='LEGACY0001'").fetchone()
    assert frame['path'] == 'data/frames/LEGACY0001/00.jpg'
    assert frame['exists_ok'] is None and frame['sha256'] is None
    c.close()


def test_schema_cli_check_reports_pending(tmp_path, capsys):
    path = tmp_path / 'cli.db'
    c = _blank(tmp_path)
    c.close()
    os.replace(tmp_path / 'test.db', path)
    assert schema.main(['--db', str(path), '--check']) == 1     # pending
    assert schema.main(['--db', str(path)]) == 0                # applies
    assert schema.main(['--db', str(path), '--check']) == 0     # now clean
    out = capsys.readouterr().out
    assert 'applied migrations' in out


# --------------------------------------------------------------------------- #
# 2. runs and jobs
# --------------------------------------------------------------------------- #

def test_run_id_shape(con):
    run_id = state.start_run(con, 'manual', config={'limit': 3})
    assert len(run_id) == 22 and run_id[10] == '_' and run_id[15] == '-'
    row = con.execute('SELECT * FROM runs WHERE run_id=?', (run_id,)).fetchone()
    assert row['status'] == 'RUNNING' and row['kind'] == 'manual'
    assert json.loads(row['config_json']) == {'limit': 3}


def test_start_run_rejects_unknown_kind(con):
    with pytest.raises(ValueError):
        state.start_run(con, 'nonsense')


def test_job_success_writes_done_with_duration(con):
    run_id = state.start_run(con, 'analysis')
    with state.job(con, run_id, 'video', 'READY0001', 'TRANSCRIPTION', provider='local') as j:
        j.set(model='small', output_refs_json={'words': 7})
    row = state.latest_job(con, 'video', 'READY0001', 'TRANSCRIPTION')
    assert row['state'] == 'DONE'
    assert row['provider'] == 'local' and row['model'] == 'small'
    assert row['duration_s'] is not None and row['duration_s'] >= 0
    assert row['error'] is None and row['retries'] == 0
    assert row['previous_state'] is None
    assert json.loads(row['output_refs_json']) == {'words': 7}


def test_job_failure_records_error_and_reraises(con):
    run_id = state.start_run(con, 'analysis')
    with pytest.raises(RuntimeError, match='ffmpeg exploded'):
        with state.job(con, run_id, 'video', 'READY0001', 'FRAME_EXTRACTION'):
            raise RuntimeError('ffmpeg exploded')
    row = state.latest_job(con, 'video', 'READY0001', 'FRAME_EXTRACTION')
    assert row['state'] == 'FAILED'
    assert 'ffmpeg exploded' in row['error'] and row['error'].startswith('RuntimeError')
    assert row['finished_at'] is not None and row['duration_s'] is not None


def test_job_retry_counter_and_previous_state(con):
    run_id = state.start_run(con, 'analysis')
    with pytest.raises(RuntimeError):
        with state.job(con, run_id, 'video', 'READY0002', 'TRANSCRIPTION'):
            raise RuntimeError('boom')
    with state.job(con, run_id, 'video', 'READY0002', 'TRANSCRIPTION'):
        pass
    row = state.latest_job(con, 'video', 'READY0002', 'TRANSCRIPTION')
    assert row['state'] == 'DONE'
    assert row['retries'] == 1
    assert row['previous_state'] == 'FAILED'


def test_job_can_be_skipped(con):
    run_id = state.start_run(con, 'watchdog')
    with state.job(con, run_id, 'video', 'STALE00001', 'MEDIA_FETCHED') as j:
        j.skip('no live URL in cache')
    row = state.latest_job(con, 'video', 'STALE00001', 'MEDIA_FETCHED')
    assert row['state'] == 'SKIPPED' and row['validation'] == 'no live URL in cache'


def test_job_rejects_unknown_stage_and_entity(con):
    run_id = state.start_run(con, 'manual')
    with pytest.raises(ValueError):
        with state.job(con, run_id, 'video', 'X', 'NOT_A_STAGE'):
            pass
    with pytest.raises(ValueError):
        with state.job(con, run_id, 'banana', 'X', 'TRANSCRIPTION'):
            pass


def test_run_summary_counts_per_stage(con):
    run_id = state.start_run(con, 'analysis')
    for code in ('READY0001', 'READY0002'):
        with state.job(con, run_id, 'video', code, 'TRANSCRIPTION'):
            pass
    with pytest.raises(RuntimeError):
        with state.job(con, run_id, 'video', 'BROKEN0001', 'FRAME_EXTRACTION'):
            raise RuntimeError('nope')
    state.finish_run(con, run_id, 'DONE', summary={'ok': True})

    s = state.run_summary(con, run_id)
    assert s['stages']['TRANSCRIPTION'] == {'DONE': 2}
    assert s['stages']['FRAME_EXTRACTION'] == {'FAILED': 1}
    assert s['totals'] == {'DONE': 2, 'FAILED': 1}
    assert s['jobs'] == 3
    row = con.execute('SELECT * FROM runs WHERE run_id=?', (run_id,)).fetchone()
    assert row['status'] == 'DONE' and row['finished_at'] is not None
    assert json.loads(row['summary_json']) == {'ok': True}


# --------------------------------------------------------------------------- #
# 3. video_state
# --------------------------------------------------------------------------- #

def test_tier_analysis_ready(con, ctx_root):
    row = _state(con, 'READY0002', ctx_root)
    assert row['transcript_state'] == 'DONE'
    assert row['frames_state'] == 'DONE_FIXED9'
    assert row['corpus_tier'] == 'ANALYSIS_READY'
    assert row['analysis_ready'] == 0               # no beats / frame_labels yet
    assert row['frames_version'] == state.FRAMES_VERSION_FIXED9
    assert row['alignment_state'] == 'MISSING'
    assert _flags(row) == set()


def test_analysis_ready_flag_needs_both_analyses(con, ctx_root):
    _add_analysis(con, 'READY0001')
    row = _state(con, 'READY0001', ctx_root)
    assert row['transcript_analysis_state'] == 'DONE'
    assert row['frame_analysis_state'] == 'DONE'
    assert row['alignment_state'] == 'DONE'         # beats carry scene_ids_json
    assert row['analysis_ready'] == 1
    assert row['analysis_version'] == 'ta-v1'


def test_tier_frames_only_without_transcript(con, ctx_root):
    row = _state(con, 'FRAMESONLY', ctx_root)
    assert row['transcript_state'] == 'MISSING'
    assert row['corpus_tier'] == 'FRAMES_ONLY'
    assert 'MISSING_TRANSCRIPT' in _flags(row)
    assert row['alignment_state'] == 'NOT_POSSIBLE'


def test_empty_transcript_is_no_speech_and_unaligned(con, ctx_root):
    row = _state(con, 'NOSPEECH01', ctx_root)
    assert row['transcript_state'] == 'EMPTY_NO_SPEECH'
    assert row['corpus_tier'] == 'FRAMES_ONLY'
    assert 'UNALIGNED_TRANSCRIPT' in _flags(row)
    assert 'MISSING_TRANSCRIPT' not in _flags(row)   # the row exists, it is simply silent


def test_tier_ingested_not_analyzed(con, ctx_root):
    row = _state(con, 'STALE00001', ctx_root)
    assert row['corpus_tier'] == 'INGESTED_NOT_ANALYZED'
    assert row['frames_state'] == 'MISSING'
    assert {'MISSING_FRAMES', 'MISSING_TRANSCRIPT', 'STALE_METRICS'} <= _flags(row)


def test_broken_frames_make_state_partial(con, ctx_root):
    row = _state(con, 'BROKEN0001', ctx_root)
    assert row['frames_state'] == 'PARTIAL'
    assert 'BROKEN_FRAME_REFERENCE' in _flags(row)
    assert 'MISSING_MEDIA' in _flags(row)            # 2 of 3 files gone
    assert row['media_state'] == 'MISSING'


def test_scene_frames_switch_state_and_version(con, ctx_root):
    con.execute("INSERT INTO scenes (scene_id, code, idx, start_s, end_s, duration_s, "
                "boundary_reason, frames_version) VALUES "
                "('S-READY0002-0','READY0002',0,0.0,3.0,3.0,'detector',?)",
                (state.FRAMES_VERSION_SCENE,))
    con.commit()
    row = _state(con, 'READY0002', ctx_root)
    assert row['frames_state'] == 'DONE_SCENE'
    assert row['frames_version'] == state.FRAMES_VERSION_SCENE


def test_aug2026_frames_are_detected_by_path(con, ctx_root):
    con.execute("DELETE FROM frames WHERE code='READY0002'")
    for i in range(3):
        con.execute('INSERT INTO frames (code, idx, t_sec, path, exists_ok) VALUES (?,?,?,?,1)',
                    ('READY0002', i, 0.4, f'data/frames/READY0002/legacy_{i:02d}.jpg'))
    con.commit()
    assert _state(con, 'READY0002', ctx_root)['frames_version'] == state.FRAMES_VERSION_AUG2026


def test_flag_duplicate_video(con, ctx_root):
    for code in ('DUPE00001', 'DUPE00002'):
        assert 'DUPLICATE_VIDEO' in _flags(_state(con, code, ctx_root))
    assert 'DUPLICATE_VIDEO' not in _flags(_state(con, 'READY0001', ctx_root))


def test_flag_missing_stats_and_unresolved_creator(con, ctx_root):
    assert 'MISSING_STATS' in _flags(_state(con, 'NOSTATS001', ctx_root))
    assert 'UNRESOLVED_CREATOR_ID' in _flags(_state(con, 'TWOIDS0001', ctx_root))
    assert 'UNRESOLVED_CREATOR_ID' not in _flags(_state(con, 'READY0001', ctx_root))


def test_snapshot_bounds(con, ctx_root):
    row = _state(con, 'READY0001', ctx_root)
    assert (row['first_snapshot_id'], row['last_snapshot_id']) == (1, 2)
    assert row['ingested_at'] == '2026-09-01'


def test_refresh_all_is_idempotent_and_counts_tiers(con):
    first = state.refresh_all_video_states(con)
    assert first['codes'] == con.execute(
        'SELECT COUNT(DISTINCT code) FROM reels').fetchone()[0]
    assert first['corpus_tier']['ANALYSIS_READY'] == 3        # READY0001/2 + BROKEN0001
    assert first['corpus_tier']['FRAMES_ONLY'] == 2           # FRAMESONLY + NOSPEECH01
    assert first['flags']['STALE_METRICS'] == 1
    assert first['flags']['DUPLICATE_VIDEO'] == 2

    snap = {r['code']: dict(r) for r in con.execute('SELECT * FROM video_state')}
    second = state.refresh_all_video_states(con)
    assert second['corpus_tier'] == first['corpus_tier']
    again = {r['code']: dict(r) for r in con.execute('SELECT * FROM video_state')}
    for code, row in snap.items():                 # only the timestamp may move
        assert {k: v for k, v in row.items() if k != 'updated_at'} == \
               {k: v for k, v in again[code].items() if k != 'updated_at'}


def test_refresh_video_state_writes_one_row(con, ctx_root):
    ctx = state._Context(con, root=ctx_root)
    state.refresh_video_state(con, 'READY0001', ctx=ctx)
    row = con.execute("SELECT * FROM video_state WHERE code='READY0001'").fetchone()
    assert row['corpus_tier'] == 'ANALYSIS_READY'
    assert con.execute('SELECT COUNT(*) FROM video_state').fetchone()[0] == 1


def test_explicit_versions_override_derived(con, ctx_root):
    ctx = state._Context(con, root=ctx_root)
    row = state.refresh_video_state(con, 'READY0001', ctx=ctx,
                                    asr_version='x-v9', frames_version='scene-v1')
    assert row['asr_version'] == 'x-v9' and row['frames_version'] == 'scene-v1'


def test_corpus_codes_helper(con):
    state.refresh_all_video_states(con)
    assert 'FRAMESONLY' in state.corpus_codes(con, 'FRAMES_ONLY')
    assert 'READY0001' in state.corpus_codes(con, 'ANALYSIS_READY')


# --------------------------------------------------------------------------- #
# 4. legacy backfill
# --------------------------------------------------------------------------- #

def test_segments_stats():
    segs = canonical_json([{'s': 0.0, 'e': 2.0, 't': 'one two three'},
                           {'s': 2.0, 'e': 4.5, 't': 'four five'}])
    st = migrate_legacy._segments_stats(segs, 'one two three four five')
    assert st['segments_n'] == 2
    assert st['words'] == 5
    assert st['chars'] == len('one two three four five')
    assert st['speech_seconds'] == 4.5
    assert st['words_per_second'] == round(5 / 4.5, 3)
    assert st['tokens'] == 7                       # round(5 * 1.3)


def test_segments_stats_on_empty_segments():
    st = migrate_legacy._segments_stats('[]', '')
    assert st == {'segments_n': 0, 'words': 0, 'chars': 0, 'speech_seconds': None,
                  'words_per_second': None, 'tokens': 0}


def test_backfill_transcript_meta(con):
    log = {}
    migrate_legacy.step_b_transcript_meta(con, log)
    assert log['transcript_meta']['rows'] == 4
    assert log['transcript_meta']['local_faster_whisper'] == 4
    assert log['transcript_meta']['unknown_provenance'] == 0
    row = con.execute("SELECT * FROM transcript_meta WHERE code='READY0001'").fetchone()
    assert row['provider'] == migrate_legacy.ASR_PROVIDER
    assert row['asr_version'] == migrate_legacy.ASR_VERSION
    assert row['model'] == migrate_legacy.ASR_MODEL
    assert row['language'] == 'en'
    assert row['segments_n'] == 2 and row['words'] == 7
    assert row['speech_seconds'] == 5.0
    assert row['created_at'] == '2026-09-10'        # from deepdives.done_at
    assert row['version'] == 1

    migrate_legacy.step_b_transcript_meta(con, {})  # re-runnable
    assert con.execute('SELECT COUNT(*) FROM transcript_meta').fetchone()[0] == 4


def test_transcript_without_deepdive_gets_unknown_provenance(con):
    """A transcript we did not produce must never be labelled faster-whisper."""
    con.execute("INSERT INTO transcripts (code, lang, words, text, segments) "
                "VALUES ('ORPHANTR01','en',2,'two words',?)",
                (canonical_json([{'s': 0.0, 'e': 1.0, 't': 'two words'}]),))
    con.commit()

    log = {}
    migrate_legacy.step_b_transcript_meta(con, log)
    assert log['transcript_meta']['unknown_provenance'] == 1
    row = con.execute("SELECT * FROM transcript_meta WHERE code='ORPHANTR01'").fetchone()
    assert row['provider'] == 'unknown'
    assert row['asr_version'] is None and row['model'] is None
    assert row['created_at'] is None
    assert row['note'] == migrate_legacy.UNKNOWN_PROVENANCE_NOTE


def test_backfill_does_not_overwrite_archive_provenance(con):
    """Step (b) must leave a transcript already described by step (e) alone."""
    con.execute("INSERT INTO transcripts (code, lang, words, text, segments) "
                "VALUES ('AUGOLD0001','en',2,'old words','[]')")
    con.execute("INSERT INTO transcript_meta (code, provider, asr_version, note) "
                "VALUES ('AUGOLD0001','unknown',NULL,?)", (migrate_legacy.AUG_NOTE,))
    con.commit()

    log = {}
    migrate_legacy.step_b_transcript_meta(con, log)
    assert log['transcript_meta']['left_untouched'] == 1
    row = con.execute("SELECT * FROM transcript_meta WHERE code='AUGOLD0001'").fetchone()
    assert row['provider'] == 'unknown' and row['note'] == migrate_legacy.AUG_NOTE
    assert row['asr_version'] is None


def test_backfill_evidence_state(con):
    log = {}
    migrate_legacy.step_d_evidence_state(con, log)
    assert log['deepdives_evidence_state']['rows'] == 5
    assert {r[0] for r in con.execute('SELECT DISTINCT evidence_state FROM deepdives')} == \
           {migrate_legacy.EVIDENCE_STATE_LEGACY}


def test_frames_exists_ok_and_sha256(con, tmp_path, monkeypatch):
    monkeypatch.setattr(migrate_legacy, 'ROOT', tmp_path)
    present = tmp_path / 'data' / 'frames' / 'READY0001'
    present.mkdir(parents=True)
    for i in range(3):
        (present / f'{i:02d}.jpg').write_bytes(b'jpeg-bytes-' + str(i).encode())

    log = {}
    migrate_legacy.step_c_frames_files(con, log)
    assert log['frames_files']['exists_ok'] == 3
    assert log['frames_files']['broken'] == 12       # 4 other codes x 3 frames
    rows = con.execute("SELECT idx, exists_ok, sha256 FROM frames WHERE code='READY0001' "
                       'ORDER BY idx').fetchall()
    assert [r['exists_ok'] for r in rows] == [1, 1, 1]
    assert all(r['sha256'] and len(r['sha256']) == 64 for r in rows)
    assert len({r['sha256'] for r in rows}) == 3     # different bytes, different hash

    missing = con.execute("SELECT exists_ok, sha256 FROM frames WHERE code='FRAMESONLY' "
                          'AND idx=0').fetchone()
    assert missing['exists_ok'] == 0 and missing['sha256'] is None

    before = con.execute('SELECT code, idx, sha256 FROM frames ORDER BY code, idx').fetchall()
    migrate_legacy.step_c_frames_files(con, {})      # re-runnable, byte-identical
    after = con.execute('SELECT code, idx, sha256 FROM frames ORDER BY code, idx').fetchall()
    assert [tuple(r) for r in before] == [tuple(r) for r in after]


def test_providers_never_store_secret_values(con, monkeypatch):
    monkeypatch.delenv('LOORE_KEY', raising=False)
    monkeypatch.setattr(migrate_legacy, 'env_present', lambda name: name == 'HIKER_KEY')
    log = {}
    migrate_legacy.step_g_providers(con, log)
    got = {r['name']: r for r in con.execute('SELECT * FROM providers')}
    assert got['hiker']['state'] == 'CONFIGURED' and got['hiker']['role'] == 'DEFAULT'
    assert got['loore']['state'] == 'DISABLED'
    assert got['local-faster-whisper']['state'] == 'CONFIGURED'
    assert got['supabase']['state'] == 'NOT_CONFIGURED'
    assert got['higgsfield']['state'] == 'NOT_CONFIGURED'
    # env_var holds the NAME of the variable, never a value
    assert got['hiker']['env_var'] == 'HIKER_KEY'
    for row in got.values():
        assert 'secret' not in (row['detail'] or '').lower()


def test_august_import_only_touches_absent_codes(con, tmp_path, monkeypatch):
    """The importer must never overwrite a transcript or frame set we already have."""
    src = tmp_path / 'dataset' / '2026-08-niche-research'
    frames_dir = src / 'frames'
    frames_dir.mkdir(parents=True)
    (src / 'transcripts.json').write_text(json.dumps({
        'READY0001': {'lang': 'en', 'segments': [{'s': 0, 'e': 1, 't': 'should be ignored'}]},
        'AUGNEW0001': {'lang': 'en', 'segments': [{'s': 0.0, 'e': 3.0, 't': 'brand new words'}]},
    }))
    (src / 'frames.json').write_text(json.dumps({'AUGNEW0001': ['frames/AUGNEW0001_0004.jpg']}))
    for ds in (4, 12, 240):
        (frames_dir / f'AUGNEW0001_{ds:04d}.jpg').write_bytes(b'jpeg' + str(ds).encode())

    monkeypatch.setattr(migrate_legacy, 'ROOT', tmp_path)
    monkeypatch.setattr(migrate_legacy, 'AUG_JSON_DIRS', [src])
    monkeypatch.setattr(migrate_legacy, 'AUG_FRAME_DIRS', [frames_dir])

    log = {}
    migrate_legacy.step_e_august_archive(con, log)
    rec = log['august_archive']

    assert rec['transcripts_imported'] == 1
    assert rec['transcripts_skipped_present'] == 1
    assert rec['frames_imported'] == 3
    # AUGNEW0001 has no reels row -> UNRESOLVED, and no reels row is invented
    assert rec['unresolved_codes'] == ['AUGNEW0001']
    assert con.execute("SELECT COUNT(*) FROM reels WHERE code='AUGNEW0001'").fetchone()[0] == 0

    new = con.execute("SELECT * FROM transcripts WHERE code='AUGNEW0001'").fetchone()
    assert new['words'] == 3 and new['text'] == 'brand new words'
    meta = con.execute("SELECT * FROM transcript_meta WHERE code='AUGNEW0001'").fetchone()
    assert meta['provider'] == 'unknown'
    assert meta['asr_version'] is None
    assert meta['note'] == migrate_legacy.AUG_NOTE

    frames = con.execute("SELECT idx, t_sec, path, exists_ok, sha256 FROM frames "
                         "WHERE code='AUGNEW0001' ORDER BY idx").fetchall()
    assert [r['path'] for r in frames] == [f'data/frames/AUGNEW0001/legacy_{i:02d}.jpg'
                                           for i in range(3)]
    assert [r['t_sec'] for r in frames] == [0.4, 1.2, 24.0]      # file number is deciseconds
    assert all(r['exists_ok'] == 1 and r['sha256'] for r in frames)
    for i in range(3):
        assert (tmp_path / 'data' / 'frames' / 'AUGNEW0001' / f'legacy_{i:02d}.jpg').is_file()

    # the existing transcript is untouched
    assert con.execute("SELECT text FROM transcripts WHERE code='READY0001'").fetchone()[0] \
        == 'hello there friend and now the point'

    # second run changes nothing
    log2 = {}
    migrate_legacy.step_e_august_archive(con, log2)
    assert log2['august_archive']['transcripts_imported'] == 0
    assert log2['august_archive']['frames_imported'] == 0
    assert con.execute('SELECT COUNT(*) FROM transcripts').fetchone()[0] == 5


def test_august_import_falls_back_to_base64(con, tmp_path, monkeypatch):
    src = tmp_path / 'archive'
    src.mkdir(parents=True)
    (src / 'transcripts.json').write_text(json.dumps({}))
    (src / 'frames.json').write_text(json.dumps({}))
    import base64 as b64mod
    blob = 'data:image/jpeg;base64,' + b64mod.b64encode(b'raw-jpeg').decode()
    (src / 'frames_b64.json').write_text(json.dumps({'B64CODE001': [blob, blob]}))

    monkeypatch.setattr(migrate_legacy, 'ROOT', tmp_path)
    monkeypatch.setattr(migrate_legacy, 'AUG_JSON_DIRS', [src])
    monkeypatch.setattr(migrate_legacy, 'AUG_FRAME_DIRS', [])

    log = {}
    migrate_legacy.step_e_august_archive(con, log)
    assert log['august_archive']['frames_from_base64'] == 2
    rows = con.execute("SELECT t_sec, path FROM frames WHERE code='B64CODE001'").fetchall()
    assert [r['t_sec'] for r in rows] == [None, None]     # timing genuinely unknown
    assert (tmp_path / 'data' / 'frames' / 'B64CODE001' / 'legacy_00.jpg').read_bytes() \
        == b'raw-jpeg'


def test_full_migration_validation_block(con, tmp_path, monkeypatch):
    """Steps b, d, f, g plus validation, end to end on the synthetic corpus."""
    monkeypatch.setattr(migrate_legacy, 'ROOT', tmp_path)
    monkeypatch.setattr(migrate_legacy, 'AUG_JSON_DIRS', [])
    monkeypatch.setattr(migrate_legacy, 'AUG_FRAME_DIRS', [])
    monkeypatch.setattr(migrate_legacy, 'MIGRATION_LOG', tmp_path / 'migration_log.md')
    monkeypatch.setattr(migrate_legacy, 'VALIDATION_JSON', tmp_path / 'validation.json')

    from engine.db_util import row_counts, table_names
    before = row_counts(con, table_names(con))
    log = {'db_path': str(tmp_path / 'test.db')}
    migrate_legacy.step_b_transcript_meta(con, log)
    migrate_legacy.step_c_frames_files(con, log)
    migrate_legacy.step_d_evidence_state(con, log)
    migrate_legacy.step_e_august_archive(con, log)
    migrate_legacy.step_f_video_state(con, log)
    migrate_legacy.step_g_providers(con, log)
    v = migrate_legacy.step_h_validate(con, log, before)

    assert v['integrity_check'] == 'ok'
    assert v['foreign_key_violations'] == []
    assert v['uniques']['video_state'] == v['uniques']['videos_unique_codes']
    assert v['orphans']['transcript_meta_without_transcript'] == 0
    assert v['orphans']['video_state_without_reel'] == 0
    assert v['row_count_delta']['transcript_meta'] == 4
    assert (tmp_path / 'migration_log.md').is_file()
    assert (tmp_path / 'validation.json').is_file()
    written = json.loads((tmp_path / 'validation.json').read_text())
    assert written['corpus_tier'] == v['corpus_tier']
    md = (tmp_path / 'migration_log.md').read_text()
    assert 'UNRESOLVED' in md and 'Provider registry' in md
