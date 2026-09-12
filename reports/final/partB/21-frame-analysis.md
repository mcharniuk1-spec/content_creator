# 21. Frame Analysis

**Denominators and the limitation that governs them.** The legacy corpus carries **9 fixed frames per
reel** — sampled at 0.4 / 1.2 / 2.4 / 4.0 s and then evenly spaced. **295** codes have an fa-v1 read,
producing **2 645 labelled frames**; 266 of those 295 also have a transcript and appear in the
performance joins; 243 of those have a save rate. Every roll share below is a fraction of **labelled
samples, not of screen time** (`features_json.visual.share_basis` says so on every row), so a screen shown
for three seconds between two samples is invisible to this entire chapter. A "scene" is a run of
consecutive samples with the same `frame_type` — `boundary_reason = 'sampled'`,
`boundary_confidence = 'low'` — and can read as 4.5 s long when the real shot was 0.6 s.

## What a reel in this niche looks like

| frame_type | frames | % of 2 645 |
|---|---:|---:|
| SPLIT_SCREEN | **591** | **22.3** |
| A_ROLL_MEDIUM | 363 | 13.7 |
| A_ROLL_CLOSE_UP | 353 | 13.3 |
| SCREENSHOT | 294 | 11.1 |
| SCREEN_RECORDING | 258 | 9.8 |
| UI_DEMO | 127 | 4.8 |
| OVERLAY | 123 | 4.7 |
| B_ROLL_CONTEXT | 113 | 4.3 |
| A_ROLL_WIDE | 78 | 2.9 |
| B_ROLL_PROCESS | 72 | 2.7 |
| DATA_VISUAL | 64 | 2.4 |
| MOTION_GRAPHIC | 54 | 2.0 |
| A_ROLL_TALKING_HEAD | 47 | 1.8 |
| TEXT_ONLY | 46 | 1.7 |
| everything else | 55 | 2.1 |

Rolled up: **A-roll 33 %, SPLIT 26 %, SCREEN 26 %, B-roll 7 %, other 5 %, text 2 %.** Per frame,
**text_overlay 86 %**, **face_present 65 %**, **ui_present 58 %**, **is_proof_visual 41 %**,
**is_cta_visual 3 %**. Framing: medium 1 043 · screen 728 · close-up 440 · wide 321. Caption placement:
bottom 1 099 · top 571 · middle 568 · none 403. Visual density: medium 1 148 · high 857 · low 640.
Median per-reel shares in the analysed set: `a_roll_share` 0.333, `screen_share` 0.222, `split_share`
0.000, `b_roll_share` 0.000, `text_overlay_density` **1.000**.

Three facts in that table are worth isolating. **Captions are table stakes, not a lever**: the median
`text_overlay_density` is 1.0 in both the strong and the weak `robust_z` quartile (p=0.418) and the pooled
save-rate correlation (+0.180, p=0.005) does not survive creator normalisation (cn +0.080). **Forty-one
per cent of frames are flagged as proof visuals** while only 50 % of reels carry a proof *beat* — proof in
this niche is visual more often than it is spoken. And **the CTA almost never has a visual** (3 % of
frames), which is consistent with chapter 18's finding that the closing line is delivered on the face.

## Visual complexity is not a lever

![Scene count vs performance, n=282](reports/charts/scenes_vs_performance.png)

Median `scenes_n` is **3** (p25 2, p75 5). Across the 282 codes with a scene count the Spearman
correlation against `robust_z` is **+0.085 (p=0.17)** and against `view_lift` **+0.052 (p=0.40)**; the
strong quartile's median is 4 scenes against 3 (p=0.110). Grouping instead by the number of **distinct
coarse visual states** per reel gives the same answer across the whole observable range:

| coarse states per reel | reels | median robust_z |
|---:|---:|---:|
| 1 | 68 | 1.25 |
| 2 | 40 | 1.21 |
| 3 | 52 | 1.14 |
| 4 | 41 | **1.63** |
| 5 | 36 | 1.39 |
| 6 | 18 | 1.35 |
| 7 | 9 | — |
| 8 | 2 | — |

From one state to six the median `robust_z` moves between 1.14 and 1.63 with no trend. **Visual complexity
is not a lever**, and the measurement floor reinforces rather than undermines the null: `scenes_n` is a
lower bound on real cuts, so if anything the real range of complexity is wider than plotted and still
shows nothing.

