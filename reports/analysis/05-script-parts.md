# 05 — Script parts

Spec §11. Typical part lengths and shares, their distributions, the strong-vs-ordinary split, the split by
creator reliability, by topic and by narrative archetype; frequency of every hook / pain / solution /
proof / CTA / narrative / transition type; and the recurring phrases and rhetorical devices visible in the
lexical features.

**Sources.** `reports/data/script_parts.json` (n=264 — codes whose script block was built from ta-v1
beats, i.e. `features_json.script.part_source == 'beats'`; **not** the timing-only fallback and **not** the
full `ANALYSIS_READY` tier), `data/analysis/transcripts/*.json` (266 semantic reads, 1 527 beats),
`video_features.features_json.lexical` over the same codes, `reports/data/category_freq_perf.json`.

**Part definition.** Beat roles fold into eight columns per method §5: `hook_s` ← hook + hook_extension;
`setup_s` ← setup + audience; `problem_s` ← problem + pain + tension; `explanation_s` ← explanation +
mechanism + context; `solution_s` ← solution; `proof_s` ← proof + example; `payoff_s` ← payoff +
transformation; `cta_s` ← cta + closing. `objection`, `rehook` and `other` stay outside the eight and are
counted separately. `total_s` is the **spoken** length, shorter than `reels.dur` for any reel with a silent
opening or an outro card; the two are never swapped.

---

## 1. Typical lengths and shares

Medians over the codes where the part exists (n differs per row by design):

| part | n | % of 264 | median s | mean s | median share of speech | mean share | median words |
|---|---:|---:|---:|---:|---:|---:|---:|
| hook | 260 | 98 % | 6.7 | 7.50 | 13.2 % | 14.6 % | 21.5 |
| setup | 34 | 13 % | 7.8 | 9.41 | 14.0 % | 14.3 % | 29 |
| problem | 64 | 24 % | 8.95 | 12.04 | 16.4 % | 20.2 % | 32 |
| explanation | 208 | 79 % | 18.6 | 23.54 | 38.3 % | 39.4 % | 64 |
| solution | 70 | 27 % | 10.4 | 12.95 | 20.1 % | 25.9 % | 36 |
| proof | 133 | 50 % | 17.0 | 23.19 | 30.5 % | 36.3 % | 57 |
| payoff | 150 | 57 % | 8.2 | 10.24 | 17.0 % | 17.8 % | 26.5 |
| cta | 216 | 82 % | 4.95 | 6.27 | 9.7 % | 11.5 % | 21 |

Whole-reel reference values: median spoken length **53.6 s**, **182 words**, **3.52 words per second**;
median video duration 54.2 s in the analysed set (47.6 s across all 3 211 ingested reels). Shares are
computed per part against that reel's own speech seconds, so they do not sum to 1.0 across the table —
read each row on its own.

### Distributions, not just medians

| part | p25 | median | p75 | notes |
|---|---:|---:|---:|---|
| hook_s | 4.6 | 6.7 | 9.6 | 6 % close inside 3 s, 31 % inside 5 s, 19 % run past 10 s |
| total_s | 39.1 | 53.6 | 69.7 | min 0.8 s (a five-word ASR row), max 259.0 s |
| total_words | 128.8 | 182 | 237 | max 1 034 |
| wps | 3.07 | 3.52 | 3.83 | min 0.65, max 6.25 |
| time to first proof beat | 11.1 | 22.0 | 32.0 | n=133 |
| time to solution beat | 7.7 | 19.7 | 29.0 | n=70 |
| CTA start as share of speech | 0.84 | 0.90 | 0.94 | 94 % in the final quarter; 3 of 216 before halfway |
| problem start as share of speech | 0.15 | 0.21 | 0.39 | 56 % inside the first quarter |

`unbucketed_s` (objection + rehook + other) is non-zero in only 35 of 264 reels, so the eight columns
account for essentially all spoken time.

---

## 2. Orderings

1 527 beats, 264 reels, median 6 beats per reel (min 0, max 12). The hook is the first beat in **259 of
264**; a CTA or closing beat is last in **215**. Raw beat-role frequencies:

hook 259 · mechanism 250 · cta 205 · example 157 · payoff 145 · proof 104 · explanation 96 · solution 84 ·
context 40 · setup 31 · tension 31 · problem 29 · closing 23 · objection 19 · rehook 15 · pain 12 ·
transformation 10 · other 5 · audience 3 · hook_extension 2.

Collapsed to the eight buckets and de-duplicated, there are **146 distinct orderings across 264 reels**.
The ten most frequent:

