# 01 — General conclusions

Written 2026-09-12 by the synthesis role (H) over `reports/data/*`, `reports/stats/stats-2026-09-12.json`,
`data/analysis/transcripts/*.json` (266 files) and `data/analysis/frames/*.json` (295 files).
Roles A–G below were run in order and their outputs are kept as separate sections so that any line in
`data/analysis/insights.json` can be traced back to the pass that produced it.

**Denominators used throughout.** `N_ingested = 3 211` (metric-only statements), `N_ready = 268`
(script + visual statements), `N_transcript_usable = 268`, `N_frames = 297`, `N_beats_codes = 264`
(codes with a ta-v1 semantic parse), `N_frames_analysed = 295` (codes with an fa-v1 read, of which 266
also have a transcript analysis). `engine.corpus.tiers()` and `video_state.corpus_tier` disagree by
design on the frames-only boundary; every number below names which one it came from.

**The caveat that governs everything.** `deep.py` only processed reels that `score.py` had already
ranked near the top of their creator's output. The median `robust_z` inside the analysis-ready tier is
**+1.26** against **0.00** across all 3 211 ingested reels. Every contrast in this document therefore
compares strong reels with other strong reels. Where a contrast is absent, that is not evidence the
feature is irrelevant in the niche at large; where a contrast is present, it is probably understated.

---

## A — Transcript structural analyst

**Coverage.** 1 527 beats across 264 codes, median 6 beats per reel (min 0, max 12). Beat roles fold
into the eight script parts of the method doc §5; `objection`, `rehook` and `other` stay outside the
eight and are reported separately.

**The parts that exist.** Of 264 parsed reels: hook 260 (98 %), CTA or closing 216 (82 %), explanation /
mechanism / context 208 (79 %), payoff or transformation 150 (57 %), proof or example 133 (50 %),
solution 70 (27 %), problem / pain / tension 64 (24 %), setup or audience 34 (13 %), objection 19 (7 %),
re-hook 15 (6 %).

**Typical lengths** (median seconds / median share of spoken time / median words, on the codes where the
part exists):

| part | n | median s | median share | median words |
|---|---:|---:|---:|---:|
| hook | 260 | 6.7 | 13.2 % | 21.5 |
| setup | 34 | 7.8 | 14.0 % | 29 |
| problem | 64 | 8.95 | 16.4 % | 32 |
| explanation | 208 | 18.6 | 38.3 % | 64 |
| solution | 70 | 10.4 | 20.1 % | 36 |
| proof | 133 | 17.0 | 30.5 % | 57 |
| payoff | 150 | 8.2 | 17.0 % | 26.5 |
| cta | 216 | 4.95 | 9.7 % | 21 |

Total spoken length: median 53.6 s, 182 words, 3.52 words per second. Video duration: median 54.2 s in
the analysed set, 47.6 s across all 3 211 ingested reels.

**Orderings.** 146 distinct bucketed orderings across 264 reels. The hook is the first beat in 259 of
264; a CTA or closing beat is the last in 215. The modal shape is `HOOK > EXPLAIN > PAYOFF > CTA`
(27 reels), then `HOOK > EXPLAIN > CTA` (13), `HOOK > EXPLAIN > PROOF > CTA` (10) and
`HOOK > PROOF > CTA` (8). No ordering covers more than 10 % of the corpus.

**Hook length.** Median 6.7 s (p25 4.6, p75 9.6), mean 7.5 s. Only 6 % close inside 3 seconds, 31 %
inside 5, and 19 % run past 10. Hook length correlates with nothing (robust_z rho +0.063, p=0.31;
view_lift rho +0.075, p=0.23). The hook is a semantic unit, not a stopwatch window.

**Where the problem lands.** In the 64 reels that state one, the problem beat starts at a median 21 % of
spoken length (p25 0.15, p75 0.39); 56 % of them are inside the first quarter. Median time to the first
proof beat is 22.0 s (p25 11.1, p75 32.0); median time to a solution beat is 19.7 s (p25 7.7, p75 29.0).

