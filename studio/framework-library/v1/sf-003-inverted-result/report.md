# SF-003 — Inverted Result

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN / OWNER_REVIEW_PENDING`

## Purpose

Lead with the outcome before context This is a 6-second reusable hook/intro/B-roll insert, not a final video and not a performance claim.

## Signal provenance

- Export: `SIGEXP-SF-003`
- Sources: `SRC-WEB-001`
- Evidence: `EVID-WEB-001`
- Rights: `metadata_commentary_only` source abstraction; output frames are original local previsualization.

## Taxonomy

| Axis | Value |
|---|---|
| `hook_mechanism` | `visual_anomaly` |
| `viewer_job` | `learn_mechanism` |
| `broll_function` | `demonstrate_process` |
| `proof_form` | `paraphrased_source` |
| `visual_grammar` | `object_macro` |
| `pacing_profile` | `held_reveal` |
| `transition_family` | `graphic_reveal` |
| `a_roll_integration` | `voice_over_broll` |
| `sound_role` | `music_pulse` |
| `text_role` | `keyword_captions` |
| `cta_exit` | `save_reference` |
| `risk_class` | `source_dependent` |

## Talking-head integration

Follow each frame's `a_roll_state`. `full` and `return_cut` show the speaker; `voice_over` keeps narration while B-roll carries the image; `picture_in_picture` retains the speaker as an inset; `absent` is a full visual insert. Preserve narration continuity with a J- or L-cut only when it clarifies the spoken beat.

## Second-by-second plan

| Time | Story function | A-roll | B-roll function | Editable text | Frame |
|---|---|---|---|---|---|
| 0–1s | anomaly | voice_over | demonstrate_process | WAIT | `frames/SF-003-F01.svg` |
| 1–2s | name tension | voice_over | demonstrate_process | WHAT CHANGED? | `frames/SF-003-F02.svg` |
| 2–3s | orient | voice_over | demonstrate_process | THE CLUE | `frames/SF-003-F03.svg` |
| 3–4s | connect | voice_over | demonstrate_process | CONNECT IT | `frames/SF-003-F04.svg` |
| 4–5s | payoff | voice_over | demonstrate_process | NOW IT FITS | `frames/SF-003-F05.svg` |
| 5–6s | clean exit | return_cut | demonstrate_process | RETURN | `frames/SF-003-F06.svg` |

## Production prompt

Create a vertical 9:16 6-second clean-room insert titled “Inverted Result.” Use one meaningful visual state per second. Hook mechanism: `visual_anomaly`. Viewer job: `learn_mechanism`. Visual grammar: `object_macro`. B-roll function: `demonstrate_process`. Proof form: `paraphrased_source`. Keep all captions, labels, UI-like elements, and proof callouts as editable deterministic overlays. Maintain an 8% horizontal and 10% vertical planning inset, then verify the actual platform UI safe zone at production. Use only original or licensed footage and audio. Do not copy creator wording, source frames, layouts, music, gestures, identity, branded UI, or distinctive sequence. External image/video/audio provider execution remains NOT RUN.

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
