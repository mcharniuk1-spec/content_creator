# M2Radar Content Engine — Architecture

Authoritative reference for the whole engine, written by the production-layer owner
(engine/SPEC.md §9) on 2026-09-12, against the `content-engine` branch as it exists
today. Every module, table and number below was checked against the code or a real
command run in this session — not recalled from the spec alone. Where the spec and the
code disagree, both are stated and the disagreement is named as such.

Binding documents this file sits beside, never duplicates: `engine/SPEC.md` (the
canonical schema/ownership contract), `engine/HANDOFF_NOTES.md` (open cross-owner
decisions), `reports/audit/01-branch-comparison.md` (why `main` is canonical and what
was ported from `origin/Latest`), `docs/data-lifecycle.md` (Hiker/cache/provenance),
`docs/NOTION_DASHBOARD.md` (the Notion projection), `cards/README.md` and
`studio/remotion/README.md` (card → EDL → render mechanics),
`M2Radar_Content_Engine_Full_Execution_Prompt_v4.md` (the full execution brief this
branch implements).

---

## 1. Purpose

M2Radar is a research-to-production pipeline for M2 Lab's English-language Instagram
account about AI workflows (`~/Desktop/how-i-work` project "M2 Lab"; positioning and
audience decisions live in that project's own memory, not here). It turns a weekly
Instagram collection into: a normalized SQLite corpus of reels and creators; a local,
free, per-video analysis (transcript, frames, scenes, semantic beats, visual labels);
statistics that compare a reel to its own author's history; numeric insights and
ranked content hypotheses; original shooting cards (script + storyboard) that
*transform* what worked elsewhere rather than copy it; and, once a card is shot, a
deterministic Remotion render of the approved edit. Nothing here posts, spends money,
or claims a result it has not measured — every stage that could plausibly be mistaken
for "done" instead records an explicit state (`PENDING`, `NOT_CONFIGURED`, `SKIPPED`,
`FAILED`) with a reason.

## 2. North-star flow

```
Hiker (paid, weekly)                    engine/SPEC.md §0.3
  -> reels/accounts snapshot (db.py, 14 tables)
  -> local faster-whisper transcript (engine/local_pipeline.py)
  -> local ffmpeg scene/frame extraction (engine/scenes.py)
  -> transcript <-> scene alignment (engine/align.py)
  -> per-video LLM analysis: ta-v1 transcript beats, fa-v1 frame labels
     (engine/prompts/*, engine/ingest_analysis.py)
  -> consolidated video_features row (engine/features.py, engine/lexical.py)
  -> creator/video statistics, robust z, creator-relative lift (engine/stats.py)
  -> numeric insights -> ranked hypotheses (engine/ingest_insights.py + data files)
  -> hypothesis-specific reference selection (function-tagged: hook/pain/proof/...)
  -> transformed original script + frame-aware storyboard -> card JSON
     (engine/cards_v2.py, cards/<card_id>.json)
  -> template storyboard frames (engine/storyboard_render.py) -> previs EDL
     (engine/edl.py, studio/remotion/contract.mjs)
  -> [Phase 3, this owner] supplied MP4 takes -> validated -> bound into the EDL
     (engine/production.py) -> Remotion render (studio/remotion/render.mjs)
     -> stored (engine/storage.py: Supabase canonical, local fallback)
  -> Notion projection (engine/notion_sync.py) -> Misha reviews and decides
  -> publish (always a separate, explicit, human action — never automated here)
```

Everything up to "card JSON" runs for free (no paid API beyond the weekly Hiker
collection); everything from "supplied MP4 takes" onward is Phase 3, this document's
main subject.

## 3. Module map

### `engine/` (the versioned engine; SPEC.md §9 names the owner of each file)

| Module | Role |
|---|---|
| `SPEC.md` | Canonical schema/ownership contract for every module below. |
| `HANDOFF_NOTES.md` | Cross-owner decisions and open requests, one section per owner. |
| `schema.py` | Versioned, idempotent migration that creates every table in §5 below. |
| `state.py` | Run/job tracing (`start_run`, `job`) and `video_state` recomputation (`refresh_video_state`). See §6. |
| `db_util.py` | Shared connection (`connect()` = `db.connect()` + FK pragma), `canonical_json`, `now()`, `new_id`, `git_commit()`, `table_exists`/`columns`. |
| `migrate_legacy.py` | One-off, re-runnable migration of the legacy 14-table corpus into the new engine tables (`video_state`, `providers`, column adds). |
| `hiker_config.py` | Checks `HIKER_KEY`/Notion env config; printed by `cron.sh` before every run. |
| `providers.py` | Provider registry (`PROVIDERS` list) — resolves each provider's state from env only, never logs a secret value. See §7. |
| `local_pipeline.py` | Phase 1/2 per-video contract: download → transcribe → scene/frame-extract → refresh state. `engine/SPEC.md` §6. See §8. |
| `scenes.py` | ffmpeg scene-cut detection (`detect_cuts`) and frame extraction (`extract_frames`, contact sheets). |
| `align.py` | Transcript segment ↔ scene overlap by time; writes `beats.scene_ids_json` or a flags-only map. |
| `watchdog.py` | Phase 2 catch-up worker: replays already-cached Hiker URLs, never calls Hiker again. See §11. |
| `process_budget.py` | Ported from `origin/Latest`: bounded subprocess capture, minimal env, process-group cleanup for ASR/ffmpeg calls. |
| `ingest_analysis.py` | Loads `data/analysis/{transcripts,frames}/<code>.json` (ta-v1/fa-v1) into `beats`/`frame_labels`/`scenes`, refreshes `video_state`. |
| `lexical.py` | Phrase/word-class/timing features from a transcript (V4 §63) — pure text, no LLM call. |
| `features.py` | Consolidates transcript + frame + stats signal into one `video_features` row per code (V4 §17C). See §9. |
| `stats.py` | `creator_stats`, `video_perf` (robust z, creator-relative lift), `temporal`, `associations`, `report` (V4 §18-21A). |
| `corpus.py` | `tiers(con)` — the **evidence** corpus split (own definition, deliberately different from `video_state.corpus_tier`, see §4.4). |
| `ingest_insights.py` | Loads `data/analysis/{insights,hypotheses}.json` into `insights`/`hypotheses`/`hypothesis_refs`. |
| `cards_v2.py` | Validates/persists `cards/<card_id>.json` against the SPEC §8 shape + §4 closed vocabularies; mirrors into `cards_v2`/`card_scenes`/`script_versions`. |
| `storyboard_render.py` | Renders each storyboard scene to a labelled placeholder PNG (Pillow, `design/tokens/tokens.json` only — never a stock photo). |
| `edl.py` | `card_to_edl()` — card JSON → `m2.remotion-edl.v1` PREVIS document; `validate_with_node()` runs `contract.mjs`'s `validateEDL` via Node. |
| `production.py` | **This owner.** Phase 3: probe/validate/ingest supplied MP4 takes, bind them into the EDL, build the render command. See §12. |
| `storage.py` | **This owner.** Storage providers for rendered video (Supabase canonical, local fallback) + Cloudflare public-delivery stub. See §12. |
| `notion_blocks.py` | Pure Notion block-JSON builders (heading/table/toggle/…), no network. |
| `notion_sync.py` | `--dry`/`--apply` Notion dashboard sync (SPEC §85-91). `--apply` is CLI-refused by design; see `docs/NOTION_DASHBOARD.md`. |
| `charts.py` | Analytical PNG charts for the report (V4 §42) from a synthetic or real corpus. |
| `report_data.py` | Report-ready data bundles feeding the analytical PDF and the Notion dashboard. |
| `pdf_build.py` | Python entry point for `tools/pdf/md2pdf.mjs`, the dependency-free Markdown → PDF renderer used for the analytical report and card PDFs. |
| `prompts/transcript-analysis.md`, `prompts/frame-analysis.md` | The ta-v1/fa-v1 LLM prompt templates (§5's analysis JSON contracts). |

### `lib/`, root scripts (main's pre-existing pipeline, unchanged in shape per SPEC §0.6)

| Module | Role |
|---|---|
| `lib/hiker.py` | Caching HikerAPI client; writes the response body + a provenance sidecar per call (`docs/data-lifecycle.md` §3). |
| `db.py` | The legacy SQLite schema (14 tables, `SCHEMA` + `ADDED` guarded column list) and `connect()`. |
| `collect_snapshot.py` | Weekly collection → a `snapshots` row + `reels` rows, now writing `fetch_log` provenance when the engine tables exist. |
| `roster.py` | Account roster maintenance: liveness check, culling, backfill. |
| `harvest.py`, `freeprofile.py` | Free (non-Hiker) account discovery/enrichment, rate-limit aware. |
| `deep.py` | Legacy deep-dive: frames, contact sheet, transcript, all local, video deleted after (`docs/data-lifecycle.md` §1). |
| `score.py`, `baseline.py` | Per-reel score against the author's own history; age-banded, focal-row-excluded baseline (kept canonical over `origin/Latest`'s weaker version — `reports/audit/01-branch-comparison.md` §5.1). |
| `topics.py`, `tag_topics.py`, `tag_candidates.py`, `judge_accounts.py` | Topic vocabulary and manual/LLM-assisted labelling of reels and candidate accounts. |
| `analyze.py`, `blocks.py`, `delta.py`, `review.py` | Legacy per-run signal extraction, hook/body/close segmentation, week-over-week delta, plan-vs-result review. |
| `cards.py` | Legacy (v1) card candidate selection — superseded for new work by `engine/cards_v2.py`, kept for the existing 10 reviewed cards in Notion. |
| `pages.py`, `journal.py`, `posts.py` | The three weekly Notion report pages, tool-run journal, and our own posted-content tracking. |
| `notion.py`, `notion_db.py` | Legacy Notion card push and the two operational Reels/Accounts databases (kept separate from the new engine databases — `docs/NOTION_DASHBOARD.md`). |
| `prune.py` | Deletes frame JPGs (not DB rows) 8 weeks after a deep-dive, unless the code became a card. |
| `check.py` | Database invariant checks (not a diff against a prior state). |
| `run.py` | The weekly run, in order; still the only entry point `cron.sh` calls for Phase 1. |
| `stats.py` (root) | Legacy report tables pushed to the Notion homepage — distinct from `engine/stats.py`. |

### `studio/`, `schemas/`, `config/`, `prompts/`

| Path | Role |
|---|---|
| `studio/remotion/contract.mjs` | The single source of truth for EDL validity (`validateEDL`) and the speech-alignment hash — both Python (`engine/edl.py`) and Node call into behavior this file defines. |
| `studio/remotion/render.mjs` | Renders one EDL to an MP4 via `@remotion/bundler`/`@remotion/renderer`, given an explicit `--browser` binary; writes a `.receipt.json` alongside the output. |
| `studio/remotion/storyboards.mjs` | Batch-renders previs storyboards from a directory of unbound EDLs. |
| `studio/remotion/src/` | The React/Remotion composition itself (layouts, captions, typography). |
| `schemas/video-scene-segmentation.schema.json` | Ported from `origin/Latest`: the scene/frame contract this branch's `scenes`/`frame_labels` tables implement a simplified version of. |
| `schemas/m2-corpus-field-dictionary.v1.json` | Field dictionary for the existing Notion operational databases. |
| `schemas/supplied-take.schema.json` | **This owner.** The Phase 3 MP4 shot contract (§12.1). |
| `schemas/render-record.schema.json` | **This owner.** The rendered-artifact record contract (§12.4). |
| `config/provider-catalog.json` | Ported from `origin/Latest`: external video/image-generation provider capabilities — dated, `execution_enabled: false`, not wired to any call site in this repo. |
| `prompts/angles.md` | Editorial angles / claim-map rules merged from `origin/Latest`'s `skills/m2-script-writer`. |

## 4. Data model

### 4.1 Legacy tables (`db.py`, 14 tables, verified by counting `CREATE TABLE` statements directly — SPEC.md §0.1 and the audit both say "15"; this document could not find a fifteenth table in `db.py` and flags the discrepancy rather than repeating the unverified number)

`accounts, snapshots, reels, scores, topics, deepdives, frames, transcripts, our_posts,
our_metrics, followers, cards, tool_log, spend`. Untouched in shape; `db.ADDED` guards
a handful of columns added over time (`scores.baseline_n`, etc.) via idempotent
`ALTER TABLE`.

### 4.2 Engine tables (`engine/schema.py`, additive, versioned via `schema_migrations`)

State tracing: `runs`, `jobs` (indexed on `entity_kind, entity_id, stage`), `video_state`
(one row per code, the processing contract — full column list in `engine/state.py`'s
`VIDEO_STATE_COLUMNS`).

Analysis: `transcript_meta`, `beats` (semantic chapters, one row per beat), `scenes`
(real scene-v1 intervals or legacy `fixed9-v1`/`aug2026` samples), `frame_labels` (one
row per code+idx), `video_features` (one row per code — the §17C consolidated object).

Statistics: `creator_stats` (one row per creator per snapshot).

Content generation: `insights`, `hypotheses`, `hypothesis_refs`, `cards_v2`,
`card_scenes`, `script_versions`.

Provenance/registry: `providers`, `fetch_log`.

**Phase 3 (this owner, `engine/storage.py`):** `render_records` — not in
`engine/schema.py`'s list (SPEC §9 assigns table ownership per file; this table's
columns are the render-record schema, §12.4). Created by `engine/storage.py`'s own
guarded `CREATE TABLE IF NOT EXISTS`, the same pattern `engine/local_pipeline.py` uses
for its own tables before `engine.schema` exists — this module does not assume
`engine.schema.migrate` has been extended to include it, and never needs to.

