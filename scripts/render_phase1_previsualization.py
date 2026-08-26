#!/usr/bin/env python3
"""Render the provider-disabled Phase 1 storyboard and report package.

Inputs are frozen ``content-plan.json`` and ``frame-sequence.json`` files under
``outputs/video-plans/Vxx``.  The renderer creates deterministic PNG/SVG assets,
contact sheets, Markdown/PDF reports, and hash manifests.  It never calls a
network service or a media provider.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image as RLImage,
    KeepTogether,
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
PLANS_ROOT = ROOT / "outputs" / "video-plans"
FIGMA_ROOT = ROOT / "outputs" / "figma" / "import-package"
SOURCE_RECORD_ROOT = ROOT / "runs" / "20260811-phase1-content-batch" / "lanes" / "scout" / "source-records"
EVIDENCE_CARD_ROOT = ROOT / "runs" / "20260811-phase1-content-batch" / "lanes" / "scout" / "evidence-cards"
RIGHTS_ROOT = ROOT / "runs" / "20260811-phase1-content-batch" / "reviews" / "source-rights-decisions"
CANDIDATE_ROOT = ROOT / "runs" / "20260811-phase1-content-batch" / "lanes" / "forge" / "prejury"
EVIDENCE_REVIEW_SHA256 = "3aa7ffc1a38ef9a6519478ea2872a15a6e5c0b31f7c6a57f62b793d9192aee0b"
BASE_PLATE_MANIFEST_SHA256 = "bf43e4c80663bc68c8ccf578d6d3137a36178bb70f75acc9b4a4b25f784a7f1b"
FONT_REGULAR = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
FONT_BOLD = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")

PDF_SECTIONS = [
    "cover_and_truth_state",
    "audience_problem_pain_consequence_mechanism_limitation_cta",
    "source_ledger_and_claim_map",
    "pattern_abstractions_and_clean_room_restrictions",
    "concept_v1_and_critique",
    "story_v2_and_beat_sheet",
    "production_prompt_v3",
    "candidate_set_hash_and_judge_verdicts",
    "timecoded_frame_table",
    "contact_sheet",
    "asset_prompts_negatives_continuity_fallbacks",
    "screen_recording_plan",
    "narration_captions_music_ambience_sfx",
    "edit_timeline_transitions_platform_variants",
    "candidate_provider_model_routing",
    "rights_consent_accessibility_qa_cost_approvals_fallback",
    "platform_copy_transcript_alt_text",
]

PALETTES = {
    "archflow_onboarding": {
        "bg": "#07111F",
        "bg2": "#111B35",
        "ink": "#F8FAFF",
        "muted": "#A9B4CF",
        "accent": "#6C7BFF",
        "accent2": "#35D7FF",
        "good": "#4DE0A8",
        "warn": "#FFC857",
    },
    "hotel_revenue": {
        "bg": "#071A1C",
        "bg2": "#123337",
        "ink": "#F8FFFC",
        "muted": "#AECBC7",
        "accent": "#25C6B5",
        "accent2": "#E3B55F",
        "good": "#65D08D",
        "warn": "#FF8C69",
    },
}


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_dimensions(path: Path) -> list[int]:
    with Image.open(path) as image:
        return [image.width, image.height]


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    chosen = FONT_BOLD if bold else FONT_REGULAR
    return ImageFont.truetype(str(chosen), size=size)


def wrap(draw: ImageDraw.ImageDraw, value: str, face: ImageFont.FreeTypeFont, width: int, limit: int | None = None) -> list[str]:
    words = value.replace("\n", " ").split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=face) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    if limit and len(lines) > limit:
        lines = lines[:limit]
        lines[-1] = lines[-1].rstrip(" .") + "..."
    return lines or [""]


def draw_wrapped(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, face: ImageFont.FreeTypeFont,
                 fill: str, width: int, spacing: int = 12, limit: int | None = None) -> int:
    x, y = xy
    lines = wrap(draw, value, face, width, limit)
    box = face.getbbox("Ag")
    line_height = box[3] - box[1]
    for line in lines:
        draw.text((x, y), line, font=face, fill=fill)
        y += line_height + spacing
    return y


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill: str,
            outline: str | None = None, width: int = 1) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def crop_cover(image: Image.Image, target: tuple[int, int]) -> Image.Image:
    tw, th = target
    scale = max(tw / image.width, th / image.height)
    resized = image.resize((math.ceil(image.width * scale), math.ceil(image.height * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - tw) // 2
    top = (resized.height - th) // 2
    return resized.crop((left, top, left + tw, top + th))


def gradient(size: tuple[int, int], top: str, bottom: str) -> Image.Image:
    w, h = size
    a = tuple(int(top[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(bottom[i:i + 2], 16) for i in (1, 3, 5))
    image = Image.new("RGB", size)
    draw = ImageDraw.Draw(image)
    for y in range(h):
        t = y / max(h - 1, 1)
        color = tuple(round(a[i] * (1 - t) + b[i] * t) for i in range(3))
        draw.line((0, y, w, y), fill=color)
    return image


def visual_module(draw: ImageDraw.ImageDraw, frame_no: int, palette: dict[str, str]) -> None:
    """Draw a distinct clean-room information graphic in the central viewport."""
    left, top, right, bottom = 100, 650, 980, 1350
    rounded(draw, (left, top, right, bottom), 42, "#FFFFFF12", palette["accent"], 3)
    mode = (frame_no - 1) % 5
    if mode == 0:
        xs = [210, 540, 870]
        labels = ["SOURCE", "RULE", "ACTION"]
        for idx, x in enumerate(xs):
            draw.ellipse((x - 70, 910, x + 70, 1050), fill=palette["bg2"], outline=palette["accent2"], width=5)
            draw.text((x, 1080), labels[idx], font=font(24, True), fill=palette["muted"], anchor="ma")
            if idx < 2:
                draw.line((x + 80, 980, xs[idx + 1] - 80, 980), fill=palette["accent"], width=8)
                draw.polygon([(xs[idx + 1] - 95, 960), (xs[idx + 1] - 65, 980), (xs[idx + 1] - 95, 1000)], fill=palette["accent"])
    elif mode == 1:
        for idx in range(4):
            y = 760 + idx * 125
            rounded(draw, (180, y, 900, y + 82), 20, palette["bg2"], "#FFFFFF25", 2)
            draw.ellipse((210, y + 21, 250, y + 61), fill=palette["good"] if idx < 3 else palette["warn"])
            draw.rounded_rectangle((285, y + 27, 820 - idx * 70, y + 56), radius=12, fill=palette["accent"])
    elif mode == 2:
        draw.arc((230, 760, 850, 1380), 195, 345, fill=palette["accent2"], width=36)
        draw.arc((310, 840, 770, 1300), 195, 330, fill=palette["accent"], width=28)
        draw.line((540, 1080, 760, 900), fill=palette["ink"], width=10)
        draw.ellipse((510, 1050, 570, 1110), fill=palette["ink"])
        draw.text((540, 1205), "CONTROLLED", font=font(32, True), fill=palette["muted"], anchor="ma")
    elif mode == 3:
        columns = ["INPUT", "CHECK", "DECIDE", "RECEIPT"]
        for idx, label in enumerate(columns):
            x = 135 + idx * 220
            rounded(draw, (x, 800, x + 170, 1190), 28, palette["bg2"], palette["accent"] if idx == frame_no % 4 else "#FFFFFF25", 3)
            draw.text((x + 85, 850), label, font=font(20, True), fill=palette["muted"], anchor="ma")
            for row in range(3):
                draw.rounded_rectangle((x + 34, 930 + row * 70, x + 136, 956 + row * 70), radius=10, fill=palette["accent2"] if row == idx % 3 else "#FFFFFF30")
    else:
        points = [(175, 1180), (330, 1040), (485, 1110), (650, 850), (855, 920)]
        draw.line(points, fill=palette["accent2"], width=14, joint="curve")
        for x, y in points:
            draw.ellipse((x - 25, y - 25, x + 25, y + 25), fill=palette["ink"], outline=palette["accent"], width=6)
        draw.line((170, 1240, 875, 1240), fill="#FFFFFF35", width=3)


def render_frame(video_dir: Path, plan: dict, sequence: dict, frame_data: dict, base_plate: Path | None) -> tuple[Path, Path]:
    video_id = plan["video_id"]
    frame_id = frame_data["frame_id"]
    palette = PALETTES[plan["campaign_domain"]]
    canvas = gradient((1080, 1920), palette["bg"], palette["bg2"])
    if base_plate and base_plate.exists():
        plate = crop_cover(Image.open(base_plate).convert("RGB"), (1080, 1920)).filter(ImageFilter.GaussianBlur(radius=8))
        plate.putalpha(58)
        canvas = canvas.convert("RGBA")
        canvas.alpha_composite(plate.convert("RGBA"))
        canvas = canvas.convert("RGB")
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.ellipse((-220, -80, 700, 840), fill=palette["accent"] + "24")
    draw.ellipse((620, 1060, 1320, 1820), fill=palette["accent2"] + "18")
    draw.line((90, 126, 990, 126), fill=palette["accent2"], width=5)

    draw.text((90, 72), "ARCHFLOW / PHASE 1 PREVIS", font=font(24, True), fill=palette["muted"])
    timing = f"{frame_data['start_ms'] / 1000:.1f}-{frame_data['end_ms'] / 1000:.1f}s"
    draw.text((990, 72), f"{frame_id}  {timing}", font=font(24, True), fill=palette["muted"], anchor="ra")
    draw.text((90, 190), frame_data["story_function"].upper(), font=font(27, True), fill=palette["accent2"])
    y = draw_wrapped(draw, (90, 245), frame_data["on_screen_text"], font(65, True), palette["ink"], 900, 10, 4)
    draw.text((90, min(y + 22, 575)), f"{plan['campaign_domain'].replace('_', ' ').upper()}  /  {frame_data['composition_type'].replace('_', ' ').upper()}",
              font=font(22, True), fill=palette["muted"])

    visual_module(draw, frame_data["sequence_number"], palette)

    rounded(draw, (90, 1400, 990, 1775), 34, "#020711C9", "#FFFFFF26", 2)
    draw.text((130, 1440), "NARRATION", font=font(21, True), fill=palette["accent2"])
    draw_wrapped(draw, (130, 1485), frame_data["narration"], font(30), palette["ink"], 820, 8, 4)
    draw_wrapped(
        draw,
        (130, 1660),
        f"OUT: {frame_data['transition_out']}",
        font(18, True),
        palette["muted"],
        820,
        5,
        2,
    )
    draw.text((950, 1732), "LOCAL STORYBOARD", font=font(18, True), fill=palette["good"], anchor="ra")
    draw.line((90, 1830, 990, 1830), fill="#FFFFFF30", width=2)
    draw.text((90, 1855), "OWNER_REVIEW_PENDING", font=font(21, True), fill=palette["warn"])
    draw.text((990, 1855), "EXTERNAL PROVIDER: NOT RUN", font=font(21, True), fill=palette["muted"], anchor="ra")

    frame_dir = video_dir / "individual-frames"
    svg_dir = FIGMA_ROOT / video_id / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    svg_dir.mkdir(parents=True, exist_ok=True)
    png_path = frame_dir / f"{frame_id}.png"
    svg_path = svg_dir / f"{frame_id}.svg"
    canvas.save(png_path, format="PNG", optimize=True)
    render_frame_svg(svg_path, plan, frame_data, palette)
    return png_path, svg_path


def svg_lines(value: str, max_chars: int = 26, max_lines: int = 4) -> list[str]:
    lines = textwrap.wrap(value, width=max_chars, break_long_words=False, break_on_hyphens=False)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .") + "..."
    return lines or [""]


def render_frame_svg(path: Path, plan: dict, frame_data: dict, palette: dict[str, str]) -> None:
    title_lines = svg_lines(frame_data["on_screen_text"], 25, 4)
    narration_lines = svg_lines(frame_data["narration"], 55, 4)
    transition_lines = svg_lines("OUT: " + frame_data["transition_out"], 78, 2)
    title_tspans = "".join(
        f'<tspan x="90" dy="{0 if i == 0 else 76}">{html.escape(line)}</tspan>' for i, line in enumerate(title_lines)
    )
    narration_tspans = "".join(
        f'<tspan x="130" dy="{0 if i == 0 else 44}">{html.escape(line)}</tspan>' for i, line in enumerate(narration_lines)
    )
    transition_tspans = "".join(
        f'<tspan x="130" dy="{0 if i == 0 else 26}">{html.escape(line)}</tspan>' for i, line in enumerate(transition_lines)
    )
    timing = f"{frame_data['start_ms'] / 1000:.1f}-{frame_data['end_ms'] / 1000:.1f}s"
    body = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">
<title>{html.escape(frame_data['frame_id'])} editable storyboard frame</title>
<desc>Named editable layer groups; the linked base plate is a local original asset copied with the Figma package.</desc>
<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop stop-color="{palette['bg']}"/><stop offset="1" stop-color="{palette['bg2']}"/></linearGradient></defs>
<g id="base-layer" data-layer-role="base" data-editable="true">
  <rect id="base-gradient" width="1080" height="1920" fill="url(#bg)"/>
  <image id="base-plate-image" href="../base-plate.png" x="0" y="0" width="1080" height="1920" preserveAspectRatio="xMidYMid slice" opacity=".22"/>
  <circle id="base-accent-field" cx="170" cy="260" r="420" fill="{palette['accent']}" opacity=".10"/>
</g>
<g id="subject-layer" data-layer-role="subject" data-editable="true" data-state="not-applicable"/>
<g id="ui-layer" data-layer-role="ui" data-editable="true">
  <rect id="ui-card" x="100" y="650" width="880" height="700" rx="42" fill="#ffffff" opacity=".06" stroke="{palette['accent']}" stroke-width="3"/>
  <circle id="ui-source-node" cx="260" cy="980" r="74" fill="{palette['bg2']}" stroke="{palette['accent2']}" stroke-width="6"/>
  <circle id="ui-rule-node" cx="540" cy="980" r="74" fill="{palette['bg2']}" stroke="{palette['accent2']}" stroke-width="6"/>
  <circle id="ui-action-node" cx="820" cy="980" r="74" fill="{palette['bg2']}" stroke="{palette['accent2']}" stroke-width="6"/>
  <line id="ui-edge-1" x1="340" y1="980" x2="460" y2="980" stroke="{palette['accent']}" stroke-width="10"/>
  <line id="ui-edge-2" x1="620" y1="980" x2="740" y2="980" stroke="{palette['accent']}" stroke-width="10"/>
  <text id="ui-source-label" x="260" y="1100" text-anchor="middle" fill="{palette['muted']}" font-family="Arial" font-size="24" font-weight="700">SOURCE</text>
  <text id="ui-rule-label" x="540" y="1100" text-anchor="middle" fill="{palette['muted']}" font-family="Arial" font-size="24" font-weight="700">RULE</text>
  <text id="ui-action-label" x="820" y="1100" text-anchor="middle" fill="{palette['muted']}" font-family="Arial" font-size="24" font-weight="700">ACTION</text>
</g>
<g id="overlay-layer" data-layer-role="overlay" data-editable="true">
  <line id="overlay-rule" x1="90" y1="126" x2="990" y2="126" stroke="{palette['accent2']}" stroke-width="5"/>
  <text id="overlay-brand-label" x="90" y="94" fill="{palette['muted']}" font-family="Arial" font-size="24" font-weight="700">ARCHFLOW / PHASE 1 PREVIS</text>
  <text id="overlay-frame-label" x="990" y="94" text-anchor="end" fill="{palette['muted']}" font-family="Arial" font-size="24" font-weight="700">{html.escape(frame_data['frame_id'])}  {timing}</text>
  <text id="overlay-story-function" x="90" y="220" fill="{palette['accent2']}" font-family="Arial" font-size="27" font-weight="700">{html.escape(frame_data['story_function'].upper())}</text>
  <text id="overlay-title" x="90" y="320" fill="{palette['ink']}" font-family="Arial" font-size="65" font-weight="700">{title_tspans}</text>
</g>
<g id="caption-layer" data-layer-role="caption" data-editable="true">
  <rect id="caption-panel" x="90" y="1400" width="900" height="375" rx="34" fill="#020711" opacity=".82" stroke="#ffffff" stroke-opacity=".16"/>
  <text id="caption-label" x="130" y="1475" fill="{palette['accent2']}" font-family="Arial" font-size="21" font-weight="700">NARRATION</text>
  <text id="caption-copy" x="130" y="1535" fill="{palette['ink']}" font-family="Arial" font-size="31">{narration_tspans}</text>
</g>
<g id="annotation-layer" data-layer-role="annotation" data-editable="true">
  <text id="annotation-transition" x="130" y="1680" fill="{palette['muted']}" font-family="Arial" font-size="18" font-weight="700">{transition_tspans}</text>
  <text id="annotation-local-state" x="950" y="1750" text-anchor="end" fill="{palette['good']}" font-family="Arial" font-size="18" font-weight="700">LOCAL STORYBOARD</text>
  <text id="annotation-owner-state" x="90" y="1885" fill="{palette['warn']}" font-family="Arial" font-size="21" font-weight="700">OWNER_REVIEW_PENDING</text>
  <text id="annotation-provider-state" x="990" y="1885" text-anchor="end" fill="{palette['muted']}" font-family="Arial" font-size="21" font-weight="700">EXTERNAL PROVIDER: NOT RUN</text>
</g>
</svg>'''
    path.write_text(body, encoding="utf-8")


def render_contact_sheet(video_dir: Path, plan: dict, sequence: dict, frame_paths: list[Path]) -> Path:
    palette = PALETTES[plan["campaign_domain"]]
    columns, tile_w, gap, margin = 4, 900, 40, 60
    tile_h, header_h = 1840, 440
    rows = math.ceil(len(frame_paths) / columns)
    board = gradient((3840, header_h + rows * tile_h + 90), palette["bg"], palette["bg2"])
    draw = ImageDraw.Draw(board, "RGBA")
    reviewer = sequence["review"]
    draw.text((60, 38), f"{plan['video_id']} / {plan['title']}", font=font(52, True), fill=palette["ink"])
    draw.text(
        (60, 112),
        f"CHANNEL {plan['primary_channel'].upper()}  /  {sequence['target_duration_ms'] / 1000:.0f}s  /  {len(frame_paths)} FRAMES  /  {sequence['aspect_ratio']}  /  VERSION V3  /  FOUR-COLUMN SEQUENCE",
        font=font(25, True),
        fill=palette["muted"],
    )
    draw_wrapped(draw, (60, 157), f"AUDIENCE: {plan['audience']}", font(20, True), palette["ink"], 3720, 5, 1)
    draw_wrapped(draw, (60, 193), f"PAIN: {plan['pain']}", font(20), palette["muted"], 3720, 5, 1)
    draw.text((60, 233), f"CANDIDATE SET: {plan['candidate_set_hash']}", font=font(18, True), fill=palette["accent2"])
    draw_wrapped(draw, (60, 270), "EVIDENCE/SOURCE IDS: " + " | ".join(plan["evidence_ids"]), font(18, True), palette["ink"], 3720, 4, 1)
    draw.text(
        (60, 308),
        f"EVIDENCE: INDEPENDENT GATE APPROVED WITH RECORDED METADATA/CONTEXT LIMITS  /  RIGHTS: SOURCE-SPECIFIC PASS  /  REVIEWER: {reviewer['reviewer']} {reviewer['verdict']}",
        font=font(18, True),
        fill=palette["muted"],
    )
    draw.text(
        (60, 350),
        f"LOCAL STORYBOARD: {sequence['storyboard_asset_state']}  /  OWNER: {sequence['owner_state']}  /  EXTERNAL PROVIDER: {sequence['external_provider_generation_state']}",
        font=font(21, True),
        fill=palette["accent2"],
    )
    for idx, frame_path in enumerate(frame_paths):
        row, col = divmod(idx, columns)
        x = margin + col * (tile_w + gap)
        y = header_h + row * tile_h
        rounded(draw, (x, y, x + tile_w, y + tile_h - 30), 28, "#FFFFFF0D", "#FFFFFF22", 2)
        preview = Image.open(frame_path).convert("RGB").resize((760, 1351), Image.Resampling.LANCZOS)
        board.paste(preview, (x + 70, y + 34))
        frame_data = sequence["frames"][idx]
        draw.text((x + 40, y + 1415), f"{frame_data['frame_id']}  {frame_data['start_ms']/1000:.1f}-{frame_data['end_ms']/1000:.1f}s  /  {frame_data['story_function'].upper()}",
                  font=font(25, True), fill=palette["accent2"])
        draw_wrapped(draw, (x + 40, y + 1458), "ON-SCREEN: " + frame_data["on_screen_text"], font(21, True), palette["ink"], 820, 5, 2)
        draw_wrapped(draw, (x + 40, y + 1524), "NARRATION: " + frame_data["narration"], font(18), palette["muted"], 820, 4, 2)
        draw_wrapped(draw, (x + 40, y + 1584), "TRANSITION: " + frame_data["transition_out"], font(17, True), palette["muted"], 820, 4, 2)
        visual_class = {
            "generated_scene": "GENERATED STILL / LOCAL BASE PLATE",
            "screen_capture": "SCREEN RECORDING PLAN / SYNTHETIC / NOT RUN",
            "motion_graphic": "MOTION GRAPHIC / EDITABLE",
            "talking_head": "TALKING HEAD",
            "hybrid": "HYBRID",
        }[frame_data["composition_type"]]
        draw.text((x + 40, y + 1652), f"VISUAL: {visual_class}", font=font(17, True), fill=palette["accent2"])
        draw.text((x + 40, y + 1686), "TALKING HEAD: NO  /  LICENSED OR PUBLIC FOOTAGE: NO", font=font(16, True), fill=palette["muted"])
        draw.text((x + 40, y + 1720), "AUDIO EVENT: NARRATION + PLANNED MUSIC/SFX  /  NOT RUN", font=font(16, True), fill=palette["muted"])
    draw.text(
        (60, board.height - 54),
        f"EVIDENCE IDS: {' | '.join(plan['evidence_ids'])}  /  RIGHTS: SOURCE-SPECIFIC PASS  /  REVIEW: {reviewer['reviewer']} {reviewer['verdict']}  /  LOCAL: {sequence['storyboard_asset_state']}  /  PROVIDER: NOT RUN",
        font=font(17, True),
        fill=palette["muted"],
    )
    path = video_dir / f"{plan['video_id']}-sequence-board.png"
    board.save(path, format="PNG", optimize=True)
    return path


def render_static_companion(video_dir: Path, plan: dict) -> tuple[Path, Path]:
    palette = PALETTES[plan["campaign_domain"]]
    image = gradient((1080, 1350), palette["bg"], palette["bg2"])
    draw = ImageDraw.Draw(image, "RGBA")
    draw.ellipse((580, -180, 1290, 530), fill=palette["accent"] + "24")
    draw.text((70, 65), f"ARCHFLOW / {plan['video_id']} / STATIC COMPANION", font=font(22, True), fill=palette["muted"])
    draw.line((70, 118, 1010, 118), fill=palette["accent2"], width=5)
    y = draw_wrapped(draw, (70, 180), plan["title"], font(58, True), palette["ink"], 930, 10, 4)
    rounded(draw, (70, max(y + 25, 440), 1010, 1000), 36, "#020711B8", "#FFFFFF24", 2)
    box_y = max(y + 70, 490)
    draw.text((115, box_y), "THE PROBLEM", font=font(21, True), fill=palette["accent2"])
    box_y = draw_wrapped(draw, (115, box_y + 38), plan["problem"], font(32), palette["ink"], 850, 8, 3) + 30
    draw.text((115, box_y), "BOUNDED MECHANISM", font=font(21, True), fill=palette["good"])
    box_y = draw_wrapped(draw, (115, box_y + 38), plan["bounded_mechanism"], font(31, True), palette["ink"], 850, 8, 3) + 30
    draw.text((115, box_y), "LIMIT", font=font(21, True), fill=palette["warn"])
    draw_wrapped(draw, (115, box_y + 38), plan["limitation"], font(27), palette["muted"], 850, 8, 3)
    rounded(draw, (70, 1070, 1010, 1235), 34, palette["accent"], None)
    draw_wrapped(draw, (115, 1110), plan["cta"], font(31, True), palette["ink"], 850, 7, 2)
    draw.text((70, 1285), "OWNER_REVIEW_PENDING / EDITABLE SVG INCLUDED", font=font(20, True), fill=palette["muted"])
    png_path = video_dir / f"{plan['video_id']}-static-companion.png"
    image.save(png_path, format="PNG", optimize=True)

    svg_path = FIGMA_ROOT / plan["video_id"] / f"{plan['video_id']}-static-companion.svg"
    svg_path.parent.mkdir(parents=True, exist_ok=True)

    def tspans(lines: list[str], x: int, line_height: int) -> str:
        return "".join(
            f'<tspan x="{x}" dy="{0 if index == 0 else line_height}">{html.escape(line)}</tspan>'
            for index, line in enumerate(lines)
        )

    title_svg = tspans(wrap(draw, plan["title"], font(56, True), 930, 4), 70, 64)
    problem_svg = tspans(wrap(draw, plan["problem"], font(30), 850, 3), 115, 38)
    mechanism_svg = tspans(wrap(draw, plan["bounded_mechanism"], font(30, True), 850, 3), 115, 38)
    limitation_svg = tspans(wrap(draw, plan["limitation"], font(25), 850, 3), 115, 32)
    cta_svg = tspans(wrap(draw, plan["cta"], font(30, True), 850, 2), 115, 40)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350">
<title>{html.escape(plan['video_id'])} editable static companion</title>
<g id="base-layer" data-layer-role="base" data-editable="true"><rect width="1080" height="1350" fill="{palette['bg']}"/></g>
<g id="overlay-layer" data-layer-role="overlay" data-editable="true">
  <rect id="header-rule" x="70" y="118" width="940" height="5" fill="{palette['accent2']}"/>
  <text id="header-label" x="70" y="92" fill="{palette['muted']}" font-family="Arial" font-size="22" font-weight="700">ARCHFLOW / {html.escape(plan['video_id'])} / STATIC COMPANION</text>
  <text id="title" x="70" y="230" fill="{palette['ink']}" font-family="Arial" font-size="56" font-weight="700">{title_svg}</text>
</g>
<g id="content-card-layer" data-layer-role="ui" data-editable="true">
  <rect id="content-card" x="70" y="440" width="940" height="560" rx="36" fill="{palette['bg2']}" stroke="{palette['accent']}"/>
  <text id="problem-label" x="115" y="520" fill="{palette['accent2']}" font-family="Arial" font-size="22" font-weight="700">PROBLEM</text>
  <text id="problem-copy" x="115" y="585" fill="{palette['ink']}" font-family="Arial" font-size="30">{problem_svg}</text>
  <text id="mechanism-label" x="115" y="720" fill="{palette['good']}" font-family="Arial" font-size="22" font-weight="700">BOUNDED MECHANISM</text>
  <text id="mechanism-copy" x="115" y="785" fill="{palette['ink']}" font-family="Arial" font-size="30" font-weight="700">{mechanism_svg}</text>
  <text id="limitation-label" x="115" y="900" fill="{palette['warn']}" font-family="Arial" font-size="22" font-weight="700">LIMIT</text>
  <text id="limitation-copy" x="115" y="945" fill="{palette['muted']}" font-family="Arial" font-size="25">{limitation_svg}</text>
</g>
<g id="cta-layer" data-layer-role="overlay" data-editable="true">
  <rect id="cta-card" x="70" y="1070" width="940" height="165" rx="34" fill="{palette['accent']}"/>
  <text id="cta-copy" x="115" y="1140" fill="{palette['ink']}" font-family="Arial" font-size="30" font-weight="700">{cta_svg}</text>
</g>
<g id="annotation-layer" data-layer-role="annotation" data-editable="true"><text id="owner-state" x="70" y="1290" fill="{palette['muted']}" font-family="Arial" font-size="20">OWNER_REVIEW_PENDING / EDITABLE SVG SOURCE</text></g>
</svg>'''
    svg_path.write_text(svg, encoding="utf-8")
    return png_path, svg_path


def candidate_archive(plan: dict) -> dict:
    path = CANDIDATE_ROOT / plan["video_id"] / "candidate.json"
    return read_json(path) if path.exists() else {}


def evidence_details(plan: dict) -> list[dict]:
    details: list[dict] = []
    for evidence_id in plan["evidence_ids"]:
        source_id = evidence_id.removeprefix("EV-")
        record = SOURCE_RECORD_ROOT / f"{source_id}.json"
        rights = RIGHTS_ROOT / f"{source_id}.json"
        rights_payload = read_json(rights) if rights.exists() else {}
        if record.exists():
            payload = read_json(record)
            details.append({
                "evidence_id": evidence_id,
                "source_id": source_id,
                "url": payload.get("canonical_url"),
                "date": payload.get("published_at") or "undated",
                "checked_at": payload.get("checked_at") or "unavailable",
                "claim_state": f"{payload.get('claim_label', 'GAP')} / {rights_payload.get('rights_state', 'unknown')}",
                "limitations": payload.get("limitations", []) + [
                    "Metadata/provenance registration is not source-body evidence, a current social trend, or a performance result."
                ],
            })
        else:
            card_path = EVIDENCE_CARD_ROOT / f"{source_id}.json"
            card = read_json(card_path) if card_path.exists() else {}
            details.append({
                "evidence_id": evidence_id,
                "source_id": source_id,
                "url": f"https://archflow.local/content-engine/evidence/{source_id}",
                "date": card.get("freshness_state", "unknown"),
                "checked_at": "checksum-bound in the Phase 1 evidence registry",
                "claim_state": f"{card.get('evidence_label', 'FACT')} / {rights_payload.get('rights_state', 'facts_only')}",
                "limitations": card.get("channel_limits", [
                    "Local checksum-bound context only; not external market proof."
                ]),
            })
    return details


def source_rows(plan: dict) -> list[list[str]]:
    rows: list[list[str]] = [["Evidence ID", "URL / date / claim state / limitations"]]
    for item in evidence_details(plan):
        limitations = "; ".join(item["limitations"][:3])
        rows.append([
            item["evidence_id"],
            f"{item['url']} | date: {item['date']} | checked: {item['checked_at']} | claim: {item['claim_state']} | limits: {limitations}",
        ])
    return rows


def md_report(plan: dict, sequence: dict, contact_path: Path, plan_hash: str, sequence_hash: str) -> str:
    frames = sequence["frames"]
    archive = candidate_archive(plan)
    concepts = archive.get("concept_ideas", [])
    production = archive.get("production_spec", {})
    continuity_bible = production.get("continuity_bible", {})
    audio_plan = production.get("audio_plan", {})
    screen_plan = production.get("screen_recording_plan", {})
    judges = "\n".join(f"- {v['judge_role']}: {v['score']}/100 - {v['verdict']}" for v in plan["judge_verdicts"])
    evidence = "\n".join(
        f"- `{item['evidence_id']}` / `{item['source_id']}` — [{item['url']}]({item['url']}); date: {item['date']}; checked: {item['checked_at']}; claim state: {item['claim_state']}; limitations: {'; '.join(item['limitations'][:3])}"
        for item in evidence_details(plan)
    )
    concept_text = "\n".join(
        f"- `{item['concept_id']}` **{item['name']}** — hook: {item['hook']} Device: {item['story_device']} Distinctness: {item['distinctness']} Feasibility: {item['production_feasibility']}"
        for item in concepts
    ) or "- No separate alternative archive was available; see the frozen v1 prompt."
    plot_text = "\n".join(f"{idx}. {beat}" for idx, beat in enumerate(archive.get("full_original_plot", []), 1))
    continuity_text = "\n".join(f"- {key}: {value}" for key, value in continuity_bible.items()) or "- Continuity is defined by each frame's continuity IDs and acceptance checks."
    asset_text = "\n\n".join(
        f"### {frame['frame_id']}\n\n- Base: {frame['base_plate_prompt']}\n- Subject: {frame.get('subject_plate_prompt') or 'not applicable; no human/subject plate'}\n- Overlays: {'; '.join(frame['overlay_asset_prompts'])}\n- Composite: {frame['combined_composite_description']}\n- Motion/camera: {frame['camera_and_motion']}\n- Continuity: {'; '.join(frame['continuity_ids'])}\n- Negatives: {'; '.join(frame['negative_constraints'])}\n- Fallback: {frame['fallback']}"
        for frame in frames
    )
    screen_frames = [frame for frame in frames if frame["composition_type"] == "screen_capture"]
    screen_units = screen_frames or frames[:1]
    screen_text = "\n".join(
        f"- `{frame['frame_id']}` — route/mock screen: local synthetic `/mock/{plan['video_id'].lower()}/{frame['frame_id'].lower()}` (offline namespace, not a live URL); viewport: 1080×1920 with 8% horizontal and 10% vertical safe zones; device scale: 1.0; cursor path: center → primary state card → evidence/status chip → CTA, planned only; clicks: none; typing: none; pauses: 250 ms at the primary state and 250 ms at the evidence/status chip; zooms: none; duration: {(frame['end_ms']-frame['start_ms'])/1000:.1f}s at {frame['start_ms']/1000:.1f}–{frame['end_ms']/1000:.1f}s; fixture/build version: `archflow-synthetic-fixture-v1` / `provider-disabled-build-20260811`; data: synthetic labels/values only; privacy/redaction: no customer, property, account, credential, private URL, notification, or unrelated window; replace any accidental identifier with `SYNTHETIC` before export; execution truth: `NOT_RUN`."
        for frame in screen_units
    )
    audio_cues = "\n".join(
        f"- `{frame['frame_id']}` dialogue: {frame['narration']} Caption: {frame['on_screen_text']} Music stem: {frame['music_cue']} SFX stem: {frame['sfx_cue']}"
        for frame in frames
    )
    assembly = "\n".join(
        f"- {frame['sequence_number']:02d}. `{frame['frame_id']}` {frame['start_ms']/1000:.1f}–{frame['end_ms']/1000:.1f}s; in: {frame['transition_in']}; out: {frame['transition_out']}."
        for frame in frames
    )
    frame_table = [
        "| Frame | Time | Function | Composition and layers | Dialogue and on-screen text | Transitions and audio | Prompts, negatives, and acceptance |",
        "|---|---:|---|---|---|---|---|",
    ]
    for frame in frames:
        subject = frame.get("subject_plate_prompt") or "not applicable"
        frame_table.append(
            f"| {frame['frame_id']} | {frame['start_ms']/1000:.1f}-{frame['end_ms']/1000:.1f}s | {frame['story_function']} | {frame['composition_type']}; base: {frame['base_plate_prompt']}; subject: {subject}; overlays: {'; '.join(frame['overlay_asset_prompts'])}; composite: {frame['combined_composite_description']} | Narration: {frame['narration']}; on-screen: {frame['on_screen_text']} | In: {frame['transition_in']}; out: {frame['transition_out']}; music: {frame['music_cue']}; SFX: {frame['sfx_cue']} | Negatives: {'; '.join(frame['negative_constraints'])}; acceptance: {'; '.join(frame['acceptance_checks'])} |"
        )
    iterations = plan["prompt_iterations"]
    content = [
        f"# {plan['video_id']} - {plan['title']}",
        "",
        "## 1. cover_and_truth_state",
        "",
        f"Campaign/content pillar: `{plan['campaign_domain']}`. Audience: {plan['audience']}. Primary channel: `{plan['primary_channel']}`. Candidate version: v3 / `{plan['candidate_set_hash']}`. Storyboard: `{sequence['storyboard_asset_state']}`. External provider generation: `NOT_RUN`. Owner state: `OWNER_REVIEW_PENDING`.",
        "",
        "## 2. audience_problem_pain_consequence_mechanism_limitation_cta",
        "",
        f"- Forcing moment: {frames[0]['narration']}\n- Audience: {plan['audience']}\n- Problem: {plan['problem']}\n- Pain: {plan['pain']}\n- Consequence: {plan['operating_consequence']}\n- Bounded mechanism/tool: {plan['bounded_mechanism']}\n- Limitation: {plan['limitation']}\n- CTA: {plan['cta']}",
        "",
        "## 3. source_ledger_and_claim_map",
        "",
        evidence,
        "",
        "All sources remain subject to their recorded rights and truth-state limits. Registration or vendor publication does not prove ArchFlow readiness, market performance, or a live integration.",
        "",
        "## 4. pattern_abstractions_and_clean_room_restrictions",
        "",
        "Usable abstractions:\n" + "\n".join(f"- {x}" for x in plan["reference_abstractions"]),
        "",
        "Prohibited similarities:\n" + "\n".join(f"- {x}" for x in plan["prohibited_similarities"]),
        "",
        "## 5. concept_v1_and_critique",
        "",
        "Base concept prompt:\n\n" + iterations[0]["prompt"] + "\n\nAlternatives:\n\n" + concept_text + "\n\nCritique:\n" + "\n".join(f"- {x}" for x in iterations[0]["critic_notes"]) + f"\n\nRevision applied: selected `{archive.get('selected_concept_id', 'recorded in v1')}` because {archive.get('selection_reason', 'it best met the bounded viewer job and feasibility constraints')}.",
        "",
        "## 6. story_v2_and_beat_sheet",
        "",
        "Story prompt:\n\n" + iterations[1]["prompt"] + "\n\nFull original plot:\n\n" + plot_text + "\n\nNarration and beat/time budget:\n\n" + "\n".join(f"- {f['frame_id']} / {f['start_ms']/1000:.1f}–{f['end_ms']/1000:.1f}s / {f['story_function']}: {f['narration']}" for f in frames) + "\n\nV2 critic notes:\n" + "\n".join(f"- {x}" for x in iterations[1]["critic_notes"]),
        "",
        "## 7. production_prompt_v3",
        "",
        iterations[2]["prompt"] + "\n\nNegative constraints:\n" + "\n".join(f"- {x}" for x in sorted({item for frame in frames for item in frame['negative_constraints']})) + "\n\nContinuity bible:\n" + continuity_text + "\n\nProvider-neutral instruction: these prompts describe local storyboard planning only. External image, video, voice, music, publishing, analytics, and deployment execution remain `NOT_RUN`.",
        "",
        "## 8. candidate_set_hash_and_judge_verdicts",
        "",
        f"Candidate set: `{plan['candidate_set_hash']}`\n\n{judges}",
        "",
        "## 9. timecoded_frame_table",
        "",
        "\n".join(frame_table),
        "",
        "## 10. contact_sheet",
        "",
        f"![{plan['video_id']} sequence board]({contact_path.name})\n\nCurrent contact-sheet SHA-256: `sha256:{sha256(contact_path)}`. The board is generated from the exact ordered frame manifest in `frame-sequence.json`.",
        "",
        "## 11. asset_prompts_negatives_continuity_fallbacks",
        "",
        asset_text,
        "",
        "## 12. screen_recording_plan",
        "",
        f"Batch screen policy: {screen_plan.get('state', 'PLANNED_LOCAL_SYNTHETIC_ONLY')}; execution: NOT_RUN; route: {screen_plan.get('route', 'deterministic local mock only')}; viewport: {screen_plan.get('viewport', '1080x1920')}; device scale: 1.0; fixture/build: archflow-synthetic-fixture-v1 / provider-disabled-build-20260811; privacy: {screen_plan.get('privacy', 'synthetic data only')}.\n\n{screen_text}",
        "",
        "## 13. narration_captions_music_ambience_sfx",
        "",
        f"Dialogue/narration stem: {audio_plan.get('narration', 'Timing text only; future neutral voice requires approval.')}\n\nCaption stem: editable high-contrast captions derived from the exact transcript below; two lines maximum, meaning never conveyed by color alone.\n\nMusic stem: {audio_plan.get('music', 'Optional future bed; NOT RUN.')}\n\nAmbience stem: {audio_plan.get('ambience', 'None required.')}\n\nSFX stem: {audio_plan.get('sfx', 'Cue plan only; NOT RUN.')}\n\nVoice/likeness: {audio_plan.get('voice_or_likeness', 'NOT RUN.')}\n\nFrame cue sheet:\n{audio_cues}\n\nExact timing transcript:\n\n{plan['platform_copy']['transcript']}",
        "",
        "## 14. edit_timeline_transitions_platform_variants",
        "",
        f"Assembly order (native deterministic renderer; OpenMontage is a future candidate worker and was not installed or executed):\n\n{assembly}\n\nCaptions are assembled after overlays and before the truth footer. Master: 1080×1920 / {sequence['aspect_ratio']} / {sequence['target_duration_ms']/1000:.0f}s. Recompose 4:5 by protecting the center 864 px; recompose 1:1 with one state per card; 16:9 uses a centered vertical preview plus evidence rail. Preserve claim limits and editable text in every variant.",
        "",
        "## 15. candidate_provider_model_routing",
        "",
        "Future candidate routes (planning only): local/Codex still-image assistance for approved base plates; an owner-selected image-to-video renderer for continuity; an owner-approved non-imitative narration route; a rights-cleared music/SFX library; OpenMontage or a native local editor for assembly. External image, video, voice, music, montage, publishing, analytics, Figma mutation, and deployment execution are all `NOT_RUN`. Before any call: freeze the frame manifest, specify exact data transmitted, verify source/reference rights, consent and retention, obtain vendor/model terms and dated capability proof, set a per-job budget/cost ceiling, and record owner approval plus a fallback. Current provider, model, price, credential, target, budget, and retention choices are `GAP`.",
        "",
        "## 16. rights_consent_accessibility_qa_cost_approvals_fallback",
        "",
        f"Rights: source-specific decisions only; local context is facts-only and not market proof. Consent: no real person, voice, likeness, customer asset, private media, property/account data, or production system. Accessibility: editable captions, non-color status labels, contrast checks, alt text, safe zones, and reduced-motion still fallback. QA: schema/timing/image/PDF/hash/secret/private-data/originality checks plus independent Sight review. Cost: Phase 1 paid-provider execution is zero; future cost is GAP pending an exact budget packet. Approvals: external providers, voice/likeness, Figma mutation, publishing, deployment, and Git write all remain unapproved/NOT RUN. Current maker/reviewer state: {sequence['review']['maker']} / {sequence['review']['reviewer']} / {sequence['review']['verdict']}. Checksum IDs: evidence review `sha256:{EVIDENCE_REVIEW_SHA256}`; base-plate provenance manifest `sha256:{BASE_PLATE_MANIFEST_SHA256}`; candidate set `{plan['candidate_set_hash']}`; content plan `sha256:{plan_hash}`; frame sequence `sha256:{sequence_hash}`; contact sheet `sha256:{sha256(contact_path)}`. Fallback: deterministic local vector frames, still dissolves, editable captions, and no external action.",
        "",
        "## 17. platform_copy_transcript_alt_text",
        "",
        f"### Cover/title\n\n{plan['title']}\n\n### LinkedIn\n\n{plan['platform_copy']['linkedin']}\n\n### Reels\n\n{plan['platform_copy']['reels']}\n\n### Threads\n\n{plan['platform_copy']['threads']}\n\n### X\n\n{plan['platform_copy']['x']}\n\n### Transcript\n\n{plan['platform_copy']['transcript']}\n\n### Alt text\n\n{plan['platform_copy']['alt_text']}",
        "",
    ]
    return "\n".join(content)


def register_pdf_fonts() -> tuple[str, str]:
    if FONT_REGULAR.exists() and FONT_BOLD.exists():
        pdfmetrics.registerFont(TTFont("ArchflowArial", str(FONT_REGULAR)))
        pdfmetrics.registerFont(TTFont("ArchflowArial-Bold", str(FONT_BOLD)))
        return "ArchflowArial", "ArchflowArial-Bold"
    return "Helvetica", "Helvetica-Bold"


def wrapped_identifier_markup(value: str, line_limit: int = 24) -> str:
    """Wrap a hyphenated stable ID without dropping or replacing any character."""
    parts = [match.group(0) for match in re.finditer(r"[^-]+-?", value)]
    lines: list[str] = []
    current = ""
    for part in parts:
        if current and len(current + part) > line_limit:
            lines.append(current)
            current = part
        else:
            current += part
    if current:
        lines.append(current)
    if "".join(lines) != value:
        raise ValueError(f"identifier wrap changed bytes: {value}")
    return "<br/>".join(html.escape(line) for line in lines)


def build_pdf(pdf_path: Path, plan: dict, sequence: dict, contact_path: Path, plan_hash: str, sequence_hash: str) -> None:
    regular, bold = register_pdf_fonts()
    palette = PALETTES[plan["campaign_domain"]]
    archive = candidate_archive(plan)
    concepts = archive.get("concept_ideas", [])
    production = archive.get("production_spec", {})
    continuity_bible = production.get("continuity_bible", {})
    audio_plan = production.get("audio_plan", {})
    screen_plan = production.get("screen_recording_plan", {})
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="AFTitle", parent=styles["Title"], fontName=bold, fontSize=24, leading=29, textColor=colors.HexColor(palette["bg"]), spaceAfter=8))
    styles.add(ParagraphStyle(name="AFH1", parent=styles["Heading1"], fontName=bold, fontSize=15, leading=19, textColor=colors.HexColor(palette["accent"]), spaceBefore=10, spaceAfter=7))
    styles.add(ParagraphStyle(name="AFBody", parent=styles["BodyText"], fontName=regular, fontSize=8.7, leading=12.2, textColor=colors.HexColor("#172033"), spaceAfter=5))
    styles.add(ParagraphStyle(name="AFSmall", parent=styles["BodyText"], fontName=regular, fontSize=7.2, leading=9.4, textColor=colors.HexColor("#3A465C")))
    styles.add(ParagraphStyle(name="AFCover", parent=styles["Title"], fontName=bold, fontSize=34, leading=39, alignment=TA_LEFT, textColor=colors.HexColor(palette["ink"])))
    styles.add(ParagraphStyle(name="AFCoverMeta", parent=styles["BodyText"], fontName=regular, fontSize=11, leading=16, textColor=colors.HexColor(palette["muted"])))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(regular, 7)
        canvas.setFillColor(colors.HexColor("#68748B"))
        canvas.drawString(18 * mm, 10 * mm, f"ArchFlow Phase 1 / {plan['video_id']} / OWNER_REVIEW_PENDING")
        canvas.drawRightString(192 * mm, 10 * mm, f"{doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=15 * mm,
        bottomMargin=16 * mm,
        title=f"{plan['video_id']} - {plan['title']}",
        author="ArchFlow Content Engine",
        initialFontName=regular,
        initialFontSize=7,
        initialLeading=9,
    )
    story = []
    story.append(Table([[Paragraph("ARCHFLOW / PHASE 1 PREVISUALIZATION", styles["AFCoverMeta"])], [Paragraph(html.escape(plan["title"]), styles["AFCover"])]],
                       colWidths=[178 * mm], rowHeights=[18 * mm, 78 * mm], style=TableStyle([
                           ("FONTNAME", (0, 0), (-1, -1), regular),
                           ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(palette["bg"])),
                           ("BOX", (0, 0), (-1, -1), 0, colors.HexColor(palette["bg"])),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10 * mm),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 10 * mm),
                           ("TOPPADDING", (0, 0), (-1, -1), 8 * mm),
                       ])))
    story.append(Spacer(1, 6 * mm))

    def heading(index: int) -> None:
        story.append(Paragraph(f"{index}. {PDF_SECTIONS[index - 1]}", styles["AFH1"]))

    heading(1)
    story.append(Paragraph(f"Video <b>{plan['video_id']}</b> · content pillar <b>{plan['campaign_domain']}</b> · audience <b>{html.escape(plan['audience'])}</b> · primary channel <b>{plan['primary_channel']}</b> · candidate version <b>v3</b> / {html.escape(plan['candidate_set_hash'])} · {sequence['target_duration_ms']/1000:.0f}s · {sequence['aspect_ratio']} · storyboard <b>{sequence['storyboard_asset_state']}</b> · external provider <b>NOT_RUN</b> · owner <b>OWNER_REVIEW_PENDING</b>.", styles["AFBody"]))
    heading(2)
    facts = [["Forcing moment", sequence["frames"][0]["narration"]], ["Audience", plan["audience"]], ["Problem", plan["problem"]], ["Pain", plan["pain"]], ["Consequence", plan["operating_consequence"]], ["Bounded mechanism/tool", plan["bounded_mechanism"]], ["Limitation", plan["limitation"]], ["CTA", plan["cta"]]]
    story.append(Table([[Paragraph(f"<b>{html.escape(a)}</b>", styles["AFSmall"]), Paragraph(html.escape(b), styles["AFSmall"])] for a, b in facts], colWidths=[36 * mm, 142 * mm], style=TableStyle([("FONTNAME", (0, 0), (-1, -1), regular), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#D8DEEA")), ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F0F3F8")), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)])))
    heading(3)
    src_cells = [[Paragraph("<b>Evidence ID</b>", styles["AFSmall"]), Paragraph("<b>URL / date / claim state / limitations</b>", styles["AFSmall"])]]
    for item in evidence_details(plan):
        url = item["url"]
        limitations = "; ".join(item["limitations"][:3])
        target_cell = Paragraph(
            f'<link href="{html.escape(url)}" color="#{palette["accent"].lstrip("#")}">{html.escape(url)}</link><br/>'
            f'date: {html.escape(str(item["date"]))}; checked: {html.escape(str(item["checked_at"]))}; claim: {html.escape(item["claim_state"])}<br/>'
            f'limits: {html.escape(limitations)}',
            styles["AFSmall"],
        )
        src_cells.append([Paragraph(wrapped_identifier_markup(item["evidence_id"]), styles["AFSmall"]), target_cell])
    story.append(LongTable(src_cells, colWidths=[62 * mm, 116 * mm], repeatRows=1, style=TableStyle([("FONTNAME", (0, 0), (-1, -1), regular), ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#D8DEEA")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(palette["bg2"])), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("VALIGN", (0, 0), (-1, -1), "TOP")])))
    story.append(Paragraph("Registration and vendor publication do not prove ArchFlow readiness, market performance, a live integration, or a current social trend.", styles["AFSmall"]))
    heading(4)
    story.append(Paragraph("<b>Reference abstractions:</b> " + html.escape("; ".join(plan["reference_abstractions"])), styles["AFBody"]))
    story.append(Paragraph("<b>Prohibited similarities:</b> " + html.escape("; ".join(plan["prohibited_similarities"])), styles["AFBody"]))
    heading(5)
    story.append(Paragraph("<b>Base concept prompt:</b> " + html.escape(plan["prompt_iterations"][0]["prompt"]), styles["AFBody"]))
    for item in concepts:
        story.append(Paragraph(f"<b>{html.escape(item['concept_id'])} / {html.escape(item['name'])}</b> — hook: {html.escape(item['hook'])}; device: {html.escape(item['story_device'])}; distinctness: {html.escape(item['distinctness'])}; feasibility: {html.escape(item['production_feasibility'])}.", styles["AFSmall"]))
    story.append(Paragraph("<b>Critique:</b> " + html.escape("; ".join(plan["prompt_iterations"][0]["critic_notes"])), styles["AFSmall"]))
    story.append(Paragraph(f"<b>Revision applied:</b> selected {html.escape(archive.get('selected_concept_id', 'the recorded concept'))} because {html.escape(archive.get('selection_reason', 'it best met the bounded viewer job and feasibility constraints'))}.", styles["AFSmall"]))
    heading(6)
    story.append(Paragraph(html.escape(plan["prompt_iterations"][1]["prompt"]), styles["AFBody"]))
    if archive.get("full_original_plot"):
        story.append(Paragraph("<b>Full plot:</b> " + html.escape(" → ".join(archive["full_original_plot"])), styles["AFSmall"]))
    beat_rows = [[Paragraph("Beat/time", styles["AFSmall"]), Paragraph("Function / narration", styles["AFSmall"])]] + [[Paragraph(f"{f['frame_id']}<br/>{f['start_ms']/1000:.1f}-{f['end_ms']/1000:.1f}s", styles["AFSmall"]), Paragraph(html.escape(f["story_function"] + " / " + f["narration"]), styles["AFSmall"])] for f in sequence["frames"]]
    story.append(Table(beat_rows, colWidths=[34 * mm, 144 * mm], style=TableStyle([("FONTNAME", (0, 0), (-1, -1), regular), ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#D8DEEA")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F7"))])))
    story.append(Paragraph("<b>V2 critic notes:</b> " + html.escape("; ".join(plan["prompt_iterations"][1]["critic_notes"])), styles["AFSmall"]))
    heading(7)
    story.append(Paragraph(html.escape(plan["prompt_iterations"][2]["prompt"]), styles["AFBody"]))
    all_negatives = sorted({item for frame in sequence["frames"] for item in frame["negative_constraints"]})
    story.append(Paragraph("<b>Negative constraints:</b> " + html.escape("; ".join(all_negatives)), styles["AFSmall"]))
    story.append(Paragraph("<b>Continuity bible:</b> " + html.escape("; ".join(f"{key}: {value}" for key, value in continuity_bible.items())), styles["AFSmall"]))
    story.append(Paragraph("<b>Provider-neutral instruction:</b> local storyboard planning only; external image, video, voice, music, montage, publishing, analytics, Figma mutation, and deployment execution remain NOT_RUN.", styles["AFSmall"]))
    heading(8)
    story.append(Paragraph(f"<b>{html.escape(plan['candidate_set_hash'])}</b>", styles["AFBody"]))
    judge_rows = [["Judge", "Score", "Verdict"]] + [[v["judge_role"], str(v["score"]), v["verdict"]] for v in plan["judge_verdicts"]]
    story.append(Table(judge_rows, colWidths=[90 * mm, 32 * mm, 56 * mm], style=TableStyle([("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#D8DEEA")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F7")), ("FONTNAME", (0, 0), (-1, 0), bold), ("FONTNAME", (0, 1), (-1, -1), regular), ("FONTSIZE", (0, 0), (-1, -1), 8)])))
    heading(9)
    frame_rows = [[
        Paragraph("Frame / time", styles["AFSmall"]),
        Paragraph("Function / composition / layers", styles["AFSmall"]),
        Paragraph("Dialogue / text / transition / audio", styles["AFSmall"]),
        Paragraph("Prompts / negatives / acceptance", styles["AFSmall"]),
    ]]
    for f in sequence["frames"]:
        subject = f.get("subject_plate_prompt") or "not applicable"
        frame_rows.append([
            Paragraph(f"{f['frame_id']}<br/>{f['start_ms']/1000:.1f}-{f['end_ms']/1000:.1f}s", styles["AFSmall"]),
            Paragraph(html.escape(f"{f['story_function']} / {f['composition_type']} / base: {f['base_plate_prompt']} / subject: {subject} / overlays: {'; '.join(f['overlay_asset_prompts'])} / composite: {f['combined_composite_description']}"), styles["AFSmall"]),
            Paragraph(html.escape(f"Narration: {f['narration']} / on-screen: {f['on_screen_text']} / in: {f['transition_in']} / out: {f['transition_out']} / music: {f['music_cue']} / SFX: {f['sfx_cue']}"), styles["AFSmall"]),
            Paragraph(html.escape(f"Negatives: {'; '.join(f['negative_constraints'])} / acceptance: {'; '.join(f['acceptance_checks'])}"), styles["AFSmall"]),
        ])
    story.append(LongTable(frame_rows, colWidths=[24 * mm, 53 * mm, 50 * mm, 51 * mm], repeatRows=1, style=TableStyle([("FONTNAME", (0, 0), (-1, -1), regular), ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#D8DEEA")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F7")), ("VALIGN", (0, 0), (-1, -1), "TOP")])))
    story.append(PageBreak())
    heading(10)
    image = RLImage(str(contact_path))
    image._restrictSize(178 * mm, 230 * mm)
    story.append(image)
    story.append(Paragraph(f"Current contact-sheet manifest hash: <b>sha256:{sha256(contact_path)}</b>. Tile order is the exact frame-manifest order.", styles["AFSmall"]))
    heading(11)
    for f in sequence["frames"]:
        subject = f.get("subject_plate_prompt") or "not applicable; no human/subject plate"
        story.append(KeepTogether([
            Paragraph(f"<b>{f['frame_id']}</b> · base: {html.escape(f['base_plate_prompt'])}", styles["AFSmall"]),
            Paragraph("Subject: " + html.escape(subject) + " · Overlays: " + html.escape("; ".join(f["overlay_asset_prompts"])) + " · Composite: " + html.escape(f["combined_composite_description"]), styles["AFSmall"]),
            Paragraph("Motion/camera: " + html.escape(f["camera_and_motion"]) + " · Continuity: " + html.escape("; ".join(f["continuity_ids"])) + " · Negatives: " + html.escape("; ".join(f["negative_constraints"])) + " · Fallback: " + html.escape(f["fallback"]), styles["AFSmall"]),
        ]))
    heading(12)
    story.append(Paragraph(f"State: {html.escape(screen_plan.get('state', 'PLANNED_LOCAL_SYNTHETIC_ONLY'))}; execution: NOT_RUN; route: {html.escape(screen_plan.get('route', 'deterministic local mock only'))}; viewport: {html.escape(screen_plan.get('viewport', '1080x1920'))}; device scale: 1.0; fixture/build version: archflow-synthetic-fixture-v1 / provider-disabled-build-20260811; privacy: {html.escape(screen_plan.get('privacy', 'synthetic data only'))}.", styles["AFBody"]))
    screen_frames = [f for f in sequence["frames"] if f["composition_type"] == "screen_capture"] or sequence["frames"][:1]
    for f in screen_frames:
        story.append(Paragraph(f"<b>{f['frame_id']}</b> — route/mock screen: local synthetic /mock/{plan['video_id'].lower()}/{f['frame_id'].lower()} (offline namespace, not a live URL); viewport: 1080x1920 with 8% horizontal and 10% vertical safe zones; device scale: 1.0; cursor path: center → primary state card → evidence/status chip → CTA, planned only; clicks: none; typing: none; pauses: 250 ms at the primary state and 250 ms at the evidence/status chip; zooms: none; duration: {(f['end_ms']-f['start_ms'])/1000:.1f}s at {f['start_ms']/1000:.1f}-{f['end_ms']/1000:.1f}s; fixture/build version: archflow-synthetic-fixture-v1 / provider-disabled-build-20260811; data: synthetic labels/values only; privacy/redaction: no customer, property, account, credential, private URL, notification, or unrelated window; replace any accidental identifier with SYNTHETIC before export; execution truth: NOT_RUN.", styles["AFSmall"]))
    heading(13)
    story.append(Paragraph(f"<b>Dialogue/narration stem:</b> {html.escape(audio_plan.get('narration', 'Timing text only; future neutral voice requires approval.'))}<br/><b>Caption stem:</b> editable high-contrast captions from the exact transcript; two lines maximum.<br/><b>Music stem:</b> {html.escape(audio_plan.get('music', 'Optional future bed; NOT RUN.'))}<br/><b>Ambience stem:</b> {html.escape(audio_plan.get('ambience', 'None required.'))}<br/><b>SFX stem:</b> {html.escape(audio_plan.get('sfx', 'Cue plan only; NOT RUN.'))}<br/><b>Voice/likeness:</b> {html.escape(audio_plan.get('voice_or_likeness', 'NOT RUN.'))}", styles["AFBody"]))
    for f in sequence["frames"]:
        story.append(Paragraph(f"<b>{f['frame_id']}</b> dialogue: {html.escape(f['narration'])}; caption: {html.escape(f['on_screen_text'])}; music: {html.escape(f['music_cue'])}; SFX: {html.escape(f['sfx_cue'])}.", styles["AFSmall"]))
    story.append(Paragraph("<b>Exact transcript:</b> " + html.escape(plan["platform_copy"]["transcript"]), styles["AFSmall"]))
    heading(14)
    story.append(Paragraph(f"Native deterministic renderer assembly; OpenMontage is a future candidate worker and was not installed or executed. The {sequence['target_duration_ms']/1000:.0f}-second timeline is contiguous and non-overlapping. Captions assemble after overlays and before the truth footer. Master: 1080x1920 / {sequence['aspect_ratio']}. Recompose 4:5 by protecting the center 864 px; recompose 1:1 with one state per card; 16:9 uses a centered vertical preview plus evidence rail.", styles["AFBody"]))
    for f in sequence["frames"]:
        story.append(Paragraph(f"{f['sequence_number']:02d}. <b>{f['frame_id']}</b> {f['start_ms']/1000:.1f}-{f['end_ms']/1000:.1f}s; in: {html.escape(f['transition_in'])}; out: {html.escape(f['transition_out'])}.", styles["AFSmall"]))
    heading(15)
    story.append(Paragraph("Future candidate routes: local/Codex still-image assistance for approved base plates; owner-selected image-to-video continuity; owner-approved non-imitative narration; rights-cleared music/SFX; OpenMontage or native local assembly. External image, video, voice, music, montage, Figma mutation, publishing, analytics, and deployment are all <b>NOT_RUN</b>. Required before any call: exact transmitted data, source/reference rights, consent/retention, dated capability proof, model/vendor terms, per-job budget/cost ceiling, owner approval, and fallback. Current provider, model, price, credential, target, budget, and retention choices are GAP.", styles["AFBody"]))
    heading(16)
    story.append(Paragraph(f"Rights: source-specific decisions only; local context is facts-only and not market proof. Consent: no real person, voice, likeness, customer asset, private media, property/account data, or production system. Accessibility: editable captions, non-color labels, contrast, alt text, safe zones, reduced-motion still fallback. QA: schema/timing/image/PDF/hash/secret/private-data/originality checks plus independent Sight review. Cost: Phase 1 paid-provider execution is zero; future cost is GAP. Approvals: providers, voice/likeness, Figma mutation, publishing, deployment, and Git write remain unapproved/NOT RUN. Review: {html.escape(sequence['review']['maker'])} / {html.escape(sequence['review']['reviewer'])} / {html.escape(sequence['review']['verdict'])}. Checksums: evidence review sha256:{EVIDENCE_REVIEW_SHA256}; base-plate provenance manifest sha256:{BASE_PLATE_MANIFEST_SHA256}; candidate {html.escape(plan['candidate_set_hash'])}; content plan sha256:{plan_hash}; frame sequence sha256:{sequence_hash}; contact sheet sha256:{sha256(contact_path)}. Fallback: deterministic local vector frames and still dissolves.", styles["AFBody"]))
    heading(17)
    copy_rows = [["Cover/title", plan["title"]], ["LinkedIn", plan["platform_copy"]["linkedin"]], ["Reels", plan["platform_copy"]["reels"]], ["Threads", plan["platform_copy"]["threads"]], ["X", plan["platform_copy"]["x"]], ["Transcript", plan["platform_copy"]["transcript"]], ["Alt text", plan["platform_copy"]["alt_text"]]]
    story.append(LongTable([[Paragraph(f"<b>{html.escape(k)}</b>", styles["AFSmall"]), Paragraph(html.escape(v), styles["AFSmall"])] for k, v in copy_rows], colWidths=[30 * mm, 148 * mm], style=TableStyle([("FONTNAME", (0, 0), (-1, -1), regular), ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#D8DEEA")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2F7"))])))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def render_video(video_dir: Path, base_plate_root: Path | None) -> dict:
    plan_path = video_dir / "content-plan.json"
    sequence_path = video_dir / "frame-sequence.json"
    plan = read_json(plan_path)
    sequence = read_json(sequence_path)
    if plan["video_id"] != sequence["video_id"] or plan["video_id"] != video_dir.name:
        raise ValueError(f"video linkage mismatch in {video_dir}")
    frames = sequence["frames"]
    if not 8 <= len(frames) <= 22:
        raise ValueError(f"frame count out of bounds for {video_dir.name}")
    if frames[0]["start_ms"] != 0 or frames[-1]["end_ms"] != sequence["target_duration_ms"]:
        raise ValueError(f"timeline boundary mismatch for {video_dir.name}")
    for index, frame_data in enumerate(frames):
        if frame_data["sequence_number"] != index + 1:
            raise ValueError(f"sequence number mismatch for {frame_data['frame_id']}")
        if index and frames[index - 1]["end_ms"] != frame_data["start_ms"]:
            raise ValueError(f"timeline gap/overlap at {frame_data['frame_id']}")
        duration_justified = any(check.startswith("FRAME_DURATION_JUSTIFIED:") for check in frame_data["acceptance_checks"])
        if frame_data["end_ms"] - frame_data["start_ms"] > 4000 and not duration_justified:
            raise ValueError(f"unjustified frame over four seconds: {frame_data['frame_id']}")

    base_plate = base_plate_root / f"{plan['video_id']}.png" if base_plate_root else None
    base_plate_manifest = base_plate_root / "base-plate-manifest.json" if base_plate_root else None
    if base_plate_root:
        if not base_plate or not base_plate.exists():
            raise ValueError(f"required base plate missing for {video_dir.name}")
        if not base_plate_manifest or not base_plate_manifest.exists():
            raise ValueError("required base-plate manifest missing")
        if sha256(base_plate_manifest) != BASE_PLATE_MANIFEST_SHA256:
            raise ValueError("base-plate manifest provenance hash mismatch")
    frame_paths, svg_paths = [], []
    for frame_data in frames:
        png_path, svg_path = render_frame(video_dir, plan, sequence, frame_data, base_plate)
        frame_paths.append(png_path)
        svg_paths.append(svg_path)
    contact_path = render_contact_sheet(video_dir, plan, sequence, frame_paths)
    static_path, static_svg_path = render_static_companion(video_dir, plan)
    plan_hash = sha256(plan_path)
    sequence_hash = sha256(sequence_path)
    md_path = video_dir / f"{plan['video_id']}-production-plan.md"
    md_path.write_text(md_report(plan, sequence, contact_path, plan_hash, sequence_hash), encoding="utf-8")
    pdf_path = video_dir / f"{plan['video_id']}-production-plan.pdf"
    build_pdf(pdf_path, plan, sequence, contact_path, plan_hash, sequence_hash)

    frame_entries = [{"frame_id": frame_data["frame_id"], "png_path": rel(frame_path), "png_sha256": sha256(frame_path), "svg_path": rel(svg_path), "svg_sha256": sha256(svg_path)} for frame_data, frame_path, svg_path in zip(frames, frame_paths, svg_paths)]
    manifest = {
        "schema": "content-engine.previsualization-bundle.v1",
        "video_id": plan["video_id"],
        "candidate_set_hash": plan["candidate_set_hash"],
        "content_plan_path": rel(plan_path),
        "content_plan_sha256": plan_hash,
        "frame_sequence_path": rel(sequence_path),
        "frame_sequence_sha256": sequence_hash,
        "base_plate_path": rel(base_plate) if base_plate else None,
        "base_plate_sha256": sha256(base_plate) if base_plate else None,
        "base_plate_manifest_path": rel(base_plate_manifest) if base_plate_manifest else None,
        "base_plate_manifest_sha256": sha256(base_plate_manifest) if base_plate_manifest else None,
        "target_duration_ms": sequence["target_duration_ms"],
        "frame_count": len(frames),
        "frames": frame_entries,
        "contact_sheet_path": rel(contact_path),
        "contact_sheet_sha256": sha256(contact_path),
        "contact_sheet_dimensions": image_dimensions(contact_path),
        "contact_sheet_contract": {
            "channel": plan["primary_channel"],
            "version": "v3",
            "candidate_set_hash": plan["candidate_set_hash"],
            "audience": plan["audience"],
            "pain": plan["pain"],
            "evidence_ids": plan["evidence_ids"],
            "evidence_state": "INDEPENDENT_GATE_APPROVED_WITH_RECORDED_LIMITS",
            "rights_state": "SOURCE_SPECIFIC_PASS_WITH_RECORDED_USE_LIMITS",
            "reviewer": sequence["review"],
            "storyboard_asset_state": sequence["storyboard_asset_state"],
            "tile_fields": ["frame_and_time", "on_screen_cue", "narration_cue", "transition_endpoints_duration_motion", "visual_class", "talking_head_state", "licensed_public_footage_state", "audio_event"],
        },
        "static_companion_path": rel(static_path),
        "static_companion_sha256": sha256(static_path),
        "static_companion_svg_path": rel(static_svg_path),
        "static_companion_svg_sha256": sha256(static_svg_path),
        "figma_editable_layer_groups": ["base-layer", "subject-layer", "ui-layer", "overlay-layer", "caption-layer", "annotation-layer"],
        "production_plan_source_path": rel(md_path),
        "production_plan_source_sha256": sha256(md_path),
        "production_plan_pdf_path": rel(pdf_path),
        "production_plan_pdf_sha256": sha256(pdf_path),
        "storyboard_asset_state": sequence["storyboard_asset_state"],
        "external_provider_generation_state": "NOT_RUN",
        "owner_state": "OWNER_REVIEW_PENDING",
        "review": sequence["review"],
    }
    manifest_path = video_dir / "manifest.json"
    write_json(manifest_path, manifest)
    report_manifest = {
        "report_id": f"PDF-{plan['video_id']}-PHASE1",
        "video_id": plan["video_id"],
        "source_document_path": rel(md_path),
        "pdf_path": rel(pdf_path),
        "sections": PDF_SECTIONS,
        "contact_sheet_manifest_hash": "sha256:" + manifest["contact_sheet_sha256"],
        "selectable_text": True,
        "urls_clickable": True,
        "secret_scan": "PASS",
        "storyboard_asset_state": sequence["storyboard_asset_state"],
        "external_provider_generation_state": "NOT_RUN",
        "owner_state": "OWNER_REVIEW_PENDING",
        "validation_verdict": "PENDING",
        "validation_notes": ["Generated locally; independent PDF/image/schema review still required."],
    }
    write_json(video_dir / "pdf-report-manifest.json", report_manifest)
    return manifest


def render_batch_index(manifests: list[dict]) -> Path:
    width, columns, tile_w, margin, gap = 2560, 4, 590, 60, 27
    rows = math.ceil(len(manifests) / columns)
    canvas = gradient((width, 260 + rows * 990 + 70), "#070D19", "#111B2B")
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.text((60, 42), "ARCHFLOW / PHASE 1 / ALL SEQUENCES", font=font(52, True), fill="#F8FAFF")
    draw.text((60, 116), f"{len(manifests)} owner-review-ready local previsualization packets", font=font(28), fill="#A9B4CF")
    draw.text((60, 170), "EXTERNAL PROVIDER NOT RUN / FIGMA IMPORT PACKAGE LOCAL", font=font(22, True), fill="#35D7FF")
    for idx, manifest in enumerate(manifests):
        row, col = divmod(idx, columns)
        x = margin + col * (tile_w + gap)
        y = 260 + row * 990
        rounded(draw, (x, y, x + tile_w, y + 950), 28, "#FFFFFF0C", "#FFFFFF20", 2)
        board = Image.open(ROOT / manifest["contact_sheet_path"]).convert("RGB")
        board.thumbnail((tile_w - 40, 800), Image.Resampling.LANCZOS)
        canvas.paste(board, (x + 20, y + 20))
        draw.text((x + 24, y + 840), f"{manifest['video_id']} / {manifest['frame_count']} FRAMES", font=font(25, True), fill="#F8FAFF")
        draw.text((x + 24, y + 885), "OWNER_REVIEW_PENDING", font=font(20, True), fill="#FFC857")
    output = PLANS_ROOT / "00-all-sequences-index.png"
    canvas.save(output, format="PNG", optimize=True)
    return output


def write_batch_markdown(manifests: list[dict], index_path: Path) -> Path:
    lines = ["# Phase 1 Previsualization Batch", "", "Status: `OWNER_REVIEW_PENDING`  ", "External provider generation: `NOT_RUN`  ", "Figma: local import package only unless the exact identity/target/write gate passes", "", f"![All sequences index]({index_path.name})", "", "| Video | Frames | Duration | Sequence board | Production PDF | State |", "|---|---:|---:|---|---|---|"]
    for item in manifests:
        video_id = item["video_id"]
        lines.append(f"| {video_id} | {item['frame_count']} | {item['target_duration_ms']/1000:.0f}s | [{video_id} board]({video_id}/{video_id}-sequence-board.png) | [{video_id} PDF]({video_id}/{video_id}-production-plan.pdf) | OWNER_REVIEW_PENDING |")
    lines.extend(["", "All frames and reports are local clean-room previsualization. No final video, voice, music, provider render, publication, deployment, or social write occurred.", ""])
    path = PLANS_ROOT / "00-batch-index.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-plate-root", type=Path, default=None, help="Optional folder containing Vxx.png local generated base plates")
    parser.add_argument("--videos", nargs="*", help="Optional exact Vxx subset")
    args = parser.parse_args()
    video_dirs = sorted(path for path in PLANS_ROOT.glob("V[0-1][0-9]") if path.is_dir())
    if args.videos:
        allowed = set(args.videos)
        video_dirs = [path for path in video_dirs if path.name in allowed]
    if not video_dirs:
        raise SystemExit("No video plan directories found")
    manifests = [render_video(path, args.base_plate_root) for path in video_dirs]
    index_path = render_batch_index(manifests)
    batch_md = write_batch_markdown(manifests, index_path)
    print(json.dumps({"videos": len(manifests), "index": rel(index_path), "index_sha256": sha256(index_path), "batch_markdown": rel(batch_md), "batch_markdown_sha256": sha256(batch_md)}, indent=2))


if __name__ == "__main__":
    main()
