# 11. Creator Analysis

**Denominators.** 132 creators carry a `creator_stats` row at snapshot 3 (2026-09-10). 102 of them
contribute at least one reel to the analysis-ready corpus of 268, at a median of **2 reels each**
(p75 4, max 6). Creator-level statements below use n=132; reel-level statements inside the analysed
set use n=268 and are strong-vs-strong by construction [I-01]. The `followers` table is empty, so
**creator growth cannot be answered at all** — no statement about audience gain appears anywhere in
this report.

## The landscape

| | value |
|---|---|
| creators with a `creator_stats` row | 132 |
| `CONSISTENT` (CV < 1 **and** n ≥ 8) | **17** (13 %) |
| `HIGH_VARIANCE` | **115** (87 %) |
| `SMALL_SAMPLE` (n < 5) | 0 |
| median videos in baseline | 26 |
| median creator median play | **14 936** (p10 3 099, p90 71 198) |
| median consistency score, 1/(1+CV) | **0.352** |
| median MAD-to-median ratio | 0.47 |
| Spearman(median_play, mad_play) | **+0.967** |
| max CV | 4.77 (`adamstewartmarketing`) |
| posts above 5× their creator's rolling median | 269 of 3 078 (**8.7 %**), 101 creators |

The table describes a lottery, not a craft. Eighty-seven per cent of tracked creators cannot repeat
their own results, the median account's typical reel lands within roughly half a median of its own
median, and dispersion rises almost perfectly with level (+0.967) — which is exactly why both
`score.py` and `engine/stats.py` compute the z on `ln(1 + play)` rather than on raw views. The
practical consequence is that **a creator's median is the only fair yardstick for their own reels and
is useless for comparing one creator with another**: a 2× at a 483 982-play median and a 2× at a
459-play median are not the same event.

![Creator median views, top 30 — the roster spans more than an order of magnitude](reports/charts/creator_median_views.png)

The top 30 accounts run from `askcatgpt` at a 483 982-play median down to `codewithnishant` at 32 292,
against a roster-wide median of 14 936. Only 3 of those 30 carry the CONSISTENT label; the other 27 are
HIGH_VARIANCE, so most of the bars represent a median that any single post can swing. Reading this
chart as a ranking of "who is good" would be a mistake — it is a ranking of who has an audience, and
the two are separate questions answered by the next figure.

![Creator median vs MAD — dispersion rises with level](reports/charts/creator_dispersion.png)

Every creator sits close to the diagonal: bigger accounts are not steadier accounts, they are bigger
and equally unsteady. The 17 CONSISTENT creators cluster below the line and the 115 HIGH_VARIANCE
creators above it. Because MAD and median are both plotted on the raw play scale, a creator with one
enormous outlier can still show a low MAD if the rest of their output is flat — a second reason the
log-space z is the number that travels into every downstream table.

## The seventeen consistent creators

| username | n | median play | CV | posts/week | share/1k | save/1k |
|---|---:|---:|---:|---:|---:|---:|
| angus.sewell | 12 | 89 439 | 0.98 | 4.39 | 9.6 | 23.1 |
| harshsharma_ai | 12 | 44 377 | 0.96 | 2.59 | 13.9 | — |
| chris.raroque | 12 | 36 820 | 0.80 | 5.60 | 6.8 | 23.3 |
| decodingai.vs | 29 | 30 932 | 0.73 | 4.09 | 12.6 | 24.5 |
| ajsahni.ai | 12 | 28 067 | 0.95 | 1.64 | 4.4 | — |
| justyn.ai | 30 | 19 173 | 0.91 | 0.72 | 5.8 | 17.9 |
| divyannshisharma | 27 | 18 948 | 0.78 | 1.47 | **22.0** | **36.1** |
| damini.knows | 14 | 12 678 | 0.64 | 3.06 | **19.9** | **31.4** |
| seb.ai | 42 | 8 344 | 0.74 | 14.55 | 13.5 | 32.0 |
| umangratani | 23 | 7 825 | 0.51 | 0.13 | 1.3 | 0.9 |
| nicholas.puru | 32 | 4 988 | 0.72 | 5.14 | 2.9 | 11.6 |
| omarmeski | 24 | 2 979 | 0.37 | 0.81 | 4.0 | 8.6 |
| seymourofdevin | 12 | 2 842 | 0.69 | 7.71 | 4.8 | 20.7 |
| brycenwood.ai | 24 | 2 572 | 0.42 | 1.39 | 5.3 | 7.1 |
| pritam.nagrale | 29 | 1 613 | 0.61 | 3.49 | 2.3 | 6.2 |
| automationatlas.co | 48 | 459 | 0.90 | 32.13 | 0.0 | 0.4 |
| hcmetellus | 25 | 410 | 0.68 | 0.47 | 0.0 | 0.0 |

