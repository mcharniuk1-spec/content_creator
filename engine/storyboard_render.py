#!/usr/bin/env python3
"""Template-rendered storyboard frames for a card (SPEC.md §8; design/tokens/tokens.json).

Renders one 1080x1920 PNG per storyboard scene with Pillow, using the M2 Lab brand
tokens (colours, type, safe zones) straight from `design/tokens/tokens.json` — never
a hardcoded palette. Every frame is an explicit, visibly-labelled placeholder
(`[SHOT] close-up`, `[SCREEN] ...`, `[TEXT CARD]`, ...): this module never
substitutes a stock photo or an AI-generated image for footage that has not been
shot yet (see `cards/README.md` "template asset status").

A frame reads top to bottom as a producer's storyboard panel, not a mockup of the
finished reel:

    header strip   -- card_id / scene idx / time range / frame_type / layout / transition
    banner plate   -- overlay_text, if any (omitted when there is none)
    main area      -- one of four distinct layouts (a_roll / split_screen / demo /
                      motion_graphic), each showing the scene's `visual` description
                      in full, never hidden behind another element
    caption band   -- the full script_text, burned-caption style
    footer strip   -- source_inspiration codes + asset_status

The ground is the brand's paper surface (paper-first, per design/README.md), not the
Ink/dark surface used only where the tokens call for it (plates, screen chrome, the
motion_graphic statement card).

    python3 -m engine.storyboard_render cards/C-2026-09-11-01.json

`render_card()` mutates the storyboard scenes of the `card` dict it is given
in place (`asset_status='template'`, `asset_path=<relative path>`) and returns
the list of PNG paths it wrote, plus a contact sheet at
`cards/frames/<card_id>_sheet.png`.
"""
from __future__ import annotations

import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

from engine.db_util import ROOT

WIDTH, HEIGHT = 1080, 1920
FONTS_DIR = ROOT / 'design' / 'assets' / 'fonts' / 'ttf'
TOKENS_PATH = ROOT / 'design' / 'tokens' / 'tokens.json'


# --------------------------------------------------------------------------- #
# Brand tokens (design/tokens/tokens.json) — colours, type, safe zones
# --------------------------------------------------------------------------- #

def _px(value: str) -> int:
    return int(round(float(str(value).rstrip('px'))))


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def load_tokens(path=TOKENS_PATH) -> dict:
    """Read `design/tokens/tokens.json`; falls back to the documented v2 defaults
    (SPEC-adjacent, not invented) if the file is ever missing."""
    try:
        raw = json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raw = None
    base = (raw or {}).get('color', {}).get('base', {})

    def col(name, default):
        v = base.get(name, {}).get('$value')
        return _hex_to_rgb(v) if v else _hex_to_rgb(default)

    frame = (raw or {}).get('frame', {})
    size = (raw or {}).get('size', {})
    stroke = (raw or {}).get('stroke', {})

    def size_of(*keys, default='40px'):
        d = size
        for k in keys:
            d = d.get(k, {})
        return _px(d.get('$value', default)) if isinstance(d, dict) else _px(default)

    return {
        'color': {
            'paper': col('paper', '#E4E9EA'), 'ink': col('ink', '#0C1D1D'),
            'signal': col('signal', '#7DD774'), 'oxide': col('oxide', '#BB4347'),
            'blueprint': col('blueprint', '#1E4A80'), 'graphite': col('graphite', '#5C6565'),
            'rule': col('rule', '#BEC6C7'),
        },
        'pad_x': _px(frame.get('pad-x', {}).get('$value', '96px')),
        'pad_top': _px(frame.get('pad-top-reel', {}).get('$value', '272px')),
        'pad_bottom': _px(frame.get('pad-bottom-reel', {}).get('$value', '672px')),
        'size': {
            'hook': size_of('hook', 'default', default='96px'),
            'title': size_of('title', 'default', default='72px'),
            'body': size_of('body', 'default', default='46px'),
            'body_small': size_of('body', 'small', default='42px'),
            'caption': size_of('caption', 'default', default='40px'),
            'label': size_of('label', 'default', default='36px'),
            'label_small': size_of('label', 'small', default='32px'),
        },
        'hairline': _px(stroke.get('hairline', {}).get('$value', '2px')),
        'emphasis': _px(stroke.get('emphasis', {}).get('$value', '4px')),
    }


