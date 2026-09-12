# 19. Script Part Lengths

**Denominators.** Part lengths run on **264** codes — those whose script block was built from ta-v1 beats
(`features_json.script.part_source == 'beats'`). The four analysis-ready codes without a beat-derived
block are excluded, and the clock-based timing fallback never writes these columns. Each row reports the
median **only over the codes where that part exists**, so the n differs by row by design and the shares
do not sum to 1.0. `total_s` is **spoken** length, always shorter than `reels.dur` for a reel with a
silent opening or an outro card; the two are never swapped. Strong-versus-weak splits are quartiles of
`robust_z` *inside* the analysed tier, so the weak side still beats its own authors' medians [I-01].

## Typical lengths and shares

| part | n | % of 264 | median s | mean s | median share of speech | median words |
|---|---:|---:|---:|---:|---:|---:|
| hook | 260 | 98 % | 6.7 | 7.50 | 13.2 % | 21.5 |
| setup | 34 | 13 % | 7.8 | 9.41 | 14.0 % | 29 |
| problem | 64 | 24 % | 8.95 | 12.04 | 16.4 % | 32 |
| explanation | 208 | 79 % | **18.6** | 23.54 | **38.3 %** | 64 |
| solution | 70 | 27 % | 10.4 | 12.95 | 20.1 % | 36 |
| proof | 133 | 50 % | 17.0 | 23.19 | 30.5 % | 57 |
| payoff | 150 | 57 % | 8.2 | 10.24 | 17.0 % | 26.5 |
| cta | 216 | 82 % | 4.95 | 6.27 | 9.7 % | 21 |

Whole-reel reference values: median spoken length **53.6 s**, **182 words**, **3.52 words per second**;
median video duration 54.2 s in the analysed set against 47.6 s across all 3 211 ingested reels.
`unbucketed_s` (objection + rehook + other) is non-zero in only **35 of 264** reels, so the eight columns
account for essentially all spoken time.

The table's shape is the finding. **Two parts are near-universal** (hook 98 %, CTA 82 %) and
**explanation is the load-bearing middle** — present in 79 % of reels and taking 38 % of the speech, more
than twice any other part's share. **Four parts are minority moves**: solution 27 %, problem 24 %,
setup 13 %, and proof only 50 %. Half of this niche never proves anything and three quarters never state
a problem. For M2 that is the structural gap: the mandatory editorial filter requires friction and an AI
boundary, which means M2's script will spend seconds the niche's does not, and those seconds have to come
out of the mechanism block rather than being added to the runtime.

## Distributions, not just medians

| quantity | p25 | median | p75 | notes |
|---|---:|---:|---:|---|
| hook_s | 4.6 | 6.7 | 9.6 | 6 % under 3 s, 31 % under 5 s, 19 % over 10 s |
| total_s | 39.1 | 53.6 | 69.7 | min 0.8 s (a five-word ASR row), max 259.0 s |
| total_words | 128.8 | 182 | 237 | max 1 034 |
| wps | 3.07 | 3.52 | 3.83 | min 0.65, max 6.25 |
| time to first proof beat | 11.1 | **22.0** | 32.0 | n=133 |
| time to solution beat | 7.7 | 19.7 | 29.0 | n=70 |
| CTA start, share of speech | 0.84 | **0.90** | 0.94 | 94 % in the final quarter; 3 of 216 before halfway |
| problem start, share of speech | 0.15 | **0.21** | 0.39 | 56 % inside the first quarter |

Three of these are production instructions in disguise. The first proof beat arrives at a median
**22.0 seconds** — that is where this audience expects evidence, and a reel that proves nothing by then
has spent its credibility window. The problem, where it exists, lands at 21 % of spoken length. The CTA
lands at 90 %. Those three timings are the only placement facts this dataset supports, and all three are
descriptions of convergence rather than measured advantages.

## Strong versus weak: reallocation, not extension

![Script part shares, strong vs weak robust_z quartile (n=66 per side)](reports/charts/script_parts_strong_vs_weak.png)

| part | n S | median s S | share S | n W | median s W | share W | Δ s | Mann-Whitney p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| hook | 66 | 7.6 | 13.8 % | 64 | 7.0 | 12.4 % | +0.6 | 0.162 |
| setup | 7 | 11.0 | 13.4 % | 11 | 4.7 | 9.1 % | +6.3 | 0.057 |
| problem | 18 | 8.6 | 18.4 % | 16 | 9.15 | 14.5 % | −0.55 | 0.809 |
| explanation | 54 | 17.3 | **34.1 %** | 53 | 19.5 | **41.9 %** | −2.2 | 0.236 |
| solution | 18 | **12.25** | 21.1 % | 19 | **8.4** | 15.3 % | **+3.85** | **0.0065** |
| proof | 32 | 19.25 | 32.9 % | 34 | 23.9 | 37.1 % | −4.65 | 0.551 |
| payoff | 37 | 10.3 | 18.6 % | 38 | 7.95 | 16.8 % | +2.35 | 0.123 |
| cta | 56 | 5.7 | 10.3 % | 51 | 4.4 | 8.4 % | +1.3 | 0.075 |

