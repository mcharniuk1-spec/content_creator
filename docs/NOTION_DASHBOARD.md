# Notion Dashboard — engine.notion_sync

Owner of this doc and of `engine/notion_sync.py`, `engine/notion_blocks.py`,
`tests/test_notion_sync.py`. Built against `reports/audit/05-notion-state.md` (2026-09-11)
and SPEC §85-91. **Nothing in this document reflects a write that has actually happened.**
As of this writing `engine.notion_sync` has only ever been run with `--dry`: it has made
zero writes to Notion. `--apply` is implemented but has never been executed.

## What exists in Notion today (per the audit) vs what this module adds

| Object | ID | Status |
|---|---|---|
| Content Engine Tool (dashboard page) | `3d00bd21ed6a800fb0ffda652e539ef1` | Existing. Its **body gets replaced** by `--apply --scope dashboard` (old children archived, not deleted — see Notion's own block trash). |
| Cards (10 reviewed shooting plans) | `225e60a9-3198-4e3c-a151-b462d20d2e63` | Existing, **reused as-is**. Never recreated, never schema-changed. |
| M2 Signal + Studio · 7 September (release ledger) | `3d20bd21ed6a813a9a4cd8f51a28af71` | Existing. Linked from the new dashboard's **Legacy** section, not altered. |
| Reels · Signal 2026-09-05 (2,352 rows) | `c26c6990-bba9-4ab5-a700-e94bd42e327d` | Existing. Linked + labelled "one-off audit corpus, not live" under Legacy. |
| Accounts · Signal 2026-09-05 (100 rows) | `e45a50d2-a910-47b8-99a0-f2ec9f1a3393` | Existing. Same treatment. |
| Two orphaned "🗑️ M2 Lab — Radar" stub pages | see audit §6 | Existing. Linked under Legacy with a "candidate for deletion — needs Misha's sign-off" caption. Never deleted by this module. |
| Operational `NOTION_REELS_DB` / `NOTION_ACCOUNTS_DB` | not extracted (see below) | Existing, cron-writable. **Not re-pointed, not read for their literal IDs by this module** — see the open decision below. |
| **Runs, Insights, Hypotheses, Cards v2, Reels analysis, Accounts analysis, Categories** | none yet | **New.** Created under the dashboard page on the first `--apply --scope dbs` (or `all`), only if a same-titled database isn't already cached in `data/notion_ids.json`. |

The two operational database IDs are deliberately never hard-coded or printed anywhere in
this module, its plan output, or this doc — matching the audit's own restraint (§1/§4.4).
`legacy_section()` only reports *presence* of `NOTION_REELS_DB`/`NOTION_ACCOUNTS_DB` in
`.env` (booleans), the same pattern `engine.db_util.env_present` uses for `HIKER_KEY`.

## Open decision — Misha/Max, not picked silently

Audit §8.1 named two ways to resolve the two-systems split:

- **(a)** Re-point `NOTION_REELS_DB`/`NOTION_ACCOUNTS_DB` at the richer Signal schema and
  migrate `notion_db.py`'s property mapping — folds the two systems into one, but needs
  real migration code and a manual copy of the `Verdict`/`What to borrow` columns someone
  already hand-added to the old Accounts DB (nothing in this repo writes those back).
- **(b)** Keep them separate: link the *existing* operational Reels/Accounts databases into
  the visible page tree so they're at least navigable, and relabel the Signal ones clearly
  as a one-off 2026-09-05 snapshot.

**This build implements (b)** per the task brief that commissioned it. That is a working
assumption, not Misha's sign-off — confirm or override before `--apply` runs for real.

## Architecture

```
engine/notion_blocks.py   pure block-JSON builders (heading/paragraph/bullet/table/toggle/
                          callout/code/bookmark/link_to_page), chunking rich_text at 2000
                          chars and block batches at 100 — no network, no Notion imports.

engine/notion_sync.py
  IdCache                 data/notion_ids.json — {databases: {title: id}, rows: {db: {key: id}}}.
                          Only written during --apply (resumable idempotency).
  ReadOnlyTransport       .get_page / .get_database only. No write method exists on this
                          class — --dry can only ever hold one of these.
  LiveTransport(RO)       adds query_database / create_page / update_page_properties /
                          replace_children / create_database / find_page_by_key. Only
                          constructed inside apply_plan(), which --dry's code path never
                          calls (tests/test_notion_sync.py asserts this directly).
  *_section() / *_rows()  gather plan data from the local SQLite DB (data/radar.db via
                          engine.db_util) and from reports/data/*.json, data/analysis/
                          {insights,hypotheses}.json, cards/*.json — all optional; every
                          one has a documented fallback for "not produced yet".
  build_dashboard_blocks  assembles the Content Engine Tool body per SPEC §86.
  build_plan()            the --dry entry point: local data only, plus an opt-in --discover
                          read-only GET against the two known existing objects.
  render_plan_markdown /
  render_plan_summary     reports/notion-sync-plan.md and the console summary.
  upsert_rows() /
  ensure_database() /
  apply_plan()            the --apply path. Generic upsert shared by every new database —
                          one field-mapping function (_row_to_properties) instead of a
                          bespoke loop per database. Rate-limited at ~3 req/s
                          (RATE_LIMIT_SLEEP_S). Not exercised in this task.
```

## New databases (created only under `--apply --scope dbs|all`, only if missing)

All seven live under the Content Engine Tool page. `KEY_PROPERTY` is the idempotency key
(also the Notion title property); `FIELD_OVERRIDES` documents every property whose Notion
label doesn't slug-match its row-dict field name (e.g. `Comments` ← `comm`, `Videos` ←
`n_videos`) — see `engine/notion_sync.py` for the full list, and
`tests/test_notion_sync.py::test_row_to_properties_*` for the tests that pin it down.