| ordering | n |
|---|---:|
| HOOK > EXPLAIN > PAYOFF > CTA | 27 |
| HOOK > EXPLAIN > CTA | 13 |
| HOOK > EXPLAIN > PROOF > CTA | 10 |
| HOOK > PROOF > CTA | 8 |
| HOOK > PROOF > PAYOFF > CTA | 6 |
| HOOK > EXPLAIN > PROOF > PAYOFF > CTA | 6 |
| HOOK > SOLUTION > PAYOFF > CTA | 5 |
| HOOK > PROOF (no CTA) | 5 |
| HOOK > EXPLAIN > PROOF > EXPLAIN > CTA | 5 |
| HOOK > SETUP > EXPLAIN > PROOF > PAYOFF | 4 |

No single ordering covers more than 10 % of the corpus. The stable facts are the two endpoints (hook
first, CTA last) and the dominance of explanation in the middle.

---

## 3. Strong versus ordinary

Split on `robust_z` quartiles inside the 264-code set (n=66 per side, q1 **+0.581**, q3 **+2.862**). Per
method §1.4 the weak side still beats its authors' medians — this is strong-vs-strong.

| part | n S | median s S | share S | n W | median s W | share W | Δ seconds |
|---|---:|---:|---:|---:|---:|---:|---:|
| hook | 66 | 7.6 | 13.8 % | 64 | 7.0 | 12.4 % | +0.6 |
| setup | 7 | 11.0 | 13.4 % | 11 | 4.7 | 9.1 % | +6.3 |
| problem | 18 | 8.6 | 18.4 % | 16 | 9.15 | 14.5 % | −0.55 |
| explanation | 54 | 17.3 | 34.1 % | 53 | 19.5 | 41.9 % | **−2.2** |
| solution | 18 | 12.25 | 21.1 % | 19 | 8.4 | 15.3 % | **+3.85** |
| proof | 32 | 19.25 | 32.9 % | 34 | 23.9 | 37.1 % | −4.65 |
| payoff | 37 | 10.3 | 18.6 % | 38 | 7.95 | 16.8 % | +2.35 |
| cta | 56 | 5.7 | 10.3 % | 51 | 4.4 | 8.4 % | +1.3 |

Significance (Mann-Whitney, from `associations.json`, n=67 per side on its own denominator):
`solution_s` **p=0.0065** — the only part clearing p<0.01; `hook_words` p=0.028; `setup_s` p=0.057;
`cta_s` p=0.075; `payoff_s` p=0.123; `explanation_s` p=0.236; `proof_s` p=0.551; `problem_s` p=0.809;
`hook_s` p=0.162; `total_s` p=0.582.

**The pattern is reallocation, not extension.** Total spoken length is identical between the quartiles
(56.9 s vs 58.0 s, p=0.98). Strong reels take seconds out of the mechanism and put them into the solution
statement, the payoff and the closing line.

---

## 4. By creator reliability

Joining the 268 analysed reels to `creator_stats.reliability` at snapshot 3: 28 reels from 15 CONSISTENT
creators, 240 from 87 HIGH_VARIANCE creators (no SMALL_SAMPLE creators appear in the analysed set).

| | CONSISTENT (n=28) | HIGH_VARIANCE (n=240) |
|---|---:|---:|
| hook_s | 6.7 | 6.7 |
| problem_s | 10.5 (n=6) | 8.9 (n=58) |
| explanation_s | 17.4 (n=26) | 19.0 (n=182) |
| solution_s | 10.6 (n=8) | 10.4 (n=62) |
| proof_s | 11.2 (n=19) | 18.6 (n=114) |
| payoff_s | 10.6 (n=15) | 8.1 (n=135) |
| cta_s | 6.3 (n=25) | 4.8 (n=191) |
| total_s | 53.8 | 53.5 |
| total_words | 177.5 | 184 |
| wps | 3.4 | 3.5 |
| duration | 57.4 | 53.6 |
| median robust_z | **0.60** | **1.37** |
| median view_lift | **0.65** | **2.38** |
| median share_rate | 0.0121 | 0.0156 |
| median save_rate | 0.0212 | 0.0283 |

**Script shape is identical; the scores are not.** The gap is arithmetic: `robust_z` and `view_lift`
divide by the creator's own spread, so a steady creator produces small lifts from good reels and a
lottery account produces enormous lifts from ordinary ones. Two real differences in shape: consistent
creators spend less on proof (11.2 s vs 18.6 s) and more on the closing line (6.3 s vs 4.8 s).

---

## 5. By topic

Top eight topics by size, from `script_parts.json.by_topic_top8`:

