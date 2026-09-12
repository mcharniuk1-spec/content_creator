"""Tests for engine/production.py and engine/storage.py (Phase 3 production layer).

Uses a synthetic 3-second vertical (270x480, 9:16) MP4 with a real sine-wave audio
track, generated with the same `imageio_ffmpeg` binary the pipeline itself uses — no
network, no HikerAPI, no Supabase/Cloudflare credentials, same fixture approach as
tests/test_local_pipeline.py's `synthetic_video`.

Every Supabase test either asserts `StorageNotConfigured` before any transport call
happens, or injects a fake `transport` — no test in this file ever performs a real
HTTP request.
"""
import hashlib
import json
import pathlib
import shutil
import sqlite3
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import imageio_ffmpeg  # noqa: E402

import db as legacy_db  # noqa: E402
from engine import schema as engine_schema  # noqa: E402
from engine import production  # noqa: E402
from engine import storage  # noqa: E402

FF = imageio_ffmpeg.get_ffmpeg_exe()

CARD_ID = 'C-TEST-01'


# --------------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------------- #

@pytest.fixture(scope='session')
def synthetic_take_video(tmp_path_factory):
    """3s vertical (270x480, 9:16) video with a real sine-wave audio track."""
    out = tmp_path_factory.mktemp('media') / 'take.mp4'
    cmd = [
        FF, '-y', '-loglevel', 'error',
        '-f', 'lavfi', '-i', 'color=c=black:size=270x480:duration=3:rate=25',
        '-f', 'lavfi', '-i', 'sine=frequency=440:duration=3',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', str(out),
    ]
    import subprocess
    subprocess.run(cmd, check=True, capture_output=True)
    assert out.exists() and out.stat().st_size > 0
    return out


@pytest.fixture()
def con(tmp_path):
    c = sqlite3.connect(str(tmp_path / 'radar.db'))
    c.row_factory = sqlite3.Row
    c.executescript(legacy_db.SCHEMA)
    engine_schema.migrate(c)
    yield c
    c.close()


@pytest.fixture()
def card():
    """A minimal, valid-shaped card with two storyboard scenes."""
    return {
        'card_id': CARD_ID,
        'script': {'total_s': 6.0},
        'storyboard': [
            {'scene_id': 'S00', 'idx': 0, 'start_s': 0.0, 'end_s': 3.0, 'layout': 'a_roll'},
            {'scene_id': 'S01', 'idx': 1, 'start_s': 3.0, 'end_s': 6.0, 'layout': 'a_roll'},
        ],
    }


@pytest.fixture()
def tmp_root(tmp_path, monkeypatch, card):
    """Points engine.production.ROOT at a scratch directory with cards/<id>.json
    already written, so ingest_takes/edl_with_takes never touch the real repo."""
    monkeypatch.setattr(production, 'ROOT', tmp_path)
    (tmp_path / 'cards').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'cards' / f'{CARD_ID}.json').write_text(json.dumps(card), encoding='utf-8')
    return tmp_path


def _valid_take(**overrides):
    take = {
        'card_id': CARD_ID, 'scene_id': 'S00', 'script_segment': 'hook', 'take': 1,
        'shot_type': 'A_ROLL_CLOSE_UP', 'roll': 'A',
        'duration_s': 3.0, 'fps': 25.0, 'width': 270, 'height': 480, 'orientation': 'portrait',
        'has_audio': True, 'audio_quality': 'clean', 'subject': 'Misha, presenter',
        'in_s': 0.0, 'out_s': 3.0, 'sync_notes': 'clap at 0.0s',
        'quality_status': 'OK', 'retake_of': None,
        'sha256': hashlib.sha256(b'x').hexdigest(), 'path': 'cards/takes/C-TEST-01/S00-take1.mp4',
    }
    take.update(overrides)
    return take


