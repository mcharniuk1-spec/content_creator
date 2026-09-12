#!/usr/bin/env python3
"""Card -> Remotion EDL (SPEC.md §8, `studio/remotion/contract.mjs`, `src/types.ts`).

`card_to_edl()` turns a validated card-v2 dict (see `engine/cards_v2.py`) into an
`m2.remotion-edl.v1` document: PREVIS render mode, one scene per storyboard entry,
a `placeholder` layer standing in for real A-roll footage, an `image` layer for the
template frame `engine/storyboard_render.py` rendered for that scene, and a `text`
layer for any burned-in overlay text. Nothing here pretends footage exists: every
scene keeps a `placeholder` layer, `speech_policy` is `REQUIRED_RECORDED_SPEECH`,
and `pending_audio_assets` always lists `speech` — this is a previs plan, not a
render-ready edit (contract.mjs enforces the difference when `production: true`).

    python3 -m engine.edl cards/C-2026-09-11-01.json     # build + validate via node
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

from engine.db_util import ROOT

EDL_SCHEMA = 'm2.remotion-edl.v1'
VALID_FPS = (24, 25, 30, 50, 60)
VALID_WIDTH = (540, 1080, 1920)
VALID_HEIGHT = (960, 1080, 1920)
CONTRACT_PATH = ROOT / 'studio' / 'remotion' / 'contract.mjs'


def _partition_frames(seconds_list: list[float], total_frames: int, fps: int) -> list[tuple[int, int]]:
    """Split `total_frames` across `seconds_list` proportionally, rounding without drift.

    Uses cumulative-boundary rounding (round each running total, then take
    consecutive differences) so the parts always sum exactly to `total_frames`,
    which is what `contract.mjs`'s `EDL_PARTITION_INVALID` / `EDL_COVERAGE_INCOMPLETE`
    checks require. Every part keeps at least 1 frame; raises if `total_frames` is too
    small to give every entry its own frame (a genuinely degenerate input).
    """
    n = len(seconds_list)
    if n == 0:
        return []
    if total_frames < n:
        raise ValueError(f'{total_frames} frames cannot cover {n} scenes (need >=1 frame each)')
    total_seconds = sum(seconds_list) or 1.0
    cum = 0.0
    boundaries = [0]
    for s in seconds_list:
        cum += s
        boundaries.append(round(cum / total_seconds * total_frames))
    boundaries[-1] = total_frames
    for i in range(1, n):  # enforce strictly increasing so no scene collapses to 0 frames
        if boundaries[i] <= boundaries[i - 1]:
            boundaries[i] = boundaries[i - 1] + 1
    if boundaries[n - 1] >= total_frames:
        raise ValueError('too many scenes for the available frame budget after rounding')
    boundaries[n] = total_frames
    return [(boundaries[i], boundaries[i + 1] - boundaries[i]) for i in range(n)]


def _placeholder_panel(layout: str) -> str:
    return 'bottom' if layout == 'split_screen' else 'full'


def _edl_layout(layout: str) -> str:
    """Map a storyboard layout to the EDL's 4-value closed set (contract.mjs)."""
    return 'motion_graphic' if layout in ('text', 'motion_graphic') else layout


