#!/usr/bin/env python3
"""Build the evidence-bound English YouTube market report as a styled PDF."""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from PIL import Image as PILImage, ImageChops, ImageEnhance, ImageOps, ImageStat
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, Image, KeepTogether, NextPageTemplate,
    PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle,
)


INK = colors.HexColor("#101210")
CREAM = colors.HexColor("#F3EEDC")
LIME = colors.HexColor("#C8FF32")
ORANGE = colors.HexColor("#FF6B35")
MINT = colors.HexColor("#73E2C6")
MUTED = colors.HexColor("#64675E")
GRID = colors.HexColor("#CAC3AE")
WHITE = colors.white


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.is_file() else []


def human(value: int | float | None) -> str:
    if value is None:
        return "—"
    value = float(value)
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:.0f}"


def label(value: str) -> str:
    return value.replace("_", " ").title()


def pct(count: int, total: int) -> str:
    return f"{count / total * 100:.1f}%" if total else "—"


def esc(value: Any) -> str:
    return str(value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def words(value: str, limit: int = 24) -> str:
    tokens = value.split()
    return " ".join(tokens[:limit]) + ("…" if len(tokens) > limit else "")


class BarChart(Flowable):
    def __init__(self, rows: list[tuple[str, int]], width: float, title: str, color=LIME, height: float | None = None):
        self.rows = rows
        self.width = width
        self.height = height or (18 * mm + len(rows) * 8 * mm)
        self.title = title
        self.color = color

    def draw(self) -> None:
        c = self.canv
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(0, self.height - 7 * mm, self.title)
        maximum = max((value for _, value in self.rows), default=1)
        y = self.height - 15 * mm
        label_width = self.width * .42
        for name, value in self.rows:
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 7.5)
            c.drawString(0, y + 1.5 * mm, label(name)[:34])
            c.setFillColor(colors.HexColor("#DED7C2"))
            c.rect(label_width, y, self.width - label_width - 15 * mm, 4.4 * mm, fill=1, stroke=0)
            c.setFillColor(self.color)
            c.rect(label_width, y, (self.width - label_width - 15 * mm) * value / maximum, 4.4 * mm, fill=1, stroke=0)
            c.setFillColor(INK)
            c.setFont("Helvetica-Bold", 7.5)
            c.drawRightString(self.width, y + 1.2 * mm, str(value))
            y -= 8 * mm


def on_cover(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(INK)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.setFillColor(LIME)
    canvas.rect(0, A4[1] - 11 * mm, A4[0], 11 * mm, fill=1, stroke=0)
    canvas.restoreState()


def on_body(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(CREAM)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.setStrokeColor(GRID)
    canvas.line(16 * mm, A4[1] - 13 * mm, A4[0] - 16 * mm, A4[1] - 13 * mm)
    canvas.setFont("Helvetica-Bold", 6.8)
    canvas.setFillColor(MUTED)
    canvas.drawString(16 * mm, A4[1] - 9.5 * mm, "NORTH HUX × ARCHFLOW / YOUTUBE AI-AGENT CONTENT INTELLIGENCE")
    canvas.drawRightString(A4[0] - 16 * mm, 9 * mm, f"{doc.page:02d}")
    canvas.restoreState()


def make_styles():
    styles = getSampleStyleSheet()
    return {
        "cover_kicker": ParagraphStyle("cover_kicker", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=LIME, spaceAfter=8 * mm),
        "cover_title": ParagraphStyle("cover_title", fontName="Helvetica-Bold", fontSize=31, leading=31, textColor=CREAM, spaceAfter=7 * mm),
        "cover_sub": ParagraphStyle("cover_sub", fontName="Helvetica", fontSize=12, leading=17, textColor=colors.HexColor("#D5D1C4"), spaceAfter=4 * mm),
        "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=23, leading=25, textColor=INK, spaceAfter=5 * mm, spaceBefore=1 * mm),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=INK, spaceBefore=5 * mm, spaceAfter=3 * mm),
        "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=INK, spaceBefore=3 * mm, spaceAfter=1.5 * mm),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=8.4, leading=12, textColor=INK, spaceAfter=2.5 * mm),
        "small": ParagraphStyle("small", fontName="Helvetica", fontSize=6.7, leading=9, textColor=INK),
        "caption": ParagraphStyle("caption", fontName="Helvetica", fontSize=6.5, leading=8, textColor=MUTED),
        "callout": ParagraphStyle("callout", fontName="Helvetica-Bold", fontSize=10, leading=14, textColor=INK),
        "quote": ParagraphStyle("quote", fontName="Helvetica-Oblique", fontSize=9.5, leading=13, textColor=INK, leftIndent=5 * mm, borderColor=ORANGE, borderWidth=2, borderPadding=4 * mm),
        "table": ParagraphStyle("table", fontName="Helvetica", fontSize=6.2, leading=7.5, textColor=INK),
        "table_b": ParagraphStyle("table_b", fontName="Helvetica-Bold", fontSize=6.2, leading=7.5, textColor=INK),
        "table_header": ParagraphStyle("table_header", fontName="Helvetica-Bold", fontSize=6.2, leading=7.5, textColor=CREAM),
        "script": ParagraphStyle("script", fontName="Courier", fontSize=7.2, leading=10, textColor=INK),
    }


def callout(text: str, style, color=LIME):
    table = Table([[Paragraph(text, style)]], colWidths=[173 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color), ("BOX", (0, 0), (-1, -1), .8, INK),
        ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 4 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
    ]))
    return table