| topic | n | hook | problem | explanation | solution | proof | payoff | cta |
|---|---:|---|---|---|---|---|---|---|
| Сборка агентов и мультиагентные системы | 27 | 8.4 s / 15 % | 7.0 s (n=3) | 20.6 s / 37 % | 11.4 s (n=6) | 19.4 s / 37 % | 11.5 s / 14 % | 5.0 s / 8 % |
| AI-видео и производство контента | 22 | 7.0 s / 16 % | 8.2 s (n=4) | 17.6 s / 42 % | 10.7 s (n=6) | 11.0 s / 23 % | 8.1 s / 18 % | 4.5 s / 13 % |
| Claude Code: скиллы, плагины, команды | 22 | 6.3 s / 10 % | 16.3 s (n=6) | 22.2 s / 44 % | 12.4 s (n=8) | 23.6 s / 32 % | 7.8 s / 17 % | 4.4 s / 9 % |
| Бесплатный доступ и обход платы | 21 | 6.4 s / 13 % | 8.9 s (n=3) | 18.0 s / 45 % | 12.4 s (n=7) | 19.7 s / 37 % | 7.7 s / 23 % | 5.1 s / 12 % |
| Новости моделей и лабораторий | 21 | 8.1 s / 10 % | 10.2 s (n=4) | 23.4 s / 40 % | — | 31.3 s / 36 % | 10.2 s / 14 % | 6.9 s / 9 % |
| Дизайн и сайты через AI | 19 | 6.2 s / 16 % | 10.2 s (n=1) | 18.6 s / 48 % | 7.5 s (n=3) | 33.0 s / 43 % | 6.2 s / 17 % | 4.3 s / 9 % |
| Лидогенерация, скрейпинг, CRM | 14 | 5.2 s / 14 % | 6.8 s (n=5) | 20.8 s / 43 % | 8.4 s (n=8) | 10.2 s / 19 % | 5.1 s / 14 % | 6.7 s / 14 % |
| AI-агентство как бизнес | 13 | 6.7 s / 11 % | 20.9 s (n=4) | 20.6 s / 34 % | 14.3 s (n=4) | 15.8 s / 29 % | 11.4 s / 19 % | 6.5 s / 14 % |

Every topic cell is PROBABLE or INSUFFICIENT — none reaches n≥30 with ≥8 creators. The usable
observations: news reels carry the longest proof (31.3 s) and the longest hooks (8.1 s); lead-generation
reels carry the shortest hooks (5.2 s) and the longest CTAs relative to length; agency-business reels
carry by far the longest problem statements (20.9 s on n=4 — INSUFFICIENT, but it is the only topic where
the problem beat is the biggest part).

---

## 6. By narrative archetype

| narrative | n | creators | hook | explanation | proof | payoff | cta | median view_lift | median robust_z |
|---|---:|---:|---|---|---|---|---|---:|---:|
| demo_walkthrough | 62 | 42 | 7.8 s / 14 % | 19.9 s / 38 % | 19.3 s / 34 % | 8.0 s / 15 % | 5.0 s / 9 % | **3.70** | **1.71** |
| tutorial_steps | 45 | 32 | 6.7 s / 14 % | 22.6 s / 52 % | 11.2 s / 20 % | 6.1 s / 16 % | 4.7 s / 9 % | 1.88 | 1.10 |
| listicle | 43 | 32 | **4.6 s / 9 %** | 24.3 s / 46 % | 37.8 s / 72 % | 6.7 s / 13 % | 5.3 s / 10 % | 1.91 | 1.23 |
| problem_solution | 34 | 23 | 6.9 s / 15 % | 16.5 s / 32 % | 7.4 s / 15 % | 8.8 s / 19 % | **3.9 s / 8 %** | 1.01 | 1.16 |
| announcement_news | 30 | 21 | 6.8 s / 14 % | 16.4 s / 35 % | 13.7 s / 24 % | 8.3 s / 19 % | 5.3 s / 13 % | 1.29 | 0.96 |
| story_arc | 17 | 13 | 7.8 s / 15 % | 13.1 s / 27 % | 17.1 s / 27 % | 11.1 s / 19 % | 7.6 s / 14 % | 3.47 | 1.34 |
| myth_bust | 13 | 9 | **8.5 s / 16 %** | 12.4 s / 28 % | 16.7 s / 19 % | 11.3 s / 23 % | 5.6 s / 9 % | 1.71 | **1.93** |
| rant_opinion | 9 | 6 | 8.0 s / 11 % | 15.4 s / 32 % | 27.2 s / 25 % | 15.0 s / 21 % | 4.2 s / 6 % | 1.57 | 1.08 |
| other | 8 | 6 | 7.8 s / 16 % | 9.8 s / 24 % | 19.2 s / 32 % | 11.1 s / 24 % | 6.2 s / 14 % | 3.66 | 1.97 |
| contrast_before_after | 5 | 5 | 5.8 s / 8 % | 12.8 s / 32 % | 15.2 s / 30 % | 6.7 s / 10 % | 8.0 s / 14 % | 0.67 | 1.03 |

