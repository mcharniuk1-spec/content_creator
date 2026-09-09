# Check: content-plan.md / content-plan.json

Checked against `data/top-reels.csv`, `radar-0907.db` (sqlite3, read-only),
`runs/2026-09-07/README.md`, `data/topics.csv`, `m2lab-brand/brand/04-06.md`,
`m2lab-brand/stickers/manifest.json` + `README.md`, `notion-raw/10..19`.

## Per-topic

| # | Data | Filter (4Q) | Hook (words/chars) | Banned words | Overlap w/ Max | Notes |
|---|---|---|---|---|---|---|
| 01 | OK exact (views/shares/saves/z/dur/median all match CSV+DB) | OK, 4 yes, honest | OK 8w, lines 20/20 | clean | none found | plate=oxide + paper stickers = correct pairing |
| 02 | OK exact; spend $12.46/623 units = DB `spend` rows 1-7 sum exactly; cards 9/4 = DB `cards` week 2026-09-07 exactly | OK, 4 yes | OK 8w, 20/19 | clean | none found | plate=ink but stickers 27, 50 are Paper-surface → mismatch (see Stickers below) |
| 03 | OK exact | OK, 4 yes | OK 7w, 17/19 | clean | none found | plate=oxide, stickers correct pairing |
| 04 | OK exact; $2.12/106 = DB `spend` row 8 exactly; 78 min = 07:00–08:18 in `runs/2026-09-07/README.md` exactly | OK, 4 yes | OK 8w, 20/19 | clean | none found | plate=ink, stickers 21, 19 are Paper-surface → mismatch |
| 05 | No reference reel (by design); topic-tag numbers (29 reels/0.473 median/0 top100; 80/5; 117/9) match `topics.csv` exactly; "3 reels, 6 of top 15" verified against `top-reels.csv` top-15 by z (aiforbusinesses247 x3 codes, 2 snapshot-rows each = 6) | OK, 4 yes | OK 8w, 19/17 | clean | none found | plate=ink, stickers 39, 43 are Paper-surface → mismatch |
| 06 | OK exact; 1,260/1,255/1,156/97 all match `runs/2026-09-07/README.md` and `radar-data.md` §6 exactly | OK, 4 yes | OK 8w, 20/17 | clean | thin thematic overlap with I03 ("one job before subscription" = ranking/deciding) but no shared hook or premise | plate=ink, stickers 30, 15 are Paper-surface → mismatch |
| 07 | OK exact (both primary and supporting reel) | OK, 4 yes | OK 8w, 19/20 | clean | none found | plate=ink, stickers 32, 18 are Paper-surface → mismatch; 2nd cover line lowercase while 01/03/06 capitalize an equivalent second-sentence start — cosmetic inconsistency only |
| 08 | OK exact | OK, 4 yes | OK 8w, 20/20 | clean | thematic overlap with **P04** "ask for the awkward case before buying automation" (both: interrogate a pitch/proposal before adopting, name the unanswered step) — not a hook/premise duplicate | plate=oxide, stickers correct pairing |
| 09 | OK exact (both primary and supporting reel) | OK, 4 yes | OK 8w, 18/20 | clean | thematic overlap with **P05** "add a failure column to your AI shortlist" (both: a check that catches what a polished output misses) — not a hook/premise duplicate | plate=ink, stickers 40 (ink), 54 (ink) — **only topic with correct surface pairing on an ink plate** |
| 10 | OK exact, all 5 combined reels re-verified | OK, 4 yes | OK 8w, 19/19 | clean | none found beyond the five references it already declares | plate=ink, stickers 26, 50 are Paper-surface → mismatch |

`node checks/lint.mjs --copy` on both files: **"lint: clean — 0 error(s), 0 warning(s)"**. Independently re-counted every cover's word count (7-8) and per-line character count (≤20) by script; matches lint. No em-dash, no banned-vocabulary hits.

## Structure (§4)

5 Intro (4 by reference: 01-04, 1 new: 05) + 5 Regular (4 by reference: 06-08,07, 1 synthesis: 10) — counts match spec exactly.
Recommended six (02,03,04,06,09,10): content-plan's own math holds — 03 is the pinned intro sitting outside the weekly cadence, leaving 04+10 Radar, 06+09 Builds, 02 Teardown = 2/2/1 as claimed.

## Overlap with Max — factual problem found

Content-plan.md (lines 25-34) states cards **15-19 "are absent"** from `notion-raw/`. This is **false**: `notion-raw/15-card-...md` through `19-card-...md` (M2-P01 to M2-P05) exist and are fully readable, dated 2026-09-07, before the plan's 8 Sep write date. The plan's 5-point differentiation vs Max was therefore checked against only half of Max's ten cards (I01-I05). Re-checked P01-P05 directly: no exact hook or premise is duplicated, but two thematic overlaps exist (topic 08 vs P04, topic 09 vs P05 — noted above). Separately, point (1) "every one says imagine or suppose" is not literally true of I04 (uses "fictional"/"say you want" instead) — same fictional-framing substance, imprecise wording. Points (2) no tool/number and (3) no verdict label in Max's cards: verified true (only ordinary-English "test/keep" verbs, no KEEP/TEST/KILL construct, no digits in spoken scripts).

## Freshness

All 10 "why now" claims carry an explicit date (11 Aug, 1-2 Sep, 7 Sep, 8 Sep) or a measured cross-snapshot signal (topic 08). None asserted without a source.

## Stickers — surface/plate mismatch (brand rule, beyond "exists in manifest")

All 18 sticker names exist exactly in `manifest.json`. But `stickers/README.md` requires picking the Ink-surface variant (files 51-65) on an Ink-ground cover; Paper-surface stickers "go blind on an Ink ground." Six of ten covers (02, 04, 05, 06, 07, 10) use `plate: "ink"` with stickers whose manifest `surfaces` is `["paper"]` on both slots — a real legibility failure if built as specified. Only topic 09 pairs `plate: "ink"` with true Ink-surface stickers (40, 54). Topics 01, 03, 08 use `plate: "oxide"` (paper ground) with Paper stickers — correct.

## Verdict: PASS WITH FIXES

1. Fix the "15-19 absent" claim in content-plan.md lines 25-34 (they exist) and add the two thematic-overlap notes (topic 08 vs P04, topic 09 vs P05) to that section, or explain why they're not real duplicates.
2. Swap the stickers on topics 02, 04, 05, 06, 10 (and 07) to their Ink-surface equivalents wherever one exists (e.g. 15→54 already proven), or move those covers to `plate: "oxide"`/paper.
3. Optional/cosmetic: make topic 07's second cover line capitalization consistent with the 01/03/06 pattern if it's meant to read as two sentences.

Everything else — every reference metric, every internal number (spend, cards, run counts, wall clock), topic-tag counts, structure counts, banned-vocabulary/hook-length lint, and freshness sourcing — checks out exactly against the data.