**Where the CTA lands.** Median start at 90 % of spoken length (p25 0.84, p75 0.94). 202 of 216 sit in
the final quarter; three reels place it before halfway. There is no positional experiment left to run.

---

## B — Marketing and persuasion analyst

**Pain.** 13 canonical pains are used, none reaching the RELIABLE threshold. Largest cells:
`cost_money` (n=48, 33 creators, median view_lift 1.96), `dont_know_where_to_start` (34/30, 1.34),
`keeping_up_with_ai` (29/24, 1.73), `missing_skills` (25/20, 1.34), `quality_trust` (25/20, 1.63).
Highest-lift small cells: `manual_repetition` (15/13, 6.94), `scaling_without_hiring` (8/8, 4.83),
`time_waste` (20/17, 3.54). Lowest: `chaos_no_process` (17/14, 0.87) and `slow_response_to_leads`
(5/3, 0.47) — the two pains closest to M2's own territory.

**Desire.** Classified from the ta-v1 `desire` and `thesis` fields: a ready-made artefact (n=27, save
rate 0.0346 vs 0.0270, p=0.052), time saving (n=33, save 0.0330 vs 0.0275, p=0.025), money saving
(n=84, save 0.0306 vs 0.0250, p=0.007), control or self-hosting (n=42), status edge (n=19), certainty
(n=19, save 0.0140 vs 0.0282, p=0.017 — negative). What is wanted is a thing to keep, not a conclusion
to agree with.

**Promise.** `resource_handoff` has the highest save rate of any solution type (0.0429, n=38),
`framework_mental_model` the lowest of the large cells (0.0135, n=25). `agent_build` has the highest
lift (6.33, n=23) and `prompt_technique` the lowest (0.71, n=10).

**Persuasion mechanisms** observed repeatedly in the beat texts: deliberate incompleteness (the artefact
is named but withheld), objection pre-emption placed exactly where the viewer would reject the idea,
price contrast ("used to cost $10,000"), borrowed authority (a named repo's star count, a named
company), teach-then-automate (give the whole recipe, then offer the one-line version), and the
share-with-a-peer close ("show this to anyone who says…").

**CTA.** 158 of 266 reels (59 %) run a comment-keyword gate; 58 have no CTA at all; 17 ask for a follow,
12 for a link in bio, 11 pose a question to the audience. The gate raises comment_rate 23-fold, save
rate 2.8-fold and share rate 1.8-fold — and moves reach not at all (view_lift p=0.58, robust_z p=0.63).

**Positioning types.** `educator` 138, `news` 38, `builder` 38, `seller` 31, `entertainer` 21. Builder
outperforms educator on lift (3.42 vs 1.73). Funnel role: awareness 125, conversion 83, trust 58;
trust reels are the weakest on every metric (view_lift 1.06, robust_z 0.82).

**Language.** Urgency and fear track negatively (urgency vs view_lift rho -0.164, p=0.007; fear vs
share_rate -0.157). Second person, CTA verbs and named platforms track positively with saves and all
survive creator normalisation. Questions track negatively with saves (-0.229, RELIABLE).

---

## C — Performance analyst

Source: `reports/data/associations.json` — 460 Spearman pairs (115 numeric features × 4 metrics),
1 135 categorical contrasts with bootstrap CIs over 1 000 creator-resampled replicates (seed 20260911),
and a strong-vs-weak quartile test on all 115 features.

**RELIABLE (n≥30, creators≥8, p<0.01, creator-normalised rho keeps sign and half the magnitude) — 13 of
460 pairs.** Eleven of them are save-rate correlations (two of those, `questions_n` and
`lex_questions_n`, are the same count computed twice, so ten distinct save-rate features), one
share-rate, one view_lift, none robust_z.

