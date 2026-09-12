# 23. Split-Screen Analysis

**Denominators.** `split_share` is computed over the **295** fa-v1 codes as a fraction of nine labelled
samples; performance joins use the **266** with a transcript and **243** with a save rate. First-frame
counts use 266. The quartile contrast in `visual_patterns.json` uses 74 per side; the Mann-Whitney feature
test uses 67 per side. Baselines: analysed-set median `view_lift` **2.03**, `robust_z` **1.26**, share rate
**0.0152**, save rate **0.0278**.

## Split screen is the niche's most-used and least-rewarded arrangement

| | value |
|---|---|
| share of all labelled frames | **591 of 2 645 = 22.3 %** — the single largest frame type |
| reels opening on it | **73 of 266** — the most common opening state |
| reels containing any split state | **99** |
| reels holding it across all nine samples | **27**, from **18** creators |
| creators using a split state at all | **51** |
| median per-reel `split_share` (analysed set) | **0.000** |

![Split-screen share vs performance, n=295](reports/charts/split_share_vs_performance.png)

| comparison | split | no split | p |
|---|---:|---:|---:|
| any split state, median `robust_z` | **1.03** | **1.43** | **0.044** |
| any split state, median `view_lift` | 1.38 | 2.49 | 0.093 |
| pure `SPLIT_SCREEN` sequence (n=27, 18 creators), median `view_lift` | **0.94** | corpus 2.03 | — |
| pure `SPLIT_SCREEN`, median `robust_z` | 0.76 | corpus 1.26 | — |
| `A_ROLL_MEDIUM > SPLIT_SCREEN > A_ROLL_MEDIUM` (n=7, 6 creators), `view_lift` | 0.83 | corpus 2.03 | — |
| first frame is SPLIT_SCREEN (n=73, 40 creators), `view_lift` / `robust_z` | 1.63 / 1.10 | corpus 2.03 / 1.26 | — |
| `split_share`, strong vs weak quartile | 0.0 | 0.0 | 0.628 |

The scatter and the table agree on an unusual combination: **the layout the niche uses most is the only
roll share with a negative association to reach that reaches p<0.05**, and its pure form sits at less than
half the corpus median on `view_lift`. The one positive pooled association — `split_share` → `save_rate`
**+0.193 (p=0.0025)** — **collapses under creator normalisation (cn +0.036)**, which means it is a
statement about *which creators use split screen*, not about the layout. The median `split_share` is 0.0
in both quartiles (p=0.628), so the quartile test adds nothing either way.

Two honest limits on this finding. First, p=0.044 on a single Mann-Whitney inside a pre-selected corpus is
a weak result, and split use is heavily creator-specific — 18 accounts supply all 27 pure-form reels.
Second, 9 samples cannot distinguish a held split from a reel that cuts to full-frame screen between
samples, so the measured `split_share` is noisy. What survives both caveats is the *absence of any
positive evidence* for a layout that covers 22.3 % of all frames in the niche. With 99 reels and 51
creators, an advantage of any size should have been visible here.

## Why it plausibly does not pay

Stated as interpretation, not as cause: a split halves the pixels available to the evidence at the exact
moment the evidence is the argument, and it signals reaction content rather than first-hand work. Chapter
22's measurement is the complement — full-frame screen is the only roll with a positive RELIABLE
association, and opening on it is worth roughly half again the forwarding rate.

**Transcript reading.** The split-screen reels in this corpus are usually **talking over footage the
creator did not make**. [DcnHtUGS_tE](https://www.instagram.com/reel/DcnHtUGS_tE/) is the clearest case:
"You can now turn a single idea into an entire AI film. Script, characters, scenes, all of it. This is
called Buzzy." (hook, 0.0–7.3 s). It reached **65×** its author's median on views and carries **share rate
0.0016 and save rate 0.0005** — the lowest hi-intent rates anywhere in the top thirty by reach. Plenty of
attention, almost no intent. The pattern recurs: [DVwI55QDinY](https://www.instagram.com/reel/DVwI55QDinY/)
holds a split for all nine samples and its ta-v1 read is INSUFFICIENT — there is no spoken script to
analyse at all.

The corpus's strongest pure-split reel is the exception that still does not rescue the layout.
[Dct6Op3n6Zd](https://www.instagram.com/reel/Dct6Op3n6Zd/) carries **75.9 saves per 1 000**, the second
highest in the corpus, on a held split. Its hook — "4 GitHub Repos went viral this week and barely anyone's
actually using them yet." (0.0–4.4 s) — is followed by four explanation beats ordered by increasing scale,
so retention survives to the last item, which sits immediately before the gate. **Copy the ordering, not
the layout**: the reel works because of a countdown structure and a gated artefact, and its save rate
carries the gate's ×2.8 inflation (chapter 18).

**Visual reading.** fa-v1's read of Dct6Op3n6Zd shows bold `Graft` and `GitHub` logo cards appearing above
the host, with a before/after pipeline diagram and an agent-count dashboard as its only two proof visuals
across nine samples — two pieces of evidence in 38 seconds, each at half size. DcnHtUGS_tE is the same
geometry applied to generated footage: a cinematic AI clip above a reacting host, with the host occupying
the lower half throughout. In both, the thing the viewer is being asked to believe never gets the full
frame.

## What this explains about M2's existing cards

**Nine of main's 23 legacy source reels open on `SPLIT_SCREEN`** — the corpus's weakest opening state.
That is not an editorial preference; `cards.py` ranks candidates on metrics only and has no visual input at
all, so the selection was blind to layout. The three shot-plan columns the card writer fills automatically
(`shot_banner`, `shot_frame`, `shot_screen`) therefore had nothing to inherit from the reference. The fix
is structural: **a card must not inherit a reference's layout without checking it**, and the reference's
`first_frame_type` and coarse `visual_sequence` must travel onto the card so the check is possible.

## Strategic implication

**Split screen has no place in the M2 template.** If a reaction layout is genuinely needed — commenting on
someone else's demo, for instance — **cut between full-frame face and full-frame screen instead**, which is
chapter 22's `A > SCREEN > A` pattern and the one arrangement with positive evidence behind it. Where a
reference M2 wants to borrow is a split-screen reel, borrow its script ordering and its topic and replace
its geometry. And do not spend production time testing split variants: the corpus has already run that
experiment across 99 reels and 51 creators, and the result is at best nothing.

**Confidence: PROBABLE.** The headline contrast reaches p=0.044 pooled on `robust_z` — above the p<0.01
bar the method requires for RELIABLE — the creator-normalised save-rate check does not survive, and split
use is concentrated in 18 accounts. The supporting cells (pure split n=27; `A > SPL > A` n=7) are small.
Shares are fractions of nine samples, not screen time, so a reel that cut to full-frame screen between
samples may be miscoded. No causal claim is licensed: this is an association between a layout and a
creator-relative score inside a corpus pre-selected for strength.
