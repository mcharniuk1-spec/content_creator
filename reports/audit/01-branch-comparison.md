# M2Radar — branch architecture audit: `main` vs `origin/Latest` vs `max/main`

Auditor: repository-architecture pass, 2026-09-11. All claims below are backed by commands actually run
(git reads, code reads, test executions, and a full end-to-end execution of `origin/Latest` against the real
production database mirror). Where something could not be verified it is marked **UNVERIFIED**.

---

## Summary (read this first)

1. `origin/Latest` is **not a fork of current `main`** — it branches at `02102dd1` and never received main's
   last 17 commits (design system, `prompts/angles.md` rewrite, `deep.py`/`cards.py` fixes, audit, runs).
2. Max **did not touch main's engine**: `db.py`, `deep.py`, `collect_snapshot.py`, `blocks.py`, `score.py`,
   `baseline.py`, `cards.py`, `notion.py`, `notion_db.py`, `lib/hiker.py` are byte-identical on both branches.
3. He **did replace `run.py` and neutralize `install-cron.sh`** — merging Latest as-is silently breaks the
   `/opt/radar` cron pipeline. This is the single highest-risk collision.
4. Latest adds ~20,000 LOC in `m2_signal/` (release/observation ledger), `m2_orchestrator/` (41-stage DAG,
   hash-linked event log, bounded media workers), `m2_studio/` (timeline/provider escrow), `studio/remotion/`.
5. Latest's code **does run end-to-end on main's real DB** — I ran it. `m2_signal/legacy.py` exports a
   completed snapshot, then the 12 deterministic stages complete: `PASS_WITH_LIMITATIONS`, 1535 reels, 129 accounts.
6. But it stops there: **29 of 41 stages have no code**, they are agent/human handoffs. And it returns
   `final_best_reels: 0` — by design it refuses to name winners without media/scene/rights evidence.
7. Tests: Latest `tests/` = **367 passed, 2 failed, 1 skipped** (pytest 9.1.1, Python 3.10). The 2 failures are
   real, at Latest's tip, in `scripts/run_m2_transcription_recovery.py:144`.
8. Max's own gate `scripts/test_local.py` **fails out of the box** (needs pytest, which is not in his
   requirements file) and only covers 7 of 32 test modules.
9. Main: `check.py` 14/15 pass; test scripts **145/153 checks pass**. All 8 failures are fixture coupling to
   live DB state, not code defects — main's tests run against a copy of the production database.
10. Max's 1062 transcripts and 19,808 frames are **not in git** on either branch. Confirmed by full tree scan.
11. `max/main` adds only one commit: two reports (md+pdf) and `scripts/build_m2_reconciled_pdf.py`. No code.
12. Statistics verdict: **main's `score.py` is stronger** (age bands, focal-row exclusion, cross-snapshot
    baseline). Latest's `metrics.py` is honest about its own weakness — it includes the focal row.
13. Recommendation: keep main relational DB as source of truth; port the **state DAG, scene contract,
    Remotion EDL contract, provider catalog, bounded media workers**; leave `m2_signal` ledger as a read-side
    projection, not a replacement schema.
14. Storage gotcha: one snapshot in `signal.sqlite` = **24 MB** vs main's whole 3-snapshot DB at **5.2 MB**.
15. Portability gotcha: Latest calls bare `ffmpeg` from PATH; main uses bundled `imageio_ffmpeg`. Latest's
    OCR is a **Swift/Apple Vision** binary — macOS only, will not run on the Linux server.

---

## 0. Method and environment