def _minimal_edl(fps=30, width=1080, height=1920):
    """A hand-built, contract.mjs-valid PREVIS EDL with two scenes — avoids depending
    on engine.storyboard_render/Pillow just to get a template PNG on disk; contract.mjs
    never checks that an asset's sha256 matches real file bytes, only its shape."""
    img_sha = hashlib.sha256(b'template-png-bytes').hexdigest()
    return {
        'schema': 'm2.remotion-edl.v1', 'card_id': CARD_ID, 'title': 'test card',
        'fps': fps, 'width': width, 'height': height, 'duration_frames': 6 * fps,
        'scenes': [
            {'scene_id': 'S00', 'from_frame': 0, 'duration_frames': 3 * fps, 'layout': 'a_roll',
             'layers': [{'kind': 'placeholder', 'panel': 'full'},
                        {'kind': 'image', 'asset_id': 'img-S00', 'panel': 'full'}]},
            {'scene_id': 'S01', 'from_frame': 3 * fps, 'duration_frames': 3 * fps, 'layout': 'a_roll',
             'layers': [{'kind': 'placeholder', 'panel': 'full'},
                        {'kind': 'image', 'asset_id': 'img-S01', 'panel': 'full'}]},
        ],
        'assets': [
            {'asset_id': 'img-S00', 'kind': 'image', 'path': 'cards/frames/C-TEST-01-S00.png',
             'sha256': img_sha, 'rights_approved': True, 'rights_receipt_id': 'internal-template'},
            {'asset_id': 'img-S01', 'kind': 'image', 'path': 'cards/frames/C-TEST-01-S01.png',
             'sha256': img_sha, 'rights_approved': True, 'rights_receipt_id': 'internal-template'},
        ],
        'captions': [{'from_frame': 0, 'duration_frames': 3 * fps, 'text': 'hook'},
                     {'from_frame': 3 * fps, 'duration_frames': 3 * fps, 'text': 'body'}],
        'audio_stems': [], 'pending_audio_assets': ['speech'],
        'speech_policy': 'REQUIRED_RECORDED_SPEECH', 'render_mode': 'PREVIS', 'review_state': 'DRAFT',
    }


# --------------------------------------------------------------------------------- #
# probe_media
# --------------------------------------------------------------------------------- #

def test_probe_media_reads_duration_fps_resolution_audio(synthetic_take_video):
    info = production.probe_media(synthetic_take_video)
    assert info['duration_s'] == pytest.approx(3.0, abs=0.2)
    assert info['width'] == 270
    assert info['height'] == 480
    assert info['has_audio'] is True
    assert info['fps'] is not None
    assert len(info['sha256']) == 64


def test_probe_media_missing_file_raises(tmp_path):
    with pytest.raises(production.PipelineError) as exc:
        production.probe_media(tmp_path / 'nope.mp4')
    assert exc.value.code == 'MEDIA_NOT_FOUND'


# --------------------------------------------------------------------------------- #
# validate_take
# --------------------------------------------------------------------------------- #

def test_validate_take_pass(card):
    take = _valid_take()
    assert production.validate_take(take, card) == []


def test_validate_take_missing_keys(card):
    errors = production.validate_take({'card_id': CARD_ID}, card)
    assert any('scene_id' in e for e in errors)
    assert any('path' in e for e in errors)


def test_validate_take_bad_enum_and_unknown_scene(card):
    take = _valid_take(roll='C', orientation='landscape', scene_id='S99')
    errors = production.validate_take(take, card)
    assert any('roll' in e for e in errors)
    assert any('orientation' in e and 'portrait' in e for e in errors)
    assert any('S99' in e for e in errors)


def test_validate_take_out_of_bounds_time(card):
    take = _valid_take(out_s=5.0, duration_s=3.0)
    errors = production.validate_take(take, card)
    assert any('exceeds probed duration_s' in e for e in errors)


def test_validate_take_out_before_in(card):
    take = _valid_take(in_s=2.0, out_s=1.0)
    errors = production.validate_take(take, card)
    assert any('must be greater than in_s' in e for e in errors)


def test_validate_take_allows_null_probe_fields(card):
    take = _valid_take(duration_s=None, fps=None, width=None, height=None, has_audio=None, sha256=None)
    assert production.validate_take(take, card) == []


# --------------------------------------------------------------------------------- #
# ingest_takes
# --------------------------------------------------------------------------------- #

def test_ingest_takes_no_sidecar_is_pending(con, tmp_root):
    summary = production.ingest_takes(con, CARD_ID)
    assert summary['state'] == 'PENDING'
    assert 'no takes sidecar' in summary['reason']


