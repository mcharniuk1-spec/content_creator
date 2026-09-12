# Cards v2 — structure, validation, storyboard render, Remotion EDL

Owner modules: `engine/cards_v2.py`, `engine/storyboard_render.py`, `engine/edl.py`.
Binding spec: `engine/SPEC.md` §8 (card JSON), §2.9 (DB tables), §9 (ownership).
Content policy for what may go into `strategy`/`script`/`claims` is `POSITIONING.md` and
`RULES.md`, not this file — this file only covers the data/render mechanics.

## What a card is

One JSON document, `cards/<card_id>.json`, schema `m2radar.card.v2` (see
`tests/fixtures/card-example.json` for a complete, valid, fictional example — its
`title` starts with `EXAMPLE —` on purpose, never remove that marker if you copy it).

Top-level shape (SPEC §8):

```
schema, card_id, hypothesis_id, format, title,
strategy   { concept, audience, objective, positioning, pain, promise, rationale,
             filter { process, friction, ai_boundary, next_action } }   <- the 4 mandatory fields
references [ { code, username, url, function, reason,
               play, creator_median_play, view_lift, share_rate, save_rate,
               useful_transcript, useful_frame, transformed_how } ]
hooks      [ { text, type, is_question } ]                              <- need >= 2
script     { version, sections [ {role, text, words, seconds} ], total_words, total_s,
             target_wps, tone, emotional_effect }
storyboard [ { scene_id, idx, start_s, end_s, script_text, script_role, frame_type,
               layout, visual, overlay_text, transition, source_inspiration,
               asset_status, asset_path, editing, cta_type? } ]
editing    { cut_timing, captions, emphasis, zooms, motion, assets_required }
claims     [ { text, state, source } ]                                  <- state is closed vocab
traceability { insights, hypothesis, evidence_summary, original_synthesis, why_better_than_generic }
review     { version, findings, revised }
remotion_edl_path, status
```

## Closed vocabularies (SPEC §4), enforced by `validate()`

- `storyboard[].frame_type` — the 21-value taxonomy (`A_ROLL_CLOSE_UP`, `SPLIT_SCREEN`, …).
- `hooks[].type` — the 13-value hook taxonomy (`bold_claim`, `question`, …).
- `storyboard[].cta_type` / `card.cta_type` (optional, checked only if present) — the
  9-value CTA taxonomy (`comment_keyword`, `follow`, `none`, …).
- `storyboard[].layout` — exactly `a_roll | split_screen | demo | motion_graphic`. This is
  the **same 4-value set the Remotion EDL contract (`studio/remotion/contract.mjs`,
  `UNSUPPORTED_LAYOUT`) accepts** — `engine/storyboard_render.py` additionally accepts the
  alias `"text"` (rendered identically to `motion_graphic`) purely as a rendering-time
  convenience; `validate()` deliberately does **not** accept `"text"` in a saved card, so a
  card that passes validation always has a layout the EDL can carry unchanged.
- `claims[].state` — `OBSERVED | PLANNED | TO_MEASURE | MISSING`.

## What `validate(card) -> list[str]` checks

Returns a flat list of messages. A message starting with `WARNING: ` is advisory and never
fails the card; use `is_valid(errors)` (or filter the prefix yourself) to get pass/fail.
Checked, beyond the vocabularies above:

- every SPEC §8 key is present; the four `strategy.filter` fields are non-empty strings;
- `references[]` is non-empty and every entry has `code/url/function/reason` plus all five
  performance numbers (`play, creator_median_play, view_lift, share_rate, save_rate`);
- `hooks[]` has >= 2 entries, each with non-empty `text`, a closed-vocab `type`, and a
  boolean `is_question`;
- `storyboard[]` scenes are contiguous: `idx` is exactly `0..N-1`, each scene's `start_s`
  follows the previous scene's `end_s` within 0.05s, and the last scene's `end_s` matches
  `script.total_s` within 0.5s;
