# 12. Video Analysis

**Denominators.** This chapter works at the level of the individual reel. Metric-only statements use
**N_ingested = 3 211** (every unique code with a `reels` row; 3 209 have computable rates after the
100-play denominator guard). Statements that need a script or a frame read use **n=268** (analysis-ready)
and are strong-vs-strong [I-01]. 56 codes carry a `DUPLICATE_VIDEO` flag and 1 676 a `STALE_METRICS`
flag; 3 006 of 3 211 codes carry at least one flag of some kind, which is a statement about pipeline
hygiene, not about content quality.

## How a reel performs relative to its own author

| | value |
|---|---|
| median `view_lift` across 3 211 | **0.00** — the corpus is centred exactly on the author's own median |
| reels below their author's median | 49.4 % |
| reels at or above 2× their author's median | 25.1 % |
| p95 `view_lift` | **+20.96** |
| maximum | **+2 381** (`Cq3Lkw1JaBv`, loganwelbaum, 7 550 238 plays on a 3 170 median) |
| `outlier_status` HIGH (`robust_z` ≥ +2) | **375** |
| `outlier_status` LOW (≤ −2) | 49 |
| NORMAL | 2 787 |
| rows with `robust_z_floored = 1` | **0** — no magnitude in this wave is an upper bound for that reason |

![Video performance ratio distribution — view_lift across 3 211 reels, log count axis](reports/charts/video_view_lift_distribution.png)

The log y-axis is not cosmetic. The bulk of the mass sits between −1 and +2 and everything interesting
about this niche lives in a tail that a linear axis would erase. Two readings follow. First, a "winner"
in this corpus is a rare event: 375 of 3 211 reels (11.7 %) reach `robust_z` ≥ 2, and 150 (4.7 %) exceed
ten times their creator's rolling median. Second, the tail is so long that the top of it is
uninterpretable on its own — a +2 381 is a statement about a 3 170-view baseline, and RULES.md §6's label
for that case ("резонировало у своих" — resonated with its own audience) is the honest one. Every
multiplier in this report should be read next to its denominator, never alone.

## Duration is not a lever

![Video duration vs performance across all 3 211 ingested reels](reports/charts/duration_vs_performance.png)

Across the full ingested corpus the Spearman correlation between duration and `robust_z` is **−0.069**
(p = 9.5e-05 — significant only because n is 3 211) and against `view_lift` **−0.0004**. The band
comparison is flat: under 20 s median `robust_z` **0.25**, 20–45 s **0.00**, 45–70 s **−0.01**,
70–90 s **−0.19**, over 90 s **+0.05**. The 375 HIGH outliers have a median duration of **46.8 s**
against **47.8 s** for the other 2 836, and **14 %** of them are under 20 s against **12 %** of the rest.

Two numbers previously published inside M2 do not reproduce here and are corrected in chapter 33:
PRODUCTION.md's "the winners' median is 55 seconds against 47 for the rest" and "under twenty seconds
is 5 % of winners and 13 % of the rest". Both came from a 100-reel top slice of an earlier 2 352-reel
export; on 3 211 creator-normalised reels they become 46.8 s vs 47.8 s and 14 % vs 12 %. The direction of
the second claim is reversed, not merely attenuated [I-02].

## Script length is not a lever either

![Script length vs performance, 268 analysed reels](reports/charts/script_length_vs_performance.png)

Across the 268 codes with both values, total spoken word count correlates with `robust_z` at **+0.048**
(p = 0.44), and the strong `robust_z` quartile carries a median 198 words against 179 for the weak
quartile (Mann-Whitney p = 0.33). The cloud is as wide at 100 words as at 400. Median spoken length in
the analysed set is **53.6 s / 182 words / 3.52 words per second**; median video duration is 54.2 s
against 47.6 s across all 3 211, which is a selection effect of the analysed tier, not a finding.

**Transcript reading — both extremes work.** The corpus's shortest script is
[DZgBxjnBzMe](https://www.instagram.com/reel/DZgBxjnBzMe/): **14 spoken words in 27 seconds**, at
**207×** its author's median and 1 570 719 plays. Its entire hook beat is "Welcome back." (5.3–7.3 s)
and its entire proof beat is "Unlock my phone. Open Geohot Star in my phone. Call my sister."
(7.3–23.0 s). Its opposite is [DLzPQzGNEmY](https://www.instagram.com/reel/DLzPQzGNEmY/) — 340 words in
100 seconds, 72.5× on a 22 121 median. A rule expressed in words or seconds would have to condemn one of
them.

**Visual reading.** The two reels are also visual opposites and both are legible. DZgBxjnBzMe holds a
single `B_ROLL_PROCESS` state across all nine samples — fa-v1 records a camera filming a laptop running
a Jarvis Python script, a "J.A.R.V.I.S V6.5" HUD, and a phone changing state beside it, under one
white title pinned for the whole reel. DLzPQzGNEmY is a held `SCREEN_RECORDING`. What both share is not
a length or a cut rate: it is that **the thing being claimed is visible while the claim is made**.

## What this chapter licenses

Nothing about form. Of the video-level properties measurable here — duration, spoken length, words per
second, cut rate, scene count, caption density — not one separates the top from the bottom `robust_z`
quartile at p<0.01, and the negative result was obtained inside a sample pre-selected for strength,
which should have made a difference *easier* to see [I-22]. The video-level variable that does carry
signal is not a shape at all: it is how many distinct named things the script contains
(`lex_entities_distinct` → `view_lift` +0.161 pooled, **+0.198 creator-normalised**, the only reach
correlation in 460 pairs that survives normalisation).

## Strategic implication

Keep M2's 50–70 second band as a **shooting convenience** — it fits one filming day and one take — and
stop citing it as an evidence-backed reach lever. Never cut a good idea short to hit the band and never
pad a thin one to reach it. Judge an individual M2 reel against M2's own accumulated median, carry the
baseline `n` with every multiplier, and expect the first six months of M2 numbers to be uninterpretable
in isolation: with fewer than 5 baseline videos the engine itself returns `SMALL_SAMPLE` rather than a
score.

**Confidence: RELIABLE** for the duration null and the lift distribution (n=3 211, complete corpus,
direct measurement). **RELIABLE** for the script-length null within the analysed tier (n=268).
**PROBABLE** for the two-extremes reading, which rests on two named reels chosen because they are
extremes. No causal claim is licensed by any number above.