| Database | Key property | Size at last `--dry --scope all` run | Source |
|---|---|---|---|
| Reels analysis | Code | 297 (corpus tier ANALYSIS_READY ∪ FRAMES_ONLY ∪ TRANSCRIPT_UNUSABLE) | `reels` + `scores` + `video_features` (LEFT JOIN — category fields are `None` on any row `video_features` hasn't reached yet) |
| Accounts analysis | Username | 132 | `creator_stats` (already populated) + `accounts` |
| Cards v2 | Card ID | 0 | `cards_v2` table + `cards/*.json` on disk (JSON wins when present — it carries the untruncated script) |
| Runs | Run ID | 0 | `runs` table + `engine.state.run_summary` |
| Insights | Insight ID | 0 | `data/analysis/insights.json`, falls back to the `insights` table |
| Hypotheses | Title | 0 | `data/analysis/hypotheses.json`, falls back to the `hypotheses` table |
| Categories | Label | 181 | `video_features` aggregated by topic/pain/hook/solution/cta/visual — one row per (dimension, value) pair with `n≥1` |

These are not fixed numbers this module assumes — every one is computed live from
`data/radar.db` on each `--dry` run (see the exact run captured in the final report of the
session that built this module). Cards v2/Runs/Insights/Hypotheses read 0 today because
that stage of the pipeline (card generation, insight/hypothesis synthesis, run tracing)
hasn't produced rows on this corpus yet; Reels analysis/Categories/Accounts analysis are
already live because `video_features`/`creator_stats` are partially populated. `--dry`
reports whatever is true at run time, never a cached assumption.

## How to run it

```bash
# Safe, default, no network required, no token needed:
python3 -m engine.notion_sync --dry --scope all
python3 -m engine.notion_sync --dry --scope reels --limit 50

# Same, but also confirms (read-only GET) that the dashboard page and the reused Cards DB
# are reachable with the current NOTION_TOKEN — needs .env, makes exactly 2 GET calls:
python3 -m engine.notion_sync --dry --scope all --discover

# Refused on purpose by this build (prints a message, exit code 2, touches nothing):
python3 -m engine.notion_sync --apply
```

`--dry` always writes `reports/notion-sync-plan.md` (override with `--out`) and prints a
short summary to stdout. Neither ever calls a Notion write endpoint; `--dry`'s scope option
(`dashboard|dbs|reels|accounts|cards|runs|all`) only changes which sections are computed.

**To actually run `--apply`** (orchestrator only, after a human has reviewed a `--dry`
plan): `engine.notion_sync.apply_plan(con, plan, id_cache)` is fully implemented — a CLI
invocation of `--apply` is intentionally hard-refused in this build (see `main()`) so that
running it requires calling `apply_plan()` directly and deliberately, not a stray flag.

## Verification run (read-only, this task)

```
$ python3 -m engine.notion_sync --dry --scope all
```
See the session's final report for the exact captured output; `reports/notion-sync-plan.md`
holds the full plan including per-database sample rows.

## Tests

```bash
python3 -m pytest tests/test_notion_sync.py -q
```

Covers: rich-text/block chunking limits, corpus-tier-driven row selection for Reels
analysis, the property-name mapping for every database that has a mismatch between its
Notion label and its row-dict field (this caught three real naming bugs during review —
`Comments`/`Reshares`/`Saves`/`Scenes`/`View lift` on Reels analysis, `Videos`/
`Consistency`/`Top reels` on Accounts analysis, `Hypothesis`/`Total seconds`/`Words` on
Cards v2 — fixed via `FIELD_OVERRIDES` before this suite was written against it), the
idempotent upsert logic against a fake in-memory transport (create vs. update, and that a
second run reuses the id cache instead of re-querying Notion), and — the one non-negotiable
assertion in the file — that `build_plan()` with `discover=False` (the CLI default) never
constructs `LiveTransport`, the only class in this module capable of a write.