def test_ingest_takes_sidecar_but_no_media_is_pending(con, tmp_root):
    takes_dir = tmp_root / 'cards' / 'takes'
    takes_dir.mkdir(parents=True)
    sidecar = {'card_id': CARD_ID, 'takes': [_valid_take(path='cards/takes/C-TEST-01/missing.mp4')]}
    (takes_dir / f'{CARD_ID}.json').write_text(json.dumps(sidecar), encoding='utf-8')

    summary = production.ingest_takes(con, CARD_ID)

    assert summary['state'] == 'PENDING'
    assert 'no MP4 files exist on disk' in summary['reason']
    validated = json.loads((takes_dir / f'{CARD_ID}.validated.json').read_text())
    assert validated['summary']['with_media'] == 0
    assert validated['takes'][0]['_media_present'] is False


def test_ingest_takes_missing_card_is_failed(con, tmp_path, monkeypatch):
    monkeypatch.setattr(production, 'ROOT', tmp_path)
    summary = production.ingest_takes(con, 'C-NOPE')
    assert summary['state'] == 'FAILED'
    assert 'card not found' in summary['reason']


def test_ingest_takes_happy_path_probes_and_validates(con, tmp_root, synthetic_take_video):
    takes_dir = tmp_root / 'cards' / 'takes' / CARD_ID
    takes_dir.mkdir(parents=True)
    take_path = takes_dir / 'S00-take1.mp4'
    shutil.copy2(synthetic_take_video, take_path)
    rel_path = str(take_path.relative_to(tmp_root))

    sidecar = {
        'card_id': CARD_ID,
        'takes': [_valid_take(path=rel_path, duration_s=None, fps=None, width=None,
                               height=None, has_audio=None, sha256=None)],
    }
    (tmp_root / 'cards' / 'takes' / f'{CARD_ID}.json').write_text(json.dumps(sidecar), encoding='utf-8')

    summary = production.ingest_takes(con, CARD_ID)

    assert summary['state'] == 'DONE'
    assert summary['takes']['with_media'] == 1
    assert summary['takes']['with_errors'] == 0

    validated = json.loads((tmp_root / 'cards' / 'takes' / f'{CARD_ID}.validated.json').read_text())
    enriched = validated['takes'][0]
    assert enriched['_media_present'] is True
    assert enriched['duration_s'] == pytest.approx(3.0, abs=0.2)
    assert len(enriched['sha256']) == 64
    assert enriched['_errors'] == []

    # one jobs row was actually written at the canonical stage
    rows = con.execute(
        "SELECT stage, state FROM jobs WHERE entity_kind='card' AND entity_id=?", (CARD_ID,)).fetchall()
    assert any(r['stage'] == 'VIDEO_GENERATION_READY' and r['state'] == 'DONE' for r in rows)


# --------------------------------------------------------------------------------- #
# select_takes
# --------------------------------------------------------------------------------- #

def test_select_takes_prefers_ok_and_latest_take():
    validated = {'takes': [
        {'scene_id': 'S00', 'take': 1, 'quality_status': 'OK', '_errors': []},
        {'scene_id': 'S00', 'take': 2, 'quality_status': 'RETAKE', '_errors': []},
        {'scene_id': 'S00', 'take': 3, 'quality_status': 'OK', '_errors': []},
        {'scene_id': 'S01', 'take': 1, 'quality_status': 'PENDING', '_errors': []},
        {'scene_id': 'S02', 'take': 1, 'quality_status': 'OK', '_errors': ['bad take']},
    ]}
    selection = production.select_takes(validated)
    assert selection['S00']['take'] == 3            # OK + highest take number
    assert 'S01' not in selection                   # no OK take at all
    assert 'S02' not in selection                   # OK but carries validation errors


# --------------------------------------------------------------------------------- #
# edl_with_takes
# --------------------------------------------------------------------------------- #

def _node_available():
    return shutil.which('node') is not None


