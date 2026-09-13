# Script reviewer brief — prompt version sr-v1 (2026-09-12)

You review every card in `cards/C-*.json` (schema `m2radar.card.v2`) as an independent reviewer
(spec = `M2Radar_Content_Engine_Full_Execution_Prompt_v4.md`, §28 Script review sub-agent). You did not write them. You may edit the card files in place, but every change is
recorded: the original writer script is kept as `script_versions` version 1 when the card is
saved (the orchestrator does that), so you must (a) set `review.version = 1`, `review.findings`
= list of concrete findings (each: `"[<area>] <what is wrong> → <what you changed / left>"`),
`review.revised = true` when you changed script text or storyboard timing, and (b) bump
`script.version` to 2 when the script text changed (recompute `words`, `seconds`, `total_words`,
`total_s`, and the storyboard `start_s`/`end_s` so scenes stay contiguous and cover the script).

Check every card against, in this order:
1. **Evidence grounding** — every number in the script exists in `claims[]` with the right state and a
   real source (`data/analysis/insights.json`, `reports/analysis/*.md`, `reports/data/*`, the
   reference reels' metrics in `data/radar.db`, our run logs quoted in `reports/audit/03-*.md`). Recompute
   any number you doubt from `data/radar.db` (tables video_features, beats, scenes, reels, scores,
   creator_stats). A wrong number is a hard finding: fix the script or downgrade the claim to
   TO_MEASURE/MISSING and rewrite the line.
2. **Source relevance & originality** — open each referenced reel's `data/analysis/transcripts/<code>.json`
   beat text and compare with the script: no sentence may be a paraphrase of a source sentence; the borrowed
   element must match the declared `function`; `transformed_how` must be true.
3. **Positioning fit** — POSITIONING.md §4–§8: audience is a non-technical SMB leader; the four filter
   fields are literally true and the `process` is the viewer's own repeated process (our pipeline only as
   evidence); nothing from the "do not publish" list; no revenue/savings/client claims; no service pitch;
   a comment-keyword CTA is allowed (Misha, 12 Sep 2026) but only if the promised artefact exists in the repo or is named in `claims[]` as OBSERVED/PLANNED — a gate promising nothing real is a hard finding.
4. **Hook strength** — first line states or shows the payoff; ≤ 8 s; no tool name/jargon/"token" before
   second 3; the three candidate hooks are distinct and at most one is a question.
5. **Clarity, spoken naturalness, pacing** — read it aloud in your head: short sentences, concrete nouns,
   2.3–2.6 wps; total 50–70 s (PRODUCTION.md) unless justified in findings; no repetition; information
   density high but followable by a level-0–6 viewer without pausing.
6. **Emotional flow & payoff** — tension → mechanism → proof → payoff → next action; a payoff scene exists.
7. **Visual compatibility** — storyboard contiguous, every section mapped; a screen/proof insert within the
   first 10 s where a screen exists (I-09); `frame_type`/`layout` consistent with PRODUCTION.md (one take,
   a speaker change is the only hard cut; inserts are `overlay_reveal`/`ui_zoom`/`text_punch_in`); overlay
   text ≤ 7 words, no emoji; CTA scene has a visual; scene durations ≥ 1.5 s; the frame plan supports the hook.
8. **Timing arithmetic** — `sections[].seconds` ≈ words / target_wps; storyboard sums to `total_s` (±0.5).
9. **Traceability** — `traceability` answers the ten questions of §54 of the execution spec (`M2Radar_Content_Engine_Full_Execution_Prompt_v4.md`: which evidence, which hypothesis, which sources and why, which transcripts, which statistical signals, which visual patterns, how transformed, what is original, why better than generic, can the path be reconstructed from DB records) (evidence, hypothesis, references
   with reasons, transcripts, stats signals, frame patterns, transformation, original synthesis, why better
   than generic); insights ids exist in `data/analysis/insights.json`; hypothesis id matches
   `data/analysis/hypotheses.json`.
10. **Schema** — `python3 -m engine.cards_v2 validate cards/<id>.json` → 0 errors after your edits.
11. **Audience language** (writer rule 13; `reports/audience/07-reddit-pass.md`) — the card names a persona and a
    question from the phrasebank; the hook and first 10 s contain no LLM/RAG/agent/workflow/MCP/API/"AI-powered";
    no machine-text tells ("quietly", "it's not X, it's Y", em-dashes); a human check is visible on screen; cost is a
    monthly number with the break-even point; no "replace people"; no customer-facing bot as the promise (after-hours
    intake excepted); prices come from a price sheet; the CTA artefact is a real one-page deliverable. Any miss is a
    hard finding.

Also produce `reports/analysis/10-script-review.md`: one section per card with the findings, what was
revised, the before/after of any changed line, the final verdict (PRODUCTION_READY | READY_WITH_NOTES |
NOT_READY) and the ten-question checklist (execution spec §54, listed above) answered in one line each. Then set
`status` = "REVIEWED" on every card that is PRODUCTION_READY or READY_WITH_NOTES, leave "DRAFT" otherwise.
Never invent numbers. English.
