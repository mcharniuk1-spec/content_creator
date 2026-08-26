# SF-020 — One Bad Handoff

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN / OWNER_REVIEW_PENDING`

## Purpose

Trace one broken handoff downstream This is a 5-second reusable hook/intro/B-roll insert, not a final video and not a performance claim.

## Signal provenance

- Export: `SIGEXP-SF-020`
- Sources: `SRC-WEB-004`
- Evidence: `EVID-WEB-005`
- Rights: `metadata_commentary_only` source abstraction; output frames are original local previsualization.

## Taxonomy

| Axis | Value |
|---|---|
| `hook_mechanism` | `consequence` |
| `viewer_job` | `verify_claim` |
| `broll_function` | `concretize_abstraction` |
| `proof_form` | `constraint` |
| `visual_grammar` | `split_screen` |
| `pacing_profile` | `rapid_beat` |
| `transition_family` | `none` |
| `a_roll_integration` | `return_cut` |
| `sound_role` | `voice_plus_accent` |
| `text_role` | `keyword_captions` |
| `cta_exit` | `no_cta` |
| `risk_class` | `low` |

## Talking-head integration

Follow each frame's `a_roll_state`. `full` and `return_cut` show the speaker; `voice_over` keeps narration while B-roll carries the image; `picture_in_picture` retains the speaker as an inset; `absent` is a full visual insert. Preserve narration continuity with a J- or L-cut only when it clarifies the spoken beat.

## Second-by-second plan

| Time | Story function | A-roll | B-roll function | Editable text | Frame |
|---|---|---|---|---|---|
| 0–1s | failure result | voice_over | concretize_abstraction | THIS FAILED | `frames/SF-020-F01.svg` |
| 1–2s | first cause | voice_over | concretize_abstraction | FIRST CAUSE | `frames/SF-020-F02.svg` |
| 2–3s | chain reaction | voice_over | concretize_abstraction | THEN | `frames/SF-020-F03.svg` |
| 3–4s | control | voice_over | concretize_abstraction | CONTROL | `frames/SF-020-F04.svg` |
| 4–5s | return to speaker | return_cut | concretize_abstraction | BACK TO YOU | `frames/SF-020-F05.svg` |

## Production prompt

Create a vertical 9:16 5-second clean-room insert titled “One Bad Handoff.” Use one meaningful visual state per second. Hook mechanism: `consequence`. Viewer job: `verify_claim`. Visual grammar: `split_screen`. B-roll function: `concretize_abstraction`. Proof form: `constraint`. Keep all captions, labels, UI-like elements, and proof callouts as editable deterministic overlays. Maintain an 8% horizontal and 10% vertical planning inset, then verify the actual platform UI safe zone at production. Use only original or licensed footage and audio. Do not copy creator wording, source frames, layouts, music, gestures, identity, branded UI, or distinctive sequence. External image/video/audio provider execution remains NOT RUN.

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