Guarded `ALTER TABLE` additions to legacy tables: `reels.fetch_id`, `frames.sha256`,
`frames.exists_ok`, `deepdives.evidence_state`, `cards.status_v2`.

### 4.3 `video_state` (the processing contract, one row per code)

Every column is *derived*, never hand-set: `engine.state.compute_video_state()` is a
pure function of `reels`/`transcripts`/`frames`/`scenes`/`beats`/`frame_labels`/
`video_features`/`deepdives`, and `refresh_video_state`/`refresh_all_video_states`
simply write its output. Columns: `media_state` (`UNKNOWN|AVAILABLE|EXPIRED|MISSING|
DOWNLOADED`), `transcript_state` (`MISSING|PENDING|DONE|EMPTY_NO_SPEECH|FAILED`),
`frames_state` (`MISSING|PENDING|DONE_FIXED9|DONE_SCENE|FAILED|PARTIAL`),
`alignment_state` (`MISSING|DONE|NOT_POSSIBLE`), `transcript_analysis_state`,
`frame_analysis_state`, `features_state` (all `MISSING|DONE`, currently — no
`PENDING`/`FAILED` path is written by any module today), `analysis_ready` (1 only when
transcript DONE + frames DONE_* + **both** semantic analyses DONE), `corpus_tier`
(`ANALYSIS_READY|FRAMES_ONLY|INGESTED_NOT_ANALYZED`), and `flags_json` (a sorted list
from `MISSING_STATS, MISSING_MEDIA, MISSING_TRANSCRIPT, MISSING_FRAMES,
BROKEN_FRAME_REFERENCE, UNALIGNED_TRANSCRIPT, DUPLICATE_VIDEO, STALE_METRICS,
UNRESOLVED_CREATOR_ID`).

