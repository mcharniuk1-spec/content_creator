# 04 — Strong vs weak

Spec §73. Top versus bottom quartile of `robust_z` **inside the analysis-ready corpus**, every measured
numeric feature, with medians, n on each side and a two-sided Mann-Whitney U test. Source:
`reports/data/associations.json` (`engine.stats.associations`, copied verbatim, not recomputed) plus
`reports/data/script_parts.json` and `reports/data/visual_patterns.json` for the part-level and roll-level
splits, which use slightly different denominators and are reported separately below.

## The split

| | value |
|---|---|
| corpus | `ANALYSIS_READY` (n=268; 266 with a semantic parse) |
| strong | n=**67**, 41 creators, `robust_z` ≥ **+2.855** (q3) |
| weak | n=**67**, 43 creators, `robust_z` ≤ **+0.596** (q1) |
| test | Mann-Whitney U, two-sided (none of these distributions is normal and several are counts with a floor at zero) |
| features tested | **115** |

**Read this before the tables.** Per method §1.4 the "weak" quartile is **not weak content**. Its median
`robust_z` is about **+0.6**, i.e. these reels still beat their own authors' medians — they are the least
strong of a pre-selected strong set. The whole comparison is strong-vs-strong, and the true gaps in the
niche are almost certainly larger than anything below.

## The headline: almost nothing separates them

**Of 115 features, none reaches p<0.01. Seven reach p<0.05**, and two of those run in the counter-intuitive
direction (lexical diversity is *lower* in the strong quartile).

| feature | strong | weak | diff | p | direction |
|---|---:|---:|---:|---:|---|
| `solution_s` | 12.25 s | 8.4 s | +3.85 | **0.0065** | strong spends longer stating the solution |
| `lex_entities_distinct` | 2.0 | 1.0 | +1.0 | **0.0107** | strong names twice as many distinct things |
| `lex_entities_n` | 2.0 | 1.0 | +1.0 | **0.0207** | same, total mentions |
| `lex_tools_n` | 0.0 | 0.0 | 0.0 | **0.0254** | distribution shifted, medians identical |
| `hook_words` | 26.5 | 22.0 | +4.5 | **0.0282** | strong hooks are longer in words, not seconds |
| `lex_ttr` | 0.605 | 0.628 | −0.023 | **0.0387** | strong repeats itself more |
| `lex_mattr50` | 0.795 | 0.811 | −0.016 | **0.0443** | same, length-robust measure |

Just outside: `lex_urgency_per_100w` 0.683 vs 0.901 (p=0.053), `lex_urgency_n` 1 vs 2 (p=0.056),
`lex_platforms_n` (p=0.057), `setup_s` 11.0 vs 4.7 (p=0.057), `cta_s` 5.7 vs 4.4 (p=0.075),
`specificity` 4.255 vs 3.448 (p=0.080), `lex_money_mentions_n` (p=0.088).

**The structural contrast, stated plainly.** Strong and weak reels in this corpus are the same length
(56.9 s vs 58.0 s, p=0.98), carry the same number of words (198 vs 179, p=0.33), are spoken at the same
rate (3.53 vs 3.45 wps, p=0.44), have the same hook duration (7.6 s vs 7.0 s, p=0.16), the same A-roll
share (0.222 both, p=0.57), the same split share (0.0 both, p=0.63), the same caption density (1.0 both,
p=0.42) and the same cut rate (7.06 vs 6.75 per minute, p=0.42). The differences are **what is named and
how long the solution statement is** — nothing about the build of the video.

The two lexical-diversity reversals are worth reading rather than dismissing: a lower type-token ratio in
the strong quartile means the winners **say the same words again** — the tool name, the step number, the
promise — instead of reaching for variety. That is consistent with the entity findings and with the
repeated-phrase patterns in `05-script-parts.md`.

## Every measured feature


### Length and pacing

