# SF-032 — Three Fast Checks

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN / OWNER_REVIEW_PENDING`

## Purpose

Give a rapid preflight This is a 5-second reusable hook/intro/B-roll insert, not a final video and not a performance claim.

## Signal provenance

- Export: `SIGEXP-SF-032`
- Sources: `SRC-WEB-005`
- Evidence: `EVID-WEB-007`
- Rights: `metadata_commentary_only` source abstraction; output frames are original local previsualization.

## Taxonomy

| Axis | Value |
|---|---|
| `hook_mechanism` | `countdown` |
| `viewer_job` | `identify_problem` |
| `broll_function` | `attention_reset` |
| `proof_form` | `constraint` |
| `visual_grammar` | `mock_screen_capture` |
| `pacing_profile` | `held_reveal` |
| `transition_family` | `push` |
| `a_roll_integration` | `return_cut` |
| `sound_role` | `accent_sfx` |
| `text_role` | `step_counter` |
| `cta_exit` | `recap` |
| `risk_class` | `source_dependent` |

## Talking-head integration

Follow each frame's `a_roll_state`. `full` and `return_cut` show the speaker; `voice_over` keeps narration while B-roll carries the image; `picture_in_picture` retains the speaker as an inset; `absent` is a full visual insert. Preserve narration continuity with a J- or L-cut only when it clarifies the spoken beat.

## Second-by-second plan

| Time | Story function | A-roll | B-roll function | Editable text | Frame |
|---|---|---|---|---|---|
| 0–1s | number promise | voice_over | attention_reset | 3 THINGS | `frames/SF-032-F01.svg` |
| 1–2s | item one | voice_over | attention_reset | 01 | `frames/SF-032-F02.svg` |
| 2–3s | item two | voice_over | attention_reset | 02 | `frames/SF-032-F03.svg` |
| 3–4s | pattern | voice_over | attention_reset | THE PATTERN | `frames/SF-032-F04.svg` |
| 4–5s | save exit | return_cut | attention_reset | SAVE | `frames/SF-032-F05.svg` |

## Production prompt

Create a vertical 9:16 5-second clean-room insert titled “Three Fast Checks.” Use one meaningful visual state per second. Hook mechanism: `countdown`. Viewer job: `identify_problem`. Visual grammar: `mock_screen_capture`. B-roll function: `attention_reset`. Proof form: `constraint`. Keep all captions, labels, UI-like elements, and proof callouts as editable deterministic overlays. Maintain an 8% horizontal and 10% vertical planning inset, then verify the actual platform UI safe zone at production. Use only original or licensed footage and audio. Do not copy creator wording, source frames, layouts, music, gestures, identity, branded UI, or distinctive sequence. External image/video/audio provider execution remains NOT RUN.

## Analysis notes

- FACT: every visual change is explicitly timecoded and has an A-roll/B-roll function.
- INTERPRETATION: the one-second cadence is a review scaffold; production may hold or subdivide a beat only after the story function remains legible.
- HYPOTHESIS: this framework may help orient attention for its declared viewer job; it does not guarantee retention or reach.
- GAP: no owned performance test, platform-specific UI-safe-zone check, final footage, audio, or owner approval exists.

## Acceptance

- All 5 intervals are contiguous and cover 0–5000 ms.
- The hook is visible during 0–1000 ms.
- Text stays editable and within the planning safe zone.
- Source lineage and rights IDs remain attached.
- Final video, provider generation, Figma, publishing, and deployment remain `NOT_RUN`.