| feature | metric | n | creators | rho | p | creator-normalised rho |
|---|---|---:|---:|---:|---:|---:|
| lex_platforms_n | save_rate | 245 | 95 | +0.331 | 1.1e-07 | +0.173 |
| lex_cta_verb_n | save_rate | 245 | 95 | +0.241 | 0.00014 | +0.155 |
| lex_questions_per_10s | save_rate | 245 | 95 | −0.235 | 0.0002 | −0.186 |
| questions_n | save_rate | 245 | 95 | −0.229 | 0.00031 | −0.162 |
| lex_questions_n (duplicate of questions_n) | save_rate | 245 | 95 | −0.229 | 0.00031 | −0.162 |
| lex_second_person_n | save_rate | 245 | 95 | +0.206 | 0.0012 | +0.177 |
| blk_hook_wps | save_rate | 240 | 94 | +0.205 | 0.0014 | +0.156 |
| **screen_share** | **share_rate** | **266** | **102** | **+0.203** | **0.00085** | **+0.129** |
| blk_hook_segments | save_rate | 245 | 95 | +0.198 | 0.0019 | +0.197 |
| lex_rhetorical_questions_n | save_rate | 245 | 95 | −0.186 | 0.0035 | −0.151 |
| lex_first_person_n | save_rate | 245 | 95 | −0.180 | 0.0048 | −0.124 |
| lex_direct_address_per_100w | save_rate | 245 | 95 | +0.174 | 0.0063 | +0.127 |
| **lex_entities_distinct** | **view_lift** | **268** | **102** | **+0.161** | **0.0083** | **+0.198** |

Two additional pairs computed in this pass clear the same bar and are reported as RELIABLE in the
insights file: **first visual state is a screen → share_rate** (pooled +0.208, p=0.00063;
creator-normalised +0.285, p=0.00025, n=161) and **any screen state present → save_rate** (pooled
+0.210, p=0.00098; creator-normalised +0.213, p=0.0093).

**PROBABLE (p<0.05, does not clear one of the RELIABLE conditions) — 72 pairs.** The ones worth acting
on: `lex_tools_n` → view_lift (+0.157, cn +0.223, survives), `specificity` → view_lift (+0.132, cn
+0.205, survives), `lex_urgency_n` → view_lift (−0.164, cn −0.028, does not survive), `split_share` →
save_rate (+0.193, cn +0.036, does not survive), `a_roll_share` → share_rate (−0.156, cn −0.094,
survives), `solution_s` → view_lift (+0.343 on n=70, cn +0.085, does not survive).

**INSUFFICIENT / no signal.** Duration (all four metrics, |rho| ≤ 0.09), hook_s, hook_words, total_s,
total_words, wps against reach, cuts, cuts_per_min, scenes_n, avg_scene_s, a_roll_share and
b_roll_share against robust_z, text_overlay_density, and every part-length except `solution_s`.
`visual_to_script_sync` was never tested because the field holds free prose, not a category.

**Strong vs weak.** Top vs bottom `robust_z` quartile inside the analysis-ready corpus (n=67 each, 41
and 43 creators, q1 +0.596, q3 +2.855). Of 115 features, **none reaches p<0.01** and only seven reach
p<0.05. See `04-strong-vs-weak.md`.

---

## D — Hook specialist

**Verbal openings.** First-word frequencies across 264 hook beats: "I" 22, "this" 18, "if" 16, "you" 15,
"so" 11, "the" 10, "here's" 8. First-bigrams: "you can" 10, "if you" 9, "I just" 9, "this is" 7.
First-trigrams: "you can now" 7, "if you want" 4, "I just built" 3, "most people think" 2, "nobody is
talking" 2.

**Question hooks are rare and costly.** 24 of 264 opening beats (9 %) contain a question mark. Their
median view_lift is higher (3.00 vs 1.91) but their save rate is less than half (0.0130 vs 0.0284), and
the script-level question count is one of the strongest RELIABLE negatives in the whole run.

