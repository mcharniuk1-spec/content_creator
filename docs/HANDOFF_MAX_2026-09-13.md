# Handoff to Max — the radar on 13 September 2026

Written 2026-09-13 (evening) for Max. Supersedes `docs/HANDOFF_MAX_2026-09-12.md` for the
selection and card layer; the engine architecture in that document still holds. Every number
below is read from the repository or from `data/radar.db` on the server (`/opt/radar`, branch
`main`). Russian originals of the rules are in `RULES.md`; the English rendering is
`docs/RULES.en.md`. The Notion side lives under the Content Engine Tool page
(`3d00bd21ed6a800fb0ffda652e539ef1`).

## 1. TL;DR

1. Misha's decisions of 13 September, in order: personas are **not** the selection axis any more;
   the axis is nine **content blocks**; the weekly output is a **shortlist of 15 reels in three
   stages** from which he picks 5; each shortlisted reel becomes a **decision card** (what they shot
   and what it did, our version, the shoot plan by parts); and a reel exists for cards **only with a
   full English transcript and frames** (the evidence gate). All of it is in code, tests, RULES §13,
   the server and Notion.
2. The first shortlist under the new rules is in Notion, database **Shortlist**
   (`3da0bd21-ed6a-81e3-98bc-ec2baa710ce7`), 15 rows, and in
   `reports/shortlist/2026-09-13-cards.md`. Misha's verdict: the card format is right, but only
   **6 of 15** had the evidence the rules now require (1, 3, 4, 9, 14, 15); the rest were built from a
   caption alone or from Hindi speech. That is what produced the evidence gate (§13.7).
3. Root cause of the language error: both local ASR paths (`deep.py`, `engine/local_pipeline.py`)
   ran Whisper with `language='en'` forced, which **translates** Hindi speech into English. Both now
   detect the language. Older transcripts without a `ta-v1` file may still carry a wrong language.
4. The old Notion **Cards** database (`NOTION_CARDS_DB` in `.env`) is in the Notion trash. `notion.py`
   detects an archived or invisible database and writes to **Shortlist** instead (id cached in
   `data/notion_ids.json`). Nothing else changed in your databases.
5. The weekly run (`cron.sh`, Monday and Thursday 07:00 server time) now includes: block routing by
   an agent (only reels without a file), the shortlist, the decision cards, the Notion push to
   Shortlist, and `data/runs/<date>/shortlist.md`. Next run: **Monday 2026-09-14, 07:00**.
6. A **project-manager agent** (Sonnet 5, `prompts/pm.md`, `pm.sh`) runs daily at 08:30 and after each
   weekly run. It is read-only on code and data; it writes `data/pm/latest.md` and applies it to the
   Execution Review page under "Project manager", with kanban drift, rule compliance and failures.

## 2. The rules now in force (RULES.md §13)

| Rule | Where in code | Test |
|---|---|---|
| Nine content blocks; a reel gets one block | `content_blocks.py` (BLOCKS, classify, route) | `test_cards.py` routing block |
| Block by agent first (br-v1), tags + regex as fallback | `engine/block_route.py`, `engine/prompts/block-route.md`, files `data/analysis/blocks/<code>.json` | `test_cards.py` agent override |
| Agent says "off niche / no text" (null block) → reel leaves the pool | `content_blocks.route` + `cards._pool` | `test_cards.py` |
| Shortlist 15: stage 1 one per block above the author norm; stage 2 by shares + saves, cap 3 per block; stage 3 Misha picks 5, max 2 per block (checked by `cards.py show`) | `cards.select`, `cards.pick_violations` | `test_cards.py` |
| Decision card per shortlisted reel (sa-v1): original + result, our version under the four-part filter, shoot plan by parts, optional CTA with a real artefact | `engine/shortlist_adapt.py`, `engine/prompts/shortlist-adapt.md`, files `data/analysis/shortlist/<code>.json` | `tests/test_shortlist_adapt.py` |
| Evidence gate: full transcript (last speech segment ≥ 90 % of the duration, ≥ 30 words), frames > 0, English speech (`ta-v1` language, else `transcripts.lang`) | `cards.evidence`, `cards._pool(require_evidence=True)` | `test_cards.py` E1–E4 cases |
| `deep.py` takes the pool **without** the gate (it produces the evidence) | `deep.pick` | `test_deep.py` |
| Personas (Rick, Emma, Anna) are the example layer inside a block, not a filter | `personas/*.json`, prompt `shortlist-adapt.md` | `tests/test_personas.py` |

Process the gate follows from (`run.py` steps 1 → 2 → 3 → 8): collect reels per blogger → select the
ones above their author's norm (1.5×) → download and fully transcribe those with frames while the
video links are alive (`deep.py`) → only then is the reel a candidate. The `reels` table keeps every
collected reel as raw material for the author norm; the working base is the pool `cards._pool()`.

## 3. Numbers on the server tonight