### 4.4 Corpus tiers and the two vocabularies (`engine/HANDOFF_NOTES.md`'s features-owner section, unresolved as of this writing)

There are **two different, deliberately unmerged** definitions of "corpus tier" in this
branch, and every report must say which one it used:

| | `video_state.corpus_tier` (processing state) | `engine.corpus.tiers()` (evidence tier) |
|---|---|---|
| Meaning | What still needs doing | What a report may divide by |
| ANALYSIS_READY | usable transcript AND frames (does *not* require both LLM analyses — `video_state.analysis_ready` is the stricter flag for that) | same, reproduces the audit exactly |
| FRAMES_ONLY | frames AND `transcript_state != DONE` → **29** codes | frames AND **no `transcripts` row at all** → **22** codes |
| Empty-transcript codes | folded into FRAMES_ONLY (7 codes: frames + a `transcripts` row with `words=0`) | its own tier, `TRANSCRIPT_UNUSABLE` (7) |
| Verified against | live `data/radar.db` (drifting, see below) | `data/server-mirror/radar.db`, the audit's frozen mirror: **273 analysis-ready / 266 (features-owner's stricter reading) / 22 frames-only / 1313 ingested-not-analyzed / 411 total with any signal** |

The live `data/radar.db` has already drifted from the audit mirror by the time of
writing (`engine/HANDOFF_NOTES.md`'s features-owner section: 3217 codes vs 3211, 274
analysis-ready vs 266, six codes with transcript+frames but no `video_state` row at
all pending a `refresh_video_state` pass). **Any number quoted from this corpus must
name its source query and its tier**, never a bare count.

## 5. State tracing

`runs` (one row per pipeline execution — `kind` ∈ `weekly|watchdog|analysis|cards|
manual`) → `jobs` (one row per processing step, `entity_kind` ∈ `video|creator|corpus|
hypothesis|card`, `state` ∈ `PENDING|RUNNING|DONE|FAILED|RETRY_REQUIRED|SKIPPED`) →
`video_state` (the always-current summary, recomputed, never hand-written).

Canonical `jobs.stage` list (`engine/state.py:STAGES`, 25 stages, in pipeline order):

```
DISCOVERED, PROFILE_FETCHED, VIDEO_METADATA_FETCHED, STATS_FETCHED, MEDIA_FETCHED,
TRANSCRIPTION, TRANSCRIPT_ANALYSIS, FRAME_EXTRACTION, FRAME_ANALYSIS, ALIGNMENT,
GENERAL_ANALYSIS, STATISTICAL_ANALYSIS, CATEGORIZATION, REFERENCE_SELECTION,
CONCEPT_GENERATION, CARD_GENERATION, SCRIPT_GENERATION, SCRIPT_REVIEW, FRAME_PLAN,
FRAME_GENERATION, VIDEO_GENERATION_READY, VIDEO_RENDER, QUALITY_REVIEW, NOTION_SYNC,
COMPLETED
```

Phase 3 (this owner) writes `VIDEO_GENERATION_READY` (`engine.production.ingest_takes`,
one row per card per attempt). `VIDEO_RENDER` and `QUALITY_REVIEW` are named in the
canonical list but **no module in this branch writes them yet** — `render_plan()`
builds and can execute the render command but does not itself open a `job()` context
around the render (a render can run for minutes and the caller, not this module,
decides whether to trace it as one job or as an operator-supervised step; see
`docs/PRODUCTION_PIPELINE.md` §5 for the recommended manual trace command).

