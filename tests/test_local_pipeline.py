"""Tests for engine/scenes.py, engine/local_pipeline.py, engine/align.py, engine/watchdog.py.

Uses a synthetic 12-second video (three 4s hard-cut color segments) generated with the
same `imageio_ffmpeg` binary the pipeline itself uses — no network, no HikerAPI, no
real faster-whisper weights downloaded for the default (fast) test run.

Note on the synthetic colors: ffmpeg's built-in `scene` cut score is computed on the
luma (Y) plane only. Named colors `red`/`green` land on nearly the same luma and a cut
between them is invisible to the detector even at threshold 0 (confirmed empirically
while writing this fixture) — so the fixture uses black/gray/white, which are maximally
separated in luma and reliably produce two detected cuts.

    M2_REAL_ASR=1 python3 -m pytest tests/test_local_pipeline.py -q -m slow
runs the one real-faster-whisper test too (downloads/uses the local `small` model).
"""
import json
import os
import pathlib
import sqlite3
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import imageio_ffmpeg  # noqa: E402

import db  # noqa: E402
from engine import scenes  # noqa: E402
from engine import local_pipeline as lp  # noqa: E402
from engine import align as align_mod  # noqa: E402
from engine import watchdog  # noqa: E402

FF = imageio_ffmpeg.get_ffmpeg_exe()


# --- fixtures --------------------------------------------------------------------------

