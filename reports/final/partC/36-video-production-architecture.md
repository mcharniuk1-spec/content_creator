# 36. Video Production Architecture

Everything from an approved card to a reviewed MP4 runs through two modules,
`engine/production.py` and `engine/storage.py`, on top of one file format: the Remotion
EDL. `engine/edl.py`'s `card_to_edl()` turns a validated card into an
`m2.remotion-edl.v1` document at `cards/edl/<card_id>.json`, and `studio/remotion/
contract.mjs` is the single source of truth for its validity — both the Python builder
and the Node renderer call into behavior that file defines.

## PREVIS vs PRODUCTION

An EDL's `render_mode` is either `PREVIS` or `PRODUCTION`. `card_to_edl()` always writes
`PREVIS`: every scene carries a `placeholder` layer standing in for real A-roll, an
`image` layer for the rendered template PNG (`rights_approved: true`,
`rights_receipt_id: "internal-template"`), and `pending_audio_assets: ["speech"]` — this
module never invents a speech asset. `PRODUCTION` mode is gated by `contract.mjs` behind
`review_state='APPROVED'` and no pending audio or placeholder layers remaining; nothing
in this branch produces a `PRODUCTION`-mode EDL yet. Phase 3's
`engine.production.edl_with_takes()` moves a scene from placeholder to real: for every
scene with a selected take it swaps in a real `video` layer (verified sha256, timing
from the probed file), leaves every other scene untouched, and re-validates the whole
document through `contract.mjs` again.

## The verified PREVIS render

This is not a theoretical contract — it was run. `docs/PRODUCTION_PIPELINE.md` records a
real render of the example card (`C-2026-09-11-EX`) on 2026-09-12, after `npm ci`
(179 packages, `tsc --noEmit` clean):

```
node studio/remotion/render.mjs --edl cards/edl/C-2026-09-11-EX.json --assets . \
  --output <scratch>/render-ex.mp4 --browser "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
```

Result: 1,800 frames at 30fps (60s), 1080×1920 H.264, 3.4 MB. The receipt,
`reports/evidence/remotion-previs-receipt-C-2026-09-11-EX.json`, carries
`"status": "RENDERED_REVIEW_REQUIRED"`, `"render_mode": "PREVIS"`,
`"remotion_version": "4.0.520"`, an EDL sha256
(`bfd8aa9a159981bb4fa3eebaf560b3fdb24910273b70e17c643a7d3a58ab0510`), an output sha256
(`0716c154c1d4b076a22b4475d9ad623726e9315e67b51ada1b9b22d93b72245f`), and per-asset
hashes for all seven storyboard images — a mid-render frame is saved at
`reports/evidence/remotion-previs-frame-12s.jpg`. The MP4 itself was not committed. This
confirms what `reports/audit/01-branch-comparison.md` §7 had listed as explicitly
unverified a day earlier — "whether Remotion actually renders" — and closes that gap
with a real artefact.

## The supplied-MP4 take contract

`schemas/supplied-take.schema.json` defines one take: `card_id, scene_id,
script_segment, take, shot_type, roll (A|B), duration_s, fps, width, height,
orientation, has_audio, audio_quality, subject, in_s, out_s, sync_notes, quality_status
(PENDING|OK|RETAKE), retake_of, sha256, path`. Six fields (`duration_s, fps, width,
height, has_audio, sha256`) stay `null` until `probe_media(path)` reads the real file —
via `ffprobe` if present (verified absent here: `imageio_ffmpeg`'s bundled binaries hold
only ffmpeg, not ffprobe) or a regex fallback over `ffmpeg -i`'s stderr. Everything else
is filled in by hand at shoot time. `orientation` must be `"portrait"` — every M2Radar
card is a 9:16 reel, so anything else is a hard validation error, never a warning.

## Take selection and `edl_with_takes`

`engine.production.ingest_takes(con, card_id)` reads `cards/takes/<card_id>.json`,
probes every file that exists on disk, validates each take against the card's
storyboard, and writes `cards/takes/<card_id>.validated.json`. It always records exactly
one `jobs` row (`entity_kind='card', stage='VIDEO_GENERATION_READY'`) and never claims
success it did not observe — a missing card is `SKIPPED`/`FAILED`; no sidecar or zero
real files on disk is `SKIPPED`/`PENDING`; at least one real, validated take is
`DONE`/`DONE`. `select_takes()` then picks, per scene, the take marked `quality_status:
"OK"` with no validation errors and the highest take number — a scene with no such take
is simply absent, so its EDL slot stays a placeholder rather than being guessed at.

## Render plan and QA

`engine.production.render_plan(card_id)` builds the exact
`node studio/remotion/render.mjs --edl … --assets … --output … --browser …` command
(read from `render.mjs` itself, never guessed) and returns four states:
`NOT_CONFIGURED` (no EDL yet, `node_modules` missing, no Chrome/Chromium binary, or
`node` missing from `PATH`), `READY` (command built, nothing run), `EXECUTED`
(subprocess exited 0, receipt attached), `FAILED` (non-zero exit, or the output path
already exists — `render.mjs` refuses to overwrite on purpose). QA is explicitly a human
step: nothing in `engine/production.py` auto-approves a render; `docs/PRODUCTION_
PIPELINE.md` §6 has the operator record `qa_status: 'OK'` (or `'FAILED'`, "never invent
a pass") by hand before `record_render()` is called.

## Storage: Supabase canonical, Cloudflare delivery-only

`engine/storage.py` is a fresh implementation — `git grep` across this repo and
`origin/Latest` for Supabase/Cloudflare/R2 code turns up only documentation and false
positives (a regression variable named `r2`, a test fixture reel named `"R2"`),
confirmed by reading each hit. `LocalStorage` copies into `data/renders/objects/` and is
always configured; `SupabaseStorage` does `POST {SUPABASE_URL}/storage/v1/object/
{bucket}/{key}` behind an injectable `transport()` so no test makes a real HTTP call,
and raises `StorageNotConfigured` naming the exact missing variable when
`SUPABASE_URL`/`SUPABASE_SERVICE_KEY` are absent — true here, verified.
`CloudflareDelivery` implements no upload path at all by design: its only justified role
is turning an already-Supabase-stored key into a public preview URL from
`CF_PUBLIC_BASE_URL`, a variable `.env.example` does not yet define. `record_render()`
writes `data/renders/<run_id>-<card_id>.json` and upserts into a guarded
`render_records` table this module creates itself, the same "create your own table"
pattern `local_pipeline.py` uses.

## What is not implemented or verified

No owner footage exists yet anywhere in this repository — every take example above is
illustrative. Supabase and Cloudflare are both `NOT_CONFIGURED` (no credentials in this
checkout's `.env`), so every real render today can only land in `LocalStorage`. There is
no `cron.sh` step for Phase 3: `engine.production` and
`engine.storage` are operator-run, confirmed by reading `cron.sh`, which stops at the
watchdog and features stages. `VIDEO_RENDER` and `QUALITY_REVIEW` are named in
the canonical `jobs.stage` list but no module opens a job around either — a render is
traced only if the operator manually wraps the render command in an `engine.state.job()`
context (`docs/PRODUCTION_PIPELINE.md` §5). None of this is hidden: every gap above is
named in `docs/M2RADAR_CONTENT_ENGINE_ARCHITECTURE.md` §16, not smoothed over as
"coming soon."