`job()`'s contract (verified by reading `engine/state.py`): it always writes `RUNNING`
on entry; on a clean return it closes `DONE` unless the step called `handle.skip(reason)`
(→ `SKIPPED`) or `handle.retry_required(reason)` (→ `RETRY_REQUIRED`); on any exception
it closes `FAILED` with the exception text and re-raises. **There is no
`handle.pending()`** — nothing in `engine/state.py` can close a job row as literally
`PENDING`. `engine.production.ingest_takes` maps "nothing to do yet" (no sidecar, or a
sidecar with zero real MP4 files on disk) to `handle.skip(reason)` — an accurate
`SKIPPED` job row — while its own return value's `state` field says `PENDING` in the
business sense ("come back once footage exists"). This is a deliberate, documented
mapping (see the module docstring), not an inconsistency.

Example end-to-end trace query, for one code:

```sql
SELECT stage, state, started_at, finished_at, duration_s, error
FROM jobs WHERE entity_kind='video' AND entity_id='<code>' ORDER BY started_at;

SELECT transcript_state, frames_state, alignment_state, analysis_ready, corpus_tier, flags_json
FROM video_state WHERE code='<code>';
```

For a card in Phase 3:

```sql
SELECT stage, state, started_at, error FROM jobs
WHERE entity_kind='card' AND entity_id='<card_id>' ORDER BY started_at;
```

## 6. Providers table and roles

`engine/providers.py`'s `PROVIDERS` list, state resolved from environment only
(`Provider.resolve_state` never returns a secret value, only presence/length):