Consistency and distribution are separate properties, and only the top seven rows have both.
`automationatlas.co` posts 32 times a week to a 459-play median and `hcmetellus` is steady at 410 — a
steady nothing is still nothing. The two rows worth copying are `divyannshisharma` and `damini.knows`:
consistent **and** above the analysed-set medians on both hi-intent rates (corpus medians 0.0152 share,
0.0278 save, n=268 and 245). Cadence itself explains nothing — the roster spans 32.1 posts a week
(`automationatlas.co`) to 0.13 (`umangratani`) with no relation to performance, and `posts_per_week` is
a lower bound throughout because the corpus holds only what was visible on a profile page at collection
time.

## The measurement trap this creates

The 28 analysed reels from CONSISTENT creators carry a median `robust_z` of **0.60** and `view_lift`
**0.65**. The 240 from HIGH_VARIANCE creators carry **1.37** and **2.38**. Their scripts are the same
object: median hook 6.7 s on both sides, spoken length 53.8 s against 53.5 s, 3.4 against 3.5 words per
second. The gap is arithmetic, not editorial — both metrics divide by the creator's own spread, so a
steady creator produces small lifts from genuinely good reels and a lottery account produces enormous
lifts from ordinary ones [I-23]. Two real differences in shape survive: consistent creators spend less
on proof (11.2 s vs 18.6 s) and longer on the closing line (6.3 s vs 4.8 s).

**Transcript reading.** `damini.knows` is the corpus's cleanest example of what consistency looks like
in a script. Her [DcoE5ZsK4I7](https://www.instagram.com/reel/DcoE5ZsK4I7/) opens "With one prompt, you
will create some crazy animated websites. First, understand the whole process." (hook, 0.0–4.9 s) and
then does exactly that in 49 seconds. The reel is 1.4× her own median — a number that would be discarded
by any lift-ranked filter — while carrying 36.1 shares and 62.4 saves per 1 000, both far above the
corpus median. This is what a reliable creator's win looks like: unremarkable reach, exceptional intent.

**Visual reading.** The same reel runs `A_ROLL_MEDIUM > UI_DEMO > SPLIT_SCREEN > UI_DEMO` — host,
then the generated site, then the extension, then the site again. fa-v1 records the proof visuals as
two finished website mockups and the `Woblo` browser extension itself. Nothing is asserted that is not
shown, which is the visual equivalent of a low variance.

## Strategic implication

Three rules follow for M2. First, **every reference must carry its creator's `reliability`, CV and
baseline `n` on the card**, because a 300× from a 1 374-view median and a 1.4× from a steady
12 677-view median are not comparable claims. Second, **prefer references from CONSISTENT creators or
from creators with more than one entry in the pool** — the reference pool in
`06-creators-and-references.md` contains exactly one CONSISTENT row out of 40, which is a property of
the selection rule, not of the niche. Third, when M2's own account becomes consistent, **expect its
multipliers to shrink**, and do not read that shrinkage as decline; it is the same arithmetic operating
on M2.

**Confidence: RELIABLE** for the landscape description (n=132, complete roster, direct measurement).
**PROBABLE** for "who is worth studying", which rests on eight rows and on a share/save comparison that
does not hold `cta_type` constant. **INSUFFICIENT** for anything about follower growth: the table is
empty and the question cannot be asked of this dataset.
