# SF-021 — Stale Metric

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN / OWNER_REVIEW_PENDING`

## Purpose

Make freshness failure concrete This is a 6-second reusable hook/intro/B-roll insert, not a final video and not a performance claim.

## Signal provenance

- Export: `SIGEXP-SF-021`
- Sources: `SRC-WEB-004`
- Evidence: `EVID-WEB-005`
- Rights: `metadata_commentary_only` source abstraction; output frames are original local previsualization.

## Taxonomy

| Axis | Value |
|---|---|
| `hook_mechanism` | `consequence` |
| `viewer_job` | `imagine_outcome` |
| `broll_function` | `demonstrate_process` |
| `proof_form` | `worked_example` |
| `visual_grammar` | `object_macro` |
| `pacing_profile` | `measured_beat` |
| `transition_family` | `hard_cut` |
| `a_roll_integration` | `absent` |
| `sound_role` | `music_pulse` |
| `text_role` | `proof_callout` |
| `cta_exit` | `comment_prompt` |
| `risk_class` | `low` |

## Talking-head integration

Follow each frame's `a_roll_state`. `full` and `return_cut` show the speaker; `voice_over` keeps narration while B-roll carries the image; `picture_in_picture` retains the speaker as an inset; `absent` is a full visual insert. Preserve narration continuity with a J- or L-cut only when it clarifies the spoken beat.

## Second-by-second plan

| Time | Story function | A-roll | B-roll function | Editable text | Frame |
|---|---|---|---|---|---|
| 0–1s | failure result | absent | demonstrate_process | THIS FAILED | `frames/SF-021-F01.svg` |
| 1–2s | first cause | absent | demonstrate_process | FIRST CAUSE | `frames/SF-021-F02.svg` |
| 2–3s | chain reaction | absent | demonstrate_process | THEN | `frames/SF-021-F03.svg` |
| 3–4s | human impact | absent | demonstrate_process | IMPACT | `frames/SF-021-F04.svg` |
| 4–5s | control | absent | demonstrate_process | CONTROL | `frames/SF-021-F05.svg` |
| 5–6s | return to speaker | absent | demonstrate_process | BACK TO YOU | `frames/SF-021-F06.svg` |

## Production prompt

Create a vertical 9:16 6-second clean-room insert titled “Stale Metric.” Use one meaningful visual state per second. Hook mechanism: `consequence`. Viewer job: `imagine_outcome`. Visual grammar: `object_macro`. B-roll function: `demonstrate_process`. Proof form: `worked_example`. Keep all captions, labels, UI-like elements, and proof callouts as editable deterministic overlays. Maintain an 8% horizontal and 10% vertical planning inset, then verify the actual platform UI safe zone at production. Use only original or licensed footage and audio. Do not copy creator wording, source frames, layouts, music, gestures, identity, branded UI, or distinctive sequence. External image/video/audio provider execution remains NOT RUN.

## Analysis notes

- FACT: every visual change is explicitly timecoded and has an A-roll/B-roll function.
- INTERPRETATION: the one-second cadence is a review scaffold; production may hold or subdivide a beat only after the story function remains legible.
- HYPOTHESIS: this framework may help orient attention for its declared viewer job; it does not guarantee retention or reach.
- GAP: no owned performance test, platform-specific UI-safe-zone check, final footage, audio, or owner approval exists.

## Acceptance

- All 6 intervals are contiguous and cover 0–6000 ms.
- The hook is visible during 0–1000 ms.
- Text stays editable and within the planning safe zone.
- Source lineage and rights IDs remain attached.
- Final video, provider generation, Figma, publishing, and deployment remain `NOT_RUN`.