Read the segments individually, never as a stacked total: each share is a median taken independently per
role over a different n, so the bars need not sum to 1.0. **Total spoken length is identical** between
the quartiles — 56.9 s against 58.0 s, p=0.98 — and so are word count (198 vs 179, p=0.33) and pace
(3.53 vs 3.45 wps, p=0.44). What changes is the allocation: the strong quartile takes 2.2 seconds and
7.8 points of share out of the mechanism and puts them into the solution statement (+3.85 s), the payoff
(+2.35 s) and the closing line (+1.3 s). **`solution_s` is the only part clearing p<0.01 in the entire
115-feature test.** Proof length moves the *other* way (p=0.55) and the problem statement does not move
at all (p=0.81) — what matters about proof in this corpus is whether it is on screen, not how long it is
spoken [I-16, I-18].

The plainest reading: **a longer "how" is usually an unclear "what".** The weak quartile gives 41.9 % of
its speech to the mechanism; the strong one gives 34.1 % and spends the difference saying what the thing
is and what it changes.

## By creator reliability, topic and archetype

Joining the 268 analysed reels to `creator_stats.reliability`: 28 reels from 15 CONSISTENT creators, 240
from 87 HIGH_VARIANCE creators. **Script shape is identical** — hook 6.7 s both sides, total 53.8 s
against 53.5 s, 3.4 against 3.5 wps — while median `robust_z` is 0.60 against 1.37 and `view_lift` 0.65
against 2.38. Two real differences in shape: consistent creators spend **less on proof (11.2 s vs
18.6 s)** and **more on the closing line (6.3 s vs 4.8 s)**.

By narrative archetype, **`demo_walkthrough` is the largest (n=62, 42 creators), the highest-lift
(view_lift 3.70, robust_z 1.71) and the most evenly balanced** — 7.8 s hook / 19.9 s explanation (38 %) /
19.3 s proof (34 %) / 8.0 s payoff / 5.0 s CTA. Listicles run the shortest hooks (4.6 s) and by far the
largest proof share (72 %, because every list item is tagged as an example). Myth-bust carries the longest
hooks (8.5 s) and the second-highest `robust_z` (1.93) on the smallest explanation share (28 %). By topic,
news reels carry the longest proof (31.3 s) and longest hooks (8.1 s); lead-generation reels the shortest
hooks (5.2 s); agency-business reels by far the longest problem statements (20.9 s, but on n=4 —
INSUFFICIENT, and the only topic where problem is the biggest part). Every topic cell is PROBABLE or
INSUFFICIENT.

**Transcript reading.** The reallocation is audible. [DYC-x8DogOI](https://www.instagram.com/reel/DYC-x8DogOI/)
(399.4×, the corpus's highest lift) gives 11.8 s to a hook that already contains the result
("I just built a website that looks like it costs $10,000 with literally one line of code and honestly
the whole thing took Claude about two minutes"), **17 s** to the mechanism, **10 s** to a payoff that
restates what it means ("But here's the crazy part. We wrapped all four into one single repo"), and
3.6 s to one ask. Mechanism is a third of the reel. Compare
[DaDn5L-xKWi](https://www.instagram.com/reel/DaDn5L-xKWi/), five identically shaped ten-second tricks
with no solution statement at all — five open loops, no reallocation, and a reel that flattens.

**Visual reading.** DYC-x8DogOI's frame read is `SCREENSHOT > A_ROLL_CLOSE_UP > SCREENSHOT`: the finished
websites carry the mechanism, the face carries the payoff, and eight of eight observed sample transitions
are hard cuts. The seconds taken out of the spoken mechanism are visible on screen instead.

## Strategic implication

Budget the M2 script as: hook 6–8 s · friction 8–10 s in the first quarter · mechanism capped at **one
third** · solution statement **~12 s** · screen proof arriving by **~22 s** · payoff ~10 s naming what
changes on Monday · closing line ~5 s and 20 words at 90 % of the script. The friction block is M2's
addition to the niche's shape and must be paid for out of the mechanism, not bolted onto the runtime.
Do not set a words-per-second target; set a words-per-idea target (chapter 26).

**Confidence: RELIABLE** for the part-length distributions as a description (n=264, direct measurement of
1 527 beats). **PROBABLE** for the reallocation finding — `solution_s` clears p<0.01 but on 18 against 19
reels, and the explanation and payoff differences do not reach p<0.05. **INSUFFICIENT** for every
topic-level part table (largest cell n=27, most under 10) and for `setup_s` (7 against 11 reels). No
causal claim: a longer solution statement is associated with a higher creator-relative score inside a
pre-selected sample.