@pytest.fixture(scope='session')
def synthetic_video(tmp_path_factory):
    """12s video: 4s black, 4s gray, 4s white, silent mono audio track. Two hard cuts
    at t=4 and t=8."""
    out = tmp_path_factory.mktemp('media') / 'synthetic.mp4'
    cmd = [
        FF, '-y', '-loglevel', 'error',
        '-f', 'lavfi', '-i', 'color=c=black:size=320x240:duration=4:rate=25',
        '-f', 'lavfi', '-i', 'color=c=gray:size=320x240:duration=4:rate=25',
        '-f', 'lavfi', '-i', 'color=c=white:size=320x240:duration=4:rate=25',
        '-f', 'lavfi', '-i', 'anullsrc=r=16000:cl=mono',
        '-filter_complex', '[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]',
        '-map', '[v]', '-map', '3:a', '-shortest',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(out),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    assert out.exists() and out.stat().st_size > 0
    return out


@pytest.fixture()
def con(tmp_path):
    c = sqlite3.connect(str(tmp_path / 'radar.db'))
    c.row_factory = sqlite3.Row
    c.executescript(db.SCHEMA)
    lp._ensure_tables(c)
    yield c
    c.close()


@pytest.fixture()
def fake_data_dir(tmp_path, monkeypatch):
    d = tmp_path / 'data'
    monkeypatch.setattr(lp, 'DATA_DIR', d)
    return d


def _fake_segments():
    return [
        {'s': 0.5, 'e': 2.0, 't': 'hello from the hook'},
        {'s': 4.5, 'e': 6.0, 't': 'now the body of the video'},
        {'s': 9.5, 'e': 11.5, 't': 'and this is the closing line'},
    ]


def _fake_transcribe(mp4, model_size='small'):
    return list(_fake_segments()), {
        'model': model_size, 'asr_version': 'faster-whisper-small-int8-v1',
        'language': 'en', 'lang_probability': 0.99, 'processing_seconds': 0.01,
    }


# --- engine.scenes -----------------------------------------------------------------------

def test_detect_cuts_finds_the_two_hard_cuts(synthetic_video):
    cuts = scenes.detect_cuts(FF, synthetic_video, threshold=0.30)
    assert len(cuts) == 2
    assert abs(cuts[0] - 4.0) < 0.2
    assert abs(cuts[1] - 8.0) < 0.2


def test_scene_intervals_match_the_three_segments(synthetic_video):
    cuts = scenes.detect_cuts(FF, synthetic_video, threshold=0.30)
    intervals = scenes.scene_intervals(cuts, dur=12.0, min_len=0.4)
    assert len(intervals) == 3
    assert intervals[0][0] == 0.0
    assert intervals[-1][1] == 12.0
    for (s, e) in intervals:
        assert e > s


def test_scene_intervals_merges_short_intervals():
    # a spurious cut 0.1s after a real one should not produce a sub-0.4s scene
    intervals = scenes.scene_intervals([4.0, 4.1, 8.0], dur=12.0, min_len=0.4)
    assert all((e - s) >= 0.4 for s, e in intervals)


def test_scene_intervals_empty_duration_is_empty_list():
    assert scenes.scene_intervals([1.0, 2.0], dur=0, min_len=0.4) == []


def test_keyframe_times_covers_hook_and_scene_starts():
    intervals = [(0.0, 4.0), (4.0, 8.0), (8.0, 12.0)]
    times = scenes.keyframe_times(intervals)
    assert times == sorted(times)
    assert len(times) == len(set(times))
    # a keyframe near the start of every scene
    for s, _e in intervals:
        assert any(abs(t - (s + 0.2)) < 0.01 for t in times)
    # hook timestamps present since they're all < dur
    for h in (0.4, 1.2, 2.4, 4.0):
        assert any(abs(t - h) < 0.01 for t in times)


def test_keyframe_times_adds_mid_frame_for_long_scenes():
    intervals = [(0.0, 20.0)]
    times = scenes.keyframe_times(intervals, mid_over=6.0)
    assert any(abs(t - 10.0) < 0.01 for t in times)


def test_extract_frames_and_sha256(tmp_path, synthetic_video):
    out_dir = tmp_path / 'frames'
    got = scenes.extract_frames(FF, synthetic_video, [0.5, 5.0, 9.0], out_dir, scale=320, start_idx=3)
    assert len(got) == 3
    idxs = [g[0] for g in got]
    assert idxs == [3, 4, 5]
    for idx, t, path in got:
        p = pathlib.Path(path)
        assert p.exists() and p.stat().st_size > 0
        sha = scenes.sha256_file(p)
        assert len(sha) == 64
        int(sha, 16)  # valid hex


def test_extract_frames_skips_a_bad_timestamp(tmp_path, synthetic_video):
    out_dir = tmp_path / 'frames2'
    # a timestamp far beyond the video's duration should fail cleanly, not raise
    got = scenes.extract_frames(FF, synthetic_video, [1.0, 999.0], out_dir, scale=320)
    codes_ok = [t for _, t, _ in got]
    assert 1.0 in codes_ok
    assert 999.0 not in codes_ok


def test_contact_sheet(tmp_path, synthetic_video):
    frames_dir = tmp_path / 'framesheet'
    scenes.extract_frames(FF, synthetic_video, [0.5, 4.5, 8.5], frames_dir, scale=320)
    sheet = tmp_path / 'sheet.jpg'
    result = scenes.contact_sheet(FF, frames_dir, sheet, cols=3)
    assert result == str(sheet)
    assert sheet.exists() and sheet.stat().st_size > 0


def test_contact_sheet_no_frames_returns_none(tmp_path):
    empty_dir = tmp_path / 'empty'
    empty_dir.mkdir()
    result = scenes.contact_sheet(FF, empty_dir, tmp_path / 'sheet2.jpg', cols=3)
    assert result is None


# --- engine.local_pipeline: process_video ------------------------------------------------

def test_process_video_writes_frames_scenes_deepdives_video_state(
        con, fake_data_dir, synthetic_video, monkeypatch):
    monkeypatch.setattr(lp, 'transcribe', _fake_transcribe)
    code = 'TESTCODE1'

    result = lp.process_video(con, code, str(synthetic_video), run_id=lp.start_run(con, 'manual'),
                               asr_version='faster-whisper-small-int8-v1', frames_version='scene-v1')

    assert result['errors'] == []
    assert result['status'] == 'DONE'
    assert result['skipped'] is False
    assert result['steps']['media']['sha256'] and len(result['steps']['media']['sha256']) == 64

    frame_rows = con.execute('SELECT * FROM frames WHERE code=?', (code,)).fetchall()
    assert len(frame_rows) > 0
    for r in frame_rows:
        assert pathlib.Path(r['path']).exists()

    scene_rows = con.execute('SELECT * FROM scenes WHERE code=? ORDER BY idx', (code,)).fetchall()
    assert len(scene_rows) == 3
    assert scene_rows[0]['boundary_reason'] == 'detector'
    assert scene_rows[0]['frames_version'] == 'scene-v1'

    dd = con.execute('SELECT * FROM deepdives WHERE code=?', (code,)).fetchone()
    assert dd is not None
    assert dd['cuts'] == 2
    assert dd['evidence_state'] == 'scene-v1'
    assert dd['sheet'] and pathlib.Path(dd['sheet']).exists()

    vs = con.execute('SELECT * FROM video_state WHERE code=?', (code,)).fetchone()
    assert vs is not None
    assert vs['transcript_state'] == 'DONE'
    assert vs['frames_state'] == 'DONE_SCENE'
    # analysis_ready (SPEC §2.2) additionally requires beats + frame_labels — the
    # transcript/frame *semantic* analyses, owned by a different module. This
    # pipeline only gets the corpus as far as transcript+frames, so corpus_tier
    # already reads ANALYSIS_READY while analysis_ready itself stays 0 until that
    # later analysis lands (verified against the real engine.state.compute_video_state
    # once engine/state.py existed alongside this module).
    assert vs['corpus_tier'] == 'ANALYSIS_READY'
    # media_sha256 in the returned result is the immediate, reliable signal (computed
    # right after download); once the video is deleted (default keep_video=False) and
    # the authoritative video_state gets recomputed from disk, the real
    # engine.state.compute_video_state legitimately reports EXPIRED (deepdive ran,
    # frames landed, but the mp4 itself is gone by design — SPEC §4.4).
    assert vs['media_state'] == 'EXPIRED'

    tm = con.execute('SELECT * FROM transcript_meta WHERE code=?', (code,)).fetchone()
    assert tm is not None
    assert tm['asr_version'] == 'faster-whisper-small-int8-v1'
    assert tm['words'] > 0

    # video deleted by default (keep_video=False)
    assert not (fake_data_dir / 'video' / f'{code}.mp4').exists()


def test_process_video_is_idempotent(con, fake_data_dir, synthetic_video, monkeypatch):
    monkeypatch.setattr(lp, 'transcribe', _fake_transcribe)
    code = 'TESTCODE2'
    r1 = lp.process_video(con, code, str(synthetic_video), run_id=lp.start_run(con, 'manual'),
                           asr_version='faster-whisper-small-int8-v1', frames_version='scene-v1')
    assert r1['skipped'] is False

    r2 = lp.process_video(con, code, str(synthetic_video), run_id=lp.start_run(con, 'manual'),
                           asr_version='faster-whisper-small-int8-v1', frames_version='scene-v1')
    assert r2['skipped'] is True


def test_process_video_force_reruns(con, fake_data_dir, synthetic_video, monkeypatch):
    monkeypatch.setattr(lp, 'transcribe', _fake_transcribe)
    code = 'TESTCODE3'
    r1 = lp.process_video(con, code, str(synthetic_video), run_id=lp.start_run(con, 'manual'),
                           asr_version='faster-whisper-small-int8-v1', frames_version='scene-v1')
    assert r1['skipped'] is False

    r2 = lp.process_video(con, code, str(synthetic_video), run_id=lp.start_run(con, 'manual'), force=True,
                           asr_version='faster-whisper-small-int8-v1', frames_version='scene-v1')
    assert r2['skipped'] is False
    assert r2['status'] == 'DONE'
    # idx continues past what the first run wrote, never restarts at 0
    idxs = [r['idx'] for r in con.execute('SELECT idx FROM frames WHERE code=? ORDER BY idx', (code,))]
    assert idxs == sorted(set(idxs))
    assert idxs[0] == 0  # first run started at 0...
    assert len(idxs) > len(set(scenes.keyframe_times(
        scenes.scene_intervals(scenes.detect_cuts(FF, synthetic_video), 12.0))))  # ...second run appended more


def test_process_video_media_download_failed_is_typed_error(con, fake_data_dir):
    result = lp.process_video(con, 'NOFILE', '/no/such/file.mp4', run_id=lp.start_run(con, 'manual'),
                               asr_version='faster-whisper-small-int8-v1', frames_version='scene-v1')
    assert result['status'] == 'FAILED'
    assert result['errors'][0]['code'] == 'MEDIA_DOWNLOAD_FAILED'
    vs = con.execute('SELECT media_state FROM video_state WHERE code=?', ('NOFILE',)).fetchone()
    # 'MISSING' is what this module records immediately; once engine.state.refresh_video_state
    # (a pure recompute from disk + deepdives) runs, a code that never got as far as a
    # deepdive row falls back to its default 'UNKNOWN' — both are correct, non-DOWNLOADED
    # signals for "we never got the media".
    assert vs['media_state'] in ('MISSING', 'UNKNOWN')


def test_process_video_media_too_small_is_typed_error(con, fake_data_dir, tmp_path):
    tiny = tmp_path / 'tiny.mp4'
    tiny.write_bytes(b'not a real video')
    result = lp.process_video(con, 'TINY1', str(tiny), run_id=lp.start_run(con, 'manual'),
                               asr_version='faster-whisper-small-int8-v1', frames_version='scene-v1')
    assert result['status'] == 'FAILED'
    assert result['errors'][0]['code'] == 'MEDIA_TOO_SMALL'


# --- engine.align --------------------------------------------------------------------------

def test_align_on_synthetic_data(con, fake_data_dir, synthetic_video, monkeypatch):
    monkeypatch.setattr(lp, 'transcribe', _fake_transcribe)
    code = 'TESTCODE4'
    lp.process_video(con, code, str(synthetic_video), run_id=lp.start_run(con, 'manual'),
                      asr_version='faster-whisper-small-int8-v1', frames_version='scene-v1')

    feats = align_mod.align(con, code)
    for key in ('semantic_boundary_cut_rate', 'visual_change_per_sentence', 'scene_changes_per_beat',
                'first_cut_s', 'hook_cut_count', 'cta_cut_count'):
        assert key in feats
    assert feats['first_cut_s'] is not None
    assert feats['hook_cut_count'] == 0  # cuts at ~4s/~8s, none inside the first 3s
    # last 15% of a 12s video is [10.2, 12] — neither the ~4s nor ~8s cut lands there
    assert feats['cta_cut_count'] == 0

    vs = con.execute('SELECT flags_json FROM video_state WHERE code=?', (code,)).fetchone()
    flags = json.loads(vs['flags_json'])
    assert 'alignment' in flags
    assert 'segment_scene_map' in flags['alignment']
    assert len(flags['alignment']['segment_scene_map']) == len(_fake_segments())


def test_align_not_possible_without_scenes(con):
    result = align_mod.align(con, 'NEVERSEEN')
    assert result['alignment_state'] == 'NOT_POSSIBLE'
    assert 'reason' in result
    vs = con.execute('SELECT alignment_state FROM video_state WHERE code=?', ('NEVERSEEN',)).fetchone()
    assert vs['alignment_state'] == 'NOT_POSSIBLE'


# --- engine.watchdog: selection logic (no processing, no network) --------------------------

def _write_fake_cache(cache_root, mapping):
    """mapping: {code: url or None}. Writes one clips*.json cache file."""
    d = cache_root / '2026-01-01'
    d.mkdir(parents=True, exist_ok=True)
    items = []
    for code, url in mapping.items():
        entry = {'code': code}
        if url:
            entry['video_versions'] = [{'url': url}]
        items.append(entry)
    (d / 'user_1_clips.json').write_text(json.dumps({'items': items}))


def _seed_video_state(con, code, analysis_ready, transcript_state='MISSING', frames_state='MISSING'):
    con.execute("""INSERT INTO video_state (code, analysis_ready, transcript_state, frames_state, updated_at)
                   VALUES (?,?,?,?,'2026-01-01T00:00:00Z')""",
                (code, analysis_ready, transcript_state, frames_state))
    con.commit()


def test_watchdog_selects_only_not_ready_codes_with_live_urls(con, tmp_path, monkeypatch):
    cache_root = tmp_path / 'cache'
    _seed_video_state(con, 'READY1', analysis_ready=1, transcript_state='DONE', frames_state='DONE_SCENE')
    _seed_video_state(con, 'PENDING1', analysis_ready=0)
    _seed_video_state(con, 'PENDING2', analysis_ready=0)
    _write_fake_cache(cache_root, {
        'READY1': 'https://example.com/ready1.mp4',
        'PENDING1': 'https://example.com/pending1.mp4',
        # PENDING2 deliberately has no URL in cache
    })
    monkeypatch.setattr(watchdog, 'links_alive', lambda url: True)

    selected, no_url = watchdog.select_codes(con, limit=10, codes=None, cache_root=cache_root)

    selected_codes = {c for c, _u in selected}
    assert selected_codes == {'PENDING1'}
    assert 'PENDING2' in no_url
    assert 'READY1' not in selected_codes and 'READY1' not in no_url


def test_watchdog_marks_expired_when_links_are_dead(con, tmp_path, monkeypatch):
    cache_root = tmp_path / 'cache'
    _seed_video_state(con, 'DEAD1', analysis_ready=0)
    _seed_video_state(con, 'DEAD2', analysis_ready=0)
    _write_fake_cache(cache_root, {
        'DEAD1': 'https://example.com/dead1.mp4',
        'DEAD2': 'https://example.com/dead2.mp4',
    })
    monkeypatch.setattr(watchdog, 'links_alive', lambda url: False)

    selected, no_url = watchdog.select_codes(con, limit=10, codes=None, cache_root=cache_root)

    assert selected == []
    assert set(no_url) == {'DEAD1', 'DEAD2'}


def test_watchdog_explicit_codes_bypasses_video_state_scan(con, tmp_path, monkeypatch):
    cache_root = tmp_path / 'cache'
    _write_fake_cache(cache_root, {'EXPLICIT1': 'https://example.com/explicit1.mp4'})
    monkeypatch.setattr(watchdog, 'links_alive', lambda url: True)

    selected, no_url = watchdog.select_codes(con, limit=10, codes=['EXPLICIT1'], cache_root=cache_root)

    assert [c for c, _u in selected] == ['EXPLICIT1']
    assert no_url == []


def test_watchdog_lock_prevents_duplicate_worker(tmp_path, monkeypatch):
    monkeypatch.setattr(watchdog, 'LOCK_PATH', tmp_path / 'watchdog.lock')
    got1, _ = watchdog._acquire_lock()
    assert got1 is True
    got2, holder = watchdog._acquire_lock()
    assert got2 is False
    assert holder['pid'] == os.getpid()
    watchdog._release_lock()
    got3, _ = watchdog._acquire_lock()
    assert got3 is True
    watchdog._release_lock()


# --- optional real-ASR test (slow, opt-in) --------------------------------------------------

@pytest.mark.slow
@pytest.mark.skipif(os.environ.get('M2_REAL_ASR') != '1',
                     reason='set M2_REAL_ASR=1 to run the real faster-whisper model')
def test_transcribe_real_asr_on_silent_video(synthetic_video):
    segments, meta = lp.transcribe(synthetic_video, model_size='small')
    assert isinstance(segments, list)  # silent video: likely empty, must not crash
    assert meta['asr_version'] == 'faster-whisper-small-int8-v1'
    assert meta['model'] == 'small'
    assert meta['processing_seconds'] >= 0
