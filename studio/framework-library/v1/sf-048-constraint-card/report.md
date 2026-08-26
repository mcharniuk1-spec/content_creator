# SF-048 — Constraint Card

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN / OWNER_REVIEW_PENDING`

## Purpose

Lead with the boundary that makes a claim honest This is a 9-second reusable hook/intro/B-roll insert, not a final video and not a performance claim.

## Signal provenance

- Export: `SIGEXP-SF-048`
- Sources: `SRC-WEB-003`
- Evidence: `EVID-WEB-010`
- Rights: `metadata_commentary_only` source abstraction; output frames are original local previsualization.

## Taxonomy

| Axis | Value |
|---|---|
| `hook_mechanism` | `reveal` |
| `viewer_job` | `identify_problem` |
| `broll_function` | `concretize_abstraction` |
| `proof_form` | `paraphrased_source` |
| `visual_grammar` | `mock_screen_capture` |
| `pacing_profile` | `rapid_beat` |
| `transition_family` | `push` |
| `a_roll_integration` | `voice_over_broll` |
| `sound_role` | `accent_sfx` |
| `text_role` | `step_counter` |
| `cta_exit` | `no_cta` |
| `risk_class` | `low` |

## Talking-head integration

Follow each frame's `a_roll_state`. `full` and `return_cut` show the speaker; `voice_over` keeps narration while B-roll carries the image; `picture_in_picture` retains the speaker as an inset; `absent` is a full visual insert. Preserve narration continuity with a J- or L-cut only when it clarifies the spoken beat.

## Second-by-second plan

| Time | Story function | A-roll | B-roll function | Editable text | Frame |
|---|---|---|---|---|---|
| 0–1s | claim | voice_over | concretize_abstraction | THE CLAIM | `frames/SF-048-F01.svg` |
| 1–2s | hide/reveal | voice_over | concretize_abstraction | REVEAL | `frames/SF-048-F02.svg` |
| 2–3s | proof close-up | voice_over | concretize_abstraction | PROOF | `frames/SF-048-F03.svg` |
| 3–4s | trace | voice_over | concretize_abstraction | TRACE | `frames/SF-048-F04.svg` |
| 4–5s | limitation | voice_over | concretize_abstraction | LIMIT | `frames/SF-048-F05.svg` |
| 5–6s | bridge detail | voice_over | concretize_abstraction | BRIDGE | `frames/SF-048-F06.svg` |
| 6–7s | proof hold | voice_over | concretize_abstraction | HOLD | `frames/SF-048-F07.svg` |
| 7–8s | counterpoint | voice_over | concretize_abstraction | CHECK | `frames/SF-048-F08.svg` |
| 8–9s | verdict | return_cut | concretize_abstraction | VERDICT | `frames/SF-048-F09.svg` |

## Production prompt

Create a vertical 9:16 9-second clean-room insert titled “Constraint Card.” Use one meaningful visual state per second. Hook mechanism: `reveal`. Viewer job: `identify_problem`. Visual grammar: `mock_screen_capture`. B-roll function: `concretize_abstraction`. Proof form: `paraphrased_source`. Keep all captions, labels, UI-like elements, and proof callouts as editable deterministic overlays. Maintain an 8% horizontal and 10% vertical planning inset, then verify the actual platform UI safe zone at production. Use only original or licensed footage and audio. Do not copy creator wording, source frames, layouts, music, gestures, identity, branded UI, or distinctive sequence. External image/video/audio provider execution remains NOT RUN.

## Analysis notes

- FACT: every visual change is explicitly timecoded and has an A-roll/B-roll function.
- INTERPRETATION: the one-second cadence is a review scaffold; production may hold or subdivide a beat only after the story function remains legible.
- HYPOTHESIS: this framework may help orient attention for its declared viewer job; it does not guarantee retention or reach.
- GAP: no owned performance test, platform-specific UI-safe-zone check, final footage, audio, or owner approval exists.

## Acceptance

- All 9 intervals are contiguous and cover 0–9000 ms.
- The hook is visible during 0–1000 ms.
- Text stays editable and within the planning safe zone.
- Source lineage and rights IDs remain attached.
- Final video, provider generation, Figma, publishing, and deployment remain `NOT_RUN`.
