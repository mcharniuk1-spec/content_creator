# M2Radar Content Engine — Integration Execution Report

Required by the execution specification §46 ("Execution report") and §50 ("Final execution
summary"). Written 2026-09-12. Every number in this document was read from the repository
or from `data/radar.db` at the time of writing; nothing is estimated. Where a figure could
not be reproduced locally it says so in the same line.

Four values are filled in by the orchestrator and are left as literal placeholders here:
`<<COMMIT_HASH>>`, `<<LATEST_SYNC>>`, `<<NOTION_RESULT>>`, `<<SERVER_DEPLOY>>`.

---

## 1. Summary

1. The content engine now exists as 30 Python modules under `engine/`, layered on top of the
   existing radar scripts, with its own versioned schema (18 engine tables) inside the same
   `data/radar.db`.
2. The legacy corpus was migrated in place: 1,357 accounts, 3,211 unique reel codes, 5,147 reel
   readings, 281 transcripts, 2,727 frame rows. Zero rows were added or dropped by the migration
   (`data/migration_log.md`: every delta `+0`).
3. Analysis coverage is small and stated everywhere as such: 266 transcript analyses (ta-v1) and
   295 frame analyses (fa-v1), giving `N_ready = 268` of `N_ingested = 3,211` — **8.3 %**.
4. 30 insights (12 RELIABLE, 16 PROBABLE, 2 INSUFFICIENT), 24 hypotheses of which 10 were
   SELECTED, and 41 hypothesis-specific references are persisted in the database.
5. Ten new cards were written, reviewed by two independent reviewer passes, revised, and
   persisted (`cards_v2` 10, `card_scenes` 70, `script_versions` 20). Eight are
   READY_WITH_NOTES, two are PRODUCTION_READY.
6. 80 storyboard frame images were rendered for the new cards (70 scene frames + 10 contact
   sheets); 10 Remotion EDLs validate `EDL_OK` against the shipped contract.
7. One real Remotion render was executed end to end on the example card: 1080×1920, 30 fps,
   60.05 s, 3,433,827 bytes, Remotion 4.0.520 (`reports/evidence/`).
8. Two PDFs were produced: the analytical report (132 pages) and the card book (105 pages).
9. Tests: `pytest -q` → **252 passed, 1 skipped**; `check.py` → 23/23; the 12 root scripts →
   165/165 checks, all "ТЕСТ ПРОЙДЕН".
10. Not done: nothing is committed (`git log main..content-engine` is empty), Notion `--apply`
    has not been observed to complete, and the 1,312 unprocessed newest-snapshot reels are still
    unprocessed.

---

## 2. Repository & branches

| Item | Value |
|---|---|
| Repository (local) | `/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar` |
| `origin` | `git@github.com:MickaelAmpl/m2lab-radar.git` |
| `max` (Max's fork) | `git@github.com:mcharniuk1-spec/m2lab-radar.git` |
| `main` | `92e71e7a0543bacce2adafd65941eaa008632d62` |
| `origin/main` | `92e71e7a0543bacce2adafd65941eaa008632d62` (identical) |
| `content-engine` (working branch) | `92e71e7a0543bacce2adafd65941eaa008632d62` — **no commits yet** |
| Pushed commit hash | `<<COMMIT_HASH>>` |
| `origin/Latest` | `31ed2d41aea62b97959d8e22b01d30a62834ba02` — intact, never written to |
| `max/main` | `6462f409cd5f5c89cb9bc72e79f93e52f853907b` |
| `latest` sync state | `<<LATEST_SYNC>>` |

**On the `latest` sync state.** `git rev-parse origin/Latest max/main` returns two different
hashes, so the two are **not** equal at the time of writing. `git merge-base origin/Latest
max/main` = `31ed2d41`, and `git merge-base --is-ancestor origin/Latest max/main` returns true:
`max/main` is exactly one commit ahead of `origin/Latest` (`6462f409` "Add reconciled M2 analysis
and ten cards" — two reports plus `scripts/build_m2_reconciled_pdf.py`, no code). `origin/Latest`
itself is untouched by this work: `git log main..content-engine` is empty and no branch other
than the local `content-engine` working tree was modified.

**Working-tree state.** `git status --porcelain` shows 17 modified tracked files and 29 untracked
paths (`engine/`, `tests/`, `cards/`, `reports/`, `schemas/`, `studio/`, `tools/`, `config/`,
`reference/`, seven new `docs/*.md`, `pytest.ini`, `lib/__init__.py`, and ten leftover
`runs/2026-09-07/*.jpg` contact-sheet crops). None of it is committed.

**What was ported from `origin/Latest` / `max/main`** (audit: `reports/audit/01-branch-comparison.md`
§5.1–5.2, "port the state DAG, scene contract, Remotion EDL contract, provider catalog, bounded
media workers"):

- the run/job **state DAG** → `engine/state.py`, tables `runs` / `jobs` / `video_state`;
- the **scene contract** → `engine/scenes.py`, `engine/align.py`, table `scenes`;
- the **Remotion EDL contract** → `engine/edl.py` + `studio/remotion/` (contract
  `m2.remotion-edl.v1`);
- the **provider catalog** → `engine/providers.py`, table `providers`;
- **bounded media workers** → `engine/process_budget.py` (bounded subprocess capture, minimal
  environment, process-group cleanup).

**What stays historical and was deliberately not merged:**

- `m2_signal/` (release/observation ledger, ~24 MB per snapshot against main's whole 5.2 MB DB),
  `m2_orchestrator/` (41-stage DAG of which 29 stages have no code), `m2_studio/` — kept as a
  read-side projection idea, not as a replacement schema (audit §5.3 "What NOT to do");
- Latest's `run.py` replacement and neutralised `install-cron.sh` — merging them as-is breaks the
  `/opt/radar` cron chain (audit summary item 3, the highest-risk collision);
- Latest's Swift/Apple Vision OCR binary (macOS-only, will not run on the Linux server) and its
  bare-`ffmpeg`-from-PATH assumption;
- Max's 1,062 transcripts and 19,808 frames — **not in git on either branch** (audit §1.6,
  confirmed by full tree scan), so they could not be ported and remain an export task.

---

## 3. What was executed, wave by wave

Orchestration model: a **Fable** orchestrator dispatched each wave; **Opus** ran the audits,
the analytical passes and the long-form writing; **Sonnet** built the integration modules, the
frame/EDL work, the tests and the documentation; **Haiku** produced the requirements checklist
and the mechanical ports.

| # | Wave | Model | What actually landed |
|---|---|---|---|
| 1 | Audit | Opus (Haiku for the checklist) | Six documents in `reports/audit/`: `00-requirements-checklist.md` (185 tracked requirements), `01-branch-comparison.md` (811 lines), `02-data-inventory.md` + `.json`, `03-server-runtime-hiker.md` (613 lines, read-only pass over `/opt/radar` on `m2vps`), `04-existing-cards-review.md` (33 cards), `05-notion-state.md`. |
| 2 | Engine build | Sonnet | `engine/` — 30 Python modules, `engine/SPEC.md` (356 lines), versioned schema (`engine/schema.py`, migrations v1+v2 applied), `engine/migrate_legacy.py`. Migration run 2026-09-11T22:20:22Z: all row deltas `+0`, `integrity_check ok`, 0 foreign-key violations. |
| 3 | Corpus analysis | Opus | 266 ta-v1 transcript analyses (`data/analysis/transcripts/`) and 295 fa-v1 frame analyses (`data/analysis/frames/`), ingested through `engine/ingest_analysis.py` in **seven batches** logged in `data/analysis/ingest_warnings.md` (16:43, 16:52, 16:53, 16:54 ×2, 22:20, 22:26 UTC on 2026-09-11). File timestamps show the transcript pass ran 18:19–18:29, **stopped for 13 minutes**, and resumed 18:42–19:01; the frame pass wrote 192 files in the 18:00 hour and 59 in the 19:00 hour (251), then was resumed on 2026-09-12 in the 00:00 hour for the remaining 44. Out-of-vocabulary labels were kept in `labels_json` and logged rather than dropped (`thesis`, `demo_first`, `story_open`, `contrast`, `comparison`). |
| 4 | Stats / features | Sonnet | `engine/stats.py`, `engine/features.py`, `engine/lexical.py` → `video_features` 3,211 rows at `features_version = fv-1`; `creator_stats` 132; `reports/stats/stats-2026-09-12.json` (802,749 bytes); `reports/data/` (14 files) and 18 charts in `reports/charts/`. |
| 5 | Insights | Opus | 30 insights persisted (`insights` table), loaded via `engine/ingest_insights.py`; rejected/soft-warned records logged to `data/analysis/ingest_insights_warnings.md` rather than silently accepted. |
| 6 | Hypotheses | Opus | 24 hypotheses generated and scored (`reports/analysis/08-hypotheses.md`, 413 lines); 10 SELECTED, 14 REJECTED; 41 hypothesis-specific references (`hypothesis_refs`). |
| 7 | Scripts | Opus | 10 cards written frame-aware against their own hypothesis's references; `script_versions` 20 rows (two per card). |
| 8 | Reviews | Opus | Two independent reviewer passes: `reports/analysis/10-script-review-A.md` (cards 01/03/05/07/09, 41 findings) and `10-script-review-B.md` (cards 02/04/06/08/10, 66 findings). 107 findings total; nine of ten scripts revised to a new version. |
| 9 | Cards | Sonnet | `engine/cards_pipeline.py` runs: validate → render storyboard → persist → EDL → node validation. Two `cards` runs recorded (`2026-09-12_0844-1baa1c` 5 cards, `2026-09-12_0853-138ee2` 10 cards), both `DONE`, `failed: []`. |
| 10 | PDFs | Sonnet | `engine/pdf_build.py` + `tools/pdf/md2pdf.mjs` → `reports/final/M2RADAR_ANALYTICAL_REPORT.pdf` (132 pages) from 38 Markdown sections, and `M2RADAR_CARD_BOOK.pdf` (105 pages) from 12 card-book sections. |
| 11 | Notion | Sonnet | `engine/notion_sync.py` + `engine/notion_blocks.py` + `docs/NOTION_DASHBOARD.md`. Dry plan regenerated 2026-09-12T08:53:56Z: `reports/notion-sync-plan.md`, 567 lines, dashboard body 169 blocks in 1 append call. See §10. |
| 12 | Tests | Sonnet | `tests/` (13 pytest modules), `pytest.ini`, `docs/TESTING.md`. Results in §9. |
| 13 | Server staging | Sonnet | `<<SERVER_DEPLOY>>` — see §11. |

---

## 4. Data

### 4.1 Corpus counts and denominators — both vocabularies

The project deliberately carries **two** corpus-tier vocabularies and they disagree on the
frames-only boundary. `reports/data/corpus_tiers.json` states it in its own `note`: *"The two
vocabularies disagree by design ... and are not interchangeable — every downstream report must
name which one a number was divided by."*

`engine.corpus.tiers()` (run 2026-09-12):

| tier | codes | share of ingested |
|---|---:|---:|
| ANALYSIS_READY | 268 | 8.3 % |
| FRAMES_ONLY | 22 | 0.7 % |
| TRANSCRIPT_UNUSABLE | 7 | 0.2 % |
| INGESTED_NOT_ANALYZED | 2,914 | 90.8 % |
| **TOTAL** | **3,211** | 100 % |

Plus 6 orphan codes that have analysis but no `reels` row and are excluded from every tier:
`DT0fJmxjVnI`, `DU9OIJUCBQz`, `DZw4aTtzJpg`, `Db9AEm5upfu`, `DbOUP9OPDAQ`, `DcdbJKmxZ5o`.

`video_state.corpus_tier` (the second vocabulary, as recorded in
`reports/migration-validation.json`): ANALYSIS_READY 268, **FRAMES_ONLY 29**,
INGESTED_NOT_ANALYZED 2,914. The difference is definitional: `engine.corpus` gives the 7
empty-transcript codes their own `TRANSCRIPT_UNUSABLE` tier instead of folding them into
FRAMES_ONLY (22 + 7 = 29).

Denominators, all from `python3 -m engine.corpus`:

| name | n | what it counts |
|---|---:|---|
| `N_ingested` | 3,211 | reel codes with Hiker metadata — the only denominator for metric-only stats |
| `N_transcript` | 275 | codes with a `transcripts` row (7 of them empty) |
| `N_transcript_usable` | 268 | words > 0 and timed segments — denominator for every language statement |
| `N_frames` | 297 | codes with `frames` rows (9 fixed samples each, `fixed9-v1`) |
| `N_ready` | 268 | usable transcript **and** frames — denominator for script + visual conclusions |

**A discrepancy worth naming.** `docs/M2RADAR_ANALYSIS_METHOD.md` and every narrative report use
**266** for `N_transcript_usable` / `N_ready`; `python3 -m engine.corpus` returns **268** today.
266 is the count of ta-v1 analysis *files* actually written (`data/analysis/transcripts/` = 266
files); 268 is the count of codes that qualify as analysis-ready in the database. The gap is
exactly two named codes — `DRXZJeHiAES` and `Db5sXEAP6C4`, both August-archive imports — which
qualify as analysis-ready but have no ta-v1 file; the reverse set is empty. Beats were loaded for
**264** codes, so two of the 266 analysed files produced no beat rows. All three numbers are
correct for what they count; they are not interchangeable.

### 4.2 Migration, before → after

`data/migration_log.md` (generated 2026-09-11T22:20:22Z by `python3 -m engine.migrate_legacy`)
records **every table delta as `+0`** — the migration was verification and back-fill, not
movement. Row counts before = after: `accounts` 1357, `reels` 5147, `scores` 7477, `topics` 2482,
`deepdives` 282, `frames` 2727, `transcripts` 281, `transcript_meta` 281, `beats` 1527,
`scenes` 948, `frame_labels` 2600, `video_features` 3211, `video_state` 3211, `cards` 23,
`spend` 10, `tool_log` 37.

Identity counts: accounts 1,357 (130 active) · creators with reels 132 · unique video codes 3,211
· video readings 5,147 · transcripts 281 (274 usable by the migration's own rule) · frames rows
2,727 across 303 codes · deepdives 282 · cards 23.

`integrity_check` = `ok`; `foreign_key_violations` = `[]`; `reels_pk_violations` = 0;
`frames_pk_violations` = 0. Unmatched records were **logged, not dropped**: 6 unresolved August
archive codes are listed by code in `steps.august_archive.unresolved_codes`.

Since that snapshot the analysis tables grew (`frame_labels` 2600 → 2645, `scenes` 948 → 960) and
the engine tables were populated (`runs` 0 → 7, `jobs` 0 → 265, `insights` 0 → 30, `hypotheses`
0 → 24, `hypothesis_refs` 0 → 41, `cards_v2` 0 → 10, `card_scenes` 0 → 70, `script_versions`
0 → 20). `reports/data/manifest.json` and `reports/data/runs_jobs.json` were generated before
that and still show the zero state — they are a snapshot of 2026-09-11T22:26, not current.

### 4.3 Flags

`reports/data/flags.json`, 3,211 codes examined, **3,006 carry at least one flag**:

| flag | n |
|---|---:|
| MISSING_TRANSCRIPT | 2,936 |
| MISSING_FRAMES | 2,914 |
| STALE_METRICS | 1,676 |
| DUPLICATE_VIDEO | 56 |
| UNALIGNED_TRANSCRIPT | 7 |
| BROKEN_FRAME_REFERENCE | 1 |
| MISSING_MEDIA | 1 |
| MISSING_STATS | 1 |
| UNRESOLVED_CREATOR_ID | 1 |

### 4.4 What is excluded and why

- **2,914 INGESTED_NOT_ANALYZED codes** — no transcript and no frames. They contribute to
  metric-only statistics (`N_ingested`) and to nothing else. No script or visual conclusion in
  any report divides by 3,211 unless it is a pure metric statement.
- **7 TRANSCRIPT_UNUSABLE codes** — a `transcripts` row exists but is empty (no speech
  detected). Excluded from every language statement.
- **6 orphan codes** — analysis exists, no `reels` row. Excluded from every tier and every
  denominator; listed by code above.
- **8 broken frame files** — all on one code, `DcxV37-CJOC` (truncated download). Marked
  `frames.exists_ok = 0` and reported by `check.py` as a known limitation, not as a discrepancy.
- **The `followers` table is empty**, so no creator-growth claim is possible.
- **The selection bias itself.** `deep.py` only processed reels `score.py` had already ranked
  near the top of their creator's output. Median `robust_z` inside the analysis-ready tier is
  **+1.26** against **0.00** across all 3,211. Every contrast in the analysis compares strong
  reels with other strong reels — stated at the top of `reports/analysis/01-general-conclusions.md`
  and repeated in the executive summary.

### 4.5 Newest Hiker reels pending the watchdog

Newest snapshot: `snapshot_id = 3`, **1,535 codes**, of which **1,312 are unprocessed** (no
transcript, no frames) and **410 were first seen in that snapshot**. They are queued for
`engine/watchdog.py`, which finds codes that are ingested but not analysis-ready and runs the
local pipeline on them using **only already-cached HikerAPI URLs** — it never calls HikerAPI and
never pays. It has not yet been run against the live corpus. Because Instagram's signed CDN URLs
expire in hours (`docs/data-lifecycle.md` §2), any code whose cached `clips*.json` no longer
yields a live URL needs a fresh paid Hiker call — see the open decision in §15.

---

## 5. Architecture delivered

### 5.1 Modules (`engine/`, 30 Python modules + SPEC, handoff notes and 4 analysis prompts)

| Module | One line |
|---|---|
| `align.py` | Segment ↔ scene alignment (SPEC §6 step 5). |
| `cardbook.py` | Turns `cards/<id>.json` documents into the card-book Markdown. |
| `cards_pipeline.py` | Finalize a card: validate → render frames → save to DB → EDL → node validation. |
| `cards_v2.py` | Validate, persist and list `cards/<id>.json` (`m2radar.card.v2`). |
| `charts.py` | The 18 analytical PNG charts for the report. |
| `corpus.py` | Corpus tiers, code lists and the five denominators. |
| `db_util.py` | Connection and value helpers shared by every engine module. |
| `edl.py` | Card → Remotion EDL against `studio/remotion/contract.mjs`. |
| `features.py` | Consolidates everything known about one video into `video_features`. |
| `hiker_config.py` | Hiker and Notion configuration validation (SPEC §9). |
| `ingest_analysis.py` | Loads the ta-v1 / fa-v1 LLM analysis JSON into the database. |
| `ingest_insights.py` | Loads insights / hypotheses / hypothesis_refs JSON into the database. |
| `lexical.py` | Phrase-level and word-class features from a transcript. |
| `local_pipeline.py` | Local, free, per-video processing: media → transcription → scenes/frames. |
| `migrate_legacy.py` | Re-runnable migration of the legacy corpus into the engine tables. |
| `notion_blocks.py` | Pure Notion block-JSON builders; no network. |
| `notion_sync.py` | Notion dashboard sync (SPEC §85–91), `--dry` and `--apply`. |
| `pdf_build.py` | Python entry point for the dependency-free Markdown → PDF builder. |
| `process_budget.py` | Bounded subprocess capture, minimal env, process-group cleanup. |
| `production.py` | Phase 3: supplied MP4 takes → validated sidecar → EDL with real footage. |
| `providers.py` | Provider registry (SPEC §2.10, §9). |
| `report_data.py` | Report-ready data bundles for the report writers. |
| `scenes.py` | Scene/cut detection and frame extraction. |
| `schema.py` | Versioned, idempotent migration for the engine tables. |
| `state.py` | Run/job tracing and the per-video processing contract. |
| `stats.py` | Creator and video statistics. |
| `storage.py` | Storage for rendered video: Supabase canonical, local fallback, Cloudflare stub. |
| `storyboard_render.py` | Template-rendered storyboard frames for a card. |
| `watchdog.py` | Catch-up worker for ingested-but-not-analysed codes; cache-only, never pays. |
| `SPEC.md` | The engine's own specification (356 lines). |
| `HANDOFF_NOTES.md` | Per-owner handoff notes (291 lines). |
| `prompts/`, `__init__.py` | Analysis prompts; package marker. |

Schema state: `python3 -m engine.schema --check` → **"schema up to date", "pending migrations:
none"**, migrations v1 and v2 applied.

### 5.2 Providers (`python3 -m engine.providers`, run 2026-09-12)

| Provider | Kind | Role | State | Detail |
|---|---|---|---|---|
| `hiker` | social_data | DEFAULT | NOT_CONFIGURED | not set (checked process env and `.env`) |
| `local-faster-whisper` | transcription | DEFAULT | **CONFIGURED** | local tool, no credentials required |
| `local-ffmpeg-scenes` | frames | DEFAULT | **CONFIGURED** | local tool, no credentials required |
| `remotion` | render | DEFAULT | **CONFIGURED** | `/usr/local/bin/npx` on PATH; Chrome presence not separately verified — PREVIS mode |
| `loore` | media | OPTIONAL_PROVIDER | DISABLED | never required for the default path; `LOORE_ENABLED=1` to opt in |
| `supabase` | storage | OPTIONAL_PROVIDER | NOT_CONFIGURED | missing `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` |
| `cloudflare` | storage | OPTIONAL_PROVIDER | NOT_CONFIGURED | missing `CLOUDFLARE_API_TOKEN`, `CF_R2_BUCKET` |
| `openai` | image_gen | OPTIONAL_PROVIDER | NOT_CONFIGURED | missing `OPENAI_API_KEY` |
| `higgsfield` | video_gen | OPTIONAL_PROVIDER | NOT_CONFIGURED | missing `HIGGSFIELD_API_KEY` |

The `providers` table in the database holds 9 rows and is stale relative to this live probe (it
still carries the older `hiker` detail text and shows `remotion NOT_CONFIGURED`); the live probe
is authoritative. The `hiker` row's own detail records the trap: `lib/hiker.py`
also falls back to the local MCP settings file, which the registry does not inspect, so on a
machine where only that third source holds the key Hiker works while the row says
NOT_CONFIGURED.

### 5.3 State tracing

`runs` = **7**, `jobs` = **265**.

Runs by kind: `analysis` 5 (all `DONE`, 2026-09-11 23:39–23:45, each summarising 30 insights /
24 hypotheses / 41 refs, `rejected_*` all empty), `cards` 2 (`2026-09-12_0844-1baa1c`, 5 cards
ok; `2026-09-12_0853-138ee2`, 10 cards ok; `failed: []` in both).

Jobs by stage — every one in state `DONE`:

| stage | n |
|---|---:|
| CONCEPT_GENERATION | 120 |
| REFERENCE_SELECTION | 50 |
| CARD_GENERATION | 15 |
| FRAME_GENERATION | 15 |
| FRAME_PLAN | 15 |
| SCRIPT_GENERATION | 15 |
| SCRIPT_REVIEW | 15 |
| VIDEO_GENERATION_READY | 15 |
| GENERAL_ANALYSIS | 5 |
| **total** | **265** |

Jobs per run: 35 for each of the five analysis runs, 30 and 60 for the two card runs.
`check.py` confirms 0 jobs pointing at a missing run and 0 orphaned `beats` / `frame_labels` /
`scenes` against `video_state`.

### 5.4 Hiker in git without the key

`reports/audit/03-server-runtime-hiker.md` §1: `git grep -nE "hiker_|HIKER|Bearer|x-access-key"`
across `*.py` returns only references to environment-variable and header names — **no literal key
or token is hardcoded anywhere in the repo**. `.env` is git-ignored (`.gitignore` line 2, with
`!.env.example`), mode `-rw-------` both locally and on the server, and the only `.env*` file
tracked by git is `.env.example`. The committed architecture is `lib/hiker.py` (HTTP client),
`engine/hiker_config.py` (configuration validator), `collect_snapshot.py` / `roster.py` /
`deep.py` (normalisation into the canonical models) and `cron.sh` (13-step chain) — deployable to
`/opt/radar` with nothing but a populated `.env`. The audit confirms server code == git main
exactly at `92e71e7a`.

### 5.5 Local-first defaults

`local-faster-whisper` (`faster-whisper/small`, `int8`, `asr_version =
faster-whisper-small-int8-v1`) is the DEFAULT transcription provider and accounts for **273 of
281** `transcript_meta` rows (the other 8 predate the version field and are `provider = unknown`).
`local-ffmpeg-scenes` is the DEFAULT frames provider. Both are CONFIGURED and require no
credentials. `loore` is `OPTIONAL_PROVIDER` / `DISABLED` and is never on the default path —
`LOORE_ENABLED=1` is required to opt in.

---

## 6. Analysis outputs

### 6.1 Insights

30 insights persisted in the `insights` table:

| Confidence | n |
|---|---:|
| RELIABLE | 12 |
| PROBABLE | 16 |
| INSUFFICIENT | 2 |

Each row carries `statement`, `claim`, `metric`, `n`, `comparison`, `evidence_json`,
`supporting_codes_json`, `supporting_creators_json`, `transcript_pattern`, `frame_pattern`,
`interpretation`, `implication`, `confidence` and `limitations` — the numbers and their evidence
are in the database, not only in prose.

### 6.2 The ten headline findings

From `reports/final/partA/01-executive-summary.md`:

| # | Finding | Confidence |
|---|---|---|
| 1 | The analysed corpus is 268 of 3,211 codes (8.3 %) and is the **top** of `score.py`'s own ranking, not a random sample — median `robust_z` inside it is +1.26 against 0.00 across all ingested reels. | RELIABLE |
| 2 | Duration does not predict performance: Spearman(duration, `robust_z`) = −0.069 (p<0.001) over all 3,211 reels; HIGH outliers run a median 46.8 s against 47.8 s for the rest. | RELIABLE |
| 3 | Hook length carries no measured signal (rho ≈ +0.06–0.08, p>0.2); the median hook is 6.7 s / 21.5 words, not the 0–3 s window house rules assume. | PROBABLE |
| 4 | Show-first hooks (demo/result first, n=42) outperform on reach: median `robust_z` 2.17 / `view_lift` 5.81 vs 1.21 / 1.80 for the rest. | PROBABLE |
| 5 | Setup-first hooks (identity/story/problem-call-out, n=39) underperform: median `robust_z` 0.67 vs 1.36 (p=0.002). | PROBABLE |
| 6 | Questions in the script depress saves: rho(questions, `save_rate`) = −0.229 (p<0.001), survives creator normalisation. | RELIABLE |
| 7 | A screen on camera is the single most reliable visual finding: `screen_share` vs `share_rate` rho +0.203, creator-normalised +0.129–0.285 across two related tests. | RELIABLE |
| 8 | Split screen — the niche's most common opening (73/266) — is also its weakest visual pattern: median `robust_z` 1.03 vs 1.43 (p=0.044). | PROBABLE |
| 9 | Comment-keyword gates (59 % of the corpus) inflate comment rate 23×, save rate 2.8×, share rate 1.8× and move reach not at all (p=0.58–0.63) — a live contamination risk for M2's own reference selection. | RELIABLE |
| 10 | Naming specific tools/numbers (`lex_entities_distinct`, specificity) is the one lexical family that predicts reach and survives creator normalisation (+0.16–0.21). | PROBABLE |

### 6.3 Hypotheses

24 generated, **10 SELECTED**, 14 REJECTED (`hypotheses` table; narrative in
`reports/analysis/08-hypotheses.md`).

Selected mix by format: **M2 Builds 4** (H-11, H-12, H-13, H-18), **M2 Radar 4** (H-01, H-04,
H-05, H-09), **M2 Teardown 2** (H-19, H-20). Selected `total_score` runs 4.16–4.69; the
best-scoring rejected hypothesis sits at 3.67, so the cut is clean. By confidence the selected set is 4 RELIABLE and 6
PROBABLE; every INSUFFICIENT hypothesis was rejected.

### 6.4 References

**41** rows in `hypothesis_refs`, all attached to a selected hypothesis: H-11 carries 5, the
other nine carry 4 each. Every row records `function`, `reason`, `useful_beat_ids_json`,
`useful_scene_ids_json`, `performance_json` and `transformation` — references are per-hypothesis,
not a global pool. The 41 refs map one-to-one onto the 41 references embedded in the ten card
JSON documents (5 + 9 × 4).

### 6.5 The two PRODUCTION.md numbers that did not reproduce

`reports/analysis/01-general-conclusions.md` §H item 6 and
`reports/charts/duration_vs_performance.json`:

| PRODUCTION.md claim | Original basis | What reproduces on 3,211 creator-normalised reels |
|---|---|---|
| "the winners' median is 55 seconds against 47 for the rest" | a 100-reel top slice of an earlier 2,352-reel export | 46.8 s for the 375 HIGH outliers against 47.8 s for the other 2,836 |
| "under twenty seconds is 5 % of winners and 13 % of the rest" | same 100-reel slice | 14 % of HIGH outliers against 12 % of the rest — the direction is reversed |

A third, related correction lands on `RULES.md` §7: "a share separates a winner 3.6× more
reliably, a save 2.8×" becomes **2.62×** and **2.09×** on the full corpus with the denominator
guard applied.

---

## 7. Cards

### 7.1 The ten cards

`total_s`, `words` and claim states are read from `cards_v2`; `scenes` from `card_scenes`;
`refs` from the card JSON; verdicts from the two reviewer documents.

| Card | Hyp. | Format | `total_s` | Words | Scenes | Refs | Claims (OBS/PLAN/TO_MEASURE/MISSING) | Verdict | Status |
|---|---|---|---:|---:|---:|---:|---|---|---|
| C-2026-09-12-01 | H-11 | M2 Builds | 68.4 | 171 | 8 | 5 | 6 / 1 / 1 / 1 | READY_WITH_NOTES | REVIEWED |
| C-2026-09-12-02 | H-12 | M2 Builds | 65.2 | 163 | 6 | 4 | 5 / 1 / 2 / 2 | READY_WITH_NOTES | REVIEWED |
| C-2026-09-12-03 | H-18 | M2 Builds | 69.6 | 167 | 7 | 4 | 5 / 1 / 1 / 1 | READY_WITH_NOTES | REVIEWED |
| C-2026-09-12-04 | H-01 | M2 Radar | 68.0 | 170 | 7 | 4 | 5 / 0 / 1 / 4 | **PRODUCTION_READY** | REVIEWED |
| C-2026-09-12-05 | H-13 | M2 Builds | 68.5 | 178 | 8 | 4 | 4 / 1 / 1 / 1 | READY_WITH_NOTES | REVIEWED |
| C-2026-09-12-06 | H-04 | M2 Radar | 69.2 | 173 | 7 | 4 | 4 / 1 / 1 / 2 | READY_WITH_NOTES | REVIEWED |
| C-2026-09-12-07 | H-20 | M2 Teardown | 69.2 | 173 | 7 | 4 | 7 / 1 / 1 / 1 | READY_WITH_NOTES | REVIEWED |
| C-2026-09-12-08 | H-09 | M2 Radar | 69.6 | 174 | 7 | 4 | 3 / 1 / 1 / 3 | READY_WITH_NOTES | REVIEWED |
| C-2026-09-12-09 | H-05 | M2 Radar | 68.0 | 170 | 7 | 4 | 5 / 1 / 1 / 2 | READY_WITH_NOTES | REVIEWED |
| C-2026-09-12-10 | H-19 | M2 Teardown | 66.4 | 166 | 6 | 4 | 5 / 0 / 1 / 3 | **PRODUCTION_READY** | REVIEWED |

Totals: **1,705 words**, **682.1 seconds**, **70 scenes**, **41 references**, **88 claims**
(49 OBSERVED, 8 PLANNED, 11 TO_MEASURE, 20 MISSING). Every `total_s` sits inside PRODUCTION.md's
50–70 s band. All ten are `review.revised: true`, `review.version: 1`; nine carry
`script.version: 2` and card 01 stayed at version 1 (its nine findings were all evidence-source
rewrites, no script change).

Reviewer volume: 107 findings across the two passes (A: 9 + 8 + 7 + 8 + 9 = 41 on cards
01/03/05/07/09; B: 14 + 13 + 13 + 13 + 13 = 66 on cards 02/04/06/08/10). Three cards arrived with
a hard evidence error (05, 07, 09); two of those (07, 09) would have been NOT_READY as written and
were fixed rather than dropped.

### 7.2 Where things live

- Card JSON (`m2radar.card.v2`): `cards/C-2026-09-12-01.json` … `-10.json` (10 files).
- Storyboard frames: `cards/frames/` — **88 PNGs total**: 70 scene frames + 10 contact sheets for
  the new cards, plus 7 scene frames + 1 sheet for the example card `C-2026-09-11-EX`.
- Remotion EDLs: `cards/edl/C-2026-09-12-*.json` (10) plus `C-2026-09-11-EX.json`.
- Database: `cards_v2` (10), `card_scenes` (70), `script_versions` (20).
- Card book source: `reports/final/cardbook/` (12 Markdown sections).

### 7.3 EDL validation

All ten validated against contract `m2.remotion-edl.v1` on 2026-09-12T08:53:25–28Z, render mode
`PREVIS`, 30 fps, `returncode 0`, `stdout: EDL_OK`, `ok: true`, `skipped: false` — zero failures.
Duration in frames: 01 → 2052, 02 → 1956, 03 → 2088, 04 → 2040, 05 → 2055, 06 → 2076, 07 → 2076,
08 → 2088, 09 → 2040, 10 → 1992.

### 7.4 The real Remotion PREVIS render

Executed on the example card `C-2026-09-11-EX`, not simulated
(`reports/evidence/remotion-previs-render-C-2026-09-11-EX.json` and
`…-receipt-….json`):

- command: `node studio/remotion/render.mjs --edl cards/edl/C-2026-09-11-EX.json --assets . --output <scratch>/render-ex.mp4 --browser "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"`
- output: 3,433,827 bytes; ffprobe reports `Duration: 00:01:00.05`, `h264 (High)`,
  `1080x1920 [SAR 1:1 DAR 9:16]`, `30 fps`;
- receipt: schema `m2.remotion-render-receipt.v1`, status `RENDERED_REVIEW_REQUIRED`, Remotion
  **4.0.520**, `duration_frames` 1800, `edl_sha256` `bfd8aa9a…`, `output_sha256` `0716c154…`,
  seven asset hashes, `provider_execution: false`, `downloaded_browser: false`;
- environment: macOS 14 (Remotion warns it is older than macOS 15), Node 22.20, Chrome from
  `/Applications`;
- a single frame at 12 s is kept as `reports/evidence/remotion-previs-frame-12s.jpg` (30,824
  bytes). The MP4 itself was left in the session scratchpad and is not committed.

---

## 8. Reports & documents

| Document | Path | Size |
|---|---|---:|
| Architecture | `docs/M2RADAR_CONTENT_ENGINE_ARCHITECTURE.md` | 684 lines |
| Database reconciliation | `docs/M2RADAR_DATABASE_RECONCILIATION.md` | 451 lines |
| Analysis method | `docs/M2RADAR_ANALYSIS_METHOD.md` | 816 lines |
| Notion dashboard | `docs/NOTION_DASHBOARD.md` | 148 lines |
| Production pipeline (Phase 3 runbook) | `docs/PRODUCTION_PIPELINE.md` | 276 lines |
| Testing | `docs/TESTING.md` | 109 lines |
| Data lifecycle | `docs/data-lifecycle.md` | 130 lines |
| Field dictionary | `docs/m2-field-dictionary.csv` | 65 Notion columns |
| Engine spec | `engine/SPEC.md` | 356 lines |
| Engine handoff notes | `engine/HANDOFF_NOTES.md` | 291 lines |
| Execution report | `reports/M2RADAR_INTEGRATION_EXECUTION_REPORT.md` | this file |
| Audits (6) | `reports/audit/00`…`05` | 271 / 811 / 773 / 613 / 388 / 355 lines |
| Analysis (11) | `reports/analysis/01`…`10-script-review-B` | 3,394 lines total |
| Migration log | `data/migration_log.md` | 159 lines |
| Migration validation | `reports/migration-validation.json` | 8,119 bytes |
| Notion dry plan | `reports/notion-sync-plan.md` | 567 lines |
| Report source (Parts A/B/C) | `reports/final/partA/`, `partB/`, `partC/` | 38 sections, 3,859 lines |
| Card book source | `reports/final/cardbook/` | 12 sections |
| **Analytical PDF** | `reports/final/M2RADAR_ANALYTICAL_REPORT.pdf` | **132 pages**, 4.50 MB |
| **Card book PDF** | `reports/final/M2RADAR_CARD_BOOK.pdf` | **105 pages**, 6.84 MB |
| Charts | `reports/charts/` | 18 PNG + 18 JSON + `index.json` |
| Report data bundles | `reports/data/` | 14 files |
| Statistics | `reports/stats/stats-2026-09-12.json` | 802,749 bytes |

Page counts read with PyMuPDF (`fitz`) on 2026-09-12.

---

## 9. Tests

### 9.1 Local environment (macOS, Python 3.10) — run for this report on 2026-09-12

**`python3 -m pytest -q`:**

```
252 passed, 1 skipped, 16 warnings in 26.03s
```

The single skip is by design (`tests/test_local_pipeline.py`, `slow` marker). The 16 warnings are
all one `PendingDeprecationWarning` from `engine/charts.py:224` (`vert=` on `ax.boxplot`).

**`python3 check.py`:** `ВСЁ СОШЛОСЬ (23 проверок)` — 23/23 health checks on `data/radar.db`
pass, including `sqlite integrity_check = ok`, `video_state = 3211` distinct codes, no orphaned
`beats` / `frame_labels` / `scenes`, no `jobs` without a run, providers registered, and spend
reconciling to `17.78` USD over 889 units. One known limitation is reported and deliberately not
counted as a discrepancy: 8 frames flagged `exists_ok=0` on `DcxV37-CJOC`.

**The 12 root test scripts** — every one printed `ТЕСТ ПРОЙДЕН`, 165 `✓` checks in total:

| script | checks | script | checks |
|---|---:|---|---:|
| `test_baseline.py` | 6 | `test_deep.py` | 16 |
| `test_roster.py` | 11 | `test_collect.py` | 19 |
| `test_topup.py` | 16 | `test_topics.py` | 9 |
| `test_posts.py` | 12 | `test_score.py` | 15 |
| `test_journal.py` | 10 | `test_pipeline.py` | 19 |
| `test_cards.py` | 20 | `test_notion.py` | 12 |

Grand total across the three suites: **441 collected** (253 pytest cases + 23 `check.py` + 165
root-script checks), of which **440 passed, 1 skipped, 0 failed**.

`docs/TESTING.md` states "242 pytest cases (241 passed + 1 skipped)" — that line is 11 cases stale
against today's 253; the suite grew after the doc was written. Worth a one-line fix.

### 9.2 Server staging environment

Reported by the orchestrator as **249 passed / 4 skipped** after the scipy fix. **This figure
could not be reproduced from this repository** — no server test log is committed and the server
is not reachable from this session; it is recorded here as supplied, not as verified.

The scipy fact behind the fix is in the repo: `engine/HANDOFF_NOTES.md` §6 ("Server / cron") —
*"`numpy`, `pandas` and `scipy` are used by `engine/stats.py` (`associations`, `report`,
`corpus.latest_metrics`) and are **not** needed for anything `cron.sh` calls today …
If a stats stage is ever added to `cron.sh`, guard it the way the other new stages are guarded so
a missing scientific stack never blocks the 13-step chain."* The one arithmetic check that can be
made from here: 249 + 4 = 253, the same number of cases the local run collects (252 + 1), so the
server run differs only by three extra skips and no failures.

---

## 10. Notion

`<<NOTION_RESULT>>`

What is verifiable from the repository at the time of writing:

- `engine/notion_sync.py` and `engine/notion_blocks.py` are implemented and covered by
  `tests/test_notion_sync.py`; `python3 test_notion.py` passes 12/12.
- The most recent dry plan is `reports/notion-sync-plan.md`, generated **2026-09-12T08:53:56Z**,
  scope `all`, mode **DRY (no writes made)**: dashboard body 169 blocks in 1 `append-children`
  call, engine 1.0.0, commit `92e71e7a0543`.
- `docs/NOTION_DASHBOARD.md` line 7 states plainly: *"As of this writing `engine.notion_sync` has
  only ever been run with `--dry`: it has made zero writes to Notion. `--apply` is implemented but
  has never been executed."*
- `data/notion_ids.json` — the idempotency cache that `--apply` writes on its first successful
  run — **does not exist**, which is consistent with `--apply` never having completed.
- The Notion apply log named in the brief
  (`…/scratchpad/notion-apply.log`) **does not exist on disk**, and no Notion process is running.

### The open decision — (a) or (b)

`docs/NOTION_DASHBOARD.md` §"Open decision", from audit §8.1:

- **(a)** Re-point `NOTION_REELS_DB` / `NOTION_ACCOUNTS_DB` at the richer Signal schema and
  migrate `notion_db.py`'s property mapping. Folds the two systems into one, but needs real
  migration code and a manual copy of the `Verdict` / `What to borrow` columns someone hand-added
  to the old Accounts DB — nothing in this repo writes those back.
- **(b)** Keep them separate: link the *existing* operational Reels/Accounts databases into the
  visible page tree so they are at least navigable, and relabel the Signal ones clearly as a
  one-off 2026-09-05 snapshot.

**This build implements (b)** per the brief that commissioned it. The doc is explicit that this is
a working assumption, not Misha's sign-off, and must be confirmed or overridden before `--apply`
runs for real.

Two operational database IDs are deliberately never hard-coded or printed by the module, its plan
output or its doc — only their *presence* in `.env` is reported as a boolean.

---

## 11. Server deployment

`<<SERVER_DEPLOY>>`

Verified context from `reports/audit/03-server-runtime-hiker.md` (read-only audit,
2026-09-11): `/opt/radar` on `m2vps` sits on branch `main` at `92e71e7a0543…`, clean tree, the
only untracked path being the git-ignored `.venv/`. **Server code == git main, exactly** — the
runtime gap is entirely in what is not in git (data 303 MB, cache 112 MB, the 509 MB venv), not in
code drift. Cron: `0 7 * * 1,4 /opt/radar/cron.sh` (Mon/Thu 07:00 server TZ). Hardware: 6 CPUs,
11 GiB RAM, 187 GB free — headroom for faster-whisper `small` int8 on CPU and ffmpeg frame
extraction, which is what the cron run uses. Server `.env` variable names match `.env.example`
exactly, permissions `600`.

---

## 12. Security

- **No secret is committed.** `git grep -nE "hiker_|HIKER|Bearer|x-access-key"` over `*.py`
  returns only environment-variable and header *names*; a scan for key-shaped literals
  (`x-access-key: <value>`, `secret_…`, `ntn_…`) over tracked files returns nothing.
- `.gitignore` blocks `.env` and `.env.*` with an explicit `!.env.example` exception; `git
  ls-files | grep -i '\.env'` returns exactly one path: `.env.example`.
- `.env.example` lists 15 variable names with empty values: `HIKER_KEY`, `LOORE_KEY`,
  `NOTION_TOKEN`, `NOTION_PAGE`, `NOTION_CARDS_DB`, `NOTION_REELS_DB`, `NOTION_ACCOUNTS_DB`,
  `OPENAI_API_KEY`, `HIGGSFIELD_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`,
  `SUPABASE_BUCKET`, `CLOUDFLARE_API_TOKEN`, `CF_R2_BUCKET`, `CF_PUBLIC_BASE_URL`.
- `.env` permissions are `-rw-------` (600) both locally and on the server.
- Paid API responses (`cache/`, `hiker-cache/`, `cache-free*/`), the database and frames (`data/`)
  are all git-ignored, so signed Instagram CDN URLs and third-party biographical data never leave
  the machine through git.
- **One item requires action.** During testing on **2026-09-11** a Notion token briefly appeared
  in one subagent's tool output. It was never written to a file and never committed, but a token
  that has been rendered once should be treated as exposed: **rotate `NOTION_TOKEN` as a
  precaution** and re-populate `.env` on the laptop and on `/opt/radar`. This is listed again as
  an open decision in §15.

---

## 13. Definition-of-done check (§97)

Legend: ✓ done · ◐ partial · ✗ not done.

| # | §97 requirement | Status | Evidence |
|---:|---|:--:|---|
| 1 | current database architecture is merged | ✓ | `python3 -m engine.schema --check` → "schema up to date"; 18 engine tables alongside 14 legacy tables in one `data/radar.db` |
| 2 | every relevant column is mapped and validated | ✓ | `docs/M2RADAR_DATABASE_RECONCILIATION.md` (451 lines, per-field source→canonical table); `docs/m2-field-dictionary.csv` |
| 3 | no useful main data is silently lost | ✓ | `data/migration_log.md` — every table delta `+0`; unmatched codes listed by name in `reports/migration-validation.json` `steps.august_archive.unresolved_codes` |
| 4 | current valid transcripts are exhaustively analyzed | ◐ | 266 of 268 usable transcripts analysed (`data/analysis/transcripts/` = 266 files, beats loaded for 264 codes); the 2,936 MISSING_TRANSCRIPT codes have no transcript to analyse |
| 5 | current valid frames/scenes are exhaustively analyzed | ◐ | 295 of 297 frame codes analysed (`data/analysis/frames/` = 295 files; `frame_labels` 2,645 rows across 295 codes) |
| 6 | transcript chapters, beats, phrases, lexical features persisted or reproducibly generated | ✓ | `beats` 1,527 rows at `ta-v1`; `engine/lexical.py` (reproducible); `video_features` 3,211 rows at `fv-1` |
| 7 | scenes/cuts/A-roll/B-roll/split-screen/visual sequences measured where reliable | ✓ | `scenes` 960, `frame_labels` 2,645; `reports/data/visual_patterns.json` (206 distinct visual sequences over 295 codes) with an explicit caveat that the legacy cut metric is a scene-score threshold, not shot-boundary detection |
| 8 | current report separates ingested vs analyzed denominators | ✓ | Five named denominators in `engine/corpus.py`, `docs/M2RADAR_ANALYSIS_METHOD.md` §1.1, and restated at the top of every analysis document |
| 9 | newest Hiker-only reels excluded from false transcript/frame conclusions | ✓ | The 2,914 INGESTED_NOT_ANALYZED codes are a separate tier and are never inside `N_ready`; §4.4 above |
| 10 | newest Hiker-only reels queued for the post-merge watchdog | ◐ | `engine/watchdog.py` exists and targets exactly this set (1,312 codes); it has **not been run** against the live corpus |
| 11 | Hiker architecture is in Git without the key | ✓ | `reports/audit/03-server-runtime-hiker.md` §1; `.env.example`; §12 above |
| 12 | local transcription is canonical | ✓ | `local-faster-whisper` = DEFAULT + CONFIGURED; 273 of 281 `transcript_meta` rows carry `asr_version = faster-whisper-small-int8-v1` |
| 13 | local frame processing is canonical | ✓ | `local-ffmpeg-scenes` = DEFAULT + CONFIGURED; `engine/scenes.py` uses bundled `imageio_ffmpeg` |
| 14 | Loore/Lure is optional only | ✓ | `providers` row: `loore … OPTIONAL_PROVIDER … DISABLED`, "never required for the default path" |
| 15 | normalized engagement metrics exist | ✓ | `video_features.like_rate / comment_rate / share_rate / save_rate / hi_intent_rate` over 3,211 rows |
| 16 | creator-relative metrics exist | ✓ | `view_lift`, `share_rate_lift`, `save_rate_lift`, `robust_z`, `percentile_in_creator`, `creator_median_play`, `creator_consistency`; `creator_stats` 132 rows |
| 17 | cross-metric analysis exists | ✓ | 460 correlation pairs, 13 RELIABLE — `reports/stats/stats-2026-09-12.json`, `reports/data/associations.json` |
| 18 | strong-vs-weak comparisons exist | ✓ | `reports/analysis/04-strong-vs-weak.md`; 115 numeric features tested, n_strong 74 / n_weak 74 (`reports/data/visual_patterns.json`) |
| 19 | insights are numerical and evidence-grounded | ✓ | 30 `insights` rows each carrying `metric`, `n`, `comparison`, `evidence_json`, `supporting_codes_json`, `limitations` |
| 20 | hypotheses are explicit | ✓ | 24 rows in `hypotheses` with scores, strengths, risks, novelty, reviewer comment, status |
| 21 | references are hypothesis-specific | ✓ | 41 `hypothesis_refs` rows, all bound to a selected hypothesis (5 + 9×4); no global pool |
| 22 | scripts are original transformations | ✓ | Each card's `traceability` and `references[].transformation` name what was borrowed as shape and what was rewritten; the two reviewer passes checked this and logged 107 findings |
| 23 | cards are frame-aware | ✓ | 70 `card_scenes` rows, 70 rendered scene frames, 10 EDLs validating `EDL_OK` |
| 24 | main visual patterns are identified | ✓ | `reports/analysis/03-visual-patterns.md`; `reports/data/visual_patterns.json`; charts `visual_sequence_top10`, `a_roll_share_vs_performance`, `split_share_vs_performance` |
| 25 | Notion `Content Engine Tool` is current and navigable | ✗ | Dry plan only (`reports/notion-sync-plan.md`, 2026-09-12T08:53:56Z); `--apply` not observed to complete; `<<NOTION_RESULT>>` |
| 26 | stale/legacy dashboard information cleaned/archived | ✗ | Planned in `docs/NOTION_DASHBOARD.md` (Legacy section, old children archived not deleted) but not executed |
| 27 | reel/account/run/card/category subpages/views linked | ✗ | Seven new databases (Runs, Insights, Hypotheses, Cards v2, Reels analysis, Accounts analysis, Categories) are defined in the plan and created only on `--apply` |
| 28 | supplied MP4 parameters are defined | ✓ | `docs/PRODUCTION_PIPELINE.md` §1 take sidecar contract (`scene_id`, `shot_type`, `roll`, `in_s`/`out_s`, fps, resolution, orientation, audio quality, sync notes); `engine/production.py`; `tests/test_production.py` |
| 29 | Remotion flow is defined/testable | ✓ | `engine/edl.py` + `studio/remotion/`; 10 × `EDL_OK`; one real 60.05 s 1080×1920 render with a hashed receipt (§7.4) |
| 30 | Supabase final video storage is prepared | ◐ | `engine/storage.py` implements Supabase-canonical with local fallback; provider state NOT_CONFIGURED (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY` unset) — prepared, not connected |
| 31 | Cloudflare's downstream role is defined | ◐ | `docs/M2RADAR_CONTENT_ENGINE_ARCHITECTURE.md` §12.4 defines it as public delivery only; `CloudflareDelivery.public_url()` reads `CF_PUBLIC_BASE_URL`, which is a stub and unset |
| 32 | all critical tests run | ✓ | 441 collected across three suites, 440 passed, 0 failures (§9.1); server figure unverified (§9.2) |
| 33 | fixable issues are solved | ◐ | 107 reviewer findings addressed; the scipy guard is documented; `docs/TESTING.md`'s pytest count and `reports/data/manifest.json` / `runs_jobs.json` are stale and were not regenerated |
| 34 | reports are clear, numerical, and argumented | ✓ | 38-section analytical report (132 pp) + card book (105 pp) + 11 analysis documents, every claim carrying its n and its denominator |
| 35 | all work is committed and pushed to main before Phase 2 begins | ✗ | `git log main..content-engine` is empty; 46 uncommitted paths in the working tree; `<<COMMIT_HASH>>` |

Score over the 35 bullets: **25 ✓ · 6 ◐ · 4 ✗**.

---

## 14. Limitations & unresolved blockers

1. **8.3 % coverage, and it is not a random 8.3 %.** Every structural conclusion rests on 268 of
   3,211 codes, selected as the top of `score.py`'s own ranking. Median `robust_z` inside the
   analysed tier is +1.26 against 0.00 overall. Absent contrasts are not evidence a feature is
   irrelevant; present contrasts are probably understated.
2. **Nothing is committed.** `git log main..content-engine` returns zero commits; 46 paths are
   uncommitted. Until the orchestrator commits and pushes, none of this is deployable and
   `<<COMMIT_HASH>>` cannot be filled.
3. **Notion has never been written to.** `--apply` has not been observed to complete;
   `data/notion_ids.json` does not exist; §97 items 25–27 are unmet.
4. **1,312 newest-snapshot reels are unprocessed** and their cached CDN URLs have largely expired,
   so `engine/watchdog.py` will only recover the subset whose cached `clips*.json` still resolves.
   The rest need a fresh paid Hiker call.
5. **The legacy cut metric is not a cut count.** `cut_metric_quality =
   ffmpeg_scene_0.35_count_only` is a scene-score threshold count over 282 codes; it is a relative
   "busy vs calm" signal inside this dataset only and must never be quoted as an edit rate.
6. **Two corpus-tier vocabularies coexist** (`engine.corpus.tiers()` vs `video_state.corpus_tier`,
   FRAMES_ONLY 22 vs 29). They must never be mixed inside one report, and no single number has
   been declared canonical.
7. **266 vs 268 vs 264.** The narrative documents say 266, `engine.corpus` says 268, and beats
   exist for 264 codes. All three are right for what they count, but the reports do not currently
   carry that reconciliation inline (§4.1).
8. **Max's 1,062 transcripts and 19,808 frames are not in git** on either branch and could not be
   reconciled into this database. They need an export in a receipt format.
9. **The `followers` table and `our_posts` / `our_metrics` are empty.** No claim about creator
   growth, or about M2's own publishing performance, is possible from this corpus. Zero of the 33
   reviewed cards has ever been shot.
10. **`deepdives.suitable` is NULL for every one of the 3,211 codes** and for all 23 legacy cards;
    only 4 of 282 `deepdives` rows have it set at all, all rejections dated 2026-09-01. The human
    fitness gate that `cards.py` filters on has effectively never fired.
11. **Saves are missing on 9–10 % of rows** by HikerAPI's own behaviour, not by design
    (`reports/final/partA/01-executive-summary.md`, Limitations).
12. **8 frame files are broken** on `DcxV37-CJOC` (truncated download), flagged `exists_ok = 0`.
13. **The requirements checklist was never ticked.** `reports/audit/00-requirements-checklist.md`
    tracks 185 requirements and all 185 are still `☐` — it served as a planning artefact, and §13
    of this report is the actual completion pass.
14. **Three generated artefacts are stale**: `docs/TESTING.md` (242 pytest cases vs 253 today),
    `reports/data/manifest.json` and `reports/data/runs_jobs.json` (both frozen at
    2026-09-11T22:26, showing `runs` 0 / `jobs` 0 / `cards_v2` 0), and
    `reports/final/partA/01-executive-summary.md`'s line that the state-tracing tables hold zero
    rows — they now hold 7 runs and 265 jobs.
15. **The server staging test result could not be verified** from this repository (§9.2).
16. **No causal claim is licensed anywhere.** Everything is associational, inside a pre-selected
    top-of-ranking sample.

---

## 15. Open decisions for Misha

1. **Two asks per card, or one?** `01-general-conclusions.md` §G rule 14 says one ask per CTA; the
   mandatory four-part filter requires a `next_action` *and* the card carries a CTA. Reviewer A
   flagged this as a direct conflict for every card in its batch — four of five ship with two
   asks (`reports/analysis/10-script-review-A.md` items 2 and 418–419). Decide: drop the CTA and
   let `next_action` be the only ask, drop `next_action` from the spoken script and keep it as
   caption/pinned-comment copy, or accept two asks and retire rule 14.
2. **Notion: (a) or (b)?** Confirm (b) — keep the operational and Signal databases separate and
   link both into the page tree — or switch to (a) and fund the migration of `notion_db.py`'s
   property mapping plus the hand-added `Verdict` / `What to borrow` columns. `--apply` should not
   run for real until this is answered (§10).
3. **Do the four Builds cards stand, framed on our own pipeline?** H-11, H-12, H-13 and H-18 are
   all instrumented inside our own research pipeline, which PRODUCTION.md already names as the gap
   ("everything we have measured so far is our own tooling, which is not what the audience runs on
   a Monday"). The mitigation was to pick four *different generic work steps* — triage, extraction,
   sign-off, retirement — each naming its ordinary-business equivalent. Accept that, or hold the
   Builds slots until a real business process has been taken apart.
4. **Pay to re-fetch the 1,312 unprocessed reels?** At the observed HikerAPI unit price of $0.02
   per request (`spend` table, 889 units → $17.78 to date), a re-fetch of 1,312 reels is on the
   order of **$26** before transcription and frame extraction, which are free and local. That is
   over the $5-per-task ceiling, so it needs an explicit yes. The alternative is to run
   `engine.watchdog` first — it is free — and see how many still resolve from cache.
5. **Rotate the Notion token?** A Notion token briefly appeared in one subagent's tool output on
   2026-09-11 (§12). Nothing was committed, but the recommendation is to rotate it and re-populate
   `.env` locally and on `/opt/radar`. Yes or no.
6. **Keep `deepdives.suitable` as a mandatory gate?** It is NULL for all 3,211 codes and all 23
   legacy cards; only 4 rows have ever been set. Either commit to filling it before an angle is
   written (as RULES.md §2а already requires on paper, and as
   `reports/analysis/07-existing-cards-verdict.md` item 3 recommends), or drop it from `cards.py`'s
   filter and stop pretending there is a human fitness check.

---

## 16. Final execution summary (§50)

| Field | Value |
|---|---|
| Repository | `/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar` · `origin` = `git@github.com:MickaelAmpl/m2lab-radar.git` |
| Main branch | `main` @ `92e71e7a0543bacce2adafd65941eaa008632d62`, equal to `origin/main` |
| Pushed commit hash | `<<COMMIT_HASH>>` |
| `latest` intact | Yes — `origin/Latest` = `31ed2d41aea62b97959d8e22b01d30a62834ba02`, never written to; sync state vs `max/main` (`6462f409…`): `<<LATEST_SYNC>>` |
| Creators analyzed | 132 with reels (of 1,357 accounts; 130 active) — `creator_stats` 132 rows |
| Videos analyzed | 3,211 unique codes ingested (5,147 readings); 268 analysis-ready |
| Transcripts analyzed | 266 ta-v1 analyses over 268 usable transcripts (275 transcript rows, 7 empty); beats loaded for 264 codes |
| Transcript coverage | 268 / 3,211 = **8.3 %** usable; 266 / 3,211 = 8.3 % analysed |
| Frames analyzed | 295 fa-v1 analyses; `frame_labels` 2,645 rows; `frames` 2,727 rows over 297 in-corpus codes (303 including 6 orphans); `scenes` 960 |
| Frame coverage | 297 / 3,211 = **9.2 %** with frames; 295 / 3,211 = 9.2 % analysed |
| Cards reviewed | 33 (23 legacy `cards` rows on main + Max's 10-card release) |
| Scripts reviewed | 33 legacy/fork scripts audited, plus the 10 new scripts reviewed twice (107 findings) |
| Luna outputs reviewed | **0 — no Luna run exists.** Searched across this tree, `origin/Latest`, `max/main`, all history and the whole project disk. "Luna" is a model-preference label inside Max's config, not a run (`reports/audit/04-existing-cards-review.md` §D) |
| New cards generated | 10 (`cards_v2` = 10) |
| New scripts generated | 10 (`script_versions` = 20 rows, two per card) |
| New frame plans generated | 10 storyboards, 70 scenes (`card_scenes` = 70) |
| Frame images generated | 80 for the new cards (70 scene frames + 10 contact sheets); 88 PNGs in `cards/frames/` including the example card |
| Providers used | `local-faster-whisper` (CONFIGURED, 273/281 transcripts), `local-ffmpeg-scenes` (CONFIGURED), `remotion` (CONFIGURED, one real render), `hiker` (historically — 889 paid units, $17.78) |
| Providers configured but unavailable | `hiker` NOT_CONFIGURED in this environment; `loore` DISABLED; `supabase`, `cloudflare`, `openai`, `higgsfield` NOT_CONFIGURED |
| Tests passed | **440** locally — pytest 252, `check.py` 23, root scripts 165; plus 1 pytest skip, 441 collected. Server staging reported 249 passed / 4 skipped (253 collected), unverified here |
| Tests failed | **0** |
| Database migration result | Success. `data/migration_log.md`: every table delta `+0`; `integrity_check ok`; 0 foreign-key violations; 0 pk violations; 6 unresolved archive codes logged by name, none dropped |
| Architecture document | `docs/M2RADAR_CONTENT_ENGINE_ARCHITECTURE.md` |
| Database mapping document | `docs/M2RADAR_DATABASE_RECONCILIATION.md` |
| Analytical method | `docs/M2RADAR_ANALYSIS_METHOD.md` |
| Execution report | `reports/M2RADAR_INTEGRATION_EXECUTION_REPORT.md` |
| Analytical PDF | `reports/final/M2RADAR_ANALYTICAL_REPORT.pdf` (132 pages) |
| Card PDF | `reports/final/M2RADAR_CARD_BOOK.pdf` (105 pages) |
| Structured cards | `cards/C-2026-09-12-01.json` … `-10.json`; EDLs in `cards/edl/`; DB tables `cards_v2` / `card_scenes` / `script_versions` |
| Main strategic findings | (1) Format is not the lever — of 115 numeric features none separates the top from the bottom `robust_z` quartile at p<0.01. (2) What the video controls is the save and the share, not the view — 11 of 13 RELIABLE correlations are save-rate correlations. (3) Put a screen on camera: `screen_share` → `share_rate` rho +0.203 is the only visual finding that survives creator normalisation on two metrics. (4) The comment gate contaminates our own selection — 59 % of the analysed corpus runs one, it moves reach not at all and moves exactly the two rates the radar ranks by. (5) M2's territory is genuinely empty and genuinely weak: business-process n=8 at 0.65× lift against agent-building n=27 at 6.63× |
| Limitations | See §14 (16 items). Headline: 8.3 % coverage over a pre-selected top-of-ranking sample; two disagreeing tier vocabularies; the legacy cut metric is not a cut count; `followers` / `our_posts` empty; no causal claim licensed |
| Unresolved technical blockers | Nothing committed or pushed (`<<COMMIT_HASH>>`); Notion `--apply` not completed (`<<NOTION_RESULT>>`); server deployment (`<<SERVER_DEPLOY>>`); 1,312 reels unprocessed with expired CDN URLs; Max's 1,062 transcripts / 19,808 frames not in git; `deepdives.suitable` NULL corpus-wide |
