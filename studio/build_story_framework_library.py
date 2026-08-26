#!/usr/bin/env python3
"""Build 50 deterministic, sequential micro-story storyboard packages."""

from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "studio" / "story-framework-library" / "v2"
GENERATED_AT = "2026-08-25T00:00:00+03:00"

PALETTES = [
    ("#081720", "#7DE2D1", "#F7E8C6", "#FF786E"),
    ("#16112A", "#B6A1FF", "#FFE078", "#FF758F"),
    ("#0B211A", "#85D69A", "#F5E1A4", "#FF8169"),
    ("#25131A", "#FF9BA6", "#F7E7C9", "#75C9FF"),
    ("#0D1C2E", "#70B8FF", "#F2CE82", "#FF746D"),
]

FAMILY_PLANS = [
    ("in_medias_res", "hook_intro", ["hook", "orientation", "obstacle", "attempt", "proof", "handback"],
     ["The change is already happening.", "Who is acting and what must be saved?", "What blocks the objective?", "Which concrete action changes the state?", "What proves the action worked?", "What should the viewer do with the rule?"]),
    ("result_rewind", "hook_broll", ["hook", "orientation", "obstacle", "mechanism", "proof", "payoff"],
     ["How did this result appear?", "What was the original state?", "Where did the process break?", "Which decisive step changed it?", "What evidence survives inspection?", "What bounded result can be claimed?"]),
    ("diagnostic_mystery", "hook_intro", ["hook", "orientation", "obstacle", "attempt", "proof", "payoff"],
     ["Which clue explains the symptom?", "Where does the symptom live?", "Which tempting explanation is wrong?", "How does the hero test the clue?", "What artifact resolves the diagnosis?", "What answer closes the question?"]),
    ("failed_attempt_correction", "intro_broll", ["hook", "orientation", "attempt", "obstacle", "mechanism", "payoff"],
     ["Why did the obvious move fail?", "What did the hero expect?", "What first attempt is visible?", "Which failure becomes diagnostic?", "What corrected action follows?", "What changed because of the correction?"]),
    ("object_metaphor", "hook_broll", ["hook", "orientation", "mechanism", "obstacle", "proof", "handback"],
     ["What unusual object is doing?", "What system does the object stand for?", "How does the object expose the mechanism?", "Where does resistance appear?", "What observable state proves the mapping?", "What rule returns to the real workflow?"]),
    ("countdown_ladder", "hook_intro", ["hook", "orientation", "attempt", "mechanism", "proof", "handback"],
     ["What finite path is promised?", "What is rung one?", "What is rung two?", "What is the decisive rung?", "What final check prevents false completion?", "What compact checklist remains?"]),
    ("before_after_transformation", "intro_broll", ["hook", "orientation", "obstacle", "mechanism", "proof", "payoff"],
     ["Can the contrast be read instantly?", "What is the before-state?", "What friction keeps it stuck?", "What visible transformation occurs?", "What constraint keeps the after-state honest?", "What useful after-state remains?"]),
    ("proof_reveal", "hook_broll", ["hook", "orientation", "obstacle", "mechanism", "proof", "limitation"],
     ["What claim is waiting for proof?", "Where should proof exist?", "What missing field would invalidate it?", "How is the proof uncovered?", "What exact artifact supports the claim?", "Where does the evidence stop?"]),
    ("contradiction_resolution", "hook_intro", ["hook", "orientation", "obstacle", "mechanism", "proof", "payoff"],
     ["Why is the expected rule failing?", "What expectation does the hero hold?", "What contradiction becomes visible?", "What reframe makes both facts fit?", "What example tests the reframe?", "What corrected rule should be remembered?"]),
    ("process_handback", "broll", ["hook", "orientation", "attempt", "mechanism", "proof", "handback"],
     ["What process will finish on screen?", "What input enters?", "What first transformation occurs?", "How does the mechanism complete?", "What output can be checked?", "How does the sequence return to the speaker?"]),
]

FAMILY_LABELS = {
    "in_medias_res": ["ALREADY MOVING", "WHAT MUST CHANGE", "THE COLLISION", "ACT NOW", "VISIBLE CHECK", "BACK WITH THE RULE"],
    "result_rewind": ["HERE'S THE RESULT", "REWIND", "THE MISSED STEP", "THE TURNING MOVE", "WHY IT HOLDS", "BOUNDED RESULT"],
    "diagnostic_mystery": ["SPOT THE CLUE", "LOCATE THE SYMPTOM", "RULE OUT THE OBVIOUS", "TEST ONE CAUSE", "THE TRACE", "DIAGNOSIS"],
    "failed_attempt_correction": ["THE FIRST MOVE FAILS", "WHAT WAS EXPECTED", "TRY ONE", "FAILURE REVEALS", "CORRECT THE PATH", "CHANGED STATE"],
    "object_metaphor": ["WATCH THE OBJECT", "MAP IT TO THE SYSTEM", "SHOW THE MECHANISM", "RESISTANCE", "TEST THE MAPPING", "RETURN TO REALITY"],
    "countdown_ladder": ["A FINITE PATH", "RUNG ONE", "RUNG TWO", "DECISIVE RUNG", "FINAL CHECK", "KEEP THE LADDER"],
    "before_after_transformation": ["READ THE CONTRAST", "BEFORE", "WHY IT STICKS", "THE CONVERSION", "CHECK THE AFTER", "AFTER—WITH A LIMIT"],
    "proof_reveal": ["CLAIM WITHOUT PROOF", "WHERE PROOF SHOULD BE", "THE MISSING FIELD", "PEEL IT BACK", "INSPECT THE ARTIFACT", "EVIDENCE STOPS HERE"],
    "contradiction_resolution": ["BOTH LOOK TRUE", "THE EXPECTATION", "THE CONTRADICTION", "ADD THE DISTINCTION", "TEST THE REFRAME", "THE CORRECTED RULE"],
    "process_handback": ["WATCH IT COMPLETE", "INPUT ENTERS", "FIRST CHANGE", "MECHANISM MOVES", "CHECK THE OUTPUT", "BACK TO THE SPEAKER"],
}