| feature | n strong | n weak | median strong | median weak | diff | Mann-Whitney p |
|---|---:|---:|---:|---:|---:|---:|
| `lex_sentences` | 67 | 67 | 15.0 | 12.0 | 3.0 | 0.225 |
| `lex_words` | 67 | 67 | 198.0 | 180.0 | 18.0 | 0.328 |
| `total_words` | 67 | 67 | 198.0 | 179.0 | 19.0 | 0.333 |
| `lex_wps` | 67 | 67 | 3.5214 | 3.4062 | 0.1152 | 0.362 |
| `lex_content_words` | 67 | 67 | 98.0 | 88.0 | 10.0 | 0.4 |
| `lex_chars` | 67 | 67 | 1073.0 | 1040.0 | 33.0 | 0.407 |
| `info_density` | 67 | 67 | 1.6247 | 1.565 | 0.0597 | 0.426 |
| `lex_info_density` | 67 | 67 | 1.6247 | 1.565 | 0.0597 | 0.426 |
| `wps` | 67 | 67 | 3.5276 | 3.4512 | 0.0764 | 0.444 |
| `total_s` | 66 | 66 | 56.9 | 56.8 | 0.1 | 0.582 |
| `avg_sentence_len` | 67 | 67 | 13.615 | 14.5 | -0.885 | 0.612 |
| `lex_avg_sentence_len` | 67 | 67 | 13.615 | 14.5 | -0.885 | 0.612 |
| `lex_median_sentence_len` | 67 | 67 | 13.0 | 12.5 | 0.5 | 0.632 |
| `lex_types` | 67 | 67 | 118.0 | 117.0 | 1.0 | 0.677 |
| `lex_content_word_share` | 67 | 67 | 0.4734 | 0.4653 | 0.0081 | 0.679 |
| `dur` | 67 | 67 | 56.9 | 58.0 | -1.1 | 0.981 |
| `lex_dur_s` | 67 | 67 | 56.9 | 58.0 | -1.1 | 0.981 |

### Script parts (seconds)

| feature | n strong | n weak | median strong | median weak | diff | Mann-Whitney p |
|---|---:|---:|---:|---:|---:|---:|
| `solution_s` | 18 | 19 | 12.25 | 8.4 | 3.85 | 0.00652 |
| `hook_words` | 66 | 64 | 26.5 | 22.0 | 4.5 | 0.0282 |
| `setup_s` | 7 | 11 | 11.0 | 4.7 | 6.3 | 0.0568 |
| `cta_s` | 56 | 51 | 5.7 | 4.4 | 1.3 | 0.0749 |
| `payoff_s` | 37 | 38 | 10.3 | 7.95 | 2.35 | 0.123 |
| `hook_s` | 66 | 64 | 7.6 | 7.0 | 0.6 | 0.162 |
| `explanation_s` | 54 | 53 | 17.3 | 19.5 | -2.2 | 0.236 |
| `proof_s` | 32 | 34 | 19.25 | 23.9 | -4.65 | 0.551 |
| `problem_s` | 18 | 16 | 8.6 | 9.15 | -0.55 | 0.809 |

### Timing blocks (clock-based fallback)

| feature | n strong | n weak | median strong | median weak | diff | Mann-Whitney p |
|---|---:|---:|---:|---:|---:|---:|
| `blk_tail_segments` | 67 | 67 | 3.0 | 2.0 | 1.0 | 0.148 |
| `blk_body_segments` | 67 | 67 | 15.0 | 12.0 | 3.0 | 0.172 |
| `blk_body_words` | 67 | 67 | 150.0 | 135.0 | 15.0 | 0.33 |
| `blk_hook_segments` | 67 | 67 | 2.0 | 2.0 | 0.0 | 0.336 |
| `blk_tail_share_of_dur` | 67 | 67 | 0.1348 | 0.131 | 0.0037 | 0.336 |
| `blk_tail_words` | 67 | 67 | 28.0 | 25.0 | 3.0 | 0.356 |
| `blk_tail_span_s` | 67 | 67 | 7.2 | 6.4 | 0.8 | 0.367 |
| `blk_hook_wps` | 66 | 64 | 3.636 | 3.448 | 0.188 | 0.37 |
| `blk_tail_speech_s` | 67 | 67 | 7.2 | 6.4 | 0.8 | 0.371 |
| `blk_body_wps` | 66 | 67 | 3.5345 | 3.495 | 0.0395 | 0.386 |
| `blk_body_share_of_dur` | 67 | 67 | 0.7581 | 0.7603 | -0.0022 | 0.474 |
| `blk_hook_speech_s` | 67 | 67 | 6.4 | 6.4 | 0.0 | 0.504 |
| `blk_hook_span_s` | 67 | 67 | 6.4 | 6.4 | 0.0 | 0.526 |
| `blk_body_speech_s` | 67 | 67 | 41.1 | 41.7 | -0.6 | 0.564 |
| `blk_body_span_s` | 67 | 67 | 41.1 | 43.2 | -2.1 | 0.648 |
| `blk_body_share_of_words` | 67 | 67 | 0.7479 | 0.7453 | 0.0026 | 0.72 |
| `blk_hook_share_of_words` | 67 | 67 | 0.1124 | 0.1117 | 0.0007 | 0.757 |
| `blk_hook_share_of_dur` | 67 | 67 | 0.1229 | 0.1134 | 0.0096 | 0.771 |
| `blk_hook_words` | 67 | 67 | 21.0 | 23.0 | -2.0 | 0.839 |
| `blk_tail_wps` | 64 | 63 | 3.927 | 4.024 | -0.097 | 0.954 |
| `blk_tail_share_of_words` | 67 | 67 | 0.1429 | 0.1452 | -0.0024 | 0.97 |