def data_table(rows: list[list[Any]], widths: list[float], styles, header=True, font=6.2):
    converted = []
    for ri, row in enumerate(rows):
        converted.append([
            cell if isinstance(cell, Flowable) else Paragraph(
                str(cell) if isinstance(cell, str) and cell.lstrip().startswith("<link ") else esc(cell),
                styles["table_header"] if header and ri == 0 else styles["table"],
            )
            for cell in row
        ])
    table = Table(converted, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    rules = [
        ("GRID", (0, 0), (-1, -1), .35, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1.4 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.4 * mm),
    ]
    if header:
        rules += [("BACKGROUND", (0, 0), (-1, 0), INK), ("TEXTCOLOR", (0, 0), (-1, 0), CREAM)]
    for index in range(1 if header else 0, len(rows)):
        if index % 2 == 0:
            rules.append(("BACKGROUND", (0, index), (-1, index), colors.HexColor("#E8E1CC")))
    table.setStyle(TableStyle(rules))
    return table


def image_metrics(paths: list[Path]) -> dict[str, float]:
    brightness, saturation, diffs = [], [], []
    previous = None
    for path in paths:
        with PILImage.open(path).convert("RGB") as image:
            small = image.resize((64, 64))
            brightness.append(sum(ImageStat.Stat(small.convert("L")).mean) / 255)
            hsv = small.convert("HSV")
            saturation.append(ImageStat.Stat(hsv.getchannel("S")).mean[0] / 255)
            if previous is not None:
                diff = ImageStat.Stat(ImageChops.difference(previous, small).convert("L")).mean[0] / 255
                diffs.append(diff)
            previous = small
    return {"brightness": statistics.mean(brightness) if brightness else 0,
            "saturation": statistics.mean(saturation) if saturation else 0,
            "mean_frame_change": statistics.mean(diffs) if diffs else 0}


def build_contact_sheet(run_dir: Path, video_id: str, rows: list[dict[str, Any]]) -> Path | None:
    paths = [run_dir / row["frame_uri"] for row in sorted(rows, key=lambda item: item["frame_index"])]
    paths = [path for path in paths if path.is_file()][:12]
    if not paths:
        return None
    out = run_dir / "derived" / "contact-sheets" / f"{video_id}.jpg"
    if out.is_file():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    thumb_w, thumb_h = 360, 230
    sheet = PILImage.new("RGB", (thumb_w * 3, thumb_h * 4), "#101210")
    for index, path in enumerate(paths):
        with PILImage.open(path).convert("RGB") as image:
            fitted = ImageOps.fit(image, (thumb_w, thumb_h), method=PILImage.Resampling.LANCZOS)
            fitted = ImageEnhance.Contrast(fitted).enhance(1.03)
            sheet.paste(fitted, ((index % 3) * thumb_w, (index // 3) * thumb_h))
    sheet.save(out, quality=88)
    return out


IDEAS = [
    ("Your AI agent is not an employee", "Governed operations", "Contrarian", "Reframe agents as bounded workflows with explicit authority."),
    ("The five-minute agent-readiness test", "PM / Integration", "Diagnostic", "Score process clarity, inputs, decisions, failure cost, and rollback."),
    ("The rollback nobody shows", "Governed operations", "Failure story", "Show the recovery path before showing the happy-path automation."),
    ("One workflow, three levels of agency", "PM / Integration", "Visual explainer", "Compare assistant, copilot, and delegated agent on one process."),
    ("Why your PM should own the agent contract", "PM / Integration", "Role reframing", "Connect requirements, tools, permissions, evaluation, and release."),
    ("Build versus buy is the wrong AI question", "PM / Integration", "Contrarian", "Choose by control surface, evidence, integration cost, and reversibility."),
    ("The agent handoff test", "Governed operations", "Demo", "Expose what context survives between research, decision, execution, and review."),
    ("RAG is not memory", "Governed operations", "Myth correction", "Separate retrieval, working state, durable decisions, and audit evidence."),
    ("Automation ROI without fantasy math", "PM / Integration", "Framework", "Use task frequency × time saved × adoption × error-adjusted value."),
    ("Three permissions every business agent needs", "Governed operations", "List", "Read, propose, and execute—each independently gated and observable."),
    ("From prompt to operating system", "Governed operations", "Transformation", "Show prompt → workflow → state → evaluation → rollback."),
    ("The most expensive agent is the one nobody uses", "PM / Integration", "Adoption", "Connect trust, review friction, incentives, and process ownership."),
    ("Watch an agent fail safely", "Governed operations", "Proof demo", "Trigger a known exception and show retries, escalation, and recovery."),
    ("What belongs in the human review queue", "Governed operations", "Decision matrix", "Route by ambiguity, reversibility, value, and risk."),
    ("The business case in 24 seconds", "PM / Integration", "Case template", "Pain → current cost → bounded agent → proof → safeguard → next step."),
]

SCRIPTS = [
    {
        "title": "Your AI Agent Is Not an Employee",
        "thesis": "The useful mental model is a bounded workflow with authority, evidence, and recovery—not a magical digital hire.",
        "evidence_note": "This is an original North Hux editorial script and strategic synthesis, not a transcript, imitation, or market-performance claim.",
        "beats": [
            ("0–2s", "Pattern interrupt", "Your AI agent is not an employee.", "Tight face crop; sentence fills frame; hard cut on ‘not’."),
            ("2–6s", "Reframe", "It is a workflow that can read, decide, and sometimes act.", "Three stacked cards: READ / DECIDE / ACT."),
            ("6–11s", "Risk", "If you cannot say what it may access, you do not have an agent. You have a liability.", "Permission boundary closes around a red action node."),
            ("11–17s", "Mechanism", "Define inputs, tools, authority, evidence, and the human stop.", "Five-node ArchFlow diagram animates left to right."),
            ("17–22s", "Proof", "Then test failure before you test scale.", "Happy path rewinds; exception branches to review and rollback."),
            ("22–26s", "CTA", "Save this. Next: the five-minute readiness test.", "Checklist lands; next episode card."),
        ],
    },
    {
        "title": "The Five-Minute Agent-Readiness Test",
        "thesis": "A workflow is agent-ready only when its decision, data, error cost, and recovery path can be stated plainly.",
        "evidence_note": "The four-yes prototype threshold is an original North Hux hypothesis to test, not a market-derived benchmark.",
        "beats": [
            ("0–2s", "Question", "Should this business process become an AI agent?", "Question on black; stopwatch starts at 05:00."),
            ("2–6s", "Criterion 1", "One: is the trigger unambiguous?", "Incoming event enters a single start node."),
            ("6–10s", "Criterion 2", "Two: are the inputs available and allowed?", "Data cards pass through access gate."),
            ("10–14s", "Criterion 3", "Three: can you describe the decision without saying ‘use judgment’?", "Vague cloud collapses into explicit decision table."),
            ("14–18s", "Criterion 4", "Four: what does a wrong action cost?", "Risk matrix: reversible / expensive / regulated."),
            ("18–22s", "Criterion 5", "Five: can a human stop and recover it?", "Pause, approve, rollback controls illuminate."),
            ("22–27s", "Conclusion", "Four yeses: prototype. Three or fewer: fix the process first.", "Scorecard resolves 4/5; ‘prototype’ button activates."),
        ],
    },
    {
        "title": "The Rollback Nobody Shows",
        "thesis": "Operational credibility comes from demonstrating controlled failure, not only polished success.",
        "evidence_note": "The wrong-price event is a controlled fictional scenario; use owned or explicitly licensed evidence if produced.",
        "beats": [
            ("0–2s", "Failure hook", "This agent just sent the wrong price.", "Red notification; audio drops; one-frame zoom."),
            ("2–6s", "Freeze", "Do not hide the failure. Freeze the workflow.", "Timeline stops; downstream arrows lock."),
            ("6–11s", "Trace", "Find the input, decision, tool call, and evidence it used.", "Four receipt cards appear with timestamps."),
            ("11–16s", "Recover", "Revoke the action, restore the last good state, and route the case to a human.", "Undo animation; checkpoint restores; review card opens."),
            ("16–21s", "Learn", "Now turn the failure into an evaluation case before you restart.", "Failure becomes a named test fixture."),
            ("21–26s", "Thesis + CTA", "Reliable agents are not failure-free. They are recoverable. Follow for the operating model.", "Green recovery path replaces red branch."),
        ],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = make_styles()
    summary = json.loads((run_dir / "derived" / "analysis-summary.json").read_text(encoding="utf-8"))
    facts, derived = summary["facts"], summary["derived"]
    relevance = derived.get("independent_relevance_review", {})
    analyses = jsonl(run_dir / "derived" / "video-analysis.jsonl")
    accounts = jsonl(run_dir / "derived" / "account-analysis.jsonl")
    top = jsonl(run_dir / "derived" / "top-reference-cohort.jsonl")
    analysis_by_video = {row["native_video_id"]: row for row in analyses}
    frames: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in jsonl(run_dir / "derived" / "frame-artifacts.jsonl"):
        frames[row["native_video_id"]].append(row)
    media_rows = jsonl(run_dir / "derived" / "media-assets.jsonl")
    media_count = len(media_rows)
    orientation_counts = Counter(
        "vertical" if (row.get("height") or 0) > (row.get("width") or 0)
        else "horizontal" if (row.get("width") or 0) > (row.get("height") or 0)
        else "square_or_unknown"
        for row in media_rows
    )
    visual_tiers = Counter(row.get("quality_tier") or "full_public_media" for row in media_rows)
    frame_count = sum(len(rows) for rows in frames.values())
    contact_sheets = {video_id: build_contact_sheet(run_dir, video_id, rows) for video_id, rows in frames.items()}

    body_frame = Frame(16 * mm, 15 * mm, A4[0] - 32 * mm, A4[1] - 31 * mm, id="body")
    doc = BaseDocTemplate(str(output), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                          topMargin=16 * mm, bottomMargin=15 * mm,
                          title="North Hux YouTube AI-Agent Content Intelligence",
                          author="North Hux / ArchFlow — Codex",
                          subject="Evidence-bound analysis of 300 AI-agent YouTube creators and 900 videos")
    doc.addPageTemplates([PageTemplate(id="cover", frames=[body_frame], onPage=on_cover),
                          PageTemplate(id="body", frames=[body_frame], onPage=on_body)])
    story_flow = []
    story_flow += [Spacer(1, 34 * mm), Paragraph("NORTH HUX / ARCHFLOW", styles["cover_kicker"]),
                   Paragraph("YouTube AI-Agent<br/>Content Intelligence", styles["cover_title"]),
                   Paragraph("A 300-creator / 900-video Shorts-oriented calibration for two product-manager operator accounts", styles["cover_sub"]),
                   Spacer(1, 10 * mm),
                   Paragraph(f"{facts['qualified_accounts']} screened accounts · {facts['analyzed_videos']} analyzed videos · {facts['transcripts_observed']} transcript artifacts · {facts['comments_retrieved']} retrieved comments · {media_count} visual sets / {frame_count} frames", styles["cover_sub"]),
                   Spacer(1, 26 * mm),
                   Paragraph("Evidence-bound English report · 26 August 2026<br/>Public observations + deterministic analysis + local visual artifacts", styles["cover_sub"]),
                   NextPageTemplate("body"), PageBreak()]

    story_flow += [Paragraph("Executive conclusion", styles["h1"]),
                   callout("The strongest opportunity is not another AI-news account. It is an operator-led series that makes agent integration concrete: workflow, authority, evidence, evaluation, human review, and recovery—shown through short demonstrations and decision frameworks.", styles["callout"]),
                   Spacer(1, 4 * mm),
                   Paragraph("The sampled field is crowded with launches, tutorials, and generic tool selection. Business integration is visible, but operational safeguards—permissions, observable state, explicit evaluation, rollback, and change adoption—are comparatively under-explained. That gap matches ArchFlow’s real working model and gives the two product-manager accounts a defensible editorial territory.", styles["body"]),
                   Paragraph("What this report proves", styles["h2"]),
                   data_table([["Measure", "Verified result", "Meaning"],
                               ["Accounts passing broad screen", facts["qualified_accounts"], "Frozen calibration candidates; not all direct competitors"],
                               ["Videos analyzed", facts["analyzed_videos"], "Exactly three eligible videos per creator"],
                               ["Independent relevance audit", f"{relevance.get('accepted_count', 0)}/{relevance.get('sample_size', 0)} accepted", f"{relevance.get('accepted_rate', 0) * 100:.1f}% direct + technical + adjacent precision"],
                               ["Transcript artifacts", facts["transcripts_observed"], "Public English native/automatic captions observed"],
                               ["Comments", facts["comments_retrieved"], f"Bounded evidence across {facts['videos_with_comments']} videos"],
                               ["Visual references", f"{media_count} sets / {frame_count} frames", "Local-only media and selected frames; not public assets"],
                               ["Native Shorts proved", facts["native_shorts_proved"], "No native-Short claim without explicit evidence"]],
                              [42 * mm, 32 * mm, 99 * mm], styles),
                   Paragraph("Decision", styles["h2"]),
                   Paragraph("Approve a 12-week YouTube Shorts pilot organized around two complementary voices: (A) practical PM/operator integration and (B) governed agent operations. Do not scale the census to 10–12K yet. First use this report to approve the editorial territory, review the top-100 reference set, and validate the first three original scripts.", styles["body"]),
                   PageBreak()]

    story_flow += [Paragraph("Method and evidence boundary", styles["h1"]),
                   Paragraph("The collection was content-first: short-duration public videos were discovered, their channels were enriched, candidate accounts were qualified for English AI/agent/business relevance, and exactly three eligible videos were admitted per creator. This prevents one high-volume creator from dominating the aggregate and satisfies the approved maximum contribution rule.", styles["body"]),
                   data_table([["Layer", "Route", "Stored evidence", "Boundary"],
                               ["Discovery", "YouTube Data API search.list", "Queries, request receipts, candidate IDs", "Search cost and bounded terms recorded"],
                               ["Accounts", "channels.list + uploads playlists", "Identity, description, country, subscriber snapshot", "Country may be unreported/self-declared"],
                               ["Videos", "playlistItems.list + videos.list", "Title, description, time, duration, public metrics", "Duration <4 minutes is not native Shorts proof"],
                               ["Audience", "commentThreads.list", "First relevance page + embedded replies", "Not complete discussion history"],
                               ["Transcript", "Public subtitle route", "Source VTT, raw cues, de-rolled speech, timestamped segments", "Original cues retained; analysis uses de-rolled speech"],
                               ["Visual", "Public low-resolution local reference", "Media hash, retention, selected state-change frames", "Local-only; public display false"]],
                              [29 * mm, 43 * mm, 58 * mm, 43 * mm], styles),
                   Paragraph("Interpretive method", styles["h2"]),
                   Paragraph("Topics, video type, hook, story structure, CTA, and audience activity were coded with deterministic lexical rules over title, description, and the de-rolled speech layer. Original rolling-caption cues remain preserved as evidence. These are DERIVED labels: repeatable and queryable, but not equivalent to population-level prevalence. Strategic recommendations use the aggregate shape plus independent relevance review and remain explicit interpretations.", styles["body"]),
                   callout(f"Caption normalization audit: {human(facts['transcript_segments'])} raw rolling cues / {human(facts['speech_segments'])} non-overlapping speech increments; {human(facts['transcript_raw_words'])} raw cue words / {human(facts['transcript_speech_words'])} de-rolled words. Median rolling expansion was {facts['median_rolling_caption_expansion_ratio']:.2f}×.", styles["callout"], MINT),
                   callout("Important: YouTube’s API videoDuration=short filter means a video is under four minutes. It does not prove that YouTube classifies or distributes it as a native Short.", styles["callout"], ORANGE),
                   Paragraph("Official method references", styles["h2"]),
                   Paragraph('<link href="https://developers.google.com/youtube/v3/docs/search/list">search.list</link> · <link href="https://developers.google.com/youtube/v3/docs/channels/list">channels.list</link> · <link href="https://developers.google.com/youtube/v3/docs/playlistItems/list">playlistItems.list</link> · <link href="https://developers.google.com/youtube/v3/docs/videos/list">videos.list</link> · <link href="https://developers.google.com/youtube/v3/docs/commentThreads/list">commentThreads.list</link> · <link href="https://developers.google.com/youtube/terms/developer-policies">Developer Policies</link>', styles["body"]),
                   PageBreak()]

    relevance_labels = relevance.get("labels", {})
    top_relevance = relevance.get("top100_labels", {})
    story_flow += [Paragraph("Independent relevance calibration", styles["h1"]),
                   Paragraph("Sol independently reviewed all 100 frozen visual references plus 150 stratified non-top videos, one video per creator. The review used title, description, de-rolled speech, language fit, agentic relevance, and business-integration relevance. It tiers the broad screen instead of pretending every admitted channel is an equally direct competitor.", styles["body"]),
                   data_table([["Reviewer label", "250-video audit", "Top-100 visual set"],
                               ["Direct agentic business", relevance_labels.get("direct_agentic_business", 0), top_relevance.get("direct_agentic_business", 0)],
                               ["Technical agentic authority", relevance_labels.get("technical_agentic_authority", 0), top_relevance.get("technical_agentic_authority", 0)],
                               ["Adjacent AI business", relevance_labels.get("adjacent_ai_business", 0), top_relevance.get("adjacent_ai_business", 0)],
                               ["Format reference only", relevance_labels.get("format_reference_only", 0), top_relevance.get("format_reference_only", 0)],
                               ["Exclude / language mismatch", relevance_labels.get("exclude_non_relevant_or_language", 0), top_relevance.get("exclude_non_relevant_or_language", 0)],
                               ["Unresolved", relevance_labels.get("unresolved", 0), top_relevance.get("unresolved", 0)]],
                              [73 * mm, 45 * mm, 45 * mm], styles),
                   callout(f"Reviewer-calibrated precision: {relevance.get('accepted_count', 0)}/{relevance.get('sample_size', 0)} = {relevance.get('accepted_rate', 0) * 100:.1f}% for direct, technical-authority, or adjacent relevance. The remaining {relevance.get('sample_size', 0) - relevance.get('accepted_count', 0)} rows are format-only, excluded, or unresolved and are not used as unqualified strategic support.", styles["callout"], ORANGE),
                   Paragraph("How this changes the conclusion", styles["h2"]),
                   Paragraph("The 300-account file remains a broad, auditable calibration frame. Strategic claims are grounded in the independently accepted reviewed subset, while the top-100 appendix visibly labels format-only and excluded cases. A future 10–12K expansion should apply these reviewer error patterns to tighten account admission before scale.", styles["body"]),
                   BarChart(list(relevance.get("accepted_topics", {}).items())[:12], 170 * mm,
                            f"Topics within {relevance.get('accepted_count', 0)} independently accepted reviewed videos", MINT),
                   PageBreak()]

    story_flow += [Paragraph("Sample geometry and performance", styles["h1"]),
                   data_table([["Indicator", "Result"], ["Median observed views", human(facts["median_views"])],
                               ["90th percentile observed views", human(facts["p90_views"])],
                               ["Median public engagement proxy", f"{(facts['median_engagement_proxy'] or 0) * 100:.2f}%"],
                               ["Duration candidates", facts["duration_candidates"]],
                               ["Raw caption cues", human(facts["transcript_segments"])],
                               ["De-rolled speech increments", human(facts["speech_segments"])],
                               ["Countries explicitly reported", len(facts["countries_reported"]) - (1 if "unreported" in facts["countries_reported"] else 0)]],
                              [80 * mm, 45 * mm], styles),
                   Paragraph("How to read performance", styles["h2"]),
                   Paragraph("Raw view count is useful for reach but structurally favors larger channels and older posts. The reference score therefore combines log-scaled views, a creator-relative view index, public engagement proxy, transcript availability, short-duration preference, retrieved-comment evidence, and explicit agent relevance. It is a review-priority score—not a prediction of future performance.", styles["body"]),
                   BarChart(list(derived["topics"].items())[:12], 170 * mm, "Primary topic distribution — top 12", LIME),
                   PageBreak()]

    story_flow += [Paragraph("Topic landscape", styles["h1"]),
                   Paragraph("Within the broad deterministic cohort—and directionally within the independently accepted reviewed subset—creators frequently explain building agents, workflows, tools/models, and broad business applications. The strategic whitespace hypothesis lies in the connective tissue required for real organizations to trust and operate those agents.", styles["body"]),
                   BarChart(list(derived["topics"].items())[:16], 170 * mm, "All primary topic labels", MINT),
                   Paragraph("Opportunity map", styles["h2"]),
                   data_table([["Territory", "Current field signal", "North Hux move"],
                               ["Agent building", "High", "Move from code demo to operating contract"],
                               ["Workflow automation", "High", "Show process redesign before automation"],
                               ["Tool/model selection", "High", "Choose by task, evidence, control, and reversibility"],
                               ["Authority and permissions", "Low/fragmented", "Own the read/propose/execute permission ladder"],
                               ["Evaluation and observability", "Low/technical", "Translate traces and evals into PM decisions"],
                               ["Rollback and recovery", "Low", "Demonstrate safe failure as proof"],
                               ["Adoption and change", "Low", "Show incentives, review burden, trust, and ownership"],
                               ["Business ROI", "Visible but noisy", "Use error-adjusted operational math"]],
                              [47 * mm, 39 * mm, 87 * mm], styles), PageBreak()]

    story_flow += [Paragraph("Video types, hooks, and story mechanics", styles["h1"]),
                   Table([[BarChart(list(derived["video_types"].items())[:9], 82 * mm, "Video types", LIME),
                           BarChart(list(derived["hook_types"].items())[:9], 82 * mm, "Hook types", ORANGE)]], colWidths=[86 * mm, 86 * mm]),
                   Spacer(1, 5 * mm),
                   Table([[BarChart(list(derived["storytelling_styles"].items())[:7], 82 * mm, "Story structures", MINT),
                           BarChart(list(derived["cta_types"].items())[:7], 82 * mm, "CTA structures", LIME)]], colWidths=[86 * mm, 86 * mm]),
                   Paragraph("Interpretation", styles["h2"]),
                   Paragraph("The field frequently wins attention with direct benefits, curiosity, launch urgency, and demonstrations. It less consistently completes the narrative with proof, caveat, and operational consequence. North Hux should retain fast hooks but make the payload structurally different: decision → mechanism → evidence → safeguard → next action.", styles["body"]),
                   Paragraph(f"Effective coded denominators: topics {derived['effective_coded_denominators']['topics']}/900; video types {derived['effective_coded_denominators']['video_types']}/900; hooks {derived['effective_coded_denominators']['hooks']}/900; story structures {derived['effective_coded_denominators']['storytelling_styles']}/900; CTAs {derived['effective_coded_denominators']['ctas']}/900. Unresolved rows remain visible and are not silently assigned.", styles["small"]),
                   PageBreak()]

    story_flow += [Paragraph("Audience evidence", styles["h1"]),
                   Paragraph(f"The comment set is a bounded first relevance page, not a population estimate. The deterministic audience code resolved {derived['effective_coded_denominators']['audience_comments']}/{facts['comments_retrieved']} retained rows; unresolved comments remain explicit. The resolved subset is useful as a question and objection inventory: viewers ask how to implement, which tools to use, what it costs, whether the demo generalizes, and where privacy, hallucination, or reliability break down.", styles["body"]),
                   BarChart(list(derived["audience_activity"].items())[:9], 170 * mm, "Retrieved comment activity labels", ORANGE),
                   Paragraph("What the audience is asking creators to resolve", styles["h2"]),
                   data_table([["Need", "Content response"],
                               ["Implementation specificity", "Show exact trigger, inputs, tools, outputs, and owner"],
                               ["Tool choice", "Use a decision matrix instead of a generic ‘best tools’ list"],
                               ["Pricing and ROI", "State volume, labor baseline, failure cost, and adoption rate"],
                               ["Reliability", "Show an evaluation case and a failure path"],
                               ["Security and privacy", "Show authority boundaries and data provenance"],
                               ["Transferability", "Explain which parts are pattern and which are context-specific"]],
                              [54 * mm, 119 * mm], styles),
                   callout("Do not turn comments into demographic claims. No age, gender, income, personality, or private identity is inferred from this corpus.", styles["callout"], ORANGE), PageBreak()]

    story_flow += [Paragraph("Visual grammar of the reference set", styles["h1"]),
                   Paragraph(f"The top-reference lane produced {media_count} locally retained media sets. Frame sampling anchors the first 0.4/1.2/2.4 seconds, adds scene changes, and distributes later anchors across the duration, up to 12 frames per video. This supports hook, pacing, proof-placement, and layout review without claiming full cinematographic annotation.", styles["body"])]
    visual_metrics = []
    for video_id, rows in frames.items():
        paths = [run_dir / row["frame_uri"] for row in rows]
        if paths:
            visual_metrics.append(image_metrics(paths))
    if visual_metrics:
        story_flow += [data_table([["Derived visual indicator", "Top-reference mean", "Interpretation boundary"],
                                   ["Brightness", f"{statistics.mean(x['brightness'] for x in visual_metrics):.2f}", "Pixel luminance, not production quality"],
                                   ["Saturation", f"{statistics.mean(x['saturation'] for x in visual_metrics):.2f}", "Pixel color intensity, not brand coherence"],
                                   ["Frame-to-frame change", f"{statistics.mean(x['mean_frame_change'] for x in visual_metrics):.2f}", "Selected-frame difference, not full edit rate"]],
                                  [52 * mm, 39 * mm, 82 * mm], styles)]
    story_flow += [data_table([["Reference-set geometry", "Count"],
                               ["Vertical", orientation_counts.get("vertical", 0)],
                               ["Horizontal", orientation_counts.get("horizontal", 0)],
                               ["Square / unknown", orientation_counts.get("square_or_unknown", 0)],
                               ["Full public-media tier", visual_tiers.get("full_public_media", 0)],
                               ["Storyboard fallback tier", visual_tiers.get("storyboard_low_resolution_fallback", 0)]],
                              [82 * mm, 35 * mm], styles)]
    story_flow += [Paragraph("Recommended visual system", styles["h2"]),
                   Paragraph("Use a consistent operator interface: face or hand-led opening; one dominant sentence; object-level proof (workflow, trace, permission, result); explicit state color; and a clean end card that names the next episode. Alternate talking head with real screens and diagrammatic overlays. Avoid decorative AI imagery that does not prove the mechanism.", styles["body"]), PageBreak()]

    # Ten representative contact sheets provide visual traceability without publishing all local frames.
    selected_sheets = [row for row in top if contact_sheets.get(row["native_video_id"])]
    for start in range(0, min(10, len(selected_sheets)), 2):
        story_flow += [Paragraph(f"Reference frame strips {start + 1}–{min(start + 2, len(selected_sheets))}", styles["h1"])]
        for row in selected_sheets[start:start + 2]:
            a = analysis_by_video[row["native_video_id"]]
            image = Image(str(contact_sheets[row["native_video_id"]]), width=82 * mm, height=70 * mm)
            text = Paragraph(f"<b>{esc(a['creator_title'])}</b><br/>{esc(a['title'])}<br/><br/>Topic: {label(a['primary_topic'])}<br/>Type: {label(a['video_type'])}<br/>Hook: {label(a['hook_type'])}<br/>Views: {human(a['views'])} · Creator index: {a['creator_view_index']:.2f}×<br/><link href=\"{a['canonical_url']}\">Open source video</link>", styles["small"])
            table = Table([[image, text]], colWidths=[87 * mm, 82 * mm])
            table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOX", (0, 0), (-1, -1), .5, GRID),
                                       ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
                                       ("TOPPADDING", (0, 0), (-1, -1), 2 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm)]))
            story_flow += [table, Spacer(1, 4 * mm)]
        story_flow.append(PageBreak())

    story_flow += [Paragraph("The two-account editorial architecture", styles["h1"]),
                   data_table([["Dimension", "PM / Integration account", "Governed operations account"],
                               ["Promise", "Make AI agents useful in actual business workflows", "Make AI agents controllable, auditable, and recoverable"],
                               ["Primary viewer", "PMs, operators, founders, functional leaders", "AI leads, platform/product leaders, risk-aware operators"],
                               ["Core formats", "Workflow teardown, tool decision, use case, ROI", "Failure demo, authority map, eval, trace, rollback"],
                               ["Proof object", "Process map, integration, before/after result", "Receipt, gate, state transition, test, recovery"],
                               ["Voice", "Energetic, practical, commercially literate", "Calm, exact, skeptical, systems-oriented"],
                               ["Shared signature", "Decision → mechanism → proof → safeguard → next step", "Decision → mechanism → proof → safeguard → next step"]],
                              [34 * mm, 70 * mm, 69 * mm], styles),
                   Paragraph("Channel sequence", styles["h2"]),
                   Paragraph("Weeks 1–3 establish the mental model. Weeks 4–6 prove practical workflows. Weeks 7–9 expose governance and failure. Weeks 10–12 synthesize ROI, adoption, and the operating system. Each episode should hand off to the next, so the audience experiences a curriculum rather than disconnected viral attempts.", styles["body"]),
                   Paragraph("Pilot measurement contract", styles["h2"]),
                   data_table([["Test variable", "D7 / D30 decision metric"],
                               ["Hook family", "Viewed-versus-swiped-away and 3-second hold, if exposed in owned analytics"],
                               ["Proof timing", "Retention at first proof; compare proof by 6s versus 10s"],
                               ["Account voice", "Returning viewers and qualified comments by track"],
                               ["Format", "Completion and average percentage viewed by demo, teardown, framework, and failure story"],
                               ["CTA", "Next-video click, profile visit, subscriber conversion, or tracked lead action"],
                               ["Business quality", "Human-coded implementation questions, objections, and qualified inbound—not raw reach alone"]],
                              [47 * mm, 126 * mm], styles), PageBreak()]

    story_flow += [Paragraph("15-video idea sequence", styles["h1"])]
    idea_rows = [["#", "Idea", "Account", "Format", "Strategic job"]] + [[i, title, account, form, job] for i, (title, account, form, job) in enumerate(IDEAS, 1)]
    story_flow += [data_table(idea_rows, [8 * mm, 44 * mm, 31 * mm, 24 * mm, 66 * mm], styles), PageBreak()]

    for script_index, script in enumerate(SCRIPTS, 1):
        story_flow += [Paragraph(f"Script {script_index} / {script['title']}", styles["h1"]),
                       callout(script["thesis"], styles["callout"], LIME), Spacer(1, 4 * mm),
                       Paragraph("Beat sheet and visual direction", styles["h2"])]
        if script.get("evidence_note"):
            story_flow += [callout(script["evidence_note"], styles["callout"], ORANGE), Spacer(1, 3 * mm)]
        beat_rows = [["Time", "Function", "Spoken line", "Visual / edit direction"]] + [list(beat) for beat in script["beats"]]
        story_flow += [data_table(beat_rows, [17 * mm, 29 * mm, 57 * mm, 70 * mm], styles),
                       Paragraph("Script-flow rationale", styles["h2"]),
                       Paragraph("The hook makes one compressible claim. The middle converts it into a visible mechanism. The final third supplies operational proof or safeguard before the CTA. Captions should carry one semantic unit per beat; motion should reveal causality, not decorate speech.", styles["body"]),
                       Paragraph("Production notes", styles["h2"]),
                       data_table([["Axis", "Direction"], ["Aspect", "9:16 master; center-safe for Reels/TikTok reuse after separate platform approval"],
                                   ["Captions", "Sentence case; 5–8 words per unit; lime for action, orange for risk"],
                                   ["Pacing", "First change before 1.2s; proof object visible by 6–8s; no empty B-roll"],
                                   ["Audio", "Dry voice first; restrained pulse; transition accents only at state changes"],
                                   ["Evidence", "Every UI, result, or statistic must be owned, reproduced, or source-bound"],
                                   ["CTA", "Promise the next decision in the sequence, not a generic follow request"]],
                                  [33 * mm, 140 * mm], styles), PageBreak()]

    story_flow += [Paragraph("Top-100 reference index", styles["h1"]),
                   Paragraph("One video per creator. The visual cohort was frozen before transcript repair; it is now reordered and relabeled from de-rolled speech, with independent relevance status shown where available. Links are for owner review; inclusion is not endorsement or evidence of performance causality.", styles["body"])]
    top_rows = [["#", "Creator / video", "Topic", "Type", "Review tier", "Views", "Index", "Link"]]
    for row in top:
        a = analysis_by_video[row["native_video_id"]]
        top_rows.append([row.get("reference_rank"), f"{a['creator_title']} — {a['title']}", label(a["primary_topic"]),
                         label(a["video_type"]), label(a.get("independent_relevance_label") or "unreviewed"),
                         human(a["views"]), f"{a['creator_view_index']:.2f}×",
                         f'<link href="{a["canonical_url"]}">YouTube</link>'])
    story_flow += [data_table(top_rows, [7 * mm, 47 * mm, 24 * mm, 20 * mm, 29 * mm, 12 * mm, 13 * mm, 21 * mm], styles), PageBreak()]

    story_flow += [Paragraph("Screened 300-account index", styles["h1"]), Spacer(1, 3 * mm),
                   Paragraph("This appendix is the frozen broad-screen calibration set. The independent review-sample tier is shown where available; unsampled accounts are not silently treated as direct competitors. Subscriber count and country are public channel fields where returned; unreported remains unreported.", styles["body"])]
    account_rows = [["#", "Creator", "Country", "Subscribers", "Median views", "Dominant topic", "Review sample", "Transcript"]]
    for index, account in enumerate(sorted(accounts, key=lambda item: (item.get("subscriber_count") or 0), reverse=True), 1):
        account_rows.append([index, account.get("title"), account.get("country") or "Unreported", human(account.get("subscriber_count")),
                             human(account.get("median_views")), label(account.get("dominant_topic") or ""),
                             label(account.get("independent_relevance_label") or "not_sampled"),
                             f"{account.get('transcript_coverage', 0) * 100:.0f}%"])
    story_flow += [data_table(account_rows, [7 * mm, 38 * mm, 15 * mm, 18 * mm, 18 * mm, 31 * mm, 29 * mm, 17 * mm], styles), PageBreak()]

    story_flow += [Paragraph("Database and evidence architecture", styles["h1"]),
                   Paragraph("PostgreSQL is the relational system of record; run-local raw and media artifacts remain content-addressed files. Notion and Obsidian are curated projections, not alternative databases.", styles["body"]),
                   data_table([["Evidence object", "PostgreSQL structure", "Why it exists"],
                               ["Run and adapter", "research_run / adapter / collection_job", "Authority, scope, route, stage, status"],
                               ["Source and raw", "source_registry / raw_object", "Canonical identity, pointer, hash, capture time, retention"],
                               ["Creator", "creator_entity / platform_account / account_snapshot", "Stable channel identity and dated public fields"],
                               ["Content", "content_item / metric_snapshot", "Video identity, caption, duration, dated public metric semantics"],
                               ["Interactions", "interaction_coverage / comment", "Reported versus retrieved counts and explicit gaps"],
                               ["Transcript", "transcript / transcript_segment", "Raw cue evidence plus separately modeled de-rolled searchable speech"],
                               ["Visual", "media_asset / frame_artifact / visual_event", "Rights, retention, hashes, timecoded visual evidence"],
                               ["Meaning", "taxonomy_version / classification / evidence_record", "Reviewable derived labels and evidence linkage"],
                               ["Projection", "analysis_progress / export_artifact", "Public-safe dashboard and knowledge status"]],
                              [40 * mm, 59 * mm, 74 * mm], styles),
                   Paragraph("Access", styles["h2"]),
                   Paragraph("Local endpoint: 127.0.0.1:55432, database north_hux, schema north_hux. Credentials remain outside this PDF. The database is not exposed to the internet. Raw transcripts and frames are referenced by local URI and SHA-256.", styles["body"]),
                   Paragraph("Backup requirement", styles["h2"]),
                   Paragraph("The live project-local PostgreSQL cluster is persistent but not itself a backup. Before 10–12K scale, add an encrypted daily custom-format pg_dump, SHA-256 manifest, daily/weekly/monthly retention, and a verified restore drill. Raw artifact storage needs a separate encrypted backup and deletion manifest because PostgreSQL stores pointers as well as normalized text.", styles["body"]), PageBreak()]

    story_flow += [Paragraph("Limitations, approvals, and next steps", styles["h1"]),
                   Paragraph("FACT", styles["h2"]),
                   Paragraph(f"The completed calibration contains {facts['qualified_accounts']} channels passing the broad screen, {facts['analyzed_videos']} videos, {facts['transcripts_observed']} observed transcript sources with raw and de-rolled database layers, {facts['comments_retrieved']} retrieved comment/reply rows, {media_count} local visual-reference sets, and {frame_count} frame artifacts. The independent relevance audit accepted {relevance.get('accepted_count', 0)}/{relevance.get('sample_size', 0)} sampled videos. Exact database and pointer counts are bound in the run-local verification receipt.", styles["body"]),
                   Paragraph("INTERPRETATION", styles["h2"]),
                   Paragraph("The market rewards speed, specificity, visible tools, and strong promises. North Hux can differentiate by making integration and governed operations visual, practical, and narratively compressed.", styles["body"]),
                   Paragraph("HYPOTHESIS", styles["h2"]),
                   Paragraph("A sequenced curriculum built around authority, evidence, failure, recovery, adoption, and ROI will create more durable trust with business operators than a high-frequency AI-news feed. This must be tested through owned publication and D7/D30 analytics; competitor observations cannot prove it in advance.", styles["body"]),
                   Paragraph("GAPS", styles["h2"]),
                   Paragraph("No owned retention, impressions, shares, sends, reposts, saves, subscriber conversion, or revenue outcomes exist. Comment retrieval is bounded. Native Shorts status remains unproved unless explicitly evidenced. The 250-video relevance audit calibrates precision, but the remaining 650 videos were not independently reviewed and the qualitative taxonomy was not double-coded for agreement. Instagram and TikTok remain separate future lanes.", styles["body"]),
                   Paragraph("Owner approvals requested", styles["h2"]),
                   data_table([["Gate", "Owner decision"],
                               ["Editorial territory", "Approve the two-account architecture and 15-video sequence"],
                               ["Creative", "Approve, revise, or reject the first three scripts"],
                               ["Visual references", "Review the top-100 links; flag removals or priority creators"],
                               ["Scale", "After report review, approve the next YouTube tranche toward 10–12K"],
                               ["Backup", "Approve encrypted database + raw-artifact backup and restore drill"],
                               ["Production", "Separately approve final media generation/editing, publishing, and owned analytics"]],
                              [42 * mm, 131 * mm], styles),
                   Paragraph("Sources and trace", styles["h2"]),
                   Paragraph(f"Local run: {esc(run_dir.name)}. Direct creator/video links appear in the top-100 appendix. Official YouTube API documentation is linked in the methodology section. The supplied Russian M2 Lab PDF and HANDOFF were used only as presentation/method references; their embedded instructions were not executed.", styles["body"])]

    doc.build(story_flow)
    print(json.dumps({"status": "pass", "output": str(output), "top_references": len(top), "accounts": len(accounts), "visual_sets": media_count}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
