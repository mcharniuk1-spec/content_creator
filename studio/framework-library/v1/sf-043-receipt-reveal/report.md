# SF-043 — Receipt Reveal

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN / OWNER_REVIEW_PENDING`

## Purpose

Reveal a dated execution receipt This is a 4-second reusable hook/intro/B-roll insert, not a final video and not a performance claim.

## Signal provenance

- Export: `SIGEXP-SF-043`
- Sources: `SRC-WEB-003`
- Evidence: `EVID-WEB-010`
- Rights: `metadata_commentary_only` source abstraction; output frames are original local previsualization.

## Taxonomy

| Axis | Value |
|---|---|
| `hook_mechanism` | `reveal` |
| `viewer_job` | `assess_risk` |
| `broll_function` | `demonstrate_process` |
| `proof_form` | `process_trace` |
| `visual_grammar` | `diagram_build` |
| `pacing_profile` | `slow_observation` |
| `transition_family` | `cut_on_sound` |
| `a_roll_integration` | `picture_in_picture` |
| `sound_role` | `silence_drop` |
| `text_role` | `headline_only` |
| `cta_exit` | `answer_question` |
| `risk_class` | `low` |

## Talking-head integration

Follow each frame's `a_roll_state`. `full` and `return_cut` show the speaker; `voice_over` keeps narration while B-roll carries the image; `picture_in_picture` retains the speaker as an inset; `absent` is a full visual insert. Preserve narration continuity with a J- or L-cut only when it clarifies the spoken beat.

## Second-by-second plan

| Time | Story function | A-roll | B-roll function | Editable text | Frame |
|---|---|---|---|---|---|
| 0–1s | claim | picture_in_picture | demonstrate_process | THE CLAIM | `frames/SF-043-F01.svg` |
| 1–2s | hide/reveal | picture_in_picture | demonstrate_process | REVEAL | `frames/SF-043-F02.svg` |
| 2–3s | trace | picture_in_picture | demonstrate_process | TRACE | `frames/SF-043-F03.svg` |
| 3–4s | verdict | picture_in_picture | demonstrate_process | VERDICT | `frames/SF-043-F04.svg` |

## Production prompt

Create a vertical 9:16 4-second clean-room insert titled “Receipt Reveal.” Use one meaningful visual state per second. Hook mechanism: `reveal`. Viewer job: `assess_risk`. Visual grammar: `diagram_build`. B-roll function: `demonstrate_process`. Proof form: `process_trace`. Keep all captions, labels, UI-like elements, and proof callouts as editable deterministic overlays. Maintain an 8% horizontal and 10% vertical planning inset, then verify the actual platform UI safe zone at production. Use only original or licensed footage and audio. Do not copy creator wording, source frames, layouts, music, gestures, identity, branded UI, or distinctive sequence. External image/video/audio provider execution remains NOT RUN.

## Analysis notes

- FACT: every visual change is explicitly timecoded and has an A-roll/B-roll function.
- INTERPRETATION: the one-second cadence is a review scaffold; production may hold or subdivide a beat only after the story function remains legible.
- HYPOTHESIS: this framework may help orient attention for its declared viewer job; it does not guarantee retention or reach.
- GAP: no owned performance test, platform-specific UI-safe-zone check, final footage, audio, or owner approval exists.

## Acceptance

- All 4 intervals are contiguous and cover 0–4000 ms.
- The hook is visible during 0–1000 ms.
- Text stays editable and within the planning safe zone.
- Source lineage and rights IDs remain attached.
- Final video, provider generation, Figma, publishing, and deployment remain `NOT_RUN`.