**Hook type against performance** (analysis-ready, n=266):

| hook_type | n | creators | median view_lift | median robust_z | share | save |
|---|---:|---:|---:|---:|---:|---:|
| demo_first | 18 | 14 | 9.55 | 2.52 | 0.0172 | 0.0212 |
| result_first | 24 | 18 | 4.20 | 1.74 | 0.0201 | 0.0331 |
| list_promise | 21 | 18 | 2.72 | 1.52 | 0.0174 | 0.0463 |
| question | 10 | 10 | 2.37 | 1.36 | 0.0054 | 0.0198 |
| curiosity_gap | 22 | 19 | 2.16 | 1.26 | 0.0155 | 0.0301 |
| warning_fear | 13 | 12 | 2.16 | 1.30 | 0.0104 | 0.0255 |
| bold_claim | 67 | 43 | 1.88 | 1.09 | 0.0169 | 0.0306 |
| contrarian | 23 | 19 | 1.71 | 2.04 | 0.0076 | 0.0139 |
| story_open | 13 | 11 | 1.43 | 0.89 | 0.0005 | 0.0017 |
| number_stat | 20 | 15 | 1.04 | 1.30 | 0.0160 | 0.0339 |
| problem_call_out | 17 | 15 | 0.49 | 0.67 | 0.0099 | 0.0220 |
| identity_call | 9 | 8 | 0.41 | 0.37 | 0.0144 | 0.0184 |

Grouped: **show-first** (demo_first + result_first, n=42, 29 creators) median robust_z 2.17 / view_lift
5.81 against 1.21 / 1.80 for everything else (p=0.021 and 0.008); **setup-first** (identity_call +
story_open + problem_call_out, n=39, 31 creators) 0.67 / 0.80 against 1.36 / 2.25 (p=0.002 both).
`bold_claim` — the most common hook in the niche — sits exactly at the corpus median.

**Visual hooks.** First-frame type across 266: SPLIT_SCREEN 73, A_ROLL_MEDIUM 57, A_ROLL_CLOSE_UP 45,
B_ROLL_CONTEXT 18, SCREEN_RECORDING 16, OVERLAY 14, A_ROLL_WIDE 13, A_ROLL_TALKING_HEAD 9, UI_DEMO 8,
B_ROLL_PROCESS 8, SCREENSHOT 7, MOTION_GRAPHIC 7, HOOK_VISUAL 6, DATA_VISUAL 5, MEME 4, TEXT_ONLY 4,
TRANSITION 1. Grouped into coarse first states: screen 35 (median view_lift 5.25, robust_z 2.13),
text/graphic 31 (2.12 / 1.43), A-roll 114 (1.99 / 1.15), B-roll 23 (1.60 / 1.25), split 63 (1.34 / 1.05).
The `is_visual_hook` flag on frame 0 is set on all 295 codes and is therefore a labelling artefact,
not a signal.

**Verbal × visual combinations with n≥5:** result_first on A_ROLL_MEDIUM (n=8, 6 creators, robust_z
2.98, view_lift 8.07) is the strongest; contrarian on A_ROLL_CLOSE_UP (6/5, 1.86/4.98) and
curiosity_gap on A_ROLL_CLOSE_UP (5/5, 1.76/13.42) follow. bold_claim on SPLIT_SCREEN is the single
most common combination (n=22, 17 creators) and one of the weakest (robust_z 0.84, view_lift 1.21).

---

## E — Narrative analyst

**Archetypes** (n=266): demo_walkthrough 62 (42 creators, view_lift 3.70, robust_z 1.71), tutorial_steps
45 (32, 1.88, 1.10), listicle 43 (32, 1.91, 1.23), problem_solution 34 (23, 1.01, 1.16),
announcement_news 30 (21, 1.29, 0.96), story_arc 17 (13, 3.47, 1.34), myth_bust 13 (9, 1.71, 1.93),
rant_opinion 9, contrast_before_after 5. Demo walkthrough is both the largest and the highest-lift
archetype with a SUFFICIENT sample.