def test_edl_with_takes_binds_video_layer_and_keeps_contract_valid(tmp_root, synthetic_take_video):
    edl = _minimal_edl(fps=30)
    local_copy = tmp_root / 'cards' / 'takes' / 'S00-take1.mp4'
    local_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(synthetic_take_video, local_copy)
    take = production.probe_media(local_copy)
    take.update({'in_s': 0.0, 'path': str(local_copy)})

    result = production.edl_with_takes({'card_id': CARD_ID}, edl, {'S00': take})

    scene0 = next(s for s in result['edl']['scenes'] if s['scene_id'] == 'S00')
    kinds = [layer['kind'] for layer in scene0['layers']]
    assert 'video' in kinds
    video_layer = next(layer for layer in scene0['layers'] if layer['kind'] == 'video')
    assert video_layer['asset_id'] == 'video-S00'

    scene1 = next(s for s in result['edl']['scenes'] if s['scene_id'] == 'S01')
    assert any(layer['kind'] == 'placeholder' for layer in scene1['layers'])  # untouched

    video_asset = next(a for a in result['edl']['assets'] if a['asset_id'] == 'video-S00')
    assert video_asset['kind'] == 'video'
    assert video_asset['duration_frames'] >= scene0['duration_frames']

    out_path = tmp_root / 'cards' / 'edl' / f'{CARD_ID}.json'
    assert out_path.exists()

    if _node_available():
        assert result['node']['ok'] is True, result['node']
    else:
        assert result['node']['skipped'] is True


def test_edl_with_takes_rejects_unprobed_take(tmp_root):
    edl = _minimal_edl(fps=30)
    unprobed = {'duration_s': None, 'sha256': None, 'path': 'x.mp4', 'in_s': 0.0}
    with pytest.raises(ValueError, match='has not been probed'):
        production.edl_with_takes({'card_id': CARD_ID}, edl, {'S00': unprobed})


def test_edl_with_takes_rejects_take_too_short(tmp_root, synthetic_take_video):
    edl = _minimal_edl(fps=30)
    take = production.probe_media(synthetic_take_video)   # ~3s = 90 frames @30fps
    take.update({'in_s': 2.5, 'path': str(synthetic_take_video)})  # only ~0.5s left, scene needs 3s
    with pytest.raises(ValueError, match='too short'):
        production.edl_with_takes({'card_id': CARD_ID}, edl, {'S00': take})


# --------------------------------------------------------------------------------- #
# render_plan
# --------------------------------------------------------------------------------- #

def test_render_plan_not_configured_without_edl(tmp_root):
    result = production.render_plan(CARD_ID)
    assert result['state'] == 'NOT_CONFIGURED'
    assert 'no EDL' in result['reason']


def test_render_plan_not_configured_without_node_modules(tmp_root, monkeypatch):
    (tmp_root / 'cards' / 'edl').mkdir(parents=True)
    (tmp_root / 'cards' / 'edl' / f'{CARD_ID}.json').write_text('{}', encoding='utf-8')
    # studio/remotion/node_modules genuinely doesn't exist in this checkout (see
    # module docstring / PRODUCTION_PIPELINE.md); no monkeypatching needed to assert it.
    result = production.render_plan(CARD_ID)
    assert result['state'] == 'NOT_CONFIGURED'
    assert 'install_command' in result
    assert not result.get('command') is None  # command is still built for visibility


# --------------------------------------------------------------------------------- #
# storage.py — LocalStorage / record_render
# --------------------------------------------------------------------------------- #

def test_local_storage_put_and_get_url(tmp_path):
    local = storage.LocalStorage(root=tmp_path)
    src = tmp_path / 'src.mp4'
    src.write_bytes(b'fake video bytes')

    key = local.put(src, 'C-TEST-01/v1.mp4')

    assert key == 'C-TEST-01/v1.mp4'
    dest = tmp_path / 'objects' / 'C-TEST-01' / 'v1.mp4'
    assert dest.exists() and dest.read_bytes() == b'fake video bytes'
    url = local.get_url('C-TEST-01/v1.mp4')
    assert url.startswith('file://')


def _render_record(**overrides):
    record = {
        'run_id': '2026-09-12_0000-abcdef', 'card_id': CARD_ID, 'script_version': 1,
        'storyboard_version': 1, 'render_version': 1, 'source_take_ids': ['S00#1'],
        'final_object_key': f'{CARD_ID}/v1.mp4', 'thumbnail_key': None, 'duration_s': 6.0,
        'render_metadata': {'fps': 30, 'width': 1080, 'height': 1920, 'codec': 'h264',
                             'remotion_version': '4.0.520',
                             'edl_sha256': hashlib.sha256(b'edl').hexdigest()},
        'qa_status': 'PENDING', 'storage_provider': 'local', 'created_at': '2026-09-12T00:00:00Z',
    }
    record.update(overrides)
    return record


