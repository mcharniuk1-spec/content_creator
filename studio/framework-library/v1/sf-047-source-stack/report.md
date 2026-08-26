# SF-047 — Source Stack

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN / OWNER_REVIEW_PENDING`

## Purpose

Layer sources behind a claim This is a 8-second reusable hook/intro/B-roll insert, not a final video and not a performance claim.

## Signal provenance

- Export: `SIGEXP-SF-047`
- Sources: `SRC-WEB-003`
- Evidence: `EVID-WEB-010`
- Rights: `metadata_commentary_only` source abstraction; output frames are original local previsualization.

## Taxonomy

| Axis | Value |
|---|---|
| `hook_mechanism` | `reveal` |
| `viewer_job` | `imagine_outcome` |
| `broll_function` | `establish_context` |
| `proof_form` | `calculation` |
| `visual_grammar` | `object_macro` |
| `pacing_profile` | `slow_observation` |
| `transition_family` | `graphic_reveal` |
| `a_roll_integration` | `delayed_reveal` |
| `sound_role` | `music_pulse` |
| `text_role` | `labels` |
| `cta_exit` | `loop_to_open` |
| `risk_class` | `low` |

## Talking-head integration

Follow each frame's `a_roll_state`. `full` and `return_cut` show the speaker; `voice_over` keeps narration while B-roll carries the image; `picture_in_picture` retains the speaker as an inset; `absent` is a full visual insert. Preserve narration continuity with a J- or L-cut only when it clarifies the spoken beat.

## Second-by-second plan

| Time | Story function | A-roll | B-roll function | Editable text | Frame |
|---|---|---|---|---|---|
| 0–1s | claim | absent | establish_context | THE CLAIM | `frames/SF-047-F01.svg` |
| 1–2s | hide/reveal | absent | establish_context | REVEAL | `frames/SF-047-F02.svg` |
| 2–3s | proof close-up | full | establish_context | PROOF | `frames/SF-047-F03.svg` |
| 3–4s | trace | voice_over | establish_context | TRACE | `frames/SF-047-F04.svg` |
| 4–5s | limitation | voice_over | establish_context | LIMIT | `frames/SF-047-F05.svg` |
| 5–6s | bridge detail | voice_over | establish_context | BRIDGE | `frames/SF-047-F06.svg` |
| 6–7s | proof hold | voice_over | establish_context | HOLD | `frames/SF-047-F07.svg` |
| 7–8s | verdict | return_cut | establish_context | VERDICT | `frames/SF-047-F08.svg` |

## Production prompt

Create a vertical 9:16 8-second clean-room insert titled “Source Stack.” Use one meaningful visual state per second. Hook mechanism: `reveal`. Viewer job: `imagine_outcome`. Visual grammar: `object_macro`. B-roll function: `establish_context`. Proof form: `calculation`. Keep all captions, labels, UI-like elements, and proof callouts as editable deterministic overlays. Maintain an 8% horizontal and 10% vertical planning inset, then verify the actual platform UI safe zone at production. Use only original or licensed footage and audio. Do not copy creator wording, source frames, layouts, music, gestures, identity, branded UI, or distinctive sequence. External image/video/audio provider execution remains NOT RUN.

## Analysis notes

- FACT: every visual change is explicitly timecoded and has an A-roll/B-roll function.
- INTERPRETATION: the one-second cadence is a review scaffold; production may hold or subdivide a beat only after the story function remains legible.
- HYPOTHESIS: this framework may help orient attention for its declared viewer job; it does not guarantee retention or reach.
- GAP: no owned performance test, platform-specific UI-safe-zone check, final footage, audio, or owner approval exists.

## Acceptance

- All 8 intervals are contiguous and cover 0–8000 ms.
- The hook is visible during 0–1000 ms.
- Text stays editable and within the planning safe zone.
- Source lineage and rights IDs remain attached.
- Final video, provider generation, Figma, publishing, and deployment remain `NOT_RUN`.