| Provider | Kind | Role | Configured via | Default state on this machine |
|---|---|---|---|---|
| `hiker` | social_data | DEFAULT | `HIKER_KEY` | per `engine.hiker_config.check()` |
| `local-faster-whisper` | transcription | DEFAULT | — | CONFIGURED (local) |
| `local-ffmpeg-scenes` | frames | DEFAULT | — | CONFIGURED (local) |
| `remotion` | render | DEFAULT | — | CONFIGURED if `node`/`npx` on PATH (Chrome itself not separately verified) |
| `loore` | media | OPTIONAL_PROVIDER | `LOORE_KEY` + `LOORE_ENABLED=1` | DISABLED even with a key present, until explicitly opted in |
| `supabase` | storage | OPTIONAL_PROVIDER | `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` | NOT_CONFIGURED (verified: neither var set in this checkout's `.env`) |
| `cloudflare` | storage | OPTIONAL_PROVIDER | `CLOUDFLARE_API_TOKEN` + `CF_R2_BUCKET` | NOT_CONFIGURED |
| `openai` | image_gen | OPTIONAL_PROVIDER | `OPENAI_API_KEY` | NOT_CONFIGURED |
| `higgsfield` | video_gen | OPTIONAL_PROVIDER | `HIGGSFIELD_API_KEY` | NOT_CONFIGURED |

DEFAULT = part of the production path (SPEC §0.3); OPTIONAL_PROVIDER = never required,
off unless explicitly configured; no provider in this table is FALLBACK today. No paid
API is called anywhere in this branch by default — verified: `hiker` is the only paid
call site (`lib/hiker.py`), `loore` is DISABLED by construction even with a key present,
and `openai`/`higgsfield` have no call site in this repo at all (checked with
`grep -rn` for their client imports — none found).

`engine.storage.status()` (this owner) prints the same shape for the two Phase 3
providers plus `local`:

```
$ python3 -m engine.storage status
local       CONFIGURED      <repo>/data/renders/objects
supabase    NOT_CONFIGURED  Supabase storage not configured: missing SUPABASE_URL, SUPABASE_SERVICE_KEY (set them in .env — see .env.example)
cloudflare  NOT_CONFIGURED  CF_PUBLIC_BASE_URL not set; no public delivery role configured
```

(Exact output of a real run in this session, reproduced verbatim — not paraphrased.)

## 7. Server execution model

`cron.sh` runs on a plain `git pull` + `.venv/` at `/opt/radar` (`docs/data-lifecycle.md`
§5). Verified sequence, reading `cron.sh` directly:

1. `python -m engine.hiker_config` — prints `HIKER_KEY`/Notion state; aborts the whole
   run **only** if `HIKER_KEY` is not configured.
2. `python -m engine.providers refresh` — best-effort, `|| true` (never blocks).
3. `python run.py` (unchanged main entry point — collection + legacy deep-dive + the
   original 13 steps; `cron.sh` line calling this has not moved, per the audit's
   explicit warning against ever doing so).
4. `timeout 3600 python -m engine.watchdog --limit 40 --yes || echo "watchdog failed"`
   — Phase 2, guarded so a watchdog failure never blocks step 5 or the run's exit
   code.
5. `timeout 1800 python -m engine.features --refresh || echo "features failed"` —
   same guard.

Every new stage added after the original 13 steps is wrapped so its failure is logged
and never blocks the older chain — this document did not find a `cron.sh` step for
Phase 3 (`engine.production`/`engine.storage`) yet: **Phase 3 is operator-run today**,
not scheduled. `docs/PRODUCTION_PIPELINE.md` gives the exact manual commands; adding a
guarded cron step for it (e.g. "ingest any new takes sitting under `cards/takes/`") is
a reasonable next step but was not in this owner's file list and is not done here.

Incremental processing: `local_pipeline.process_video` skips a code already `DONE` for
the same `asr_version`/`frames_version` unless `--force`; `watchdog` selects only codes
where `analysis_ready=0` and a still-live cached URL exists, so a run only ever touches
what changed. Version-aware reprocessing: bumping `DEFAULT_ASR_VERSION` or
`DEFAULT_FRAMES_VERSION` in `engine/local_pipeline.py` makes every code eligible again
under the new version, without touching old rows.

## 8. Video-by-video contract and the new-video input contract

### 8.1 Local processing contract (SPEC §17B / §6, `engine/local_pipeline.py`)

`process_video(con, code, media_url_or_path, run_id, *, asr_version, frames_version)`:
skip if already done for the same versions → download (curl, 3 tries, sha256 recorded)
→ faster-whisper `small`/int8 transcription (`vad_filter=True`) → ffmpeg scene-cut
detection (`select='gt(scene,0.30)'`) + keyframe extraction → `align.py` (segment/beat
↔ scene overlap) → delete the mp4 unless `--keep-video` (no call site passes it) →
`refresh_video_state`. Every step is one `jobs` row; the whole function retries up to 3
times and is idempotent.

### 8.2 New-video input contract (V4 §81 — required/nullable fields per stage)

| Stage | Required/nullable fields |
|---|---|
| Social/reference reel input | platform, creator ID, reel/video ID, source URL, Hiker payload reference, views/likes/comments/shares/saves, metric timestamp, media availability, ingestion run ID — carried by `reels` + `fetch_log` (this repo has no non-Instagram platform yet, so "platform" is implicit/constant, not a column). |
| Local processing input | media file/object reference, transcription model/version, frame extraction version, scene-detection config, processing run ID, retry state — carried by `video_state` (`media_path`, `asr_version`, `frames_version`) + `jobs.retries`. |
| Analysis input | transcript ID, segment IDs, scene IDs, frame IDs, creator baseline version, feature schema version, analysis prompt version, model/version — carried by `beats.segment_idx_json`/`scene_ids_json`, `frame_labels`, `video_features.features_version`, `transcript_meta.asr_version`. |
| Generated content input | hypothesis ID, selected reference IDs, positioning, audience, script version, storyboard version, target duration, aspect ratio — carried by `cards_v2`/`card_scenes`/`script_versions` and the card JSON's `traceability`/`strategy` blocks. |

Incomplete records fail clearly or stay in an explicit pending state throughout — this
is the same discipline `engine.production.ingest_takes` applies to Phase 3's own input
contract (§12.1).

## 9. Analysis layer

### 9.1 ta-v1 / fa-v1 contracts

`data/analysis/transcripts/<code>.json` (ta-v1, SPEC §5): `beats[]` (role from the SPEC
§4 vocabulary, timing, text, `audience_function`/`emotion`/`intention`/`persuasion`),
`semantics` (topic/pain/solution_type/proof_type/hook_type/narrative/funnel_role/
positioning_type — all closed vocabularies), `interpretation`, `quality` (1-5 scores),
`confidence`. `data/analysis/frames/<code>.json` (fa-v1): per-frame labels
(`frame_type`, `roll`, presence flags, `caption_placement`, `framing`) plus video-level
aggregates (`visual_sequence`, share estimates, `sync_notes`, `limitations`).
`engine.ingest_analysis.run()` loads both into `beats`/`frame_labels`/`scenes` and
refreshes `video_state`; three beat-role vocabulary leaks (`thesis`, `demo_first` used
as a role instead of a hook_type) are logged, not silently coerced, in
`data/analysis/ingest_warnings.md` (per `engine/HANDOFF_NOTES.md`'s features-owner
section).

### 9.2 Lexical / stats / features split

`engine.lexical.features()` — phrase/word-class/timing signal from text alone (no
LLM): tokenization, sentence rhythm, n-grams, per-10-seconds rates. `engine.stats.py` —
`creator_stats` (median/MAD/IQR/CV, `posts_per_week`, `reliability`), `video_perf`
(rates with a `play>=100` denominator guard, `view_lift`, `robust_z`, `percentile_in_
creator`), `temporal` (delta/rolling-median/slope per creator), `associations`
(Spearman + creator-clustered bootstrap CI, small-cell suppression). `engine.features.
build()` — the §17C **consolidation**: `semantics_block` (from ta-v1), `script_block`
(from ta-v1 + `engine.lexical`), `visual_block` (from fa-v1 + `scenes`), plus the
performance columns `engine.stats.video_perf` already computed — written once per code
into `video_features`.

### 9.3 The eight analytical roles (V4 §12) mapped to where each actually lives

V4 §12 names eight *conceptual* sub-agent roles for script analysis and explicitly
allows folding them into "modular analysis stages" instead of literal agents — this
branch takes that option. Verified mapping (by reading each module, not assumed from
the letter names):

| Role | Where it lives |
|---|---|
| A. Transcript Structural Analyst | `engine/prompts/transcript-analysis.md` (ta-v1 `beats[]`) + `engine/align.py` |
| B. Marketing/Persuasion Analyst | ta-v1 `semantics` block (`pain`, `desire`, `proof_type`, `cta_type`, `positioning_type`) |
| C. Performance Analyst | `engine/stats.py` (`video_perf`, `robust_z`, `view_lift`, creator-relative lift) |
| D. Hook Specialist | ta-v1 `semantics.hook_type`/`hook_text` + `engine.lexical`'s hook-segment word/second counts + fa-v1 `hook_visual` |
| E. Narrative Analyst | ta-v1 `semantics.narrative` + `beats[].role` ordering |
| F. Audience/Positioning Analyst | ta-v1 `semantics.audience`/`audience_stage`/`positioning_type`/`funnel_role` |
| G. Script Reviewer | `engine/cards_v2.py`'s `script_versions` `reviewer` row + the card JSON's `review{}` block (V4 §28) |
| H. Synthesis Agent | `engine.features.build()` — the one place all of the above are consolidated into a single `video_features` row |

## 10. Insight → hypothesis → reference → script → review → storyboard → card

`insights` (numeric claim + evidence + confidence `RELIABLE|PROBABLE|INSUFFICIENT`) →
`hypotheses` (title, audience/pain/hook/mechanism/proof/cta, `status` `PROPOSED|
SELECTED|REJECTED`, `total_score`) → `hypothesis_refs` (function-tagged: hook/pain/
explanation/proof/cta/a_roll/b_roll/split/screen_proof/rhythm/transition — V4 §76's
"reference selection must be function-specific") → the card's `script` (versioned,
`script_versions` keeps writer + reviewer rows) → `storyboard` (frame-aware, one scene
per beat-aligned segment) → `cards_v2`/`card_scenes` (the persisted, validated form).
`engine.ingest_insights` loads the JSON files; `engine.cards_v2.save()` refuses to
persist a card with a hard validation error (missing vocabulary value, non-contiguous
storyboard, `total_s` outside 20-120s). This whole chain is the free part of the
pipeline — no paid generation happens before a card reaches `APPROVED`.

## 11. Phase 2 — post-merge watchdog

