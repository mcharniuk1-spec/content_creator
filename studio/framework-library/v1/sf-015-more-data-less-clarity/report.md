# SF-015 — More Data, Less Clarity

Truth state: `ORIGINAL_LOCAL_PREVISUALIZATION / EXTERNAL_PROVIDER_NOT_RUN / OWNER_REVIEW_PENDING`

## Purpose

Contrast volume with decision quality This is a 6-second reusable hook/intro/B-roll insert, not a final video and not a performance claim.

## Signal provenance

- Export: `SIGEXP-SF-015`
- Sources: `SRC-WEB-002`
- Evidence: `EVID-WEB-002`
- Rights: `metadata_commentary_only` source abstraction; output frames are original local previsualization.

## Taxonomy

| Axis | Value |
|---|---|
| `hook_mechanism` | `contradiction` |
| `viewer_job` | `verify_claim` |
| `broll_function` | `establish_context` |
| `proof_form` | `paraphrased_source` |
| `visual_grammar` | `diagram_build` |
| `pacing_profile` | `rapid_beat` |
| `transition_family` | `cut_on_sound` |
| `a_roll_integration` | `voice_over_broll` |
| `sound_role` | `silence_drop` |
| `text_role` | `step_counter` |
| `cta_exit` | `answer_question` |
| `risk_class` | `source_dependent` |

## Talking-head integration

Follow each frame's `a_roll_state`. `full` and `return_cut` show the speaker; `voice_over` keeps narration while B-roll carries the image; `picture_in_picture` retains the speaker as an inset; `absent` is a full visual insert. Preserve narration continuity with a J- or L-cut only when it clarifies the spoken beat.

## Second-by-second plan

| Time | Story function | A-roll | B-roll function | Editable text | Frame |
|---|---|---|---|---|---|
| 0–1s | contradiction | voice_over | establish_context | THE OPPOSITE | `frames/SF-015-F01.svg` |
| 1–2s | expected model | voice_over | establish_context | YOU EXPECT | `frames/SF-015-F02.svg` |
| 2–3s | break | voice_over | establish_context | BUT | `frames/SF-015-F03.svg` |
| 3–4s | explanation | voice_over | establish_context | HERE'S WHY | `frames/SF-015-F04.svg` |
| 4–5s | bounded rule | voice_over | establish_context | THE RULE | `frames/SF-015-F05.svg` |
| 5–6s | reframe | return_cut | establish_context | REFRAME | `frames/SF-015-F06.svg` |

## Production prompt

Create a vertical 9:16 6-second clean-room insert titled “More Data, Less Clarity.” Use one meaningful visual state per second. Hook mechanism: `contradiction`. Viewer job: `verify_claim`. Visual grammar: `diagram_build`. B-roll function: `establish_context`. Proof form: `paraphrased_source`. Keep all captions, labels, UI-like elements, and proof callouts as editable deterministic overlays. Maintain an 8% horizontal and 10% vertical planning inset, then verify the actual platform UI safe zone at production. Use only original or licensed footage and audio. Do not copy creator wording, source frames, layouts, music, gestures, identity, branded UI, or distinctive sequence. External image/video/audio provider execution remains NOT RUN.

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
