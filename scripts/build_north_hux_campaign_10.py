#!/usr/bin/env python3
"""Build the provider-disabled North Hux ten-video campaign and shot package.

The output is an original, evidence-bound Studio handoff. It creates no generated
media and never treats optional AI B-roll as proof.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


CAMPAIGN = [
    {
        "key": "agent-not-employee",
        "title": "Your AI Agent Is Not an Employee",
        "track": "governed_agent_operations",
        "pillar": "authority_and_control",
        "hook": "Your AI agent is not an employee.",
        "lines": [
            "Your AI agent is not an employee.",
            "It is a workflow that can read, decide, and sometimes act.",
            "If you cannot name its inputs, tools, and authority, you do not have an agent. You have an unbounded risk.",
            "Give it a contract: allowed data, allowed actions, required evidence, and a human stop.",
            "Then test failure before you test scale.",
            "Reliable agents are bounded, observable, and recoverable.",
        ],
        "proof": "Five-node agent contract: INPUTS → TOOLS → AUTHORITY → EVIDENCE → HUMAN STOP.",
        "ai_context": "Abstract glass office corridor with one clearly bounded luminous workflow lane; no logos, people, dashboards, numbers, or proof claims; vertical cinematic insert.",
        "cta": "Save this contract before your next agent build.",
    },
    {
        "key": "workflow-not-job",
        "title": "Automate the Workflow, Not the Job Title",
        "track": "pm_integration",
        "pillar": "workflow_diagnosis",
        "hook": "Do not automate a job title.",
        "lines": [
            "Do not automate a job title.",
            "A job is a bundle of decisions, exceptions, handoffs, and trust.",
            "Start with one recurring workflow and draw the trigger, inputs, decision, action, and failure path.",
            "Then choose: augment the human, automate one step, or leave it alone.",
            "The smallest safe pilot has one owner, one metric, and one review queue.",
            "That is how AI improves work without pretending people are process diagrams.",
        ],
        "proof": "Workflow decomposition canvas with five stages and an explicit AUGMENT / AUTOMATE / NO ACTION decision.",
        "ai_context": "Close-up of modular paper workflow cards separating cleanly on a dark table; symbolic context only, no readable data or interfaces.",
        "cta": "Comment WORKFLOW for the audit template.",
    },
    {
        "key": "three-levels-agency",
        "title": "One Workflow, Three Levels of Agency",
        "track": "pm_integration",
        "pillar": "agency_design",
        "hook": "The same workflow can contain three different agents.",
        "lines": [
            "The same workflow can contain three different levels of agency.",
            "An assistant drafts. A copilot recommends. A delegated agent executes inside a boundary.",
            "Use the same customer request and change only decision authority.",
            "Drafting is easy to reverse. Recommendations need evidence. Execution needs permissions, limits, and rollback.",
            "Do not buy the most autonomous option by default.",
            "Choose the lowest agency level that produces the business result.",
        ],
        "proof": "Side-by-side authority ladder: DRAFT → RECOMMEND → EXECUTE, with reversibility and review controls.",
        "ai_context": "Three ascending illuminated platforms in an abstract operations space; no humanoid robots, text, charts, or claimed results.",
        "cta": "Which level is your workflow actually ready for?",
    },
    {
        "key": "permission-not-yet",
        "title": "The Permission Your Agent Should Not Have Yet",
        "track": "governed_agent_operations",
        "pillar": "authority_and_control",
        "hook": "The dangerous permission is not read. It is irreversible write.",
        "lines": [
            "The dangerous permission is not read. It is irreversible write.",
            "Reading data creates exposure. Writing creates consequences.",
            "Start with read, then propose, then reversible write, and only later bounded execution.",
            "For every step, log the source, decision, tool call, and outcome.",
            "If rollback is impossible, require human approval before the action.",
            "Authority should expand after evidence, never before it.",
        ],
        "proof": "Permission matrix with READ, PROPOSE, REVERSIBLE WRITE, and EXECUTE; approval gate before irreversible action.",
        "ai_context": "A sealed red switch behind clear glass in a minimal control room; dramatic context only, no UI or operational evidence.",
        "cta": "Audit one irreversible action today.",
    },
    {
        "key": "build-buy-wrong-question",
        "title": "Build vs Buy Is the Wrong First Question",
        "track": "pm_integration",
        "pillar": "business_integration",
        "hook": "Build or buy? Wrong first question.",
        "lines": [
            "Build or buy? Wrong first question.",
            "First ask which control surface your workflow needs.",
            "Can you inspect evidence, change permissions, replace a model, recover state, and export your history?",
            "A bought tool can be right when the workflow is standard and reversible.",
            "Build when differentiation, integration depth, or control is the product.",
            "Choose by constraints and exit cost, not demo excitement.",
        ],
        "proof": "Decision table scoring differentiation, integration depth, control, reversibility, and exit cost.",
        "ai_context": "Two unlabeled architectural paths joining one operations hub; abstract strategic context with no brands, prices, or performance claims.",
        "cta": "Save the five-question decision table.",
    },
    {
        "key": "rag-not-memory",
        "title": "RAG Is Not Memory—and Neither Is Chat History",
        "track": "governed_agent_operations",
        "pillar": "state_and_knowledge",
        "hook": "RAG is not memory.",
        "lines": [
            "RAG is not memory. And chat history is not an operating record.",
            "Retrieval finds source material. Working state tracks the current job.",
            "Durable memory preserves reviewed decisions. Audit evidence proves what happened.",
            "Mix these layers and stale context becomes invisible authority.",
            "Separate source, state, decision, and receipt—with retention rules for each.",
            "Your agent becomes easier to debug because every fact has a home.",
        ],
        "proof": "Four-layer knowledge architecture: SOURCE / WORKING STATE / REVIEWED MEMORY / AUDIT RECEIPT.",
        "ai_context": "Four transparent archive layers floating apart in a dark studio; metaphor only, no documents, interfaces, or factual claims.",
        "cta": "Map these four layers in your stack.",
    },
    {
        "key": "eval-not-permission",
        "title": "A Passing Eval Is Not Permission to Deploy",
        "track": "governed_agent_operations",
        "pillar": "evaluation_and_evidence",
        "hook": "A passing eval is not permission to deploy.",
        "lines": [
            "A passing eval is not permission to deploy.",
            "An eval measures behavior on a defined set. Production adds new users, tools, data, and failure costs.",
            "Separate quality evidence from release authority.",
            "Require outcome tests, trajectory checks, permission review, monitoring, and a rollback owner.",
            "Then release to the smallest reversible scope.",
            "Evaluation informs the gate. It does not replace the gate.",
        ],
        "proof": "Release gate showing QUALITY, TRAJECTORY, PERMISSIONS, MONITORING, and ROLLBACK as independent checks.",
        "ai_context": "A green test light stopping before a second guarded doorway; abstract context only, no test scores or deployment proof.",
        "cta": "Send this to whoever owns your release gate.",
    },
    {
        "key": "fail-safely",
        "title": "Watch the Agent Fail Safely",
        "track": "governed_agent_operations",
        "pillar": "failure_and_recovery",
        "hook": "This agent just sent the wrong price.",
        "lines": [
            "This agent just sent the wrong price.",
            "Do not hide the failure. Freeze the workflow.",
            "Trace the input, model decision, tool call, and evidence it used.",
            "Revoke the action, restore the last good state, and route the case to a human.",
            "Now save the failure as a permanent evaluation case.",
            "Reliable agents are not failure-free. They are recoverable.",
        ],
        "proof": "Controlled fictional failure trace: FREEZE → TRACE → REVOKE → RESTORE → REVIEW → TEST FIXTURE.",
        "ai_context": "A domino chain stopping safely before the final tile; metaphor only, no real customer event, prices, or interface evidence.",
        "cta": "Test one recovery path before your next demo.",
    },
    {
        "key": "human-review-queue",
        "title": "What Belongs in the Human Review Queue?",
        "track": "pm_integration",
        "pillar": "human_review",
        "hook": "Human review is not a safety strategy until you define the queue.",
        "lines": [
            "Human review is not a safety strategy until you define the queue.",
            "Route work by ambiguity, reversibility, value, and risk.",
            "Low ambiguity and easy rollback can flow automatically.",
            "High value or irreversible action needs named approval and evidence.",
            "Measure queue age, override rate, and repeated exception types.",
            "The goal is not more review. It is review where human judgment changes the outcome.",
        ],
        "proof": "Two-by-two routing matrix plus queue metrics: age, override rate, exception recurrence.",
        "ai_context": "A calm human silhouette at a single illuminated checkpoint while routine paths continue; no faces, data, or product UI.",
        "cta": "Build the queue before you activate execution.",
    },
    {
        "key": "business-case-reality",
        "title": "The Agent Business Case After Reality",
        "track": "pm_integration",
        "pillar": "economics_and_adoption",
        "hook": "Your automation ROI is probably missing four costs.",
        "lines": [
            "Your automation ROI is probably missing four costs.",
            "Time saved is only the first line.",
            "Subtract integration, review, exceptions, and change adoption.",
            "Then adjust the benefit by actual usage and error cost.",
            "Pilot one workflow with one owner, one baseline, and one outcome metric.",
            "Scale only when the workflow and customer outcome improve—not when the demo looks impressive.",
        ],
        "proof": "Transparent business-case equation: benefit × adoption − integration − review − exceptions − error cost.",
        "ai_context": "A polished demo pedestal dissolving into a real operations floor; conceptual context only, no currency values or ROI proof.",
        "cta": "Use the real equation before you promise savings.",
    },
]


SHOT_TEMPLATE = [
    (0, 2000, "creator_aroll", "none", 0),
    (2000, 5000, "deterministic_overlay", "context", 1),
    (5000, 8000, "creator_aroll", "none", 2),
    (8000, 11000, "screen_demo", "proof", None),
    (11000, 14000, "creator_aroll", "none", 3),
    (14000, 18000, "deterministic_overlay", "proof", 4),
    (18000, 20000, "ai_generated_broll", "context", None),
    (20000, 24000, "creator_aroll", "none", 5),
    (24000, 26000, "deterministic_overlay", "context", None),
    (26000, 30000, "end_card", "none", None),
]


COLORS = {
    "creator_aroll": "#C8FF32",
    "screen_demo": "#73E2C6",
    "deterministic_overlay": "#FFB000",
    "ai_generated_broll": "#B9A7FF",
    "end_card": "#F3EEDC",
}


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def project_uri(path: Path) -> str:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f"evidence file must be under project root: {resolved}")
    return resolved.relative_to(ROOT).as_posix()


def dump_json(path: Path, payload: Any) -> str:
    data = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return digest_bytes(data)


def svg_frame(script: dict[str, Any], shot: dict[str, Any], sequence: int) -> str:
    color = COLORS[shot["capture_mode"]]
    title = html.escape(script["title"])
    narration = html.escape(shot.get("narration") or "No narration—visual beat.")
    visual = html.escape(shot["visual_spec"]["composition"])
    prompt = html.escape(shot["asset_requirement"].get("prompt") or "Original creator or deterministic graphic asset.")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">
<rect width="1080" height="1920" fill="#101210"/>
<rect width="1080" height="30" fill="{color}"/>
<text x="70" y="105" fill="#F3EEDC" font-family="Helvetica,Arial" font-size="34" font-weight="700">NORTH HUX / {sequence:02d}</text>
<text x="70" y="172" fill="{color}" font-family="Helvetica,Arial" font-size="24" font-weight="700">{html.escape(shot['capture_mode'].replace('_', ' ').upper())} · {shot['start_ms']/1000:.1f}–{shot['end_ms']/1000:.1f}s · {html.escape(shot['evidence_role'].upper())}</text>
<foreignObject x="70" y="235" width="940" height="360"><div xmlns="http://www.w3.org/1999/xhtml" style="font:700 62px/1.05 Helvetica,Arial;color:#F3EEDC">{title}</div></foreignObject>
<rect x="70" y="620" width="940" height="480" rx="32" fill="#1A1D1A" stroke="{color}" stroke-width="5"/>
<foreignObject x="115" y="680" width="850" height="360"><div xmlns="http://www.w3.org/1999/xhtml" style="font:500 42px/1.2 Helvetica,Arial;color:#F3EEDC">{visual}</div></foreignObject>
<text x="70" y="1190" fill="{color}" font-family="Helvetica,Arial" font-size="25" font-weight="700">NARRATION</text>
<foreignObject x="70" y="1230" width="940" height="250"><div xmlns="http://www.w3.org/1999/xhtml" style="font:400 37px/1.25 Helvetica,Arial;color:#F3EEDC">{narration}</div></foreignObject>
<text x="70" y="1535" fill="{color}" font-family="Helvetica,Arial" font-size="25" font-weight="700">ASSET / CAPTURE INSTRUCTION</text>
<foreignObject x="70" y="1575" width="940" height="230"><div xmlns="http://www.w3.org/1999/xhtml" style="font:400 28px/1.25 Helvetica,Arial;color:#C9C6BA">{prompt}</div></foreignObject>
<text x="70" y="1870" fill="#777A72" font-family="Helvetica,Arial" font-size="21">Frame plan only · provider generation NOT RUN · 9:16</text>
</svg>'''


def make_shots(script: dict[str, Any]) -> list[dict[str, Any]]:
    shots = []
    for index, (start, end, mode, role, line_index) in enumerate(SHOT_TEMPLATE, 1):
        narration = script["lines"][line_index] if line_index is not None else ""
        if mode == "creator_aroll":
            composition = "Creator speaking directly to camera. Chest-up 9:16, eye line at upper third, practical operator tone, natural hand movement, clean depth separation."
            requirement = {"owner_action": "Record original creator take", "prompt": "Record two clean takes plus five seconds of room tone; neutral wardrobe; no synthetic likeness."}
            generation = "not_run"
            rights = "owner_media_required"
        elif mode == "screen_demo":
            composition = script["proof"]
            requirement = {"owner_action": "Capture an owned deterministic prototype or render the supplied diagram", "prompt": "Use only owned/synthetic example data. Screen must visibly support the claim; no competitor UI reuse."}
            generation = "not_run"
            rights = "original_plan"
        elif mode == "ai_generated_broll":
            composition = "Optional two-second metaphorical context insert. It must not carry evidence, results, UI, numbers, people, likeness, or logos."
            requirement = {"owner_action": "Approve provider, prompt, budget, and rights before generation", "prompt": script["ai_context"]}
            generation = "blocked_approval"
            rights = "provider_review_required"
        elif mode == "end_card":
            composition = f"North Hux end card: {script['cta']}"
            requirement = {"owner_action": "Approve CTA and brand lockup", "prompt": "Render deterministically from North Hux typography and color tokens."}
            generation = "not_run"
            rights = "original_plan"
        else:
            composition = script["proof"] if role == "proof" else f"Kinetic type supports: {narration or script['cta']}"
            requirement = {"owner_action": "Review exact wording", "prompt": "Render as deterministic motion typography/diagram; never fabricate screenshots, statistics, or results."}
            generation = "not_run"
            rights = "original_plan"
        shots.append({
            "shot_index": index,
            "start_ms": start,
            "end_ms": end,
            "capture_mode": mode,
            "evidence_role": role,
            "narration": narration,
            "on_screen_text": script["hook"] if index == 1 else (script["cta"] if index >= 9 else ""),
            "visual_spec": {"aspect_ratio": "9:16", "composition": composition, "safe_zone": "120px sides; 220px top/bottom"},
            "transition": {"in": "hard_cut" if index in (1, 3, 5, 8) else "match_cut", "out": "hard_cut", "max_ms": 160},
            "audio": {"creator_voice": mode == "creator_aroll", "music": "low instrumental bed", "sfx": "single restrained accent" if index in (1, 4, 6) else "none"},
            "source_evidence_ids": [],
            "asset_requirement": requirement,
            "generation_state": generation,
            "rights_state": rights,
            "acceptance_checks": ["9:16 safe zones pass", "claim and visual agree", "no unlicensed source media", "AI B-roll is not evidence"],
        })
    return shots


def contact_sheet(script: dict[str, Any], shots: list[dict[str, Any]]) -> str:
    panels = []
    for idx, shot in enumerate(shots):
        x = 40 + (idx % 2) * 500
        y = 170 + (idx // 2) * 300
        color = COLORS[shot["capture_mode"]]
        label = html.escape(shot["capture_mode"].replace("_", " ").upper())
        text = html.escape((shot.get("narration") or shot["visual_spec"]["composition"])[:92])
        panels.append(f'<rect x="{x}" y="{y}" width="460" height="250" rx="20" fill="#1A1D1A" stroke="{color}" stroke-width="4"/><text x="{x+24}" y="{y+42}" fill="{color}" font-family="Helvetica" font-size="20" font-weight="700">{idx+1:02d} · {label}</text><foreignObject x="{x+24}" y="{y+68}" width="412" height="145"><div xmlns="http://www.w3.org/1999/xhtml" style="font:400 24px/1.2 Helvetica;color:#F3EEDC">{text}</div></foreignObject>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1800" viewBox="0 0 1080 1800"><rect width="1080" height="1800" fill="#101210"/><text x="40" y="70" fill="#C8FF32" font-family="Helvetica" font-size="28" font-weight="700">CONTACT INDEX — INDIVIDUAL SVG FRAMES ARE CANONICAL</text><foreignObject x="40" y="95" width="1000" height="70"><div xmlns="http://www.w3.org/1999/xhtml" style="font:700 38px Helvetica;color:#F3EEDC">{html.escape(script['title'])}</div></foreignObject>{''.join(panels)}</svg>'''


def validate_package(package: dict[str, Any]) -> None:
    shots = package["shots"]
    assert len(shots) == 10
    assert shots[0]["start_ms"] == 0 and shots[-1]["end_ms"] == package["target_duration_ms"]
    assert all(left["end_ms"] == right["start_ms"] for left, right in zip(shots, shots[1:]))
    ai_ms = sum(s["end_ms"] - s["start_ms"] for s in shots if s["capture_mode"] == "ai_generated_broll")
    ar_ms = sum(s["end_ms"] - s["start_ms"] for s in shots if s["capture_mode"] == "creator_aroll")
    ui_ms = sum(s["end_ms"] - s["start_ms"] for s in shots if s["capture_mode"] in {"screen_demo", "deterministic_overlay"})
    assert ai_ms / package["target_duration_ms"] <= 0.07
    assert 0.39 <= ar_ms / package["target_duration_ms"] <= 0.42
    assert 0.39 <= ui_ms / package["target_duration_ms"] <= 0.42
    assert all(s["evidence_role"] != "proof" for s in shots if s["capture_mode"] == "ai_generated_broll")
    word_count = len(package["full_script"].split())
    assert 55 <= word_count <= 100, (package["script_key"], word_count)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--evidence-summary", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    evidence = json.loads(args.evidence_summary.read_text(encoding="utf-8"))
    evidence_hash = digest_bytes(args.evidence_summary.read_bytes())
    output.mkdir(parents=True, exist_ok=True)

    manifest_scripts = []
    for sequence, script in enumerate(CAMPAIGN, 1):
        shots = make_shots(script)
        package = {
            "schema": "north-hux.script-package.v1",
            "script_key": script["key"],
            "version": 1,
            "sequence_position": sequence,
            "title": script["title"],
            "creator_track": script["track"],
            "pillar": script["pillar"],
            "primary_platform": "youtube_shorts",
            "adaptation_targets": ["instagram_reels", "tiktok"],
            "target_duration_ms": 30000,
            "hook": script["hook"],
            "full_script": " ".join(script["lines"]),
            "proof_visual": script["proof"],
            "cta": script["cta"],
            "claim_state": "evidence_bound_and_hypothesis_labeled",
            "evidence_bundle_sha256": evidence_hash,
            "evidence_boundary": evidence["claims_boundary"],
            "owner_state": "owner_review_pending",
            "provider_generation_state": "blocked_approval",
            "creator_media_state": "not_received",
            "resolve_mutation_state": "blocked_approval",
            "publication_state": "blocked_approval",
            "shots": shots,
        }
        validate_package(package)
        script_dir = output / f"{sequence:02d}-{script['key']}"
        frames_dir = script_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        for shot in shots:
            frame = frames_dir / f"{shot['shot_index']:02d}.svg"
            frame.write_text(svg_frame(script, shot, sequence), encoding="utf-8")
            shot["frame_uri"] = frame.relative_to(output).as_posix()
            shot["frame_sha256"] = digest_bytes(frame.read_bytes())
        (script_dir / "contact-sheet.svg").write_text(contact_sheet(script, shots), encoding="utf-8")
        package_hash = dump_json(script_dir / "script-package.json", package)
        edit_plan = {
            "schema": "north-hux.studio-edit-plan.v1",
            "script_key": script["key"],
            "timeline": shots,
            "audio_policy": "Original creator voice only; no cloning or synthetic likeness.",
            "evidence_policy": "Only deterministic UI/diagrams may carry proof. AI B-roll is context-only.",
            "provider_generation_state": "blocked_approval",
            "creator_media_state": "not_received",
            "resolve_mutation_state": "blocked_approval",
            "publication_state": "blocked_approval",
        }
        edit_hash = dump_json(script_dir / "studio-edit-plan.json", edit_plan)
        markdown = [
            f"# {sequence:02d}. {script['title']}", "",
            f"Creator track: `{script['track']}`  ",
            f"Pillar: `{script['pillar']}`  ",
            "State: `OWNER_REVIEW_PENDING`; generation/editing/publication `BLOCKED_APPROVAL`.", "",
            "## Spoken script", "", package["full_script"], "", "## Creator capture", "",
            "Record four creator A-roll beats (0–2s, 5–8s, 11–14s, 20–24s), two takes each, with five seconds of room tone. The screen proof and deterministic diagrams must use owned or synthetic data. The 18–20s AI B-roll slot is optional and may be replaced with an original creator insert.", "",
            "## Shot files", "",
        ]
        markdown.extend(f"- `{shot['frame_uri']}` — {shot['start_ms']/1000:.1f}–{shot['end_ms']/1000:.1f}s, `{shot['capture_mode']}`, evidence `{shot['evidence_role']}`." for shot in shots)
        (script_dir / "README.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
        manifest_scripts.append({
            "sequence_position": sequence,
            "script_key": script["key"],
            "title": script["title"],
            "creator_track": script["track"],
            "pillar": script["pillar"],
            "package_uri": (script_dir / "script-package.json").relative_to(output).as_posix(),
            "package_sha256": package_hash,
            "edit_plan_uri": (script_dir / "studio-edit-plan.json").relative_to(output).as_posix(),
            "edit_plan_sha256": edit_hash,
            "contact_sheet_uri": (script_dir / "contact-sheet.svg").relative_to(output).as_posix(),
        })

    manifest = {
        "schema": "north-hux.campaign-manifest.v1",
        "campaign_key": "north-hux-youtube-10-v1",
        "market_position": "AI-agent integration in business: workflow diagnosis, authority, evidence, evaluation, recovery, and measurable adoption.",
        "audience": "English-speaking product managers, operators, founders, and AI transformation leads, with primary relevance to the US, UK, Canada, Australia, and Europe.",
        "platform": "youtube_shorts",
        "script_count": len(manifest_scripts),
        "evidence_summary_uri": project_uri(args.evidence_summary),
        "evidence_summary_sha256": evidence_hash,
        "native_shorts_claim": "not_proved_for_market_corpus",
        "provider_generation_state": "blocked_approval",
        "scripts": manifest_scripts,
    }
    dump_json(output / "campaign-manifest.json", manifest)
    print(json.dumps({"output": str(output), "scripts": len(manifest_scripts), "frames": len(manifest_scripts) * 10}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