**Pacing.** 3.52 words per second, median, with an interquartile range of 3.07–3.83 and no relation to
reach (robust_z rho +0.044, p=0.48; strong quartile 3.53 vs weak 3.45, p=0.44). The corpus's extremes
both work: 14 spoken words in 27 seconds (DZgBxjnBzMe, view_lift 207×) and 340 words in 100 seconds
(DLzPQzGNEmY, 72×).

**Open loops.** 240 of 266 reels carry at least one; the median is exactly one (198 reels), 36 carry
two, 26 carry none. Pattern interrupts: 140 reels have none, 110 have one. Explicit re-hook beats appear
in 15 of 264 reels (6 %). The niche's retention device is a single unresolved promise held from the hook
to the payoff, not repeated re-hooking.

**Payoff placement.** Payoff beats exist in 150 reels at a median 8.2 s and 17 % of spoken time, and
they sit immediately before the CTA in the modal ordering. The strong quartile gives the payoff 10.3 s
against 7.95 s in the weak quartile (p=0.12) and the solution 12.25 s against 8.4 s (p=0.0065) — the
only script part whose strong-weak difference clears p<0.01.

**Longer reels survive on loop discipline.** The corpus's 178-second outlier (Db3SERzzOqG) opens four
loops in its hook and closes them in the exact order they were opened; the 100-second DLzPQzGNEmY runs a
five-rung ladder with a status payoff. Long reels that lose are the ones that flatten: DaDn5L-xKWi's
five identically shaped ten-second tricks, DcbnTAtxb8C's three departments described with identical
grammar.

---

## F — Audience and positioning analyst

**Who the corpus serves.** Classifying the ta-v1 `audience` free text: 54 of 266 reels (20 %) name a
developer, coder or engineer audience; 103 (39 %) name a business owner, operator or founder; 40 (15 %)
name an agency owner or someone trying to earn from AI; 106 (40 %) match none of these. Performance is
flat across the split — developer-not-business 1.87 median view_lift against business-not-developer 1.89.
**M2's audience narrowing costs nothing measurable.**

**But the "business" audience in this corpus is not M2's audience.** Reading the free text, it is
overwhelmingly *agency operators and solo builders who want to sell AI services*, not a non-technical
operations lead trying to fix one repeated process. The `AI в конкретном бизнес-процессе` topic is the
smallest cell in the corpus that is not suppressed: n=8, 8 creators, median view_lift 0.65, robust_z
0.85, share rate 0.0040 — a quarter of the corpus median. `chaos_no_process` (n=17) and
`slow_response_to_leads` (n=5) are the two weakest pains.

**What the corpus does that M2 must not do.**

1. **Comment-keyword gates** — 59 % of the analysed corpus. Banned by RULES.md §1.2 already. The data
   adds that the gate costs nothing in reach and buys nothing in reach, so refusing it forfeits no
   distribution; what it forfeits is the inflated share and save rate (see the selection warning below).
2. **Tool lists with no process** — `resource_handoff` is 38 reels with the corpus's highest save rate.
   It is exactly what POSITIONING.md §8 lists under "do not publish".
3. **Developer tutorials** — 54 reels aimed at people who already build. DVZGBgTk6zz's hook ("nobody
   wants to touch terminal") is the closest the whole corpus comes to a non-technical framing, and it is
   still addressed to people building agents.
4. **Income framing** — 71 reels (27 %) frame the outcome as money and run at median view_lift 1.19
   against 2.12. RULES.md §1.2 already refuses it; the data says nothing is lost.
