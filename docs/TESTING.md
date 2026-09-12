# Testing

Two separate suites, on purpose — see `pytest.ini` for why they can't be one:

1. **Root scripts** (`test_*.py` in the repo root) — plain modules, no pytest. Each
   builds its own throwaway SQLite file from `db.SCHEMA` (or, for `test_score.py`,
   works on hand-built dicts with no database at all), runs, prints `✓`/`✗` per
   check, and exits 1 on any failure. Run one directly: `python3 test_cards.py`.
2. **`tests/`** — a real pytest suite (`engine/*` and supporting libraries). Run with
   `python3 -m pytest -q`.

## Run everything

```bash
python3 check.py && for t in baseline roster topup posts journal cards deep collect topics score pipeline notion; do python3 test_$t.py; done
python3 -m pytest -q
```

The first line is 188 checks: 23 in `check.py` (health checks on `data/radar.db`) plus
165 across the 12 root scripts (behaviour, on synthetic data). The second is 253+ pytest cases
(252 passed + 1 skipped by design at the time of writing; the count grows as test files are added — see `tests/test_local_pipeline.py`'s `slow` marker)
covering `engine/`. `pytest -q` only ever collects `tests/` (`testpaths` in
`pytest.ini`) — the root scripts call `sys.exit()` at import time, which crashes
pytest's collector if it ever tries to import them directly.

## `check.py` — health checks on `data/radar.db` (23 checks)

Not a comparison against a frozen snapshot (that broke the day the database started
growing) — invariants that must hold regardless of how much data has accumulated:
referential integrity (СВЯЗНОСТЬ), roster bookkeeping rules (ПРАВИЛА НАБОРА), data
shape (ДАННЫЕ), and the engine tables added by `engine/schema.py` SPEC §2
(ДВИЖОК): migrations applied, `video_state` row count equal to the number of
distinct reel codes, `beats`/`frame_labels`/`scenes` not orphaned against
`video_state`, no `jobs` row pointing at a missing `run`, at least one provider
registered. Ends with a "known limitations" section (see below) that is reported,
not counted as a discrepancy.

## Root scripts — one file per subsystem (165 checks)

Every one of these used to `shutil.copy(data/radar.db, tmp)` and assert against
whatever the live numbers happened to be that day — the audit
(`reports/audit/01-branch-comparison.md` §3.7) found 8 of 153 checks failing purely
from that coupling (the database had grown since the assertions were written), plus
`check.py` failing 1 of 15 on a since-explained frame gap. All 12 now build their own
small SQLite file from `db.SCHEMA` with exactly the rows the check needs — nothing
here reads or depends on the state of `data/radar.db`.

| File | Covers | Checks |
|---|---|---:|
| `test_baseline.py` | author comparison base across snapshots: no double-counting, freshest measurement wins, history grows | 6 |
| `test_roster.py` | liveness / dropout: two misses in a row (12+ days apart) drops an account, one waits, a skipped snapshot doesn't penalize, a silent account does | 11 |
| `test_topup.py` | paid search+neighbor stage vs free-profile stage, threshold rejection, resuming after the free source rate-limits | 16 |
| `test_posts.py` | published-topic memory window (6 weeks), six-number metrics entry, partial updates | 12 |
| `test_journal.py` | tool log: add/close, the 30-day window, kind validation | 10 |
| `test_cards.py` | card selection: 3 formats x 3 slots, one card per author, closed topics sink but aren't dropped, used references excluded, Teardown only on topics repeated across ≥3 authors (and placeholder topics don't count) | 20 |
| `test_deep.py` | deep-dive queue: freshness window, per-author cap, already-analyzed reels skipped, timecodes | 16 |
| `test_collect.py` | snapshot collection: spend accounting, dropped accounts skipped, re-run doesn't duplicate | 19 |
| `test_topics.py` | topic tagging: regex matches, full manual coverage of the deep-dived top, sample size cap, reproducible sampling | 9 |
| `test_score.py` | scoring formula safeguards (no live DB — hand-built reel dicts) | 15 |
| `test_pipeline.py` | empty-database orchestration, speech-block split, step ordering | 19 |
| `test_notion.py` | Notion push/pull on a faked transport: all of a week's cards exported, human-touched pages not overwritten, decisions read back, rejected cards excluded from the next pool | 12 |

