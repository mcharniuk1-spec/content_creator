# 17. Hook Analysis

**Denominators.** 266 analysis-ready reels carry a ta-v1 `hook_type` from a closed list of 13 values;
the boxplot draws the twelve cells with n ≥ 5, **n=257**. Hook *length* statistics divide by **260** —
the codes with a beat-derived hook (`hook_s` is never written from the clock-based fallback). First-word
and n-gram counts run over the **264** hook beats. Visual first-frame statistics divide by 266.
**Only `bold_claim` clears the SUFFICIENT_SAMPLE threshold**, so every individual cell below is PROBABLE
and only the grouped contrasts should be quoted [I-30].

## Hook type against performance

![Hook type vs performance — twelve cells, n=257](reports/charts/hook_type_vs_performance.png)

| hook_type | n | creators | median view_lift | median robust_z | share/1k | save/1k |
|---|---:|---:|---:|---:|---:|---:|
| demo_first | 18 | 14 | **9.55** | **2.52** | 17.1 | 21.1 |
| result_first | 24 | 18 | **4.20** | 1.74 | 20.0 | 33.1 |
| list_promise | 21 | 18 | 2.72 | 1.52 | 17.4 | **46.3** |
| question | 10 | 10 | 2.37 | 1.36 | 5.4 | 19.8 |
| curiosity_gap | 22 | 19 | 2.16 | 1.26 | 15.5 | 30.1 |
| warning_fear | 13 | 12 | 2.15 | 1.30 | 10.4 | 25.5 |
| bold_claim | **67** | **43** | 1.88 | 1.09 | 16.9 | 30.6 |
| contrarian | 23 | 19 | 1.71 | 2.04 | **7.6** | **13.9** |
| story_open | 13 | 11 | 1.43 | 0.89 | **0.5** | **1.7** |
| number_stat | 20 | 15 | 1.04 | 1.30 | 16.0 | 33.9 |
| problem_call_out | 17 | 15 | **0.49** | 0.67 | 9.8 | 22.0 |
| identity_call | 9 | 8 | **0.41** | 0.37 | 14.4 | 18.4 |

Grouped, the contrast is the largest hook effect measured in the wave. **Show-first** (`demo_first` +
`result_first`, n=42, 29 creators) runs at median `robust_z` **2.17** and `view_lift` **5.81** against
**1.21** and **1.80** for everything else (Mann-Whitney p=0.021 and 0.008). **Setup-first**
(`identity_call` + `story_open` + `problem_call_out`, n=39, 31 creators) runs at **0.67** and **0.80**
against **1.36** and **2.25** (p=0.002 on both) [I-05, I-06]. `bold_claim` — the niche's default, used in
67 reels by 43 creators — sits exactly at the corpus median on both metrics. It is the baseline, not an
advantage.