### Specificity and naming

| feature | n strong | n weak | median strong | median weak | diff | Mann-Whitney p |
|---|---:|---:|---:|---:|---:|---:|
| `lex_entities_distinct` | 67 | 67 | 2.0 | 1.0 | 1.0 | 0.0107 |
| `lex_entities_n` | 67 | 67 | 2.0 | 1.0 | 1.0 | 0.0207 |
| `lex_tools_n` | 67 | 67 | 0.0 | 0.0 | 0.0 | 0.0254 |
| `lex_platforms_n` | 67 | 67 | 0.0 | 0.0 | 0.0 | 0.0568 |
| `specificity` | 67 | 67 | 4.255 | 3.448 | 0.807 | 0.0795 |
| `lex_specificity` | 67 | 67 | 4.255 | 3.448 | 0.807 | 0.0795 |
| `lex_money_mentions_n` | 67 | 67 | 0.0 | 0.0 | 0.0 | 0.0875 |
| `lex_numeric_evidence_per_10s` | 67 | 67 | 0.4425 | 0.2774 | 0.1651 | 0.113 |
| `lex_claims_per_10s` | 67 | 67 | 1.0204 | 0.8602 | 0.1602 | 0.128 |
| `lex_models_n` | 67 | 67 | 0.0 | 0.0 | 0.0 | 0.128 |
| `lex_technical_n` | 67 | 67 | 3.0 | 2.0 | 1.0 | 0.151 |
| `lex_numeric_evidence_n` | 67 | 67 | 3.0 | 1.0 | 2.0 | 0.153 |
| `lex_claims_n` | 67 | 67 | 6.0 | 5.0 | 1.0 | 0.173 |
| `numbers_n` | 67 | 67 | 3.0 | 1.0 | 2.0 | 0.179 |
| `lex_numbers_n` | 67 | 67 | 3.0 | 1.0 | 2.0 | 0.179 |
| `lex_brands_n` | 67 | 67 | 0.0 | 0.0 | 0.0 | 0.182 |
| `lex_numeric_evidence_per_100w` | 67 | 67 | 1.293 | 0.741 | 0.552 | 0.202 |
| `lex_spelled_numbers_n` | 67 | 67 | 2.0 | 1.0 | 1.0 | 0.593 |
| `lex_percentages_n` | 67 | 67 | 0.0 | 0.0 | 0.0 | 0.963 |

### Address and persuasion vocabulary

| feature | n strong | n weak | median strong | median weak | diff | Mann-Whitney p |
|---|---:|---:|---:|---:|---:|---:|
| `lex_superlatives_n` | 67 | 67 | 1.0 | 1.0 | 0.0 | 0.0871 |
| `lex_intensifiers_n` | 67 | 67 | 1.0 | 1.0 | 0.0 | 0.0996 |
| `lex_comparisons_n` | 67 | 67 | 0.0 | 1.0 | -1.0 | 0.256 |
| `lex_pronouns_n` | 67 | 67 | 27.0 | 22.0 | 5.0 | 0.267 |
| `lex_repeated_phrases_n` | 67 | 67 | 0.0 | 0.0 | 0.0 | 0.286 |
| `lex_cta_verb_per_100w` | 67 | 67 | 2.174 | 2.183 | -0.009 | 0.296 |
| `lex_direct_address_per_10s` | 67 | 67 | 1.626 | 1.5009 | 0.1251 | 0.33 |
| `lex_imperatives_n` | 67 | 67 | 1.0 | 1.0 | 0.0 | 0.339 |
| `lex_cta_verb_n` | 67 | 67 | 4.0 | 4.0 | 0.0 | 0.486 |
| `lex_second_person_n` | 67 | 67 | 8.0 | 7.0 | 1.0 | 0.498 |
| `questions_n` | 67 | 67 | 0.0 | 0.0 | 0.0 | 0.556 |
| `lex_questions_n` | 67 | 67 | 0.0 | 0.0 | 0.0 | 0.556 |
| `lex_questions_per_10s` | 67 | 67 | 0.0 | 0.0 | 0.0 | 0.594 |
| `lex_first_person_authority_n` | 67 | 67 | 0.0 | 0.0 | 0.0 | 0.643 |
| `lex_negations_n` | 67 | 67 | 2.0 | 2.0 | 0.0 | 0.677 |
| `lex_rhetorical_questions_n` | 67 | 67 | 0.0 | 0.0 | 0.0 | 0.738 |
| `lex_modals_n` | 67 | 67 | 3.0 | 3.0 | 0.0 | 0.907 |
| `lex_direct_address_per_100w` | 67 | 67 | 4.678 | 4.667 | 0.011 | 0.97 |
| `lex_first_person_n` | 67 | 67 | 4.0 | 5.0 | -1.0 | 0.973 |