## The literal vocabulary fragments

![Visual sequence frequency, top 10 — 75 of 295 reels](reports/charts/visual_sequence_top10.png)

**295 reels produce 206 distinct `visual_sequence` strings**, so the median sequence occurs exactly once,
and the ten most frequent cover only **75 of 295 reels (25 %)**. That is why every visual finding in this
report is stated on a **coarse four-way collapse** (A = any A-roll · SCR = screen recording / screenshot /
UI demo / data visual · SPL = split screen · B = B-roll · TXT = text, meme, motion graphic, overlay),
which reduces 295 reels to 121 strings of which 15 cover 53 % of the corpus. Two reels edited very
differently between samples can still produce the same string.

Within that caveat, the chart's two endpoints are the chapter's real content. **`SPLIT_SCREEN` held
throughout is the single most common arrangement (n=27, 18 creators) and among the weakest** (median
`view_lift` **0.94** against a corpus median of 2.03). **`B_ROLL_PROCESS` held throughout is the
strongest (n=6, 4 creators, median `view_lift` 30.90, `robust_z` 4.13, median play 554 907)**, and the
strongest multi-state form is `A_ROLL_CLOSE_UP > SCREENSHOT > A_ROLL_CLOSE_UP` (n=3, 3 creators,
`view_lift` 52.04, `robust_z` 5.0). Both extreme cells are INSUFFICIENT on their own and are dominated by
large outliers; they are reported because they point the same way as the much better-powered screen
findings in chapters 17 and 22, not as evidence in themselves.

## What the frames see that the transcript cannot

**Transcript reading, with its visual counterpart.** [DZgBxjnBzMe](https://www.instagram.com/reel/DZgBxjnBzMe/)
speaks **14 words in 27 seconds** — hook "Welcome back." (5.3–7.3 s), then "Unlock my phone. Open Geohot
Star in my phone. Call my sister." (7.3–23.0 s) — and reaches 207× its author's median. Its ta-v1
confidence is INSUFFICIENT, so it contributes nothing to any script finding. The frame read is where the
reel actually lives: a held `B_ROLL_PROCESS`, a camera filming a laptop running a Jarvis Python script,
a "J.A.R.V.I.S V6.5" HUD appearing, and a phone changing state beside the laptop, under one white title
pinned for the whole runtime — **seven of eight observed sample transitions are `same_shot`**. The
evidence is continuous, so there is no cut where a trick could hide.

The mirror case is [DcxV37-CJOC](https://www.instagram.com/reel/DcxV37-CJOC/) (559 515 plays, 72.2 saves
per 1 000) whose transcript is four words and whose frame read is complete: a host holding a printed card
with a pink dot pattern, one held `A_ROLL_MEDIUM`, **no proof visual at all**. Two reels invisible to the
transcript pipeline, both legible to the frame pipeline, and they reach the same conclusion from opposite
directions: the frame read is not a decoration on the script read, it is an independent measurement.

## Strategic implication

**(1) Fix one caption system and never revisit it** — bold white on a solid box, bottom-anchored for
speech, plus a persistent top banner carrying the promise. It is universal in the niche (86 % of frames)
and has no measured performance effect, which means its absence is a penalty and its presence is not a
gain. **(2) Do not set a scene count.** Max's fixed 60-second / 7-scene template is wrong to be fixed at
all: the observable range is 1 to 8 coarse states with no performance difference, so the one thing that
should vary with the topic is being held constant. **(3) Let 41 % of frames be proof.** That is the niche
baseline for evidence on screen, and M2's own footage — its own build, its own sheet, its own inbox —
should at minimum match it. **(4) Never inherit a reference's layout without checking it** (chapters 22
and 23).

**Confidence: RELIABLE** as a description of the visual baseline (2 645 frames, direct labelling) and for
the caption-density null. **RELIABLE** for the scene-count and visual-complexity nulls (n=282 and 266).
**INSUFFICIENT** for every literal `visual_sequence` cell except the top few — 9 of 15 reported cells fall
below the size floor, and the two extreme cells are n=6 and n=3. All shares are fractions of nine samples,
not of screen time; no number here may be quoted as a screen-time percentage.
