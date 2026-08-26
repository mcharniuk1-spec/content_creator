# SF-010 — Tool Fit

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN / OWNER_REVIEW_PENDING`

## Purpose

Test whether a tool matches the job This is a 7-second reusable hook/intro/B-roll insert, not a final video and not a performance claim.

## Signal provenance

- Export: `SIGEXP-SF-010`
- Sources: `SRC-WEB-004`
- Evidence: `EVID-WEB-004`
- Rights: `metadata_commentary_only` source abstraction; output frames are original local previsualization.

## Taxonomy

| Axis | Value |
|---|---|
| `hook_mechanism` | `diagnostic_question` |
| `viewer_job` | `verify_claim` |
| `broll_function` | `attention_reset` |
| `proof_form` | `observed_artifact` |
| `visual_grammar` | `split_screen` |
| `pacing_profile` | `rapid_beat` |
| `transition_family` | `dissolve` |
| `a_roll_integration` | `full_open` |
| `sound_role` | `voice_plus_accent` |
| `text_role` | `question_card` |
| `cta_exit` | `save_reference` |
| `risk_class` | `source_dependent` |

## Talking-head integration

Follow each frame's `a_roll_state`. `full` and `return_cut` show the speaker; `voice_over` keeps narration while B-roll carries the image; `picture_in_picture` retains the speaker as an inset; `absent` is a full visual insert. Preserve narration continuity with a J- or L-cut only when it clarifies the spoken beat.

## Second-by-second plan

| Time | Story function | A-roll | B-roll function | Editable text | Frame |
|---|---|---|---|---|---|
| 0–1s | question | full | attention_reset | IS THIS YOU? | `frames/SF-010-F01.svg` |
| 1–2s | symptom | voice_over | attention_reset | THE SYMPTOM | `frames/SF-010-F02.svg` |
| 2–3s | choice | voice_over | attention_reset | CHOOSE | `frames/SF-010-F03.svg` |
| 3–4s | diagnosis | voice_over | attention_reset | DIAGNOSIS | `frames/SF-010-F04.svg` |
| 4–5s | mechanism | voice_over | attention_reset | WHY | `frames/SF-010-F05.svg` |
| 5–6s | bridge detail | voice_over | attention_reset | BRIDGE | `frames/SF-010-F06.svg` |
| 6–7s | answer frame | return_cut | attention_reset | ANSWER | `frames/SF-010-F07.svg` |

## Production prompt

Create a vertical 9:16 7-second clean-room insert titled “Tool Fit.” Use one meaningful visual state per second. Hook mechanism: `diagnostic_question`. Viewer job: `verify_claim`. Visual grammar: `split_screen`. B-roll function: `attention_reset`. Proof form: `observed_artifact`. Keep all captions, labels, UI-like elements, and proof callouts as editable deterministic overlays. Maintain an 8% horizontal and 10% vertical planning inset, then verify the actual platform UI safe zone at production. Use only original or licensed footage and audio. Do not copy creator wording, source frames, layouts, music, gestures, identity, branded UI, or distinctive sequence. External image/video/audio provider execution remains NOT RUN.

## Analysis notes

- FACT: every visual change is explicitly timecoded and has an A-roll/B-roll function.
- INTERPRETATION: the one-second cadence is a review scaffold; production may hold or subdivide a beat only after the story function remains legible.
- HYPOTHESIS: this framework may help orient attention for its declared viewer job; it does not guarantee retention or reach.
- GAP: no owned performance test, platform-specific UI-safe-zone check, final footage, audio, or owner approval exists.

## Acceptance

- All 7 intervals are contiguous and cover 0–7000 ms.
- The hook is visible during 0–1000 ms.
- Text stays editable and within the planning safe zone.
- Source lineage and rights IDs remain attached.
- Final video, provider generation, Figma, publishing, and deployment remain `NOT_RUN`.
