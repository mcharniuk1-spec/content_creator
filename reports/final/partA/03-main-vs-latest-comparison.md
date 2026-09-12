# 3. Main vs `latest` / Max Fork Comparison

## Topology

`origin/Latest` is not a fork of current `main` — it branches at the merge base `02102dd1` and
never received main's last 17 commits (design system, engine fixes, the current audit and runs).
Its own topology adds one further hop: `max/main` sits one commit ahead of `origin/Latest`,
containing only two reports (md+pdf) and a 31-line PDF build script — no executable engine change.
That report is itself anchored to the 2026-09-01 snapshot (2,352 canonical reels), ten days stale
against main's current 5,147-row, three-snapshot database.

Critically, Max **did not touch main's engine**: `db.py`, `deep.py`, `collect_snapshot.py`,
`blocks.py`, `score.py`, `baseline.py`, `cards.py`, `notion.py`, `notion_db.py` and `lib/hiker.py`
are byte-identical on both branches, confirmed by diffing each file against the merge base rather
than assumed from directory names. Latest instead adds ~20,000 LOC in four new packages
(`m2_signal/`, `m2_orchestrator/`, `m2_studio/`, `studio/remotion/`) that never ran in production
and whose own module docstrings say so explicitly (`hiker_adapter.py`:
*"LIVE_SCHEMA_UNVERIFIED"*; the activation doc: *"No step here was executed against HikerAPI
during this integration"*).

## What was ported, what was not, and why

| Adopted as-is | Adopted as pattern only | Not adopted |
|---|---|---|
| `schemas/video-scene-segmentation.schema.json` | Per-metric `observation_state` + `reason_code` (idea, not the payload table) | `m2_signal/schema.sql` as a store — 24 MB/snapshot vs 5.2 MB for main's whole history |
| `studio/remotion/` (EDL contract + composition) | `price_receipt_sha256`-style cost provenance | Content-addressed releases — forbids re-running a day whose bytes changed |
| `m2_orchestrator/process_budget.py` → `engine/process_budget.py` | Dispatch-then-call idempotency for Hiker calls | The 41-stage DAG — 29 stages had no implementation |
| `m2_studio/provider-catalog.json` → `config/provider-catalog.json` | `OWNER_FIELDS` Notion conflict guard | `analysis_eligibility.load_feature_rows(expected_rows=2352)` — hardcoded, fails closed |
| `docs/m2-field-dictionary.csv` (65 Notion columns) | PTS-indexed frame extraction, cut/shot/scene distinction | `media_ocr.py` / Apple Vision — macOS only, dead on the Linux server |
| — | Claim-map / editorial-contract rules from `skills/m2-script-writer` | `requirements-m2-media.txt` — pins newer versions than the working ASR stack, including a Pillow *downgrade* |

The state/job-tracing model (`m2_orchestrator/state.py` + `policy.py`) was adopted as the single
most valuable structural idea on Latest, trimmed from 41 stages to the 25 that reflect what this
branch actually runs (chapter 6).

## Tests before and after

| Suite | Before (audit, 2026-09-11) | After (this branch) |
|---|---|---|
| `origin/Latest` `tests/` | 367 passed, 2 failed, 1 skipped (both failures real, stale test fixtures at Latest's tip) | unchanged — not merged as code |
| Max's own gate `scripts/test_local.py` | Fails out of the box (`pytest` not in his requirements file); covers 7 of 32 modules | unchanged |
| `main` root scripts (12 files) | 153 checks, 145 pass, 8 fail — all fixture coupling to live DB state, plus `check.py` 14/15 | 165 checks across 12 files, decoupled from `data/radar.db` via synthetic fixtures; `check.py` 23 checks |
| `tests/` (new `engine/` suite) | did not exist | 241 passed, 1 skipped by design (`test_local_pipeline.py`'s `slow` marker) |

Combined today: `python3 check.py` (23) + 12 root scripts (165) + `pytest -q` (241 passed / 1
skipped) = 429 automated checks, none of them coupled to a frozen snapshot of live data any longer.

## The cron-breaking risk found and avoided

The single highest-risk collision in the whole comparison: Max's branch **replaced `run.py` and
neutralized `install-cron.sh`.** `cron.sh:25` runs `.venv/bin/python run.py --yes` after a `git
pull`; merging Latest's `run.py` as-is would mean the very next scheduled cron execution runs the
Signal planner instead of the collection pipeline — and Latest's planner defaults to `PLAN_ONLY`
with no `--yes`, printing a plan and exiting 0, so **the failure would have been silent**, visible
only as a week with no new cards. This branch's decision (`engine/SPEC.md` §0.6): main's `run.py`
never moves; a same-named file from Latest would be renamed `run_signal.py` on import, and no such
import has happened — Latest's `run.py`/`test_pipeline.py`/`install-cron.sh` remain unmerged,
confirmed by `cron.sh` still calling the original file today.

## The `latest` = Max fork sync, still to do

`origin/Latest`'s ~1,062 transcripts and ~19,808 frames exist only on Max's machine — a full
non-binary tree scan of both `origin/Latest` and `max/main` for
`transcript|frame|asr|.local|outputs|.jsonl|whisper` found only source modules, tests and
documentation, no committed media analysis. This is the one open item this chapter flags rather
than resolves: exporting his corpus through `m2_signal`'s own hash-bound receipt format (so
provenance survives the transfer) and reconciling it against this database's 268 analysis-ready
codes is scheduled for push time, not done in this migration (chapter 5).