TOKENS = load_tokens()
C = TOKENS['color']

# The brand bans rounded corners, shadows, gradients and centered text (tokens.json
# "banned" block) — every draw helper below respects that: sharp rects, flat fills,
# left-aligned text. The one deliberate exception is the motion_graphic statement
# card, where the spec for this render calls for a centred statement; nothing else
# is ever centred.

FONT_FILES = {
    'display': 'SairaSemiCondensed-Black.ttf',        # hooks/statements
    'text': 'IBMPlexSans-Regular.ttf',
    'text_medium': 'IBMPlexSans-Medium.ttf',
    'text_semibold': 'IBMPlexSans-SemiBold.ttf',
    'mono': 'IBMPlexMono-Medium.ttf',
    'mono_semibold': 'IBMPlexMono-SemiBold.ttf',
}
_FONT_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def _font(key: str, size: int) -> ImageFont.ImageFont:
    size = max(int(size), 8)
    cache_key = (key, size)
    if cache_key in _FONT_CACHE:
        return _FONT_CACHE[cache_key]
    candidates = [FONTS_DIR / FONT_FILES.get(key, '')]
    is_bold_ish = key in ('display', 'text_semibold', 'mono_semibold')
    candidates += [
        pathlib.Path('DejaVuSans-Bold.ttf' if is_bold_ish else 'DejaVuSans.ttf'),
        pathlib.Path('/System/Library/Fonts/Helvetica.ttc'),
        pathlib.Path('/Library/Fonts/Arial.ttf'),
    ]
    font = None
    for c in candidates:
        try:
            if c.exists() or not c.is_absolute():
                font = ImageFont.truetype(str(c), size)
                break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    _FONT_CACHE[cache_key] = font
    return font


# --------------------------------------------------------------------------- #
# Small drawing helpers
# --------------------------------------------------------------------------- #

def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = (text or '').split()
    if not words:
        return []
    lines, cur = [], words[0]
    for w in words[1:]:
        trial = f'{cur} {w}'
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def _capped_lines(draw, text, font, max_width, max_lines) -> list[str]:
    """`_wrap` plus an ellipsis on the last kept line when it truncates."""
    lines = _wrap(draw, text, font, max_width)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip() + '…'
    return lines


def _draw_text_block(draw, xy, text, font, fill, max_width, line_height=None, max_lines=None):
    x, y = xy
    lines = _capped_lines(draw, text, font, max_width, max_lines)
    lh = line_height or int(font.size * 1.2)
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)  # left-aligned: centering is banned
        y += lh
    return y  # y after the last line


def _fit_single_line(draw, text, key, start_size, max_width, floor=16):
    """Shrink a mono/label line until it fits `max_width` on one line."""
    font = _font(key, start_size)
    while draw.textlength(text, font=font) > max_width and font.size > floor:
        font = _font(key, font.size - 2)
    return font