`engine/watchdog.py` selects codes where `analysis_ready=0` and a signed CDN URL is
still findable in an already-cached `cache/**/*clips*.json` file (never calls Hiker
again — `docs/data-lifecycle.md` §2 explains why the signed-URL window makes that the
only safe source). Guarantees verified by reading the module: idempotent (`process_
video`'s own version-aware skip), retryable (3 tries per step), observable (one `jobs`
row per step), rate-limited (`RATE_SLEEP_S` between codes), safe against duplicate
workers (`data/watchdog.lock`, pid+timestamp, stale after 3h), version-aware (bumping
`asr_version`/`frames_version` reopens eligibility). This matches V4 §92's watchdog
selection query and 11-step list exactly (media validation → transcript → segmentation
→ keyframes → scene detection → alignment → semantic transcript analysis → visual
analysis → statistical normalization → category update → analysis-ready) except that
today's `engine.watchdog` calls `local_pipeline.process_video` (steps 1-6) and
`cron.sh` separately calls `engine.features --refresh` (steps 9-11); steps 7-8
(semantic transcript/visual analysis, i.e. ta-v1/fa-v1 generation) are **not** invoked
by any scheduled step in this branch — they are produced by a separate, currently
manual/session-driven LLM analysis pass and then loaded by `engine.ingest_analysis`.
This is a real gap between V4 §92's literal step list and today's `cron.sh`, named
here rather than assumed closed.

**Update: that gap is closed.** `engine/analyze_pending.py` is a new scheduled stage,
appended to `cron.sh` right after the watchdog line: `timeout 7200 python -m
engine.analyze_pending --yes --limit 60 || echo "semantic analysis failed"`, guarded
the same way and never blocking `engine.features --refresh` after it. It selects ta-v1/
fa-v1 pending codes straight from the database (usable transcript with no `beats` row;
`frames` + a contact sheet on disk with no `frame_labels` row — skipping any code whose
analysis JSON already sits on disk, which just needs ingesting), exports batches in the
exact shape of this week's hand-run `data/analysis/input/*-batch-N.json` files to
`data/analysis/input/pending-{transcripts,frames}-<run_id>-N.json`, and — only when
`--yes` is given and `claude` is on PATH — runs one unattended `claude -p` per batch
(`engine/prompts/analyze-pending.md` with the real paths substituted,
`--allowed-tools "Read,Write,Bash"`, one `jobs` row per batch: `entity_kind='corpus'`,
stage `TRANSCRIPT_ANALYSIS`/`FRAME_ANALYSIS`, `agent='claude -p'`), exactly like
`cron.sh`'s existing `prompts/angles.md` step. `claude` missing is not a failure —
`NOT_CONFIGURED` is printed, the batches stay on disk for the manual/session-driven
pass, and the jobs are recorded `SKIPPED`, exit code 0. Either way it then runs
`engine.ingest_analysis`, `engine.align`, `engine.features.build` and
`engine.state.refresh_video_state` for whatever code actually landed a `beats`/
`frame_labels` row this run, closing steps 7-8 of V4 §92's 11-step list.

## 12. Phase 3 — production (this owner)

Everything in this section is `engine/production.py` + `engine/storage.py`, built and
tested in this session (test output in §14). See `docs/PRODUCTION_PIPELINE.md` for the
operator runbook (exact commands); this section is the contract, not the how-to.

### 12.1 Supplied MP4 shot contract (`schemas/supplied-take.schema.json`, V4 §82)

One take = `card_id, scene_id, script_segment, take, shot_type, roll (A|B), duration_s,
fps, width, height, orientation, has_audio, audio_quality, subject, in_s, out_s,
sync_notes, quality_status (PENDING|OK|RETAKE), retake_of, sha256, path`. Six fields
(`duration_s, fps, width, height, has_audio, sha256`) are legitimately null until a real
file has been probed; everything else is supplied by the person logging the take and
is never null. The sidecar file is `cards/takes/<card_id>.json` (`{"card_id":...,
"takes": [...]}`, per `cards/README.md`'s own sketch of this file, which this owner's
schema formalizes).

### 12.2 `probe_media(path)`

Tries `ffprobe` first — either bundled next to `imageio_ffmpeg`'s ffmpeg binary (some
platforms ship both; this machine does not, verified: `imageio_ffmpeg`'s binaries
directory holds only `ffmpeg-macos-aarch64-v7.1`) or found on PATH (also absent on this
machine, verified with `shutil.which('ffprobe')` — both checked directly, not assumed).
Falls back to parsing `ffmpeg -i <path>`'s stderr with regexes for `Duration:`,
the video stream's `WxH` and `fps`, and any `Audio:` stream line. Pure stdlib +
`imageio_ffmpeg`, no new dependency, no network. Raises `PipelineError('MEDIA_NOT_
FOUND', ...)` for a missing/empty file and `PipelineError('PROBE_FAILED', ...)` if
neither method could read a real file — never fabricates a duration or resolution.

### 12.3 `validate_take` / `ingest_takes` / `select_takes` / `edl_with_takes`

`validate_take(take, card)` — schema-lite (no `jsonschema` dependency): required
keys/types/enums, `scene_id` must exist in `card['storyboard']`, `in_s < out_s`, and
`out_s` inside a known `duration_s` (0.05s tolerance), and **orientation must be
`portrait`** — every M2Radar card is a 9:16 reel, so anything else is a hard error, not
a warning.

`ingest_takes(con, card_id, takes_dir='cards/takes')` reads the sidecar, probes every
take whose file exists, validates every take against the card, and writes
`cards/takes/<card_id>.validated.json`. It always records one `jobs` row at
`VIDEO_GENERATION_READY` (§5 explains the `SKIPPED`-vs-summary-`PENDING` mapping) and
never claims success it did not observe:

| Condition | `jobs` state | Summary `state` |
|---|---|---|
| `cards/<card_id>.json` missing | `SKIPPED` | `FAILED` |
| No `cards/takes/<card_id>.json` sidecar | `SKIPPED` | `PENDING` |
| Sidecar exists, zero takes have a real file on disk | `SKIPPED` | `PENDING` |
| At least one take has a real file on disk | `DONE` | `DONE` (per-take gaps still reported in `summary['takes']`) |

`select_takes(validated)` — per `scene_id`, the take with `quality_status=='OK'`, no
validation errors, and the highest `take` number; a scene with no qualifying take is
simply absent from the result, so the caller leaves that scene's EDL placeholder
untouched rather than guessing.