| Measure | Value |
|---|---|
| Reels in the 30-day window (before any gate) | 580 |
| Routed by the agent (br-v1 files, 0 errors) | 580 |
| Agent disagreed with tags + regex | 313 |
| Marked off-niche by the agent (leave the pool) | 153 |
| Pool after the evidence gate | 105 |
| Dropped: no full transcript / not English / no frames | 460 / 4 / 0 |
| Shortlist of 13 Sep (built before the gate) | 15 of 15, all nine blocks at stage 1 |
| Decision cards validated (sa-v1) | 15 of 15 |
| Cards with full evidence by the new rule | 6 of 15 |
| Transcripts in the base / with ta-v1 | 281 / 126 |
| Tests | local 358 passed, 1 skipped; server 353 passed, 6 skipped |

The pool of 105 is small because transcription only ever covered the top of the ranking. The
Monday run transcribes the new top (deep.py, N=100) and the watchdog continues after it; the pool
will grow week by week without paid re-fetches (Misha, 12 Sep: no Hiker re-fetch of old reels).

## 4. What runs on Monday, in order

1. `cron.sh` → `git pull --ff-only`, Hiker config check, `run.py --yes`.
2. `run.py`: collect (HikerAPI, paid) → score against the author norm → deep dive of the top with
   local Whisper (language detected) and frames → topic tags → followers → roster check → Notion
   pull → **step 8**: block routing (`engine.block_route run`, only reels without a file), shortlist
   (`cards.select`, gate on), decision cards (`engine.shortlist_adapt run`) → delta → Notion push of the
   shortlist (`notion.py push` → Shortlist DB, Block and Stage properties, body from the sa-v1 file) →
   stats → full DBs → pages.
3. `cron.sh` continues: angles agent (`prompts/angles.md`), `notion.py push` again, pages, then
   `data/runs/<date>/shortlist.md`, then watchdog (`--limit 40`), `analyze_pending` (ta-v1 / fa-v1 for
   new reels), features, then **`pm.sh`** (project-manager note → Execution Review).
4. `pm.sh` again daily at 08:30.

Budgets inside `run.py` step 8: block routing 3600 s, adaptation 2700 s. Each `claude -p` batch is
5–9 minutes; a batch that dies on a Claude subscription limit is recorded as RETRY_REQUIRED and the
module re-run only does the missing files (`python3 -m engine.block_route run --yes`,
`python3 -m engine.shortlist_adapt run --yes`).

## 5. Notion map

| Object | Id | Generated by |
|---|---|---|
| Content Engine Tool (dashboard page) | `3d00bd21ed6a800fb0ffda652e539ef1` | `engine.notion_sync --apply --scope dashboard` |
| Shortlist (weekly cards, 15 rows for 2026-09-13) | `3da0bd21-ed6a-81e3-98bc-ec2baa710ce7` | `notion.py push` |
| Execution Kanban (tasks + stages) | `3da0bd21-ed6a-813b-a968-e8ea7b1c6504` | `engine.notion_kanban --apply` |
| Execution Review (argumentation, review, plan, project-manager note, stage trace) | `3da0bd21-ed6a-8113-9cb3-db428cb72f93` | `engine.notion_kanban --apply` |
| Runs, Insights, Hypotheses, Cards v2, Reels analysis, Accounts analysis, Categories, Personas | `data/notion_ids.json` on the server | `engine.notion_sync --apply` |
| Cards (legacy, 7–12 Sep) | in the Notion trash | not written any more |

The Notion API cannot create Board views: switch Shortlist and Execution Kanban to a board by hand
if you want columns by Status / Block.

Misha's feedback of 13 Sep on the Shortlist cards was left in Notion between 19:12 and 19:25 (page
edit timestamps); the integration cannot read inline comments, so the substance is recorded here
from his message in chat: the two rules of §13.7 (no card without a full transcript and frames; English
speech only, a caption is not enough).

## 6. Open for you

1. The export of your 1,062 transcripts and 19,808 frames is still the fastest way to widen the pool
   under the evidence gate (import path in `docs/HANDOFF_MAX_2026-09-12.md` §3.1). Language must be
   stored per transcript; anything not English will be dropped by the gate, which is intended.
2. Roster: the 13 Sep shortlist addressed Anna or Emma in 11 of 15 cards and Rick in 3. Misha rejected
   widening the roster per persona; if you want more local-services material, that is a decision for
   him, not a rule.
3. Board views in Notion (above).
4. Read `data/pm/latest.md` (or the "Project manager" section of Execution Review) each morning:
   it lists kanban drift and failed jobs with the exact re-run command.

## 7. Commits of 13 September (main)

`31d4f622` content blocks + shortlist 15 · `7ed061c` block routing by agent · `e32041c` shortlist
adaptation (sa-v1) · `e1980b3` weekly run wiring · `9eee8ce` / next: Notion Shortlist fallback ·
`Evidence gate` (two commits) · this handoff, PM agent and cron. Full list: `git log --since=2026-09-13`.