## `tests/` — pytest suite (241 passed, 1 skipped)

Owned by other agents; listed here only so the two suites' combined coverage is
visible in one place.

| File | Covers | Cases |
|---|---|---:|
| `test_engine_schema.py` | `engine.schema` / `engine.state` / `engine.migrate_legacy` migrations | 39 |
| `test_notion_sync.py` | `engine.notion_sync` / `engine.notion_blocks` on a faked transport | 35 |
| `test_stats.py` | creator statistics on a synthetic corpus with known-by-construction answers | 27 |
| `test_production.py` | `engine.production` / `engine.storage` on a synthetic ffmpeg-built video | 26 |
| `test_providers.py` | `engine.providers` / `engine.hiker_config` environment + fake transports | 25 |
| `test_lexical.py` | feature extraction on three hand-annotated transcripts | 23 |
| `test_local_pipeline.py` | `engine.scenes` / `local_pipeline` / `align` / `watchdog` on a synthetic video; 1 case marked `slow` and skipped by default | 22 (1 skipped) |
| `test_hiker_client.py` | `lib/hiker.py` transport, retries, cache — on a fake transport | 13 |
| `test_cards_v2.py` | `engine.cards_v2` / `storyboard_render` / `edl` against a fixture card | 12 |
| `test_ingest_insights.py` | `engine.ingest_insights` payload validation, `--dry`, idempotency | 11 |
| `test_charts.py` | `engine.charts` on a synthetic corpus | 6 |
| `test_pdf_build.py` | `engine.pdf_build` / `tools/pdf/md2pdf.mjs` on a synthetic markdown set | 3 |

## Known issues (surfaced by `check.py`, not hidden by weakening a check)

- **8 frames flagged `frames.exists_ok=0`** — all belong to `DcxV37-CJOC`, a
  confirmed truncated download. `check.py` reports these under "known limitations"
  and does not count them as a discrepancy; a *new* missing frame (any file gone
  missing without the flag) still fails the check.
- **`tag_topics.py`'s "top" query joins reels to the caption in the current latest
  snapshot only** (`WHERE r.snapshot_id = <latest>`). A deep-dived code whose only
  `reels` row lives under an earlier snapshot (normal once the database has more
  than one) has no caption visible to that join, so a from-scratch re-tag
  (`DELETE FROM topics` + `tag_topics.tag()`) will not manually-tag it — confirmed
  against the live database (219/282 on this checkout after a full wipe+retag,
  reports/audit/01-branch-comparison.md §3.7). At rest this does not currently show
  up as an untagged deepdive (topics accumulate across runs and nobody wipes the
  table), so `check.py`'s `разборов без темы` line only prints when the count is
  nonzero. `tag_topics.py` is a pipeline script outside Test-Health's owned files
  (root `test_*.py`, `check.py`, `pytest.ini`, `tests/conftest.py`, this file) — the
  fix is a caption lookup that isn't pinned to the single latest snapshot (e.g. the
  same "latest known row per code" pattern `baseline.latest_rows()` already uses),
  which belongs to whoever owns `tag_topics.py`.
- **`test_notion.py`'s previous failure was a test bug, not a `notion.py` bug**: it
  read `SELECT code FROM cards LIMIT 1` with no `WHERE week=?` and no `ORDER BY` to
  find "a card from this week" — harmless while `cards` held one week's worth of
  rows, wrong once it accumulated 23 rows across several weeks (it could return a
  card from a different week entirely). `notion.py`'s own push/pull matching (by
  `Reference` URL) was not touched and needed no fix. Fixed by scoping every such
  query to the week under test.
