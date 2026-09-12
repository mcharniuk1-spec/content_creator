# 6. State Tracing

State tracing is the one capability main's legacy pipeline never had. `run.py` is a linear,
13-step script with a `tool_log` table for human notes but no machine state: if step 7 dies, the
only recovery is rerunning from step 1. The engine adds a three-layer model, adopted from Max's
`origin/Latest` orchestrator and trimmed from his 41-stage DAG (29 of which had no implementation)
to the 25 stages this branch actually runs.

## The three tables

`runs` (one row per pipeline execution, `kind` ∈ `weekly|watchdog|analysis|cards|manual`) → `jobs`
(one row per processing step, indexed on `entity_kind, entity_id, stage`) → `video_state` (the
always-current, never hand-written summary, one row per code). `jobs.state` ∈ `PENDING|RUNNING|
DONE|FAILED|RETRY_REQUIRED|SKIPPED`; the `job()` context manager (`engine/state.py`) always writes
`RUNNING` on entry and closes `DONE` on a clean return unless the step explicitly called
`handle.skip(reason)` or `handle.retry_required(reason)`, or closes `FAILED` with the exception
text on any raised error. There is deliberately no `handle.pending()` — nothing in this contract
can close a job row as literally `PENDING`; a "nothing to do yet" condition (e.g. no supplied takes
exist) is mapped to an honest `SKIPPED` job row whose *business-level* summary separately reports
`PENDING`.

## Canonical stage list (`jobs.stage`, 25 stages, pipeline order)

```
DISCOVERED, PROFILE_FETCHED, VIDEO_METADATA_FETCHED, STATS_FETCHED, MEDIA_FETCHED,
TRANSCRIPTION, TRANSCRIPT_ANALYSIS, FRAME_EXTRACTION, FRAME_ANALYSIS, ALIGNMENT,
GENERAL_ANALYSIS, STATISTICAL_ANALYSIS, CATEGORIZATION, REFERENCE_SELECTION,
CONCEPT_GENERATION, CARD_GENERATION, SCRIPT_GENERATION, SCRIPT_REVIEW, FRAME_PLAN,
FRAME_GENERATION, VIDEO_GENERATION_READY, VIDEO_RENDER, QUALITY_REVIEW, NOTION_SYNC,
COMPLETED
```

Two of these — `VIDEO_RENDER` and `QUALITY_REVIEW` — are named in the canonical list but **no
module in this branch writes them yet**: a render can run for minutes, and whether to trace it as
one job is left to the operator (`docs/PRODUCTION_PIPELINE.md` §5 gives the manual trace command),
not automated by `engine.production`.

## `video_state`: the always-current summary

Every column is *derived*, never hand-set — `engine.state.compute_video_state()` is a pure
function over `reels`/`transcripts`/`frames`/`scenes`/`beats`/`frame_labels`/`video_features`/
`deepdives`. Columns: `media_state` (`UNKNOWN|AVAILABLE|EXPIRED|MISSING|DOWNLOADED`),
`transcript_state` (`MISSING|PENDING|DONE|EMPTY_NO_SPEECH|FAILED`), `frames_state`
(`MISSING|PENDING|DONE_FIXED9|DONE_SCENE|FAILED|PARTIAL`), `alignment_state`
(`MISSING|DONE|NOT_POSSIBLE`), `analysis_ready` (1 only when transcript DONE + frames DONE_* +
both semantic analyses DONE), `corpus_tier` (`ANALYSIS_READY|FRAMES_ONLY|INGESTED_NOT_ANALYZED`),
and `flags_json` (the sorted damage-flag list, chapter 10).

## Example trace, run against the real database in this session

Code `DBKJLzavogz` (creator `tech_with_tim`, 62,204 plays, 27.4s duration) was picked as the first
`ANALYSIS_READY` code returned by `SELECT code FROM video_state WHERE corpus_tier='ANALYSIS_READY'
LIMIT 1`. The canonical trace query and its live result:

```sql
SELECT stage, state, started_at, finished_at, duration_s, error
FROM jobs WHERE entity_kind='video' AND entity_id='DBKJLzavogz' ORDER BY started_at;
-- returns 0 rows

SELECT media_state, transcript_state, frames_state, alignment_state, analysis_ready,
       corpus_tier, flags_json
FROM video_state WHERE code='DBKJLzavogz';
```

| media_state | transcript_state | frames_state | alignment_state | analysis_ready | corpus_tier | flags_json |
|---|---|---|---|---|---|---|
| EXPIRED | DONE | DONE_FIXED9 | DONE | 1 | ANALYSIS_READY | `[]` |

**What this returns, and what it does not.** The `video_state` half answers the question
completely and matches the architecture contract: this code's media link has expired (as expected
— every legacy video is deleted after frame extraction, chapter 7), its transcript and frames are
both done, alignment has completed, and it carries no damage flags. For this video code the `jobs` query returns no rows — its transcript and frames were produced by
the legacy `deep.py` pass before the state-tracing tables existed, and the migration backfills
`video_state` by direct computation rather than inventing historical jobs. The tables are not
empty, however: at the final build `runs` holds 7 runs (5 `analysis`, 2 `cards`) and `jobs` 265
rows. The card-finalisation runs traced every card through six stages (15 rows per stage: the first five cards were finalised twice, once before and once after the storyboard renderer was reworked):

| stage | state | jobs |
|---|---|---:|
| CARD_GENERATION | DONE | 15 |
| FRAME_GENERATION | DONE | 15 |
| FRAME_PLAN | DONE | 15 |
| SCRIPT_GENERATION | DONE | 15 |
| SCRIPT_REVIEW | DONE | 15 |
| VIDEO_GENERATION_READY | DONE | 15 |

and the analysis runs traced the insight, hypothesis and reference ingest (`GENERAL_ANALYSIS` = insights, `CONCEPT_GENERATION` = hypotheses, `REFERENCE_SELECTION` = hypothesis references; the ingest was re-run, so counts include repeats):

| stage | state | jobs |
|---|---|---:|
| CONCEPT_GENERATION | DONE | 120 |
| GENERAL_ANALYSIS | DONE | 5 |
| REFERENCE_SELECTION | DONE | 50 |

What is still missing is a traced *collection* and *watchdog* run on the server: those stages
(download, transcribe, extract, align — one row each) exist as a mechanism and are unit-tested
(39 tests in `tests/test_engine_schema.py`, 21 in `tests/test_local_pipeline.py`), and will
appear as observed history after the first scheduled run under the new schema. Any future report claiming a specific stage's timing or retry count for a specific code must
first confirm `jobs` is non-empty for that code rather than assuming the contract has been
exercised.

## Cards trace (Phase 3)

For a card in production: `SELECT stage, state, started_at, error FROM jobs WHERE
entity_kind='card' AND entity_id='<card_id>' ORDER BY started_at`. `engine.production.ingest_takes`
does write real `jobs` rows at `VIDEO_GENERATION_READY` — verified in `tests/test_production.py`'s
26 cases, including the full happy path that probes a real synthetic MP4 and writes a real `jobs`
row — but that verification ran against a test fixture database, not this repository's live
`data/radar.db`, which is why the direct query above returns nothing for either entity kind today.
