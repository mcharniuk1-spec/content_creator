# 03 — Visual patterns

Spec §80. Sources: `data/analysis/frames/*.json` (295 fa-v1 reads, 2 645 labelled frames),
`reports/data/visual_patterns.json`, `reports/data/analysis_ready.csv`, `reports/data/associations.json`.

## The limitation that shapes every number here

The legacy corpus carries **9 fixed frames per reel** — sampled at 0.4 / 1.2 / 2.4 / 4.0 s and then
evenly spaced. Everything below is an interpolation between nine points.

* `a_roll_share`, `b_roll_share`, `split_share`, `screen_share` are fractions of **labelled samples**,
  not of screen time. A screen shown for three seconds between two samples is invisible.
* A "scene" is a run of consecutive samples with the same `frame_type`. It can read as 4.5 s long when
  the real shot was 0.6 s. `boundary_reason = 'sampled'`, `boundary_confidence = 'low'`.
* `visual_sequence` is the frame types in order with consecutive duplicates collapsed. 295 reels produce
  **206 distinct sequences** — the median sequence occurs once. Every pattern below is therefore stated
  on a **coarse four-way vocabulary** (A = any A-roll, SCR = screen recording / screenshot / UI demo /
  data visual, SPL = split screen, B = B-roll, TXT = text, meme, motion graphic, overlay), which reduces
  295 reels to 121 distinct strings of which 15 cover 53 % of the corpus.
* `transitions_observed` counts only changes fa-v1 actually saw between two labelled samples: 663
  `hard_cut_or_more` and 15 `unknown` across the corpus. Nothing else is claimed.
* The analysis-ready corpus is the top of `score.py`'s ranking (median robust_z +1.26), so every
  performance figure compares strong with strong.

**Denominators.** 295 codes have an fa-v1 read; 266 of those also have a transcript analysis and appear
in the performance joins below; 243 of those have a save rate. Frame-level percentages divide by 2 645.

---

## Baseline: what a reel in this niche looks like

Frame types across all 2 645 labelled frames:

| frame_type | frames | % |
|---|---:|---:|
| SPLIT_SCREEN | 591 | 22.3 |
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

Rolls: A 33 %, SPLIT 26 %, SCREEN 26 %, B 7 %, OTHER 5 %, TEXT 2 %.
Per frame: `text_overlay` 86 %, `face_present` 65 %, `ui_present` 58 %, `is_proof_visual` 41 %,
`is_cta_visual` 3 %. Framing: medium 1 043, screen 728, close-up 440, wide 321. Caption placement:
bottom 1 099, top 571, middle 568, none 403. Visual density: medium 1 148, high 857, low 640.

Median per-reel shares in the analysed set: a_roll 0.333, screen 0.222, split 0.000, b_roll 0.000,
text_overlay_density 1.000. Median scenes_n 3, median cuts_per_min 7.26.

Number of coarse visual states per reel: 1 state 68 reels, 2 states 40, 3 states 52, 4 states 41,
5 states 36, 6 states 18, 7 states 9, 8 states 2. Median robust_z by state count is flat
(1.25 / 1.21 / 1.14 / 1.63 / 1.39 / 1.35) — **visual complexity is not a lever**.

---

## Core pattern 1 — Talk / show / come back (`A > SCR > A`)