def _sha256_of(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()


def _asset_relpath(scene: dict) -> str:
    asset_path = scene.get('asset_path')
    if not asset_path:
        raise ValueError(
            f"storyboard scene idx={scene.get('idx')} has no asset_path; run "
            f"engine.storyboard_render.render_card(card) before card_to_edl(card)")
    p = pathlib.Path(asset_path)
    return str(p) if not p.is_absolute() else str(p.relative_to(ROOT))


def card_to_edl(card: dict, fps: int = 30, width: int = 1080, height: int = 1920) -> dict:
    """Build an `m2.remotion-edl.v1` PREVIS document from a card dict.

    Requires every `card['storyboard']` scene to already carry an `asset_path`
    pointing at an existing PNG (i.e. `engine.storyboard_render.render_card` has
    run). Writes `cards/edl/<card_id>.json` and returns the dict.
    """
    if fps not in VALID_FPS:
        raise ValueError(f'fps {fps} not one of {VALID_FPS}')
    if width not in VALID_WIDTH or height not in VALID_HEIGHT:
        raise ValueError(f'resolution {width}x{height} not accepted by contract.mjs')

    scenes_in = sorted(card['storyboard'], key=lambda s: s['idx'])
    total_s = card['script']['total_s']
    duration_frames = round(total_s * fps)

    scene_durations_s = [s['end_s'] - s['start_s'] for s in scenes_in]
    frame_parts = _partition_frames(scene_durations_s, duration_frames, fps)

    assets: list[dict] = []
    scenes_out: list[dict] = []
    seen_asset_ids: set[str] = set()
    for (from_frame, dur_frames), scene in zip(frame_parts, scenes_in):
        scene_id = scene.get('scene_id') or f"S{scene['idx']:02d}"
        layout = _edl_layout(scene.get('layout', 'a_roll'))

        rel_path = _asset_relpath(scene)
        abs_path = ROOT / rel_path
        if not abs_path.exists():
            raise FileNotFoundError(f'storyboard frame not found on disk: {abs_path}')
        asset_id = f'img-{scene_id}'
        if asset_id not in seen_asset_ids:
            assets.append({
                'asset_id': asset_id, 'kind': 'image', 'path': rel_path,
                'sha256': _sha256_of(abs_path), 'rights_approved': True,
                'rights_receipt_id': 'internal-template',
            })
            seen_asset_ids.add(asset_id)

        layers = [
            {'kind': 'placeholder', 'panel': _placeholder_panel(layout)},
            {'kind': 'image', 'asset_id': asset_id, 'panel': 'full'},
        ]
        overlay_text = scene.get('overlay_text')
        if overlay_text and overlay_text.strip():
            layers.append({'kind': 'text', 'text': overlay_text, 'panel': 'full'})

        scenes_out.append({
            'scene_id': scene_id, 'from_frame': from_frame, 'duration_frames': dur_frames,
            'layout': layout, 'layers': layers,
        })

    caption_seconds = [max(s['end_s'] - s['start_s'], 0.001) for s in scenes_in]
    caption_parts = _partition_frames(caption_seconds, duration_frames, fps)
    captions = []
    for (from_frame, dur_frames), scene in zip(caption_parts, scenes_in):
        text = (scene.get('script_text') or '').strip()
        if text:
            captions.append({'from_frame': from_frame, 'duration_frames': dur_frames, 'text': text})

    edl = {
        'schema': EDL_SCHEMA,
        'card_id': card['card_id'],
        'title': card.get('title', card['card_id']),
        'fps': fps, 'width': width, 'height': height,
        'duration_frames': duration_frames,
        'scenes': scenes_out,
        'assets': assets,
        'captions': captions,
        'audio_stems': [],
        'pending_audio_assets': ['speech'],
        'speech_policy': 'REQUIRED_RECORDED_SPEECH',
        'render_mode': 'PREVIS',
        'review_state': card.get('status', 'DRAFT'),
    }

    out_path = ROOT / 'cards' / 'edl' / f"{card['card_id']}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(edl, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')
    return edl


def validate_with_node(path) -> dict:
    """Run `contract.mjs`'s `validateEDL` over the EDL at `path` via Node.

    Returns `{'ok': bool, 'skipped': bool, 'stdout': str, 'stderr': str}`.
    `skipped` is True (and `ok` is False) only when node is not on PATH — callers
    that must not hard-fail in that case should check `skipped` explicitly.
    """
    node = shutil.which('node')
    if not node:
        return {'ok': False, 'skipped': True, 'reason': 'node not found on PATH', 'stdout': '', 'stderr': ''}
    if not CONTRACT_PATH.exists():
        return {'ok': False, 'skipped': True, 'reason': f'{CONTRACT_PATH} not found', 'stdout': '', 'stderr': ''}

    edl_path = pathlib.Path(path).resolve()
    contract_url = CONTRACT_PATH.resolve().as_uri()
    script = (
        f"import({contract_url!r}).then(m => {{"
        f"  const edl = JSON.parse(require('fs').readFileSync(process.argv[1], 'utf8'));"
        f"  m.validateEDL(edl);"
        f"  console.log('EDL_OK');"
        f"}}).catch(e => {{"
        f"  console.error(e && e.message ? e.message : String(e));"
        f"  process.exit(1);"
        f"}});"
    )
    try:
        proc = subprocess.run(
            [node, '-e', script, str(edl_path)],
            capture_output=True, text=True, timeout=30, cwd=str(ROOT))
    except subprocess.TimeoutExpired as exc:
        return {'ok': False, 'skipped': False, 'reason': f'node timed out: {exc}', 'stdout': '', 'stderr': ''}

    ok = proc.returncode == 0 and 'EDL_OK' in proc.stdout
    return {
        'ok': ok, 'skipped': False, 'returncode': proc.returncode,
        'stdout': proc.stdout.strip(), 'stderr': proc.stderr.strip(),
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print('usage: python3 -m engine.edl <card.json>')
        return 1
    card = json.loads(pathlib.Path(argv[0]).read_text(encoding='utf-8'))
    edl = card_to_edl(card)
    out_path = ROOT / 'cards' / 'edl' / f"{card['card_id']}.json"
    print(f'wrote {out_path} ({edl["duration_frames"]} frames @ {edl["fps"]}fps, '
          f'{len(edl["scenes"])} scene(s), {len(edl["assets"])} asset(s))')
    result = validate_with_node(out_path)
    if result['skipped']:
        print(f"node validation skipped: {result.get('reason')}")
        return 0
    print('EDL_OK' if result['ok'] else f"EDL_INVALID: {result['stderr'] or result['stdout']}")
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
