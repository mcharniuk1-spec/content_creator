#!/usr/bin/env python3
"""Build lightweight, provider-disabled short-form storyboard framework packages."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "studio" / "framework-library" / "v1"
GENERATED_AT = "2026-08-25T00:00:00+03:00"

VIEWER_JOBS = [
    "identify_problem", "assess_risk", "learn_mechanism",
    "compare_options", "verify_claim", "imagine_outcome",
]
BROLL_FUNCTIONS = [
    "establish_context", "concretize_abstraction", "demonstrate_process",
    "prove_state", "contrast", "attention_reset",
]
PROOF_FORMS = [
    "observed_artifact", "calculation", "paraphrased_source",
    "process_trace", "constraint", "worked_example",
]
VISUAL_GRAMMARS = [
    "kinetic_type", "split_screen", "object_macro",
    "mock_screen_capture", "diagram_build", "layered_pip",
]
PACING = ["rapid_beat", "measured_beat", "held_reveal", "slow_observation"]
TRANSITIONS = ["hard_cut", "match_on_action", "graphic_reveal", "push", "wipe", "dissolve", "cut_on_sound", "none"]
AROLL = ["full_open", "delayed_reveal", "voice_over_broll", "picture_in_picture", "return_cut", "absent"]
SOUND = ["voice_anchor", "voice_plus_accent", "music_pulse", "accent_sfx", "silence_drop", "ambient_bed"]
TEXT = ["headline_only", "question_card", "keyword_captions", "proof_callout", "labels", "step_counter", "no_text"]
CTA = ["answer_question", "next_step", "save_reference", "recap", "loop_to_open", "no_cta", "comment_prompt"]

FAMILIES = [
    {
        "family": "pattern_interrupt", "hook": "visual_anomaly", "kind": "hook",
        "source": "SRC-WEB-001", "evidence": "EVID-WEB-001",
        "names": ["Visual Mismatch", "Silent Freeze", "Inverted Result", "Wrong Tool Macro", "Abrupt Scale Shift", "Missing Object"],
        "uses": ["Break an expected visual pattern", "Create a deliberate attention reset", "Lead with the outcome before context", "Make the wrong choice physically visible", "Move from extreme close-up to system view", "Use absence as the first visible clue"],
        "beats": ["anomaly", "name tension", "orient", "connect", "payoff", "clean exit"],
        "labels": ["WAIT", "WHAT CHANGED?", "THE CLUE", "CONNECT IT", "NOW IT FITS", "RETURN"],
    },
    {
        "family": "diagnostic_question", "hook": "diagnostic_question", "kind": "hook_intro",
        "source": "SRC-WEB-004", "evidence": "EVID-WEB-004",
        "names": ["Hidden Bottleneck", "Risk Check", "Cost Leak", "Tool Fit", "Owner Gap", "Proof Gap"],
        "uses": ["Help viewers locate a workflow bottleneck", "Ask for a fast self-assessment", "Expose an invisible repeated cost", "Test whether a tool matches the job", "Reveal missing decision ownership", "Ask what evidence is actually present"],
        "beats": ["question", "symptom", "choice", "diagnosis", "mechanism", "answer frame"],
        "labels": ["IS THIS YOU?", "THE SYMPTOM", "CHOOSE", "DIAGNOSIS", "WHY", "ANSWER"],
    },
    {
        "family": "contradiction", "hook": "contradiction", "kind": "hook_intro",
        "source": "SRC-WEB-002", "evidence": "EVID-WEB-002",
        "names": ["Faster Made Slower", "Automation Needs a Gate", "More Data, Less Clarity", "Busy Is Not Progress", "AI Is Not Autonomy", "Feature Is Not Outcome"],
        "uses": ["Open on a counterintuitive operational result", "Separate automation from authorization", "Contrast volume with decision quality", "Separate activity from movement", "Correct an autonomy assumption", "Separate product surface from user result"],
        "beats": ["contradiction", "expected model", "break", "explanation", "bounded rule", "reframe"],
        "labels": ["THE OPPOSITE", "YOU EXPECT", "BUT", "HERE'S WHY", "THE RULE", "REFRAME"],
    },
    {
        "family": "consequence", "hook": "consequence", "kind": "hook_broll",
        "source": "SRC-WEB-004", "evidence": "EVID-WEB-005",
        "names": ["Ignored Warning", "One Bad Handoff", "Stale Metric", "Missing Is Not Zero", "Bypassed Approval", "Hidden Rollback"],
        "uses": ["Show the cost of ignoring a visible warning", "Trace one broken handoff downstream", "Make freshness failure concrete", "Prevent null-to-zero confusion", "Show risk from bypassing a gate", "Reveal that recovery was never planned"],
        "beats": ["failure result", "first cause", "chain reaction", "human impact", "control", "return to speaker"],
        "labels": ["THIS FAILED", "FIRST CAUSE", "THEN", "IMPACT", "CONTROL", "BACK TO YOU"],
    },
    {
        "family": "before_after", "hook": "before_after", "kind": "intro_broll",
        "source": "SRC-WEB-004", "evidence": "EVID-WEB-006",
        "names": ["Clutter to Map", "Manual to Governed", "Claim to Receipt", "Inbox to Queue", "Flat List to Graph", "Guessing to Experiment"],
        "uses": ["Transform scattered context into a navigable map", "Show added governance without hype", "Turn an assertion into inspectable evidence", "Convert reactive intake into controlled flow", "Expose relationships hidden by a list", "Move from belief to a bounded test"],
        "beats": ["before", "friction", "change action", "after", "limitation", "hold comparison"],
        "labels": ["BEFORE", "FRICTION", "CHANGE", "AFTER", "LIMIT", "COMPARE"],
    },
    {
        "family": "countdown", "hook": "countdown", "kind": "hook_intro",
        "source": "SRC-WEB-005", "evidence": "EVID-WEB-007",
        "names": ["Three Warning Signs", "Three Fast Checks", "Five System Layers", "Four Common Mistakes", "Three Cut Rules", "Five Proof States"],
        "uses": ["Package a diagnostic list", "Give a rapid preflight", "Orient viewers inside a system", "Expose predictable errors", "Teach cut logic compactly", "Differentiate evidence states"],
        "beats": ["number promise", "item one", "item two", "item three", "pattern", "save exit"],
        "labels": ["3 THINGS", "01", "02", "03", "THE PATTERN", "SAVE"],
    },
    {
        "family": "object_demo", "hook": "object_demo", "kind": "hook_broll",
        "source": "SRC-WEB-008", "evidence": "EVID-WEB-009",
        "names": ["Domino Chain", "Transparent Box", "Leaking Bucket", "Red String Trace", "Balance Scale", "Lock and Key"],
        "uses": ["Demonstrate dependency and propagation", "Make hidden system state visible", "Visualize compounding resource loss", "Trace provenance through steps", "Compare competing constraints", "Explain access and approval boundaries"],
        "beats": ["object action", "macro detail", "cause", "system analogy", "rule", "object resolves"],
        "labels": ["WATCH", "DETAIL", "CAUSE", "SYSTEM", "RULE", "RESOLVE"],
    },
    {
        "family": "proof_reveal", "hook": "reveal", "kind": "hook_broll",
        "source": "SRC-WEB-003", "evidence": "EVID-WEB-010",
        "names": ["Receipt Reveal", "Screen Proof", "Calculation Reveal", "Annotation Peel", "Source Stack", "Constraint Card"],
        "uses": ["Reveal a dated execution receipt", "Show a deterministic screen state", "Walk from inputs to a result", "Expose meaning one annotation at a time", "Layer sources behind a claim", "Lead with the boundary that makes a claim honest"],
        "beats": ["claim", "hide/reveal", "proof close-up", "trace", "limitation", "verdict"],
        "labels": ["THE CLAIM", "REVEAL", "PROOF", "TRACE", "LIMIT", "VERDICT"],
    },
    {
        "family": "story_in_progress", "hook": "story_in_progress", "kind": "intro_broll",
        "source": "SRC-WEB-001", "evidence": "EVID-WEB-011",
        "names": ["Missed Handoff", "Late-Night Alert", "Launch-Day Choice", "Review Collision", "One-Minute Audit", "Choice at the Threshold"],
        "uses": ["Enter at the moment context disappears", "Start with an operational alert", "Open on a bounded decision", "Show two reviewers reaching different states", "Compress an audit into causal beats", "Pause before an irreversible action"],
        "beats": ["scene in progress", "stakes", "decision", "action", "result", "lesson"],
        "labels": ["IN PROGRESS", "STAKES", "DECIDE", "ACT", "RESULT", "LESSON"],
    },
    {
        "family": "process_broll", "hook": "direct_promise", "kind": "broll",
        "source": "SRC-WEB-008", "evidence": "EVID-WEB-012",
        "names": ["Hands Build the System", "Macro Tool Sequence", "Environment Transformation", "Screen-to-Real Match", "Rhythmic Assembly", "Closing the Loop"],
        "uses": ["Cover narration with concrete assembly", "Turn a tool explanation into macro cutaways", "Establish place and change over time", "Match an interface state to physical action", "Use repeated action as a pacing bed", "Visualize feedback returning to the start"],
        "beats": ["establish", "action one", "action two", "detail", "completed state", "A-roll return"],
        "labels": ["CONTEXT", "STEP 1", "STEP 2", "DETAIL", "DONE", "RETURN"],
    },
]

PALETTES = [
    ("#0b1420", "#80e1d1", "#f7e7c6"),
    ("#151126", "#b89cff", "#f6d365"),
    ("#102019", "#85d18a", "#f8d49d"),
    ("#231218", "#ff8f9d", "#f9e6c8"),
    ("#0f1b2a", "#62b5ff", "#f2c879"),
    ("#171717", "#f0b44d", "#e9e9e9"),
]


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def canonical_hash(payload: dict) -> str:
    material = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(material).hexdigest()


def dump_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def aroll_state(mode: str, index: int, frame_count: int) -> str:
    if mode == "full_open":
        return "full" if index == 0 else ("return_cut" if index == frame_count - 1 else "voice_over")
    if mode == "delayed_reveal":
        reveal = min(2, frame_count - 2)
        return "absent" if index < reveal else ("full" if index == reveal else ("return_cut" if index == frame_count - 1 else "voice_over"))
    if mode == "voice_over_broll":
        return "return_cut" if index == frame_count - 1 else "voice_over"
    if mode == "picture_in_picture":
        return "picture_in_picture"
    if mode == "return_cut":
        return "return_cut" if index == frame_count - 1 else "voice_over"
    return "absent"


def shot_scale(grammar: str, index: int) -> str:
    if grammar == "object_macro":
        return "macro" if index in (0, 1, 3) else "medium"
    if grammar == "mock_screen_capture":
        return "screen"
    if grammar == "diagram_build":
        return "diagram"
    if grammar in ("split_screen", "static_tableau"):
        return "wide"
    return "close" if index == 0 else "medium"


def svg_geometry(grammar: str, accent: str, ink: str, index: int) -> str:
    if grammar == "split_screen":
        return f'<rect x="58" y="230" width="202" height="420" rx="22" fill="{accent}" opacity=".22"/><rect x="280" y="230" width="202" height="420" rx="22" fill="{ink}" opacity=".14"/><path d="M270 230V650" stroke="{accent}" stroke-width="4"/>'
    if grammar == "object_macro":
        return f'<circle cx="270" cy="430" r="142" fill="{accent}" opacity=".18"/><circle cx="270" cy="430" r="82" fill="none" stroke="{accent}" stroke-width="14"/><path d="M210 430h120M270 370v120" stroke="{ink}" stroke-width="10" stroke-linecap="round"/>'
    if grammar == "mock_screen_capture":
        return f'<rect x="64" y="205" width="412" height="480" rx="28" fill="{ink}" opacity=".08" stroke="{accent}" stroke-width="4"/><rect x="92" y="252" width="356" height="74" rx="16" fill="{accent}" opacity=".25"/><rect x="92" y="350" width="220" height="32" rx="10" fill="{ink}" opacity=".18"/><rect x="92" y="404" width="300" height="32" rx="10" fill="{ink}" opacity=".12"/><circle cx="410" cy="618" r="28" fill="{accent}"/>'
    if grammar == "diagram_build":
        offset = index * 8
        return f'<path d="M112 530 C190 {300+offset}, 350 {300-offset}, 430 520" fill="none" stroke="{accent}" stroke-width="8"/><circle cx="112" cy="530" r="34" fill="{accent}"/><circle cx="270" cy="350" r="34" fill="{ink}" opacity=".8"/><circle cx="430" cy="520" r="34" fill="{accent}"/><path d="M150 620h240" stroke="{ink}" stroke-width="10" opacity=".12"/>'
    if grammar == "layered_pip":
        return f'<rect x="58" y="210" width="424" height="470" rx="28" fill="{accent}" opacity=".12"/><circle cx="270" cy="420" r="96" fill="{ink}" opacity=".16"/><rect x="322" y="492" width="132" height="156" rx="22" fill="{ink}" opacity=".88" stroke="{accent}" stroke-width="5"/><circle cx="388" cy="548" r="26" fill="{accent}"/><path d="M354 618q34-48 68 0" fill="{accent}" opacity=".65"/>'
    return f'<text x="270" y="410" text-anchor="middle" font-family="Arial,sans-serif" font-size="110" font-weight="800" fill="{accent}" opacity=".92">{index + 1:02d}</text><rect x="92" y="470" width="356" height="22" rx="11" fill="{ink}" opacity=".18"/><rect x="150" y="520" width="240" height="22" rx="11" fill="{ink}" opacity=".12"/>'


def render_svg(frame: dict, framework: dict, palette: tuple[str, str, str]) -> str:
    bg, accent, ink = palette
    label = frame["on_screen_text"].replace("&", "&amp;").replace("<", "&lt;")
    story = frame["story_function"].replace("&", "&amp;").replace("<", "&lt;")
    geometry = svg_geometry(framework["taxonomy"]["visual_grammar"], accent, ink, frame["sequence_number"] - 1)
    pip = ""
    if frame["a_roll_state"] in ("full", "return_cut"):
        pip = f'<circle cx="270" cy="708" r="38" fill="{accent}"/><path d="M210 790q60-90 120 0" fill="{accent}" opacity=".55"/>'
    elif frame["a_roll_state"] == "picture_in_picture":
        pip = f'<rect x="370" y="650" width="96" height="130" rx="18" fill="{bg}" stroke="{accent}" stroke-width="4"/><circle cx="418" cy="694" r="20" fill="{accent}"/><path d="M390 758q28-44 56 0" fill="{accent}" opacity=".55"/>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 540 960" width="540" height="960">
<rect width="540" height="960" fill="{bg}"/>
<rect x="44" y="96" width="452" height="768" rx="28" fill="none" stroke="{ink}" stroke-opacity=".16" stroke-dasharray="10 10"/>
<text x="44" y="58" font-family="Arial,sans-serif" font-size="20" fill="{ink}" opacity=".74">{framework['framework_id']} · {frame['start_ms']//1000:02d}:00–{frame['end_ms']//1000:02d}:00 · {frame['a_roll_state']}</text>
<text x="270" y="142" text-anchor="middle" font-family="Arial,sans-serif" font-size="38" font-weight="800" fill="{ink}">{label}</text>
<text x="270" y="180" text-anchor="middle" font-family="Arial,sans-serif" font-size="18" fill="{ink}" opacity=".66">{story}</text>
{geometry}{pip}
<rect x="64" y="820" width="412" height="64" rx="18" fill="{ink}" opacity=".10"/>
<text x="84" y="848" font-family="Arial,sans-serif" font-size="15" fill="{ink}" opacity=".72">B-ROLL: {frame['broll_function']}</text>
<text x="84" y="872" font-family="Arial,sans-serif" font-size="15" fill="{ink}" opacity=".72">CUT: {frame['transition']} · TEXT: editable</text>
<text x="270" y="925" text-anchor="middle" font-family="Arial,sans-serif" font-size="14" fill="{ink}" opacity=".48">LOCAL PREVIS · EXTERNAL PROVIDER NOT RUN</text>
</svg>'''


def framework_specs() -> list[dict]:
    specs = []
    seq = 0
    for family_index, family in enumerate(FAMILIES):
        for variant in range(6):
            seq += 1
            framework_id = f"SF-{seq:03d}"
            name = family["names"][variant]
            taxonomy = {
                "hook_mechanism": family["hook"],
                "viewer_job": VIEWER_JOBS[(variant + family_index) % len(VIEWER_JOBS)],
                "broll_function": BROLL_FUNCTIONS[(variant + 2 * family_index) % len(BROLL_FUNCTIONS)],
                "proof_form": PROOF_FORMS[(variant + 3 * family_index) % len(PROOF_FORMS)],
                "visual_grammar": VISUAL_GRAMMARS[(variant + 4 * family_index) % len(VISUAL_GRAMMARS)],
                "pacing_profile": PACING[(variant + family_index) % len(PACING)],
                "transition_family": TRANSITIONS[(variant + 2 * family_index) % len(TRANSITIONS)],
                "a_roll_integration": AROLL[(variant + 3 * family_index) % len(AROLL)],
                "sound_role": SOUND[(variant + 4 * family_index) % len(SOUND)],
                "text_role": TEXT[(variant + 5 * family_index) % len(TEXT)],
                "cta_exit": CTA[(variant + 6 * family_index) % len(CTA)],
                "risk_class": "source_dependent" if family_index in (0, 1, 2, 5, 8) else "low",
            }
            specs.append({
                "framework_id": framework_id,
                "name": name,
                "slug": f"{framework_id.lower()}-{slugify(name)}",
                "family": family["family"],
                "kind": family["kind"],
                "use": family["uses"][variant],
                "beats": family["beats"],
                "labels": family["labels"],
                "source_id": family["source"],
                "evidence_id": family["evidence"],
                "taxonomy": taxonomy,
                "duration_seconds": 4 + variant,
            })
    return specs


def build_export(spec: dict) -> dict:
    payload = {
        "schema": "signal-to-studio.v1",
        "export_id": f"SIGEXP-{spec['framework_id']}",
        "export_version": 1,
        "generated_at": GENERATED_AT,
        "signal_record_id": f"SIG-{spec['framework_id']}",
        "source_ids": [spec["source_id"]],
        "evidence_ids": [spec["evidence_id"]],
        "rights_decision_ids": ["RIGHTS-PUBLIC-COMMENTARY-001"],
        "epistemic_state": "CLASSIFIED",
        "rights_state": "metadata_commentary_only",
        "freshness": {"observed_at": GENERATED_AT, "valid_until": None, "supersedes_export_id": None},
        "taxonomy_version": "studio-shortform@1.0.0",
        "pattern": spec["taxonomy"],
        "studio_constraints": {
            "duration_ms": spec["duration_seconds"] * 1000,
            "aspect_ratio": "9:16",
            "editable_text": True,
            "safe_zone": "platform-ui-aware; 8% horizontal and 10% vertical local planning inset; verify per platform at production",
            "acceptance_checks": [
                "Opening hook signal occurs in the first 1000 ms.",
                "Every visual change has a story function and explicit A-roll state.",
                "No source expression, brand UI, identity, or restricted media is reused.",
            ],
        },
        "provenance": {"raw_object_state": "NOT_AVAILABLE", "source_raw_hashes": [], "record_hash": ""},
        "external_provider_state": "NOT_RUN",
    }
    hash_payload = json.loads(json.dumps(payload))
    hash_payload["provenance"].pop("record_hash")
    payload["provenance"]["record_hash"] = canonical_hash(hash_payload)
    return payload


def timed_beats(spec: dict) -> list[tuple[str, str]]:
    base = list(zip(spec["beats"], spec["labels"]))
    count = spec["duration_seconds"]
    if count == 4:
        return [base[0], base[1], base[3], base[5]]
    if count == 5:
        return [base[0], base[1], base[2], base[4], base[5]]
    if count == 6:
        return base
    extras = [("bridge detail", "BRIDGE"), ("proof hold", "HOLD"), ("counterpoint", "CHECK")]
    return base[:-1] + extras[:count - 6] + [base[-1]]


def build_framework(spec: dict, export: dict) -> dict:
    frames = []
    grammar = spec["taxonomy"]["visual_grammar"]
    beats = timed_beats(spec)
    for index, (beat, label) in enumerate(beats):
        frames.append({
            "frame_id": f"{spec['framework_id']}-F{index + 1:02d}",
            "sequence_number": index + 1,
            "start_ms": index * 1000,
            "end_ms": (index + 1) * 1000,
            "story_function": beat,
            "visual_change": f"{spec['name']}: {beat}; advance one meaningful information state.",
            "composition": f"{grammar} clean-room 9:16 composition with editable overlays and safe-zone guide.",
            "a_roll_state": aroll_state(spec["taxonomy"]["a_roll_integration"], index, len(beats)),
            "broll_function": spec["taxonomy"]["broll_function"],
            "shot_scale": shot_scale(grammar, index),
            "caption_relation": "keyword_emphasis" if index in (0, 3) else ("on_cut" if index in (1, 2, 4) else "continuous"),
            "on_screen_text": label,
            "motion": f"{spec['taxonomy']['pacing_profile']} motion; use {spec['taxonomy']['transition_family']} only at this state boundary.",
            "transition": spec["taxonomy"]["transition_family"],
            "sound_cue": f"{spec['taxonomy']['sound_role']} aligned to the {beat} boundary; licensed or original audio only.",
            "image_path": f"frames/{spec['framework_id']}-F{index + 1:02d}.svg",
            "acceptance_checks": [
                "Primary subject and editable label remain inside the planning safe zone.",
                "Frame differs materially from the previous state in meaning or visual orientation.",
                "No generated pixel text is relied on for final production.",
            ],
        })
    return {
        "framework_id": spec["framework_id"],
        "name": spec["name"],
        "version": "1.0.0",
        "kind": spec["kind"],
        "duration_ms": spec["duration_seconds"] * 1000,
        "aspect_ratio": "9:16",
        "purpose": spec["use"],
        "signal_input": {
            "export_schema": "signal-to-studio.v1",
            "export_id": export["export_id"],
            "record_hash": export["provenance"]["record_hash"],
            "source_rights_state": export["rights_state"],
            "source_ids": export["source_ids"],
            "evidence_ids": export["evidence_ids"],
            "rights_decision_ids": export["rights_decision_ids"],
        },
        "taxonomy": spec["taxonomy"],
        "frames": frames,
        "rights_state": "original_local_previsualization",
        "external_provider_state": "NOT_RUN",
    }


def report_markdown(framework: dict) -> str:
    tax = framework["taxonomy"]
    rows = "\n".join(
        f"| {f['start_ms']/1000:.0f}–{f['end_ms']/1000:.0f}s | {f['story_function']} | {f['a_roll_state']} | {f['broll_function']} | {f['on_screen_text']} | `{f['image_path']}` |"
        for f in framework["frames"]
    )
    taxonomy_rows = "\n".join(f"| `{key}` | `{value}` |" for key, value in tax.items())
    return f"""# {framework['framework_id']} — {framework['name']}

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN / OWNER_REVIEW_PENDING`

## Purpose

{framework['purpose']} This is a {framework['duration_ms']/1000:.0f}-second reusable hook/intro/B-roll insert, not a final video and not a performance claim.

## Signal provenance

- Export: `{framework['signal_input']['export_id']}`
- Sources: {', '.join(f'`{v}`' for v in framework['signal_input']['source_ids'])}
- Evidence: {', '.join(f'`{v}`' for v in framework['signal_input']['evidence_ids'])}
- Rights: `metadata_commentary_only` source abstraction; output frames are original local previsualization.

## Taxonomy

| Axis | Value |
|---|---|
{taxonomy_rows}

## Talking-head integration

Follow each frame's `a_roll_state`. `full` and `return_cut` show the speaker; `voice_over` keeps narration while B-roll carries the image; `picture_in_picture` retains the speaker as an inset; `absent` is a full visual insert. Preserve narration continuity with a J- or L-cut only when it clarifies the spoken beat.

## Second-by-second plan

| Time | Story function | A-roll | B-roll function | Editable text | Frame |
|---|---|---|---|---|---|
{rows}

## Production prompt

Create a vertical 9:16 {framework['duration_ms']/1000:.0f}-second clean-room insert titled “{framework['name']}.” Use one meaningful visual state per second. Hook mechanism: `{tax['hook_mechanism']}`. Viewer job: `{tax['viewer_job']}`. Visual grammar: `{tax['visual_grammar']}`. B-roll function: `{tax['broll_function']}`. Proof form: `{tax['proof_form']}`. Keep all captions, labels, UI-like elements, and proof callouts as editable deterministic overlays. Maintain an 8% horizontal and 10% vertical planning inset, then verify the actual platform UI safe zone at production. Use only original or licensed footage and audio. Do not copy creator wording, source frames, layouts, music, gestures, identity, branded UI, or distinctive sequence. External image/video/audio provider execution remains NOT RUN.

## Analysis notes

- FACT: every visual change is explicitly timecoded and has an A-roll/B-roll function.
- INTERPRETATION: the one-second cadence is a review scaffold; production may hold or subdivide a beat only after the story function remains legible.
- HYPOTHESIS: this framework may help orient attention for its declared viewer job; it does not guarantee retention or reach.
- GAP: no owned performance test, platform-specific UI-safe-zone check, final footage, audio, or owner approval exists.

## Acceptance

- All {len(framework['frames'])} intervals are contiguous and cover 0–{framework['duration_ms']} ms.
- The hook is visible during 0–1000 ms.
- Text stays editable and within the planning safe zone.
- Source lineage and rights IDs remain attached.
- Final video, provider generation, Figma, publishing, and deployment remain `NOT_RUN`.
"""


def prompt_markdown(framework: dict) -> str:
    return "# Prompt and assembly notes\n\n" + report_markdown(framework).split("## Production prompt\n\n", 1)[1].split("\n\n## Analysis notes", 1)[0] + "\n"


def contact_sheet(framework: dict, palette: tuple[str, str, str]) -> str:
    bg, accent, ink = palette
    tiles = []
    for index, frame in enumerate(framework["frames"]):
        col, row = index % 3, index // 3
        x, y = 36 + col * 184, 116 + row * 334
        tiles.append(f'<rect x="{x}" y="{y}" width="160" height="284" rx="18" fill="{ink}" opacity=".08" stroke="{accent}" stroke-opacity=".5"/><image href="{frame["image_path"]}" x="{x}" y="{y}" width="160" height="284" preserveAspectRatio="xMidYMid meet"/>')
    height = 130 + ((len(framework["frames"]) + 2) // 3) * 334
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 588 {height}" width="588" height="{height}">
<rect width="588" height="{height}" fill="{bg}"/>
<text x="36" y="52" font-family="Arial,sans-serif" font-size="28" font-weight="800" fill="{ink}">{framework['framework_id']} · {framework['name']}</text>
<text x="36" y="84" font-family="Arial,sans-serif" font-size="16" fill="{ink}" opacity=".62">{framework['duration_ms']//1000} seconds · one review frame per second · provider NOT RUN</text>
{''.join(tiles)}
</svg>'''


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    index_rows = []
    records = []
    frame_total = 0
    for number, spec in enumerate(framework_specs()):
        export = build_export(spec)
        framework = build_framework(spec, export)
        package_dir = OUT / spec["slug"]
        frames_dir = package_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        palette = PALETTES[number % len(PALETTES)]
        for frame in framework["frames"]:
            (package_dir / frame["image_path"]).write_text(render_svg(frame, framework, palette), encoding="utf-8")
        dump_json(package_dir / "framework.json", framework)
        dump_json(package_dir / "signal-export.json", export)
        (package_dir / "report.md").write_text(report_markdown(framework), encoding="utf-8")
        (package_dir / "prompt.md").write_text(prompt_markdown(framework), encoding="utf-8")
        (package_dir / "contact-sheet.svg").write_text(contact_sheet(framework, palette), encoding="utf-8")
        package_hashes = {}
        for path in sorted(p for p in package_dir.rglob("*") if p.is_file() and p.name != "manifest.json"):
            package_hashes[path.relative_to(package_dir).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        dump_json(package_dir / "manifest.json", {
            "schema": "studio-framework-package-manifest.v1",
            "framework_id": framework["framework_id"],
            "files": package_hashes,
            "external_provider_state": "NOT_RUN",
        })
        index_rows.append(f"| `{framework['framework_id']}` | [{framework['name']}]({spec['slug']}/report.md) | `{framework['kind']}` | `{framework['taxonomy']['hook_mechanism']}` | `{framework['taxonomy']['broll_function']}` |")
        records.append({
            "framework_id": framework["framework_id"],
            "path": spec["slug"],
            "kind": framework["kind"],
            "taxonomy": framework["taxonomy"],
            "record_hash": export["provenance"]["record_hash"],
        })
        frame_total += len(framework["frames"])
    dump_json(OUT / "library-manifest.json", {
        "schema": "studio-framework-library.v1",
        "version": "1.0.0",
        "generated_at": GENERATED_AT,
        "framework_count": len(records),
        "frame_count": frame_total,
        "image_format": "svg",
        "generation_route": "deterministic_local_provider_disabled",
        "external_provider_state": "NOT_RUN",
        "records": records,
    })
    index = """# Studio Short-form Framework Library v1

Status: `LOCAL PREVISUALIZATION / EXTERNAL PROVIDER NOT RUN`

This library contains 60 original 4–9 second hook, intro, and B-roll packages. Every folder includes a report, prompt, Signal export, machine manifest, contact sheet, and one lightweight SVG frame per second. The SVGs are production diagrams, not final generated footage.

| ID | Framework | Kind | Hook | B-roll function |
|---|---|---|---|---|
""" + "\n".join(index_rows) + "\n"
    (OUT / "README.md").write_text(index, encoding="utf-8")
    print(json.dumps({"frameworks": len(records), "frames": frame_total, "output": OUT.relative_to(ROOT).as_posix()}, indent=2))


if __name__ == "__main__":
    main()
