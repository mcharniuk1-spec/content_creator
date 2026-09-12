# 06 — Final QA audit

Auditor: independent read-only pass, 2026-09-12.
Scope: branch `content-engine`, repo `/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar`.
Nothing outside this file was written or modified. No git command other than `status` /
`ls-files` / `check-ignore` was run.

---

## Verdict: **PASS WITH FIXES**

The engine is sound. Every traceability chain I walked closes end to end, every reference
metric in every card reproduces from `video_features` and `reels` to the digit, the scripts
share **zero** 5-grams with any transcript in the corpus, the positioning filters are complete
and correctly aimed at the viewer's process, both test suites pass clean, and no secret is
present anywhere in the tree.

What stops this being a plain PASS is five things: two layout defects that make the shipped
PDFs unfit to hand to anyone (a footer that eats the last line on 55 pages, and a card-book
image that never renders and prints Misha's home directory instead), one numeric error
propagated from a source insight into five documents, both PDFs and a card's claim register,
one false statement about the database contradicted by another deliverable in the same set,
and `PRODUCTION.md` still carrying three figures that this very analysis proves wrong.

None of the five requires re-running the pipeline. All five are edits.

| Area | Result |
|---|---|
| 1. Number consistency (57 claims recomputed) | 6 mismatches, 5 internal inconsistencies |
| 2. Traceability (3 cards + all 10) | Chain intact; 3 unpopulated link columns |
| 3. Originality (10 cards × 266 transcripts) | **Clean — 0 shared 5-grams anywhere** |
| 4. Positioning rules (10 cards) | **Clean — no violations** |
| 5. Secrets | **Clean — no hits; `.env` ignored, untracked** |
| 6. Required files + PDFs | 1 file absent; 2 PDF defects |
| 7. Tests | **252 passed, 1 skipped; `check.py` 23/23** |

---

# Findings

## BLOCKER

### BL-1 · The footer masks the last line of body text on 55 pages across both PDFs

The footer band is fixed at y 761.3–771.7 pt on every page; the text frame runs to ~774 pt,
so there is no reserved bottom margin. On 20 of the affected pages the last line is not
merely crowded, it is **cut in half by the footer glyphs**.

- `reports/final/M2RADAR_ANALYTICAL_REPORT.pdf` — 33 of 132 pages overlap.
  Severe (>6 pt into the band): pp. **6, 38, 43, 68, 79, 83, 90, 114, 117, 121, 129**.
  Minor (2–6 pt): 8, 16, 22, 24, 27, 45, 53, 67, 76, 86, 89, 107, 115, 118, 125, 126.
  Hairline: 3, 5, 17, 20, 60, 72.
- `reports/final/M2RADAR_CARD_BOOK.pdf` — 22 of 105 pages overlap.
  Severe: pp. **38, 53, 66, 74, 78, 84, 87, 95, 98**. Minor: 21, 25, 28, 34, 63, 64, 86, 94,
  97, 101, 103. Hairline: 67, 83.

Rendered and inspected visually at 60 dpi: p8 of the analytical report loses the last table
row ("Naming specific tools/numbers…", row number breaks as "1 / 0", cell truncated at
"that pro"); p38 reads `produces s | M2RADAR — … | rom`; p43 `…words per second, cu | footer |
bust_z`; card book p38 `name. Wha | footer | e a run`; p78 `separated | footer | n day one.`;
p98 `than a con | footer | lief of`.

**Fix:** raise the bottom margin of the text frame in the PDF builder above y=755 pt (reserve
~20 pt for the footer band) and rebuild both PDFs.

### BL-2 · The card book never renders the contact sheet and prints a local filesystem path instead

On every one of the 10 card chapters the contact-sheet image leaks as raw Markdown:

```
![Contact sheet](/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar/cards/frames/C-2026-09-12-01_sheet.png)
```

Pages **13, 21, 32, 42, 52, 62, 72, 82, 92, 101** of `M2RADAR_CARD_BOOK.pdf`. The PNG files
themselves all exist (`cards/frames/C-2026-09-12-*_sheet.png`, 10 of 10). So the image is
available and simply is not converted; a distributable document instead carries the owner's
home directory. The analytical report has no such leak.

**Fix:** make the card-book Markdown→PDF step resolve `![...](abs path)` to an embedded image
(or emit a repo-relative path the renderer resolves), then rebuild.

### BL-3 · "Nine of the thirteen RELIABLE correlations are save-rate" — it is eleven

Recomputed from `reports/data/associations.json` (the file's own `spearman` array, 460 pairs):

```
RELIABLE = 13.  By metric: save_rate 11, share_rate 1, view_lift 1, robust_z 0.
save_rate rows: lex_platforms_n +0.331 · lex_cta_verb_n +0.241 · lex_questions_per_10s -0.235
  · questions_n -0.229 · lex_questions_n -0.229 · lex_second_person_n +0.206 · blk_hook_wps
  +0.205 · blk_hook_segments +0.198 · lex_rhetorical_questions_n -0.186 · lex_first_person_n
  -0.180 · lex_direct_address_per_100w +0.174
```

`questions_n` and `lex_questions_n` are the same feature under two names, so the honest
phrasing is **eleven of the thirteen, ten distinct features** — which is exactly what
`reports/analysis/01-general-conclusions.md:316` and
`reports/final/partB/30-cross-video-conclusions.md:25` already say. Seven other places say nine.

Root cause: `data/analysis/insights.json` I-22 stores `reliable_save_rate_pairs: 9` alongside
`reliable_pairs: 13`, `reliable_share_rate_pairs: 1`, `reliable_view_lift_pairs: 1` — numbers
that do not add up (9+1+1+0 = 11 ≠ 13). The same values are in the `insights` table:

```sql
sqlite> SELECT json_extract(evidence_json,'$.numbers.reliable_pairs'),
               json_extract(evidence_json,'$.numbers.reliable_save_rate_pairs')
        FROM insights WHERE insight_id='I-22';
13|9
```

Propagated to:

| location | text |
|---|---|
| `data/analysis/insights.json` I-22 + `insights` table | `reliable_save_rate_pairs: 9` |
| `reports/analysis/02-what-viewers-seek.md:14` | "Nine of the thirteen" |
| `reports/analysis/08-hypotheses.md:406` | "Nine of the thirteen RELIABLE correlations" |
| `reports/final/partB/26-performance-analysis.md:32` | "Nine of the thirteen are save-rate correlations." |
| `reports/final/partB/33-recommendations-for-our-positioning.md:12` | "Nine of the thirteen" |
| `docs/M2RADAR_ANALYSIS_METHOD.md:669, :814` | "nine save-rate" / "Nine of the 13" |
| `cards/C-2026-09-12-08.json` claim[1] (OBSERVED) | "13 clear our reliability bar, nine of them against save rate" |
| `reports/final/cardbook/08-C-2026-09-12-08.md:120` → **printed in the card book PDF** | same |

The card's claim also omits the one share-rate pair while listing the view_lift one.
The error is **not** in the spoken script — C-08's script says only "a hundred and fifteen
measurements across two hundred and sixty-eight videos", which reproduces exactly.

**Fix:** set `reliable_save_rate_pairs` to 11 in I-22 (json + DB), then replace "nine" with
"eleven (ten distinct features)" in the seven documents and in C-08 claim[1], adding the
share-rate pair to the card's enumeration; rebuild the card book.

### BL-4 · "`deepdives.suitable` is NULL for all 3 211 codes" is false, and contradicts card C-05 in the same deliverable

```sql
sqlite> SELECT COUNT(*) FROM deepdives;                          -- 282
sqlite> SELECT code,suitable,done_at FROM deepdives WHERE suitable IS NOT NULL;
DUduffIE5w5|0|2026-09-01
DUGghN2E82c|0|2026-09-01
DcWCLtCpaKu|0|2026-09-01
Dca2CyhJP1B|0|2026-09-01
```

The correct statement is **4 of 282 deep-dive rows carry the field, all four written
2026-09-01, all four rejections** — which is what `cards/C-2026-09-12-05.json` claim[1] says,
and what `reports/analysis/10-script-review-A.md:246` recorded as a correction. The
uncorrected version survives in three places, one of them a shipped final chapter:

- `reports/final/partB/27-reference-selection-logic.md:56` — "`deepdives.suitable` is NULL for
  all 3 211 codes" (**directly contradicts card C-05 in the same PDF set**)
- `reports/analysis/07-existing-cards-verdict.md:68` and `:125`
- `reports/analysis/08-hypotheses.md` H-13 evidence (same "3 211 records" framing)

**Fix:** replace all three with "filled on 4 of the 282 deep-dive rows (all 2026-09-01, all
rejections) and on none of the 23 cards' source reels", and rebuild the analytical report.

### BL-5 · `PRODUCTION.md` still carries the three figures this analysis disproves

`PRODUCTION.md` is the document the reels are actually shot from. Three separate final
chapters instruct that it be corrected; the file itself has not been touched since 8 September.

| `PRODUCTION.md` | recomputed by me from `video_features` + `reels`, 2026-09-12 |
|---|---|
| :21 "the winners' median is 55 seconds against 47 for the rest" | **46.8 s** (375 HIGH) vs **47.75 s** (2 836 rest) — one second, opposite direction |
| :22 "Under twenty seconds is 5% of winners and 13% of the rest" | **14.4 %** vs **12.4 %** — direction reversed |
| :22 "Longer than ninety is 15% against 8%" | **9.9 %** vs **8.5 %** — *not corrected anywhere; new finding* |
| :26 "A share separates a winner 3.6× more reliably…; a save, 2.8×" | **×2.615** and **×2.091** over the 2 899 reels clearing the 100-play guard |
| :3, :54 "our own set of 2 352 competitor reels" | corpus is **3 211** unique codes / 5 147 readings |
| :41 "Comment bait does not work. Present in 28% of top reels and 26% of the rest." | the gate is in **158 of 266 (59 %)** and multiplies save ×2.8, share ×1.8, comments ×23 (I-12). "Does not work" is only true of *reach*. |

The first four reproduce to the second decimal — see the evidence appendix. Nothing here is a
measurement dispute; the file is simply stale.

**Fix:** rewrite `PRODUCTION.md` lines 3, 21–22, 26, 41, 54 with the corrected figures and the
3 211 denominator, keeping the 50–70 s band (which the data does not contradict).

---

## SHOULD-FIX

### SF-1 · `hypotheses.card_id` is NULL for all 24 rows — the hypothesis→card link is never written

```sql
sqlite> SELECT hypothesis_id,status,COALESCE(card_id,'<NULL>') FROM hypotheses WHERE status='SELECTED';
H-01|SELECTED|<NULL>   H-04|SELECTED|<NULL>   H-05|SELECTED|<NULL>   H-09|SELECTED|<NULL>
H-11|SELECTED|<NULL>   H-12|SELECTED|<NULL>   H-13|SELECTED|<NULL>   H-18|SELECTED|<NULL>
H-19|SELECTED|<NULL>   H-20|SELECTED|<NULL>
```

Traceability still closes, because `cards_v2.hypothesis_id` is populated in both directions of
use — but any query starting from a hypothesis (`WHERE card_id='C-…'`) returns nothing, which
is what a reviewer will try first.
**Fix:** one `UPDATE hypotheses SET card_id=(SELECT card_id FROM cards_v2 c WHERE c.hypothesis_id=hypotheses.hypothesis_id)` at the end of `CARD_GENERATION`.

### SF-2 · `cards_v2.run_id` and `cards_v2.pdf_page` are NULL for all 10 cards

The `jobs` rows carry `run_id` (0 orphans), but the card rows themselves are not attached to
the run that produced them, and no page mapping to the card book exists even though the book
is built. **Fix:** write `run_id` at insert and back-fill `pdf_page` from the card-book build.

### SF-3 · `video_state.corpus_tier` and `video_state.analysis_ready` disagree on 5 codes, 2 of them genuinely mis-tiered

```sql
sqlite> SELECT corpus_tier, analysis_ready, COUNT(*) FROM video_state GROUP BY 1,2;
ANALYSIS_READY|0|5      ANALYSIS_READY|1|263     FRAMES_ONLY|0|29     INGESTED_NOT_ANALYZED|0|2914
```

Of the five, **DRXZJeHiAES** and **Db5sXEAP6C4** have `transcript_analysis_state='MISSING'` and
no `data/analysis/transcripts/<code>.json` file at all — they are tiered ANALYSIS_READY but
were never analysed. This is the mechanical origin of the 268 / 266 / 264 drift that runs
through every chapter: 268 tiered, 266 with a ta-v1 file, 264 with parsed beats.
`check.py` does not test tier-vs-flag agreement.
**Fix:** add a `check.py` assertion that `corpus_tier='ANALYSIS_READY'` implies
`analysis_ready=1`, and re-tier the two codes to `FRAMES_ONLY`.

### SF-4 · `reports/M2RADAR_INTEGRATION_EXECUTION_REPORT.md` does not exist

Every other spec-required file is present. Noted as possibly still being written.

### SF-5 · Insight I-12 is internally inconsistent, and I-08 / I-12 disagree on the same denominator

- I-12 `comparison` reads "cta_type = none (n=56, 29 creators)" but I-12 `groups.none` = 58,
  and `n` = 214 = 158+56. The database says 58. One of the two is wrong.
- I-12 `denominators.N_save_rate` = 245; I-08 `denominators.N_save_rate` = 243. Both are true
  of different sets (245 = save rate within the 268 analysis-ready; 243 = save rate within the
  266 also carrying a frame read) but they are printed as the same label.

**Fix:** set I-12's comparison to n=58 / 216, and label the two save-rate denominators
distinctly (`N_save_rate_ready` / `N_save_rate_frames`).

### SF-6 · Card C-02 cites a figure its own claim register declares unreproducible

`cards/C-2026-09-12-02.json` claim[2] (TO_MEASURE) states: *"The writer's figure of 118 could
not be reproduced under any counting rule tried"*. Claim[5] (OBSERVED) then states:
*"every one of the 118 flagged files names a proper noun…"*. Both are in the shipped card and
in card-book chapter 02.
**Fix:** rewrite claim[5] without the 118 — "every flagged file names a proper noun, a model
name or a figure, and none reports a mangled ordinary sentence."

### SF-7 · Card C-02 claim[4]: "Seven of the 273 transcript rows" — the table now holds 281

```sql
sqlite> SELECT COUNT(*) FROM transcripts;                                -- 281
sqlite> SELECT CASE WHEN words=0 THEN '0' ELSE '>0' END,COUNT(*) FROM transcripts GROUP BY 1;
0|7   >0|274
```

273 was the pre-August-import count and is still correct as a historical statement about the
faster-whisper run, but it reads as a present-tense claim about the database.
**Fix:** "Seven of the 273 rows produced by that run" (or restate as 7 of 281).

### SF-8 · Card C-05 claim[2]: "23 of 23 card source codes have a deepdives row"

```sql
sqlite> SELECT COUNT(DISTINCT c.code), COUNT(*), SUM(d.suitable IS NOT NULL)
        FROM cards c LEFT JOIN deepdives d ON d.code=c.code;
20|23|0
```

23 card *rows* map onto **20 distinct codes** (three reels were proposed twice). "23 of 23" is
true of rows and false of reels. The "0 with suitable set" half is exactly right.
**Fix:** "all 23 cards — 20 distinct source reels — have a deep-dive row and none of them
carries the field."

### SF-9 · `spec §54` and `spec §28` do not exist

`engine/prompts/script-reviewer.md:37` and `:45` require the writer to answer "spec §54's ten
questions". `SPEC.md` ends at §11 and `engine/SPEC.md` at §9; no "ten questions" list exists
anywhere in the repository. Reviewer A already recorded this
(`reports/analysis/10-script-review-A.md:11-17, :417`) and reconstructed the list from the
brief's own item 9. My answers below use that reconstruction.
**Fix:** either add the section to `engine/SPEC.md` or renumber the citation in the prompt.

### SF-10 · `reports/analysis/01-general-conclusions.md` §C prints 12 rows in a table its text calls 13

Already self-flagged at `10-script-review-B.md:381-384` and `:498-499`; still unfixed. The two
screen pairs at `01:134-137` are the missing rows, listed as prose after the table.
**Fix:** fold them into the table or say "twelve here, two more below".

### SF-11 · `reports/final/partA/10-corpus-coverage.md:33` uses 266/3,211 in a chapter whose own table (lines 12–31) uses 268

**Fix:** "268/3,211 ≈ 8.3 %" (the percentage is unchanged).

### SF-12 · Orphan EDL with no card and no validation

`cards/edl/C-2026-09-11-EX.json` (6 938 bytes, mtime 2026-09-12 11:04) has no
`cards/C-2026-09-11-EX.json` and no `.validation.json`. It is the only file in `cards/edl/`
that is not part of the 10+10 set.
**Fix:** delete it or move it under `tests/fixtures/`.

### SF-13 · Every evidence source cited by the deliverables is gitignored

`.gitignore:16` excludes `data/`. That covers `data/radar.db`, `data/analysis/insights.json`,
`data/analysis/hypotheses.json`, `data/analysis/hypothesis_refs.json` and all 266 transcript
analyses — i.e. every artefact the reports and cards cite as their source. Correct for the
raw frames and third-party captions; questionable for the analysis JSONs, which are our own
derived text and are what makes any of this checkable by someone who is not on this machine.
**Fix:** decide explicitly. If they stay out, say so in `START-HERE.md` and name where they
live; if they come in, add `!data/analysis/*.json` and `!data/analysis/transcripts/`.

---

## COSMETIC

- **CS-1** · C-02 claim[1]'s "140" gives **139** under the counting rule the claim itself
  states (quoted token followed by `=` / `is` / `for` / `means`). The rule is loose enough that
  a one-file difference is a tokenisation detail, not an error — but the claim presents it as
  mechanical. Either pin the exact regex in the source line or say "about 140".
- **CS-2** · `N_frames` is 297 in the denominator tables (296 `DONE_FIXED9` + 1 `PARTIAL`) and
  295 everywhere a frame statistic is computed (distinct codes in `frame_labels`). Both are
  right; the label is the same. Rename one.
- **CS-3** · `03-visual-patterns.md:25` says "266 also transcript"; the intersection of
  `frame_labels` and `beats` codes is **264**.
- **CS-4** · All ten cards land at 65.2–69.6 s, the top third of the 50–70 s band; C-03 and
  C-08 sit at 69.6 s, 0.4 s from the ceiling. Inside spec, but there is no headroom for a
  slower take on the day.
- **CS-5** · Cards 01, 03, 05, 07, 09 each carry **12** `jobs` rows — two complete
  CARD_GENERATION→VIDEO_GENERATION_READY sets from runs `2026-09-12_0844` and `_0853`.
  Cards 02, 04, 06, 08, 10 carry 6. Not wrong (two runs happened) but a naive "count the
  stages" query gives 90 rows for 10 cards.
- **CS-6** · Neither PDF has an embedded outline (`doc.get_toc()` returns 0 entries), only a
  textual TOC. Adding bookmarks would make a 132-page report navigable.
- **CS-7** · One of the 266 transcript analyses has zero words across its `beats`.

---

# Evidence appendix

## A. Method

All recomputation was done directly against `data/radar.db`, `reports/data/associations.json`,
`reports/data/spend.json` and the 266 files in `data/analysis/transcripts/`. No number was
accepted from a report. 57 numeric claims were checked; 51 reproduced exactly.

## B. The 57 claims

### B.1 Corpus counts and denominators — all reproduce

| claim | source | recomputed | ok |
|---|---|---|---|
| N_ingested 3 211 | partA/10:27 | `COUNT(DISTINCT code) FROM reels` = 3 211; `video_state` = 3 211 | ✓ |
| 5 147 reel readings | partA/01:12 | `COUNT(*) FROM reels` = 5 147 | ✓ |
| accounts 1 357; core/active 130; candidate 920; rejected 73; out 234 | partA/04:52-58 | exact | ✓ |
| tiers 268 / 29 / 2 914 | partA/10:18 | `corpus_tier` group-by: 268 / 29 / 2 914 | ✓ |
| 7 empty transcripts | partA/10:29 | `transcripts WHERE words=0` = 7 | ✓ |
| transcript rows 281 post-import | partA/05:27 | `COUNT(*) FROM transcripts` = 281 | ✓ |
| 266 ta-v1 analyses | partB/13:5 | `ls data/analysis/transcripts/*.json` = 266 | ✓ |
| 264 beat parses, 1 527 beats | partB/13:8 | 264 distinct codes, 1 527 rows | ✓ |
| all 1 527 beats carry scene ids | partB/25:15 | 1 527 non-empty `scene_ids_json` | ✓ |
| 2 645 labelled frames over 295 codes | partB/21:4 | 2 645 rows, 295 distinct codes | ✓ |
| 960 scenes over 282 codes | partB/24:4 | exact | ✓ |
| 282 deepdives | partA/09:10 | exact | ✓ |
| 38 of 282 report cuts=0 | partA/04:39 | exact | ✓ |
| saves NULL on 486 of 5 147 | partA/04:31 | exact | ✓ |
| save rate on 245 in the analysed tier | partB/16:6 | 245 | ✓ |
| share rate on 268 in the analysed tier | partB/11:75 | 268 | ✓ |
| 2 899 reels clear the 100-play guard | partB/26:6 | 2 899 with both rates | ✓ |
| flags 2 936 / 2 914 | partA/10:54 | `transcript_state='MISSING'` 2 936; `frames_state='MISSING'` 2 914 | ✓ |
| **266/3 211 = 8.3 %** at partA/10:33 | partA/10:33 | chapter's own table says 268 → SF-11 | ✗ |

### B.2 Creators — all reproduce

132 `creator_stats` rows at snapshot 3; **17 CONSISTENT / 115 HIGH_VARIANCE / 0 SMALL_SAMPLE**;
102 creators contribute to the analysis-ready set, median 2 reels each (p75 4, max 6);
`outlier_status` HIGH 375 / LOW 49 / NORMAL 2 787 (= 3 211).

### B.3 RELIABLE pairs — one mismatch (BL-3)

```
spearman pairs 460 = 115 features × 4 metrics    ✓
n_rows 268, n_creators 102, min_n 10             ✓
RELIABLE 13                                      ✓
  save_rate 11  share_rate 1  view_lift 1  robust_z 0
  → docs say save_rate 9                         ✗  BL-3
PROBABLE with p<0.05 = 72                        ✓  (01:139-143)
categorical contrasts 1 135, 1 000 replicates, seed 20260911   ✓
insights 30 rows, 12 RELIABLE / 16 PROBABLE / 2 INSUFFICIENT   ✓
hypotheses 24 (10 SELECTED / 14 REJECTED)        ✓
hypothesis_refs 41 rows over 27 distinct reels   ✓
```

### B.4 Category medians and hook length — all reproduce

```
hook_s      n=260   median 6.700    ✓  (every doc says 6.7 s)
total_s     n=264   median 53.55    ✓  (docs 53.6)
cta_type labelled 266; comment_keyword 158 = 59.4 %   ✓
beats: hook first in 259 of 264; cta-or-closing last in 215 of 264; median 6 beats   ✓
scenes: 663 hard_cut_or_more + 15 unknown among idx>0 (282 openers excluded) = 678 = 960−282   ✓
robust_z ties at the ±5 clip: 25 in the analysed set (83 corpus-wide)   ✓
top share/1k Dc_tsSeAjBy 61.3 · top save/1k DbO4zvJR1k8 87.4 · max play Dc9GZ0Gzf6o 6 043 051
  · max view_lift DYC-x8DogOI 399.39   ✓  (partB/29's corrections all hold)
```

### B.5 The `PRODUCTION.md` reproductions — all four reproduce, file is stale (BL-5)

```
median dur HIGH = 46.80 (n=375)   rest = 47.75 (n=2836)
under 20 s: HIGH 14.4 %   rest 12.4 %
over  90 s: HIGH  9.9 %   rest  8.5 %          <- PRODUCTION.md says 15 % vs 8 %
share median HIGH 0.01362 rest 0.00521  ratio 2.615
save  median HIGH 0.02557 rest 0.01223  ratio 2.091
(n with both rates = 2 899)
```

### B.6 Card claims

| card | claim | recomputed | ok |
|---|---|---|---|
| C-01 | 243 codes carry share rate + save rate + cta_type | 243 | ✓ |
| C-01 | 19 of the top 20 are `comment_keyword` | 19 (20th is `question_to_audience`) | ✓ |
| C-01 | 143 of 243 (59 %) carry the prompt | 143 = 58.85 % | ✓ |
| C-01 | within-cta re-rank puts 8 ungated in the top 20 | 8 (6 none, 1 link_in_bio, 1 follow) | ✓ |
| C-01 | DOMAtCmiSEn 67→8, DNA7-d3o5sQ 61→9 | exact | ✓ |
| C-01 | pool rule: 17 gated / 3 ungated → 15 / 5 | exact | ✓ |
| C-02 | 27 of 266 notes carry the mangled product name | 30 raw hits − the 3 named exclusions = 27 | ✓ |
| C-02 | 191 of 266 notes mention ASR | 191 | ✓ |
| C-02 | 140 name a specific wrong word | 139 under the stated rule → CS-1 | ~ |
| C-02 | named misreads Kenwa / a level lab / anything / Chachi BT | all four present in the three named files | ✓ |
| C-02 | 7 of the 273 transcript rows empty | 7 of **281** now → SF-7 | ~ |
| C-02 | "the 118 flagged files" | claim[2] says 118 is unreproducible → SF-6 | ✗ |
| C-03 | 264 codes, 1 527 boundaries, 55 aligned = 3.6 %, 215 with none | I-21 + 1 527/1 527 scene ids | ✓ |
| C-04 | 10 entries, 889 units, $17.78 | `SELECT COUNT(*),SUM(units),SUM(usd) FROM spend` → 10 / 889 / 17.78 | ✓ |
| C-04 | $2.60 on 130 accounts; $2.12 on 106 the week before | entries 10 and 8 | ✓ |
| C-04 | sixteen cents paid twice | entries 6 (52 u, $1.04) and 7 (8 u, $0.16), both 2026-09-03 | ✓ |
| C-05 | 4 rows of 282, all 2026-09-01, all rejections | exact (suitable=0 on all four) | ✓ |
| C-05 | "23 of 23 card source codes have a row" | 23 rows / **20 distinct codes** → SF-8 | ~ |
| C-06 | 23 plans, 9 struck out | `cards`: 9 вычеркнута, 5 Proposed, 9 draft | ✓ |
| C-07 | 283 515 / 19 624 = 14.45; / 151 569.5 = 1.87 | exact | ✓ |
| C-07 | 151 569.5 / 19 624 = 7.72 | 7.7237 | ✓ |
| C-07 | soojintech's twelve plays, 7 402 … 768 383 | all twelve match to the unit | ✓ |
| C-07 | baseline_n 11, creator_n 12, percentile 54.17, NORMAL | `scores` + `video_features` exact | ✓ |
| C-07 | 115 of 132 creators are HIGH_VARIANCE | 115 | ✓ |
| C-08 | 115 features over 268 analysis-ready videos | 115 / 268 | ✓ |
| C-08 | 460 pairs, 13 RELIABLE, none against robust_z | 460 / 13 / 0 | ✓ |
| C-08 | "nine of them against save rate" | **eleven** → BL-3 | ✗ |
| C-08 | I-08 screen_share → share rho +0.203, p=0.00085, cn +0.129 | exact in `associations.json` | ✓ |
| C-10 | 23 cards across three weeks: 5 / 9 / 9 | 2026-09-03 → 5, 09-07 → 9, 09-10 → 9 | ✓ |
| C-10 | our_posts and our_metrics both zero rows | 0 / 0 | ✓ |
| C-10 | three source reels proposed twice | Dco1mOJzZ4L, DcvBtiNtbYO, DcwCCgivcIQ | ✓ |

### B.7 Reference metrics vs `video_features` / `reels`

```
hypothesis_refs.performance_json: 242 numeric fields across all 41 rows
  checked against video_features (play, share_rate, save_rate, creator_median_play,
  view_lift, robust_z)                                            → 0 mismatches
card JSON references: 41 `play` values vs reels                    → 0 mismatches
card JSON references: play / share_rate / save_rate / creator_median_play / view_lift
  vs video_features across all 10 cards                            → 0 mismatches
```

---

## C. Traceability

### C.1 Three cards, chosen with `random.seed(20260912)`: C-01, C-04, C-07

The chain walked for each: `cards/<id>.json` → `cards_v2` → `hypothesis_id` →
`hypotheses` → `supporting_insights_json` → `insights` → `hypothesis_refs` →
`useful_beat_ids_json` / `useful_scene_ids_json` → `beats` / `scenes` →
`performance_json` vs `video_features` / `reels` → `jobs` → EDL + validation → frames on disk.

```sql
-- per card, run for each of the three
SELECT card_id,hypothesis_id,run_id,format,status,script_version,total_s,json_path,pdf_page
  FROM cards_v2 WHERE card_id=?;
SELECT hypothesis_id,title,status,card_id,supporting_insights_json FROM hypotheses
  WHERE hypothesis_id=?;
SELECT code,function,performance_json,useful_beat_ids_json,useful_scene_ids_json
  FROM hypothesis_refs WHERE hypothesis_id=?;
SELECT COUNT(*),MIN(start_s),MAX(end_s) FROM card_scenes WHERE card_id=?;
SELECT stage,state,agent,started_at FROM jobs WHERE entity_id=? ORDER BY started_at;
SELECT version,kind,created_at FROM script_versions WHERE card_id=?;
```

| | C-2026-09-12-01 | C-2026-09-12-04 | C-2026-09-12-07 |
|---|---|---|---|
| hypothesis | H-11 (SELECTED, 4.69) | H-01 (SELECTED, 4.59) | H-20 (SELECTED, 4.43) |
| `hypotheses.card_id` | **NULL** (SF-1) | **NULL** | **NULL** |
| insights cited / all exist in `insights` | 7 / 7 | 7 / 7 | 7 / 7 |
| refs in JSON vs `hypothesis_refs` | 5 / 5, identical codes | 4 / 4 | 4 / 4 |
| beat ids resolve in `beats` | all | all | all |
| scene ids resolve in `scenes` | all | all | all |
| ref metrics vs `video_features` | 0 mismatches | 0 | 0 |
| `card_scenes` | 8, 0.0 → 68.4 s contiguous | 7, 0.0 → 68.0 | 7, 0.0 → 69.2 |
| `jobs` stages | all 6, DONE, ×2 runs | all 6, DONE | all 6, DONE, ×2 runs |
| `script_versions` | v1 writer + v2 reviewer | v2 writer + v3 reviewer | v2 writer + v3 reviewer |
| EDL + validation | ok=true, 2 052 f @30 = 68.40 s | ok=true, 2 040 f = 68.00 s | ok=true, 2 076 f = 69.20 s |
| storyboard frames on disk | 8 / 8 | 7 / 7 | 7 / 7 |

Extended to all ten cards, the same script found: 0 missing insights, 0 ref mismatches, 0
dangling beat or scene ids, 0 metric mismatches, 10/10 EDLs with `result.ok=true`, and
**0 of 70 storyboard PNGs missing from disk**. All ten EDL durations equal `script.total_s`
exactly at 30 fps.

### C.2 The ten questions (reconstructed §54 list) answered for C-2026-09-12-07, from DB records only

Sources: `cards_v2`, `hypotheses` H-20, `hypothesis_refs`, `insights`, `beats`, `scenes`,
`video_features`, `scores`, `creator_stats`, `reels`, `card_scenes`, `jobs`,
`script_versions`. No report or card prose was used.

1. **Evidence.** `scores` for `DdCvFdHsnj1` gives `author_median_play` 19 624 at
   `baseline_n` 11; `video_features` gives `creator_median_play` 151 569.5 at `creator_n` 12,
   `percentile_in_creator` 54.17, `robust_z` 0.492, `outlier_status` NORMAL on 283 515 plays.
   `reels` holds exactly 12 distinct codes for `soojintech` in snapshot 3. Both yardsticks and
   both ratios (14.45×, 1.87×, and 7.72 between them) recompute from those rows alone.
2. **Hypothesis.** `hypotheses.hypothesis_id='H-20'`, title "The same number in two places",
   `status='SELECTED'`, `total_score` 4.43, `confidence` PROBABLE, `run_id`
   `2026-09-11_2345-04a541`. `cards_v2.hypothesis_id` on the card points at it; the reverse
   column is NULL (SF-1).
3. **References.** Four rows in `hypothesis_refs` for H-20 — `DUJYKENjZc5` (rhythm),
   `DVtgbY8Av6A` (cta), `DYC-x8DogOI` (screen_proof), `DaGTeJNN1GR` (b_roll) — and the same
   four in `hypotheses.candidate_refs_json`. The card JSON lists exactly these four.
4. **Reasons.** Every row's `reason` names its function and quotes a timed beat from the reel
   (e.g. `DUJYKENjZc5` "33 seconds, four named tools, one per step"). All four
   `performance_json` blocks match `video_features` field for field.
5. **Transcripts.** Nine beat ids are cited across the four refs — `DUJYKENjZc5-B0/B1`,
   `DVtgbY8Av6A-B0/B3`, `DYC-x8DogOI-B2`, `DaGTeJNN1GR-B1/B2` — and every one resolves to a
   row in `beats`. None of their text appears in the card's script (§D below).
6. **Stats signals.** I-23 (115 of 132 creators HIGH_VARIANCE, `creator_stats` confirms),
   plus the creator's own `reliability='HIGH_VARIANCE'` on `n_videos=12`. Seven insights are
   listed in `supporting_insights_json`; all seven exist in `insights`.
7. **Frame patterns.** Eight scene ids cited (`…-S00`, `-S01`, `-S02`, `-S03`, `-S06`), all
   resolving in `scenes`; the borrowed grammar recorded per row is SCR>A>SCR from
   `DYC-x8DogOI` and B_ROLL_PROCESS from `DaGTeJNN1GR`.
8. **Transformation.** Every `hypothesis_refs.transformation` field is populated and states
   borrowed-vs-changed explicitly, including the deliberate inversion of `DVtgbY8Av6A`
   ("Borrowed: nothing of the mechanism — it is the negative example").
9. **Original synthesis.** The two yardsticks, the 7.72 ratio and the bimodal play
   distribution are computed from `reels` + `scores` + `video_features` rows that belong to
   our own database; no reference reel supplies them.
10. **Why better than generic.** `card_scenes` carries seven contiguous scenes 0.0→69.2 s each
    with a distinct `script_role`, `overlay_text` and `source_inspiration_json`; the payoff
    scene names the definition-sheet mechanism rather than a general warning. `jobs` records
    CARD_GENERATION → SCRIPT_GENERATION → SCRIPT_REVIEW → FRAME_PLAN → FRAME_GENERATION →
    VIDEO_GENERATION_READY all DONE, and `script_versions` holds a reviewer row at v3.

---

## D. Originality

Method: tokenise to lowercase `[a-z0-9']+`; build the 5-gram set of the concatenated
`script.sections[].text` of each card; intersect with the 5-gram set of each referenced reel's
transcript (`data/analysis/transcripts/<code>.json`, all `beats[].text` concatenated) and with
the union over all 266 transcripts. Repeated against the full `transcripts.text` column in the
database as a control.

| card | script 5-grams | max overlap with any reference | overlap with **all 266** |
|---|---|---|---|
| C-2026-09-12-01 | 169 | 0 | **0** |
| C-2026-09-12-02 | 161 | 0 | **0** |
| C-2026-09-12-03 | 166 | 0 | **0** |
| C-2026-09-12-04 | 168 | 0 | **0** |
| C-2026-09-12-05 | 175 | 0 | **0** |
| C-2026-09-12-06 | 171 | 0 | **0** |
| C-2026-09-12-07 | 170 | 0 | **0** |
| C-2026-09-12-08 | 171 | 0 | **0** |
| C-2026-09-12-09 | 165 | 0 | **0** |
| C-2026-09-12-10 | 166 | 0 | **0** |

Corpus size for the comparison: 266 transcripts, 52 583 words, 50 568 distinct 5-grams (51 882
against the DB's full `transcripts.text`, which gives the same zeros). Sanity checks that the
tokeniser is doing real work: at n=4 the whole set produces two hits — `("so","none","of","the")`
in C-09 and `("it","at","all","and")` in C-10 — and at n=3, 4–12 per card, all of them ordinary
function-word runs. **Nothing to report at n≥5.**

---

## E. Positioning rules — no violations

Checked mechanically across all 10 cards, then read.

| rule | result |
|---|---|
| `strategy.filter.process` / `.friction` / `.ai_boundary` / `.next_action` non-empty | 40/40 fields present |
| `process` describes the viewer's process, not our pipeline | 10/10 — each names a business routine (a queue of enquiries, a call summary typed up weekly, a monthly renewal, a sign-off step, a recurring figure in a report, a Monday list). Not one describes the radar. |
| no `comment_keyword` CTA | 10/10. Every close is "Send this to whoever …". C-02 says it out loud: "The five fields are in the caption, not behind a comment." |
| no revenue / savings / client claims | Regex over all spoken text for `save you`, `saves you`, `revenue`, `clients`, `ROI`, `hours a week`, `10x your`, `profit`, `$Nk` and any `N %` → **0 hits in all 10**. C-04 quotes our own $0.02 unit cost and its claim register marks the savings framing MISSING. |
| no tool name in the first ~7 words of the hook | 0 hits against a 30-name tool regex |
| `total_s` within 50–70 | 65.2 / 66.4 / 68.0 ×2 / 68.4 / 68.5 / 69.2 ×2 / 69.6 ×2 — all inside, all in the top third (CS-4) |
| section seconds sum to `total_s` | exact on all 10 |
| storyboard contiguous | all 10 start at 0.0, no gaps or overlaps, last `end_s` equals `total_s` exactly |
| `overlay_text` ≤ 7 words | 0 violations across 70 storyboard scenes |
| `overlay_text` free of emoji | 0 emoji |

---

## F. Secrets — clean

Grepped the whole tree excluding `.git`, `node_modules`, `.venv`, `data/`, `cache*`,
`hiker-cache`, `__pycache__`, `.pytest_cache` for `ntn_`, `secret_`, `sk-`, `Bearer <token>`,
`key = <32+ hex>`, `HIKER_KEY=<value>`, `NOTION_TOKEN=<value>`, `ghp_`, `AKIA…`, `xox[baprs]-`.

Every hit is benign; no value is reproduced here:

| file:line | what it is |
|---|---|
| `tests/test_providers.py:41` | a dummy string written into a temp `.env` inside a test |
| `lib/hiker.py:59` | the `startswith("HIKER_KEY=")` parser, no value |
| `notion.py:13` | a docstring naming the variable |
| `reports/final/partA/07-data-acquisition.md:15`, `reports/audit/03-server-runtime-hiker.md:71` | prose describing where the key is read from |
| `reports/audit/05-notion-state.md:216, :219` | already `<redacted>` |
| `tests/test_engine_schema.py:540` | a test named `test_providers_never_store_secret_values` |

`.env.example` contains no line with a value after `=`.

```
$ git status --short --ignored | grep -i env
 M .env.example
!! .env
$ git ls-files --error-unmatch .env
error: pathspec '.env' did not match any file(s) known to git
$ git check-ignore -v .env
.gitignore:2:.env	.env
```

`.env` is ignored, untracked and unstaged. ✓

---

## G. Required files

| file | state |
|---|---|
| `docs/M2RADAR_CONTENT_ENGINE_ARCHITECTURE.md` | present, 46 975 B |
| `docs/M2RADAR_DATABASE_RECONCILIATION.md` | present, 37 346 B |
| `docs/M2RADAR_ANALYSIS_METHOD.md` | present, 47 175 B |
| `reports/M2RADAR_INTEGRATION_EXECUTION_REPORT.md` | **absent** (SF-4) |
| `reports/final/M2RADAR_ANALYTICAL_REPORT.pdf` | present, 132 pp, 4.5 MB |
| `reports/final/M2RADAR_CARD_BOOK.pdf` | present, 105 pp, 6.8 MB |
| `cards/C-2026-09-12-*.json` | 10 / 10 |
| `cards/edl/*.json` | 10 + 1 orphan (SF-12) |
| `cards/edl/*.validation.json` | 10 / 10, every one `result.ok=true`, `render_mode` PREVIS |
| `schemas/` | 4 files (corpus field dictionary, render-record, supplied-take, scene-segmentation) |
| `tests/` | 13 test modules |

### PDF inspection (PyMuPDF 1.28.0 / MuPDF 1.29.0)

- **"MISSING IMAGE": 0 occurrences in either PDF.** Also zero for `TODO`, `TKTK`,
  `Lorem ipsum`, `{{`, `N/A image`. The word *placeholder* appears only as legitimate prose
  (analytical pp. 65, 124–127; card book pp. 5, 6, 44) describing the `asset_status:
  'template'` convention.
- **Analytical report**: 132 pages, 20 image placements over 18 unique xrefs, on pp. 10, 32,
  36, 37, 41, 42, 43, 45, 48, 52, 59, 61, 63, 67, 75, 76, 79, 82, 86, 95. Textual TOC pp. 2–6
  listing 36 chapters. No embedded outline (CS-6).
- **Card book**: 105 pages, 70 image placements, 70 unique xrefs, textual TOC pp. 2–4.

| card | pages | storyboard images | ≥6 |
|---|---|---|---|
| C-…-01 | 7–16 | 8 (S00–S07) | yes |
| C-…-02 | 17–26 | 6 (S00–S05) | yes |
| C-…-03 | 27–35 | 7 | yes |
| C-…-04 | 36–45 | 7 | yes |
| C-…-05 | 46–55 | 8 | yes |
| C-…-06 | 56–65 | 7 | yes |
| C-…-07 | 66–75 | 7 | yes |
| C-…-08 | 76–85 | 7 | yes |
| C-…-09 | 86–95 | 7 | yes |
| C-…-10 | 96–105 | 6 | yes |

70 images in total, matching the printed `_SNN.png` caption labels one to one and matching the
70 rows of `card_scenes` — no frame is captioned but missing. The contact sheet is the
eleventh image on each chapter and is the one that fails (BL-2).

Footer-overlap measurement (the numbers behind BL-1):

```python
import fitz
doc = fitz.open(path)
for i, p in enumerate(doc):
    lines = [(l["bbox"], "".join(s["text"] for s in l["spans"]).strip())
             for b in p.get_text("dict")["blocks"] if b["type"] == 0 for l in b["lines"]]
    lines = [x for x in lines if x[1]]
    foot  = [ln for ln in lines if sig in ln[1]]      # footer signature
    if not foot: continue
    fy0   = min(f[0][1] for f in foot)                # 761.3 on every page
    body  = [ln for ln in lines if ln[0][1] < fy0 - 1]
    if body and max(ln[0][3] for ln in body) > fy0:
        print(i + 1, round(max(ln[0][3] for ln in body) - fy0, 2))
```

Ten pages were then rendered at 60 dpi and looked at directly; six of the ten show the footer
running through the middle of a line of body text.

---

## H. Tests

```
$ python3 -m pytest -q
........................................................................ [ 28%]
................................................................s....... [ 56%]
........................................................................ [ 85%]
.....................................                                    [100%]
252 passed, 1 skipped, 16 warnings in 26.21s          (exit 0)
```

The 16 warnings are all one `PendingDeprecationWarning` from `engine/charts.py:224`
(`ax.boxplot(vert=False)` → `orientation=`). Harmless today, will break on a future matplotlib.

```
$ python3 check.py
СВЯЗНОСТЬ        6/6 ✓      ПРАВИЛА НАБОРА  4/4 ✓
ДАННЫЕ           6/6 ✓      ДВИЖОК          7/7 ✓
  расход сходится с ценой единицы   17.78   ожидалось 17.78    889 единиц
  video_state = число уникальных роликов    3211   ожидалось 3211
ВСЁ СОШЛОСЬ  (23 проверок)   21.2 МБ
```

Both green. Note that `check.py`'s 23 checks do **not** cover the tier-vs-flag disagreement in
SF-3, nor `hypotheses.card_id` in SF-1 — both would be one-line additions.

---

## I. What I could not check

- The 2026-09-10 07:00 run log quoted throughout card C-09 lives on the server at
  `/opt/radar/data/runs/2026-09-10_0700.log` and is not in this repository. C-09's claims are
  sourced to `reports/audit/03-server-runtime-hiker.md`, which quotes it line by line; I
  verified the citation chain but not the log itself.
- `engine/SPEC.md` §3's "twenty-five named stages" (C-06 claim[0]) — I confirmed the section
  exists and that the file's headings run §0–§9, but did not count the stage list against the
  card's claim; `10-script-review-B.md:261` reports 25 and that the plan is the sixteenth.
- Nothing has been published (`our_posts` = 0 rows), so no TO_MEASURE claim on any card can be
  settled either way. Every card marks these correctly.
