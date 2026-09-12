# 13. Transcript Categorization

**Denominators.** 275 codes have a `transcripts` row; **7 of those rows are empty** (Whisper with
`vad_filter` heard no speech — music-only or text-on-screen reels) and get their own
`TRANSCRIPT_UNUSABLE` tier rather than being folded into frames-only. **268** transcripts are usable
(words > 0 **and** timed segments); **266** carry a ta-v1 semantic read; **264** produced a beat parse,
yielding **1 527 beats**. Every language, script and wording statement in this report divides by 266 or
264 and says which. The four codes with a transcript and frames but no beat-derived script block
(`features_json.script.part_source != 'beats'`) are excluded from all `*_s` columns by design — the
clock-based timing fallback (method §5.1) never writes those columns, because a five-second hook by the
clock is not a hook by meaning.

![Corpus coverage funnel — 268 of 3 211 codes carry both a script and a frame read](reports/charts/corpus_coverage_funnel.png)

The funnel is a denominator comparison, not a drop-off sequence: frames and transcripts are extracted
independently, so the stages are not strictly nested. What it establishes is the number that governs
this entire report — **268 / 3 211 = 8.3 %**, and not a random 8.3 %. `deep.py` only ever processed
reels `score.py` had already ranked near the top of their creator's output, so the median `robust_z`
inside the analysed tier is **+1.264** against **0.000** across all 3 211 [I-01]. Read every categorical
table below as a description of the already-successful part of the niche.

## What ta-v1 produces per reel

Each of the 266 semantic reads returns three layers. **Closed vocabularies** — `topic`, `subtopic`,
`pain`, `solution_type`, `proof_type`, `hook_type`, `cta_type`, `narrative`, `positioning_type`,
`funnel_role` — are normalised against a fixed list and the raw label is always kept alongside.
**Free prose** — `subject`, `thesis`, `audience`, `desire`, `mechanism`, `objection`, `payoff`,
`rhetorical_devices`, `visual_to_script_sync` — is a judgement, not a measurement. **Counts** —
`open_loops`, `pattern_interrupts`, `numbers_used`, `tools_mentioned`, `models_mentioned` — are the
model's own tallies over the transcript. A fourth block, `quality` (specificity, novelty, clarity,
info_density, grounded), and a self-assessed `confidence` travel with every row.

| ta-v1 self-assessed confidence | codes |
|---|---:|
| RELIABLE | 161 |
| PROBABLE | 94 |
| INSUFFICIENT | **11** |

The 11 INSUFFICIENT rows are kept, not dropped, and this is the right decision: a suppressed row is a
fact about the data. The clearest case is
[DcxV37-CJOC](https://www.instagram.com/reel/DcxV37-CJOC/), where ASR captured five words —
**"Did you know that the-"** (hook beat, 0.0–0.8 s) — of a 62-second reel that reached **559 515 plays**
on an 83 168 median and carries the corpus's third-highest save rate at **72.2 per 1 000**. Nothing in
this report's script findings can see that reel. It is the standing reminder of what transcript-only
analysis cannot reach.

**The frames can see it, though.** fa-v1's read of the same code records a host holding up a small
printed card with a pink dot pattern under a cut-out caption reading "How _ Advanced Design Effects",
one held `A_ROLL_MEDIUM` state across all nine samples and no proof visual at all. That is a complete
description of a reel the transcript pipeline registered as four broken words — and it is the argument
for keeping both analyses joined at the code rather than choosing one.

## Beat roles and how they fold

The beat vocabulary has twenty roles. Raw frequencies over 1 527 beats: hook 259 · mechanism 250 ·
cta 205 · example 157 · payoff 145 · proof 104 · explanation 96 · solution 84 · context 40 · setup 31 ·
tension 31 · problem 29 · closing 23 · objection 19 · rehook 15 · pain 12 · transformation 10 · other 5 ·
audience 3 · hook_extension 2. Those fold into the eight script-part columns of method §5 (`hook_s` ←
hook + hook_extension; `problem_s` ← problem + pain + tension; `explanation_s` ← explanation +
mechanism + context; `proof_s` ← proof + example; `payoff_s` ← payoff + transformation; `cta_s` ← cta +
closing). `objection`, `rehook` and `other` deliberately stay outside the eight, because they are moves
that can appear anywhere and folding them in would make the shares meaningless; their seconds are kept
as `unbucketed_s`, which is non-zero in only **35 of 264** reels.

## Two transcription defects that change how counts must be read

**Punctuation.** Whisper punctuates **255** of the 266 usable transcripts; the other **11** have none at
all, and each timed segment becomes one pseudo-sentence at Whisper's own VAD phrase boundary.
`sentence_source` records which happened on every row, so per-sentence statistics from the two groups
are never silently pooled.

**Product names.** The keyphrase bigrams contain **"claude code" 11** and **"cloud code" 7** — Whisper
mis-hears the product name consistently. The `tools_mentioned` vocabulary therefore carries both
spellings as separate rows (Claude code n=16 at median view_lift 7.81; Claude Code n=13 at 0.87;
cloud code n=8 at 3.02), and they are reported as they are rather than silently merged. The practical
consequence: `lex_entities_n` counts **mentions of anything the lexicon knows**, not distinct products —
read `lex_entities_distinct` for that.

## How much of the grid can actually carry a claim

Of **159** reported categorical cells across the eight vocabularies, **18 are SUFFICIENT_SAMPLE
(n ≥ 30 and ≥ 8 creators), 96 are PROBABLE and 45 are INSUFFICIENT (n < 5 or < 3 creators)**. All
**20** `subtopic` cells are INSUFFICIENT — every one is n ≤ 2. Only one `hook_type` (`bold_claim`),
two `pain` values, three `solution_type` values, three `proof_type` values and two `cta_type` values
clear the size threshold, and **no `topic` cell does** [I-30]. Coverage inside the analysed set is
otherwise near-complete: 266 of 268 rows carry a topic, a pain and a hook type; 256 carry a CTA type.

## Strategic implication

Two operating rules. First, **no M2 hypothesis or card may cite a category cell below n=5 or 3
creators**, and every cell it does cite must carry its `n`, `n_creators` and confidence label onto the
card — the thinness of the grid is itself a finding, and hiding it would convert a suppressed cell into
a false claim. Second, **the next processing wave must buy breadth, not depth**: more codes per cell,
not more features per code. Adding a twelfth lexical family to 266 reels changes nothing about the 20
subtopic cells that cannot be spoken about at all.

**Confidence: RELIABLE** for the coverage counts and the confidence distribution (direct counts over the
pipeline's own outputs). **PROBABLE** for anything resting on the closed vocabularies themselves: they
are LLM judgements normalised to a fixed list, not measurements, and `analysis_confidence` travels with
every row for that reason.