### Emotional families

| feature | n strong | n weak | median strong | median weak | diff | Mann-Whitney p |
|---|---:|---:|---:|---:|---:|---:|
| `lex_urgency_per_100w` | 67 | 67 | 0.683 | 0.901 | -0.218 | 0.0525 |
| `lex_urgency_n` | 67 | 67 | 1.0 | 2.0 | -1.0 | 0.0561 |
| `lex_emotional_per_100w` | 67 | 67 | 0.0 | 0.0 | 0.0 | 0.269 |
| `lex_novelty_per_100w` | 67 | 67 | 1.01 | 1.117 | -0.107 | 0.323 |
| `lex_fear_per_100w` | 67 | 67 | 0.0 | 0.0 | 0.0 | 0.408 |
| `lex_emotional_n` | 67 | 67 | 0.0 | 0.0 | 0.0 | 0.412 |
| `lex_proof_per_100w` | 67 | 67 | 0.0 | 0.265 | -0.265 | 0.467 |
| `lex_proof_per_10s` | 67 | 67 | 0.0 | 0.1036 | -0.1036 | 0.516 |
| `lex_fear_n` | 67 | 67 | 0.0 | 0.0 | 0.0 | 0.572 |
| `lex_identity_per_100w` | 67 | 67 | 0.0 | 0.0 | 0.0 | 0.643 |
| `lex_opportunity_per_100w` | 67 | 67 | 0.505 | 0.49 | 0.015 | 0.644 |
| `lex_proof_n` | 67 | 67 | 0.0 | 1.0 | -1.0 | 0.713 |
| `lex_novelty_n` | 67 | 67 | 2.0 | 2.0 | 0.0 | 0.714 |
| `lex_identity_n` | 67 | 67 | 0.0 | 0.0 | 0.0 | 0.724 |
| `lex_opportunity_n` | 67 | 67 | 1.0 | 1.0 | 0.0 | 0.909 |

### Lexical diversity and morphology

| feature | n strong | n weak | median strong | median weak | diff | Mann-Whitney p |
|---|---:|---:|---:|---:|---:|---:|
| `lex_ttr` | 67 | 67 | 0.605 | 0.6278 | -0.0228 | 0.0387 |
| `lex_mattr50` | 65 | 63 | 0.7948 | 0.8108 | -0.016 | 0.0443 |
| `lex_pos_lite_gerunds_ing` | 67 | 67 | 5.0 | 4.0 | 1.0 | 0.435 |
| `lex_rttr` | 67 | 67 | 8.2545 | 8.4916 | -0.2371 | 0.569 |
| `lex_pos_lite_adverbs_ly` | 67 | 67 | 2.0 | 2.0 | 0.0 | 0.8 |
| `lex_pos_lite_past_ed` | 67 | 67 | 2.0 | 2.0 | 0.0 | 0.909 |

### Visual