def _dashed_rect(draw, box, color, width=4, dash=12, gap=8):
    x0, y0, x1, y1 = box
    edges = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    for (ax, ay), (bx, by) in edges:
        length = max(abs(bx - ax), abs(by - ay))
        steps = max(int(length // (dash + gap)) + 1, 1)
        for i in range(steps):
            t0 = i * (dash + gap)
            t1 = min(t0 + dash, length)
            if t0 >= length:
                break
            frac0, frac1 = t0 / length if length else 0, t1 / length if length else 0
            sx = ax + (bx - ax) * frac0
            sy = ay + (by - ay) * frac0
            ex = ax + (bx - ax) * frac1
            ey = ay + (by - ay) * frac1
            draw.line([(sx, sy), (ex, ey)], fill=color, width=width)


# --------------------------------------------------------------------------- #
# Header / banner / caption / footer — the fixed top-to-bottom scaffold
# --------------------------------------------------------------------------- #

def _header_meta(draw, scene, tokens):
    """Returns (font, text) for the header strip; sized to fit on one line."""
    text = (
        f"{scene.get('_card_id', '')}  ·  S{scene.get('idx', 0):02d}  ·  "
        f"{scene.get('start_s', 0.0):.1f}-{scene.get('end_s', 0.0):.1f}s  ·  "
        f"{scene.get('frame_type', 'UNKNOWN')}  ·  {scene.get('layout', 'a_roll')}  ·  "
        f"->{scene.get('transition') or 'cut'}"
    )
    max_w = WIDTH - 2 * 28
    font = _fit_single_line(draw, text, 'mono', tokens['size']['label_small'], max_w, floor=18)
    return font, text


def _draw_header(draw, font, text, top, tokens, w=WIDTH):
    band_h = int(font.size * 1.3) + 28
    draw.rectangle((0, top, w, top + band_h), fill=C['ink'])
    ty = top + (band_h - font.size) // 2
    draw.text((28, ty), text, font=font, fill=C['rule'])  # secondary text on ink, per tokens
    return top + band_h


def _banner_plate(draw, top_y, text, tokens, w=WIDTH):
    """Ink plate with a hairline rule top/bottom, overlay text in Saira Black.
    One banner in one place (PRODUCTION.md); omitted entirely when there is no
    overlay text for this scene."""
    if not text:
        return top_y
    pad_x = tokens['pad_x']
    font = _font('display', tokens['size']['title'])
    max_w = w - 2 * pad_x
    lines = _wrap(draw, text, font, max_w)[:3]
    line_h = int(font.size * 1.03 * 1.15)
    plate_h = 2 * 28 + line_h * len(lines)
    draw.rectangle((0, top_y, w, top_y + plate_h), fill=C['ink'])
    draw.line((0, top_y, w, top_y), fill=C['rule'], width=tokens['hairline'])
    draw.line((0, top_y + plate_h, w, top_y + plate_h), fill=C['rule'], width=tokens['hairline'])
    y = top_y + 28
    for line in lines:
        draw.text((pad_x, y), line, font=font, fill=C['paper'])
        y += line_h
    return top_y + plate_h


def _measure_caption(draw, text, tokens, w=WIDTH):
    """Full script_text, burned-caption style: up to 5 lines, then an ellipsis."""
    font = _font('text_semibold', tokens['size']['caption'])
    max_w = w - 2 * tokens['pad_x']
    lines = _capped_lines(draw, text, font, max_w, 5)
    line_h = int(font.size * 1.2)
    band_h = (2 * 24 + line_h * len(lines)) if lines else 0
    return lines, font, line_h, band_h


def _draw_caption_band(draw, lines, font, line_h, top, band_h, tokens, w=WIDTH):
    if not lines or band_h <= 0:
        return
    draw.rectangle((0, top, w, top + band_h), fill=C['ink'])
    y = top + 24
    for line in lines:
        draw.text((tokens['pad_x'], y), line, font=font, fill=C['paper'])  # paper on ink: 14.2:1
        y += line_h


def _footer_meta(draw, scene, tokens):
    """Returns (font, text) for the footer strip: first two source_inspiration
    codes + asset_status, sized to fit on one line."""
    codes = [s.get('code') for s in (scene.get('source_inspiration') or []) if s.get('code')][:2]
    src = ', '.join(codes) if codes else '—'
    status = scene.get('asset_status') or '—'
    text = f'src: {src}  ·  asset: {status}'
    max_w = WIDTH - 2 * 28
    font = _fit_single_line(draw, text, 'mono', tokens['size']['label_small'] - 4, max_w, floor=16)
    return font, text


def _draw_footer(draw, font, text, top, tokens, w=WIDTH, h=HEIGHT):
    band_h = h - top
    draw.rectangle((0, top, w, h), fill=C['ink'])
    ty = top + (band_h - font.size) // 2
    draw.text((28, ty), text, font=font, fill=C['rule'])  # secondary text on ink, per tokens


# --------------------------------------------------------------------------- #
# Main-area building blocks: panels, screen chrome, presenter silhouette
# --------------------------------------------------------------------------- #

_FRAMING_LABELS = {
    'A_ROLL_TALKING_HEAD': 'talking head',
    'A_ROLL_CLOSE_UP': 'close-up',
    'A_ROLL_MEDIUM': 'medium',
    'A_ROLL_WIDE': 'wide',
}


def _framing_label(frame_type: str) -> str:
    if frame_type in _FRAMING_LABELS:
        return _FRAMING_LABELS[frame_type]
    ft = (frame_type or 'medium').replace('A_ROLL_', '').replace('_', ' ').strip().lower()
    return ft or 'medium'


def _panel_frame(draw, box, tokens, fill=None, border=None):
    """Paper panel, dashed rule border: a visibly-a-placeholder frame."""
    fill = fill or C['paper']
    border = border or C['graphite']
    draw.rectangle(box, fill=fill)
    _dashed_rect(draw, box, border, width=tokens['hairline'], dash=14, gap=10)


def _window_chrome(draw, box, tokens, h=56):
    """Title bar with three dots — a mock screen/window, brand-flat (no traffic-light
    colours, no gradient/shadow)."""
    x0, y0, x1, _ = box
    draw.rectangle((x0, y0, x1, y0 + h), fill=C['ink'])
    r = 9
    for i in range(3):
        cx = x0 + 30 + i * 30
        cy = y0 + h / 2
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=C['rule'])
    return y0 + h


def _panel_label_and_text(draw, box, label, body_text, tokens, chrome=False, max_lines=8,
                           label_color=None, text_color=None, pad=28):
    """Draws `[LABEL]` then the wrapped body text (the scene's `visual` description)
    inside a panel; returns the y just past the last line drawn."""
    x0, y0, x1, y1 = box
    top = y0 + pad
    if chrome:
        top = _window_chrome(draw, box, tokens) + pad
    font_label = _font('mono_semibold', tokens['size']['label'])
    draw.text((x0 + pad, top), label, font=font_label, fill=label_color or C['ink'])
    y = top + int(font_label.size * 1.3) + 14
    if body_text:
        font_body = _font('text', tokens['size']['body_small'])
        y = _draw_text_block(
            draw, (x0 + pad, y), body_text, font_body, text_color or C['graphite'],
            max_width=(x1 - x0) - 2 * pad, line_height=int(font_body.size * 1.3),
            max_lines=max_lines)
    return min(y, y1 - pad)


def _presenter_silhouette(draw, box, tokens, fill=None):
    """A simple head-and-shoulders placeholder shape — never a stock photo."""
    fill = fill or C['graphite']
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if w <= 40 or h <= 40:
        return
    cx = (x0 + x1) / 2
    size = min(w, h)
    head_r = size * 0.16
    head_cy = y0 + h * 0.30
    draw.ellipse((cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r), fill=fill)
    shoulder_top_y = head_cy + head_r * 0.85
    shoulder_top_half = head_r * 1.15
    shoulder_bottom_half = size * 0.36
    shoulder_bottom_y = min(y1 - h * 0.06, shoulder_top_y + h * 0.55)
    if shoulder_bottom_y <= shoulder_top_y:
        return
    draw.polygon([
        (cx - shoulder_top_half, shoulder_top_y),
        (cx + shoulder_top_half, shoulder_top_y),
        (cx + shoulder_bottom_half, shoulder_bottom_y),
        (cx - shoulder_bottom_half, shoulder_bottom_y),
    ], fill=fill)


# --------------------------------------------------------------------------- #
# Layouts — visibly distinct main areas, each rendered into `box` = (x0, y0, x1, y1)
# --------------------------------------------------------------------------- #

def _render_a_roll(draw, scene, tokens, box):
    """One large panel: presenter silhouette + a visible "[SHOT] <framing>" label,
    with the scene's `visual` description wrapped underneath the label."""
    x0, y0, x1, y1 = box
    inset = (x0 + tokens['pad_x'], y0, x1 - tokens['pad_x'], y1)
    _panel_frame(draw, inset, tokens)
    label = f"[SHOT] {_framing_label(scene.get('frame_type', ''))}"
    text_bottom = _panel_label_and_text(draw, inset, label, scene.get('visual') or '', tokens)
    _presenter_silhouette(draw, (inset[0], text_bottom + 24, inset[2], inset[3]), tokens)


def _render_split_screen(draw, scene, tokens, box):
    """Top 55% "[PROOF / SCREEN]" panel carrying the `visual` text; bottom 45%
    presenter panel with a silhouette."""
    x0, y0, x1, y1 = box
    x0i, x1i = x0 + tokens['pad_x'], x1 - tokens['pad_x']
    split_y = y0 + int((y1 - y0) * 0.55)
    top_box = (x0i, y0, x1i, split_y - 8)
    bottom_box = (x0i, split_y + 8, x1i, y1)
    _panel_frame(draw, top_box, tokens)
    _panel_label_and_text(draw, top_box, '[PROOF / SCREEN]', scene.get('visual') or '', tokens)
    _panel_frame(draw, bottom_box, tokens)
    label = f"[SHOT] {_framing_label(scene.get('frame_type', ''))}"
    text_bottom = _panel_label_and_text(draw, bottom_box, label, '', tokens)
    _presenter_silhouette(draw, (bottom_box[0], text_bottom + 16, bottom_box[2], bottom_box[3]), tokens)
    draw.line((x0, split_y, x1, split_y), fill=C['rule'], width=tokens['hairline'])


def _render_demo(draw, scene, tokens, box):
    """Full-bleed screen panel (edge to edge) with a mock window chrome, the
    `visual` text wrapped inside as "[SCREEN] …"."""
    _panel_frame(draw, box, tokens)
    visual = scene.get('visual') or 'screen recording'
    _panel_label_and_text(draw, box, '[SCREEN]', visual, tokens, chrome=True)


def _render_motion_graphic(draw, scene, tokens, box):
    """Statement card: overlay_text (or the first sentence of script_text), large
    and centred, on a Blueprint-tinted panel (accent.structure — paper surfaces
    only, which this frame's ground is). The `visual` description still shows,
    smaller, near the bottom of the card."""
    x0, y0, x1, y1 = box
    draw.rectangle(box, fill=C['blueprint'])
    pad = 40

    font_label = _font('mono_semibold', tokens['size']['label'])
    draw.text((x0 + pad, y0 + pad), '[TEXT CARD]', font=font_label, fill=C['paper'])
    content_top = y0 + pad + int(font_label.size * 1.3) + 20
    content_bottom = y1 - pad

    statement = scene.get('overlay_text')
    if not statement:
        first = (scene.get('script_text') or '').split('.')[0].strip()
        statement = f'{first}.' if first else ''

    visual = scene.get('visual') or ''
    font_body = _font('text', tokens['size']['body_small'])
    max_w = (x1 - x0) - 2 * pad
    visual_lines = _capped_lines(draw, visual, font_body, max_w, 8) if visual else []
    visual_line_h = int(font_body.size * 1.3)
    visual_h = (visual_line_h * len(visual_lines) + 16) if visual_lines else 0

    font = _font('display', tokens['size']['hook'])
    lines = _wrap(draw, statement, font, max_w) if statement else []
    line_h = int(font.size * 1.03 * 1.15)
    # shrink to fit the space left above the visual-description block
    stmt_area_bottom = content_bottom - visual_h
    while lines and font.size > 48 and line_h * len(lines) > (stmt_area_bottom - content_top):
        font = _font('display', font.size - 8)
        lines = _wrap(draw, statement, font, max_w)
        line_h = int(font.size * 1.03 * 1.15)
    total_h = line_h * len(lines)
    y = content_top + max(0, (stmt_area_bottom - content_top - total_h) // 2)
    accent_y = y
    for line in lines:
        lw = draw.textlength(line, font=font)
        draw.text((x0 + (x1 - x0 - lw) / 2, y), line, font=font, fill=C['paper'])  # 7.31:1
        accent_y = y + line_h
        y += line_h
    if lines:
        underline_w = 120
        cx = (x0 + x1) / 2
        underline_y = accent_y + int(font.size * 0.28)
        draw.line((cx - underline_w / 2, underline_y, cx + underline_w / 2, underline_y),
                   fill=C['rule'], width=tokens['emphasis'])

    if visual_lines:
        y2 = content_bottom - (visual_line_h * len(visual_lines))
        for vline in visual_lines:
            draw.text((x0 + pad, y2), vline, font=font_body, fill=C['rule'])  # 5.15:1 on blueprint
            y2 += visual_line_h


_LAYOUT_RENDERERS = {
    'a_roll': _render_a_roll,
    'split_screen': _render_split_screen,
    'demo': _render_demo,
    'motion_graphic': _render_motion_graphic,
    'text': _render_motion_graphic,  # rendering-time alias; see cards/README.md
}


def render_scene(scene: dict, tokens=TOKENS) -> Image.Image:
    im = Image.new('RGB', (WIDTH, HEIGHT), color=C['paper'])  # paper-first ground
    draw = ImageDraw.Draw(im)

    header_font, header_text = _header_meta(draw, scene, tokens)
    footer_font, footer_text = _footer_meta(draw, scene, tokens)
    footer_h = int(footer_font.size * 1.3) + 24
    caption_lines, caption_font, caption_line_h, caption_h = _measure_caption(
        draw, scene.get('script_text', ''), tokens)

    y = _draw_header(draw, header_font, header_text, 0, tokens)
    if scene.get('overlay_text'):
        y = _banner_plate(draw, y, scene['overlay_text'], tokens)

    main_bottom = HEIGHT - footer_h - caption_h
    main_bottom = max(main_bottom, y + 120)  # floor: keep a usable main area even if degenerate
    box = (0, y, WIDTH, main_bottom)

    layout = scene.get('layout', 'a_roll')
    renderer = _LAYOUT_RENDERERS.get(layout, _render_a_roll)
    renderer(draw, scene, tokens, box)

    _draw_caption_band(draw, caption_lines, caption_font, caption_line_h, main_bottom, caption_h, tokens)
    _draw_footer(draw, footer_font, footer_text, HEIGHT - footer_h, tokens)
    return im


# --------------------------------------------------------------------------- #
# render_card() + contact sheet
# --------------------------------------------------------------------------- #

def _out_dir_path(out_dir) -> pathlib.Path:
    p = pathlib.Path(out_dir)
    return p if p.is_absolute() else ROOT / p


def render_card(card: dict, out_dir='cards/frames') -> list[str]:
    """Render every storyboard scene of `card` to a PNG; mutates `card['storyboard']`
    scenes in place (`asset_status='template'`, `asset_path=<relative path>`).

    Returns the list of PNG paths written (str, relative to the repo root when
    possible). Also writes a contact sheet at `<out_dir>/<card_id>_sheet.png`.
    """
    out_path = _out_dir_path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    card_id = card['card_id']
    scenes = sorted(card['storyboard'], key=lambda s: s['idx'])

    written: list[str] = []
    thumbs: list[Image.Image] = []
    thumb_labels: list[str] = []
    for scene in scenes:
        scene_id = scene.get('scene_id') or f"S{scene['idx']:02d}"
        scene_render = dict(scene, _card_id=card_id)
        im = render_scene(scene_render)
        fname = f'{card_id}_{scene_id}.png'
        fpath = out_path / fname
        im.save(fpath, format='PNG')
        try:
            rel = str(fpath.relative_to(ROOT))
        except ValueError:
            rel = str(fpath)
        scene['asset_status'] = 'template'
        scene['asset_path'] = rel
        written.append(rel)
        thumbs.append(im)
        thumb_labels.append(f"{scene_id}  {scene.get('start_s', 0):.1f}-{scene.get('end_s', 0):.1f}s")

    _write_contact_sheet(thumbs, thumb_labels, out_path / f'{card_id}_sheet.png')
    return written


def _write_contact_sheet(frames: list[Image.Image], labels: list[str], out_path: pathlib.Path):
    if not frames:
        return
    n = len(frames)
    cols = min(3, n) or 1
    rows = (n + cols - 1) // cols
    thumb_w = 340
    thumb_h = int(thumb_w * HEIGHT / WIDTH)
    label_h = 36
    cell_w, cell_h = thumb_w + 16, thumb_h + label_h + 16
    sheet = Image.new('RGB', (cols * cell_w, rows * cell_h), color=C['paper'])
    draw = ImageDraw.Draw(sheet)
    font = _font('mono', 24)
    for i, (im, label) in enumerate(zip(frames, labels)):
        r, c = divmod(i, cols)
        thumb = im.resize((thumb_w, thumb_h))
        x, y = c * cell_w + 8, r * cell_h + 8
        sheet.paste(thumb, (x, y))
        draw.text((x, y + thumb_h + 4), label, font=font, fill=C['ink'])
    sheet.save(out_path, format='PNG')


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print('usage: python3 -m engine.storyboard_render <card.json>')
        return 1
    card_path = pathlib.Path(argv[0])
    card = json.loads(card_path.read_text(encoding='utf-8'))
    paths = render_card(card)
    card_path.write_text(json.dumps(card, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')
    for p in paths:
        print(p)
    print(f'{len(paths)} frame(s) + contact sheet written; {card_path} updated with asset_path')
    return 0


if __name__ == '__main__':
    sys.exit(main())
