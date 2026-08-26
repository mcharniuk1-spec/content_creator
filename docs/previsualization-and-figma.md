# Previsualization and Figma Delivery Contract

## First-stage output per video

Each of the 10–15 selected content concepts must be longer than 15 seconds and deliver:

1. one approved evidence-backed concept and plot;
2. one versioned three-iteration prompt chain;
3. a timecoded frame/shot sequence covering the full duration;
4. separate source/generation instructions for every base visual, talking-head plate, product/UI layer, screen recording, overlay, caption, transition, and audio cue;
5. individual storyboard frames with stable IDs;
6. one combined contact-sheet image showing the complete sequence in order;
7. captions and platform copy;
8. one self-contained PDF report;
9. a Figma delivery manifest and review status.

## Timing and frame density

“Frame-by-frame” means every meaningful visual state or shot, not 24 still images per second. Use enough frames to make the full plot, transitions, overlays, and timing unambiguous:

- 16–20 seconds: usually 8–12 meaningful frames/shots;
- 21–30 seconds: usually 10–16;
- 31–45 seconds: usually 14–22.

No visual state may last longer than the narrative can support. Talking-head segments should show planned cutaways, overlays, or visual resets. Every transition names its source frame, destination frame, duration, and motion intent.

## Layered-frame rule

When a person speaks while images, charts, UI, or captions appear:

1. plan the person/talking-head plate separately;
2. plan or create every image/UI/chart separately;
3. keep final captions and interface text as editable deterministic layers;
4. define mask, crop, position, entrance, exit, and z-order;
5. assemble one combined storyboard frame for review;
6. preserve links from the composite to every component asset and prompt.

Do not ask an image model to render final small text, charts, or product UI inside the image when editable overlays can produce a reliable result.

## Contact-sheet specification

One image per video, recommended 3840 px wide or another readable high-resolution canvas. It must contain:

- video ID, working title, platform/aspect, target duration, version, and candidate-set hash;
- all storyboard frames in reading order;
- frame number and time range under each frame;
- short visual-state label and narration/on-screen-text cue;
- explicit icons/labels for talking head, generated still, screen recording, motion graphic, licensed/public footage, and audio event;
- transitions between frames;
- no tiny unreadable production prompts; full prompts stay in the PDF;
- footer with evidence status, rights status, reviewer verdict, local storyboard-asset state, and external provider state `NOT RUN`.

Export both the single contact sheet and the individual frames. The contact sheet is a review artifact, not the only editable source.

## PDF report specification

Create one PDF per planned video, with a source Markdown/HTML/document file retained for revision. Use exactly these 17 canonical sections, in this order:

1. `cover_and_truth_state` — video ID/title, channel, aspect, duration, audience, content pillar, version, local storyboard state, external provider state, and owner state;
2. `audience_problem_pain_consequence_mechanism_limitation_cta` — forcing moment, problem, pain, consequence, bounded mechanism/tool, limitation, and CTA;
3. `source_ledger_and_claim_map` — evidence subset, URLs, dates, claim state, and limitations;
4. `pattern_abstractions_and_clean_room_restrictions` — reusable patterns and prohibited similarities;
5. `concept_v1_and_critique` — base concept prompt, alternatives, critic notes, and revision;
6. `story_v2_and_beat_sheet` — plot, narration, beats, time budget, and critic notes;
7. `production_prompt_v3` — production prompt, negative constraints, continuity bible, and provider-neutral instructions;
8. `candidate_set_hash_and_judge_verdicts` — immutable hash and all three independent scores/verdicts;
9. `timecoded_frame_table` — dialogue, on-screen text, visuals, layers, transitions, audio, prompts, and acceptance checks;
10. `contact_sheet` — the current combined sequence image and its manifest hash;
11. `asset_prompts_negatives_continuity_fallbacks` — every base/subject/overlay/motion asset and fallback;
12. `screen_recording_plan` — route/mock, viewport, cursor, data, timing, privacy, and redaction;
13. `narration_captions_music_ambience_sfx` — separate dialogue and audio-stem plan;
14. `edit_timeline_transitions_platform_variants` — assembly order, OpenMontage/native route, transitions, captions, and aspect recomposition;
15. `candidate_provider_model_routing` — future candidates, data/cost/rights gaps, and every external execution marked `NOT RUN`;
16. `rights_consent_accessibility_qa_cost_approvals_fallback` — rights, consent, accessibility, QA, cost placeholder, approvals, review verdict, checksum IDs, and fallbacks;
17. `platform_copy_transcript_alt_text` — LinkedIn, Reels, Threads, and X copy, transcript, cover/title, and alt text.

The PDF must not contain secrets, account identifiers, private URLs, raw personal media, or unsupported performance claims.

## Figma identity and mutation gate

The expected authenticated Figma account for this project is specified in the private/local handoff prompt. The Figma expert must:

1. call `whoami` before any file or page operation;
2. compare the returned email exactly with the expected identity;
3. if it differs, stop with `FIGMA_IDENTITY_MISMATCH` and ask the owner to switch accounts; never log out, log in, or change accounts autonomously;
4. obtain the exact target file or permission to create a file/page;
5. inspect existing design context and metadata, then capture a screenshot baseline;
6. present the planned page/section names and mutation scope;
7. receive exact owner approval;
8. mutate only the approved target;
9. capture post-change screenshots and a delivery receipt.

Recommended Figma page: `Content Engine — Research & Storyboards`.

Recommended sections:

- `00 — System & Status`
- `01 — Research Signals`
- `02 — Video Contact Sheets`
- `03 — Individual Frames`
- `04 — Static/Carousel Concepts`
- `05 — Components & Styles`
- `06 — Approved Delivery`

Each video section contains: title/status card, evidence/pain/solution card, full contact sheet, individual editable frames, asset/component strip, captions, and owner/reviewer status. Use auto layout, shared typography/color styles, stable frame IDs, and editable text.

## Previsualization review gate

Pass only when:

- duration exceeds 15 seconds and timecodes cover the full duration;
- narrative causality is clear without the production report;
- every frame has a story function;
- talking-head and overlay layers are separately specified;
- individual frames and the contact sheet agree;
- no final text is trapped in unreliable generated pixels;
- source/rights, local storyboard-asset state, and external provider state are visible;
- continuity, safe zones, contrast, captions, and mobile readability pass;
- the PDF opens, has every required section, and embeds the correct contact sheet;
- Figma is either verified and approved or truthfully marked pending/blocked.
