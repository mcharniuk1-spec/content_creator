# 18. CTA Analysis

**Denominators.** 256 of the 266 analysis-ready reels with a ta-v1 read carry a `cta_type` from a closed
list of nine values (the boxplot drops cells under 5, leaving the five named below). CTA *position and
length* statistics divide by the **216** reels whose beat parse contains a `cta` or `closing` beat —
82 % of the 264 parsed reels; **58 reels have no CTA at all**. Gate-versus-no-gate comparisons run on
n=214 for the rate tests [I-12]. Baselines: median `view_lift` 2.03, `robust_z` 1.26, comment rate,
share rate 0.0152 and save rate 0.0278.

![CTA type vs performance — five cells with n≥5, n=256](reports/charts/cta_type_vs_performance.png)

| cta_type | n | creators | median view_lift | median robust_z | comment/1k | share/1k | save/1k | confidence |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| comment_keyword | **158** | **71** | 2.08 | **1.2475** | 21.7 | 17.0 | **34.0** | SUFFICIENT_SAMPLE |
| none | 58 | 30 | 1.72 | **1.2481** | 0.9 | 9.6 | **12.4** | SUFFICIENT_SAMPLE |
| follow | 17 | 13 | 2.25 | 1.16 | — | 15.5 | 35.4 | PROBABLE |
| link_in_bio | 12 | 6 | 1.02 | 1.10 | — | 13.7 | 8.8 | PROBABLE |
| question_to_audience | 11 | 9 | **4.08** | 1.79 | — | 18.3 | 13.4 | PROBABLE |
| dm / next_video / free_resource / save_share | 3/3/2/2 | ≤3 | — | — | — | — | — | INSUFFICIENT |

## The central finding: the gate buys engagement, not distribution

**59 % of the analysed corpus (158 of 266) runs a comment-keyword gate**, and it is the most consequential
single fact in this report — not because of what it does to reach, but because of what it does to M2's
own selection machinery.

| | gated | ungated | ratio | p |
|---|---:|---:|---:|---:|
| comment_rate | 0.0217 | 0.0009 | **×23** | 4e-23 |
| save_rate | 0.0340 | 0.0120 | **×2.8** | 4e-10 |
| share_rate | 0.0170 | 0.0096 | **×1.8** | 0.00015 |
| view_lift | 2.08 | 1.72 | — | **0.58** |
| robust_z | 1.2475 | 1.2481 | — | **0.63** |

Two medians agreeing to four decimal places (1.2475 against 1.2481) is as flat as a comparison gets. The
gate multiplies comment rate twenty-three-fold, roughly triples saves, nearly doubles shares — and moves
reach by nothing measurable. Every one of those engagement effects survives creator normalisation, so
they are properties of the mechanic rather than of the accounts that use it.

**The consequence for the radar is a selection defect, not an editorial one.** `cards.py` ranks candidate
references on `resh_1k` and `save_1k` — exactly the two rates the gate inflates. With 59 % of the
analysed corpus gated, the radar is currently part-ranking DM funnels rather than ideas. The fix is
mechanical: **record `cta_type` on every reference and compare a candidate's share and save rates only
against other reels carrying the same `cta_type`.** The reference pool in `06-creators-and-references.md`
makes the scale of the distortion visible — **33 of its 40 rows are gated**, and the seven ungated rows
(`DNA7-d3o5sQ`, `Dc_TX1CttIc`, `DbVKVz0y8xo`, `DTCOU9DkRTG`, `DX9kWTYzssE`, `DYSKnz3TxPZ`,
`DZ-wujrTJ0u`) are the only ones whose hi-intent rates can be read at face value.

The second consequence is liberating. RULES.md §1.2 already bans the gate from M2 scripts on positioning
grounds; this measurement says **the ban is free**. Nothing in reach is forfeited. What is forfeited is
the inflated share and save rate — which means M2's own published numbers will be lower than the
references' and should not be compared against them.