5. **Agent demos with no process owner** — the highest-lift topic in the corpus (n=27, view_lift 6.63)
   and the clearest RULES.md disqualifier. DbYh2P-MQnj maps 137 agents across seven departments and
   never names a person responsible for anything.

**What M2 should take.** The builder register (positioning_type `builder`, n=38, view_lift 3.42 vs
educator's 1.73), the demo-first opening, the screen as evidence, and the B_ROLL_PROCESS visual language
that the agent-building topic invented — attached to one named repeated process with a named owner and
an explicit AI boundary, which nobody in the corpus does.

**A selection warning for the radar itself.** Because the comment gate raises save rate 2.8× and share
rate 1.8× while leaving reach untouched, ranking candidate references by share/save per 1 000 —
which `cards.py` does — systematically promotes gated reels. Reference selection must hold `cta_type`
constant or record it on the card.

---

## G — Script reviewer: 16 testable writing rules

Each rule carries the evidence line behind it. Rules are written so that a finished script can be
checked against them without opening the data.

| # | Rule | Evidence |
|---|---|---|
| 1 | Open on the artefact doing the work, not on a face and not on a claim. | Show-first hooks (n=42, 29 creators) run at median robust_z 2.17 / view_lift 5.81 vs 1.21 / 1.80; screen-first frames (n=35) carry share rate 0.0213 vs 0.0140, creator-normalised rho +0.285, p=0.00025. |
| 2 | Never open on the series, the audience or yourself. | identity_call + story_open + problem_call_out (n=39, 31 creators) median robust_z 0.67 vs 1.36, p=0.002. Same creator, edhillai: demo-first DNA7-d3o5sQ robust_z +4.69, "Day one of two AI tips…" DXb8P08Dati −1.04. |
| 3 | Give the hook 5–10 seconds and 20–30 words. Do not truncate it to hit a 3-second rule. | Median hook 6.7 s / 21.5 words / 13.2 % of speech (n=260); only 6 % close inside 3 s; hook length correlates with nothing (p≥0.23 on all four metrics). |
| 4 | Write the hook as a statement. A question is allowed only if the same sentence answers it. | 9 % of hooks contain a question mark; questions_n vs save_rate rho −0.229, p=0.0003, creator-normalised −0.162, survives. |
| 5 | Name the exact tool, the exact number and the exact step every time. | lex_entities_distinct vs view_lift +0.161 pooled, +0.198 creator-normalised — the only reach correlation that survives normalisation. Strong quartile median 2 distinct entities vs weak 1 (p=0.011). |
| 6 | Put a real screen on camera and let it carry the instruction. | screen_share vs share_rate +0.203, p=0.00085, survives normalisation (RELIABLE). Any-screen reels: share 0.0168 vs 0.0118 (p=0.00013), save 0.0308 vs 0.0220 (p=0.001). |
| 7 | Come back to the face for the payoff and the closing line. | A>SCREEN>A reels (n=39, 32 creators) share rate 0.0213 vs 0.0140, p=0.00076; the exact three-step sequence (n=11, 11 creators) median robust_z 3.01. |
| 8 | Do not use split screen. | Any split state (n=99) median robust_z 1.03 vs 1.43, p=0.044; pure split sequence (n=27, 18 creators) median view_lift 0.94 against a corpus median of 2.03. |
| 9 | Write in the second person; use "I" only to say we tested it. | second_person_n vs save_rate +0.206 (cn +0.177), first_person_n −0.180 (cn −0.124), both RELIABLE. |
| 10 | Cap the mechanism block at about a third of the script. | Explanation median 38 % of speech; strong quartile 34.1 % / 17.3 s vs weak 41.9 % / 19.5 s. Solution is the only part where strong beats weak at p<0.01 (12.25 s vs 8.4 s). |
| 11 | State the friction in the first quarter, in 8–10 seconds, as a named process. | Only 24 % of the corpus states a problem at all; where it exists it starts at a median 21 % of spoken length and 56 % of cases are inside the first quarter. This is M2's mandated addition, not the niche's habit. |
| 12 | Show the proof visually at 20–25 seconds, and show the failure. | Median time to first proof 22.0 s; screen_demo is the largest proof type (n=84) and "none" the second (n=68); 41 % of labelled frames are proof visuals. Nothing in the corpus shows a failure. |
| 13 | Open exactly one loop. Add one re-hook only if the reel runs past 45 seconds. | Median open_loops = 1 (198 of 266 reels); only 15 of 264 carry an explicit re-hook; DNA7-d3o5sQ's two-second "But how about the results?" precedes 36.5 saves per 1k. |
| 14 | Close in the last 10 % of the script, in about 5 seconds and 20 words, with one ask. | CTA starts at a median 90 % of spoken length; 94 % sit in the final quarter; median 4.95 s / 21 words. Da3uSkrNjli stacks four asks and lands at view_lift −0.05. |
| 15 | Never gate the artefact behind a comment. Publish it. | The gate moves comment_rate ×23, save ×2.8, share ×1.8 and reach not at all (p=0.58). Banned by RULES.md; the data says the ban is free. |
| 16 | Drop the pressure register and the income framing after the hook. | Urgency vs view_lift −0.164 (p=0.007); weak quartile uses more urgency words than the strong one (2 vs 1); money-framed reels view_lift 1.19 vs 2.12. |

Two rules that people expect and the data does **not** support: aim for a specific duration (no signal
across 3 211 reels, HIGH outliers 46.8 s vs 47.8 s for the rest) and cut faster (no signal, and the cut
metric is not a cut count).

---

## H — Synthesis

**1. The format question is answered, and the answer is "format is not the lever."** Of 115 numeric
features, none separates the top from the bottom `robust_z` quartile at p<0.01. Of 460 correlation
pairs, 13 are RELIABLE and none of them is against `robust_z`. Duration, pacing, script length, cut
rate, A-roll share, caption density and hook length are all flat. Once a reel is competently made,
what remains is subject, specificity and evidence.

**2. What the video actually controls is the save and the share, not the view.** Eleven of the 13
RELIABLE correlations (ten distinct features) are save-rate correlations. They describe one behaviour — a viewer filing away
something they intend to do — and they are driven by second person, named destinations, concrete verbs
and the absence of questions. Reach is driven by things this dataset does not contain.

**3. The single most reliable production instruction is: put a screen on camera.** It is the only
visual feature that survives creator normalisation on two independent metrics, and opening on it is
worth roughly half again the forwarding rate.

**4. The comment gate contaminates our own selection.** 59 % of the analysed corpus runs one. It moves
reach not at all and moves exactly the two rates the radar ranks by. Until `cta_type` is held constant
in selection, the radar is partly ranking DM funnels.

**5. M2's territory is empty and weak, and both facts are real.** The business-process topic is n=8 at
0.65× lift. The agent-building topic is n=27 at 6.63×. The gap PRODUCTION.md described is confirmed;
the high-ceiling counter-example it hoped for is not in this corpus, because nobody is producing it.

**6. Two published numbers need correcting.** PRODUCTION.md's "winners' median 55 s vs 47 s" and
"under twenty seconds is 5 % of winners against 13 % of the rest" do not reproduce on 3 211 reels: 46.8 s
vs 47.8 s and 14 % vs 12 %. RULES.md §7's "a share separates a winner 3.6× more reliably, a save 2.8×"
becomes 2.62× and 2.09× on the full corpus with the denominator guard applied.

**7. The corpus cannot answer most category questions.** Every one of 20 subtopic cells is
INSUFFICIENT; 9 of 27 topics are; only one hook type reaches the size threshold. The next processing
wave needs breadth, not more features per reel.

**8. Nothing here licenses a causal claim.** Everything above is associational, computed inside a
pre-selected top-of-ranking sample of 8.3 % of the database.
