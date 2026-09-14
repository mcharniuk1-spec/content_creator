# Handoff to Max — the radar on 14 September 2026

Previous handoffs: `HANDOFF_MAX_2026-09-13.md`, `HANDOFF_MAX_2026-09-12.md`. They stay as they
were written; this one carries what changed since.

## 1. TL;DR

The first scheduled run under the new selection rules produced **zero cards**, and the cause was
plumbing, not data. It is fixed, and two rules you rely on have changed.

- The weekly run of Monday 07:00 collected fine — 1534 reels, 1400 past the threshold — and was
  then **killed by its own watchdog** at reel 60 of 100 in the deep-dive. Everything after step 3,
  cards included, never ran.
- Each heavy step now has **its own time budget**; the outer `timeout` in `cron.sh` is a guard
  again, not a working limit.
- `cron.sh` no longer gates the week's output behind a perfect exit code.
- **Freshness window is back to 14 days.** This cancels point 1 of the 12 September rules.

## 2. What actually happened

| Step | Result |
|---|---|
| 1. Collect | 130 accounts, 1534 reels, 130 units spent |
| 2. Score against the creator's own baseline | 1529 scored, 1400 above threshold |
| 3. Deep-dive of the top of the window | **stopped at 60 of 100** |
| 4–13 (topics, followers, pruning, Notion, **cards**, delta, pages) | never started |

Two mechanisms combined.

**One stopwatch for thirteen steps.** `cron.sh` ran the pipeline as `timeout 7200 python run.py`.
That two-hour limit was meant as protection against a hung process, but it was also the only
limit the deep-dive had. A reel costs roughly two minutes end to end, so a hundred reels cannot
fit in two hours under any circumstances. The process was killed by SIGTERM at 09:00.

**All-or-nothing publication.** The angles agent, the Notion push and the week's pages sat behind
`if [ $code -eq 0 ]`. The run exited 124, so all of it was skipped — even though 60 deep-dived
reels were already more than enough to build cards from.

## 3. What changed in the code

Commits `b9b2305c` and `c33e30d7` on `main`, deployed to the server, all tests green.

- `run.py` — `DEEP_BUDGET_S = 100 min`. `deep.run()` takes a `deadline` and stops on what it has;
  the step is recorded as `PARTIAL`, not `OK`. Nothing is lost: `deep.pick()` excludes only reels
  already in `deepdives`, so the remainder heads the queue on the next run.
- `cron.sh` — outer timeout 7200 → 21600 s. The `if [ $code -eq 0 ]` gate is gone; an incomplete
  run says so in the log and the week's output is assembled from whatever is in the database.
- `run.py` — SIGTERM is turned into `SystemExit` so the `finally` block still closes the run as
  `INTERRUPTED`. Before this, a killed run stayed `RUNNING` for ever, and the PM agent read one of
  those at 08:30 and reported a live run two hours after its death.
- `engine/state.py` — `sweep_stale_runs(con, max_age_h=12)`, called from `start_run`.
- `deep.py` — the window constant, plus a per-reel timing split printed every ten reels.

## 4. Rules changed — read this before you trust a pool number

**Freshness window is 14 days again** (`cards.FRESH_DAYS`, and the mirrored `WINDOW` in `deep.py`,
`pages.py`, `stats.py`, `tag_topics.py`, `notion_db.py`). The reason is resources: 30 days lifted
the pool from 119 to 596 candidates and the server cannot take the top of that apart in one run.
Every other decision of 12 September stands — one ladder of shares + saves per thousand, the
creator-level pool gate, comment-keyword CTAs allowed.

Note for your own numbers: **the window does not set how many reels enter the deep-dive.** That is
`deep.N = 100` and now the time budget. A narrower window only means the pool is sometimes smaller
than `N` — it was 85 on 10 September.

## 5. One measurement, so you don't repeat it

The obvious suspect for the per-reel slowdown was the 13 September switch from forced English to
language detection in ASR. It is **not** the cause. Same reel, same machine:

```
forced en (before 13 Sep)   102.9 s
auto-detect (current)        98.5 s
forced en, repeat           106.8 s
```

Per-reel cost still went from ~46 s (10 Sep) to ~114 s (14 Sep) with no change in file size
(8.3 MB → 7.0 MB) or reel length. `deep.run()` now prints where the time goes — download, frames
and cuts, transcription — every ten reels, so the next run answers this for free rather than by
guesswork.

## 6. Open

- **HikerAPI price in the code is 20x too high.** `lib/hiker.PRICE_RECEIPT` says $0.02 per unit,
  but Misha's balance of $101.5 against 101478 units works out to $0.001. A run costs about
  $0.13, not $2.60. Not changed yet — it needs a look at the billing page first.
- A `CONCEPT_GENERATION` job has been sitting at `RETRY_REQUIRED` since 13 September 15:43.
- The dated handoffs of 12 and 13 September still quote the 30-day window. They are snapshots of
  their date; `RULES.md`, `docs/RULES.en.md` and this document are the current ones.