## Position and length are settled

The CTA starts at a median **90 % of spoken length** (p25 0.84, p75 0.94). **202 of 216 sit in the final
quarter**; exactly **three** of 216 place it before halfway. Median length **4.95 s / 21 words**, and the
strong `robust_z` quartile runs slightly longer (5.7 s against 4.4 s, p=0.075 — not significant). There
is no positional experiment left to run: the niche has converged, and converged sensibly.

Stacking asks is the one thing the data visibly punishes.
[Da3uSkrNjli](https://www.instagram.com/reel/Da3uSkrNjli/) spends its last twenty seconds on four
separate requests — **"So if you're interested in selling automations like this local dentist near you,
then comment the word automation in the comment section below. But if you really want to…"**
(cta beat, 68.4–88.5 s) — and lands at `view_lift` **−0.05**, below its own author's median. At the
other end, [DZPYR_0y4VV](https://www.instagram.com/reel/DZPYR_0y4VV/) is 27 seconds carrying **one**
claim and **one** ask, with the CTA occupying over a third of the runtime, at 139.3× its author's median.
One ask, clearly placed, is the whole of the instruction.

## The lexical signature

**"Comment" is the single most frequent imperative in the corpus — 41 occurrences, three times the next
verb** (follow 14, let 13, go 12, look 9, think 9, click 7). Sentences in this niche end on a destination
or an availability claim rather than a conclusion: "right now" 13, "for free" 11, "for you" 11,
"on github" 10, "the link" 5. Where the gate keyword itself is recoverable from the CTA beat text, the
most common is a generic placeholder ("comment *the* word below" patterns, 14 occurrences), then `AI` 7,
`agent` 4, `section` 3, and single letters such as `W`. That last detail matters: a one-letter gate is
not a topic signal, it is a funnel trigger, and it tells you the comment was never about the content.

Two lexical findings that are about the closing line rather than the gate survive creator normalisation
and belong here: **CTA verbs** → save_rate rho **+0.241** (cn +0.155) and **direct address per 100
words** → save_rate **+0.174** (cn +0.127), both RELIABLE. Concrete asks written in the second person are
saved; the emotion around them is not what does it.

**Visual reading.** `is_cta_visual` is set on only **3 % of the 2 645 labelled frames** — the CTA is
almost never given its own visual. fa-v1 records `cta_visual: none` on the strongest template in the
pool, [DNA7-d3o5sQ](https://www.instagram.com/reel/DNA7-d3o5sQ/), whose ungated close is simply the
artefact confirming the booking aloud: **"Perfect. Ed Hill, your appointment has been successfully booked
for tomorrow at 4 p.m."** (closing, 62.8–67.9 s). The most effective closing line in the corpus is the
machine finishing its job.

## Strategic implication

**(1) Keep the gate banned** — confirmed free by measurement, not only by policy. **(2) Hold `cta_type`
constant in reference selection**, or record it on the card so a gated reel's rates are never compared
with an ungated one's. **(3) Close in the last 10 % of the script, about 5 seconds and 20 words, with
exactly one ask.** **(4) Put the ask on the face, not on the screen** (chapter 22's A>SCREEN>A pattern),
and make the final visual the artefact having finished. **(5) Do not A/B the CTA's position** — the niche
converged at 90 % of spoken length and there is nothing left to learn there.

**Confidence: RELIABLE** for the gate's engagement effects and its reach null (n=214–256, 71 and 30
creators, p from 4e-23 to 0.00015, all surviving creator normalisation; the reach null at p=0.58 and 0.63).
**RELIABLE** for CTA position and length as a description (n=216). **PROBABLE** for `question_to_audience`
being the highest-lift cell (n=11, 9 creators). **INSUFFICIENT** for `dm`, `next_video`, `free_resource`
and `save_share` (n=2–3 each), reported with their `suppressed_reason` rather than deleted.
