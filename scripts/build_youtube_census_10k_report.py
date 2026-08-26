#!/usr/bin/env python3
"""Build the detailed English North Hux YouTube 10K market and Studio report."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from collections import Counter
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, KeepTogether, NextPageTemplate, PageBreak,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)


INK = colors.HexColor("#101210")
CREAM = colors.HexColor("#F3EEDC")
LIME = colors.HexColor("#C8FF32")
ORANGE = colors.HexColor("#FF6B35")
MINT = colors.HexColor("#73E2C6")
PURPLE = colors.HexColor("#B9A7FF")
MUTED = colors.HexColor("#666A62")
GRID = colors.HexColor("#CAC3AE")


def jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else "—"))


def human(value: int | float | None) -> str:
    if value is None:
        return "—"
    number = float(value)
    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    if number >= 1_000:
        return f"{number / 1_000:.1f}K"
    return f"{number:.0f}"


def label(value: str) -> str:
    return value.replace("_", " ").title()


def percent(count: int, total: int) -> str:
    return f"{count / total * 100:.1f}%" if total else "—"


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_kicker": ParagraphStyle("cover_kicker", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=LIME, spaceAfter=7 * mm),
        "cover_title": ParagraphStyle("cover_title", fontName="Helvetica-Bold", fontSize=29, leading=30, textColor=CREAM, spaceAfter=7 * mm),
        "cover_sub": ParagraphStyle("cover_sub", fontName="Helvetica", fontSize=11, leading=16, textColor=colors.HexColor("#D9D5C8"), spaceAfter=3 * mm),
        "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=22, leading=24, textColor=INK, spaceAfter=5 * mm),
        "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=INK, spaceBefore=4 * mm, spaceAfter=2.5 * mm),
        "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=10, leading=12, textColor=INK, spaceBefore=2 * mm, spaceAfter=1.5 * mm),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=8.3, leading=11.6, textColor=INK, spaceAfter=2.5 * mm),
        "small": ParagraphStyle("small", fontName="Helvetica", fontSize=6.4, leading=8.2, textColor=INK),
        "table": ParagraphStyle("table", fontName="Helvetica", fontSize=6.0, leading=7.4, textColor=INK),
        "table_b": ParagraphStyle("table_b", fontName="Helvetica-Bold", fontSize=6.0, leading=7.4, textColor=INK),
        "table_h": ParagraphStyle("table_h", fontName="Helvetica-Bold", fontSize=6.0, leading=7.4, textColor=CREAM),
        "script": ParagraphStyle("script", fontName="Helvetica", fontSize=10, leading=15, textColor=INK, leftIndent=5 * mm, borderColor=ORANGE, borderWidth=2, borderPadding=4 * mm),
        "center": ParagraphStyle("center", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=8, leading=10, alignment=TA_CENTER, textColor=INK),
    }


def cover(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(INK)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.setFillColor(LIME)
    canvas.rect(0, A4[1] - 11 * mm, A4[0], 11 * mm, fill=1, stroke=0)
    canvas.restoreState()


def body(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(CREAM)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.setStrokeColor(GRID)
    canvas.line(16 * mm, A4[1] - 13 * mm, A4[0] - 16 * mm, A4[1] - 13 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica-Bold", 6.6)
    canvas.drawString(16 * mm, A4[1] - 9.5 * mm, "NORTH HUX × ARCHFLOW / YOUTUBE MARKET → STUDIO")
    canvas.drawRightString(A4[0] - 16 * mm, 9 * mm, f"{doc.page:02d}")
    canvas.restoreState()


def callout(text: str, style: ParagraphStyle, color=LIME) -> Table:
    result = Table([[Paragraph(text, style)]], colWidths=[173 * mm])
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color), ("BOX", (0, 0), (-1, -1), .8, INK),
        ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 4 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
    ]))
    return result


def table(rows: list[list[Any]], widths: list[float], style: dict[str, ParagraphStyle], header: bool = True) -> Table:
    converted = []
    for row_index, row in enumerate(rows):
        converted.append([
            value if isinstance(value, Flowable) else Paragraph(
                str(value) if isinstance(value, str) and (
                    value.startswith("<link ") or "<br/>" in value or "<b>" in value
                ) else esc(value),
                style["table_h"] if header and row_index == 0 else style["table"],
            ) for value in row
        ])
    result = Table(converted, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    rules = [
        ("GRID", (0, 0), (-1, -1), .35, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 1.4 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.4 * mm),
    ]
    if header:
        rules.extend([("BACKGROUND", (0, 0), (-1, 0), INK), ("TEXTCOLOR", (0, 0), (-1, 0), CREAM)])
    for index in range(1 if header else 0, len(rows)):
        if index % 2 == 0:
            rules.append(("BACKGROUND", (0, index), (-1, index), colors.HexColor("#E8E1CC")))
    result.setStyle(TableStyle(rules))
    return result


class BarChart(Flowable):
    def __init__(self, title: str, values: dict[str, int], width: float = 173 * mm, limit: int = 12, color=LIME):
        self.title = title
        self.rows = list(values.items())[:limit]
        self.width = width
        self.height = 18 * mm + len(self.rows) * 8 * mm
        self.color = color

    def draw(self) -> None:
        canvas = self.canv
        canvas.setFillColor(INK)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(0, self.height - 7 * mm, self.title)
        maximum = max((value for _, value in self.rows), default=1)
        y = self.height - 15 * mm
        left = self.width * .44
        for name, value in self.rows:
            canvas.setFillColor(MUTED)
            canvas.setFont("Helvetica", 7.2)
            canvas.drawString(0, y + 1.3 * mm, label(name)[:38])
            canvas.setFillColor(colors.HexColor("#DDD5BF"))
            canvas.rect(left, y, self.width - left - 16 * mm, 4.3 * mm, fill=1, stroke=0)
            canvas.setFillColor(self.color)
            canvas.rect(left, y, (self.width - left - 16 * mm) * value / maximum, 4.3 * mm, fill=1, stroke=0)
            canvas.setFillColor(INK)
            canvas.setFont("Helvetica-Bold", 7.2)
            canvas.drawRightString(self.width, y + 1.2 * mm, str(value))
            y -= 8 * mm


def distribution_page(flow: list[Any], title: str, values: dict[str, int], denominator: int,
                      interpretation: str, style: dict[str, ParagraphStyle], color=LIME) -> None:
    flow.extend([
        Paragraph(title, style["h1"]),
        Paragraph(f"Effective strategic denominator: {denominator:,}. Counts are deterministic labels, not population prevalence or causal performance evidence.", style["body"]),
        BarChart(title, values, color=color), Spacer(1, 4 * mm),
        Paragraph("Interpretation", style["h2"]), Paragraph(interpretation, style["body"]),
        table([["Label", "Count", "Share of eligible"]] + [[label(key), value, percent(value, denominator)] for key, value in list(values.items())[:16]],
              [88 * mm, 35 * mm, 50 * mm], style), PageBreak(),
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--calibration-dir", type=Path, required=True)
    parser.add_argument("--campaign-dir", type=Path, required=True)
    parser.add_argument("--playbook", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    calibration = args.calibration_dir.resolve()
    campaign_dir = args.campaign_dir.resolve()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    style = styles()
    summary = json.loads((run_dir / "derived" / "analysis-summary-10k.json").read_text(encoding="utf-8"))
    calibration_summary = json.loads((calibration / "derived" / "analysis-summary.json").read_text(encoding="utf-8"))
    top = jsonl(run_dir / "derived" / "top-reference-cohort-10k.jsonl")
    campaign = json.loads((campaign_dir / "campaign-manifest.json").read_text(encoding="utf-8"))
    facts = summary["facts"]
    derived = summary["analysis_eligible_derived"]
    eligible = summary["claims_boundary"]["analysis_eligible_videos"]
    status = summary["status"]

    frame = Frame(16 * mm, 15 * mm, A4[0] - 32 * mm, A4[1] - 31 * mm, id="body")
    doc = BaseDocTemplate(
        str(output), pagesize=A4, title="North Hux YouTube 10K Market and Studio Report",
        author="North Hux / ArchFlow — Codex", subject="YouTube broad-screen evidence, market strategy, and ten-script Studio plan",
    )
    doc.addPageTemplates([PageTemplate(id="cover", frames=[frame], onPage=cover), PageTemplate(id="body", frames=[frame], onPage=body)])
    flow: list[Any] = [
        Spacer(1, 28 * mm), Paragraph("NORTH HUX / ARCHFLOW", style["cover_kicker"]),
        Paragraph("YouTube AI-Agent Market Intelligence<br/>and Studio Campaign System", style["cover_title"]),
        Paragraph("10,000-video broad screen · 1,010 creators · evidence-bound two-account strategy · ten original 30-second production plans", style["cover_sub"]),
        Spacer(1, 11 * mm),
        Paragraph(f"Run status: {status} · strategic denominator: {eligible:,} analysis-eligible videos · native Shorts proved: {facts['native_shorts_proved']}", style["cover_sub"]),
        Spacer(1, 23 * mm),
        Paragraph("English report · 26 August 2026<br/>Public YouTube observations + deterministic analysis + local PostgreSQL lineage + provider-disabled Studio planning", style["cover_sub"]),
        NextPageTemplate("body"), PageBreak(),
    ]

    flow.extend([
        Paragraph("Executive conclusion", style["h1"]),
        callout("North Hux should not compete as another AI-news or tool-roundup account. The defensible territory is the operating layer between an impressive demo and a dependable business workflow: diagnose work, choose agency, define authority, connect evidence, evaluate, recover, and prove value.", style["h2"]),
        Spacer(1, 4 * mm),
        Paragraph("The corpus is heavily weighted toward tutorials and agent-building content. The strategic opening is to retain the market’s speed and specificity while changing the payload: a product-manager decision, a visible mechanism, an owned proof surface, an operational safeguard, and one next action. Two product-manager voices make this broad enough to sustain: practical integration and governed operations.", style["body"]),
        Paragraph("What is complete", style["h2"]),
        table([
            ["Layer", "Current evidence", "Decision use"],
            ["Market screen", f"{facts['videos']:,} videos / {facts['creators']:,} creators", "Discovery breadth and collection completeness"],
            ["Strategic subset", f"{eligible:,} deterministic relevance-positive videos", "Topic, format, hook, story, and CTA distributions"],
            ["Calibration review", "211/250 independently accepted", "Precision evidence for the prior 300-account lane"],
            ["Transcripts", f"{facts['transcripts_observed']:,} observed / {facts['transcript_attempts_observed_in_manifest']:,} manifested", "Hook and script-flow evidence; remaining gaps explicit"],
            ["Visuals", f"{facts['frame_sets_observed']:,} sets / {facts['frames_observed']:,} frames", "Local reference only; separate denominator"],
            ["Audience", f"{facts['baseline_comments_retrieved']:,} inherited calibration comments", "Partial voice-of-audience, not 10K-wide sentiment"],
            ["Studio", "10 scripts / 100 individual frames / 10 EDLs", "Owner review and creator capture package"],
        ], [35 * mm, 54 * mm, 84 * mm], style),
        Paragraph("Truth boundary", style["h2"]),
        Paragraph("The 10K set is search-ranked and broad-screened; it is not 10,000 qualified direct competitors and not a probability sample. YouTube duration metadata does not prove native Shorts placement. Creator country is not viewer geography. Public metrics expose views, likes, and comments only; shares, sends, saves, retention, impressions, and conversions remain unavailable.", style["body"]),
        PageBreak(),
    ])

    flow.extend([
        Paragraph("Method: from work to content", style["h1"]),
        Paragraph("The AI Opportunity Audit Playbook is used as strategic context, not as an execution instruction. Its central method starts with work rather than tools: diagnose a workflow, score business value, feasibility, data readiness, risk controllability, and adoption readiness; choose augmentation, automation, or no action; then run the smallest safe pilot with one owner, metric, and review process.", style["body"]),
        table([
            ["Research layer", "Question", "Stored output"],
            ["Discovery", "Which English public videos discuss agents, AI workflows, integration, evaluation, and operations?", "Frozen 10K cohort with raw pointers and request fingerprints"],
            ["Evidence", "What public transcript, metrics, comments, and visual fragments are observable?", "Append-only transcript/frame attempts, hashes, typed gaps"],
            ["Analysis", "What topic, format, hook, story, CTA, and engagement patterns are present?", "Rule-based per-video and per-account artifacts"],
            ["Strategy", "Where can two product-manager operators be differentiated and useful?", "Two tracks, eight territories, seven franchises"],
            ["Script", "How does each short convert one decision into a proof-led story?", "Ten 30-second scripts with claim boundary"],
            ["Studio", "Which shots are creator-recorded, deterministic proof, optional AI context, and gated?", "100 shot/frame files + EDL + owner gates"],
        ], [34 * mm, 77 * mm, 62 * mm], style),
        Spacer(1, 4 * mm),
        callout(f"Playbook evidence file SHA-256: {file_hash(args.playbook.resolve())}. The playbook informed the opportunity lens; the YouTube evidence informed the market claims.", style["small"], MINT),
        PageBreak(),
    ])

    flow.extend([
        Paragraph("Coverage, demographics, and platform caveats", style["h1"]),
        table([
            ["Measure", "Observed", "What it does not prove"],
            ["Creator contribution", f"4–10 videos; max {facts['max_creator_fraction'] * 100:.2f}%", "Audience representativeness"],
            ["Duration candidates", human(facts['format_states'].get('DURATION_CANDIDATE')), "Native Shorts distribution"],
            ["Non-short", human(facts['format_states'].get('NON_SHORT')), "Irrelevance; some are useful format/topic references"],
            ["Creator countries in 300 calibration", "US 96; GB 9; CA 8; AU 2; Europe present; 100 unreported", "Viewer demographics or audience country mix"],
            ["Language", "English-evidenced discovery and transcript preference", "Perfect English-only content or English-only viewers"],
            ["Audience geography target", "US, UK, Canada, Australia, and English-speaking Europe", "An observed current audience; this is a targeting decision"],
        ], [43 * mm, 52 * mm, 78 * mm], style),
        Paragraph("Demographic decision", style["h2"]),
        Paragraph("Because public competitor data does not expose reliable viewer age, role, company size, or country distributions, the strategy should use job-to-be-done segments instead: product managers integrating AI, operators modernizing recurring workflows, founders evaluating build versus buy, and transformation leads responsible for risk and adoption. Owned analytics after publication must supply real viewer demographics.", style["body"]),
        PageBreak(),
    ])

    distribution_page(flow, "Topics in the analysis-eligible subset", derived["topics"], eligible,
                      "Agent building, business operations, and workflow design dominate. Authority, human review, recovery, requirements, and business-problem selection are much smaller—precisely the areas where ArchFlow’s governed workflow experience can create differentiated practical content.", style, LIME)
    distribution_page(flow, "Video types", derived["video_types"], eligible,
                      "Tutorial/build content dominates. North Hux should borrow visible demonstration and stepwise specificity, but organize episodes around decisions and operating consequences rather than tool choreography alone.", style, MINT)
    distribution_page(flow, "Hook mechanisms", derived["hook_types"], eligible,
                      "Questions, contrarian claims, direct benefits, specific results, and demonstration-first openings are reliable attention patterns. More than half of current hook labels may still rely on title proxies while transcript collection is incomplete, so exact shares remain provisional until the final evidence pass.", style, ORANGE)
    distribution_page(flow, "Storytelling structures", derived["storytelling_styles"], eligible,
                      "Claim–proof–takeaway and problem–mechanism–solution are the strongest reusable structures. North Hux’s preferred compression is decision → mechanism → evidence → safeguard → next action, with the first proof surface visible by 6–8 seconds.", style, PURPLE)
    distribution_page(flow, "Calls to action", derived["cta_types"], eligible,
                      "Follow/subscribe is common, but unresolved CTAs remain numerous. North Hux should favor one useful next action: save a decision tool, comment for a template, test a recovery path, or watch the next episode in the sequence.", style, LIME)

    audience = calibration_summary["derived"]["audience_activity"]
    flow.extend([
        Paragraph("Audience activity and opinions", style["h1"]),
        Paragraph(f"This section uses {calibration_summary['facts']['comments_retrieved']:,} bounded comments from the 300-account calibration only. It is qualitative and partial; it is not full-corpus sentiment.", style["body"]),
        BarChart("Comment intent labels", audience, color=MINT), Spacer(1, 4 * mm),
        table([
            ["Signal", "Count", "Editorial implication"],
            ["Positive confirmation", audience.get("positive_confirmation", 0), "Demonstrations and useful explanations earn validation"],
            ["Implementation question", audience.get("implementation_question", 0), "Show prerequisites, data, permissions, and exact next step"],
            ["Pricing or purchase", audience.get("pricing_or_purchase", 0), "Address cost and build/buy constraints without sales hype"],
            ["Skepticism or objection", audience.get("skepticism_or_objection", 0), "State evidence boundary and failure modes early"],
            ["Request or idea", audience.get("request_or_idea", 0), "Use comment requests as a reviewed backlog, not automatic authority"],
            ["Pain or blocker", audience.get("pain_or_blocker", 0), "Translate friction into workflow autopsies and review-queue episodes"],
            ["Unresolved", audience.get("unresolved", 0), "Do not force sentiment where the text does not support it"],
        ], [45 * mm, 22 * mm, 106 * mm], style),
        PageBreak(),
    ])

    flow.extend([
        Paragraph("Performance statistics: descriptive, not causal", style["h1"]),
        table([
            ["Metric", "Eligible subset", "Interpretation boundary"],
            ["Median views", human(derived.get("median_views")), "Search-ranked point-in-time count"],
            ["P90 views", human(derived.get("p90_views")), "Long-tail reference, not expected performance"],
            ["Median engagement proxy", f"{(derived.get('median_engagement_proxy') or 0) * 100:.2f}%", "(likes + reported comments) / views; excludes hidden engagement"],
            ["Native Shorts proved", facts["native_shorts_proved"], "Zero; duration candidate remains separate"],
            ["Frame evidence", f"{facts['frame_sets_observed']}/{facts['videos']}", "Visual denominator is independent and currently partial"],
        ], [47 * mm, 39 * mm, 87 * mm], style),
        Paragraph("Use statistics correctly", style["h2"]),
        Paragraph("The ranking score can choose references for human review; it cannot prove that a hook or visual caused views. Publication experiments should use owned impressions, retention, rewatches, saves, comments, click-through, and qualified business conversations, with predeclared hypotheses and comparable posting windows.", style["body"]),
        PageBreak(),
    ])

    for start in range(0, min(100, len(top)), 25):
        flow.append(Paragraph(f"Reference cohort: ranks {start + 1}–{min(start + 25, len(top))}", style["h1"]))
        rows = [["Rank", "Creator", "Reference", "Topic / type", "Views"]]
        for row in top[start:start + 25]:
            title = esc((row.get("title") or "Untitled")[:62])
            link = f'<link href="{esc(row["canonical_url"])}">{title}</link>'
            rows.append([row.get("reference_rank"), row.get("native_channel_id"), link,
                         f"{label(row.get('primary_topic', ''))}<br/>{label(row.get('video_type', ''))}", human(row.get("views"))])
        flow.extend([table(rows, [12 * mm, 36 * mm, 70 * mm, 40 * mm, 15 * mm], style),
                     Spacer(1, 3 * mm), Paragraph("These links are review references. Titles and public metrics are observed metadata; no source footage is approved for production reuse.", style["small"]), PageBreak()])

    flow.extend([
        Paragraph("Strategic territory and content skeleton", style["h1"]),
        callout("Position: two product managers who show how AI agents become useful business systems—not by promising autonomy, but by making workflow, authority, evidence, recovery, and value visible.", style["h2"]),
        Paragraph("Eight search territories", style["h2"]),
        table([
            ["Territory", "Core buyer question", "North Hux proof surface"],
            ["Workflow diagnosis", "What work is worth changing?", "Trigger/input/decision/action/failure map"],
            ["Agency design", "Assist, recommend, or execute?", "Authority ladder and reversibility"],
            ["Business integration", "How does it fit real systems?", "Owned workflow prototype and receipts"],
            ["Authority/control", "What may it access or change?", "Permission matrix and approval boundary"],
            ["Evidence/evaluation", "How do we know it works?", "Outcome and trajectory checks"],
            ["State/knowledge", "What does it know and remember?", "Source/state/memory/audit architecture"],
            ["Failure/recovery", "What happens when it is wrong?", "Freeze/trace/revoke/restore/review"],
            ["Economics/adoption", "Does it improve the business?", "Error-adjusted business case and usage"],
        ], [38 * mm, 65 * mm, 70 * mm], style),
        Paragraph("Seven recurring franchises", style["h2"]),
        Paragraph("Workflow Autopsy · Agency Ladder · PM Writes the Agent Contract · Failure Lab · Proof Before Scale · ROI Without Fantasy Math · Human Queue Clinic.", style["body"]),
        PageBreak(),
    ])

    flow.extend([
        Paragraph("Two creator accounts", style["h1"]),
        table([
            ["Track", "Role and promise", "Best formats", "Guardrail"],
            ["Creator A — PM / Integration", "Turns business work into bounded AI opportunities and integration decisions", "Workflow autopsy, decision matrix, operating prototype, business case", "No generic tool roundup without a workflow decision"],
            ["Creator B — Governed Operations", "Shows how authority, evidence, state, evaluation, and recovery make agents dependable", "Failure lab, permission teardown, release gate, architecture explainer", "Governance must be visual and operational, not abstract compliance language"],
        ], [38 * mm, 55 * mm, 45 * mm, 35 * mm], style),
        Paragraph("Editorial sequence", style["h2"]),
        table([["#", "Episode", "Track", "Purpose"]] + [
            [item["sequence_position"], item["title"], label(item["creator_track"]), label(item["pillar"])]
            for item in campaign["scripts"]
        ], [10 * mm, 77 * mm, 45 * mm, 41 * mm], style),
        PageBreak(),
    ])

    flow.extend([
        Paragraph("Short-form visual grammar", style["h1"]),
        table([
            ["Time share", "Mode", "Function", "Evidence rule"],
            ["40% / 12s", "Creator A-roll", "Trust, interpretation, transitions between decisions", "Original owner recording only"],
            ["40% / 12s", "Deterministic UI/diagram", "Mechanism and proof", "Owned or synthetic data; must support spoken claim"],
            ["≤7% / 2s", "Optional AI B-roll", "Metaphorical context or emotional reset", "Never evidence, UI, charts, people, results, or likeness"],
            ["13% / 4s", "End card", "One next action and sequence continuity", "Original deterministic brand asset"],
        ], [31 * mm, 42 * mm, 59 * mm, 41 * mm], style),
        Paragraph("Transcript-to-visual flow", style["h2"]),
        Paragraph("0–2s: creator hook. 2–5s: kinetic reframe. 5–8s: creator mechanism. 8–11s: first owned proof. 11–14s: creator implication. 14–18s: deterministic proof diagram. 18–20s: optional context insert. 20–24s: creator conclusion. 24–26s: visual takeaway. 26–30s: end card and next action.", style["body"]),
        callout("If the optional AI insert is not separately approved, replace it with an original creator insert. The edit remains structurally complete without provider generation.", style["body"], ORANGE),
        PageBreak(),
    ])

    for item in campaign["scripts"]:
        package_path = campaign_dir / item["package_uri"]
        package = json.loads(package_path.read_text(encoding="utf-8"))
        flow.extend([
            Paragraph(f"{package['sequence_position']:02d}. {package['title']}", style["h1"]),
            table([
                ["Track", label(package["creator_track"])],
                ["Pillar", label(package["pillar"])],
                ["Hook", package["hook"]],
                ["Proof visual", package["proof_visual"]],
                ["CTA", package["cta"]],
                ["State", "Owner review pending; provider generation, Resolve mutation, and publication blocked"],
            ], [35 * mm, 138 * mm], style, header=False),
            Paragraph("Spoken script", style["h2"]), Paragraph(package["full_script"], style["script"]),
            Paragraph("Why it belongs in the sequence", style["h2"]),
            Paragraph("This episode advances the campaign from diagnosis toward controlled execution. It uses an operator claim, one visible mechanism, one safeguard, and one concrete next action; it is original North Hux synthesis, not a competitor transcript or imitation.", style["body"]),
            Paragraph("Creator capture", style["h2"]),
            Paragraph("Record four A-roll beats in 9:16, two takes each, plus five seconds of room tone. Use calm operator delivery, direct eye line, and one physical emphasis per sentence. Capture any screen proof with owned or synthetic data. No synthetic voice or likeness is planned.", style["body"]),
            PageBreak(),
            Paragraph(f"{package['sequence_position']:02d}. Shot-by-shot production plan", style["h1"]),
        ])
        shot_rows = [["# / time", "Mode", "Narration / visual", "Asset and gate"]]
        for shot in package["shots"]:
            shot_rows.append([
                f"{shot['shot_index']:02d}<br/>{shot['start_ms']/1000:.1f}–{shot['end_ms']/1000:.1f}s",
                f"{label(shot['capture_mode'])}<br/>Evidence: {shot['evidence_role']}",
                f"{shot.get('narration') or '&lt;visual beat&gt;'}<br/><br/><b>Visual:</b> {shot['visual_spec']['composition']}",
                f"{shot['asset_requirement']['owner_action']}<br/><br/><b>State:</b> {shot['generation_state']}<br/><b>Frame:</b> {shot['frame_uri']}",
            ])
        flow.extend([
            table(shot_rows, [20 * mm, 34 * mm, 72 * mm, 47 * mm], style),
            Spacer(1, 3 * mm),
            Paragraph(f"Canonical individual frame files: {Path(item['package_uri']).parent.as_posix()}/frames/01.svg … 10.svg. Contact sheet: {item['contact_sheet_uri']} (index only).", style["small"]),
            PageBreak(),
        ])

    flow.extend([
        Paragraph("Multi-engine system blueprint", style["h1"]),
        table([
            ["Engine", "Consumes", "Produces", "Gate"],
            ["Research", "Approved queries, public platform routes", "Cohorts, source registry, raw pointers, receipts", "Source rights and bounded brief"],
            ["Evidence", "Public metadata, captions, comments, storyboards", "Immutable transcript/frame attempts and hashes", "Typed availability; no invented zero"],
            ["Market analyst", "Evidence artifacts", "Per-video labels, account aggregates, reference ranking", "Strategic denominator and independent review"],
            ["Opportunity analyst", "Market + business workflow", "Augment/automate/no-action recommendation", "Value, feasibility, data, risk, adoption"],
            ["Script engine", "Reviewed strategy and claim map", "Ten versioned original scripts", "Maker/reviewer + owner approval"],
            ["Shot planner", "Script beats and evidence roles", "A-roll/UI/AI-context shot plans and frames", "AI cannot be proof"],
            ["Studio/EDL", "Approved shots and owner media", "Validated timeline and rough-cut plan", "Provider, likeness, Resolve mutation gates"],
            ["Publication", "Approved final video", "Published asset + owned analytics", "Separate publication approval"],
        ], [32 * mm, 47 * mm, 57 * mm, 37 * mm], style),
        Paragraph("Canonical seam", style["h2"]),
        Paragraph("Every durable object is an ArtifactEnvelope: stable ID, run/content identity, schema/version, URI, SHA-256, source hashes, epistemic and rights state, maker/reviewer, review state, public-safety flag, and supersession edge. This prevents separate incompatible truth models across YouTube analysis, PostgreSQL, Studio, EDL, Notion, and WikiLLM.", style["body"]),
        PageBreak(),
    ])

    flow.extend([
        Paragraph("Database, retention, access, and recovery", style["h1"]),
        table([
            ["Layer", "Storage", "Contents"],
            ["Raw", "Run-local files", "Official metadata responses, public subtitle files, local-only storyboards"],
            ["Normalized", "Run-local JSON + PostgreSQL", "Transcript layers, frame manifests, availability/gap states"],
            ["Cleaned", "PostgreSQL", "Accounts, content, public metrics, transcript segments, media/frame pointers"],
            ["Analytical", "PostgreSQL + run artifacts", "Rule labels, reference rankings, evidence completeness"],
            ["Strategy/Studio", "PostgreSQL + public-safe files", "Strategy release, scripts, shots, EDLs, individual frame plans"],
            ["Projection", "Notion and Obsidian/WikiLLM", "Aggregates, tasks, decisions, gates, links and hashes only"],
        ], [34 * mm, 50 * mm, 89 * mm], style),
        Paragraph("Local access", style["h2"]),
        Paragraph("PostgreSQL listens locally on 127.0.0.1:55432 in database north_hux, schema north_hux. Use project scripts and views rather than editing rows manually. Raw transcript, comment, media, and frame bytes stay outside Notion, Obsidian durable memory, and Git.", style["body"]),
        Paragraph("Backup plan", style["h2"]),
        Paragraph("Create two independent backups: a PostgreSQL custom-format dump and a hashed artifact manifest/archive. Record SHA-256, size, retention, and restore-test receipt. Test restore into a disposable database and compare critical table counts and artifact hashes. Git is a reproducible code package, not a database or media backup.", style["body"]),
        PageBreak(),
    ])

    flow.extend([
        Paragraph("Obsidian, WikiLLM, Notion, and Git boundaries", style["h1"]),
        table([
            ["Surface", "Purpose", "Must not contain"],
            ["Obsidian", "Human-readable cases, run summaries, reviewed syntheses, decisions, Studio handoff, gaps", "Raw corpus, credentials, copied comment/transcript dumps"],
            ["WikiLLM", "Independently reviewed reusable memory, insights, runs, issues, decisions", "Unreviewed raw findings or unstable counts"],
            ["Notion", "Owner-facing Kanban, progress, aggregate dashboards, selected reference links, human actions", "Raw transcript/comment/media warehouse"],
            ["GitHub", "Cloneable code, migrations, schemas, tests, docs, public-safe fixtures and handoffs", "keys.md, local DB, raw evidence, private PDFs, media, frames from sources"],
        ], [32 * mm, 70 * mm, 71 * mm], style),
        Paragraph("Optimal sparse vault skeleton", style["h2"]),
        Paragraph("00 Home · 01 Cases · 02 Runs · 03 Evidence Syntheses · 04 PM Tracks and Strategy · 05 Studio · 06 Reviews and Gaps · 07 Decisions · 08 Handoffs · _templates · _views · _maps. Each note carries identifiers, scope, aggregate coverage, evidence/rights/freshness, reviewer state, manifest links/hashes, and the next gate.", style["body"]),
        PageBreak(),
    ])

    flow.extend([
        Paragraph("Owner review and next actions", style["h1"]),
        table([
            ["Priority", "Human action", "Why required"],
            ["1", "Review the ten hooks, spoken scripts, CTAs, and creator-track ownership", "Editorial approval cannot be inferred from analysis"],
            ["2", "Choose the first three episodes and approve or reject each optional 2-second AI B-roll slot", "Provider generation remains separately gated and optional"],
            ["3", "Record the four A-roll beats per selected episode using the capture notes", "Original creator media is required for production"],
            ["4", "Approve the owned prototype/UI proof for each selected episode", "Proof must not rely on generated or competitor imagery"],
            ["5", "Approve provider, budget, prompt, rights, and data packet if AI context inserts are desired", "No paid/provider call has run"],
            ["6", "Approve the exact Resolve/Studio mutation packet after media is received", "Planning does not authorize editing mutation"],
            ["7", "Approve publication separately after rough-cut review", "Publishing and analytics readback are independent gates"],
            ["8", "Approve the exact Obsidian target-note correction packet", "Broad vault approval is intentionally insufficient for those external writes"],
        ], [17 * mm, 94 * mm, 62 * mm], style),
        Paragraph("Questions to decide", style["h2"]),
        Paragraph("Which creator owns each track? Which three episodes should launch first? Should the voice be more technical, more commercial, or split by account? What concrete owned ArchFlow workflows can be shown without exposing private client data? Which CTA should lead to a public template versus a conversation? What weekly publishing capacity can the two creators sustain?", style["body"]),
        callout("Recommended launch order: 1) Your AI Agent Is Not an Employee, 2) Automate the Workflow, Not the Job Title, 3) Watch the Agent Fail Safely. Together they establish the mental model, the opportunity method, and the operational proof standard.", style["body"], LIME),
    ])

    doc.build(flow)
    print(json.dumps({"output": str(output), "sha256": file_hash(output), "pages_expected": "35+", "status": status}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
