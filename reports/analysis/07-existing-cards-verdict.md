# 07 — Existing cards: verdict

Confirms or adjusts the classification in `reports/audit/04-existing-cards-review.md` using the new
`video_features` evidence (accumulated creator medians, `robust_z`, ta-v1 semantics, fa-v1 frames) that
did not exist when that audit was written. Scope: main's **23** legacy cards and Max's **10**.
Nothing here has been shot or published — `our_posts` is still empty.

## 1. The one thing the new data changes: the multipliers move

The audit quoted multipliers from `scores.author_median_play`, which `score.py` computes **within an age
band** from whatever baseline existed at that snapshot (often 5–11 videos). `video_features.view_lift`
divides by the creator's **accumulated** median over their whole known history. The two disagree, and in
two cases the disagreement changes the verdict.

| card | audit multiplier | score.py author median (snap 3) | accumulated creator median | new lift | new robust_z | percentile in creator | verdict change |
|---|---|---:|---:|---:|---:|---:|---|
| #20 `DdCvFdHsnj1` | 14.4× | 19 624 (n=11) | **151 570** (n=12) | **1.87×** | 0.49 | 54 | **Unsupported → also statistically unjustified** |
| #15 `Dc_tsSeAjBy` | 9.1× | 257 026 (n=5) | **35 051** (n=32) | **67.0×** | 3.15 | 95 | Strong → **Strong, and far stronger than recorded** |
| #17 `DcmK70aO5VP` | 1.9× | 11 366 (n=6) | 13 987 (n=28) | 1.55× | 0.76 | 77 | Strong → **Usable with revision** (no outlier status) |
| #1 `DbO4zvJR1k8` | 15.2× | 13 729 (n=9) | 14 448 (n=27) | 14.5× | 3.01 | 83 | unchanged |
| #2 `DbVKVz0y8xo` | 8.0× | 8 813 (n=15) | 9 734 (n=25) | 7.2× | 3.79 | 90 | unchanged |
| #9/#21 `Dco1mOJzZ4L` | 3.6× | 8 116 (n=11) | 10 120 (n=27) | 2.9× | 0.76 | 72 | unchanged in kind; **NORMAL, not an outlier** |
| #12/#22 `DcwCCgivcIQ` | 4.1× | 159 665 (n=14) | 171 330 (n=29) | 3.2× | 2.07 | 88 | unchanged |
| #6/#16 `DcvBtiNtbYO` | 3.5× | 21 401 (n=13) | 22 121 (n=26) | 3.6× | 2.25 | 79 | unchanged |

**Rule this implies.** A card's headline multiplier must be recomputed against the accumulated creator
median before the card is written, and the baseline `n` must travel with it. A 14.4× that rests on an
11-video age-banded baseline is not the same object as a 14.5× that rests on 27 videos.

## 2. Main's 23 cards — confirmed and adjusted

All 23 source reels now have an fa-v1 frame read; 22 of 23 have a ta-v1 semantic parse (the exception is
`DceZCRZIatT`, which has no transcript at all and was correctly abandoned).

**Classification stands for 20 of 23.** Three changes:

1. **#20 `DdCvFdHsnj1` (Builds, draft) — downgrade from "Unsupported" to "do not produce."** The audit
   already noted it fails the Builds pass criterion (the card's own angle says "we have not built this
   yet"). The new numbers remove its statistical justification too: 1.87× against its author's accumulated
   median, `robust_z` 0.49, 54th percentile, `outlier_status = NORMAL`. It is an ordinary reel for its
   author, and the card has no build behind it.
2. **#17 `DcmK70aO5VP` (Radar, draft) — from "Strong" to "Usable with revision."** 1.55× and
   `robust_z` 0.76, `NORMAL`. Its share and save rates are genuinely high (40.3 and 62.1 per 1 000, which
   the audit quoted correctly), so it is a "резонировало у своих" reference in RULES.md §6 terms, not a
   reach signal. The angle — dropping the comment-bait and the "$8,000/month" promise, swapping the source's
   law/recruitment/insurance verticals for a cheap-to-fail one — remains exactly right, and it is now
   independently supported: income framing runs at median view_lift 1.19 against 2.12 for the rest
   (insight I-25).
3. **#15 `Dc_tsSeAjBy` (Radar, draft) — confirmed Strong, and upgraded in evidence.** 67× against the
   accumulated median, `robust_z` 3.15, 95th percentile, and the **highest share rate in the whole
   analysis-ready corpus at 61.3 per 1 000**. Its ta-v1 read explains the mechanism: the threat escalates
   from a chore to three named hired roles to the author's own test, so each beat brings it closer to the
   viewer. This is now the single best-evidenced reference main ever selected.

**The nine cards cut before writing remain correctly cut**, and two of them are now positively
vindicated: `DcxV37-CJOC` has a five-word transcript (ta-v1 confidence `INSUFFICIENT`) and `DceZCRZIatT`
has none — neither could have grounded an angle. `Dc_iv4YKCAh` (#23, cut) is in fact one of the strongest
reels in the corpus (56× lift, `robust_z` 5.0, 52.9 saves per 1 000) and was cut on content grounds, which
is the filter working as designed.

**One new defect the frame data exposes.** 9 of the 23 source reels open on `SPLIT_SCREEN` — the niche's
most-used and least-rewarded opening (insight I-10: any split state, median `robust_z` 1.03 vs 1.43,
p=0.044). Main's selection was blind to visual structure because `cards.py` ranks on metrics only. The
three shot-plan columns it writes automatically (`shot_banner`, `shot_frame`, `shot_screen`) therefore had
nothing to inherit from the reference.

**The four process defects in the audit all still stand**, and one is now quantifiable:
`deepdives.suitable` is NULL for all 23 cards and for 278 of the 282 deep-dive rows (the four exceptions are rejections dated 2026-09-01; no reel was ever marked suitable), so the
RULES.md §2а compliance record does not exist anywhere. Row 30 of the reference pool in
`06-creators-and-references.md` is a live example of a reel that should fail that check.

## 3. Max's 10 cards — classification confirmed unchanged

Nothing in the new data rehabilitates any of the ten. The audit's findings hold: `synthesis: true` on 7 of
10, `fixture.state = DESIGNED_NOT_MODEL_EXECUTED` on all 10, `AWAITING_OWNER_ASSET` on all 80 assets,
`provider_execution: false`, zero real transcripts quoted, zero real frames, zero tools named, zero
measured numbers, and 12 of the 16 source reels at or below their own author's median.

Three new measurements sharpen the verdict:

- **Every card's hook runs 4–7 s against the 0–3 s house rule** the audit flagged as a timing violation.
  The new data says the house rule was wrong, not the cards: the niche's median hook is **6.7 s** and hook
  length correlates with nothing (p≥0.23 on all four metrics, insight I-03). This is the one criticism in
  the 8 Sep audit that should be withdrawn — and the fix is to change the rule, not the scripts.
- **The fixed 60 s / 7-scene template** is not wrong about duration (duration predicts nothing, I-02) but
  is wrong to be fixed at all: scene count in this niche ranges from 1 to 8 coarse visual states with no
  performance difference (median `robust_z` 1.25 at one state, 1.63 at four).
- **All 16 source reels sit in the agent/automation-builder niche**, which POSITIONING.md §4 excludes. The
  new topic data confirms why that is tempting: agent building is the highest-lift topic in the corpus
  (n=27, median view_lift 6.63) and `AI в конкретном бизнес-процессе` the weakest (n=8, 0.65×). The pull is
  real and must be resisted deliberately.

## 4. Templates to reuse

| source | reuse as | why |
|---|---|---|
| **#6 `DcvBtiNtbYO`** (main) | the angle-writing example shown first in `prompts/angles.md` | Still the best single card: it admits M2's own governance rule went unenforced for two days. That is the "we tried / it broke" standard POSITIONING.md §6 requires, and nothing in the corpus of 266 analysed competitor reels does it — `before_after` is the second-rarest proof type (n=5) and no reel anywhere shows a failure. |
| **#15 `Dc_tsSeAjBy`** (main) | the evidence-handling example | Declines to borrow the source's "4× faster" claim and says so. Now also the best-evidenced reference in the set (67×, 61.3 shares/1k). |
| **#17 `DcmK70aO5VP`** (main) | the reframing example | Drops comment-bait and income framing and swaps high-risk verticals for a cheap-to-fail one. Independently supported by I-12 (the gate moves no reach) and I-25 (income framing costs reach). |
| **#12 `DcwCCgivcIQ`** and **#9 `Dco1mOJzZ4L`-as-Builds** (main) | secondary angle examples | Real reference, real multiplier, real transcript quote, one repeated process each. |
| **Max's `ScriptCard` JSON schema** (not its content) | the card-v2 field list | Timed shots with `on_screen_text` and an `information_job`, three candidate hooks, explicit claim states. Already adopted into `engine/SPEC.md` §8. |
| **Max's `claim_state` vocabulary** (`OBSERVED` / `PLANNED` / `TO_MEASURE` / `MISSING`) | per-statement claim tagging | The one genuinely useful idea in his 11 Sep report. |

## 5. Templates not to reuse

| source | why not |
|---|---|
| **All 10 of Max's cards as content templates** | No tool, no number, no owner footage, invented fixtures, 7 of 10 are composite scenarios citing no reel. 0 of 10 passed the brand-book checklist in the 8 Sep audit and nothing in the new data changes that. |
| **#20 `DdCvFdHsnj1` as a Builds template** | Fails the Builds pass criterion by its own admission and is now also statistically unjustified (1.87×, `NORMAL`, 54th percentile). |
| **Any card that repeats the "654-view reel ranked above a 25 000-view one" or "a free source closed mid-run" anecdote** | Five of the fourteen developed cards lean on these two internal proof points. At five publications a week the audience would see the same proof five times. |
| **The fixed 60 s / 7-scene shot template** | Scene count shows no relation to performance (1 to 8 coarse states, `robust_z` 1.25–1.63, p≥0.11), so fixing it discards the one thing that should vary with the topic. |
| **Split-screen openings inherited from the reference** | 9 of main's 23 source reels open on split screen, the corpus's weakest opening (I-10). A card must not inherit a reference's layout without checking it. |
| **The 0–3 second hook rule** | Not supported: median hook is 6.7 s, only 6 % of reels close inside 3 s, and hook length predicts nothing. Replace with "one complete promise in 5–10 s and 20–30 words". |

## 6. Three changes to make before the next card run

1. **Recompute every multiplier against the accumulated creator median** and carry the baseline `n`,
   `robust_z`, `percentile_in_creator`, `outlier_status` and the creator's `reliability` label onto the
   card. Two of 23 cards had materially wrong headline numbers without it.
2. **Record `cta_type` on every reference and compare share/save rates only within the same `cta_type`.**
   59 % of the analysed corpus runs a comment-keyword gate, which moves save rate ×2.8 and share rate ×1.8
   while moving reach not at all. `cards.py` ranks on `resh_1k`/`save_1k`, so it is currently part-ranking
   DM funnels (insight I-12).
3. **Populate `deepdives.suitable` before an angle is written**, as RULES.md §2а has required on paper
   since 1 September. It is NULL on 278 of 282 deep-dive rows (four rejections dated 2026-09-01), and on every card source. The reference pool in
   `06-creators-and-references.md` contains one reel that should fail it.
