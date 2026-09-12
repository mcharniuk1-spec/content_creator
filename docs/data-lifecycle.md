# Data lifecycle: Hiker, cache, provenance, retention

Owner: hiker (SPEC §9). Ties together what audit `reports/audit/03-server-runtime-hiker.md`
called "gap list" items 2, 4 and 8 — no single place explained what's kept, for how long,
and why collection and the deep-dive can't be split into independently-retryable steps.

## 1. What is kept, where, for how long

| Data | Path | Kept how long | Why |
|---|---|---|---|
| Raw HikerAPI response body | `cache/<snapshot-date>/*.json` | No automatic expiry today. Grows ~110 MB/month at current volume (audit §1). | Lets `deep.py`/`roster.py` re-derive a signed CDN URL or re-read a row without paying again, as long as the file is still there. |
| Provenance sidecar | `cache/<snapshot-date>/*.meta.json`, one per response file | Same lifetime as its `.json` — deleted only if the response file is deleted (they are not currently auto-pruned together; delete both by hand if you ever clear `cache/`). | fetch timestamp, endpoint, params (no secrets), HTTP status, units, sha256 — see §3. |
| `reels` rows | `data/radar.db` | Forever (one row per code per snapshot; snapshots accumulate). | Source of truth for scoring, cards, delta. |
| `fetch_log` rows | `data/radar.db` | Forever. | Provenance back-pointer from a `reels` row to the exact API call that produced it — see §3. |
| Video (mp4) | `data/video/<code>.mp4` | **Deleted immediately** after frame extraction (`deep.py`, "видео не храним" per SPEC §4.4), unless a caller explicitly passes `keep_video=True` — no call site in this repo does. | Disk: keeping every downloaded reel would dwarf everything else kept. The video itself is never the artifact anyone reviews; the contact sheet and transcript are. |
| Frames (`data/frames/<code>/*.jpg`) + contact sheet | `data/frames/` | Until `prune.py` deletes them — 8 weeks after `deepdives.done_at`, **and only** if the code never became a card (`prune.py:19-20`). | The human-facing visual evidence for a deep-dived reel; kept only as long as it might still inform a card decision. |
| `deepdives` / `frames` (DB rows) / `transcripts` (text + timestamped segments) | `data/radar.db` | Forever — `prune.py` never touches these, only the JPGs on disk (`prune.py` docstring: "строки разбора, склейки и расшифровки остались — они весят копейки"). | Cheap, and the structured signal (topics, scores, what-was-said-when) stays usable for analysis long after the pixels are gone. |
| `spend` rows | `data/radar.db` | Forever. | Historical accounting — separate from `fetch_log`, which is per-call provenance; `spend` is per-run/per-task totals. |

## 2. Why collection and the deep-dive can't be split into separate, independently-retryable steps

HikerAPI's `clips`/`medias` response embeds a **signed CDN URL** for each reel's video file.
That signature expires in **hours**, not days (confirmed by `deep.py`'s standalone
`__main__` path doing a `curl -sI` liveness check before ever attempting a batch download,
and refusing to proceed with "ссылки на видео протухли: CDN отдаёт 403" if it fails —
`deep.py:226-233`). `deep.py._urls()` never calls HikerAPI again to refresh a URL; it only
re-scans already-cached `clips*.json` files.

Consequences, all deliberate:

- `run.py` always runs step 1 (collect) and step 3 (deep-dive) in the **same process, same
  invocation** — never as separately scheduled cron jobs. This has broken before: the
  module docstring for both `collect_snapshot.py` and `run.py` records the exact incident
  ("разбор пошёл через двое суток после сбора, и все сто ссылок... отдали 403").
- A reel whose download/transcription fails **within that run is not retried later** by
  simply re-running `deep.py` — the URL is gone by the time anyone notices. The only way
  back is a fresh collection (which re-pays for the account) or accepting the gap.
- This is also why `data/video/*.mp4` is never kept (§1): even if disk were free, keeping
  the *decoded* video doesn't help — what expires is the *link*, and by the time anyone
  would want to re-derive something from `cache/`, the video referenced by that cached URL
  is unreachable regardless of whether a local mp4 copy still exists from a prior run.
- **Structural limit, not yet solved**: because the raw video is never retained and the
  HikerAPI cache (§1) has no retention guarantee of its own, once (a) a signed URL expires
  (hours) and (b) the cache file that held it is cleared or ages out, a pruned reel's frames
  (§1, 8-week window) are **permanently unrecoverable** — there is no tier between "keep
  frames forever" and "delete frames and lose the ability to ever regenerate them." Flagged
  in the audit as a real but not urgent risk (nothing has hit the 8-week mark yet).

## 3. Provenance chain: fetch_log → reels.fetch_id → cache file + sidecar

Before this work, a `reels` row carried no pointer back to the API response it came from —
the only way to find it was `deep.py:_urls()`'s linear scan over every `cache/**/*clips*.json`
file by content, sorted by file mtime (still how URL resolution works; provenance is
additive, not a replacement). The chain now looks like this, end to end:

```
lib/hiker.call()                    →  writes <cache_dir>/<endpoint>_<hash>.json  (response body)
                                     →  writes <cache_dir>/<endpoint>_<hash>.json.meta.json (sidecar)
                                     →  lib.hiker.last_fetch_meta() exposes that sidecar's dict

collect_snapshot.run()              →  reads last_fetch_meta() right after each account's
                                        hiker.clips() call
                                     →  INSERT INTO fetch_log (fetch_id, provider='hiker',
                                        endpoint, params_json, fetched_at, http_status, units,
                                        price, cache_path, sha256, snapshot_id, run_id, note)
                                     →  every reels row upserted from that account's response
                                        gets reels.fetch_id = that fetch_log.fetch_id
```

To audit any `reels` row today: `SELECT fetch_id FROM reels WHERE code=?`, then
`SELECT * FROM fetch_log WHERE fetch_id=?` gives the exact endpoint, params (key never
included), HTTP status, units billed, price, and — via `cache_path` — the exact response
file and its `sha256` for byte-level verification. The sidecar (`<cache_path>.meta.json`)
carries the same fields redundantly next to the raw response, so the cache directory is
self-describing even without the DB.

**This is all guarded**, not a hard dependency: `fetch_log` (table) and `reels.fetch_id`
(column) are created by `engine/schema.py` (a different owner's migration). Until that
migration has run against a given `data/radar.db`, `collect_snapshot.py` checks
`_table_exists()`/`_column_exists()` first and silently skips the provenance writes — the
old pipeline (accounts → reels, no provenance) keeps working exactly as before. On a
freshly migrated DB (confirmed against the real `data/radar.db` in this repo, which already
has both), provenance is written on every collection run automatically.

Pre-existing cache files from before this feature have no `.meta.json` sidecar;
`lib.hiker.call()` handles that gracefully on a cache hit (`last_fetch_meta()` returns a
minimal `{"note": "no sidecar (pre-provenance cache)"}` marker instead of failing).

## 4. Provider roles (`engine/providers.py`)

`python3 -m engine.providers status` prints this table live, resolved from environment
(never from stored secret values — only presence/length ever reaches a log or the `detail`
column). Role meanings: **DEFAULT** = part of the production path SPEC §0.3 describes;
**OPTIONAL_PROVIDER** = never required, off unless explicitly configured; **FALLBACK** =
not currently used by any provider here.

| Provider | Kind | Role | Configured via | Notes |
|---|---|---|---|---|
| `hiker` | social_data | DEFAULT | `HIKER_KEY` | The only paid collection path. State mirrors `engine.hiker_config.check()`. |
| `local-faster-whisper` | transcription | DEFAULT | — (local) | CPU ASR, `small`/int8; no credentials. |
| `local-ffmpeg-scenes` | frames | DEFAULT | — (local) | ffmpeg via `imageio_ffmpeg`; scene detection + frame extraction. |
| `remotion` | render | DEFAULT | — (local) | Checked against real `node`/`npx` presence on `PATH` — not assumed. Chrome itself is still not separately verified (audit 01 §6.5). |
| `loore` | media | OPTIONAL_PROVIDER | `LOORE_KEY` + `LOORE_ENABLED=1` | Transcription/media fallback. **Never required** — DISABLED even with a key present unless explicitly opted into via `LOORE_ENABLED=1`, so dropping a key into `.env` can never silently switch on a paid path. |
| `supabase` | storage | OPTIONAL_PROVIDER | `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` | Not used by any script today; reserved for future card assets. |
| `cloudflare` | storage | OPTIONAL_PROVIDER | `CLOUDFLARE_API_TOKEN` + `CF_R2_BUCKET` | Same. |
| `openai` | image_gen | OPTIONAL_PROVIDER | `OPENAI_API_KEY` | Image generation for future card/storyboard assets. |
| `higgsfield` | video_gen | OPTIONAL_PROVIDER | `HIGGSFIELD_API_KEY` | Video/brand asset generation. |

`engine.providers.refresh(con)` writes this table's live state into the `providers` SQL
table (guarded the same way as `fetch_log` — no-op if the table doesn't exist yet). `cron.sh`
calls it on every run so the table never drifts from what the environment actually has.

## 5. How the server runs Hiker from git alone

The server (`/opt/radar`) runs on a plain `git pull` of this repo plus a `.venv/`. The only
thing not in git is `.env`, which supplies `HIKER_KEY` (and the Notion variables) to the
process environment — `lib.hiker._key()` reads `os.environ['HIKER_KEY']` first, then falls
back to parsing `.env` directly if the shell environment doesn't already carry it (both
paths are exercised depending on how the process was started; cron's near-empty environment
relies on the `.env`-file fallback since cron does not source `.env` itself). No key or
token is ever read from git — `.env` is gitignored, and `.env.example` (§ above) only ever
holds variable names.

Every real run's cron invocation starts with `python -m engine.hiker_config`, which prints
one line for `HIKER_KEY` (`CONFIGURED`/`NOT_CONFIGURED`/`FAILED`, never the value — only
length and source) and one line per configured Notion database (`OK`/`FAILED(<http
status>)` from a cheap `GET /v1/databases/<id>`, or `NOT_CONFIGURED` if the variable or the
token is missing). `cron.sh` aborts **only** if `HIKER_KEY` isn't configured — a broken
Notion link is logged and the run proceeds regardless, matching `run.py`'s existing
per-step Notion error handling (SystemExit caught, logged, never fatal).
