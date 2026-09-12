# 35. Architecture of Frame Generation

Frame generation in this engine means one thing today: `engine/storyboard_render.py`
turns each storyboard scene into a labelled 1080×1920 PNG with Pillow, drawing only from
`design/tokens/tokens.json` — never a hardcoded palette, never a stock photo, never
AI-generated imagery. There is no image model in the render path, and that is a
deliberate design decision, not a missing feature.

## Why templates, not AI images

Two rules make the choice explicit. First, `design/tokens/tokens.json` carries a
`banned` list — no centred text, no rounded corners, no shadows, no gradients — and
`storyboard_render.py` enforces it in every layout it draws. Second, and more
fundamental: text is never generated inside an image in this system. A generative image
model that burns a caption into pixels cannot be proofread, corrected, or re-timed the
way a Pillow-drawn caption band from `script_text` can; the template renderer keeps
every word an editable string until a human presenter actually says it on camera.
Combined with `engine/SPEC.md` §0.8 ("no paid API calls from any new module by default;
anything that costs money must print the estimate and require `--yes`"), a card can move
from hypothesis to a full, reviewable storyboard for zero dollars, with every visual
still a placeholder honestly labelled as one.

`render_card(card, out_dir='cards/frames')` writes one PNG per scene plus a contact
sheet at `cards/frames/<card_id>_sheet.png`, and mutates `card['storyboard']` in place:
each scene's `asset_status` becomes `'template'` and `asset_path` points at the
rendered file (`cards/README.md`). Four layouts exist, matching the same four values
the Remotion EDL contract accepts (`studio/remotion/contract.mjs`'s
`UNSUPPORTED_LAYOUT` check): `a_roll` (one placeholder presenter box + banner + caption
band), `split_screen` (a proof panel on top, presenter below, split at 58% — the
contract's default `split_ratio`), `demo` (a full-frame `[SCREEN: …]` placeholder), and
`motion_graphic` (a left-aligned statement card, no placeholder box; `storyboard_render`
additionally accepts the rendering-time-only alias `"text"`, which `cards_v2.validate()`
deliberately refuses in a saved card so nothing invalid ever reaches the EDL builder).

## How the analysis actually informs the frame

This is not cosmetic. `fa-v1` (`engine/prompts/frame-analysis.md`) produces, per code,
`first_frame_type`, `visual_sequence`, and share estimates for A-roll/B-roll/split/
screen states; `engine.features.build()` folds these into `video_features`'s visual
block. `reports/analysis/01-general-conclusions.md` §3 states the single most reliable
production instruction the corpus yields: a screen on camera is the only visual feature
that survives creator normalisation on two independent metrics, worth roughly half again
the forwarding rate. `engine/prompts/script-writer.md`'s hard rule 7 turns that finding
into an instruction — use a screen insert or split-screen proof within the first 10
seconds wherever the hypothesis has a screen to show — and the writer records which
`layout`/`frame_type` each scene gets accordingly. `storyboard_render.py` then renders
exactly that decision: a `demo` or `split_screen` layout appears because the semantic
layer upstream said a screen belongs there, not because the renderer chose it.

## `asset_status` semantics

`card_scenes.asset_status` has four defined values, and only one is produced by any
module in this repository today:

| Value | Meaning | Written by |
|---|---|---|
| `missing` | nothing rendered yet | default state before render |
| `template` | this module's Pillow placeholder | `engine.storyboard_render.render_card` (the only writer that exists) |
| `ready` | real owner footage or graphic bound in | intended for Phase 3, not produced by any code in this repo yet |
| `generated` | an AI-generated visual | not used anywhere in this codebase — no paid image/video generation is called from any owner's files |

## How a future provider would plug in

`engine/providers.py` defines a `Provider` registry (`kind`, `role` ∈
`DEFAULT|OPTIONAL_PROVIDER|FALLBACK`, `env_vars`, a `resolve()` reporting only
presence/length of a credential, never its value). Two rows already exist for this
future: `openai` (`kind='image_gen'`, `OPTIONAL_PROVIDER`, `OPENAI_API_KEY`) and
`higgsfield` (`kind='video_gen'`, `OPTIONAL_PROVIDER`, `HIGGSFIELD_API_KEY`) — both
`NOT_CONFIGURED` here, and both verified (`grep -rn` for their client imports) to have
zero call sites anywhere in the code. `config/provider-catalog.json`, ported verbatim from `origin/Latest`, extends
this into a real capability catalogue — models like `seedance2_5` and `veo3.1` with
their admitted durations, aspect ratios and a `runtime_adapter` string
(`m2_studio.providers.RunwayImageTransport`) that does not exist in this repository —
dated `2026-09-05`, `recheck_after` a week later, and `"execution_enabled": false` at the
top level. This is an escrow pattern, not a stub waiting to be finished: capabilities are
priced and catalogued in advance, but nothing calls them until a human flips
`execution_enabled` and a real credential lands in `.env`, at which point the existing
`providers.py` registry — not a new integration — is what would report the provider
`CONFIGURED` and let a future `render_card`-equivalent choose it over the Pillow
template.

## `FRAME_GENERATION_READY` and `VIDEO_GENERATION_READY` — one real, one not

Only one of these is an actual state this pipeline writes. `VIDEO_GENERATION_READY` is a
real `jobs.stage` value, opened by `engine.production.ingest_takes` once real MP4 takes
exist for a card (`engine/production.py:392`) — it belongs to Phase 3, supplied footage,
not to frame generation. `FRAME_GENERATION` is named in the same canonical stage list
(`engine/state.py:STAGES`) alongside `FRAME_PLAN`, but neither
`engine.storyboard_render` nor any other module ever opens a `job()` context around it —
verified by reading `storyboard_render.py` directly, which mutates the card and writes
files but never touches `engine.state`. So there is no `FRAME_GENERATION_READY` flag
anywhere in this schema; the only signal that a card's frames are done is
`card_scenes.asset_status = 'template'` on every scene, checked by eye or by querying
the table — a gap that matches the same under-instrumented pattern the render stages
show later in the pipeline (chapter 36).
