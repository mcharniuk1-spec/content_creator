# Production pipeline — operator runbook (Phase 3)

How to take an **APPROVED** card (`cards/<card_id>.json`, `status: APPROVED`) from
"owner footage exists on disk" to "a reviewed MP4 sitting in storage, traced end to
end." Owner: production (`engine/production.py`, `engine/storage.py`). See
`docs/M2RADAR_CONTENT_ENGINE_ARCHITECTURE.md` §12 for the contract this runbook
executes; this document is commands, not design.

Nothing in this pipeline spends money or touches the network by default. The only
paid/networked step possible anywhere here is an actual Supabase upload, and only once
`SUPABASE_URL`/`SUPABASE_SERVICE_KEY` are set — Supabase Storage billing is
usage-based (bytes stored + bandwidth), not per-call, so there is no meaningful
per-render cost to declare up front; check your Supabase project's own billing page if
you're unsure, per this repo's general spending rule (state a cost estimate before
running anything paid).

## 0. Before you start

A card must already be `APPROVED` (or at least `REVIEWED`) and have a previs EDL:

```sh
python3 -m engine.cards_v2 validate cards/<card_id>.json
python3 -m engine.storyboard_render cards/<card_id>.json   # if storyboard scenes have no asset_path yet
python3 -m engine.edl cards/<card_id>.json                 # writes cards/edl/<card_id>.json, PREVIS
```

If any of these fail, fix the card first — Phase 3 never repairs a card, it only binds
real footage into an already-valid one.

## 1. Drop MP4 takes

For every scene you shot, put the file under `cards/takes/<card_id>/` (any filename)
and describe it in a sidecar `cards/takes/<card_id>.json`:

```json
{
  "card_id": "C-2026-09-11-01",
  "takes": [
    {
      "card_id": "C-2026-09-11-01", "scene_id": "S00", "script_segment": "hook",
      "take": 1, "shot_type": "A_ROLL_CLOSE_UP", "roll": "A",
      "duration_s": null, "fps": null, "width": null, "height": null,
      "orientation": "portrait", "has_audio": null, "audio_quality": "clean",
      "subject": "Misha, presenter", "in_s": 0.0, "out_s": 4.0,
      "sync_notes": "clap at 0.0s, aligns with script beat hook",
      "quality_status": "OK", "retake_of": null, "sha256": null,
      "path": "cards/takes/C-2026-09-11-01/S00-take1.mp4"
    }
  ]
}
```