| Item | Value |
|---|---|
| Repo | `/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar`, branch `content-engine` (= `main`, HEAD `92e71e7a`) |
| Refs read | `main`, `origin/Latest`, `max/main` — read-only via `git show` / `git ls-tree` / `git diff`. No checkout, no state change. |
| Merge base | `02102dd1013b9ed1736b01d8cda8b62563575a14` |
| Latest extracted to | `…/scratchpad/latest-tree` via `git archive origin/Latest \| tar -x` |
| Main extracted to | `…/scratchpad/main-run` via `git archive main \| tar -x` |
| Test DB | `data/server-mirror/radar.db` (5.2 MB) copied into the sandbox as `data/radar.db` |
| Python | macOS system Python **3.10.4**; a venv in the scratchpad with **pytest 9.1.1** |
| Node | present (Max's `test_local.py` ran the Remotion contract test: `PASS`) |
| FFmpeg | **not on PATH** — one Latest test skipped for this reason |

**Important environment finding.** The working copy has **no live `data/radar.db`**. The only real data locally
is `data/server-mirror/radar.db`. The file `data/radar.db` (0 rows, 140 KB) was *created by my own `check.py` run*
at 17:54 — it did not exist before. Two further byproducts of the requested test run: `data/candidates.md` and
`data/radar.notion-test.db`. All three are inside the gitignored `data/` directory. I did not delete them
(deletion is not mine to decide); flag them to Misha if he wants them gone.

Verified row counts in the mirror, matching the brief exactly:

```
accounts 1357 · snapshots 3 · reels 5147 · scores 7477 · deepdives 282
frames 2653 · transcripts 273 · topics 2482 · cards 23 · spend 10 · tool_log 37
our_posts 0 · our_metrics 0 · followers 0 · (15 tables incl. sqlite_sequence)
```

Snapshots: `2026-09-01` (2363 reels, done), `2026-09-07` (1260, done), `2026-09-10` (1535, done).

---

## 1. What exists where

### 1.1 Commit topology

```
02102dd1 (merge base)
 ├── main:          17 commits → 92e71e7a   (design system, positioning, audit, runs, engine fixes)
 └── origin/Latest:  8 commits → 31ed2d41   (m2_signal / m2_orchestrator / m2_studio / remotion)
      └── max/main:  1 commit  → 6462f409   (outputs/reports/*.md|pdf + scripts/build_m2_reconciled_pdf.py)
```

Latest's 8 commits: `0e093ca8` Signal+Studio execution · `2af2456b` transcript benchmark + stage diagnostics ·
`385b37f1` retained Reel media workflow + state queue · `5891b504` offline transcript recovery + scene evidence ·
`91f3962e` retained-media recovery + structural feature exports · `73ed2f22` recovery overlays + ASR beam
configs · `4b771f78` ten-card slate + hash-bound writing guidance · `31ed2d41` ten-card editorial update.

### 1.2 Only in `main`

| Path | What it is |
|---|---|
| `design/` (~330 files) | Brand book v3, design system, tokens, fonts, Lucide icons, templates, research |
| `audit-2026-09-08/` | 8 Sep audit: plan, checks, Notion snapshot, PDF report toolchain |
| `runs/2026-09-07/` | Published week pages + card readouts |
| `dataset/` | `radar.db`, `radar-0907.db`, 2026-08 niche research JSON |
| `docs/archive-2026-09/` | HANDOFF, archived docs |
| `POSITIONING.md`, `PRODUCTION.md`, `RULES.md`, `SPEC.md` (current versions) | Editorial + engineering contract |
| `PRODUCTION.md` | Production contract; absent from Latest |

Note: **every root-level operational script is present on both branches** — `analyze.py`, `stats.py`,
`pages.py`, `delta.py`, `review.py`, `prune.py`, `harvest.py`, `judge_accounts.py`, `tag_candidates.py`,
`freeprofile.py`, `queries.py`, `journal.py`, `posts.py`, `roster.py`, `blocks.py`, `cards.py`, `deep.py`,
`score.py`, `baseline.py`, `notion.py`, `notion_db.py`, `db.py`, `check.py`, `collect_snapshot.py`,
`topics.py`, `tag_topics.py`, `lib/hiker.py`, all 12 `test_*.py`. Latest did not delete anything from main's
engine — it only failed to receive main's later edits to five of them (see 1.4).

`PRODUCTION.md` and `docs/archive-2026-09/` exist only on main. `START-HERE.md`, `PLAN.md`, `README.md`,
`RULES.md`, `SPEC.md`, `POSITIONING.md` exist on both but main's are newer.

### 1.3 Only in `origin/Latest`

| Directory | Files | LOC | Purpose |
|---|---:|---:|---|
| `m2_signal/` | 12 py + `schema.sql` + README | ~3,600 | Immutable release/observation ledger, descriptive metrics, eligibility gates, legacy bridge, Hiker adapter, transcript benchmark |
| `m2_orchestrator/` | 23 py | ~7,900 | 41-stage DAG controller, hash-linked events, media acquisition/transcription/visual/OCR/recovery, Notion projection outbox, diagnostics |
| `m2_studio/` | 7 py + `provider-catalog.json` | ~1,100 | Media primitives, scene alignment, EDL timeline builder, provider job escrow |
| `studio/remotion/` | 8 files (mjs/tsx/ts/json) | — | Deterministic 9:16 renderer, EDL validation contract, storyboards |
| `tests/` | 32 modules | ~4,400 | Unit tests for the above |
| `scripts/` | 5 py + 1 swift | ~500 | Run entrypoints, corpus media, transcription recovery, Apple Vision OCR |
| `schemas/` | 2 json | — | `m2-corpus-field-dictionary.v1.json` (43 fields), `video-scene-segmentation.schema.json` |
| `config/` | 7 json templates | — | Metrics, stage policy, Hiker approval/pilot templates, server media/replay |
| `docs/` | 18 files | — | System architecture, operator guide, field dictionary CSV, provider assessment, review receipts |
| `knowledge/` | 11 md/json | — | Positioning, operating memory, validation lessons, studio editorial findings |
| `agents/`, `skills/` | 1 json + 3 SKILL.md | — | Role registry; `m2-script-writer`, `m2-stage-worker`, `humanize-writing` |
| `examples/ten-card-20260907/` | 12 json + 10 png | — | Reviewed ten-card slate with storyboards and hashes |
| `integrations/radar/` | server_entry + configs | — | Duplicate of root `server_entry.py` (see risk 6.3) |
| `hiker_server.py`, `server_entry.py`, `AGENTS.md`, `requirements-m2-media.txt` | | | |

### 1.4 Files present on both but diverged

I checked each shared file for which *side* changed it since the merge base:

| File | main since base | Latest since base |
|---|---|---|
| `run.py` | unchanged | **42+ / 146−  (rewritten)** |
| `test_pipeline.py` | unchanged | **159+ / 53−  (rewritten)** |
| `install-cron.sh` | unchanged | **9+ / 14−  (neutered)** |
| `prompts/angles.md` | 61+ / 21− | unchanged |
| `tag_candidates.py` | 8+ / 6− | unchanged |
| `test_deep.py` | 12+ / 4− | unchanged |
| `deep.py` | 18+ / 2− | unchanged |
| `cards.py` | 26+ / 4− | unchanged |
| `db.py`, `collect_snapshot.py`, `blocks.py`, `score.py`, `baseline.py`, `notion.py`, `notion_db.py`, `check.py`, `lib/hiker.py` | **identical** | **identical** |

**This is the most important structural fact in the audit.** Max built *alongside* main's engine, not on top
of it. There are only three real conflicts: `run.py`, `test_pipeline.py`, `install-cron.sh`.

### 1.5 What `max/main` adds

One commit, `6462f409`, 543 insertions:

- `outputs/reports/m2-20260911-execution-architecture-report.md` + `.pdf`
- `outputs/reports/m2-20260911-reconciled-analysis-and-cards.md` + `.pdf`
- `scripts/build_m2_reconciled_pdf.py` (31 lines)

**No executable engine change.** The architecture report states the authoritative run has 2,352 canonical
Reels, 1,201 retained videos, 1,062 non-empty transcripts, 1,194 frame sets, 34 accepted structural records.
2,352 is the row count of `dataset/radar.db` — i.e. **Max's work is anchored to the 2026-09-01 snapshot**,
while main has since moved to 2026-09-10 with 5,147 reel rows across three snapshots.

### 1.6 Max's ASR and frame outputs are NOT in git — confirmed

Full tree scan of both `origin/Latest` and `max/main` for `transcript|frame|asr|.local|outputs|.jsonl|whisper`
returns **only source modules, tests and documentation**. There is no `.local/`, no `runs/20260906-media-
acquisition-v1/`, no `pilot-controller-r1/`, no `structural-feature-checkpoints/`, no transcript JSONL, no
frame archive. His report references all of these paths; none are committed.

Consequence: **his 1,062 transcripts and 19,808 frames cannot be recovered from the repository.** They exist
only on his machine. If we want them, he must export them — ideally through `m2_signal`'s own hash-bound
receipt format so provenance survives the transfer.

---

## 2. Capability-by-capability comparison

Verdict legend: **M** = main stronger · **L** = Latest stronger · **=** = complementary, keep both.

### 2.1 Hiker data acquisition + normalization — **M**

- **main**: `lib/hiker.py` (293 lines) is a working cached client — disk cache keyed per snapshot date, real
  price read from the `x-hiker-info` response header, curl transport (Python SSL is broken on this Mac),
  rate limiting at 15 req/s. `collect_snapshot.py` (117 lines) writes a snapshot row, validates every code
  through `db.safe_code()`, records spend, marks `done=1` only on completion, and shards the cache by date —
  with a comment explaining that without the date shard, snapshot #2 silently returned snapshot #1's data
  for 100 of 109 accounts.
- **Latest**: `m2_signal/hiker_adapter.py` (347 lines) + `hiker_server.py` (61 lines) are a *gated plan*, not
  a collector. Its own docstring: *"This module has only fixture execution proof; LIVE_SCHEMA_UNVERIFIED."*
  Default mode is `PLAN_ONLY`; `--execute` requires `--private-dir`, an approval file, and a dated
  `price_receipt_sha256`. It has never made a live call.
- **Verdict**: main owns collection. Latest contributes one genuinely good idea — the cost-ceiling +
  price-receipt + approval-hash preflight (`validate_collection_config`, lines 28–60) — which is worth
  porting into `collect_snapshot.plan()` as a hard spend gate.

### 2.2 SQLite schema: relational vs JSON-payload registry — **M** for truth, **L** for provenance

- **main** `db.py` (243 lines): 14 normalized tables, foreign keys ON, purposeful indices, and an `ADDED`
  migration list that back-fills columns on old databases (`db.py:214–228`). Every column has a Russian
  comment explaining *why* it exists. This is a real operational schema.
- **Latest** `m2_signal/schema.sql` (48 lines): 10 tables, all content held as `payload_json` with
  `CHECK(json_valid(...))`. Immutable release identity (`releases.corpus_sha256` / `config_sha256` /
  `implementation_sha256`), content-addressed `sources`, per-metric `metric_observations` with
  `observation_state` and `reason_code`, and `reel_metric_values` with `formula_version`.
- **Measured cost**: replaying one snapshot (1,535 reels) produced a **24 MB** `signal.sqlite` — 2,816
  observations, 7,675 metric observations, 18,420 metric values, 10,745 evidence attempts. Main's *entire*
  three-snapshot database with 5,147 reels is **5.2 MB**. That is roughly a **15× storage cost per snapshot**.
- **Verdict**: main's relational schema stays canonical. Latest's contribution that matters is not the tables
  but the three ideas inside them: **(a)** a per-metric `observation_state` + `reason_code` instead of NULL,
  **(b)** `formula_version` stamped on every computed value, **(c)** a release identity that hashes config +
  implementation. All three can be added to main as columns without adopting the payload registry.

### 2.3 State tracing / job states — **L, decisively**

- **main**: none. The pipeline is a linear script (`run.py`, 13 numbered steps). If step 7 dies, you rerun
  from step 1. There is a `tool_log` table for human notes, but no machine state.
- **Latest**: `m2_orchestrator/policy.py` declares **41 stages** with explicit `role` and `requires`
  dependencies. `m2_orchestrator/state.py` (377 lines) provides a `Controller` over a `state.sqlite` with
  four tables — verified by running it:

  ```
  run(1)        id, config, hash, policy_hash
  stages(41)    id, state, actor, attempt, token, lease_until, error, receipt
  events(25)    seq, payload, previous, hash UNIQUE      ← hash-linked append-only chain
  approvals(0)  gate, subject_hash, actor, expires, revoked
  ```

  Stages take a **lease** with a token and heartbeat, so a crashed worker is recoverable; `begin()` returns
  `cached: true` for already-finished stages, so reruns are idempotent. `trace-verification.json` from my run:
  `{"state": "PASS", "events": 25, "head": "2491b6f4…"}` — the chain verifies.
  `implementation_manifest()` (`state.py:39–53`) hashes every `.py/.sql/.json/.mjs/.ts/.tsx/.md` under the
  four packages plus the config/knowledge files, so a checkpoint knows which code produced it.
- **Verdict**: **this is the single most valuable thing on Latest.** Port it.

### 2.4 Local transcription — **=** (main works today, Latest is right long-term)

- **main** `deep.py:107–124`: `WhisperModel('small', device='cpu', compute_type='int8')`, `language='en'`
  forced (comment: auto-detection lies on accents), `vad_filter=True`, segments stored as JSON in
  `transcripts.segments`. 30 lines. **It produced the 273 transcripts we actually have.**
- **Latest** `m2_orchestrator/media_transcription.py` (616 lines) + `transcription_chunk_worker.py` (531) +
  `transcription_recovery.py` (790): a hash-validated frozen model bundle (`validate_model_bundle`, requires
  a `model-hash-manifest.json` in the model directory), a bounded isolated child process with wall-clock,
  stdout/stderr, RSS watchdogs (1.5 GB ASR / 512 MB FFmpeg), windowed chunking with resumable run manifests,
  and explicit failure codes (`AUDIO_DECODE_FAILED`, `AUDIO_WINDOW_EMPTY_UNVERIFIED`).
  `m2_signal/transcript_benchmark.py` (669 lines) scores ASR quality.
- **Reality check**: Latest's path calls bare `"ffmpeg"` from PATH and needs a pre-downloaded, hash-manifested
  model directory. Main uses `imageio_ffmpeg.get_ffmpeg_exe()` — a bundled binary with no system dependency —
  and lets `faster-whisper` fetch `small` itself. **On this Mac, FFmpeg is not on PATH and one Latest media
  test skipped for exactly that reason.**
- **Verdict**: keep `deep.py` running. Port the **watchdogs, chunking and typed failure codes** into it —
  those solve real problems (a stuck ASR currently hangs the whole cron run). Do not adopt the frozen-model-
  bundle requirement until someone actually builds and hosts the bundle.

### 2.5 Frame / scene extraction — **L on correctness, M on shipping**

- **main** `deep.py:97–101` (timecodes) and `deep.py:126–175` (run): 9 frames at fixed timecodes (`0.4, 1.2, 2.4, 4.0` dense in the hook,
  then 5 evenly spaced), a 3×3 `tile` contact sheet, and cut counting via
  `select='gt(scene,0.35)',showinfo` counting `pts_time:` matches. Video deleted after processing (SPEC §4.4).
  Frames are extracted with `-ss <t> -i` — an approximate seek.
- **Latest** `media_visual.py` (293), `scene_media.py` (269), `media_ocr.py` (49):
  - Decodes the **PTS list** and extracts frames by **decoded frame index**, so a frame is bound to an exact
    presentation timestamp, not an approximate seek.
  - Separates *cut candidate* from *shot* from *semantic scene* — the module docstring says so explicitly:
    *"FFmpeg scene events are cut candidates; they are not shots or semantic scenes."* Main conflates these.
  - `MIN_CUT_SEPARATION_MS = 120` debounce; budget caps (`MAX_FRAMES=48`, `MAX_DURATION_MS=180_000`).
  - Every frame carries the source media SHA-256; symlink-ancestor rejection on output paths.
  - `scene_media.py` maps reviewed 2/4/6-sample scene plans onto the retained PTS list and does **one bounded
    indexed decode** for the union of requested indices.
  - **Never deletes the source video** — the opposite of main's policy.
  - `media_ocr.py` shells out to `scripts/m2_vision_ocr.swift` (Apple Vision). **macOS only — dead on the
    Linux server.**
- **Verdict**: the PTS-indexed extraction and the cut/shot/scene distinction are genuine improvements and
  should be ported into `deep.py`. The OCR path is a Mac-only side quest — leave it as reference.

### 2.6 Transcript segmentation / blocks — **M**

- **main** `blocks.py` (75 lines): hook = first 5 s, tail = last 15% but ≥6 s, body = the rest, with a
  documented squeeze rule so short reels still have a body (`hook_end = min(5, dur*0.3)`). The boundaries are
  justified by main's own frame sampling. It is simple, it works, and it is already consumed by `analyze.py:51`, `notion.py:90` and `pages.py:187`.
- **Latest** `m2_signal/structural_features.py` (656 lines): consumes *externally produced, human-reviewed*
  annotations (`m2.transcript-structure-annotation.v2`) with labels
  `hook / body / mechanism / proof / implication / CTA / unclear`, and admits them only with verdict
  `ACCEPT_WITH_LIMITATIONS_FOR_BOUNDED_STRUCTURAL_ANALYSIS`. **It does not segment anything itself** — it is
  a hash-bound admission gate for someone else's labels.
- **Verdict**: these are not competitors. Main segments; Latest validates. The 7-label taxonomy is a better
  vocabulary than hook/body/tail and is worth adopting as an *extension* of `blocks.py`, but the 656-line
  admission machinery is premature for a two-person operation.

### 2.7 Topic taxonomy — **M, unambiguously**

- **main** `topics.py` (40 lines): 27 topics with regexes, derived from reading ~400 real captions ("выведены
  из чтения, а не придуманы заранее"). `tag_topics.py` (100 lines) tags the whole deepdive top plus a
  reproducible seeded random sample of 400, records the source (`manual` / `sample`), and names the
  unrecognized share explicitly.
- **Latest** `m2_signal/taxonomy.py`: a **single dict** mapping main's 27 Russian labels to English slugs,
  headed *"Legacy caption-only provisional labels; no inferred market eligibility."*
- **Verdict**: Latest adds a slug table and a disclaimer. Main owns the taxonomy. Take the slug map (useful
  for English-language outputs) and nothing else.

### 2.8 Statistics — **M on method, L on honesty**

| | main `score.py` + `baseline.py` | Latest `m2_signal/metrics.py` |
|---|---|---|
| Robust z | ✅ `0.6745*(x−med)/MAD`, clip ±5 | ✅ same, `z_scale=0.67448975`, clip ±5 |
| MAD floors | ✅ `MAD_FLOOR=0.05` relative, `LOG_MAD_FLOOR=0.10` for log-views, with a written note that the views component was being dropped for 41% of reels | ✅ same two floors, plus `rate_floor_absolute=0.10` |
| **Focal row excluded from its own baseline** | ✅ `score.py:85–96` — *"иначе выброс частично прячет сам себя"* | ❌ explicitly included; docstring admits *"includes the focal Reel in its Account baseline and therefore is NOT a predictive/causal estimator"* |
| **Age bands** | ✅ `AGE_BANDS=(7,30,90)`, with the measured justification: median ran 0.70× of the author's norm under 3 days and 1.54× over 3 months | ❌ none |
| **Cross-snapshot baseline** | ✅ `baseline.py` `LATEST` CTE takes each code at its newest snapshot across all history | ❌ single release only; *"no implicit cross-snapshot union"* |
| Two weight sets | ✅ `W_MAX` and `W_IG`, compared deliberately | ❌ equal-weight diagnostic mean only |
| Coverage / missingness | ⚠️ `axes` column counts components used | ✅ per-metric coverage, `observed_n`, reason codes, Wilson 95% CI on hit rate |
| Distributions | ⚠️ printed to stdout | ✅ `metric_distributions` with mean/median/q1/q3/IQR, persisted |
| Refuses to name a winner without evidence | ❌ ranks and ships | ✅ `final_best_reels: 0` when rights/text/scene gates unmet |

Measured from my live run on the 2026-09-10 snapshot:
`views median 18,285 · duration median 49.6 s · reshares/1k median 6.54 · saves/1k median 14.96
(coverage 0.902) · comments/1k median 4.28 · exposure-eligible 1,379 of 1,535`.

- **Verdict**: main's estimator is methodologically better and must stay. Latest's *reporting discipline* —
  coverage, reason codes, Wilson intervals, and a hard refusal to declare a winner on thin evidence — is the
  part to port. Concretely: add `coverage` + `reason_code` to `scores`, and add a `best_reel_eligibility_state`
  gate to `cards.py` so a card cannot be proposed off a reel with no transcript and no frames.

### 2.9 Cards / scripts — **=** (main ships, Latest has the better editorial contract)

- **main** `cards.py` (258 lines): three formats (`M2 Radar` / `M2 Builds` / `M2 Teardown`) each with its own
  ranking metric (`resh_1k` / `save_1k`), slot counts, and shot columns. Hard exclusion of 8 off-topic
  categories grounded in `POSITIONING.md §5/§8`, a `DEV_TOPICS` set that flags rather than excludes,
  `MIN_MULT=1.5`, `DUR_MIN/MAX = 20/120`, one card per author. Writes to the `cards` table; `prompts/angles.md`
  (rewritten on main, 61+/21−) drives the agent that fills `angle` and `hook`.
- **Latest** `skills/m2-script-writer/SKILL.md` + `m2_studio/` + `examples/ten-card-20260907/`: an 11-state
  ScriptCard pipeline (`BRAND_CONTEXT_BOUND` → … → `OWNER_CARD_APPROVAL_PENDING`) with a claim map
  classifying every line as recommendation / synthetic illustration / local observed fact / externally sourced
  claim, mandatory three-openings comparison, and a ten-card worked example with per-card SHA-256 and
  storyboard hashes.
- **Verdict**: main's *selection* is the working machine. Latest's *writing contract* is materially better
  than `prompts/angles.md` — especially the claim map and the "an internal experiment is not a client case"
  rules, which line up with Misha's own "never invent data" rule. Merge the editorial rules into
  `prompts/angles.md`; do not adopt the 11-state machine.

### 2.10 Notion sync — **M** (Latest cannot write)

- **main** `notion.py` (252 lines) actually pushes cards and **pulls decisions back** — status and comments —
  closing the feedback loop; `notion_db.py` (215 lines) publishes full Reels and Accounts databases. Transport
  is curl (documented: Python has no root certs on this Mac).
- **Latest** `m2_orchestrator/notion_payload.py` (116 lines) **performs no network writes at all** — its
  docstring says so. It builds a validated payload with hard failures on release mixing, duplicate reels and
  transcript hash mismatch, then `projection.py` (124 lines) plans the write.
- **Where Latest genuinely wins**: `projection.py` has an **owner-field guard** —
  `OWNER_FIELDS = {"Status", "Lead", "Priority", "Owner note", "Decision", "Presenter"}` are never overwritten
  by the engine, and `equivalent()` handles Notion's `1` vs `1.0` and empty-rich-text-as-NULL readback quirks.
  Main's `notion.py push` has no such conflict guard.
- **Verdict**: keep `notion.py`/`notion_db.py`. Port the `OWNER_FIELDS` guard and `equivalent()` — that is a
  real data-loss bug waiting to happen in main.

### 2.11 Remotion — **L (main has nothing)**

`studio/remotion/`: Remotion 4.0.520 + React 19.1.1, pinned with a `package-lock.json`. The value is
`contract.mjs` — `validateEDL()` enforces a **gapless partition** (`scene.from_frame !== previous` fails
`EDL_PARTITION_INVALID`; total must equal `duration_frames` or `EDL_COVERAGE_INCOMPLETE`), per-asset
`rights_approved` + `rights_receipt_id` + SHA-256, path traversal rejection, and in `production` mode refuses
placeholder layers, unbuilt graphics and pending audio. `alignmentPlanHash()` produces a versioned digest over
card hash, timebase, every stem's placement/trim/role/float64 gain and exact caption timing — with a Python
twin at `m2_studio.timeline.alignment_plan_hash`, so an approval cannot survive a changed plan.
Max's own `test_local.py` ran the contract test on this machine: **PASS**.

License note in the README: Remotion is free for ≤3 people; beyond that it needs paid licensing. Relevant —
M2 Lab is two people today.

### 2.12 Provider layer — **L (main has nothing), but the catalog is stale**

`m2_studio/providers.py` (266 lines): a SQLite job escrow with `DisabledTransport` by default, one submit per
logical request, **no blind retry** (a timeout may already have been charged), bounded poll budget, reservation
held on an ambiguous submit, and secret injection rather than storage.

`provider-catalog.json`: 4 models (`seedance2_5`, `veo3.1`, `veo3.1_fast`, `gen4.5`) with admitted durations
and ratios, all marked `PUBLIC_CAPABILITY_VERIFIED_LIVE_UNTESTED`, `execution_enabled: false`,
`price_receipt: null`, `live_quality_receipt: null`.

⚠️ **`"recheck_after": "2026-09-12"` — the catalog expires tomorrow.** No price has ever been verified. Any
claim about generation cost from this file is unbacked.

### 2.13 Tests — see §3 for numbers

- **main**: 12 hand-rolled scripts, no framework, each `shutil.copy(DB_PATH, TMP)` then asserting against the
  **live production database**. Human-readable Russian output, `✓ / ✗`, exits nonzero on failure.
  Architecturally fragile: the tests encode current data state (`HAVING COUNT(*)=24`, "17 accounts must drop").
- **Latest**: 32 pytest/unittest modules, 370 tests, fully synthetic fixtures, no DB dependency, 7 s runtime.
  Heavy emphasis on adversarial cases (`*_edges.py`, symlink attacks, hash mismatch, budget exhaustion).
- **Verdict**: Latest's testing approach is better in every respect *except* that it tests a system that has
  never run in production. Main's tests are coupled but they test the thing that actually generates cards.

---

## 3. Does Latest run end-to-end on the main DB? — **Yes, verified. But only 12 of 41 stages.**

### 3.1 The bridge exists and works

`m2_signal/legacy.py` (`import-legacy-db`) is a read-only adapter written against *"the field contract
inspected at pinned Radar commit 02102dd1"*. I ran it against the real mirror:

```
python3 -m m2_signal import-legacy-db \
  --source data/server-mirror/radar.db --output …/export --snapshot-date 2026-09-10
```

Result — **success**, receipt `signal-legacy-adapter.v1`:

```
source_rows 1535 · account_profiles 129 · transcript_records 212 · cut_summaries 85
artifacts: reels.csv (460 KB) accounts.csv (25 KB) transcripts.json (353 KB)
           topics.csv (79 KB) cuts.json (2 KB) snapshot.json
logical_export_sha256 b96a797df99d928e…
```

It opens the DB with `mode=ro` + `PRAGMA query_only=ON` in a single read transaction, requires
`snapshots.done = 1`, cross-checks `reels_n` against the stored row count, and **refuses to overwrite an
existing export directory with different bytes**. It deliberately does not import: `spend`, `tool_log`,
`cards`, `our_posts`, `our_metrics`, `notes`, or environment. It records five explicit limitations, including
that account profiles are current-state rather than historical.

### 3.2 The Signal replay runs

```
python3 -m m2_signal replay --source-dir …/export --output …/signal-out
→ state PASS_WITH_LIMITATIONS · release signal-445eb59e658ebaef2ed76f91
  canonical_reels 1535 · accounts 129 · exposure_eligible_reels 1379
  numeric_valid_reels 1535 · quarantined_reels 0 · identity_conflict_groups 0
  eligible_saves_observed 1244 / missing 135 · final_best_reels 0
  new_immutable_records 2816
```

15 output artifacts, 36 MB total, including `signal.sqlite` (24 MB), `candidate-ranking.csv`,
`evidence-attempts.jsonl`, `quarantine.jsonl`, `artifact-manifest.json`, `metrics-definition.json`.

Coverage as reported by the engine itself:

| Modality | Coverage | Dominant reason |
|---|---:|---|
| transcript | 13.8% (212/1535) | `NOT_PRESENT_IN_EXPORT` 1323; of the 212, 207 `LEGACY_ASR_PROVENANCE_AND_MEDIA_QA_UNVERIFIED` |
| cut_summary | 5.5% (85) | `COARSE_COUNT_ONLY_NO_TIMECODED_SHOTS` |
| frames / shots / semantic_scenes / source_media | **0%** | `MISSING_SOURCE_MEDIA` 1535 |
| comments | 0% | `NOT_PRESENT_IN_EXPORT` |

`evidence_release_accepted: false`, `final_best_reels: 0`. The engine produces a `top_candidates` list of 20
with `creator_view_index`, `descriptive_rank` and `diagnostic_equal_weight_z`, each stamped
`best_reel_reason: MARKET_RIGHTS_TEXT_SCENE_AND_INDEPENDENT_REVIEW_GAPS`.

Note the honest finding: main's `frames` table has 2,653 rows and `deepdives` 282, yet Latest reports **0%
frame coverage** — because `legacy.py` deliberately refuses to import frame paths as verified evidence
(*"Existing frame paths are not imported as verified frame evidence"*). That is a defensible position, but it
means Latest currently throws away work main has already done.

### 3.3 The orchestrator runs

```
python3 scripts/run_m2.py --source-dir …/export --run-dir …/run1 --run-id audit-001 --mode replay
→ {"run_id":"audit-001","completed_stages":12,"hikerapi_calls":0,"provider_calls":0,"notion_writes":0}
```

Stage outcomes from `status.json`:

| PASS | PASS_WITH_LIMITATIONS | NOT_STARTED |
|---|---|---|
| admit, freeze_config, inventory, collect_or_replay, snapshot_metrics | normalize, audit_all_rows, compute_baselines, rank_candidates, transcript_attempt, visual_attempt, comment_attempt | **29 stages**, including qualify_scope, transcript_segment, scene_segment, multimodal_fuse, review_signal, release_to_studio, write_script_cards, plan_scenes, project_notion, owner_gate, render_remotion, publish, learn, close_run |

`trace-verification.json`: `{"state":"PASS","events":25}` — the hash chain verifies.

### 3.4 What it needs vs what main has

| Entrypoint | Required input | Available from main? |
|---|---|---|
| `run.py` (Latest) | `--legacy-db` + `--snapshot-date`, or `--source-dir` | ✅ yes |
| `scripts/run_m2.py` | a directory of `.csv`/`.json`, no symlinks, ≤256 MB each | ✅ via `legacy.py` |
| `m2_orchestrator/__main__.py` | same controller, plus role task export | ✅ |
| `server_entry.py` | a server media config (`config/server-media.example.json`) | ⚠️ not configured |
| `hiker_server.py --execute` | private dir + approval file + `price_receipt_sha256` | ❌ no approval artifact exists |
| media stages | `--media-manifest`, `--network-media`, hash-pinned `yt-dlp`, `ffmpeg` on PATH | ❌ **none present**; FFmpeg not on PATH here |
| transcription | a model directory with `model-hash-manifest.json` | ❌ **does not exist anywhere in the repo** |
| `media_ocr` | `scripts/m2_vision_ocr.swift` compiled — Apple Vision | ❌ macOS only |

**Answer to the question as posed**: Latest does **not** need its own `.local/` exports to run the analytical
core — the legacy adapter is a real, working bridge. It **does** need out-of-repo artifacts (media manifest,
model bundle, approval files, yt-dlp, ffmpeg) for every media stage, and none of those exist in git.

### 3.5 Test results — Latest

Run from the extracted tree with a scratchpad venv (pytest 9.1.1, Python 3.10.4):

```
python3 -m pytest tests -q
→ 2 failed, 367 passed, 1 skipped, 30 subtests passed in 7.89s
```

- Skipped: `tests/test_m2_studio.py:94` — *FFmpeg unavailable*.
- **Failed (both real, both at Latest's tip):**
  - `test_transcription_chunk_worker.py::test_run_manifest_binds_rights_and_source_record`
  - `test_transcription_chunk_worker.py::test_cli_run_manifest_is_resumable_but_binding_mismatch_blocks`

  Cause: `scripts/run_m2_transcription_recovery.py:144` raises `ValueError("CONFIG_REQUIRED")` when
  `prepared["config"]` is absent, with the comment *"Compatibility belongs in callers' fixtures, never in the
  production manifest path."* The two test fixtures were never updated to supply `config`. This is a
  **stale-test defect, not a production defect** — introduced around `5891b504`/`73ed2f22`.

Without pytest (plain `unittest discover -p 'test_*.py'`): **120 tests ran, 22 import errors** — 22 of the 32
modules import `pytest` directly.

### 3.6 Max's own gate is broken

`scripts/test_local.py` runs `unittest discover -s tests -p 'test_m2_*.py'`, i.e. only **7 of 32** modules.
Executed with the system Python it **fails immediately**:

```
ERROR: test_m2_diagnostics_edges — ModuleNotFoundError: No module named 'pytest'
Ran 78 tests … FAILED (errors=1, skipped=1)
```

`pytest` is **not listed** in `requirements-m2-media.txt`. With pytest installed it completes:
`PASS_WITH_LIMITATIONS`, 3 legacy fixtures PASS (network + subprocess denied), Remotion contract PASS,
8 private-DB tests reported as *skipped, not passing* — an honest touch.

### 3.7 Test results — main

Sandbox: `git archive main` extracted, `data/radar.db` = copy of the server mirror, `data/frames` symlinked
from the repo.

`python3 check.py` → **14 of 15 checks pass**. The single failure is `кадров без файла на диске: 494` — the
local `data/frames` directory holds 2,159 of 2,653 referenced frames. This is local data incompleteness, not
a code defect. (Without the frames link it fails 2 checks: 2,653 frames + 282 sheets.)

```
PASS test_topup.py    ok=16
PASS test_posts.py    ok=12
PASS test_journal.py  ok=10
PASS test_collect.py  ok=19
PASS test_score.py    ok=15
PASS test_pipeline.py ok=19
FAIL test_baseline.py  — IndexError: no author with exactly 24 reels in snapshot 1
FAIL test_roster.py    ok=6  fail=3
FAIL test_cards.py     ok=17 fail=1
FAIL test_deep.py      ok=13 fail=1
FAIL test_topics.py    ok=8  fail=1
FAIL test_notion.py    ok=10 fail=2
────────────────────────────────────────
TOTAL 153 checks · 145 pass · 8 fail   (+ check.py: 15 checks, 14 pass)
```

The brief's "~174 checks" is close; I measured 168 total including `check.py`. The gap is `test_baseline.py`,
which aborts before its assertions.

Every one of the 8 failures is **fixture coupling to live DB state**, not a code defect:

| Test | Assertion | Got / expected |
|---|---|---|
| `test_roster` | accounts dropping after two misses | 0 / 17 |
| `test_roster` | active remaining | 130 / 113 |
| `test_topics` | top fully tagged | 219 / 282 (63 deepdives have no caption row in the latest snapshot) |
| `test_cards` | already-closed marking | False / True |
| `test_deep` | all passed the selection threshold | False / True |
| `test_notion` | properties updated; status written | `Proposed` / `Not taking` |
| `test_baseline` | needs an author with exactly 24 reels in snapshot 1 | none exists |

Root cause: each test does `shutil.copy(DB_PATH, TMP)` and asserts against production values frozen at some
earlier date. **Worth fixing independently of the merge** — these tests will keep drifting.

Run on the server (`/opt/radar`, commit `92e71e7a`, full `data/frames`) the result may differ; I could not
verify server-side behaviour from here. **UNVERIFIED.**

---

## 4. Schema comparison

### 4.1 main `db.py` → Latest equivalents

| # | main table (`db.py`) | Key columns | Latest equivalent | Note |
|---|---|---|---|---|
| 1 | `accounts` (L25–45) | pk, username, full_name, follower_count, following_count, media_count, biography, category, is_verified, is_private, tag, status, misses, added_at, last_checked, checked_snapshot, dropped_at, why_out, via | `account_analysis` (payload) + `accounts.csv` columns | Latest imports only username/followers/media_count/category/biography. **Roster lifecycle — `tag`, `status`, `misses`, `dropped_at`, `why_out`, `via`, `checked_snapshot` — has NO equivalent.** Unique to main. |
| 2 | `snapshots` (L48–56) | id, taken, accounts_n, reels_n, units, done, note | `releases` + `snapshot.json` | Latest's release is content-addressed (`corpus_sha256`/`config_sha256`/`implementation_sha256`); main's is a date. `units` (Hiker cost) has no equivalent. |
| 3 | `reels` (L59–76) | snapshot_id, code, pk_user, username, ts, kind, play, likes, comm, resh, save, dur, cap, followers | `observations` + `reel_analysis` + `reel_metric_values` | Fully covered. `kind` and `cap` (raw caption) are dropped — Latest stores `caption_sha256` only. |
| 4 | `scores` (L79–95) | snapshot_id, code, z, eligible, author_median_play, c_views, c_eng, c_resh, c_save, c_comm, resh_1k, save_1k, comm_1k, baseline_n, baseline_snaps, axes, **weights** | `reel_metric_values` + `reel_analysis.payload` | Latest has `*_robust_z`, `*_baseline_n`, `diagnostic_component_count` (≈ `axes`), `creator_view_index`. **`weights` has no equivalent** — Latest has one equal-weight scheme; main's two-weight comparison cannot be expressed. **`baseline_snaps` has no equivalent** (single-release model). |
| 5 | `topics` (L98–104) | code, topic, source | `topic_codes`, `topic_state` in `reel_analysis` | `source` (`manual` vs `sample`) is **lost** — the provenance of a label disappears. |
| 6 | `deepdives` (L107–118) | code, snapshot_id, cuts, cuts_ps, mp4_mb, sheet, suitable, unfit_why, done_at | `cut_count`, `cut_summary_state`, `cut_summary_evidence_id` | **`suitable` / `unfit_why` — the human fitness verdict — has NO equivalent.** Unique to main and operationally central (`cards.py` filters on it). |
| 7 | `frames` (L121–127) | code, idx, t_sec, path | `evidence_attempts(modality='frames')` + `frame_sample_count`, `frame_requested_count`, `frame_budget_max`, `frames_source_identity_state` | Latest is richer per-frame (SHA-256, decoded index, PTS) but **refuses to import main's existing 2,653 frames**. |
| 8 | `transcripts` (L130–136) | code, lang, words, text, segments | `transcript_state`, `transcript_words`, `transcript_evidence_id`; corpus fields `asr_language`, `asr_language_probability`, `transcript_word_count_lexical`, `transcript_aligned_word_count`, `transcript_words_per_second`, `transcript_rate_comparability`, `transcript_source_identity_state` | **Latest is materially richer.** Main has no ASR provenance at all — no model id, no media hash, no language probability. This is the clearest place Latest should win. |
| 9 | `our_posts` (L139–150) | id, published_at, format, topic, url, lead, goal, ref_code, note | — | **No equivalent.** Unique to main. |
| 10 | `our_metrics` (L153–162) | post_id, measured_at, reach_followers, reach_nonfollowers, retention, dropoff_sec, saves, follows | — | **No equivalent.** Unique to main. |
| 11 | `followers` (L165–171) | pk, at, follower_count | `followers` (point-in-time in `accounts.csv`) | Latest has no time series; it records `profile_horizon_state: CURRENT_DB_NOT_HISTORICAL_SNAPSHOT`. Unique to main (though currently 0 rows). |
| 12 | `cards` (L175–192) | id, week, code, fmt, pri, lead, why, angle, hook, shot_frame, shot_screen, shot_banner, caption, goal, status | `docs/m2-field-dictionary.csv` card scope (11 columns) + `examples/ten-card-*/M2-*.json` | Latest's card lives in files, not a table. No `week`, no `pri`, no `fmt` slot logic. |
| 13 | `tool_log` (L195–202) | id, at, kind, what, detail, fixed | `events` in `state.sqlite` (machine) | Different purpose: main's is human-written observations, Latest's is machine state. **Complementary.** |
| 14 | `spend` (L205–213) | id, at, item, units, price, usd, note | `reserved_cost_upper_bound_usd`, `actual_provider_charge_usd`, `billing_state` in the Hiker adapter | Latest has forward cost reservation; main has historical accounting. Complementary — Latest's reservation is worth porting. |

### 4.2 Latest `m2_signal/schema.sql` → main equivalents

| Latest table | Rows in my run | main equivalent |
|---|---:|---|
| `releases` | 1 | ~`snapshots` (weaker — no hashes) |
| `sources` | 7 | **none** — content-addressed source files |
| `release_sources` | 7 | **none** |
| `observations` | 2,816 | ~`reels` (raw) |
| `release_observations` | 2,816 | **none** — row-level provenance back to the source file and row number |
| `reel_analysis` | 1,535 | ~`scores` |
| `account_analysis` | 129 | **none** — main has no account-level rollup table |
| `evidence_attempts` | 10,745 | **none** — per-reel × per-modality attempt log with reason codes |
| `metric_observations` | 7,675 | **none** — per-metric `observation_state` + `native_field_name` + `semantics_state` |
| `reel_metric_values` | 18,420 | ~`scores` columns, plus `formula_version` |

### 4.3 `schemas/m2-corpus-field-dictionary.v1.json` — 43 fields

Fields with **no counterpart in main**: `media_source_identity_state`, `media_corpus_expected_sha256`,
`media_observed_sha256`, `media_artifact_verified`, `media_has_audio`, `asr_language_probability`,
`transcript_aligned_word_count`, `transcript_words_per_second`, `transcript_aligned_words_per_second`,
`transcript_rate_comparability`, `transcript_source_identity_state`, `transcript_artifact_verified`,
`frame_requested_count`, `frame_budget_max`, `frame_sampling_truncated`, `cut_observation_state`,
`frames_source_identity_state`, `frames_artifact_verified`, `account_cluster_id`, `comparability_gate`,
`metric_eligibility_gate`, `scene_review_state`, `reviewed_scene_state`, `structural_label_state`,
`missingness_reasons`, `model_gate`, `quarantined`, `acquisition_state`, `total_actions_per_1k_views`.

Fields that map cleanly onto main: `reel_id`↔`code`, `views`↔`play`, `likes_per_1k_views` etc. ↔ `c_eng` /
`resh_1k` / `save_1k` / `comm_1k`, `media_duration_seconds`↔`dur`, `cut_candidate_count`↔`cuts`,
`transcript_word_count_lexical`↔`transcripts.words`, `transcript_state`↔(implicit), `asr_language`↔`lang`.

⚠️ `m2_signal/analysis_eligibility.py:70` — `load_feature_rows(..., expected_rows: int | None = 2352)`.
The default row count is **hardcoded to the 2026-09-01 snapshot**. Anyone calling it without an explicit
`expected_rows` on the current 1,535-row snapshot gets a fail-closed error.

### 4.4 `docs/m2-field-dictionary.csv` — 65 Notion columns

34 `reel`, 20 `account`, 11 `card`. Each row carries `notion_type`, `meaning`, `units_formula_denominator`,
`source`, `null_semantics`, `permissible_inference`, `owner_field`. Main's `notion_db.py` publishes a
comparable set of reel/account columns but **has no data dictionary at all** — no documented null semantics
and no `permissible_inference` column. This CSV is directly usable as documentation for main's existing
Notion databases and costs nothing to adopt.

---

## 5. Recommendation

### 5.1 Canonical choice per layer

| Layer | Canonical | Why |
|---|---|---|
| Collection (Hiker) | **main** | Only working implementation; cache sharding and spend accounting are proven |
| Relational storage | **main `db.py`** | 15 tables, migrations, indices, 5.2 MB for three snapshots vs 24 MB per snapshot |
| Scoring / baseline | **main `score.py`/`baseline.py`** | Age bands, focal-row exclusion, cross-snapshot baseline — none of which Latest has |
| Topic taxonomy | **main `topics.py`** | Latest's is a slug map of main's labels |
| Deep dive (frames/ASR) | **main `deep.py`**, upgraded with Latest's mechanics | Main ships; Latest's PTS indexing, watchdogs and failure codes are the upgrade |
| Transcript provenance | **Latest's field model** | Main records nothing; this is the clearest gap |
| State / job tracking | **Latest `m2_orchestrator/state.py` + `policy.py`** | Main has none |
| Scene contract | **Latest `schemas/video-scene-segmentation.schema.json` + `scene_media.py`** | Main conflates cut/shot/scene |
| Video render | **Latest `studio/remotion/`** | Main has nothing |
| Provider escrow | **Latest `m2_studio/providers.py`** | Main has nothing; catalog needs re-verification |
| Notion write | **main `notion.py`/`notion_db.py`** + Latest's owner-field guard | Only main can write; Latest has the conflict logic |
| Editorial contract | **Latest `skills/m2-script-writer` rules**, merged into main's `prompts/angles.md` | Better claim discipline |
| Tests | **both**: keep main's, add Latest's style for new code | Decouple main's tests from live DB |

### 5.2 Concrete integration strategy

**Principle: main's SQLite stays the single source of truth. Latest is adopted as (a) a state layer above it
and (b) a set of contracts beside it — never as a replacement store.**

**Phase 1 — merge without breaking production (half a day)**

Files to **port as-is**:
- `m2_orchestrator/policy.py`, `state.py`, `process_budget.py` → new `radar_state/` package.
  Pure stdlib, no third-party imports. Trim the 41-stage DAG to main's real 13 steps first.
- `schemas/video-scene-segmentation.schema.json` → `schemas/`
- `studio/remotion/` → `studio/remotion/` verbatim (self-contained, Node-only)
- `m2_studio/provider-catalog.json` → `config/`, with `recheck_after` bumped and the price receipt actually filled
- `docs/m2-field-dictionary.csv` → `docs/` (documentation for existing Notion DBs)

Files to **rename on import** (see §6.1):
- Latest `run.py` → `run_signal.py`. **Main's `run.py` must not move** — `cron.sh` line 25 calls it.
- Latest `test_pipeline.py` → `tests/test_signal_pipeline.py`
- Latest `install-cron.sh` → **discard**; keep main's.

Files to **keep as historical reference only** (import under `reference/` or leave on the branch):
- `m2_signal/` ledger (`schema.sql`, `engine.py`, `corpus_features.py`, `analysis_eligibility.py`,
  `structural_features.py`, `transcript_benchmark.py`) — valuable as a spec, 15× storage cost as a store
- `m2_orchestrator/media_recovery.py`, `recovery_overlay_report.py`, `transcription_recovery.py`,
  `semantic_queue.py` (~2,900 LOC) — solve problems we do not yet have
- `m2_orchestrator/media_ocr.py` + `scripts/m2_vision_ocr.swift` — macOS only
- `integrations/radar/` — duplicate of root `server_entry.py`
- `examples/ten-card-20260907/`, `knowledge/`, `docs/reviews/` — evidence of Max's process, not runtime code

**Phase 2 — targeted upgrades to main's engine (1–2 days)**

1. `db.py`: add to `ADDED` —
   `transcripts.model_id`, `transcripts.source_media_sha256`, `transcripts.lang_probability`,
   `transcripts.asr_state`; `frames.sha256`, `frames.decoded_index`; `scores.coverage`, `scores.reason_code`,
   `scores.formula_version`; `deepdives.evidence_state`.
2. `deep.py`: replace `-ss` seeking with PTS-indexed decode (port `_extract_indexed_frames` from
   `media_visual.py:118`); wrap ASR and FFmpeg in `bounded_process` from `process_budget.py`; adopt the typed
   failure codes; record the model id and media hash on every transcript.
3. `notion.py`: add `OWNER_FIELDS` guard and `equivalent()` from `m2_orchestrator/projection.py:13–42`.
4. `collect_snapshot.py`: add a hard cost ceiling + dated price receipt, modelled on
   `hiker_adapter.validate_collection_config` (`m2_signal/hiker_adapter.py:29–68`).
5. `cards.py`: add an evidence gate — a card cannot be proposed for a reel with no transcript and no frames
   (port the `best_reel_eligibility_state` idea, not the machinery).
6. `prompts/angles.md`: merge the claim-map classification and editorial prohibitions from
   `skills/m2-script-writer/SKILL.md`.
7. `run.py`: wrap the existing 13 steps in the `Controller` so a failed step is resumable.

**Phase 3 — fix what the audit exposed (half a day)**
- Decouple main's 12 test scripts from the live DB: build a small synthetic fixture DB. This fixes 8 failing
  checks permanently.
- Ask Max to export his 1,062 transcripts and 19,808 frames through `m2_signal`'s receipt format, then import
  them into main's `transcripts` / `frames` tables with provenance attached.
- Bump `provider-catalog.json` or delete it — it expires 2026-09-12 with no verified price.

### 5.3 What NOT to do

- **Do not** adopt `m2_signal/schema.sql` as the store. 24 MB per snapshot against 5.2 MB for everything.
- **Do not** merge Latest's `run.py` over main's. It would break the `/opt/radar` cron on the next `git pull`.
- **Do not** adopt the 41-stage DAG as-is. 29 stages have no implementation; trim to main's real steps.
- **Do not** treat Latest as "newer therefore better". Its statistics are weaker (focal row in baseline, no age
  bands, no cross-snapshot history) and its collection layer has never made a live call.

---

## 6. Risks and gotchas for the merge

### 6.1 Naming collisions — three hard, all in main's favour

| File | Risk | Mitigation |
|---|---|---|
| `run.py` | **Critical.** `cron.sh:25` runs `.venv/bin/python run.py --yes`, and `cron.sh:22` does `git pull` first. Merging Latest's `run.py` means the very next scheduled run executes the Signal planner instead of the collection pipeline — and Latest's default with no `--yes` prints `PLAN_ONLY` and exits 0, so **the failure would be silent**. | Rename Latest's to `run_signal.py` before merge. Verify `cron.sh` after. |
| `install-cron.sh` | Latest's version installs nothing and only prints a notice. | Keep main's. |
| `test_pipeline.py` | Both exist, both pass, they test different things. | Rename Latest's to `tests/test_signal_pipeline.py`. |

Soft collisions: `README.md`, `SPEC.md`, `RULES.md`, `PLAN.md`, `START-HERE.md`, `POSITIONING.md` differ —
main's are newer and reflect brand book v3. Latest adds `AGENTS.md` (no conflict).

### 6.2 Python version

| Environment | Version | Status |
|---|---|---|
| This Mac | **3.10.4** | Latest's 370 tests run here. Uses PEP 604 union syntax and dict-merge operators — 3.10 minimum, fine. |
| Server `/opt/radar` | **3.12** (per brief; not directly verified — **UNVERIFIED**) | Should be fine; nothing in Latest requires >3.10 |
| `requirements-m2-media.txt` | declares *"observed macOS Python 3.12.9"* and notes *"Linux compatibility requires a fresh host smoke test"* | Max himself has not tested his media stack on Linux |

`fcntl` is imported (POSIX-only) — fine on both macOS and Linux, but blocks any future Windows use.

### 6.3 Duplicate modules

`server_entry.py` exists **twice**, identical at 148 lines: repo root and `integrations/radar/server_entry.py`.
Same for `config/server-media.example.json` and `config/server-replay.example.json`. Keep one; the
`integrations/radar/` copy looks like a packaging experiment.

### 6.4 Dependencies

- **main today** imports only stdlib plus `faster-whisper` and `imageio-ffmpeg` (both already installed here:
  faster-whisper 1.2.1, ctranslate2 4.8.1, av 17.1.0, imageio-ffmpeg 0.6.0, numpy 2.2.6, pillow 12.3.0).
- **Latest's orchestration core** (`m2_signal`, `m2_orchestrator`, `m2_studio`) imports **no third-party
  packages at all** — deliberately. `faster_whisper` is imported inside the isolated child worker
  (`media_transcription.py:475`), never at module scope. This makes it unusually safe to port.
- `requirements-m2-media.txt` pins 25 packages at versions **newer than what is installed here** — av 18.1.0
  vs 17.1.0, ctranslate2 4.8.2 vs 4.8.1, numpy 2.5.2 vs 2.2.6, Pillow 12.2.0 vs 12.3.0 (a *downgrade*), plus
  `yt-dlp 2026.7.4` and `onnxruntime`. Installing this file wholesale would disturb main's working ASR stack.
  **Do not `pip install -r` it.**
- `pytest` is required by 22 of 32 test modules and is **not in any requirements file**.

### 6.5 Runtime binaries

| Binary | main | Latest |
|---|---|---|
| ffmpeg | bundled via `imageio_ffmpeg.get_ffmpeg_exe()` — zero system dependency | bare `"ffmpeg"` from PATH → **not available on this Mac**, one test skipped |
| Whisper model | `faster-whisper` downloads `small` on first use | requires a pre-built model dir with `model-hash-manifest.json` — **does not exist** |
| yt-dlp | not used | required for `--public-resolver`, hash-pinned |
| OCR | not used | `scripts/m2_vision_ocr.swift`, Apple Vision — **macOS only, dead on the server** |
| Node/Chrome | not used | Remotion needs Node + an existing Chrome binary (it will not auto-download one) |

### 6.6 Data-model gotchas

1. **`legacy.py` discards frame evidence.** 2,653 frames and 282 deepdives in main become `frames coverage 0%`
   in Signal. Any Signal-based decision currently ignores work main already paid for.
2. **`legacy.py` requires `done=1` and exactly one snapshot per date.** A partial collection cannot be exported.
3. **Immutable export directories.** Re-running `import-legacy-db` into an existing directory with any changed
   byte raises `immutable export target differs`. Good hygiene, but it will surprise anyone re-running a day.
4. **Two `weights` sets cannot be represented.** Main's `scores` PK is `(snapshot_id, code, weights)`;
   Latest has one equal-weight scheme. Porting scores into Signal loses the `W_IG` vs `W_MAX` comparison.
5. **Topic provenance is lost.** `topics.source` (`manual` vs `sample`) has no counterpart.
6. **`suitable` / `unfit_why` is lost.** The human fitness verdict is what `cards.py` filters on; Signal has no
   field for it.
7. **`analysis_eligibility.py` hardcodes 2352 rows** as its default population.
8. **Signal snapshot dates are capture dates, not post ages** — stated in the adapter's own limitations.
   Main's `AGE_BANDS` exists precisely because this matters.

### 6.7 Process risks

- **Max's branch is 10 days behind main's engine** and anchored to the 2026-09-01 snapshot (2,352 reels). His
  reconciled report's numbers describe that snapshot, not the current 5,147-row database.
- **His large evidence set is unreproducible from git.** 1,062 transcripts and 19,808 frames exist only locally.
- **Two failing tests at his tip** and a **broken `test_local.py` gate** mean his branch has not been run
  clean-checkout recently.
- **`provider-catalog.json` expires 2026-09-12** with `price_receipt: null`.

---

## 7. Explicitly unverified

- Server behaviour at `/opt/radar` (Python version, full `data/frames`, whether main's 12 test scripts pass
  there). Everything reported is from this Mac.
- Whether Max's 1,062 transcripts overlap main's 273 — his own report flags the same thing: *"A stable-ID
  overlap audit is still required."*
- Whether Latest's media acquisition path actually works, since no media manifest, model bundle or `yt-dlp`
  exists in the repo and FFmpeg is not on PATH here. Only its unit tests were exercised.
- Whether `hiker_server.py --execute` works. It has never made a live call; the module itself declares
  `LIVE_SCHEMA_UNVERIFIED`.
- The accuracy of the numbers in `max/main`'s reports beyond the 2,352 figure, which matches
  `dataset/radar.db`.
- Whether Remotion actually renders. Only the deterministic EDL contract test ran (PASS); the renderer needs
  `npm ci` and a Chrome binary, neither of which was invoked.