def test_record_render_writes_json_and_sql_row(con, tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'RENDERS_DIR', tmp_path / 'renders')
    record = _render_record()

    out_path = storage.record_render(con, record)

    assert out_path.exists()
    on_disk = json.loads(out_path.read_text())
    assert on_disk == record

    row = con.execute(
        'SELECT * FROM render_records WHERE run_id=? AND card_id=?',
        (record['run_id'], record['card_id'])).fetchone()
    assert row is not None
    assert row['qa_status'] == 'PENDING'
    assert json.loads(row['source_take_ids_json']) == ['S00#1']


def test_record_render_rejects_malformed_record(con, tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'RENDERS_DIR', tmp_path / 'renders')
    bad = _render_record()
    del bad['duration_s']
    with pytest.raises(ValueError, match='duration_s'):
        storage.record_render(con, bad)


# --------------------------------------------------------------------------------- #
# storage.py — SupabaseStorage
# --------------------------------------------------------------------------------- #

def test_supabase_raises_not_configured_without_env():
    sb = storage.SupabaseStorage(env={})
    with pytest.raises(storage.StorageNotConfigured, match='SUPABASE_URL'):
        sb.put('irrelevant', 'key.mp4')
    with pytest.raises(storage.StorageNotConfigured):
        sb.get_url('key.mp4')
    state, detail = sb.status()
    assert state == 'NOT_CONFIGURED'


def test_supabase_happy_path_with_fake_transport(tmp_path):
    calls = []

    def fake_transport(url, service_key, data):
        calls.append((url, service_key, data))
        return 200, 'ok'

    sb = storage.SupabaseStorage(
        env={'SUPABASE_URL': 'https://proj.supabase.co', 'SUPABASE_SERVICE_KEY': 'secret-key'},
        transport=fake_transport)

    src = tmp_path / 'render.mp4'
    src.write_bytes(b'rendered bytes')
    object_key = sb.put(src, f'{CARD_ID}/v1.mp4')

    assert object_key == f'm2-renders/{CARD_ID}/v1.mp4'
    assert len(calls) == 1
    url, service_key, data = calls[0]
    assert url == f'https://proj.supabase.co/storage/v1/object/m2-renders/{CARD_ID}/v1.mp4'
    assert service_key == 'secret-key'
    assert data == b'rendered bytes'

    public_url = sb.get_url(f'{CARD_ID}/v1.mp4')
    assert public_url == f'https://proj.supabase.co/storage/v1/object/public/m2-renders/{CARD_ID}/v1.mp4'

    state, _ = sb.status()
    assert state == 'CONFIGURED'


def test_supabase_transport_error_raises(tmp_path):
    def failing_transport(url, service_key, data):
        return 403, 'forbidden'

    sb = storage.SupabaseStorage(
        env={'SUPABASE_URL': 'https://proj.supabase.co', 'SUPABASE_SERVICE_KEY': 'k'},
        transport=failing_transport)
    src = tmp_path / 'render.mp4'
    src.write_bytes(b'x')
    with pytest.raises(RuntimeError, match='403'):
        sb.put(src, 'x.mp4')


# --------------------------------------------------------------------------------- #
# storage.py — CloudflareDelivery stub
# --------------------------------------------------------------------------------- #

def test_cloudflare_stub_not_configured_by_default():
    cf = storage.CloudflareDelivery(env={})
    state, detail = cf.status()
    assert state == 'NOT_CONFIGURED'
    with pytest.raises(storage.StorageNotConfigured):
        cf.public_url('x.mp4')


def test_cloudflare_stub_builds_url_when_configured():
    cf = storage.CloudflareDelivery(env={'CF_PUBLIC_BASE_URL': 'https://cdn.example.com'})
    state, _ = cf.status()
    assert state == 'CONFIGURED'
    assert cf.public_url('C-TEST-01/v1.mp4') == 'https://cdn.example.com/C-TEST-01/v1.mp4'