Five archetypes are SUFFICIENT_SAMPLE (demo_walkthrough, tutorial_steps, listicle, problem_solution,
announcement_news); the rest are PROBABLE. **demo_walkthrough is both the largest and the highest-lift
archetype** — and it is the one whose parts are most evenly balanced (38 % explanation, 34 % proof).
Listicles run the shortest hooks (4.6 s) and by far the largest proof share (72 %, because every list item
is tagged as an example). Myth-bust carries the longest hooks (8.5 s) and the second-highest robust_z
(1.93) on the smallest share of speech given to explanation.

---

## 7. Frequency of each type

### Hook types (n=266, 13 values, only `bold_claim` reaches SUFFICIENT_SAMPLE)

bold_claim 67 (43 creators) · result_first 24 (18) · contrarian 23 (19) · curiosity_gap 22 (19) ·
list_promise 21 (18) · number_stat 20 (15) · demo_first 18 (14) · problem_call_out 17 (15) ·
story_open 13 (11) · warning_fear 13 (12) · question 10 (10) · identity_call 9 (8) · other 9 (9).

### Pain (n=266, 13 values, two SUFFICIENT_SAMPLE)

cost_money 48 (33) · dont_know_where_to_start 34 (30) · keeping_up_with_ai 29 (24) · missing_skills 25 (20) ·
quality_trust 25 (20) · other 24 (21) · time_waste 20 (17) · chaos_no_process 17 (14) ·
manual_repetition 15 (13) · scaling_without_hiring 8 (8) · tool_overload 8 (8) · fear_of_replacement 8 (6) ·
slow_response_to_leads 5 (3).

### Solution type (n=266, three SUFFICIENT_SAMPLE)

tool_walkthrough 60 (40) · workflow_recipe 51 (35) · resource_handoff 38 (28) ·
framework_mental_model 25 (16) · agent_build 23 (17) · other 23 (17) · case_story 18 (15) ·
comparison 12 (10) · prompt_technique 10 (10) · warning_dont 6 (6).

### Proof type (n=266, three SUFFICIENT_SAMPLE)

screen_demo 84 (50) · none 68 (46) · numbers 36 (28) · personal_story 28 (20) · authority_claim 25 (20) ·
third_party_data 16 (12) · before_after 5 (5) · client_story 4 (3, INSUFFICIENT).

### CTA type (n=266, two SUFFICIENT_SAMPLE)

comment_keyword 158 (71) · none 58 (30) · follow 17 (13) · link_in_bio 12 (6) ·
question_to_audience 11 (9) · dm 3 (2, INSUFFICIENT) · next_video 3 (3, INSUFFICIENT) ·
free_resource 2 (INSUFFICIENT) · save_share 2 (INSUFFICIENT).

The comment keywords actually spoken, where recoverable from the CTA beat text: the most frequent are
generic placeholders ("comment *the* word below" patterns, 14 occurrences), then `AI` 7, `agent` 4,
`section` 3, `website` 2, `design` 2, `prompt` 2, `jarvis` 2, `canvas` 2, `flow` 2, and one-letter gates
such as `W`.

### Narrative (n=266, five SUFFICIENT_SAMPLE)

See §6. demo_walkthrough 62 · tutorial_steps 45 · listicle 43 · problem_solution 34 ·
announcement_news 30 · story_arc 17 · myth_bust 13 · rant_opinion 9 · other 8 · contrast_before_after 5.

### Positioning and funnel role (n=266)

educator 138 (68 creators, view_lift 1.73) · news 38 (27, 2.01) · builder 38 (27, **3.42**) ·
seller 31 (20, 1.17) · entertainer 21 (13, 3.12).
Funnel: awareness 125 (view_lift 2.16) · conversion 83 (**3.50**) · trust 58 (**1.06**, the weakest).

### Transition types

Only one transition type is observed anywhere in the corpus: **663 `hard_cut_or_more`** and
**15 `unknown`**. Per SPEC §5, a transition is recorded only where fa-v1 saw two adjacent labelled samples
differ; everything else becomes `unknown`. There is no evidence in this dataset for dissolves, whips,
match cuts or zoom transitions, and their absence is a measurement artefact of the 9-sample sampling,
not a finding about the niche.

---

## 8. Recurring phrases and rhetorical devices