**Sequence.** Presenter on camera, cut to full-frame screen, cut back to presenter.
**Frequency.** 39 of 266 reels contain the run; 11 reels are exactly `A > SCR > A` with nothing else.
**Creators.** 32 creators carry the pattern; the exact three-state form appears once each in 11
different creators — `tenfoldmarc`, `buildingwithstring.com_`, `kevinfremon`, `shrug.manny`,
`manthanjethwani`, `codewithnishant` among them.
**Reels.** [DWCPx0PkQzA](https://www.instagram.com/reel/DWCPx0PkQzA/),
[DTCOU9DkRTG](https://www.instagram.com/reel/DTCOU9DkRTG/),
[DZ-wujrTJ0u](https://www.instagram.com/reel/DZ-wujrTJ0u/),
[Db9MT-axxcO](https://www.instagram.com/reel/Db9MT-axxcO/),
[DYC-x8DogOI](https://www.instagram.com/reel/DYC-x8DogOI/) (the mirror form, `SCR > A > SCR`).
**Performance.** Reels containing the run: median share_rate 0.0213 vs 0.0140 (Mann-Whitney p=0.00076),
median robust_z 2.09 vs 1.22 (p=0.10). The exact 11-reel form: median robust_z **3.01**, median
view_lift **9.86**, median play 218 733. The literal three-frame-type sequence
`A_ROLL_CLOSE_UP > SCREENSHOT > A_ROLL_CLOSE_UP` (n=3, 3 creators) sits at median robust_z 5.0 and
view_lift 52.0.
**Transcript context.** The face carries the promise and the payoff; the screen carries the mechanism.
DWCPx0PkQzA: hook to camera, two mechanism beats over the screen, then payoff back on camera —
"Normandy would take you four steps to create beautiful websites like this But I've created a github
repo where all you need to do is copy one line of code" (payoff 47.4–58.5 s) — 57.3 saves per 1 000.
**Intended effect.** Prove it, then tell the viewer what it means.
**Likely reason it works.** A screen is a claim that can be checked in the moment; a face is where the
interpretation can be delivered. Reels that end on the screen have nowhere to put the "so what", and
the "so what" is what gets forwarded.
**Where to use it.** This is the default M2 storyboard: face (promise, ~8 s) → screen (the run, ~25 s) →
face (what it changes on Monday, plus the closing line, ~10 s).
**Where not to.** Not for a reel whose whole content is the artefact operating on its own (see
pattern 4). Do not cut back to the face more than twice — the four-and-more-state group shows no
additional gain.
**Confidence.** PROBABLE. Pooled p<0.001 on share_rate only; the exact-sequence cell is n=11.

---

## Core pattern 2 — Screen-first opening

**Sequence.** Frame one is a screen recording, screenshot, UI demo or data visual; the presenter appears
later or not at all.
**Frequency.** 35 of 266 reels open on a coarse screen state (16 SCREEN_RECORDING, 8 UI_DEMO,
7 SCREENSHOT, 5 DATA_VISUAL as the literal first frame type).
**Creators.** 27.
**Reels.** [DNA7-d3o5sQ](https://www.instagram.com/reel/DNA7-d3o5sQ/),
[DUJYKENjZc5](https://www.instagram.com/reel/DUJYKENjZc5/),
[DLzPQzGNEmY](https://www.instagram.com/reel/DLzPQzGNEmY/),
[DK9pFUjPQcx](https://www.instagram.com/reel/DK9pFUjPQcx/),
[DVaBP3wDAFE](https://www.instagram.com/reel/DVaBP3wDAFE/),
[DEVIE7sN_ZI](https://www.instagram.com/reel/DEVIE7sN_ZI/).
**Performance.** Median share_rate 0.0213 vs 0.0140 (p=0.0007), median view_lift 5.25 vs 1.88,
median robust_z 2.13 vs 1.21. Pooled Spearman against share_rate +0.208 (p=0.00063); **creator-normalised
+0.285 (p=0.00025, n=161)** — the effect is *stronger* within creators than between them, which is the
strongest form of evidence available in this dataset. By literal first frame: UI_DEMO n=8, 7 creators,
median view_lift 29.2, robust_z 3.57; DATA_VISUAL n=5, view_lift 18.7, robust_z 4.44.
**Transcript context.** The words assume the screen is already there. "Here's how to make YouTube short
that post themselves step by step." (DUJYKENjZc5, hook 0.0–3.4 s) opens over the workflow canvas — no
establishing shot, no introduction.
**Intended effect.** Remove the two seconds normally spent establishing who is talking.
**Likely reason it works.** The scroll decision is made before a presenter can build credibility, so
the artefact has to make it.
**Where to use it.** Every M2 Builds and M2 Radar reel. Frame one is the artefact mid-action with the
promise already burned in as a top banner.
**Where not to.** A Teardown whose subject is a process rather than a tool has no screen to open on;
there, open on the artefact of the process (the spreadsheet, the inbox, the paper form), not on a face.
**Confidence.** RELIABLE (n=266, 102 creators, p<0.01, creator-normalised survives and strengthens).
The individual sub-type cells (UI_DEMO n=8, DATA_VISUAL n=5) are INSUFFICIENT on their own.

---

## Core pattern 3 — Held split screen

**Sequence.** `SPLIT_SCREEN` for the whole reel, or split alternating with one A-roll state.
**Frequency.** The most common arrangement in the niche: 591 of 2 645 frames (22.3 %), 73 of 266 reels
open on it, 99 contain it, 27 hold it across all nine samples with no other state.
**Creators.** 51 carry a split state; 18 carry the pure form — `alliekmiller`, `automationatlas.co`,
`badarmunir_official`, `benkimball.ai`, `brand.nat`, `davi.d_roberts`, `felixbravoai`, `gerraai`,
`haroonkhaans`, `leadgenman`, `liamjohnston.ai`, `lukebuildsai`, `mikemeansbusiness_ai`, `nocode.joshua`,
`pritam.nagrale`, `seanpurvis.ai`, `shrug.manny`, `valeridoesai`.
**Reels (pure form).** [DVwI55QDinY](https://www.instagram.com/reel/DVwI55QDinY/),
[DcnHtUGS_tE](https://www.instagram.com/reel/DcnHtUGS_tE/),
[Dct6Op3n6Zd](https://www.instagram.com/reel/Dct6Op3n6Zd/),
[DcJuUdBT8Cf](https://www.instagram.com/reel/DcJuUdBT8Cf/),
[Dc9NVONstAs](https://www.instagram.com/reel/Dc9NVONstAs/).
**Performance.** Reels containing any split state: median robust_z **1.03 vs 1.43** (p=0.044), view_lift
1.38 vs 2.49 (p=0.093). Pure split (n=27, 18 creators): median view_lift **0.94**, robust_z 0.76 —
against a corpus median of 2.03 and 1.26. `split_share` shows no strong-vs-weak difference (median 0.0
on both sides, p=0.628). `A_ROLL_MEDIUM > SPLIT_SCREEN > A_ROLL_MEDIUM` (n=7, 6 creators): view_lift
0.83, robust_z 0.71.
**Transcript context.** Split-screen reels are usually talking over footage the creator did not make.
DcnHtUGS_tE ("You can now turn a single idea into an entire AI film… This is called Buzzy.") reached
65× on views and carries share_rate 0.0016 and save_rate 0.0005 — the lowest hi-intent rates anywhere
in the top thirty.
**Intended effect.** Keep a face on screen while showing something else.
**Likely reason it does not pay.** It halves the pixels available to the evidence at the exact moment
the evidence is the argument, and it signals reaction content rather than first-hand work.
**Where to use it.** Nowhere in the M2 template.
**Where not to.** Everywhere. If a reaction layout is genuinely needed, cut between full-frame face and
full-frame screen (pattern 1) instead.
**Confidence.** PROBABLE. p=0.044 pooled on robust_z, the creator-normalised save-rate check does not
survive, and split use is heavily creator-specific.

---

## Core pattern 4 — Single unbroken process shot

**Sequence.** One state for all nine samples, almost always `B_ROLL_PROCESS` (the device, dashboard or
map doing the thing) or a single A-roll framing.
**Frequency.** 68 of 266 reels hold a single coarse state. The `B` variant is 6 reels; single-A is 19;
single-SCR 16; single-SPL 21.
**Creators.** The B variant spans 4 creators — `alassafi.ai`, `bennett.spooner`, `jarvis_ai_spark`,
`olivermerrick___`.
**Reels.** [DZgBxjnBzMe](https://www.instagram.com/reel/DZgBxjnBzMe/),
[DbYh2P-MQnj](https://www.instagram.com/reel/DbYh2P-MQnj/),
[DbcPo0dMQ3d](https://www.instagram.com/reel/DbcPo0dMQ3d/),
[DbVKVz0y8xo](https://www.instagram.com/reel/DbVKVz0y8xo/),
[DZsxIrwBtvC](https://www.instagram.com/reel/DZsxIrwBtvC/),
[Db24N0bSIyJ](https://www.instagram.com/reel/Db24N0bSIyJ/).
**Performance.** Pure `B_ROLL_PROCESS` (n=6, 4 creators): median view_lift **30.90**, robust_z **4.13**,
median play 554 907 — the highest of any visual sequence in the corpus. Single-state reels overall show
no advantage (median robust_z 1.25 vs 1.26 for multi-state, p=0.47), so the effect belongs to the
B_ROLL_PROCESS content, not to holding one shot.
**Transcript context.** These reels are almost silent or almost entirely narration over a live artefact.
DZgBxjnBzMe is 14 spoken words in 27 seconds — hook beat "Welcome back." — at 207× its author's median;
almost all the runtime is the phone unlocking itself, opening apps and placing a call.
**Intended effect.** Nothing to disbelieve and nothing to argue with.
**Likely reason it works.** The evidence is continuous, so the viewer cannot locate the cut where the
trick would have to be.
**Where to use it.** An M2 Builds reel where the build genuinely runs end to end on screen — record the
whole run in one take and narrate over it.
**Where not to.** Anywhere the artefact is static. A dashboard that does not move for nine samples reads
as a screenshot, and `SCREENSHOT`-heavy sequences sit at the corpus median.
**Confidence.** PROBABLE at best; n=6 across 4 creators is above the INSUFFICIENT floor but far below
the reliability threshold, and the cell is dominated by two very large outliers.

---

## Core pattern 5 — Persistent top banner plus rolling speech caption

**Sequence.** Not a shot sequence but a text layer: one fixed title across the whole reel carrying the
promise, plus a bottom caption that tracks the spoken words one phrase at a time, usually with the
current word highlighted.
**Frequency.** Captions are universal — 86 % of all 2 645 labelled frames carry text overlay and the
median `text_overlay_density` is 1.0. Placement: bottom 1 099 frames, top 571, middle 568, none 403.
Style keywords across 295 reels: white 234, bold 227, black 111, boxed 82, yellow 59, highlight 39,
word-by-word 19, karaoke 9.
**Creators.** Universal; `gerraai`, `badarmunir_official` and `tech_with_tim` are clean examples.
**Reels.** [DS85EeYjsSt](https://www.instagram.com/reel/DS85EeYjsSt/) (persistent title
"A.I caller for construction company setup with VAPI + N8N + GHL fo $3k" across all nine samples with a
rolling highlighted bottom caption), [DZU9x_1AY2t](https://www.instagram.com/reel/DZU9x_1AY2t/),
[DBKJLzavogz](https://www.instagram.com/reel/DBKJLzavogz/).
**Performance.** None. `text_overlay_density` median is 1.0 in both the strong and the weak robust_z
quartile (p=0.418). The pooled save-rate correlation (+0.180, p=0.005) does not survive creator
normalisation.
**Intended effect.** Keep the promise legible to a viewer who arrives at second 15.
**Likely reason it is not a differentiator.** Everyone does it, so its absence is a penalty and its
presence is not a gain.
**Where to use it.** Fix one M2 caption system and never revisit it: bold white on a solid box,
bottom-anchored for speech, plus a persistent top banner holding the reel's promise.
**Where not to.** Do not spend production time A/B-ing caption styles; nothing in this corpus suggests
a return.
**Confidence.** RELIABLE as a description of ubiquity (n=2 645 frames); the performance null is also
RELIABLE. Style categories are free-text keywords and were never tested against performance.

---

## Transitions

`transitions_observed` across the corpus: **663 `hard_cut_or_more`** and **15 `unknown`**. Per SPEC §5 a
transition is recorded only where fa-v1 actually saw two adjacent samples differ; `same_shot` and
everything unobserved becomes `unknown`. There is therefore **no evidence in this dataset for any
transition type other than a hard cut** — no dissolves, whips, match cuts or zoom transitions are
recorded, and their absence is a measurement artefact, not a finding.

Cut frequency, the only related quantity available: median 7.26 cuts per minute (p25 2.49, p75 13.68,
max 78.4, n=282). No relation to any metric (robust_z rho +0.056, p=0.36; view_lift rho +0.003,
p=0.96; strong quartile 7.06 vs weak 6.75, p=0.42). 38 of 282 rows report zero cuts, which is
indistinguishable from a detector that never fired. `cut_metric_quality` is
`ffmpeg_scene_0.35_count_only` on all 282 rows: a scene-score threshold count, usable only as a relative
busy/calm signal inside this dataset, never quotable as an edit count.

**Transcript-to-frame alignment.** Only 55 of 1 527 beat boundaries (**3.6 %**) have a scene starting
within 0.3 s of them; 215 of 264 reels have no aligned boundary at all. Reels with at least one aligned
boundary show no advantage (robust_z 1.45 vs 1.25, p=0.60; share 0.0168 vs 0.0149, p=0.28; save p=0.64).
With nine samples per reel this is at least partly a measurement floor, which is why the honest reading
is a null, not a finding. **Confidence INSUFFICIENT.**

---

## Split-screen usage, summarised

Split screen is the niche's most-used and least-rewarded arrangement: 22.3 % of all frames, the most
common opening state (73 of 266 reels), 51 creators, and the only roll share with a negative association
to `robust_z` that reaches p<0.05 (1.03 vs 1.43, p=0.044). Its one positive pooled association —
`split_share` → save_rate +0.193 (p=0.0025) — does not survive creator normalisation (cn rho +0.036).
`a_roll_share` behaves similarly: pooled −0.156 against share_rate (p=0.011), creator-normalised −0.094,
survives — more face on screen, fewer forwards.

The pattern to take from the corpus is the opposite of its habit: **less face, more full-frame screen,
and a return to the face only to say what it means.**

---

## Roll shares, strong vs weak quartile

From `reports/data/visual_patterns.json` (n=74 per side, q1 robust_z 0.543, q3 2.943):

| share | strong median | weak median |
|---|---:|---:|
| a_roll_share | 0.2222 | 0.2222 |
| b_roll_share | 0.0000 | 0.0000 |
| split_share | 0.0000 | 0.0000 |
| **screen_share** | **0.2222** | **0.1111** |

Screen share is the only one that differs, and even it does not clear p<0.05 in the 67-per-side
Mann-Whitney test in `associations.json` (p=0.234). The pooled and creator-normalised correlations
(§ pattern 2) are the stronger evidence; the quartile test simply lacks power inside a pre-selected
corpus.