SCENARIOS = [
    ("Deadline Brief", "an operations lead", "a quiet project room", "turn a scattered brief into one decision", "three conflicting notes", "the meeting starts before the choice is clear", "clock", "decision receipt", "decision board", "sorts the notes by decision owner", "one accountable next step", "The receipt proves routing, not business success."),
    ("Approval at the Threshold", "a content operator", "an edit bay", "publish only after review", "the publish control is active before approval", "an unsupported claim could escape", "lock", "signed review card", "safe publish gate", "moves the draft behind a review gate", "the risky control stays locked", "The scene does not authorize real publication."),
    ("The Stale Dashboard", "a revenue analyst", "a monitor wall", "explain a sudden metric change", "the visible chart is two weeks stale", "the team could act on the wrong period", "calendar", "freshness timestamp", "current chart", "checks the timestamp before interpreting", "the stale chart is clearly quarantined", "Freshness enables analysis; it does not prove causality."),
    ("Queue Under Pressure", "a support coordinator", "an intake desk", "route the urgent request correctly", "all tickets look identical", "a time-sensitive request may be buried", "queue ticket", "priority rule", "ordered queue", "marks urgency and owner before routing", "the urgent item reaches the correct lane", "Priority is a declared rule, not inferred intent."),
    ("Source Before Claim", "a research editor", "a source library", "turn a claim into cited explanation", "the draft has no evidence parent", "the audience could mistake opinion for fact", "magnifier", "source map", "cited script", "traces the sentence to a dated source", "the claim becomes bounded and inspectable", "One source may still be incomplete or contested."),

    ("The Rebuilt Handoff", "a project manager", "a handoff table", "restore missing context", "the last owner left only a vague note", "the next person could repeat the work", "envelope", "handoff checklist", "complete handoff", "rewinds from the clean handoff to the missing fields", "the successor can act without guessing", "A checklist cannot replace domain judgment."),
    ("From Noise to Signal", "a market researcher", "a wall of clippings", "identify one reusable pattern", "popularity signals are mixed with evidence", "a trend claim could be overstated", "funnel", "evidence labels", "pattern card", "separates observation from inference", "one pattern survives with caveats", "A reference pattern is not performance proof."),
    ("Rollback Ready", "a local operator", "a deployment bench", "prove a change is reversible", "the forward path has no recovery step", "a small error could become persistent", "reverse arrow", "rollback test", "safe change set", "rewinds from recovery to the missing backup", "the change remains bounded", "A storyboard does not execute deployment."),
    ("The Clearer Screen", "a product educator", "a demo workstation", "explain one interface state", "every control is highlighted at once", "the viewer cannot locate the next action", "cursor", "focus highlight", "single-action screen", "rewinds from a clean state to excess overlays", "one control carries the explanation", "The interface is a generic mock, not branded UI."),
    ("The One-Line Outcome", "a technical writer", "a drafting desk", "compress a complex workflow honestly", "the opening promises too many outcomes", "the viewer cannot predict the lesson", "pencil", "scope bracket", "bounded promise", "removes claims until one mechanism remains", "the hook and payoff match", "Compression must not delete limitations."),

    ("Why the Number Dropped", "a business analyst", "a review room", "diagnose a visible drop", "three plausible causes compete", "the wrong intervention wastes the next cycle", "chart", "segment comparison", "diagnosis note", "compares the affected segment against the rest", "one cause remains plausible", "The comparison narrows causes; it does not prove one."),
    ("The Silent Automation", "a workflow owner", "an automation console", "find why a task stopped", "no error appears on the main screen", "work can silently accumulate", "bell", "event log", "restored trigger", "follows the last successful event", "the broken trigger becomes visible", "A log can reveal sequence, not intent."),
    ("Duplicate in the Queue", "a data steward", "a record desk", "find why counts disagree", "one entity appears under two labels", "reports may double-count the same object", "two tags", "canonical ID", "merged record", "matches stable identifiers before merging", "the duplicate is resolved without deleting evidence", "Entity resolution may require human review."),
    ("Where the Caption Went", "a video editor", "a vertical timeline", "restore a missing explanation", "the cut lands before the key caption", "the action becomes ambiguous", "caption strip", "timing marker", "aligned caption", "checks the cut against the word boundary", "the caption arrives with the action", "Timing varies with narration and language."),
    ("The Broken Source Link", "a fact checker", "a browser-free evidence desk", "verify a factual sentence", "the source pointer ends at a search snippet", "the claim cannot be audited", "broken chain", "canonical URL", "verified citation", "traces the snippet to the original page", "the sentence gains a direct parent", "Access today does not guarantee future availability."),

    ("Clicking Faster Failed", "a tool operator", "a software demo desk", "finish a controlled task", "rapid clicks skip the state check", "the wrong field may be changed", "mouse", "state checklist", "verified action", "pauses and reads the state before continuing", "the next click becomes justified", "The demo uses synthetic data only."),
    ("More Cuts, Less Meaning", "a short-form editor", "an editing timeline", "keep a technical explanation clear", "cuts occur without information change", "the viewer loses causal continuity", "scissors", "beat map", "motivated cut", "removes cuts that do not change state", "each remaining cut answers a question", "Pacing still requires audience testing."),
    ("The Missing Owner", "a program coordinator", "a planning wall", "move one decision forward", "every task has a date but no owner", "the deadline can pass without action", "name tag", "ownership card", "assigned decision", "adds one accountable role and review point", "the next action has a visible owner", "Ownership labels do not guarantee completion."),
    ("Upload Without Redaction", "a research assistant", "a safe intake desk", "prepare a public analysis sample", "a raw file still contains private fields", "private data could leave its boundary", "shield", "redaction receipt", "sanitized sample", "stops the upload and masks restricted fields", "only the bounded sample proceeds", "Redaction must be independently checked."),
    ("The Unreadable Proof", "a content designer", "a phone-sized canvas", "show evidence legibly", "the full dashboard is shrunk into one frame", "the proof becomes decorative", "phone", "cropped evidence", "readable callout", "crops to one datum and keeps context in narration", "the proof can be inspected on mobile", "Cropping must not remove relevant context."),

    ("Domino Dependency", "a systems explainer", "a tabletop studio", "show how one missing handoff propagates", "the dependency is invisible in a list", "one missing step can disrupt the full chain", "domino", "stopped chain", "dependency map", "removes one domino, then restores a labeled gate", "the chain stops safely at the gate", "The metaphor simplifies real branching systems."),
    ("Leaking Attention", "a content strategist", "a workshop table", "keep one promise alive to payoff", "every second opens a new topic", "the viewer cannot resolve the first question", "bucket", "sealed channel", "single promise", "plugs side topics and routes detail to one channel", "the original question reaches an answer", "Curiosity should not become deceptive withholding."),
    ("Lock and Key Permission", "a safety reviewer", "a controlled doorway", "explain why access and approval differ", "the key exists without permission to turn it", "a capability could be mistaken for authority", "key", "approval token", "opened gate", "pairs the key with a separate approval marker", "the door opens only when both states align", "The metaphor does not model every permission layer."),
    ("Bridge of Evidence", "a research narrator", "a paper bridge model", "connect a claim to a conclusion", "one supporting plank is missing", "the conclusion cannot bear weight", "bridge", "source plank", "bounded conclusion", "adds dated sources and labels the remaining gap", "the bridge carries only the supported claim", "More sources do not automatically remove bias."),
    ("Compass Before Speed", "a project lead", "a route-planning table", "choose the next useful action", "the team accelerates before agreeing direction", "effort could compound in the wrong lane", "compass", "decision criteria", "bounded route", "sets direction and stop conditions before moving", "speed follows a visible route", "The compass stands for criteria, not certainty."),

    ("Three Checks Before Publish", "a content reviewer", "a review station", "clear a draft safely", "the draft feels finished before claims are checked", "an error could become public", "checklist", "review receipt", "approved draft", "checks source, rights, and limitation in order", "all three gates remain visible", "This package does not publish anything."),
    ("Three Frames to Explain", "a motion designer", "a storyboard wall", "explain one mechanism quickly", "the sequence starts with decoration", "time expires before meaning arrives", "frame stack", "causal arrows", "clear sequence", "orders context, action, and consequence", "the mechanism reads without the report", "Complex mechanisms may require more beats."),
    ("Five Proof States", "an evidence analyst", "a classification desk", "separate fact from uncertainty", "all statements share one visual style", "viewers may treat hypotheses as facts", "label set", "evidence key", "classified claims", "assigns FACT, INTERPRETATION, HYPOTHESIS, and GAP", "the claim state is visible", "Labels do not improve weak evidence by themselves."),
    ("Four Cuts With Purpose", "a reel editor", "a cut timeline", "create rhythm without confusion", "every beat uses the same shot scale", "attention resets become predictable", "clapper", "shot ladder", "motivated sequence", "moves wide, medium, macro, then return", "each scale reveals new information", "Shot variety is not a retention guarantee."),
    ("Three Steps to a Hook", "a scriptwriter", "a writing desk", "open with an honest curiosity loop", "the first line is broad and abstract", "the audience cannot see a reason to continue", "three cards", "hook test", "bounded hook", "names the concrete problem, stake, and promised mechanism", "the opening question matches the answer", "Avoid certainty beyond available proof."),

    ("Inbox to Ordered Queue", "an operations coordinator", "a digital intake wall", "turn chaotic requests into controlled work", "messages arrive without priority or owner", "urgent work can disappear", "inbox", "routing rules", "ordered queue", "classifies urgency, owner, and next state", "the queue can be reviewed at a glance", "Routing quality depends on declared criteria."),
    ("Flat List to Source Map", "a researcher", "a reference wall", "see which claims share evidence", "a flat list hides dependencies", "one weak source can support too much", "list", "graph links", "source map", "connects each claim to dated evidence", "overloaded sources become obvious", "A map visualizes lineage; it does not verify truth."),
    ("Manual Copy to Checked Export", "a data operator", "a transfer bench", "move records without losing lineage", "manual copy strips IDs and null states", "downstream analysis can misread absence", "clipboard", "hash receipt", "versioned export", "exports stable IDs, nulls, and checksums", "the receiver can verify the file", "A valid export may still contain weak source data."),
    ("Guess to Bounded Test", "a growth planner", "an experiment board", "turn a creative opinion into a test", "the team argues from taste", "production time can be wasted", "dice", "test card", "two-version test", "defines one variable and one decision rule", "the hypothesis becomes falsifiable", "A small test may not generalize."),
    ("Cluttered Frame to One Action", "a visual educator", "a vertical canvas", "make the next action obvious", "captions, UI, charts, and face compete", "the viewer cannot locate the focal point", "layers", "focus ring", "single focal frame", "stages layers in causal order", "one action dominates each beat", "Accessibility and platform safe zones still need QA."),

    ("Receipt Behind the Claim", "an operations narrator", "a document table", "show that a task actually ran", "the spoken claim has no visible artifact", "confidence could replace verification", "receipt", "timestamped output", "bounded verdict", "reveals the dated receipt and matching ID", "the execution state is inspectable", "A receipt proves execution, not outcome quality."),
    ("The Timestamp Test", "a dashboard reviewer", "a monitor close-up", "decide whether a metric is current", "the chart title omits observed time", "old data may guide a new decision", "clock", "observed-at field", "freshness verdict", "reveals the timestamp before the number", "the viewer sees whether the metric is usable", "Fresh data can still be incomplete."),
    ("The Diff Tells the Story", "a software reviewer", "a code-review board", "explain what changed", "the full file hides the relevant edit", "review time is wasted", "diff marks", "changed lines", "review decision", "peels away unchanged context", "the meaningful change stays visible", "A diff does not prove runtime behavior."),
    ("Source Stack Reveal", "a policy writer", "a source shelf", "support a rule with independent parents", "one secondary summary dominates the draft", "the rule may inherit its errors", "book stack", "primary sources", "claim map", "reveals primary parents behind the summary", "the claim shows its evidence depth", "Agreement among sources is not causal proof."),
    ("Boundary Card First", "a technical presenter", "a clean studio desk", "explain a tool honestly", "the benefit appears before the constraint", "viewers may overgeneralize", "boundary card", "worked example", "bounded explanation", "reveals the limitation before the example", "the promise stays inside the evidence", "The example is illustrative, not a benchmark."),

    ("More Data, Less Clarity", "a research lead", "a crowded evidence wall", "make one decision", "additional sources arrive without synthesis", "volume can obscure the decision", "paper stack", "decision lens", "evidence subset", "groups sources by the question they answer", "less material supports a clearer choice", "Omitted sources remain in the ledger."),
    ("Faster Tool, Slower Workflow", "a team operator", "a tool-switching desk", "finish a repeatable task", "every step uses a different fast tool", "handoffs consume the saved time", "stopwatch", "handoff map", "simplified route", "counts transitions instead of tool speed", "the workflow loses unnecessary handoffs", "This is a process hypothesis until measured."),
    ("Automation Needs a Gate", "a system owner", "an automation lane", "let routine work move safely", "the agent cannot recognize every edge case", "an exception could become an external action", "robot arm", "human gate", "controlled flow", "routes normal cases forward and exceptions aside", "speed and review coexist", "The gate requires a real escalation owner."),
    ("Movement Without Progress", "a program manager", "a task board", "advance one outcome", "many cards move but no decision closes", "activity can mask stalled value", "moving cards", "outcome marker", "closed decision", "tracks the outcome instead of card motion", "progress becomes a changed state", "One outcome may still depend on external actors."),
    ("Beautiful Frame, Weak Proof", "a creative director", "a polished storyboard", "make an explanation trustworthy", "visual polish hides a missing source", "the audience may remember style as certainty", "sparkle", "evidence label", "honest frame", "reduces decoration and exposes the evidence state", "clarity replaces borrowed authority", "A plain frame is not automatically accurate."),

    ("Question to Answer", "a speaking presenter", "a small studio", "answer one audience question", "the explanation branches into side topics", "the hook may never close", "question card", "answer card", "speaker return", "moves question, mechanism, proof, then answer", "the viewer returns to the speaker with closure", "Further detail belongs in a later segment."),
    ("Source to Script", "a research writer", "a writing workstation", "convert evidence into original narration", "source wording is too close to the draft", "the script risks imitation", "source page", "claim notes", "original script", "extracts facts, closes the source, then rewrites", "the narration keeps meaning without expression", "Distinctive examples and metaphors remain excluded."),
    ("Script to Frame", "a storyboard artist", "a frame wall", "turn narration into visible actions", "the draft contains only abstract nouns", "B-roll becomes decorative", "script strip", "verb markers", "action frames", "replaces each abstraction with a hero verb and prop", "every frame performs part of the sentence", "Some ideas still require diagrams or UI."),
    ("Frame to Cut", "a video editor", "a timeline desk", "assemble a readable six-second insert", "transitions are chosen for novelty", "the sequence feels disconnected", "film strip", "motion match", "coherent cut", "matches movement or information across each cut", "the insert reads as one event", "Final timing must follow recorded speech."),
    ("Cut to Review", "an independent reviewer", "a review monitor", "decide whether a micro-story is ready", "the creator knows the intended meaning", "self-knowledge can hide ambiguity", "review flag", "acceptance checklist", "review verdict", "checks the sequence without reading the report first", "the verdict reflects visible causality", "Owner approval remains separate from review."),
]


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def dump(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(payload: object) -> str:
    material = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(material).hexdigest()


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def wrap(value: str, width: int) -> list[str]:
    words, lines, current = value.split(), [], []
    for word in words:
        if len(" ".join(current + [word])) > width and current:
            lines.append(" ".join(current)); current = [word]
        else:
            current.append(word)
    if current: lines.append(" ".join(current))
    return lines[:3]


def compact_state(value: object) -> str:
    if isinstance(value, dict):
        return f"target = {value.get('ENT-target', 'unknown')}"[:34]
    value = str(value)
    parts = [part.strip() for part in value.split(";")]
    chosen = next((part for part in parts if "ENT-target" in part), parts[0])
    chosen = re.sub(r"ENT-target:[^=]+=?", "target = ", chosen).replace("ENT-target", "target")
    return chosen[:34]


def infinitive(action: str) -> str:
    parts = action.split(maxsplit=1)
    verb = parts[0]
    if verb == "pauses":
        verb = "pause"
    elif verb.endswith("ies"):
        verb = verb[:-3] + "y"
    elif verb.endswith("ches") or verb.endswith("shes") or verb.endswith("xes") or verb.endswith("zes") or verb.endswith("ses"):
        verb = verb[:-2]
    elif verb.endswith("s") and not verb.endswith("ss"):
        verb = verb[:-1]
    return verb + (" " + parts[1] if len(parts) > 1 else "")


def prop_icon(kind: str, x: int, y: int, accent: str, ink: str, danger: str, label: str) -> str:
    k = kind.lower()
    if any(w in k for w in ("clock", "calendar", "timestamp", "stopwatch")):
        shape = f'<circle cx="{x}" cy="{y}" r="55" fill="none" stroke="{accent}" stroke-width="9"/><path d="M{x} {y}v-30m0 30l28 18" stroke="{ink}" stroke-width="8" stroke-linecap="round"/>'
    elif any(w in k for w in ("lock", "key", "gate", "shield")):
        shape = f'<rect x="{x-45}" y="{y-5}" width="90" height="75" rx="15" fill="{accent}" opacity=".28" stroke="{accent}" stroke-width="7"/><path d="M{x-28} {y-5}v-22a28 28 0 0 1 56 0v22" fill="none" stroke="{ink}" stroke-width="8"/>'
    elif any(w in k for w in ("chart", "dashboard", "screen", "monitor", "phone")):
        shape = f'<rect x="{x-70}" y="{y-52}" width="140" height="104" rx="14" fill="{ink}" opacity=".10" stroke="{accent}" stroke-width="6"/><path d="M{x-48} {y+20}l30-28 26 13 38-42" fill="none" stroke="{accent}" stroke-width="8"/>'
    elif any(w in k for w in ("domino", "cards", "stack", "list", "layers", "queue", "ticket")):
        shape = ''.join(f'<rect x="{x-68+i*25}" y="{y-48-i*7}" width="58" height="92" rx="10" fill="{accent}" opacity="{.18+i*.1}" stroke="{accent}" stroke-width="4"/>' for i in range(4))
    elif any(w in k for w in ("magnifier", "lens", "focus", "source")):
        shape = f'<circle cx="{x-12}" cy="{y-10}" r="46" fill="none" stroke="{accent}" stroke-width="9"/><path d="M{x+20} {y+22}l48 48" stroke="{accent}" stroke-width="12" stroke-linecap="round"/>'
    elif any(w in k for w in ("bridge", "chain", "arrow", "map", "route", "funnel")):
        shape = f'<path d="M{x-78} {y+38}Q{x} {y-68} {x+78} {y+38}" fill="none" stroke="{accent}" stroke-width="11"/><circle cx="{x-78}" cy="{y+38}" r="14" fill="{ink}"/><circle cx="{x+78}" cy="{y+38}" r="14" fill="{accent}"/>'
    elif any(w in k for w in ("bucket", "inbox", "envelope", "folder")):
        shape = f'<path d="M{x-65} {y-35}h130l-14 95h-102z" fill="{accent}" opacity=".25" stroke="{accent}" stroke-width="7"/><path d="M{x-65} {y-35}l65 48 65-48" fill="none" stroke="{ink}" stroke-width="6"/>'
    else:
        shape = f'<rect x="{x-66}" y="{y-50}" width="132" height="100" rx="18" fill="{accent}" opacity=".24" stroke="{accent}" stroke-width="6"/><path d="M{x-42} {y-15}h84m-84 28h60" stroke="{ink}" stroke-width="7" opacity=".65"/>'
    return shape + f'<text x="{x}" y="{y+100}" text-anchor="middle" font-family="Arial,sans-serif" font-size="19" font-weight="700" fill="{ink}">{esc(label[:24])}</text>'


def person(x: int, y: int, accent: str, ink: str, pose: int) -> str:
    arm = [f'M{x} {y+62}l-54 38m54-38l55 26', f'M{x} {y+62}l-54-15m54 15l68-35', f'M{x} {y+62}l-64 22m64-22l58 56'][pose % 3]
    return f'<circle cx="{x}" cy="{y}" r="34" fill="{accent}"/><path d="M{x} {y+38}v116m0-62l-48 118m48-118l56 118" stroke="{ink}" stroke-width="13" stroke-linecap="round"/>' + f'<path d="{arm}" stroke="{ink}" stroke-width="13" stroke-linecap="round"/>'


def operation_type(action: str) -> str:
    a = action.lower()
    if any(k in a for k in ("sort", "classif", "group", "order")):
        return "sort"
    if any(k in a for k in ("route", "connect", "pair", "match", "map")):
        return "route"
    if any(k in a for k in ("check", "inspect", "reveal", "trace", "follow", "compare")):
        return "inspect"
    if any(k in a for k in ("remove", "collapse", "fade", "mask", "crop", "reduce", "plug")):
        return "remove"
    if any(k in a for k in ("add", "assign", "attach", "include", "restore", "mark")):
        return "attach"
    if any(k in a for k in ("stop", "lock", "gate", "hold", "pause")):
        return "gate"
    return "transfer"


def operation_marks(action: str, x: int, y: int, accent: str, ink: str, danger: str) -> str:
    op = operation_type(action)
    if op == "sort":
        cards = ''.join(f'<rect x="{x-72+j*34}" y="{y-55+(j%2)*34}" width="27" height="38" rx="5" fill="{accent}" opacity="{.35+j*.15}"/>' for j in range(4))
        return cards + f'<path d="M{x-60} {y+25}q60 55 120 0" fill="none" stroke="{accent}" stroke-width="8" marker-end="url(#a)"/><path d="M{x-55} {y+65}h45m20 0h45" stroke="{ink}" stroke-width="10" opacity=".5"/>'
    if op == "route":
        return f'<circle cx="{x-62}" cy="{y}" r="19" fill="{ink}"/><circle cx="{x+62}" cy="{y}" r="19" fill="{accent}"/><path d="M{x-40} {y}C{x} {y-70} {x+18} {y+70} {x+48} {y}" fill="none" stroke="{accent}" stroke-width="9" marker-end="url(#a)"/>'
    if op == "inspect":
        return f'<circle cx="{x-18}" cy="{y-10}" r="52" fill="none" stroke="{accent}" stroke-width="9"/><path d="M{x+18} {y+26}l54 54" stroke="{accent}" stroke-width="12" stroke-linecap="round"/><path d="M{x-42} {y-10}l18 20 39-47" fill="none" stroke="{ink}" stroke-width="8"/>'
    if op == "remove":
        return f'<rect x="{x-74}" y="{y-55}" width="58" height="95" rx="9" fill="{danger}" opacity=".22"/><rect x="{x-8}" y="{y-55}" width="58" height="95" rx="9" fill="{ink}" opacity=".12"/><path d="M{x-88} {y-70}l155 135" stroke="{accent}" stroke-width="12"/><rect x="{x+48}" y="{y-28}" width="70" height="55" rx="10" fill="{accent}" opacity=".55"/>'
    if op == "attach":
        return f'<rect x="{x-74}" y="{y-52}" width="105" height="104" rx="14" fill="{ink}" opacity=".10" stroke="{accent}" stroke-width="6"/><path d="M{x+15} {y}h80m-40-40v80" stroke="{accent}" stroke-width="12" stroke-linecap="round"/><path d="M{x-52} {y}l20 22 42-49" fill="none" stroke="{ink}" stroke-width="8"/>'
    if op == "gate":
        return f'<rect x="{x-12}" y="{y-72}" width="24" height="144" rx="12" fill="{danger}"/><path d="M{x+22} {y}h75" stroke="{accent}" stroke-width="10" marker-end="url(#a)"/><circle cx="{x-42}" cy="{y}" r="24" fill="{accent}"/>'
    return f'<path d="M{x-82} {y}h164" stroke="{accent}" stroke-width="11" marker-end="url(#a)"/><circle cx="{x-90}" cy="{y}" r="18" fill="{ink}"/><circle cx="{x+92}" cy="{y}" r="24" fill="{accent}"/>'


def status_mark(x: int, y: int, stage: str, accent: str, danger: str, ink: str) -> str:
    if stage in ("resolved", "proved", "bounded"):
        return f'<circle cx="{x}" cy="{y}" r="25" fill="{accent}"/><path d="M{x-12} {y}l9 11 18-24" fill="none" stroke="{ink}" stroke-width="7"/>'
    if stage in ("blocked", "failed"):
        return f'<circle cx="{x}" cy="{y}" r="25" fill="{danger}"/><path d="M{x-10} {y-10}l20 20m0-20l-20 20" stroke="{ink}" stroke-width="7"/>'
    return f'<circle cx="{x}" cy="{y}" r="25" fill="none" stroke="{accent}" stroke-width="6"/><text x="{x}" y="{y+8}" text-anchor="middle" font-family="Arial" font-size="24" font-weight="800" fill="{accent}">?</text>'


def family_scene_geometry(story: dict, frame: dict, accent: str, ink: str, danger: str) -> str:
    family, i, role = story["family"], frame["sequence_number"] - 1, frame["beat_role"]
    trigger, target, proof = (story["continuity_bible"][k] for k in ("trigger_prop", "target_prop", "proof_prop"))
    stage = "blocked" if role == "obstacle" else ("failed" if family == "failed_attempt_correction" and i == 3 else ("resolved" if i == 5 else ("proved" if role in ("proof", "limitation") else "open")))
    target_icon = prop_icon(target, 405, 420, accent, ink, danger, target)
    target_status = status_mark(460, 325, stage, accent, danger, ink) if i >= 1 or family == "result_rewind" else ""
    proof_icon = prop_icon(proof, 402, 500, accent, ink, danger, proof) if role in ("proof", "limitation", "payoff", "handback") else ""
    action = operation_marks(story["narrative"]["action_chain"][1], 270, 455, accent, ink, danger) if role in ("attempt", "mechanism", "proof", "payoff", "handback", "limitation") else ""
    hero = person(105, 415, accent, ink, i)
    if family == "in_medias_res":
        barrier = f'<rect x="292" y="285" width="28" height="300" rx="14" fill="{danger}" opacity=".82"/>' if role in ("obstacle", "attempt") else ''
        return hero + prop_icon(trigger, 225, 380, accent, ink, danger, trigger) + (target_icon if i >= 1 else '') + barrier + action + proof_icon + target_status
    if family == "result_rewind":
        rewind = f'<path d="M445 285C300 220 170 245 145 335" fill="none" stroke="{accent}" stroke-width="9" stroke-dasharray="13 9" marker-end="url(#a)"/><text x="290" y="250" text-anchor="middle" fill="{accent}" font-family="Arial" font-size="20" font-weight="700">REWIND</text>'
        return target_icon + target_status + rewind + hero + (prop_icon(trigger, 220, 500, accent, ink, danger, trigger) if i >= 1 else '') + action + proof_icon
    if family == "diagnostic_mystery":
        clues = ''.join(f'<circle cx="{230+j*55}" cy="{350+(j%2)*85}" r="24" fill="{danger if j==1 and i<4 else accent}" opacity="{.35+j*.18}"/>' for j in range(3))
        lens = f'<circle cx="{285}" cy="{410}" r="78" fill="none" stroke="{accent}" stroke-width="10"/><path d="M335 468l58 58" stroke="{accent}" stroke-width="14"/>' if i >= 3 else ''
        return hero + clues + lens + target_icon + target_status + proof_icon
    if family == "failed_attempt_correction":
        barrier = f'<rect x="300" y="300" width="28" height="280" rx="14" fill="{danger}"/>'
        first_try = f'<path d="M175 455h105" stroke="{danger}" stroke-width="11"/><path d="M275 455l-35-30m35 30l-35 30" stroke="{danger}" stroke-width="9"/>' if i in (2,3) else ''
        correction = f'<path d="M175 455C235 285 340 285 385 400" fill="none" stroke="{accent}" stroke-width="11" marker-end="url(#a)"/>' if i >= 4 else ''
        return hero + target_icon + target_status + barrier + first_try + correction + proof_icon
    if family == "object_metaphor":
        big_object = prop_icon(trigger, 270, 380, accent, ink, danger, trigger)
        system = f'<rect x="350" y="520" width="130" height="90" rx="16" fill="{ink}" opacity=".08" stroke="{accent}" stroke-width="5"/><circle cx="380" cy="565" r="13" fill="{accent}"/><circle cx="445" cy="565" r="13" fill="{danger}"/><path d="M393 565h39" stroke="{ink}" stroke-width="7"/>' if i >= 1 else ''
        mapping = f'<path d="M305 450C330 485 350 500 380 525" fill="none" stroke="{accent}" stroke-width="8" marker-end="url(#a)"/>' if i >= 2 else ''
        return person(90, 475, accent, ink, i) + big_object + system + mapping + (target_icon if i >= 1 else '') + target_status + proof_icon
    if family == "countdown_ladder":
        steps = ''.join(f'<rect x="{155+j*82}" y="{555-j*78}" width="78" height="{45+j*6}" rx="8" fill="{accent}" opacity="{.2+j*.18}"/><text x="{194+j*82}" y="{585-j*78}" text-anchor="middle" fill="{ink}" font-family="Arial" font-size="22" font-weight="800">{j+1}</text>' for j in range(4))
        hx, hy = 118 + min(i,4)*66, 470 - min(i,4)*58
        return steps + person(hx, hy, accent, ink, i) + target_icon + target_status + proof_icon
    if family == "before_after_transformation":
        split = f'<path d="M270 280v320" stroke="{ink}" stroke-width="6" opacity=".3"/><text x="150" y="300" text-anchor="middle" fill="{danger}" font-family="Arial" font-size="20" font-weight="700">BEFORE</text><text x="390" y="300" text-anchor="middle" fill="{accent}" font-family="Arial" font-size="20" font-weight="700">AFTER</text>'
        left = prop_icon(trigger, 150, 430, danger, ink, danger, trigger)
        right = prop_icon(target, 390, 430, accent, ink, danger, target) if i >= 1 else ''
        transform = f'<path d="M215 470h105" stroke="{accent}" stroke-width="10" marker-end="url(#a)"/>' + operation_marks(story["narrative"]["action_chain"][1],270,545,accent,ink,danger) if i >= 3 else ''
        return split + left + right + transform + target_status + proof_icon
    if family == "proof_reveal":
        claim = prop_icon(target, 270, 385, accent, ink, danger, target)
        cover_w = max(0, 180 - i*36)
        cover = f'<rect x="{270-cover_w/2}" y="300" width="{cover_w}" height="190" rx="18" fill="{danger}" opacity=".88"/>' if cover_w else ''
        evidence = prop_icon(proof, 270, 555, accent, ink, danger, proof) if i >= 3 else ''
        return person(85, 470, accent, ink, i) + claim + cover + evidence + target_status + (f'<circle cx="270" cy="555" r="100" fill="none" stroke="{accent}" stroke-width="6" stroke-dasharray="12 9"/>' if i >= 4 else '')
    if family == "contradiction_resolution":
        left = prop_icon(trigger, 150, 405, danger, ink, danger, trigger)
        right = target_icon
        scale = f'<path d="M270 330v200m-110-135h220m-190 0l-35 90h70zm160 0l-35 90h70z" fill="none" stroke="{ink}" stroke-width="8" opacity=".55"/>'
        bridge = f'<path d="M205 525Q270 455 335 525" fill="none" stroke="{accent}" stroke-width="11" marker-end="url(#a)"/>' if i >= 3 else ''
        return left + right + scale + bridge + target_status + proof_icon
    positions = [115, 165, 225, 305, 385, 430]
    belt = f'<path d="M90 480h365" stroke="{ink}" stroke-width="16" opacity=".20"/><path d="M90 520h365" stroke="{ink}" stroke-width="6" opacity=".25"/>'
    moving = prop_icon(target, positions[i], 405, accent, ink, danger, target)
    nodes = ''.join(f'<circle cx="{x}" cy="500" r="12" fill="{accent if x<=positions[i] else ink}" opacity=".55"/>' for x in (130,220,310,400))
    return belt + nodes + moving + person(75, 505, accent, ink, i) + (proof_icon if i >= 4 else '') + target_status


def scene_svg(story: dict, frame: dict, colors: tuple[str, str, str, str]) -> str:
    bg, accent, ink, danger = colors
    title_lines = wrap(frame["on_screen_text"], 24)
    text_svg = ''.join(f'<text x="270" y="{132+n*42}" text-anchor="middle" font-family="Arial,sans-serif" font-size="34" font-weight="800" fill="{ink}">{esc(line)}</text>' for n, line in enumerate(title_lines))
    geometry = family_scene_geometry(story, frame, accent, ink, danger)
    limitation_lines = wrap(story["narrative"]["limitation"], 48) if frame["limitation_visible"] else []
    limitation_svg = ''
    if limitation_lines:
        rendered = ''.join(f'<text x="270" y="{628+j*22}" text-anchor="middle" font-family="Arial,sans-serif" font-size="14" font-weight="700" fill="{bg}">{esc(line)}</text>' for j, line in enumerate(limitation_lines))
        limitation_svg = f'<g data-limit-text-color="{bg}" data-limit-panel-color="{accent}"><rect x="66" y="598" width="408" height="66" rx="14" fill="{accent}" opacity=".96"/><text x="82" y="617" font-family="Arial,sans-serif" font-size="13" font-weight="800" fill="{bg}">LIMIT</text>{rendered}</g>'
    visible_ids = ",".join(frame["visible_entity_ids"])
    affected_ids = ",".join(frame["affected_entity_ids"])
    target_state = frame["entity_state_after"]["ENT-target"]
    action_lines = wrap("ACTION · " + frame["hero_action"], 52)
    cut_lines = wrap("CUT · " + frame["information_gain"], 52)
    note_lines = action_lines[:2] + cut_lines[:2]
    notes_svg = ''.join(f'<text x="76" y="{815+j*18}" font-family="Arial,sans-serif" font-size="13" fill="{ink}" opacity=".80">{esc(line)}</text>' for j, line in enumerate(note_lines))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 540 960" width="540" height="960">
<defs><marker id="a" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0 0L0 6L9 3z" fill="{accent}"/></marker></defs>
<rect width="540" height="960" fill="{bg}"/><rect x="34" y="78" width="472" height="790" rx="28" fill="none" stroke="{ink}" stroke-opacity=".14"/>
<text x="34" y="48" font-family="Arial,sans-serif" font-size="17" fill="{ink}" opacity=".72">{story['story_id']} · {frame['start_ms']/1000:.0f}–{frame['end_ms']/1000:.0f}s · {esc(story['family'])}</text>
{text_svg}<rect x="58" y="235" width="424" height="430" rx="24" fill="{ink}" opacity=".035"/>
<g data-entity-id="ENT-target" data-state="{esc(target_state)}" data-operation="{esc(frame['visual_operation'])}" data-visible-entities="{esc(visible_ids)}" data-affected-entities="{esc(affected_ids)}" data-proof-visible="{str(frame['proof_anchor_visible']).lower()}" data-limitation="{esc(story['narrative']['limitation']) if frame['limitation_visible'] else ''}">{geometry}</g>{limitation_svg}
<rect x="58" y="700" width="424" height="72" rx="18" fill="{ink}" opacity=".08"/>
<text x="76" y="729" font-family="Arial,sans-serif" font-size="16" fill="{ink}" opacity=".82">BEFORE · {esc(compact_state(frame['entity_state_before']))}</text>
<text x="76" y="757" font-family="Arial,sans-serif" font-size="16" font-weight="700" fill="{accent}">AFTER · {esc(compact_state(frame['entity_state_after']))}</text>
<rect x="58" y="795" width="424" height="82" rx="18" fill="{ink}" opacity=".09"/>{notes_svg}
<text x="270" y="923" text-anchor="middle" font-family="Arial,sans-serif" font-size="14" fill="{ink}" opacity=".48">ORIGINAL LOCAL PREVIS · EXTERNAL PROVIDER NOT RUN</text>
</svg>'''


def frame_plan(index: int, roles: list[str], questions: list[str], s: tuple, story_id: str, family: str) -> list[dict]:
    title, hero, scene, objective, obstacle, stakes, trigger, proof, target, action, payoff, limitation = s
    role_copy = {
        "hook": (f"notices the {trigger}", f"The {trigger} changes before the objective is secure.", "Open a precise question with a visible changed object."),
        "orientation": (f"locates the {target}", f"The hero and persistent {target} share one scene; objective: {objective}.", "Reveal actor, target, and spatial relationship."),
        "obstacle": (f"sees the {target} blocked", f"The {target} is visibly blocked by {obstacle}; consequence: {stakes}.", "Make resistance and consequence inspectable."),
        "attempt": (action, f"The hero attempts to {infinitive(action)}; the {target} visibly responds.", "Show an attempted causal operation on the target."),
        "mechanism": (action, f"The hero {action}; the same {target} changes state on screen.", "Show the mechanism transforming the persistent target."),
        "proof": (f"checks the {proof}", f"The changed {target} remains visible while the {proof} is isolated.", "Bind the changed target to an inspectable proof object."),
        "limitation": (f"bounds the result with {proof}", f"The {proof} and changed {target} remain visible; boundary: {limitation}", "State where the visible evidence stops."),
        "payoff": (f"confirms the changed {target}", f"The same {target} reaches its resolved state: {payoff}.", "Close the opening question with the changed target."),
        "handback": ("returns the resolved target to the viewer", f"The resolved {target} stays visible while the sequence returns to A-roll: {payoff}.", "Close the visual argument and hand it back."),
    }
    narration_by_role = {
        "hook":"The state changed before anyone was ready.", "orientation":f"The objective is to {objective}.",
        "obstacle":f"But {obstacle}.", "attempt":f"The first visible move is to {infinitive(action)}.",
        "mechanism":f"The decisive mechanism is to {infinitive(action)}.", "proof":f"Check the {proof}, not the claim.",
        "limitation":f"The evidence stops here: {limitation}", "payoff":f"Now {payoff}.",
        "handback":f"The bounded result: {payoff}.",
    }
    shot_sets = {
        "in_medias_res": (["extreme_close","wide","medium","over_shoulder","macro","medium"], ["push_in","pull_out","locked","pan_right","rack_focus","pull_out"]),
        "result_rewind": (["close","wide","medium","over_shoulder","macro","wide"], ["pull_out","whip_pan","locked","pan_right","rack_focus","pull_out"]),
        "diagnostic_mystery": (["macro","wide","close","over_shoulder","macro","medium"], ["push_in","pull_out","pan_right","push_in","rack_focus","pull_out"]),
        "failed_attempt_correction": (["close","wide","over_shoulder","close","wide","medium"], ["push_in","pull_out","pan_right","locked","match_move","pull_out"]),
        "object_metaphor": (["macro","wide","medium","close","diagram","medium"], ["push_in","pull_out","tilt_down","locked","rack_focus","pull_out"]),
        "countdown_ladder": (["close","wide","medium","medium","macro","wide"], ["push_in","pull_out","tilt_down","match_move","rack_focus","pull_out"]),
        "before_after_transformation": (["wide","wide","close","medium","macro","wide"], ["locked","locked","push_in","pan_right","rack_focus","pull_out"]),
        "proof_reveal": (["close","wide","macro","over_shoulder","macro","medium"], ["push_in","pull_out","locked","tilt_down","rack_focus","pull_out"]),
        "contradiction_resolution": (["wide","medium","close","diagram","macro","wide"], ["locked","push_in","pan_left","tilt_down","rack_focus","pull_out"]),
        "process_handback": (["close","wide","medium","over_shoulder","macro","medium"], ["push_in","pan_right","match_move","pan_right","rack_focus","pull_out"]),
    }
    scales, motions = shot_sets[family]
    entity_state = {"ENT-hero":"observing", "ENT-trigger":"stable", "ENT-target":"absent", "ENT-obstacle":"latent", "ENT-proof":"hidden"}
    state = f"ENT-target:{target}=absent; ENT-proof:{proof}=hidden"
    frames = []
    for i, role in enumerate(roles):
        hero_action, visual, info = role_copy[role]
        next_entity_state = dict(entity_state)
        if role == "hook":
            next_entity_state.update({"ENT-hero":"aware", "ENT-trigger":"changed", "ENT-target":"resolved-preview" if family == "result_rewind" else "unoriented"})
        elif role == "orientation": next_entity_state.update({"ENT-target":"present-unresolved"})
        elif role == "obstacle": next_entity_state.update({"ENT-target":"blocked", "ENT-obstacle":"active"})
        elif role == "attempt": next_entity_state.update({"ENT-hero":"acting", "ENT-target":"failed-attempt" if family == "failed_attempt_correction" else "acted-on"})
        elif role == "mechanism": next_entity_state.update({"ENT-hero":"acting", "ENT-target":"transformed", "ENT-obstacle":"clearing"})
        elif role == "proof": next_entity_state.update({"ENT-target":"changed-pending-review", "ENT-proof":"visible"})
        elif role == "limitation": next_entity_state.update({"ENT-target":"bounded", "ENT-proof":"visible"})
        elif role == "payoff": next_entity_state.update({"ENT-target":"resolved-with-boundary", "ENT-obstacle":"cleared", "ENT-proof":"visible"})
        else: next_entity_state.update({"ENT-hero":"returned-to-A-roll", "ENT-target":"resolved", "ENT-obstacle":"cleared", "ENT-proof":"visible"})
        if i == len(roles)-1:
            next_entity_state.update({"ENT-hero":"returned-to-A-roll", "ENT-target":"resolved-with-boundary", "ENT-proof":"visible"})
        after = f"ENT-target:{target}={next_entity_state['ENT-target']}; ENT-proof:{proof}={next_entity_state['ENT-proof']}"
        visible = ["ENT-hero", "ENT-trigger"]
        if i >= 1 or family == "result_rewind": visible.append("ENT-target")
        if role in ("obstacle", "attempt") or family == "failed_attempt_correction" and i >= 2: visible.append("ENT-obstacle")
        if role in ("proof", "limitation", "payoff", "handback"): visible.append("ENT-proof")
        affected = {"hook":["ENT-trigger"], "orientation":["ENT-target"], "obstacle":["ENT-obstacle","ENT-target"], "attempt":["ENT-hero","ENT-target"], "mechanism":["ENT-hero","ENT-target"], "proof":["ENT-proof","ENT-target"], "limitation":["ENT-proof","ENT-target"], "payoff":["ENT-target"], "handback":["ENT-hero","ENT-target"]}[role]
        bfunc = {"hook":"attention_reset", "orientation":"establish_context", "obstacle":"concretize_abstraction", "attempt":"demonstrate_process", "mechanism":"demonstrate_process", "proof":"prove_state", "limitation":"prove_state", "payoff":"contrast", "handback":"emotional_texture"}[role]
        beat_roles = [role]
        if i == len(roles)-1:
            beat_roles = list(dict.fromkeys(beat_roles + ["limitation", "payoff", "handback"]))
        op_type = operation_type(action)
        frames.append({
            "frame_id": f"{story_id}-F{i+1:02d}", "sequence_number": i+1,
            "start_ms": i*1000, "end_ms": (i+1)*1000, "beat_role": role,
            "cause_frame_ids": [] if i == 0 else [f"{story_id}-F{i:02d}"],
            "beat_roles": beat_roles, "visible_entity_ids": visible, "affected_entity_ids": affected,
            "state_before": state, "state_after": after, "entity_state_before": dict(entity_state), "entity_state_after": dict(next_entity_state),
            "visual_operation": op_type, "proof_anchor_visible": role in ("proof","limitation","payoff","handback"), "limitation_visible": role == "limitation" or i == 5,
            "payoff_visible": i == len(roles)-1 or role == "payoff", "handback_visible": i == len(roles)-1 or role == "handback",
            "story_question": questions[i], "narration": narration_by_role[role], "on_screen_text": FAMILY_LABELS[family][i],
            "visual_state": visual, "hero_action": hero_action,
            "object_action": f"{', '.join(affected)} changes: {state} → {after}.",
            "scene_change": f"Family grammar `{family}` advances through `{role}` with persistent ENT-target.",
            "shot_scale": scales[i], "camera_motion": motions[i], "camera_motivation": info, "screen_direction": "left_to_right" if family not in ("diagnostic_mystery","proof_reveal","contradiction_resolution") else "centered",
            "a_roll_state": "full" if i == 0 else ("return_cut" if i == 5 else "voice_over"),
            "broll_function": bfunc, "transition": f"{motions[i]} motivated by {info.lower()}",
            "audio_cue": "voice anchor" if role not in ("hook","proof","limitation") else ("single inciting accent" if role == "hook" else "brief silence under evidence"),
            "emotion": ["surprise", "orientation", "concern", "agency", "confidence-with-caution", "relief"][i],
            "information_gain": info,
            "image_path": f"frames/{story_id}-F{i+1:02d}.svg",
            "image_prompt": f"9:16 editorial storyboard still using the `{family}` scene grammar. Anonymous geometric {hero} in {scene}. {visual} Keep ENT-target `{target}` persistent and visibly transform it through `{action}`; show ENT-proof `{proof}` when declared. Strong mobile silhouette, no logos, no real person, no final small text.",
            "negative_prompt": "No recognizable person, no brand interface, no copyrighted character, no watermark, no illegible generated copy, no unsupported result claim.",
            "acceptance_checks": ["All visible and affected entity IDs are depicted consistently.", "The persistent target shows the declared before/action/after state.", "The family-specific visual operation and camera motive add the declared information."],
        })
        state = after
        entity_state = next_entity_state
    return frames


def story_payload(number: int, family_index: int, scenario: tuple) -> dict:
    family, kind, roles, questions = FAMILY_PLANS[family_index]
    title, hero, scene, objective, obstacle, stakes, trigger, proof, target, action, payoff, limitation = scenario
    story_id = f"ST-{number:03d}"
    palette = PALETTES[(number-1) % len(PALETTES)]
    frames = frame_plan(number, roles, questions, scenario, story_id, family)
    variation_axes = {
        "operation_type": operation_type(action),
        "target_transformation": f"{target}: unresolved -> {payoff}",
        "proof_mechanism": f"{proof}; boundary={limitation}",
        "scene_topology": f"{family}::{scene}"
    }
    payload = {
        "story_id": story_id, "version": "2.0.0", "title": title, "family": family,
        "kind": kind, "duration_ms": 6000, "aspect_ratio": "9:16",
        "narrative": {
            "protagonist": hero, "point_of_view": "anonymous operator-observer",
            "objective": objective, "obstacle": obstacle, "stakes": stakes, "setup": scene,
            "inciting_change": f"The {trigger} changes state before the objective is secure.",
            "action_chain": [f"notice the {trigger}", action, f"inspect the {proof}"],
            "proof": proof, "limitation": limitation, "payoff": payoff,
            "handback": "Return to the speaking person with one bounded rule or next step.",
            "emotion_arc": ["surprise", "concern", "agency", "cautious relief"],
        },
        "continuity_bible": {
            "hero_design": "anonymous circle-headed geometric operator with consistent accent color",
            "scene": scene, "trigger_prop": trigger, "proof_prop": proof, "target_prop": target,
            "palette": list(palette), "screen_direction": "progress moves left to right; resistance blocks the center",
            "wardrobe": "non-identifying solid-color workwear",
            "forbidden_changes": ["no real-person likeness or brand marks", "do not reverse screen direction before payoff", "do not change prop identity between frames"],
        },
        "entities": [
            {"entity_id":"ENT-hero", "kind":"actor", "label":hero, "visual_token":f"hero-{number:03d}", "initial_state":"observing trigger"},
            {"entity_id":"ENT-trigger", "kind":"trigger", "label":trigger, "visual_token":slugify(trigger), "initial_state":"stable before hook"},
            {"entity_id":"ENT-target", "kind":"target", "label":target, "visual_token":slugify(target), "initial_state":"absent or unresolved"},
            {"entity_id":"ENT-obstacle", "kind":"obstacle", "label":obstacle, "visual_token":f"obstacle-{family}", "initial_state":"blocking target"},
            {"entity_id":"ENT-proof", "kind":"proof", "label":proof, "visual_token":slugify(proof), "initial_state":"hidden until evidence beat"}
        ],
        "semantic_fingerprint": canonical_hash({"objective": objective, "obstacle": obstacle, "stakes": stakes, "payoff": payoff}),
        "causal_graph_fingerprint": canonical_hash({"family": family, "roles": roles, "trigger": trigger, "action": action, "proof": proof, "target": target}),
        "visual_sequence_fingerprint": canonical_hash({"family":family, "scene": scene, "trigger": trigger, "target":target, "proof": proof, "palette": palette, "shots": [(f["shot_scale"],f["camera_motion"],f["beat_role"]) for f in frames]}),
        "variation_axes": variation_axes,
        "variation_fingerprint": canonical_hash(variation_axes),
        "clean_room_risk_notes": ["No source wording, named character, branded UI, voice, music, or distinctive source sequence may be reused.", "This package uses only original anonymous geometry and generic props.", "View-count snapshots and platform guidance are not performance or virality evidence."],
        "frames": frames,
        "rights_state": "original_local_previsualization", "external_provider_state": "NOT_RUN",
    }
    return payload


def screenplay_md(story: dict) -> str:
    n = story["narrative"]
    lines = [f"# {story['story_id']} — {story['title']}", "", "Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN`", "",
             "## Logline", "", f"{n['protagonist'].capitalize()} must {n['objective']} despite {n['obstacle']}, because {n['stakes']}; the story resolves when {n['payoff']}.", "",
             "## Story spine", "", f"- Setup: {n['setup']}", f"- Inciting change: {n['inciting_change']}", f"- Objective: {n['objective']}", f"- Obstacle: {n['obstacle']}", f"- Stakes: {n['stakes']}", f"- Action: {' → '.join(n['action_chain'])}", f"- Proof: {n['proof']}", f"- Limitation: {n['limitation']}", f"- Payoff: {n['payoff']}", "", "## Second-by-second screenplay", "",
             "| Time | Role | Narration | Visible action | Object state | Shot / movement | A/B-roll | New information |", "|---|---|---|---|---|---|---|---|"]
    for f in story["frames"]:
        lines.append(f"| {f['start_ms']/1000:.0f}–{f['end_ms']/1000:.0f}s | {f['beat_role']} | {f['narration']} | {f['hero_action']} | {f['object_action']} | {f['shot_scale']} / {f['camera_motion']} | {f['a_roll_state']} / {f['broll_function']} | {f['information_gain']} |")
    lines += ["", "## Read test", "", "Read only the six frames in order. The protagonist, objective, block, corrective action, proof, limitation, and payoff must remain inferable without this document.", ""]
    return "\n".join(lines)


def prompt_md(story: dict) -> str:
    lines = [f"# Production prompts — {story['story_id']}", "", "External image/video/audio provider execution remains NOT RUN. These prompts are future, provider-neutral replacement instructions.", "", "## Continuity lock", "", json.dumps(story["continuity_bible"], indent=2, ensure_ascii=False), ""]
    for f in story["frames"]:
        lines += [f"## {f['frame_id']} · {f['start_ms']/1000:.0f}–{f['end_ms']/1000:.0f}s", "", f"Prompt: {f['image_prompt']}", "", f"Avoid: {f['negative_prompt']}", "", f"Motion intent: {f['camera_motion']}; {f['transition'].rstrip('.')}.", ""]
    return "\n".join(lines)


def report_md(story: dict) -> str:
    n = story["narrative"]
    role_path = " → ".join(frame["beat_role"] for frame in story["frames"])
    return f"""# Story Framework Report — {story['story_id']}

## Truth state

- Storyboard: `ORIGINAL_LOCAL_PREVISUALIZATION`
- External provider: `NOT_RUN`
- Source media/frames: `NOT_COLLECTED`
- Real-person likeness: `NOT_USED`

## Use

`{story['kind']}` · `{story['family']}` · 9:16 · {story['duration_ms']/1000:.0f}s. Use as a fast insert around a speaking person, not as a final publishable claim.

## Narrative contract

Protagonist: {n['protagonist']}. Objective: {n['objective']}. Obstacle: {n['obstacle']}. Stakes: {n['stakes']}. Payoff: {n['payoff']}.

## Engagement logic

This package uses the family-specific path `{role_path}`. The persistent target remains visible from orientation through action, proof/limitation, and payoff. Each operation changes a declared entity state; the final frame closes or bounds the opening question and hands back to A-roll.

## Clean-room and production limits

All characters, words, props, sequencing, and SVGs are original abstractions. Do not map them to a reference creator's identity, composition, voice, music, wording, or branded UI. Replace SVG plates only after a separate approved provider/footage/rights run. Keep final text, UI, charts, and captions editable.
"""


def contact_sheet(story: dict) -> str:
    cells = []
    for i, f in enumerate(story["frames"]):
        x = 60 + (i % 3) * 620; y = 240 + (i // 3) * 1010
        cells.append(f'<image href="{f["image_path"]}" x="{x}" y="{y}" width="540" height="960"/><text x="{x}" y="{y+990}" font-family="Arial,sans-serif" font-size="22" fill="#1b2430">{f["frame_id"]} · {f["start_ms"]/1000:.0f}–{f["end_ms"]/1000:.0f}s · {esc(f["beat_role"])}</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 2300" width="1920" height="2300"><rect width="1920" height="2300" fill="#F4F0E7"/><text x="60" y="72" font-family="Arial,sans-serif" font-size="42" font-weight="800" fill="#111927">{story['story_id']} · {esc(story['title'])}</text><text x="60" y="118" font-family="Arial,sans-serif" font-size="22" fill="#455064">{story['family']} · 6 seconds · read left to right · LOCAL PREVIS / PROVIDER NOT RUN</text>{''.join(cells)}<text x="60" y="2250" font-family="Arial,sans-serif" font-size="20" fill="#455064">Frame sequence: hook → orientation → resistance/action → proof → bounded payoff/handback.</text></svg>'''


def main() -> None:
    if len(SCENARIOS) != 50:
        raise SystemExit(f"expected 50 scenarios, got {len(SCENARIOS)}")
    if OUT.exists():
        shutil.rmtree(OUT)
    records, total_frames = [], 0
    for idx, scenario in enumerate(SCENARIOS, 1):
        family_index = (idx - 1) // 5
        story = story_payload(idx, family_index, scenario)
        package = OUT / f"{story['story_id'].lower()}-{slugify(story['title'])}"
        dump(package / "story.json", story)
        (package / "screenplay.md").write_text(screenplay_md(story), encoding="utf-8")
        (package / "prompt.md").write_text(prompt_md(story), encoding="utf-8")
        (package / "report.md").write_text(report_md(story), encoding="utf-8")
        colors = tuple(story["continuity_bible"]["palette"])
        for f in story["frames"]:
            path = package / f["image_path"]; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(scene_svg(story, f, colors), encoding="utf-8")
        (package / "contact-sheet.svg").write_text(contact_sheet(story), encoding="utf-8")
        file_paths = [p for p in package.rglob("*") if p.is_file() and p.name != "manifest.json"]
        manifest = {"schema":"studio-story-package-manifest.v2", "story_id":story["story_id"], "external_provider_state":"NOT_RUN", "files":{p.relative_to(package).as_posix():hash_file(p) for p in sorted(file_paths)}}
        dump(package / "manifest.json", manifest)
        record_hash = hashlib.sha256((package / "story.json").read_bytes()).hexdigest()
        records.append({"story_id":story["story_id"], "title":story["title"], "family":story["family"], "path":package.relative_to(OUT).as_posix(), "frame_count":len(story["frames"]), "story_sha256":record_hash})
        total_frames += len(story["frames"])
    library = {"schema":"studio-story-library.v2", "generated_at":GENERATED_AT, "story_count":len(records), "frame_count":total_frames, "rights_state":"original_local_previsualization", "external_provider_state":"NOT_RUN", "records":records}
    dump(OUT / "library-manifest.json", library)
    catalog = ["# Studio Sequential Story Library v2", "", "Truth state: `50 ORIGINAL LOCAL SVG PREVISUALIZATIONS / 300 FRAMES / EXTERNAL PROVIDER NOT RUN`", "", "Every folder contains `story.json`, `screenplay.md`, `prompt.md`, `report.md`, six ordered SVG frames, a contact sheet, and a checksum manifest.", "", "| ID | Title | Family | Protagonist | Objective |", "|---|---|---|---|---|"]
    for record in records:
        story = json.loads((OUT / record["path"] / "story.json").read_text(encoding="utf-8"))
        catalog.append(f"| {story['story_id']} | {story['title']} | `{story['family']}` | {story['narrative']['protagonist']} | {story['narrative']['objective']} |")
    catalog += ["", "## How to read one package", "", "Start with `contact-sheet.svg`, then read the six frame SVGs left-to-right. Use `screenplay.md` for narration and cut logic, `prompt.md` for future provider/footage replacement, `story.json` for automation, and `report.md` for truth/rights boundaries.", ""]
    (OUT / "CATALOG.md").write_text("\n".join(catalog), encoding="utf-8")
    print(json.dumps({"status":"BUILT", "stories":len(records), "frames":total_frames, "output":OUT.relative_to(ROOT).as_posix()}, indent=2))


if __name__ == "__main__":
    main()
