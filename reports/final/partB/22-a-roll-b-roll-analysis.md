# 22. A-roll / B-roll Analysis

**Denominators.** Roll shares are computed over the **295** codes with an fa-v1 read; performance joins
use the **266** that also carry a transcript, and save-rate joins **243**. A roll share is the fraction of
**nine labelled samples** carrying that roll, never a fraction of screen time. The quartile split in
`visual_patterns.json` uses 74 per side (q1 `robust_z` 0.543, q3 2.943); the 115-feature Mann-Whitney test
in `associations.json` uses 67 per side (q1 0.596, q3 2.855). The two denominators are reported separately
and never mixed.

## The baseline and the quartile test

A-roll is the niche's largest roll — **33 % of all 2 645 labelled frames**, with a face present in 65 % of
them — and the median per-reel `a_roll_share` in the analysed set is **0.333**. B-roll is almost absent:
**7 % of frames** (B_ROLL_CONTEXT 113, B_ROLL_PROCESS 72) and a median per-reel `b_roll_share` of
**0.000**.

| share | strong median (n=74) | weak median (n=74) |
|---|---:|---:|
| a_roll_share | 0.2222 | 0.2222 |
| b_roll_share | 0.0000 | 0.0000 |
| split_share | 0.0000 | 0.0000 |
| **screen_share** | **0.2222** | **0.1111** |

Three of the four rolls are identical on both sides of the quartile split. Only screen share differs, and
even it does not clear p<0.05 in the 67-per-side Mann-Whitney (p=0.234) — a test that simply lacks power
inside a pre-selected corpus. The stronger evidence for the screen is the correlation, not this table.

## More face is weakly worse, not better

![A-roll share vs performance, n=295](reports/charts/a_roll_share_vs_performance.png)

| pair | n | creators | rho | p | creator-normalised | survives |
|---|---:|---:|---:|---:|---:|---|
| `a_roll_share` → share_rate | 266 | 102 | **−0.156** | 0.011 | −0.094 | **yes** |
| `a_roll_share` → save_rate | 243 | 95 | −0.155 | 0.015 | −0.052 | no |
| `a_roll_share` → robust_z | 266 | 102 | −0.046 | 0.46 | — | — |
| `screen_share` → share_rate | 266 | 102 | **+0.203** | **0.00085** | **+0.129** | **yes** |
| `screen_share` → save_rate | 243 | 95 | +0.139 | 0.030 | +0.120 | yes |
| `b_roll_share` → any metric | 266 | 102 | no signal | — | — | — |

The scatter is a cloud with a faint downward tilt, and the table says what the cloud cannot: **more face
on camera is associated with fewer forwards**, and the association survives creator normalisation, so it
is not merely a statement about which creators talk to camera. Against reach there is nothing at all
(−0.046, p=0.46). The mirror finding is the one to act on: `screen_share` is **the only roll with a
positive RELIABLE association anywhere in the 460-pair run** [I-08]. Reels whose visual sequence contains
any screen state carry median share rate **0.0168 against 0.0118** (p=0.00013) and save rate **0.0308
against 0.0220** (p=0.001), and the *first-frame* version of the same finding is stronger inside creators
than between them (+0.285 against +0.208 pooled, n=161) [I-09].

## The pattern that uses both: talk, show, come back

`A > SCREEN > A` — presenter, cut to a full-frame screen, cut back to the presenter — is the strongest
named visual arrangement in the corpus.

| | value |
|---|---|
| reels containing the run | **39 of 266**, across **32 creators** |
| reels that are exactly `A > SCR > A` and nothing else | **11**, one each from 11 different creators |
| containing-the-run performance | median share rate **0.0213 vs 0.0140** (p=0.00076); median robust_z 2.09 vs 1.22 (p=0.10) |
| the exact 11-reel form | median `robust_z` **3.01**, `view_lift` **9.86**, median play 218 733 |
| the literal `A_ROLL_CLOSE_UP > SCREENSHOT > A_ROLL_CLOSE_UP` | n=3, 3 creators, `robust_z` 5.0, `view_lift` 52.04 |

The eleven exact-form reels come from eleven different creators — `tenfoldmarc`,
`buildingwithstring.com_`, `kevinfremon`, `shrug.manny`, `manthanjethwani`, `codewithnishant` among them —
which is the best protection available here against a single-account artefact.