Leave `duration_s, fps, width, height, has_audio, sha256` as `null` — the next step
fills them in from the real file. Everything else you fill in by hand at shoot time:
`scene_id` must match a `storyboard[].scene_id` already in the card, `orientation`
must be `"portrait"` (every card is a 9:16 reel — anything else is a hard error, not
just a note), and `quality_status` starts `"PENDING"` until someone actually reviews
the take (`"OK"` to make it selectable, `"RETAKE"` to reject it and point the next
attempt's `retake_of` back at this `take` number).

Full field-by-field contract: `schemas/supplied-take.schema.json`.

## 2. Validate + probe

```sh
python3 -m engine.production takes <card_id>
```

Reads the sidecar, probes every file that actually exists (duration/fps/resolution/
audio via ffprobe or an ffmpeg-stderr fallback — no new dependency, no network),
validates every take against the card's storyboard, and writes
`cards/takes/<card_id>.validated.json`. Prints one JSON summary and always records a
`jobs` row (`entity_kind='card', stage='VIDEO_GENERATION_READY'`):

| You'll see | Meaning | What to do |
|---|---|---|
| `"state": "FAILED"`, reason `card not found` | `cards/<card_id>.json` doesn't exist | Finish the card first (§0). |
| `"state": "PENDING"`, reason `no takes sidecar` | You haven't written `cards/takes/<card_id>.json` yet | Do step 1. |
| `"state": "PENDING"`, reason `no MP4 files exist on disk` | Sidecar exists but every `path` is empty/missing | Drop the actual files, re-run. |
| `"state": "DONE"` | At least one take was probed and validated | Open `cards/takes/<card_id>.validated.json`, check `summary` and each take's `_errors` — a per-take error (wrong `scene_id`, `out_s` past the probed duration, non-portrait orientation, …) does not fail the whole run; fix that one take and re-run. |

Re-running is always safe — `ingest_takes` re-reads the sidecar and re-probes every
file every time; nothing is cached across runs.

## 3. Pick the take for each scene

`select_takes()` is a library call, not its own CLI — used internally by the next
step, but you can preview the selection any time:

```sh
python3 -c "
import json
from engine import production
validated = json.load(open('cards/takes/<card_id>.validated.json'))
for scene_id, take in production.select_takes(validated).items():
    print(scene_id, '<-', 'take', take['take'], take['path'])
"
```

A scene missing from this output has no `quality_status: OK`, error-free take yet —
its storyboard slot stays a placeholder in the render until one exists. Mark a bad
take's `quality_status` as `"RETAKE"` in the sidecar, add the redo with `retake_of`
pointing at it, and re-run step 2.

## 4. Bind the takes into the EDL

```sh
python3 -c "
import json
from engine import production
card = json.load(open('cards/<card_id>.json'))
edl = json.load(open('cards/edl/<card_id>.json'))
validated = json.load(open('cards/takes/<card_id>.validated.json'))
selection = production.select_takes(validated)
result = production.edl_with_takes(card, edl, selection)
print('wrote', result['path'])
print('node validation:', result['node'])
"
```

This overwrites `cards/edl/<card_id>.json` with the same EDL, except every scene with
a selected take now carries a real `video` layer (hash-verified, `rights_approved:
true`) instead of a `placeholder`; every other scene is untouched. Raises `ValueError`
— and writes nothing — if a selected take hasn't actually been probed yet, or is too
short (after trimming to `in_s`) to fill its storyboard slot; fix the take (or its
`in_s`/`out_s`) and re-run this step. `result['node']` is `{'ok': True, ...}` when
`node` is on PATH and the EDL still validates against `studio/remotion/contract.mjs`;
`{'skipped': True, 'reason': '...'}` only means Node wasn't found — treat that as "not
yet checked," never as a pass.

## 5. Build (and, when ready, run) the render

```sh
python3 -m engine.production plan <card_id>            # prints the exact command, runs nothing
python3 -m engine.production plan <card_id> --execute   # actually renders, if configured
```

`plan` without `--execute` is always safe to run — it never touches the filesystem
beyond reading the EDL and never starts a subprocess. States:

- **`NOT_CONFIGURED`** — one or more of: no EDL yet (do step 4 first), Remotion's
  `node_modules` not installed (`install_command` in the output tells you the exact
  fix: `cd studio/remotion && npm ci --ignore-scripts --no-audit --no-fund`), no
  Chrome/Chromium binary found (set `M2_CHROME_PATH` to an existing install — this
  tool never downloads a browser), or `node` missing from `PATH`.
- **`READY`** — everything needed exists; the printed `command` is exactly what
  `--execute` would run.
- **`EXECUTED`** — the render actually ran and exited 0; `receipt` is `render.mjs`'s
  own JSON receipt (`status: "RENDERED_REVIEW_REQUIRED"` — a render is *never* a
  publish-ready artifact by itself, see `studio/remotion/README.md`).
- **`FAILED`** — the subprocess exited non-zero, or the output file already existed
  (delete or rename it and re-run — `render.mjs` refuses to overwrite an output on
  purpose).

The render lands at `data/renders/review/<card_id>.mp4` by default. There is no
`cron.sh` step for this yet (see the architecture doc §7/§16) — every Phase 3 run is
operator-initiated today.

### Manual state trace (optional but recommended)

Nothing here opens a `jobs` row for the render itself (§5 of the architecture doc
explains why: a render can run for minutes, and whether to trace it as one job is an
operator call, not this module's). If you want a row in the trace for it:

```python
from engine.db_util import connect
from engine.state import job, start_run
con = connect()
run_id = start_run(con, 'manual')
with job(con, run_id, 'card', '<card_id>', 'VIDEO_RENDER', provider='remotion') as j:
    ...  # run the plan['command'] yourself, or call render_plan(..., execute=True) here
```

## 6. QA and store

QA is a human step (watch the review MP4 against the approved storyboard/script — this
tool does not auto-approve anything). Once you've decided `qa_status`:

```python
import hashlib, json
from engine.db_util import connect, now
from engine.storage import LocalStorage, SupabaseStorage, record_render

con = connect()
review_mp4 = 'data/renders/review/<card_id>.mp4'

# pick a provider — Supabase is canonical once configured, Local otherwise
storage = SupabaseStorage()   # or: LocalStorage()
object_key = storage.put(review_mp4, key='<card_id>/v1.mp4')

record = {
    'run_id': '<the run_id from step 5, or a fresh one>', 'card_id': '<card_id>',
    'script_version': 2, 'storyboard_version': 1, 'render_version': 1,
    'source_take_ids': ['S00#1', 'S01#2'],           # from select_takes()'s picks
    'final_object_key': object_key, 'thumbnail_key': None,
    'duration_s': 6.0,
    'render_metadata': {
        'fps': 30, 'width': 1080, 'height': 1920, 'codec': 'h264',
        'remotion_version': '4.0.520',
        'edl_sha256': hashlib.sha256(open('cards/edl/<card_id>.json', 'rb').read()).hexdigest(),
    },
    'qa_status': 'OK',   # or 'FAILED' — never invent a pass
    'storage_provider': 'supabase',   # or 'local'
    'created_at': now(),
}
path = record_render(con, record)
print('recorded', path)
```

`record_render` writes `data/renders/<run_id>-<card_id>.json` and upserts a row into
the guarded `render_records` table (created automatically on first use). Full field
contract: `schemas/render-record.schema.json`.

If Supabase isn't configured yet, `SupabaseStorage().put(...)` raises
`StorageNotConfigured` naming exactly which env var is missing — use `LocalStorage()`
until you set `SUPABASE_URL`/`SUPABASE_SERVICE_KEY` in `.env`. Check any provider's
state without touching a file:

```sh
python3 -m engine.storage status
```

## 7. Update trace and Notion

`record_render` already wrote the trace-adjacent `render_records` row and JSON file.
This owner's modules do not push to Notion — that is `engine.notion_sync`'s job
(`docs/NOTION_DASHBOARD.md`). Run its `--dry` plan to see the card's row before
deciding whether/when to `--apply` (a decision for whoever owns that module + Misha,
not automated here):

```sh
python3 -m engine.notion_sync --dry --scope cards
```

## 8. Publish

Out of scope for this entire pipeline, on purpose. Publishing is always a separate,
explicit, human action, per this repo's own rules — nothing in `engine/production.py`
or `engine/storage.py` posts anywhere.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `probe_media` raises `PROBE_FAILED` | Corrupt/truncated MP4, or an exotic container ffmpeg's stderr format doesn't match the fallback regex | Open the file in a player first; if it plays fine, this is a real gap in the stderr fallback — file it, don't hand-edit the validated JSON. |
| `validate_take` flags `orientation must be 'portrait'` | You shot landscape, or an orientation-correcting rotation metadata flag confused your camera app | Re-export/crop to portrait before dropping the file here — this pipeline does not auto-rotate. |
| `edl_with_takes` raises `too short for its storyboard slot` | Your `in_s`/`out_s` trim leaves less footage than the scene's duration | Either shoot more, or shorten the storyboard scene (back in `engine.cards_v2`, another owner's module) and rebuild the previs EDL. |
| `render_plan` stuck at `NOT_CONFIGURED: node_modules missing` | Nobody has run `npm ci` in `studio/remotion` yet | `cd studio/remotion && npm ci --ignore-scripts --no-audit --no-fund` (verify `package-lock.json` first — never edit it by hand). |
| `render_plan` stuck at `NOT_CONFIGURED: no Chrome/Chromium binary found` | No local Chrome install, or it's in a non-standard location | Set `M2_CHROME_PATH=/path/to/Chrome`; never let this tool download a browser. |
| `SupabaseStorage` raises `StorageNotConfigured` | `SUPABASE_URL`/`SUPABASE_SERVICE_KEY` not in `.env` | Add them (`.env.example` already lists both keys, empty); until then use `LocalStorage`. |

## Open item for whoever owns `.env.example` (hiker owner, per `engine/SPEC.md` §9)

`CloudflareDelivery.public_url()` reads `CF_PUBLIC_BASE_URL`, which is not yet in
`.env.example` (only `CLOUDFLARE_API_TOKEN`/`CF_R2_BUCKET` are). The code degrades
correctly without it (`NOT_CONFIGURED`), so this is not blocking — but add a commented,
empty `CF_PUBLIC_BASE_URL=` line next to the other Cloudflare vars when convenient.

## Verification record (2026-09-12)

A real PREVIS render of the example card was executed on the work Mac after `npm ci` in
`studio/remotion/` (179 packages, `tsc --noEmit` clean):

```
node studio/remotion/render.mjs --edl cards/edl/C-2026-09-11-EX.json --assets . \
  --output <scratch>/render-ex.mp4 --browser "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
```

Result: 1800 frames @ 30 fps (60 s), 1080×1920 H.264, 3.4 MB, receipt
`reports/evidence/remotion-previs-receipt-C-2026-09-11-EX.json` (EDL and output hashes), a
mid-render frame at `reports/evidence/remotion-previs-frame-12s.jpg`. The MP4 itself is not
committed. Remotion warns that macOS 14 is older than its supported macOS 15; the render
nevertheless completed. `render_plan()` reports `NOT_CONFIGURED` on a machine without
`studio/remotion/node_modules` — run `npm ci` there first.
