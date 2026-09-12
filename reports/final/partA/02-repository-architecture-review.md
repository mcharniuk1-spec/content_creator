# 2. Repository/Architecture Review

Before this branch, the repository existed as two structurally separate efforts sharing one merge
base (`02102dd1`): `main` (17 commits ahead, HEAD `92e71e7a`) held the working weekly pipeline —
collection, scoring, deep-dive, cards, Notion push — and `origin/Latest` (8 commits ahead, Max's
fork) held a parallel, never-deployed ~20,000-line system (`m2_signal`, `m2_orchestrator`,
`m2_studio`, `studio/remotion/`) built *alongside* main's engine rather than on top of it: every
shared engine file except `run.py`, `test_pipeline.py` and `install-cron.sh` was byte-identical
between the two branches. That structural fact — confirmed by diffing every shared file against
the merge base, not assumed — is why the canonical architecture below could adopt Latest's ideas as
contracts without inheriting its (never-run) storage layer. Full comparison: chapter 3.

## Canonical architecture, as built

Decision (`engine/SPEC.md` §0): **main's SQLite `data/radar.db` remains the single source of
truth.** Nothing in its 14 legacy tables (`accounts, snapshots, reels, scores, topics, deepdives,
frames, transcripts, our_posts, our_metrics, followers, cards, tool_log, spend`) was renamed or
dropped; `engine/schema.py` adds 17 new tables and 5 guarded columns through an idempotent,
versioned migration recorded in `schema_migrations`. Max's `Latest` is adopted as *contracts and
vocabulary, never as a store* — verified in the audit: replaying one snapshot into his
`m2_signal` ledger produced 24 MB against main's entire three-snapshot database at 5.2 MB, and his
own import adapter (`legacy.py`) discards main's 2,653 already-extracted frames on the way in.

## North-star flow

```
Hiker (paid, weekly) -> reels/accounts snapshot (db.py, 14 tables)
  -> local faster-whisper transcript -> local ffmpeg scene/frame extraction
  -> transcript <-> scene alignment -> per-video LLM analysis (ta-v1 transcript, fa-v1 frames)
  -> consolidated video_features row -> creator/video statistics (robust z, creator-relative lift)
  -> numeric insights -> ranked hypotheses -> function-tagged reference selection
  -> transformed original script + storyboard -> card JSON
  -> template storyboard frames -> previs EDL -> [Phase 3] supplied MP4 takes -> validated,
     bound into the EDL -> Remotion render -> stored (Supabase canonical, local fallback)
  -> Notion projection -> Misha reviews and decides -> publish (always separate, human, manual)
```

Everything up to card JSON runs for free beyond the weekly Hiker call; everything from "supplied
MP4 takes" onward is Phase 3, verified end-to-end on one example card (chapter 9 of the
architecture doc; render receipt in `reports/evidence/remotion-previs-receipt-C-2026-09-11-EX.json`).

## Module map (summary)

| Layer | Key modules | Role |
|---|---|---|
| Legacy pipeline (unchanged shape) | `lib/hiker.py`, `db.py`, `collect_snapshot.py`, `deep.py`, `score.py`/`baseline.py`, `cards.py`, `notion.py`/`notion_db.py`, `run.py` | The working weekly cron chain; still the only entry point `cron.sh` calls for Phase 1. |
| Engine state | `engine/schema.py`, `engine/state.py`, `engine/migrate_legacy.py`, `engine/db_util.py` | Versioned migration; `runs`/`jobs` tracing; `video_state` recomputation. |
| Local pipeline | `engine/local_pipeline.py`, `engine/scenes.py`, `engine/align.py`, `engine/watchdog.py`, `engine/process_budget.py` | Video-by-video contract: download → transcribe → scene/frame-extract → align → refresh state. |
| Analysis | `engine/ingest_analysis.py`, `engine/lexical.py`, `engine/features.py` | Loads ta-v1/fa-v1 JSON, computes text-only lexical features, consolidates into `video_features`. |
| Statistics | `engine/stats.py`, `engine/corpus.py` | Creator/video performance, temporal trends, associations; the evidence-tier split. |
| Content generation | `engine/ingest_insights.py`, `engine/cards_v2.py`, `engine/storyboard_render.py`, `engine/edl.py` | Insight → hypothesis → reference → card JSON → previs EDL. |
| Production (Phase 3) | `engine/production.py`, `engine/storage.py` | Probe/validate/ingest supplied takes, bind into EDL, render, store. |
| Providers | `engine/providers.py`, `engine/hiker_config.py` | Environment-only state resolution (`CONFIGURED`/`NOT_CONFIGURED`/`FAILED`/`DISABLED`); no secret ever leaves the process. |

## State tracing and providers, at a glance

`runs` → `jobs` (25 canonical stages, `DISCOVERED` through `COMPLETED`) → `video_state` (the
always-current, never hand-written summary) is the model adopted from Latest's orchestrator,
trimmed from its 41-stage DAG (29 stages had no implementation) to these 25. Chapter 6 covers this
in depth, including the fact that `runs`/`jobs` currently hold zero rows in this database — the
trace model is implemented and unit-tested (39 cases in `tests/test_engine_schema.py`) but has not
yet been exercised by a full scheduled run.

Nine providers are registered, state resolved from environment presence only: `hiker` and the two
local providers (`local-faster-whisper`, `local-ffmpeg-scenes`) are `DEFAULT` (part of the
production path); `remotion` is `DEFAULT` but currently `NOT_CONFIGURED` on this machine (no
`node_modules`); `loore`, `supabase`, `cloudflare`, `openai`, `higgsfield` are `OPTIONAL_PROVIDER`,
off unless explicitly configured — `loore` stays `DISABLED` even with a key present until
`LOORE_ENABLED=1` is set, so no key drop can silently turn on a paid path. No provider is
`FALLBACK` today, and no paid API is called from any new module by default — verified by grepping
for client imports, not assumed.

This document sits beside, and never duplicates, `docs/M2RADAR_CONTENT_ENGINE_ARCHITECTURE.md`
(the full authoritative reference), `engine/SPEC.md` (the binding schema contract), and
`reports/audit/01-branch-comparison.md` (the branch audit chapter 3 summarizes).