The same-creator evidence is the most persuasive part of this. `edhillai` published
[DNA7-d3o5sQ](https://www.instagram.com/reel/DNA7-d3o5sQ/), which opens on the artefact speaking its own
first words — **"Hello, how can I assist you? This voice assistant can replace your receptionist. I'll
show you how to build it in three easy steps."** (hook, 0.0–6.4 s) — at `robust_z` **+4.69**, and
[DXb8P08Dati](https://www.instagram.com/reel/DXb8P08Dati/), which opens on the series — **"Day one of two
AI tips to make you an N8N expert."** (hook, 0.0–9.4 s) — at `robust_z` **−1.04**. Same creator, same
subject area, same production; the difference is whether second one belongs to the thing or to the
programme.

## Question hooks are rare and expensive

Only **24 of 264** opening beats (9 %) contain a question mark. Their median `view_lift` is higher
(3.00 against 1.91) and their save rate is less than half (**0.0130 against 0.0284**) — and the
script-level question count is one of the strongest RELIABLE negatives in the entire run:
`questions_n` → `save_rate` rho **−0.229** (p=0.00031, creator-normalised −0.162, survives),
`lex_questions_per_10s` −0.235 (cn −0.186) and `lex_rhetorical_questions_n` −0.186 (cn −0.151) [I-07].
The corpus median `questions_n` is **0**. The exception proves the rule by being specific:
[Db9MT-axxcO](https://www.instagram.com/reel/Db9MT-axxcO/) opens **"What happens when you ask Claw to
apply to 500 jobs for you? I tried this and I landed six interviews in 24 hours."** (0.0–7.0 s) — the
question is answered inside the same breath, and the reel carries the corpus's third-best combined
share+save (47.9 and 68.9 per 1 000) on a 1.6× lift.

## Hook length is a distribution, not a target

![Hook length vs performance, n=260](reports/charts/hook_length_vs_performance.png)

Median hook **6.7 s** (p25 4.6, p75 9.6), mean 7.5 s, median **21.5 words** and **13.2 % of spoken
time**. Only **6 %** of reels close the hook inside 3 seconds, 31 % inside 5, and 19 % run past 10.
Hook duration correlates with nothing: `robust_z` rho +0.063 (p=0.31), `view_lift` +0.075 (p=0.23), and
the strong quartile's median hook is 7.6 s against 7.0 s (p=0.162). What *does* separate the quartiles is
**hook words: 26.5 against 22.0 (p=0.028)** — how much is promised, not how long the promising takes
[I-03]. Any audit that scores hooks against a 0–3 second rule is measuring something this niche does not
do, and that is the one criticism of Max's card set that should be withdrawn (see chapter 32).

## The visual hook

First-frame type across the 266 analysed reels: SPLIT_SCREEN 73, A_ROLL_MEDIUM 57, A_ROLL_CLOSE_UP 45,
B_ROLL_CONTEXT 18, SCREEN_RECORDING 16, OVERLAY 14, A_ROLL_WIDE 13, A_ROLL_TALKING_HEAD 9, UI_DEMO 8,
B_ROLL_PROCESS 8, SCREENSHOT 7, MOTION_GRAPHIC 7, HOOK_VISUAL 6, DATA_VISUAL 5, MEME 4, TEXT_ONLY 4,
TRANSITION 1.

| coarse first state | n | median view_lift | median robust_z | share/1k |
|---|---:|---:|---:|---:|
| screen (recording / screenshot / UI demo / data visual) | 35 | **5.25** | **2.13** | **21.3** |
| text or graphic | 31 | 2.12 | 1.43 | — |
| A-roll | 114 | 1.99 | 1.15 | — |
| B-roll | 23 | 1.60 | 1.25 | — |
| split screen | 63 | 1.34 | 1.05 | 13.5 |

Opening on a screen rather than a face is worth roughly **half again the forwarding rate** (share 0.0213
vs 0.0140), and the creator-normalised correlation (**+0.285, p=0.00025, n=161**) is *stronger* than the
pooled one (+0.208, p=0.00063) — the strongest form of evidence this dataset can produce, because it
means the effect holds inside individual creators' own output and is not a fact about which creators like
screens [I-09]. Individual sub-cells are small but point the same way: UI_DEMO first (n=8, 7 creators)
median `view_lift` 29.2, DATA_VISUAL first (n=5) 18.7. One caution: the `is_visual_hook` flag is set on
frame 0 of all 295 codes, so it is a labelling artefact and carries no signal.

**Verbal × visual combinations with n ≥ 5.** `result_first` on `A_ROLL_MEDIUM` (n=8, 6 creators,
`robust_z` 2.98, `view_lift` 8.07) is the strongest; `contrarian` on `A_ROLL_CLOSE_UP` (6/5, 1.86/4.98)
and `curiosity_gap` on `A_ROLL_CLOSE_UP` (5/5, 1.76/13.42) follow. **`bold_claim` on `SPLIT_SCREEN` is
the single most common combination in the niche (n=22, 17 creators) and one of the weakest**
(`robust_z` 0.84, `view_lift` 1.21) — the default verbal hook over the default layout, and it performs
like the default.

## Strategic implication

**(1) Frame one is the artefact mid-action**, with the promise already burned in as a top banner; the
presenter arrives at the first explanation beat, not before. **(2) The hook is one complete promise in
5–10 seconds and 20–30 words** — never truncated to satisfy a three-second rule, and judged on whether
the promise is concrete. **(3) Write it as a statement.** A question is permitted only when the same
sentence answers it. **(4) Ban series preambles and "if you are a business owner" addresses**: the
identity-call shape is the worst-performing hook in the corpus, and the same-creator pair above shows
the cost is not a sampling accident. **(5) Do not open on split screen** (chapter 23).

**Confidence: PROBABLE** for the grouped show-first and setup-first contrasts (n=42 and 39, 29 and 31
creators, p=0.002–0.021, but no single cell clears the size threshold). **RELIABLE** for the
questions-depress-saves finding (n=245, 95 creators, p=0.0003, survives creator normalisation) and for
the screen-first share-rate finding (n=266/161, p<0.001, normalised effect stronger than pooled).
**RELIABLE** for the hook-length null. **INSUFFICIENT** for every verbal × visual combination (n=5–8).