**Transcript reading.** The division of labour is explicit in the beats: **the face carries the promise and
the payoff, the screen carries the mechanism.**
[DWCPx0PkQzA](https://www.instagram.com/reel/DWCPx0PkQzA/) (1 074 517 plays, 142.8×, 57.3 saves per 1 000)
opens to camera with a bold claim, hands the two mechanism beats to the screen ("copying this line into
your terminal… step three is to download the UI UX pro max skill", 14.4–47.0 s), then returns to the face
for the payoff: **"Normandy would take you four steps to create beautiful websites like this But I've
created a github repo where all you need to do is copy one line of code"** (47.4–58.5 s). The "so what" is
delivered by a person. [DZ-wujrTJ0u](https://www.instagram.com/reel/DZ-wujrTJ0u/) (51.6×, 64.9 saves per
1 000) runs the same shape over a 172-second runtime, demoing before the instructions and again after, so
the reward bookends a long middle.

**Visual reading.** fa-v1's read of DWCPx0PkQzA is `A_ROLL_CLOSE_UP > SCREENSHOT > A_ROLL_CLOSE_UP` with a
black rounded-box title ("CLAUDE CODE MAKE $10,000 WEBSITES FOR FREE") held over the opening beats and
four proof visuals: the Claude Code quickstart page, the npm `framer-motion` page, a `ui-ux-pro-max-skill`
repository and an MCP install guide. Five of eight observed sample transitions are hard cuts. Every claim
in the spoken mechanism has a page behind it.

**Why it plausibly works — stated as interpretation, not cause.** A screen is a claim a viewer can check
in the moment; a face is where the interpretation can be delivered. Reels that end on the screen have
nowhere to put the "so what", and the "so what" is what gets forwarded.

## B-roll: nearly absent, and its one strong cell is process footage

`b_roll_share` shows no signal against any metric and its median is zero on both sides of the quartile
split. The interesting cell is not the share but the content: **pure `B_ROLL_PROCESS` (n=6, 4 creators —
`alassafi.ai`, `bennett.spooner`, `jarvis_ai_spark`, `olivermerrick___`) carries median `view_lift` 30.90
and `robust_z` 4.13, the highest of any visual sequence**, while single-state reels overall show no
advantage at all (median `robust_z` 1.25 against 1.26 for multi-state, p=0.47). The effect therefore
belongs to the *content* — the device, dashboard or map visibly doing the thing — and not to holding one
shot. [DbVKVz0y8xo](https://www.instagram.com/reel/DbVKVz0y8xo/) is the ungated example: a camera filming
a curved monitor showing a "THE CLIP MACHINE" workflow diagram with a hand on a drawing tablet below, and
a spoken objection block that spends thirty seconds killing the obvious answer before offering its own.

B-roll *context* — stock clips of people at computers — is the other 4.3 % of frames and carries nothing.
The distinction matters for M2: process footage is evidence, context footage is decoration, and only one of
them is worth a shooting day.

## Strategic implication

The M2 storyboard is **face (promise, ~8 s) → screen (the run, ~25 s) → face (what it changes on Monday,
plus the closing line, ~10 s)**, with the CTA on the face and never on the screen. Two limits: do not cut
back to the face more than twice — the four-and-more-state group shows no additional gain (chapter 21) —
and do not use a screen that is not M2's own. Never a stock UI, never a slide of a UI. Where the build
genuinely runs end to end, the `B_ROLL_PROCESS` variant is licensed: record the whole run in one take and
narrate over it, which also satisfies the one-take production rule at no extra cost. For a Teardown whose
subject is a process rather than a tool, the screen is the artefact of that process — the spreadsheet, the
inbox, the paper form — not a face.

**Confidence: RELIABLE** for `screen_share` → share_rate and for any-screen-present → save_rate (n=243–266,
95–102 creators, p<0.01, creator-normalised survives). **PROBABLE** for `a_roll_share` → share_rate
(p=0.011, survives normalisation but fails the p<0.01 bar). **PROBABLE** for the `A > SCREEN > A` pattern:
pooled p<0.001 on share rate only, and the exact-sequence cell is n=11. **INSUFFICIENT** for pure
`B_ROLL_PROCESS` (n=6, 4 creators, dominated by two very large outliers). Shares are fractions of nine
samples; none of this is causal.
