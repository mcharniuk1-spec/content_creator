#!/usr/bin/env python3
"""Phase 3 production layer: supplied MP4 takes -> validated sidecar -> EDL with real
footage -> Remotion render plan (engine/SPEC.md Phase 3; M2Radar_Content_Engine_Full_
Execution_Prompt_v4.md §82, §92, §96 Phase 3). Owner: production (engine/production.py,
engine/storage.py, tests/test_production.py, docs/M2RADAR_CONTENT_ENGINE_ARCHITECTURE.md,
docs/PRODUCTION_PIPELINE.md, schemas/supplied-take.schema.json, schemas/render-record.schema.json).

Pipeline this module implements, one function per step:

    probe_media(path)                     ffprobe/ffmpeg -> duration/fps/resolution/audio
    validate_take(take, card)             schema-lite checks, no jsonschema dependency
    ingest_takes(con, card_id)             read cards/takes/<card_id>.json, probe + validate
                                           every take, write <card_id>.validated.json,
                                           record one `jobs` row (engine.state.job)
    select_takes(validated)                per scene_id: prefer quality_status=OK, latest take
    edl_with_takes(card, edl, selection)   replace `placeholder` layers with real `video`
                                           layers, keep the EDL valid for contract.mjs
    render_plan(card_id)                   the exact `node studio/remotion/render.mjs …`
                                           command; never runs it unless --execute AND
                                           Remotion's node_modules are actually installed

Nothing here calls a paid API or the network. Nothing here claims a render, a probe or a
validation succeeded when it did not — a missing MP4, a missing Chrome binary or a missing
`node_modules` always comes back as an explicit state (`PENDING`/`NOT_CONFIGURED`/`FAILED`),
never a silent skip and never a fabricated success.

    python3 -m engine.production takes <card_id>
    python3 -m engine.production plan <card_id> [--execute]
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:                       # `python3 -m engine.production` from any cwd
    sys.path.insert(0, str(ROOT))

import imageio_ffmpeg  # noqa: E402

from engine.db_util import canonical_json, loads, now  # noqa: E402
from engine import edl as edl_mod  # noqa: E402

# engine.state is another owner's module (schema-owner, SPEC §9); it exists in this
# checkout, but the same defensive import pattern local_pipeline.py uses keeps this
# module importable/testable even against a stripped-down DB that hasn't run schema
# migration yet.
try:
    from engine.state import job as _real_job, start_run as _real_start_run
    _HAVE_ENGINE_STATE = True
except ImportError:                                  # pragma: no cover - defensive only
    _HAVE_ENGINE_STATE = False
    _real_job = _real_start_run = None

import contextlib
import uuid
import datetime as _dt


def start_run(con, kind='cards'):
    """engine.state.start_run(con, kind) when available; otherwise a local run id with
    no persisted `runs` row (same fallback shape as engine/local_pipeline.py)."""
    if _HAVE_ENGINE_STATE:
        try:
            return _real_start_run(con, kind)
        except Exception as e:                        # pragma: no cover - defensive only
            print(f'engine.state.start_run failed ({e}); using a local run id', file=sys.stderr)
    return f"{_dt.datetime.utcnow():%Y-%m-%d_%H%M}-{uuid.uuid4().hex[:6]}"


@contextlib.contextmanager
def job(con, run_id, entity_kind, entity_id, stage, **meta):
    """engine.state.job(con, ...) when available; otherwise a no-op context manager
    that still propagates exceptions."""
    if _HAVE_ENGINE_STATE:
        with _real_job(con, run_id, entity_kind, entity_id, stage, **meta) as handle:
            yield handle
    else:                                              # pragma: no cover - defensive only
        class _Fallback:
            def set(self, **kw):
                return self

            def skip(self, reason=None):
                return self

            def retry_required(self, reason=None):
                return self
        yield _Fallback()


# --------------------------------------------------------------------------------- #
# 1. probe_media — duration/fps/resolution/audio from the file itself
# --------------------------------------------------------------------------------- #

class PipelineError(Exception):
    """Typed failure. `.code` is one of MEDIA_NOT_FOUND, PROBE_FAILED, PROBE_UNAVAILABLE."""

    def __init__(self, code, message=''):
        super().__init__(f'{code}: {message}')
        self.code = code
        self.message = message


def _find_ffprobe():
    """ffprobe next to imageio_ffmpeg's bundled ffmpeg binary (some platforms ship
    both), else ffprobe on PATH. Returns None if neither exists — imageio_ffmpeg only
    guarantees ffmpeg, so this is normal, not an error."""
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    candidate = ffmpeg_exe.replace('ffmpeg', 'ffprobe')
    if candidate != ffmpeg_exe and pathlib.Path(candidate).exists():
        return candidate
    return shutil.which('ffprobe')


def _sha256_file(path, chunk=1 << 20):
    import hashlib
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(chunk), b''):
            h.update(block)
    return h.hexdigest()


def _parse_r_frame_rate(value):
    if not value:
        return None
    if '/' in value:
        num, _, den = value.partition('/')
        try:
            num, den = float(num), float(den)
            return round(num / den, 3) if den else None
        except ValueError:
            return None
    try:
        return round(float(value), 3)
    except ValueError:
        return None


def _probe_with_ffprobe(ffprobe, path):
    proc = subprocess.run(
        [ffprobe, '-v', 'error', '-print_format', 'json', '-show_format', '-show_streams', str(path)],
        capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise PipelineError('PROBE_FAILED', proc.stderr.strip() or 'ffprobe exited non-zero')
    data = json.loads(proc.stdout)
    streams = data.get('streams', [])
    video = next((s for s in streams if s.get('codec_type') == 'video'), None)
    audio = next((s for s in streams if s.get('codec_type') == 'audio'), None)
    fmt = data.get('format', {})

    duration = None
    for src in (fmt.get('duration'), video.get('duration') if video else None):
        if src is not None:
            try:
                duration = round(float(src), 3)
                break
            except (TypeError, ValueError):
                continue

    width = int(video['width']) if video and video.get('width') else None
    height = int(video['height']) if video and video.get('height') else None
    fps = _parse_r_frame_rate(video.get('r_frame_rate')) if video else None
    if fps is None and video:
        fps = _parse_r_frame_rate(video.get('avg_frame_rate'))

    return {
        'duration_s': duration, 'fps': fps, 'width': width, 'height': height,
        'has_audio': audio is not None,
        'codec': (video.get('codec_name') if video else None),
    }


_DURATION_RE = re.compile(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)')
_VIDEO_RE = re.compile(
    r'Stream #\d+:\d+.*?Video:.*?(?P<w>\d{2,5})x(?P<h>\d{2,5})[^,]*(?:,.*?(?P<fps>[\d.]+)\s*fps)?')
_AUDIO_RE = re.compile(r'Stream #\d+:\d+.*?Audio:')
_CODEC_RE = re.compile(r'Video:\s*([a-zA-Z0-9_]+)')


def _probe_with_ffmpeg_stderr(ffmpeg_exe, path):
    """Fallback when ffprobe is not available anywhere: `ffmpeg -i <path>` always
    exits non-zero with no output file, but always prints stream info to stderr."""
    proc = subprocess.run([ffmpeg_exe, '-i', str(path)], capture_output=True, text=True, timeout=30)
    text = proc.stderr or ''

    duration = None
    m = _DURATION_RE.search(text)
    if m:
        h, mnt, s = m.groups()
        duration = round(int(h) * 3600 + int(mnt) * 60 + float(s), 3)

    width = height = fps = codec = None
    m = _VIDEO_RE.search(text)
    if m:
        width, height = int(m.group('w')), int(m.group('h'))
        if m.group('fps'):
            fps = round(float(m.group('fps')), 3)
    m = _CODEC_RE.search(text)
    if m:
        codec = m.group(1)

    has_audio = bool(_AUDIO_RE.search(text))

    if width is None and duration is None:
        raise PipelineError('PROBE_FAILED', 'could not find Duration/Video stream in ffmpeg -i output')

    return {'duration_s': duration, 'fps': fps, 'width': width, 'height': height,
            'has_audio': has_audio, 'codec': codec}


def probe_media(path) -> dict:
    """Probe an MP4 for duration/fps/width/height/audio-presence/codec and its sha256.

    Uses ffprobe (bundled next to imageio_ffmpeg's ffmpeg binary, or found on PATH)
    for exact JSON output when available; otherwise falls back to parsing
    `ffmpeg -i <path>`'s stderr (same fields, lower precision — e.g. fps may be
    missing for some encodes). Pure stdlib + imageio_ffmpeg, no network, no paid call.

    Raises PipelineError('MEDIA_NOT_FOUND', ...) if `path` does not exist, or
    PipelineError('PROBE_FAILED', ...) if neither method could read it.
    """
    p = pathlib.Path(path)
    if not p.exists() or p.stat().st_size == 0:
        raise PipelineError('MEDIA_NOT_FOUND', str(p))

    ffprobe = _find_ffprobe()
    if ffprobe:
        info = _probe_with_ffprobe(ffprobe, p)
    else:
        info = _probe_with_ffmpeg_stderr(imageio_ffmpeg.get_ffmpeg_exe(), p)
    info['sha256'] = _sha256_file(p)
    info['path'] = str(p)
    return info


# --------------------------------------------------------------------------------- #
# 2. validate_take — schema-lite validation, no jsonschema dependency
# --------------------------------------------------------------------------------- #

REQUIRED_TAKE_KEYS = [
    'card_id', 'scene_id', 'script_segment', 'take', 'shot_type', 'roll',
    'duration_s', 'fps', 'width', 'height', 'orientation', 'has_audio', 'audio_quality',
    'subject', 'in_s', 'out_s', 'sync_notes', 'quality_status', 'retake_of', 'sha256', 'path',
]
# fields engine.production.probe_media derives; legitimately null before a real
# file has been measured (schemas/supplied-take.schema.json)
_NULLABLE_UNTIL_PROBED = {'duration_s', 'fps', 'width', 'height', 'has_audio', 'sha256'}
_ROLL_VALUES = ('A', 'B')
_ORIENTATION_VALUES = ('portrait', 'landscape', 'square')
_AUDIO_QUALITY_VALUES = ('clean', 'noisy', 'none', 'unknown')
_QUALITY_STATUS_VALUES = ('PENDING', 'OK', 'RETAKE')
_DURATION_TOLERANCE_S = 0.05


def validate_take(take: dict, card: dict) -> list[str]:
    """Schema-lite validation of one supplied-take dict against
    schemas/supplied-take.schema.json's shape and the approved card's storyboard.
    Returns a flat list of error strings (empty = valid) — no jsonschema dependency,
    just required-key/type/enum checks plus the two checks a generic schema can't do:
    `scene_id` must exist in `card['storyboard']`, and `in_s`/`out_s` must fall inside
    a probed `duration_s` once one is known.
    """
    errors: list[str] = []

    if not isinstance(take, dict):
        return [f'take must be an object, got {type(take).__name__}']

    for key in REQUIRED_TAKE_KEYS:
        if key not in take:
            errors.append(f"missing required key '{key}'")
    if errors:
        return errors  # nothing else is safe to check without the keys present

    def _err(msg):
        errors.append(msg)

    if not isinstance(take['card_id'], str) or not take['card_id']:
        _err('card_id must be a non-empty string')
    if not isinstance(take['scene_id'], str) or not take['scene_id']:
        _err('scene_id must be a non-empty string')
    if not isinstance(take['script_segment'], str) or not take['script_segment']:
        _err('script_segment must be a non-empty string')
    if not isinstance(take['take'], int) or isinstance(take['take'], bool) or take['take'] < 1:
        _err('take must be an integer >= 1')
    if not isinstance(take['shot_type'], str) or not take['shot_type']:
        _err('shot_type must be a non-empty string')
    if take['roll'] not in _ROLL_VALUES:
        _err(f"roll must be one of {_ROLL_VALUES}, got {take['roll']!r}")
    if take['orientation'] not in _ORIENTATION_VALUES:
        _err(f"orientation must be one of {_ORIENTATION_VALUES}, got {take['orientation']!r}")
    elif take['orientation'] != 'portrait':
        _err(f"orientation must be 'portrait' for a reel take, got {take['orientation']!r}")
    if take['audio_quality'] not in _AUDIO_QUALITY_VALUES:
        _err(f"audio_quality must be one of {_AUDIO_QUALITY_VALUES}, got {take['audio_quality']!r}")
    if not isinstance(take['subject'], str):
        _err('subject must be a string')
    if not isinstance(take['sync_notes'], str):
        _err('sync_notes must be a string')
    if take['quality_status'] not in _QUALITY_STATUS_VALUES:
        _err(f"quality_status must be one of {_QUALITY_STATUS_VALUES}, got {take['quality_status']!r}")

    for key in ('duration_s', 'fps'):
        v = take[key]
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0):
            _err(f'{key} must be a positive number or null, got {v!r}')
    for key in ('width', 'height'):
        v = take[key]
        if v is not None and (isinstance(v, bool) or not isinstance(v, int) or v <= 0):
            _err(f'{key} must be a positive integer or null, got {v!r}')
    if take['has_audio'] is not None and not isinstance(take['has_audio'], bool):
        _err('has_audio must be a boolean or null')
    if take['sha256'] is not None and (
            not isinstance(take['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', take['sha256'])):
        _err('sha256 must be a 64-char lowercase hex string or null')
    if take['retake_of'] is not None and (
            isinstance(take['retake_of'], bool) or not isinstance(take['retake_of'], int) or take['retake_of'] < 1):
        _err('retake_of must be an integer >= 1 or null')

    in_s, out_s = take['in_s'], take['out_s']
    if not isinstance(in_s, (int, float)) or isinstance(in_s, bool) or in_s < 0:
        _err('in_s must be a number >= 0')
        in_s = None
    if not isinstance(out_s, (int, float)) or isinstance(out_s, bool) or out_s <= 0:
        _err('out_s must be a number > 0')
        out_s = None
    if in_s is not None and out_s is not None and out_s <= in_s:
        _err(f'out_s ({out_s}) must be greater than in_s ({in_s})')
    duration_s = take['duration_s']
    if duration_s is not None and out_s is not None and out_s > duration_s + _DURATION_TOLERANCE_S:
        _err(f'out_s ({out_s}) exceeds probed duration_s ({duration_s})')

    if not isinstance(take['path'], str) or not take['path']:
        _err('path must be a non-empty string')

    scene_ids = {s.get('scene_id') for s in (card or {}).get('storyboard', [])}
    if take['scene_id'] not in scene_ids:
        _err(f"scene_id {take['scene_id']!r} not found in card {card.get('card_id', '?')!r}'s storyboard")

    return errors


# --------------------------------------------------------------------------------- #
# 3. ingest_takes — read the sidecar, probe every MP4, validate, write <card>.validated.json
# --------------------------------------------------------------------------------- #

def _card_path(card_id):
    return ROOT / 'cards' / f'{card_id}.json'


def _takes_sidecar_path(card_id, takes_dir):
    return (ROOT / takes_dir / f'{card_id}.json') if not pathlib.Path(takes_dir).is_absolute() \
        else pathlib.Path(takes_dir) / f'{card_id}.json'


def _validated_path(card_id, takes_dir):
    base = _takes_sidecar_path(card_id, takes_dir)
    return base.with_name(f'{card_id}.validated.json')


def _resolve_take_media_path(take_path):
    p = pathlib.Path(take_path)
    return p if p.is_absolute() else ROOT / p


def ingest_takes(con, card_id, takes_dir='cards/takes') -> dict:
    """Read `cards/takes/<card_id>.json`, probe every take whose MP4 exists on disk,
    validate every take against the approved card's storyboard, and write
    `cards/takes/<card_id>.validated.json`. Always records one `jobs` row at stage
    `VIDEO_GENERATION_READY` (engine.state.job).

    Never claims success it did not observe:
    - no `cards/<card_id>.json`                    -> state FAILED, job SKIPPED
    - no `cards/takes/<card_id>.json` sidecar       -> state PENDING, job SKIPPED
    - sidecar exists but zero takes have a real file on disk
                                                     -> state PENDING, job SKIPPED
    - at least one take has a real file on disk     -> state DONE, job DONE
      (individual takes still missing media are reported per-take, not hidden)
    """
    run_id = start_run(con, 'cards')
    card_path = _card_path(card_id)
    sidecar_path = _takes_sidecar_path(card_id, takes_dir)
    validated_path = _validated_path(card_id, takes_dir)

    with job(con, run_id, 'card', card_id, 'VIDEO_GENERATION_READY', provider='local') as j:
        base = {'card_id': card_id, 'run_id': run_id, 'sidecar_path': str(sidecar_path),
                'validated_path': str(validated_path)}

        if not card_path.exists():
            reason = f'card not found: {card_path}'
            j.skip(reason=reason)
            return {**base, 'state': 'FAILED', 'reason': reason, 'takes': []}

        card = json.loads(card_path.read_text(encoding='utf-8'))

        if not sidecar_path.exists():
            reason = (f'no takes sidecar at {sidecar_path}; drop MP4s under cards/takes/{card_id}/ '
                       f'and a matching cards/takes/{card_id}.json (see docs/PRODUCTION_PIPELINE.md), '
                       f'then re-run')
            j.skip(reason=reason)
            return {**base, 'state': 'PENDING', 'reason': reason, 'takes': []}

        sidecar = json.loads(sidecar_path.read_text(encoding='utf-8'))
        takes = sidecar.get('takes', [])

        enriched = []
        any_media = False
        for take in takes:
            take = dict(take)
            media_path = _resolve_take_media_path(take.get('path', ''))
            media_present = media_path.exists() and media_path.stat().st_size > 0
            probe_error = None
            if media_present:
                try:
                    info = probe_media(media_path)
                    take['duration_s'] = info['duration_s']
                    take['fps'] = info['fps']
                    take['width'] = info['width']
                    take['height'] = info['height']
                    take['has_audio'] = info['has_audio']
                    take['sha256'] = info['sha256']
                    any_media = True
                except PipelineError as exc:
                    probe_error = f'{exc.code}: {exc.message}'
            for key in _NULLABLE_UNTIL_PROBED:
                take.setdefault(key, None)
            errors = validate_take(take, card)
            if not media_present:
                errors.append(f'media not found on disk at {media_path}')
            elif probe_error:
                errors.append(probe_error)
            enriched.append({**take, '_media_present': media_present, '_errors': errors})

        summary_takes = {
            'total': len(enriched),
            'with_media': sum(1 for t in enriched if t['_media_present']),
            'missing_media': sum(1 for t in enriched if not t['_media_present']),
            'with_errors': sum(1 for t in enriched if t['_errors']),
        }

        validated_doc = {
            'schema': 'm2radar.takes.validated.v1', 'card_id': card_id, 'run_id': run_id,
            'validated_at': now(), 'takes': enriched, 'summary': summary_takes,
        }

        if not any_media:
            reason = (f'sidecar found ({len(enriched)} take(s) declared) but no MP4 files exist on '
                       f'disk yet for card {card_id}; nothing was probed or validated against media')
            j.skip(reason=reason)
            validated_path.parent.mkdir(parents=True, exist_ok=True)
            validated_path.write_text(
                json.dumps(validated_doc, indent=2, ensure_ascii=False, sort_keys=True) + '\n',
                encoding='utf-8')
            return {**base, 'state': 'PENDING', 'reason': reason, 'takes': summary_takes}

        validated_path.parent.mkdir(parents=True, exist_ok=True)
        validated_path.write_text(
            json.dumps(validated_doc, indent=2, ensure_ascii=False, sort_keys=True) + '\n',
            encoding='utf-8')
        j.set(output_refs_json={'validated_path': str(validated_path)})
        return {**base, 'state': 'DONE', 'reason': None, 'takes': summary_takes}


# --------------------------------------------------------------------------------- #
# 4. select_takes — one usable take per scene, preferring quality OK / latest take
# --------------------------------------------------------------------------------- #

def select_takes(validated) -> dict:
    """Pick the best usable take per scene_id: `quality_status == 'OK'`, no
    validation errors, highest `take` number wins ties. A scene with no qualifying
    take is simply absent from the result — the caller (edl_with_takes) leaves that
    scene's EDL layer as the existing placeholder rather than guessing.

    `validated` may be the dict `ingest_takes`/the `.validated.json` file produces
    (reads its `takes` key) or a bare list of take dicts.
    """
    takes = validated.get('takes', []) if isinstance(validated, dict) else list(validated)

    best: dict[str, dict] = {}
    for take in takes:
        if take.get('quality_status') != 'OK':
            continue
        if take.get('_errors'):
            continue
        scene_id = take.get('scene_id')
        if scene_id is None:
            continue
        current = best.get(scene_id)
        if current is None or (take.get('take') or 0) > (current.get('take') or 0):
            best[scene_id] = take
    return best


# --------------------------------------------------------------------------------- #
# 5. edl_with_takes — bind real footage into an existing EDL, keep contract.mjs happy
# --------------------------------------------------------------------------------- #

def _relpath(path_str):
    p = pathlib.Path(path_str)
    if p.is_absolute():
        try:
            return str(p.relative_to(ROOT))
        except ValueError:
            raise ValueError(f'{p} is outside the repository root {ROOT}')
    return str(p)


def edl_with_takes(card: dict, edl: dict, selection: dict, *, validate_node: bool = True) -> dict:
    """Replace the `placeholder` layer of every scene in `selection` with a real
    `video` layer bound to that take's probed MP4 (hash + duration_frames + trim),
    leaving every other scene's placeholder untouched. Writes the result back to
    `cards/edl/<card_id>.json` (same path engine.edl.card_to_edl uses) and, unless
    `validate_node=False`, re-validates it through contract.mjs the same way
    engine.edl.validate_with_node does (skipped, not failed, if node isn't found).

    Raises ValueError if a selected take has not been probed yet (duration_s/sha256
    still null) or is too short to cover its storyboard slot — never writes a
    silently-wrong EDL.
    """
    edl = copy.deepcopy(edl)
    fps = edl['fps']
    assets_by_id = {a['asset_id']: a for a in edl.get('assets', [])}

    for scene in edl.get('scenes', []):
        take = selection.get(scene.get('scene_id'))
        if not take:
            continue
        if take.get('duration_s') is None or take.get('sha256') is None:
            raise ValueError(
                f"take for scene {scene['scene_id']} has not been probed (duration_s/sha256 "
                f"still null) — run ingest_takes on real media first")

        asset_id = f"video-{scene['scene_id']}"
        duration_frames_asset = max(1, round(take['duration_s'] * fps))
        trim_before = max(0, round(float(take.get('in_s') or 0.0) * fps))
        if trim_before + scene['duration_frames'] > duration_frames_asset:
            raise ValueError(
                f"take for scene {scene['scene_id']} is too short for its storyboard slot: "
                f"trim {trim_before}f + scene {scene['duration_frames']}f > "
                f"asset {duration_frames_asset}f (take duration_s={take['duration_s']})")

        assets_by_id[asset_id] = {
            'asset_id': asset_id, 'kind': 'video', 'path': _relpath(take['path']),
            'sha256': take['sha256'], 'rights_approved': True,
            'rights_receipt_id': 'owner-footage', 'duration_frames': duration_frames_asset,
        }

        new_layers = []
        replaced = False
        for layer in scene.get('layers', []):
            if layer.get('kind') == 'placeholder' and not replaced:
                new_layers.append({'kind': 'video', 'asset_id': asset_id,
                                    'panel': layer.get('panel', 'full'),
                                    'trim_before_frames': trim_before})
                replaced = True
            else:
                new_layers.append(layer)
        if not replaced:
            new_layers.insert(0, {'kind': 'video', 'asset_id': asset_id, 'panel': 'full',
                                   'trim_before_frames': trim_before})
        scene['layers'] = new_layers

    edl['assets'] = list(assets_by_id.values())

    out_path = ROOT / 'cards' / 'edl' / f"{card['card_id']}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(edl, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')

    result = {'edl': edl, 'path': str(out_path), 'node': None}
    if validate_node:
        result['node'] = edl_mod.validate_with_node(out_path)
    return result


# --------------------------------------------------------------------------------- #
# 6. render_plan — the exact render.mjs command; never executes without --execute
# --------------------------------------------------------------------------------- #

_CHROME_CANDIDATES = (
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome', '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium-browser', '/usr/bin/chromium',
)


def _find_chrome():
    """An explicitly supplied, already-installed Chrome/Chromium binary — studio/remotion's
    README is explicit that the renderer must never download a browser itself."""
    env_path = os.environ.get('M2_CHROME_PATH') or os.environ.get('CHROME_EXECUTABLE') \
        or os.environ.get('PUPPETEER_EXECUTABLE_PATH')
    if env_path and pathlib.Path(env_path).exists():
        return env_path
    for candidate in _CHROME_CANDIDATES:
        if pathlib.Path(candidate).exists():
            return candidate
    return shutil.which('chromium') or shutil.which('google-chrome') or shutil.which('chrome')


NODE_MODULES_INSTALL_COMMAND = 'cd studio/remotion && npm ci --ignore-scripts --no-audit --no-fund'


def render_plan(card_id: str, *, execute: bool = False, out_dir: str = 'data/renders/review') -> dict:
    """Build the exact `node studio/remotion/render.mjs …` command for `card_id`'s
    current EDL (`cards/edl/<card_id>.json`, i.e. after `edl_with_takes` or, for a
    previs-only check, `engine.edl.card_to_edl`).

    Returns `{'state': ..., 'command': [...], ...}`. `state` is:
    - `NOT_CONFIGURED` — no EDL yet, `studio/remotion/node_modules` missing, no
      Chrome/Chromium binary found, or `node` missing from PATH. `reason` explains
      which; `install_command` is included whenever node_modules is the cause.
      The command is never run in this state, `--execute` or not.
    - `READY` — everything needed exists; the command is returned but not run
      unless `execute=True`.
    - `EXECUTED` — `execute=True`, everything was configured, the subprocess ran and
      exited 0; `receipt` holds render.mjs's own JSON receipt (parsed from stdout).
    - `FAILED` — `execute=True` but the subprocess exited non-zero, or the output
      file already exists (render.mjs itself refuses to overwrite one).
    """
    edl_path = ROOT / 'cards' / 'edl' / f'{card_id}.json'
    if not edl_path.exists():
        return {'state': 'NOT_CONFIGURED',
                'reason': f'no EDL at {edl_path}; run engine.edl (or edl_with_takes) for this card first'}

    node_modules = ROOT / 'studio' / 'remotion' / 'node_modules'
    node_bin = shutil.which('node')
    chrome = _find_chrome()

    reasons = []
    if not node_modules.exists():
        reasons.append(f'{node_modules} missing — Remotion dependencies are not installed')
    if not node_bin:
        reasons.append('node not found on PATH')
    if not chrome:
        reasons.append('no Chrome/Chromium binary found (set M2_CHROME_PATH to an existing install)')

    out_path = ROOT / out_dir / f'{card_id}.mp4'
    command = [
        node_bin or 'node', str(ROOT / 'studio' / 'remotion' / 'render.mjs'),
        '--edl', str(edl_path), '--assets', str(ROOT), '--output', str(out_path),
        '--browser', chrome or 'EXISTING_CHROME_BINARY',
    ]

    if reasons:
        result = {'state': 'NOT_CONFIGURED', 'reason': '; '.join(reasons),
                  'command': command, 'output_path': str(out_path), 'edl_path': str(edl_path)}
        if not node_modules.exists():
            result['install_command'] = NODE_MODULES_INSTALL_COMMAND
        return result

    result = {'state': 'READY', 'command': command, 'output_path': str(out_path), 'edl_path': str(edl_path)}
    if not execute:
        return result

    if out_path.exists():
        return {**result, 'state': 'FAILED',
                'reason': f'{out_path} already exists; render.mjs refuses to overwrite an output file'}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(command, capture_output=True, text=True, cwd=str(ROOT))
    if proc.returncode != 0:
        return {**result, 'state': 'FAILED', 'reason': (proc.stderr or proc.stdout or 'render.mjs failed').strip()}

    receipt = None
    for line in reversed((proc.stdout or '').splitlines()):
        line = line.strip()
        if line.startswith('{'):
            try:
                receipt = json.loads(line)
            except json.JSONDecodeError:
                pass
            break
    return {**result, 'state': 'EXECUTED', 'receipt': receipt, 'stdout': proc.stdout, 'stderr': proc.stderr}


# --------------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------------- #

def _cmd_takes(args):
    from engine.db_util import connect
    con = connect()
    summary = ingest_takes(con, args.card_id, takes_dir=args.takes_dir)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary['state'] in ('DONE',) else (1 if summary['state'] == 'FAILED' else 0)


def _cmd_plan(args):
    result = render_plan(args.card_id, execute=args.execute)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['state'] in ('READY', 'EXECUTED') else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)

    p_takes = sub.add_parser('takes', help='ingest + validate + probe cards/takes/<card_id>.json')
    p_takes.add_argument('card_id')
    p_takes.add_argument('--takes-dir', default='cards/takes')
    p_takes.set_defaults(func=_cmd_takes)

    p_plan = sub.add_parser('plan', help='build (and optionally run) the render.mjs command')
    p_plan.add_argument('card_id')
    p_plan.add_argument('--execute', action='store_true')
    p_plan.set_defaults(func=_cmd_plan)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