- every `script.sections[].role` has at least one `storyboard[].script_role` scene covering it;
- `claims[]` each carry a closed-vocab `state`;
- `script.total_s` is a hard error outside **20–120s** and a `WARNING: ` outside the
  **50–70s** sweet spot from `PRODUCTION.md` ("winners' median is 55s against 47 for the rest").

## CLI

```sh
python3 -m engine.cards_v2 validate cards/C-2026-09-11-01.json
python3 -m engine.cards_v2 save cards/C-2026-09-11-01.json      # validates, then persists
python3 -m engine.cards_v2 list                                 # summary table of all saved cards
```

`save(con, card, json_dir='cards')` refuses (raises `ValueError`) a card with any hard
error. On success it:

1. writes `cards/<card_id>.json` (pretty-printed, sorted keys);
2. upserts one row in `cards_v2` (preserves the original `created_at` across re-saves);
3. replaces all `card_scenes` rows for that `card_id` from the current `storyboard[]`
   (safe to re-run: old scenes for the card are deleted first, so a shrunk storyboard
   never leaves orphaned rows);
4. appends to `script_versions`: a `writer` row at `script.version`, and — only when
   `review.revised` is `true` — a `reviewer` row at `script.version + 1` carrying
   `review.findings`. Both rows reference the same `script_json`, because the card model
   only keeps the final script text, not the pre-review draft; this is a deliberate
   simplification, not a bug — if a future card format needs the actual pre-review draft,
   add a `script.previous` field and thread it through here.

All of this is idempotent: saving the same card twice changes only `updated_at` (and
never inserts a second `script_versions` row for a version already recorded, by design —
that table is an append-only log, not a mutable one).

`load_all(con)` returns every `cards_v2` row with its JSON columns decoded and its
`card_scenes` attached as `scenes`. `summary_table(con)` prints/returns
`card_id / title / format / total_s / words / status / refs / scenes`.

## Storyboard render — what "template" asset status means

`engine/storyboard_render.py` renders each storyboard scene to a 1080x1920 PNG with
Pillow, using **only** `design/tokens/tokens.json` for colour, type and safe zones (never
a hardcoded palette, never a stock photo, never AI-generated imagery). Every frame is an
explicit, visibly-a-placeholder frame — a dashed-border box with a `[SHOT: presenter,
close-up]` / `[SCREEN: dashboard]` label — plus the scene's `overlay_text` on an ink
banner plate, a burned-in caption band from `script_text`, and a small mono metadata
footer (`card_id`, scene idx, time range, `frame_type`, transition). Layouts:

- `a_roll` — one placeholder box (presenter) + banner + caption band.
- `split_screen` — top proof-panel placeholder labelled from `visual`, bottom presenter
  placeholder, split at 58% (matching the Remotion contract's default `split_ratio`).
- `demo` — a full-frame `[SCREEN: …]` placeholder labelled from `visual`.
- `motion_graphic` (alias `text`) — no placeholder box; a large left-aligned statement
  card (never centred — `tokens.json`'s `banned.text-align-center` is enforced everywhere
  in this module, along with no rounded corners, no shadows, no gradients).

```sh
python3 -m engine.storyboard_render cards/C-2026-09-11-01.json
```

`render_card(card, out_dir='cards/frames') -> list[str]` writes one PNG per scene, a
contact sheet at `cards/frames/<card_id>_sheet.png`, and — **mutates `card['storyboard']`
in place** — sets each scene's `asset_status='template'` and `asset_path=<relative path>`.
`asset_status='template'` means exactly what it says: this is a placeholder frame
standing in for real footage, never mistake it for a shoot-ready or generated asset.
The four statuses in `card_scenes.asset_status` are `missing` (nothing rendered yet),
`template` (this module's placeholder render), `ready` (real owner footage/graphic bound
in, not yet used in this codebase), `generated` (AI-generated visual, not used by this
codebase — no paid image/video generation is called anywhere in this owner's files).

## From template to owner footage (Phase 3)

Once a card is shot, each `card_scenes` row's `template` PNG is replaced by real footage
tracked in a sidecar, **not** by editing the template PNG in place. The intended sidecar,
`cards/takes/<card_id>.json`, is not built yet (out of this owner's scope, see
`engine/SPEC.md` §8·2 "Phase 3 MP4 contract fields"); its shape should be one entry per
take:

```json
{
  "card_id": "C-2026-09-11-01",
  "takes": [
    {"scene_id": "S01", "take": 1, "shot_type": "A_ROLL_CLOSE_UP", "roll": "A",
     "duration_s": 4.2, "fps": 30, "resolution": "1080x1920", "orientation": "portrait",
     "audio": "camera_mic", "in_s": 0.0, "out_s": 4.2,
     "sync_notes": "clap at 0.0s, aligns with script beat 'hook'",
     "quality": "usable", "retake": false}
  ]
}
```

Once a take is marked `quality: usable, retake: false`, the corresponding `card_scenes`
row's `asset_status` moves to `ready` and `asset_path` points at the real clip/frame; the
EDL (`engine/edl.py`) then replaces that scene's `placeholder` layer with a real `video`
asset (hash-verified, `rights_approved`) and the `image` layer stays only if a rendered
graphic overlay is still wanted on top.

## From a card to a Remotion EDL

`engine/edl.py`'s `card_to_edl(card, fps=30, width=1080, height=1920) -> dict` builds an
`m2.remotion-edl.v1` document (`studio/remotion/contract.mjs`, `src/types.ts`) and writes
it to `cards/edl/<card_id>.json`. It requires every storyboard scene to already carry an
`asset_path` to an existing PNG — i.e. run `storyboard_render.render_card(card)` first.

- `render_mode: "PREVIS"`, `review_state` mirrors `card.status`.
- `duration_frames = round(script.total_s * fps)`; each scene's `duration_frames` is
  computed by a cumulative-boundary rounding partition so the parts always sum exactly
  (no drift, no `EDL_COVERAGE_INCOMPLETE`/`EDL_PARTITION_INVALID` from the contract).
- Every scene carries a `placeholder` layer (stands in for real A-roll footage — `bottom`
  panel for `split_screen`, `full` otherwise), an `image` layer for the rendered template
  frame (`rights_approved: true`, `rights_receipt_id: "internal-template"`, `sha256` of
  the actual PNG on disk), and a `text` layer when `overlay_text` is non-empty.
- `captions[]` come from `storyboard[].script_text`, partitioned the same way.
- `audio_stems: []`, `pending_audio_assets: ["speech"]`,
  `speech_policy: "REQUIRED_RECORDED_SPEECH"` — this module never invents a speech asset;
  the contract's `production: true` mode (not used here) is what enforces that a real,
  aligned speech stem must exist before anything renders for real.

```sh
python3 -m engine.edl cards/C-2026-09-11-01.json    # build + validate via node in one step
```

`validate_with_node(path)` runs `contract.mjs`'s `validateEDL` through Node (`import()`
of the `.mjs` file by absolute `file://` URL, so it works regardless of the caller's
working directory) and returns `{'ok', 'skipped', 'stdout', 'stderr'}`. `skipped=True`
only means Node (or `contract.mjs`) was not found — callers must not treat that as a
pass. With Node present and a valid EDL it prints `EDL_OK`.

## Worked example

```sh
python3 -m pytest tests/test_cards_v2.py -q
python3 -m engine.storyboard_render tests/fixtures/card-example.json   # do this on a COPY, see note below
python3 -m engine.edl tests/fixtures/card-example.json
```

Note: both CLIs rewrite their input file in place with the render/EDL side effects
(`asset_status`/`asset_path`, `remotion_edl_path`), so run them on a copy if you want to
keep `tests/fixtures/card-example.json` pristine — the test suite already does this
in-memory and additionally renders the example once for real into `cards/frames/` and
`cards/edl/` as a live demonstration (see `tests/test_cards_v2.py`).
