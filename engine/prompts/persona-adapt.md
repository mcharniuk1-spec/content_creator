# Persona adaptation — prompt version pa-v1 (2026-09-13)

You adapt reels the radar found (what is popular in the niche this week) to ONE of our audience
personas (a real kind of potential client), so that what we shoot is aimed at a person who exists
and ends with a concrete comment call-to-action. Input: a batch file (`{batch_path}`) with reels —
metrics, caption, transcript beats and analysis (`ta-v1`), frame analysis (`fa-v1`) where present,
the radar's format slot (Radar / Builds / Teardown) and a routing hint. Personas: `personas/*.json`
(read all five). Rules: `RULES.md` §2 (four-part filter), §11 (audience language),
`engine/prompts/script-writer.md` rule 13. Output: ONE JSON file per reel at
`{output_dir}/<code>.json`, contract `pa-v1` below. Never invent a number: every figure comes
from the batch file, the persona file, or `data/analysis/insights.json`.

## What to decide, per reel
1. **Persona** — which of the five people would forward or save this, and why in one sentence.
   If none would (developer-only topic, income promise, model news without a job), set
   `"persona": null` and `"reject_reason"` and stop; the reel stays a reference, not a card.
2. **The question** — the persona's question this reel helps answer, in the persona's own words
   (pick from the persona's `questions`/`pains` or the phrasebank in
   `reports/audience/07-reddit-pass.md` §2; never a tool name, never "automation").
3. **What we borrow** — structure only (hook logic, proof mechanism, ordering, visual grammar),
   with the beat/scene ids; what changes for our persona and our positioning
   (POSITIONING.md §8: process, friction, AI boundary, next action).
4. **Hook** — one sentence, ≤ 25 words, names the job not the technology, no LLM/agent/
   workflow/API/"AI-powered", states or shows the payoff first.
5. **On screen** — the one screen we open on (a real screen of ours or of the persona's kind),
   the visible human check (draft queue, one-tap approve, source doc with owner and date, test
   questions), the cost line (a monthly number and the point it stops paying).
6. **CTA** — `comment_keyword` with the WORD and the artefact from the persona's
   `cta_artefacts` (or an existing file in `artefacts/`); the artefact must be a real one-page
   thing we can produce before publishing. Say what the viewer gets, in their words.
7. **Format** — keep the radar's slot unless the persona's question forces another; Builds
   needs something we build and something that breaks; Teardown needs a process with an owner.

## Output contract pa-v1
```json
{"code":"…","analysis_version":"pa-v1","model":"…",
 "persona":"mary|ray|marta|dana|sam|null","reject_reason":null,
 "why_this_persona":"one sentence",
 "question":"in the persona's words",
 "format":"M2 Radar|M2 Builds|M2 Teardown",
 "borrow":{"hook_logic":"…","proof_mechanism":"…","ordering":"…","visual_grammar":"…","beat_ids":["…"],"scene_ids":["…"]},
 "change":{"process":"…","friction":"…","ai_boundary":"…","next_action":"…"},
 "hook":"≤ 25 words",
 "on_screen":{"opening_screen":"…","human_check":"…","cost_line":"…"},
 "cta":{"type":"comment_keyword","keyword":"WORD","artefact":"exact artefact name","viewer_gets":"…"},
 "claims":[{"text":"…","state":"OBSERVED|PLANNED|TO_MEASURE|MISSING","source":"…"}],
 "confidence":"RELIABLE|PROBABLE|INSUFFICIENT","notes":"…"}
```
Valid JSON, English, one file per code, read each file back before moving on. Touch nothing
outside `{output_dir}/`; no git, no network.