`edl_with_takes(card, edl, selection)` — for every scene in `selection`, replaces its
`placeholder` layer with a real `video` layer (asset `duration_frames` from the probed
`duration_s`, `trim_before_frames` from `in_s`), adds the corresponding `video` asset
(`rights_approved: true`, `rights_receipt_id: 'owner-footage'`, real sha256), and
leaves every other scene's placeholder and every scene's `image`/`text` layer exactly
as `engine.edl.card_to_edl` produced them. Raises `ValueError` — never writes a broken
EDL — if a selected take has not been probed yet, or is too short to cover its
storyboard slot once trimmed. Writes the result to `cards/edl/<card_id>.json` (same
path `engine.edl` uses — a Phase 3 EDL is a new version of the same file, not a second
one) and re-validates it through `contract.mjs` via `engine.edl.validate_with_node`
(skipped, not silently passed, if `node` is missing).

### 12.4 Render storage: Supabase canonical, Cloudflare public-delivery only

Verified before writing this module: **no Supabase or Cloudflare/R2 code exists
anywhere in this repo or in `origin/Latest`** — `git grep -il "supabase\|cloudflare\|
r2\b" main` / `origin/Latest` returns only documentation/config mentions
(`SPEC.md`, `.env.example`, `HANDOFF_NOTES.md`, `data-lifecycle.md`) plus false
positives from binary files (fonts, `.db`/`.png`/`.pdf`, matched case-insensitively) and
unrelated identifiers (a local variable `r2` holding an R² regression result in
`score.py`/`m2_signal/transcript_benchmark.py`, and a test-fixture reel literally named
`"R2"` in `origin/Latest`'s recovery tests) — confirmed by reading each text hit, not
just the filename list. `engine/storage.py` is therefore a fresh implementation, not an
upgrade of anything pre-existing.

`Storage` (abstract: `put(local_path, key) -> object_key`, `get_url(key)`,
`record_render(con, record)`). `LocalStorage` copies into `data/renders/objects/` —
always configured, the default in tests and local dev. `SupabaseStorage` — `POST
{SUPABASE_URL}/storage/v1/object/{bucket}/{key}` (bucket default `m2-renders`,
`SUPABASE_BUCKET` overrides), `Authorization: Bearer {SUPABASE_SERVICE_KEY}`; raises
`StorageNotConfigured` with the exact missing variable names whenever either is
absent; its network call is behind an injectable `transport(url, service_key, data)`
so no test in this repo ever makes a real HTTP request. `CloudflareDelivery` is a stub
for the *only* role V4 §84 says is justified here — turning an already-Supabase-stored
key into a public preview URL from `CF_PUBLIC_BASE_URL` — and implements no upload
path at all, matching §84's explicit "do not create a redundant canonical video store."

`record_render(con, record)` validates the record shape (required keys, enum values),
writes `data/renders/<run_id>-<card_id>.json`, and upserts one row into a guarded
`render_records` table this module creates (`schemas/render-record.schema.json`'s
fields, with `source_take_ids`/`render_metadata` flattened to `*_json` columns
matching the rest of this codebase's convention).

**Known gap, surfaced rather than silently worked around:** `.env.example` (owned by
the hiker owner, SPEC §9 — not a file this owner may edit) defines
`CLOUDFLARE_API_TOKEN`/`CF_R2_BUCKET` but not `CF_PUBLIC_BASE_URL`. The code works
without it (`os.environ.get('CF_PUBLIC_BASE_URL')` simply returns `NOT_CONFIGURED`),
but whoever next edits `.env.example` should add it — see
`docs/PRODUCTION_PIPELINE.md` §6.

### 12.5 `render_plan(card_id)` and the render command

Builds the exact `node studio/remotion/render.mjs --edl <edl> --assets <repo root>
--output <path> --browser <chrome>` command (read from `render.mjs` directly, not
guessed) and returns it without running it unless `execute=True`. State is always one
of:

- `NOT_CONFIGURED` — no EDL yet, `studio/remotion/node_modules` missing (**verified
  absent on this machine** — `npm ci` has never been run in this checkout), no
  Chrome/Chromium binary found (checked common macOS/Linux install paths plus
  `M2_CHROME_PATH`/`CHROME_EXECUTABLE`/`PUPPETEER_EXECUTABLE_PATH` env overrides and
  `PATH`), or `node` missing. Includes `install_command` when `node_modules` is the
  cause.
- `READY` — everything needed exists; the command is returned, not run.
- `EXECUTED` — `execute=True`, the subprocess ran and exited 0; `receipt` holds
  `render.mjs`'s own JSON receipt.
- `FAILED` — `execute=True` but the subprocess exited non-zero, or the output file
  already exists (`render.mjs` itself refuses to overwrite one).

## 13. Notion projection

Fully covered by `docs/NOTION_DASHBOARD.md` (owned by the Notion-sync owner, not this
document) — summarized here only as the pipeline's terminal step: `engine.notion_sync
--dry` computes a plan from local SQLite + JSON files only (zero network calls);
`--apply` is implemented but CLI-refused by design, callable only by invoking
`apply_plan()` directly. As of this writing `engine.notion_sync` has made zero writes
to Notion — verified by that document's own header, not re-checked independently here
since this owner does not touch that module.

## 14. Security

Secrets live only in `.env` (gitignored) or the process environment — never in git,
never in a `jobs`/`providers`/`render_records` row, never in a log line. `engine.
providers.Provider.resolve_state` and `engine.db_util.env_present` both compare a
variable against the empty string and then drop it — presence/length only, verified by
reading both functions. This owner's `SupabaseStorage`/`CloudflareDelivery` follow the
same rule: `StorageNotConfigured` messages name the missing *variable*, never its
value; `SupabaseStorage.put`'s injected `transport` receives the service key only to
build an `Authorization` header, never logs or returns it. No `.env`/`*.key`/`secrets/`
file was created, read for its contents, or referenced by value anywhere in this
owner's modules, tests, or this document.

## 15. Testing map

| Test file | Covers |
|---|---|
| `tests/test_engine_schema.py` (39) | `engine.schema`/`engine.state`/`engine.migrate_legacy` — `video_state` computation over a synthetic corpus exercising every tier and flag. |
| `tests/test_hiker_client.py` (13) | `lib/hiker.py` against a fake transport — no network. |
| `tests/test_providers.py` (25) | `engine.providers`/`engine.hiker_config` — environment dictionaries only. |
| `tests/test_local_pipeline.py` (22) | `engine.scenes`/`engine.local_pipeline`/`engine.align`/`engine.watchdog` — synthetic ffmpeg-generated video, real faster-whisper gated behind `-m slow`. |
| `tests/test_lexical.py` (23) | `engine.lexical` — hand-counted transcripts. |
| `tests/test_stats.py` (27) | `engine.stats` — synthetic corpus with a known right answer. |
| `tests/test_cards_v2.py` (12) | `engine.cards_v2`/`engine.storyboard_render`/`engine.edl` — the fictional example card, real PNG + EDL render. |
| `tests/test_ingest_insights.py` (11) | `engine.ingest_insights` — valid/invalid payloads, `--dry`, idempotency. |
| `tests/test_notion_sync.py` (35) | `engine.notion_sync`/`engine.notion_blocks` — block chunking, row mapping, and the non-negotiable "`--dry` never constructs `LiveTransport`" assertion. |
| `tests/test_charts.py` (6) | `engine.charts` — synthetic corpus, no `data/radar.db` dependency. |
| `tests/test_production.py` (26, **this owner**) | `engine.production`/`engine.storage` — see below. |

`tests/test_production.py`'s 26 tests: `probe_media` (real synthetic 3s vertical MP4
with a sine-wave audio track, and a missing-file error case); `validate_take` (a
passing take, missing keys, bad enums, an unknown `scene_id`, out-of-bounds `in_s`/
`out_s`, and the null-until-probed fields); `ingest_takes` (no sidecar → `PENDING`, a
sidecar with no real media → `PENDING`, a missing card → `FAILED`, and a full happy
path that actually probes a real file and writes a real `jobs` row); `select_takes`
(prefers `OK` + latest take, skips scenes with no qualifying take, skips a take that
carries validation errors even if marked `OK`); `edl_with_takes` (binds a real video
layer and — conditionally, only when `node` is actually on PATH — asserts the mutated
EDL still validates through `contract.mjs`; otherwise asserts the honest `skipped`
result; plus the two `ValueError` paths, unprobed and too-short); `render_plan` (`NOT_
CONFIGURED` with no EDL, and with an EDL but no `node_modules`, both real conditions on
this machine, not mocked); `LocalStorage`/`record_render` (real file copy, real SQLite
row, a malformed-record rejection); `SupabaseStorage` (raises without env, a fake-
transport happy path asserting the exact URL/headers/body the transport received, and
a transport-error path); `CloudflareDelivery` (both states).

Verified in this session:

```
$ python3 -m pytest tests/test_production.py -q
26 passed in 0.60s

$ python3 -m pytest tests -q
238 passed, 1 skipped, 17 warnings in 17.75s
```

(The skip is `test_local_pipeline.py`'s real-faster-whisper test, gated behind `-m
slow` by that file's own design, unrelated to this owner's work. The 17 warnings are
pre-existing — one unregistered `pytest.mark.slow` in `test_local_pipeline.py` and 16
`PendingDeprecationWarning`s from `matplotlib` in `test_charts.py` — neither touched by
this session.)

## 16. Limitations and known gaps

- **The legacy 9-frame corpus is sampled, not real cuts.** `frames_version='fixed9-v1'`
  codes have 9 frames at fixed offsets, not detector-found scene boundaries; any
  `cuts`/`cuts_per_min` figure for those codes is labelled `ffmpeg_scene_0.35_count_
  only` in `video_features.cut_metric_quality`, never presented as a real cut count.
- **Media is never retained.** Every downloaded mp4 is deleted after frame extraction
  (`docs/data-lifecycle.md` §1); a pruned reel whose signed URL has since expired and
  whose cache file has aged out cannot be re-derived — a structural gap named, not
  solved, in that document.
- **Max's ASR corpus is not in this git repo.** `origin/Latest`'s ~1,062 transcripts
  and ~19,808 frames exist on his side only; `reports/audit/01-branch-comparison.md`
  §5.2 recommends exporting them through the `m2_signal` receipt format, not yet done.
- **Two music-only reels** carry no usable transcript by design (not a processing
  failure) — folded into `FRAMES_ONLY`/`TRANSCRIPT_UNUSABLE` depending on which tier
  definition is used (§4.4).
- **The analysis-ready corpus is a selection, not a random sample.** It is whatever
  had a live URL when the deep-dive ran; any claim about "what performs" drawn from it
  inherits that selection bias and must say so.
- **Two disagreeing corpus-tier definitions remain unresolved** (§4.4) —
  `engine/HANDOFF_NOTES.md`'s features-owner section flags this for the orchestrator,
  not fixed here.
- **V4 §92's watchdog step list (11 steps) is not fully automated.** Steps 7-8
  (semantic transcript/visual analysis) run outside `cron.sh` today (§11).
- **Phase 3 has no cron step.** `engine.production`/`engine.storage` are operator-run;
  no scheduled job ingests new takes automatically (§7, §12).
- **`VIDEO_RENDER`/`QUALITY_REVIEW` are named stages with no writer yet** (§5) — a
  render today is traced only by whatever the operator records manually
  (`docs/PRODUCTION_PIPELINE.md` §5).
- **This owner's count correction:** `db.py` has 14 tables by direct count, not the 15
  SPEC.md §0.1 and the audit both state (§4.1) — flagged, not silently repeated.
- **`.env.example` has no `CF_PUBLIC_BASE_URL` entry** (§12.4) — the code tolerates
  this; the file itself is another owner's.

## 17. Glossary

- **code** — Instagram shortcode, the video id everywhere.
- **run_id** — `YYYY-MM-DD_HHMM-<6 hex>`; **job_id** — uuid4 hex.
- **analysis_ready** — `video_state` flag: transcript DONE + frames DONE_* + both
  semantic analyses DONE. Stricter than either corpus-tier definition (§4.4).
- **PREVIS / PRODUCTION render_mode** — an EDL's `render_mode`; PREVIS never claims
  real footage or approved audio exists, PRODUCTION is gated by `contract.mjs` behind
  `review_state='APPROVED'` and no pending audio/placeholder layers.
- **take** — one supplied MP4 shot for one storyboard scene (§12.1); not the same as
  a `scenes` row (a detected/sampled interval inside an *analyzed reference reel*).
- **object_key** — the string a `Storage.put()` call returns; a plain relative path
  for `LocalStorage`, `'<bucket>/<key>'` for `SupabaseStorage`.
- **rights_receipt_id** — the EDL asset field `contract.mjs` requires alongside
  `rights_approved: true`; `'internal-template'` for a rendered placeholder PNG,
  `'owner-footage'` for a real supplied take (this owner's convention, not itself
  defined by `contract.mjs`).