| feature | n strong | n weak | median strong | median weak | diff | Mann-Whitney p |
|---|---:|---:|---:|---:|---:|---:|
| `scenes_n` | 67 | 67 | 4.0 | 3.0 | 1.0 | 0.11 |
| `cuts` | 67 | 67 | 8.0 | 6.0 | 2.0 | 0.147 |
| `screen_share` | 67 | 67 | 0.2222 | 0.1111 | 0.1111 | 0.234 |
| `avg_scene_s` | 67 | 67 | 16.067 | 17.925 | -1.858 | 0.312 |
| `text_overlay_density` | 67 | 67 | 1.0 | 1.0 | 0.0 | 0.418 |
| `cuts_per_min` | 67 | 67 | 7.059 | 6.752 | 0.307 | 0.42 |
| `b_roll_share` | 67 | 67 | 0.0 | 0.0 | 0.0 | 0.481 |
| `a_roll_share` | 67 | 67 | 0.2222 | 0.2222 | 0.0 | 0.573 |
| `split_share` | 67 | 67 | 0.0 | 0.0 | 0.0 | 0.628 |
## Script parts, on their own denominator

`reports/data/script_parts.json` splits on the same metric but over the 264 codes with a beat-derived
script (q1 +0.581, q3 +2.862, n=66 per side), and reports each part only where it exists — so the n per
row is much smaller than 66.

| part | n strong | median s strong | median share strong | n weak | median s weak | median share weak |
|---|---:|---:|---:|---:|---:|---:|
| hook | 66 | 7.6 | 13.8 % | 64 | 7.0 | 12.4 % |
| setup | 7 | 11.0 | 13.4 % | 11 | 4.7 | 9.1 % |
| problem | 18 | 8.6 | 18.4 % | 16 | 9.15 | 14.5 % |
| explanation | 54 | 17.3 | 34.1 % | 53 | 19.5 | 41.9 % |
| solution | 18 | 12.25 | 21.1 % | 19 | 8.4 | 15.3 % |
| proof | 32 | 19.25 | 32.9 % | 34 | 23.9 | 37.1 % |
| payoff | 37 | 10.3 | 18.6 % | 38 | 7.95 | 16.8 % |
| cta | 56 | 5.7 | 10.3 % | 51 | 4.4 | 8.4 % |

Three readings:

1. **The strong quartile reallocates, it does not extend.** Total spoken length is identical; explanation
   loses 2.2 s and 7.8 points of share, while solution gains 3.85 s, payoff 2.35 s and CTA 1.3 s.
2. **Explanation length is a symptom, not a virtue.** The weak quartile gives 41.9 % of its speech to the
   mechanism against 34.1 % for the strong one. A longer how is usually an unclear what.
3. **Proof length is not the differentiator either** (19.25 s vs 23.9 s, p=0.55). What matters about
   proof in this corpus is whether it is on screen (`03-visual-patterns.md`), not how long it is spoken.

## Roll shares, on their own denominator

`reports/data/visual_patterns.json` splits over the 295 frame-analysed codes (n=74 per side, q1 +0.543,
q3 +2.943):

| share | strong median | weak median |
|---|---:|---:|
| `a_roll_share` | 0.2222 | 0.2222 |
| `b_roll_share` | 0.0000 | 0.0000 |
| `split_share` | 0.0000 | 0.0000 |
| `screen_share` | **0.2222** | **0.1111** |

Screen share is the only roll that differs, and in the 67-per-side test above it does not clear p<0.05
(p=0.234). The stronger evidence for the screen is the pooled and creator-normalised correlation
(share_rate +0.203 pooled / +0.129 normalised, RELIABLE; save_rate +0.210 / +0.213), not this quartile
contrast — a 67-per-side Mann-Whitney inside a pre-selected corpus simply lacks power.

## Categorical contrasts, for completeness

Category medians with their difference against the pooled median are in
`reports/data/associations.json` (`categorical_contrasts`, 1 135 rows, bootstrap CI over 1 000
creator-resampled replicates, seed 20260911, no CI produced below 3 creators). The cells that matter are
tabulated in `01-general-conclusions.md` (roles B and D) and `02-what-viewers-seek.md`. The summary
position: of 159 reported cells across the eight vocabularies, **18 are SUFFICIENT_SAMPLE, 96 are
PROBABLE and 45 are INSUFFICIENT** — so most categorical contrasts cannot carry a claim at all, and
`05-script-parts.md` and `06-creators-and-references.md` say which.

## What this section licenses and what it forbids

**Licensed.** Two statements survive: name more distinct things, and give the solution sentence room.
Both are about content, not form.

**Forbidden.** Any claim that a duration, a pacing target, a cut rate, a caption style, an A-roll share,
a split share, a hook duration or a script length separates winners from losers in this niche. The data
says it does not — and says so inside a sample that was pre-selected to make such differences easier to
see, not harder.
