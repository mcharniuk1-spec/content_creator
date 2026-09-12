# 26. Performance Analysis

**Denominators.** Four metrics: `view_lift` (plays ÷ the creator's accumulated median − 1), `robust_z` (a
MAD-based z on `ln(1+plays)` against the creator's own distribution, clipped to ±5), `share_rate` and
`save_rate`. **Every rate is NULL below 100 plays** (`stats.MIN_PLAY_FOR_RATE`). **HikerAPI drops the save
field on ~9–10 % of rows (486 of 5 147) and 226 codes have never had a save value**, so `save_rate` always
runs on a smaller n — 245 inside the analysed tier, 2 899 across the corpus where both rates clear the
guard. The association run covers **460 Spearman pairs (115 features × 4 metrics)** over n=268 rows and
102 creators, plus **1 135 categorical contrasts** with bootstrap CIs (1 000 replicates, seed 20260911,
**resampling creators, not videos**). `robust_z_floored` is set on **0** rows, so no magnitude here is an
upper bound for that reason.

## The headline: 13 of 460 pairs are RELIABLE, and none of them is against reach

| feature | metric | n | creators | rho | p | creator-normalised |
|---|---|---:|---:|---:|---:|---:|
| `lex_platforms_n` | save_rate | 245 | 95 | **+0.331** | 1.1e-07 | +0.173 |
| `lex_cta_verb_n` | save_rate | 245 | 95 | +0.241 | 1.4e-04 | +0.155 |
| `lex_questions_per_10s` | save_rate | 245 | 95 | **−0.235** | 2.0e-04 | −0.186 |
| `questions_n` | save_rate | 245 | 95 | −0.229 | 3.1e-04 | −0.162 |
| `lex_second_person_n` | save_rate | 245 | 95 | +0.206 | 1.2e-03 | +0.177 |
| `blk_hook_wps` | save_rate | 240 | 94 | +0.205 | 1.4e-03 | +0.156 |
| **`screen_share`** | **share_rate** | 266 | 102 | **+0.203** | 8.5e-04 | +0.129 |
| `blk_hook_segments` | save_rate | 245 | 95 | +0.198 | 1.9e-03 | +0.197 |
| `lex_rhetorical_questions_n` | save_rate | 245 | 95 | −0.186 | 3.5e-03 | −0.151 |
| `lex_first_person_n` | save_rate | 245 | 95 | −0.180 | 4.8e-03 | −0.124 |
| `lex_direct_address_per_100w` | save_rate | 245 | 95 | +0.174 | 6.3e-03 | +0.127 |
| **`lex_entities_distinct`** | **view_lift** | 268 | 102 | **+0.161** | 8.3e-03 | **+0.198** |
| first visual state is a screen | share_rate | 161 | — | +0.208 | 6.3e-04 | **+0.285** |
| any screen state present | save_rate | 245 | — | +0.210 | 9.8e-04 | +0.213 |

**Nine of the thirteen are save-rate correlations. One is share rate. One is view lift. None is
`robust_z`.** Read with the strong-versus-weak result — of 115 features, none separates the top from the
bottom `robust_z` quartile at p<0.01 — the conclusion is unavoidable: **what the video controls is the
save and the share, not the view** [I-22]. Reach is driven by things this dataset does not contain.

## Phrase and word analysis: the save is bought with second person and named destinations

The save-rate block above is not eleven findings; it is one behaviour measured eleven ways. A save is a
viewer filing away something they intend to *do*. The language that produces it is **concrete, addressed
and destination-bearing**: platform names (+0.331), CTA verbs (+0.241), second person (+0.206), direct
address per 100 words (+0.174). The language that suppresses it is **interrogative and self-referential**:
questions per 10 s (−0.235), question count (−0.229), rhetorical questions (−0.186), first person
(−0.180). All eight survive creator normalisation [I-15, I-07].

The reach side is thinner. `lex_entities_distinct` → `view_lift` is the **only reach correlation in 460
pairs that is RELIABLE**, and it is *stronger* inside creators (+0.198) than pooled (+0.161). Two PROBABLE
pairs behave the same: `lex_tools_n` → view_lift +0.157 (cn **+0.223**) and `specificity` → view_lift
+0.132 (cn **+0.205**), → robust_z +0.121 (cn +0.197). The quartile test agrees — 2 distinct entities
against 1 (p=0.011), specificity 4.26 against 3.45 (p=0.080) [I-13].

Two counter-directions. **Pressure language runs negative on everything measured**: urgency → view_lift
−0.164 (p=0.0072) and → share_rate −0.150 (cn **−0.180**), fear → share_rate −0.157 (cn −0.086), weak
quartile 2 urgency words against 1 (p=0.056) [I-14]. And **lexical diversity runs backwards**: `lex_ttr`
0.605 against 0.628 (p=0.039), `lex_mattr50` 0.795 against 0.811 (p=0.044), both lower in the strong
quartile (chapter 20).

**What vanished under creator normalisation** must travel with the table above, because until it is tested
it looks like the same kind of number.

| pair | pooled rho | creator-normalised |
|---|---:|---:|
| `info_density` → save_rate | +0.303 | +0.132 |
| `lex_technical_n` → save_rate | +0.268 | −0.060 |
| `lex_entities_distinct` → save_rate | +0.256 | +0.030 |
| `specificity` → save_rate | +0.237 | +0.047 |
| `wps` → save_rate | +0.213 | +0.071 |
| `split_share` → save_rate | +0.193 | +0.036 |
| `text_overlay_density` → save_rate | +0.180 | +0.080 |
| `solution_s` → save_rate | +0.343 | **−0.217** (sign flip) |
| `setup_s` → view_lift (n=34) | +0.395 | **−0.318** (sign flip) |

These are statements about **which creators post what**, not about videos, and quoting any of them as a
production instruction would be an error.

**Transcript reading.** [DVtgbY8Av6A](https://www.instagram.com/reel/DVtgbY8Av6A/) is these findings in
84 words: fifteen named objects in thirteen seconds ("My cost reducer skill. My internet skill. My
scalability skill…", 2.3–15.3 s), zero questions, an imperative close, **57.3 saves per 1 000**. Its
opposite is [DcvBtiNtbYO](https://www.instagram.com/reel/DcvBtiNtbYO/), a sung reel with an identity-call
hook, no destination and no ask, carrying the corpus's second-highest **share** rate (59.2 per 1 000) and
a save rate of **7.3**. The two metrics are not the same instruction.

## Proof analysis

| proof_type | n | creators | median view_lift | median save/1k | confidence |
|---|---:|---:|---:|---:|---|
| screen_demo | 84 | 50 | 2.64 | 27.6 | SUFFICIENT_SAMPLE |
| **none** | **68** | 46 | **2.09** | 29.4 | SUFFICIENT_SAMPLE |
| numbers | 36 | 28 | 1.81 | 33.5 | SUFFICIENT_SAMPLE |
| personal_story | 28 | 20 | 1.82 | 29.9 | PROBABLE |
| authority_claim | 25 | 20 | 1.25 | 14.8 | PROBABLE |
| third_party_data | 16 | 12 | 1.72 | 24.9 | PROBABLE |
| before_after | **5** | 5 | 0.78 | 21.2 | PROBABLE |
| client_story | 4 | 3 | 3.82 | 15.1 | INSUFFICIENT |

**Proof is optional in this niche and the corpus does not punish its absence.** Sixty-eight of 266 reels
carry no proof beat and perform indistinguishably from the 84 with a screen demonstration (2.09× against
2.64×; both SUFFICIENT_SAMPLE at 46 and 50 creators). Proof *length* does not separate the quartiles
either (19.25 s against 23.9 s, p=0.551). Where proof exists it is **visual rather than spoken**: 41 % of
2 645 labelled frames are flagged `is_proof_visual` against 50 % of reels carrying a proof *beat*, and the
median time to the first proof beat is **22.0 s** (p25 11.1, p75 32.0) [I-18].

Two absences are the finding. `before_after` is the **second-rarest** proof type (n=5) and below the
corpus median on lift; and **nothing in the 266 analysed reels shows a failure.** For M2 that is an
opportunity, not a cost: POSITIONING.md §6 already requires evidence M2 owns, and a reel showing its own
run *including the part that did not work* does something no measured competitor does — delivered as
screen footage at 20–25 seconds, where this audience expects evidence to arrive.

## Temporal and momentum analysis

| | value |
|---|---|
| median `log_play_slope_last10` | **−0.052** (mean −0.138, p10 −0.589, p90 +0.155) |
| creators with a full 10-post window | 131 |
| of those, trending **up** | **34 (26 %)** |
| median `delta_play_pct` against the previous post | **−5.2 %** |
| median `ratio_to_rolling_median` | **0.885** |
| posts above 5× their creator's rolling median | 269 of 3 078 (**8.7 %**), 101 creators |
| posts above 10× | 150 (**4.7 %**) |

| direction | top 12 by `log_play_slope_last10` |
|---|---|
| rising | swapsays_wtf +0.373 · manthanjethwani +0.337 · gannon.meyer +0.198 · harshsharma_ai +0.197 · soojintech +0.174 · valeridoesai +0.167 · protips.ai +0.163 · gennaroautomates +0.162 · rence_ur_hands +0.159 · wokecoder +0.145 · kayvon.ai +0.144 · chase.h.ai +0.140 |
| falling | kraya.ai −0.706 · jackroberts___ −0.428 · cashflow.automations −0.413 · andreapalacio −0.403 · kallaway −0.401 · michaelpkocher −0.349 · lukebuildsai −0.311 · petergriffin.ai −0.310 · publisity.ai −0.303 · davi.d_roberts −0.282 · sanji.chien −0.275 · techflowanjani −0.264 |

Three quarters of tracked creators are losing reach over their last ten posts; the typical post lands at
0.885 of its author's rolling median; 8.7 % of posts carry the reach and 87 % of creators cannot repeat
them [I-24]. Only `harshsharma_ai` is both rising and CONSISTENT. Four limits bind: the slope is a
**trend line over post index, not a derivative**, and one hit bends it; there are only **three snapshots**
(2026-09-01, -07, -10); the `followers` table is empty, so creator growth is unanswerable; and
`engine/stats.py` does **not** control for age, so `view_lift` for very recent reels is biased downwards.
Emerging *formats* cannot be separated from emerging *topics* here. What the data does support is the
measured justification for RULES.md's 14-day freshness threshold: **a competitor's recent reach is not a
stable benchmark.**

## Cross-metric relationships

![Share rate vs save rate, 2 899 reels clearing the 100-play guard](reports/charts/share_vs_save_rate.png)

| | value |
|---|---|
| Spearman(share_rate, save_rate) | **+0.781** (n=2 899) |
| reels whose save rate exceeds their share rate | **86 %** |
| medians across the corpus | save **0.0131** vs share **0.0056** (p95 0.0458 vs 0.0281) |
| medians inside the analysed tier | save 0.0278 (n=245) vs share 0.0152 (n=268) |
| HIGH outliers (n=375) vs the rest | share rate **×2.62**, save rate **×2.09** |
| Spearman with `robust_z` | share **+0.326**, save **+0.277** |

**Share and save are not independent selection axes.** At rho +0.781 they move together, so ranking on one
and then the other adds far less information than it appears to, and `cards.py`'s split (Radar on
`resh_1k`, Builds and Teardown on `save_1k`) is closer to one ranking than to two. Share remains the
marginally better discriminator (×2.62 against ×2.09; rho +0.326 against +0.277), which keeps "why would
anyone forward this?" as the right first production question — but **the published magnitudes are wrong**:
RULES.md §7's 3.6× and 2.8× become **2.62× and 2.09×** on the 2 899 reels clearing the guard, the original
having come from a 100-reel top slice of an earlier 2 352-reel export [I-28].

One relationship dominates and is invisible on this chart: **the comment gate** (chapter 18) multiplies
save rate ×2.8 and share rate ×1.8 while leaving `view_lift` and `robust_z` untouched (p=0.58 and 0.63).
Any comparison of hi-intent rates that does not hold `cta_type` constant is partly measuring funnels.

## Strategic implication

Judge M2's own reels on **shares and saves per 1 000, never on views**, and never promise that a script
change will move reach. Write in the second person, name three distinct destinations rather than one three
times, delete questions from the script (the corpus median `questions_n` is 0), and drop the urgency
register after the hook. Deliver proof visually at ~22 seconds and make it M2's own run including its
failure — the one evidence move nobody in this corpus makes. Re-derive the reference pool weekly. And
correct RULES.md §7 to 2.62× and 2.09× before anyone quotes it again.

**Confidence: RELIABLE** for the 13-pair table (every row meets n ≥ 30, ≥ 8 creators, p<0.01 and a
surviving creator-normalised check), for the cross-metric relationships (n=2 899) and for the temporal
aggregates as a description of three snapshots. **PROBABLE** for the specificity and tool-name reach
findings (p<0.05, survive normalisation, fail the p<0.01 bar) and for the proof table (three
SUFFICIENT_SAMPLE cells, but categorical medians admit no normalisation check and 59 % of the corpus is
gated). **INSUFFICIENT** for `before_after` (n=5) and `client_story` (n=4). Everything above is
associational; method §8 forbids reading any of it as a cause.