### Sentence openings (counts over the analysed codes, from `lexical.sentence_openings`)

"this is" 26 · "you can" 23 · "if you" 21 · "it's called" 20 · "here's how" 14 · "so you" 14 ·
"so this" 10 · "let me" 10 · "i just" 10 · "and the" 8 · "and this" 8 · "and it" 8 · "now you" 7 ·
"the first" 7 · "but here's" 7 · "you just" 7 · "most people" 7.

### Hook openings specifically (first words of the 264 hook beats)

First word: "I" 22 · "this" 18 · "if" 16 · "you" 15 · "so" 11 · "the" 10 · "here's" 8 · "someone" 6 ·
"I'm" 6 · "Claude" 5 · "hey" 5.
First bigram: "you can" 10 · "if you" 9 · "I just" 9 · "this is" 7 · "if you're" 4 · "here's how" 4 ·
"Claude can" 3 · "most people" 3 · "someone just" 3.
First trigram: "you can now" 7 · "if you want" 4 · "this is what" 3 · "I just built" 3 ·
"Claude can now" 2 · "nobody is talking" 2 · "here's how to" 2 · "most people think" 2 ·
"one developer just" 2.

The niche's hook grammar is three templates: **"you can now X"** (new capability), **"I just X"**
(first-person demonstration) and **"if you X, then Y"** (conditional address — which is also the
identity-call family that underperforms, see `01-general-conclusions.md` role D).

### Sentence endings

"right now" 13 · "for free" 11 · "for you" 11 · "on github" 10 · "to you" 7 · "do it" 6 · "use it" 6 ·
"it works" 5 · "right here" 5 · "single day" 5 · "the link" 5.
Sentences in this niche end on a destination or an availability claim, not on a conclusion.

### Imperative verbs

comment 41 · follow 14 · let 13 · go 12 · look 9 · think 9 · imagine 7 · do 7 · click 7 · tell 6 ·
make 6 · open 6 · start 5 · write 5 · build 5 · see 5 · copy 4 · take 4 · run 4 · check 3 · add 3.
**"Comment" is the single most common imperative in the corpus** — three times more frequent than the
next verb — which is the lexical signature of the keyword gate.

### Repeated phrases within a single reel

"if you want to" 3 · "you want to learn" 2 · "you don't have to" 2 · "exactly how to use" 2, then a long
tail of one-offs. Median `lex_repeated_phrases_n` is 0 in both the strong and the weak quartile
(p=0.286) — deliberate phrase repetition is rare. What the strong quartile *does* repeat is vocabulary:
its type-token ratio is **lower** (0.605 vs 0.628, p=0.039) and its MATTR50 is lower (0.795 vs 0.811,
p=0.044), i.e. winners keep saying the same tool name and the same step word rather than reaching for
variety.

### Keyphrase bigrams

"claude code" 11 · "it will" 11 · "you will" 10 · "open source" 8 · "to build" 7 · "click on" 7 ·
"your business" 7 · "cloud code" 7 · "chat gpt" 6 · "ai agent" 6 · "gpt 6" 6 · "your ai" 6.
Note "cloud code" (7) alongside "claude code" (11): Whisper mis-transcribes the product name
consistently, which is why the `tools_mentioned` vocabulary carries both spellings and why entity counts
should be read as mentions-of-anything-known rather than distinct products.

### Rhetorical devices

`semantics.rhetorical_devices` is free text and produced 975 distinct strings across 266 reels, so no
single device reaches a countable frequency. The recurring families, by repeated wording: numbered steps
or a numbered list (17 combined), borrowed authority (6), price contrast or price anchoring (6),
objection pre-emption (3), future pacing (4), rule of three (3), keyword gate (3), benefit stacking (3),
delayed reveal (2), mid-roll rehook (2), myth vs reality (2), share-with-a-peer close (2).

The exact, countable versions of the same observations live in the lexical features:
`lex_imperatives_n` (median 1), `lex_superlatives_n` (median 1), `lex_intensifiers_n` (median 1),
`lex_negations_n` (median 2), `lex_modals_n` (median 3), `lex_second_person_n` (median 8),
`lex_first_person_n` (median 4-5), `lex_questions_n` (median **0**), `lex_numbers_n` (median 3 strong /
1 weak), `lex_claims_n` (median 6 strong / 5 weak).

### Sentence source, for honesty

255 of the analysed transcripts are punctuated by Whisper and split on punctuation; **11 have no
punctuation at all** and are split on Whisper's own VAD phrase boundaries (`sentence_source =
'segments'`). Per-sentence statistics from the two groups are never pooled silently — the field records
which happened on every row.
