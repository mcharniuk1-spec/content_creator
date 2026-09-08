# M2 Lab type scale — measured, not guessed

Method: read real advance widths (hmtx), vertical metrics (hhea/OS2) and cmap coverage
from the four IBM Plex TTFs with `fontTools` (`unitsPerEm = 1000` for all four).
Line-wrap is a greedy word-wrap simulation (same algorithm a CSS renderer uses) against
a 30-line hook corpus and a 5-sentence body corpus written for this test (AI-for-business
niche, not real M2 Lab copy). Tracking is applied as `tracking_em * size_px` per character.
Script: `type-metrics.py`. Raw numbers: `type-metrics.json`. Run: `python3 type-metrics.py`.

Canvas: 1080 wide, pad-x 96 → text column **888px**. Reel safe band `1920-180-320=1420px`.
4:5 safe band `1350-180-320=850px`.

## 0. Font vertical metrics (units, upm=1000)

| font | ascent | descent | capHeight | xHeight |
|---|---:|---:|---:|---:|
| Condensed Bold (hook) | 1025 | -275 | 698 | 525 |
| Sans Regular (body) | 1025 | -275 | 698 | 516 |
| Sans SemiBold (body/caption) | 1025 | -275 | 698 | 522 |
| Mono Medium (label) | 1025 | -275 | 698 | 516 |

All four share the same capHeight (698/1000 em) — IBM Plex keeps cap height constant
across the family, so cap-height-based legibility checks below use one ratio (0.698×size)
for every role.

## 1. Hook — chars/line and line count into 888px (tracking -0.01em)

Corpus: 30 lines, 6–8 words (min 6, max 8, avg 7.27 words — verified programmatically).

| size | avg char width px | chars/line (888px) | 6-word sample | 8-word sample | corpus avg lines | corpus max lines |
|---:|---:|---:|---:|---:|---:|---:|
| 90 | 38.06 | 23 | 2 | 2 | 2.37 | 3 |
| 96 (default) | 40.60 | 21 | 2 | 2 | 2.53 | 3 |
| 104 | 43.98 | 20 | 2 | 3 | 2.70 | 4 |

6-word sample: "Here is how we automated support". 8-word sample: "This tool cut our
reporting time in half".

Reading: at the default 96px, a typical hook wraps to **2–3 lines**, worst case in the
corpus **3 lines** (one 8-word line at 104px reached 4). ~21 characters fit per line at
96px — this is the real constraint, not word count: two short words can overflow while
two long ones fit.

Body (Regular, no tracking), same 888px column, for context:

| size | avg char width px | chars/line (888px) |
|---:|---:|---:|
| 52 | 23.35 | 38 |
| 46 (default) | 20.65 | 42 |
| 42 | 18.86 | 47 |

## 2. Vertical footprint (leading × size, no extra metrics)

Hook block height = n_lines × size × 1.03:

| size | 2 lines | 3 lines | 4 lines |
|---:|---:|---:|---:|
| 90 | 185.4 | 278.1 | 370.8 |
| 96 | 197.8 | 296.6 | 395.5 |
| 104 | 214.2 | 321.4 | 428.5 |

Body paragraph, 3 lines, leading 1.35: 52px → 210.6px · 46px → 186.3px · 42px → 170.1px.
Label, 1 line, leading 1.0: 32px → 32.0px · 25px → 25.0px.

**Max hook + body that fits each band**, hook@96 + gap 48px + body@46, greedy fill:

| band | px | max hook lines | max body lines | used px | slack px |
|---|---:|---:|---:|---:|---:|
| Reels (1920) | 1420 | 4 | 7 | 878.2 | 541.8 |
| 4:5 (1350) | 850 | 4 | 6 | 816.1 | 33.9 |

Both bands technically fit 4 hook lines + several body lines arithmetically, but the 4:5
band leaves only **34px of slack** at that combination — effectively zero margin for
error (line-height rounding, extra tracking, safe-area drift). The Reels band has
**542px** of slack at the same combo, i.e. more than 5× the room. This is the load-bearing
number for recommendation 6a below.

## 3. Minimum legible size

Two viewing contexts, both scale factors from the brief:
- **Reel in feed**, ~390 CSS-px-wide phone on a 1080px canvas → scale **0.3611**.
- **Profile grid tile**, ~125 CSS-px wide on a 1080px canvas → scale **0.1157**.
  Threshold: cap height ≥ 9 CSS px to "survive" as legible at thumbnail size.

Points = css_px × 0.75 (96 css-px/in → 72pt/in, standard conversion). Physical px @3x DPR
= css_px × 3 (DPR changes sharpness, not logical size).

| role/size | css px (reel) | pt (reel) | phys px @3x | <12css? | cap-h css (grid) | ≥9css on grid? |
|---|---:|---:|---:|:---:|---:|:---:|
| hook 90 | 32.50 | 24.38 | 97.50 | no | 7.27 | **no** |
| hook 96 | 34.67 | 26.00 | 104.00 | no | 7.76 | **no** |
| hook 104 | 37.56 | 28.17 | 112.67 | no | 8.40 | **no** |
| body 52 | 18.78 | 14.08 | 56.33 | no | 4.20 | no |
| body 46 | 16.61 | 12.46 | 49.83 | no | 3.72 | no |
| body 42 | 15.17 | 11.38 | 45.50 | no | 3.39 | no |
| label 32 | 11.56 | 8.67 | 34.67 | **yes** | 2.59 | no |
| label 25 | 9.03 | 6.77 | 27.08 | **yes** | 2.02 | no |

Findings:
- On a Reel viewed in-feed, **hook and body are all above the 12 CSS px floor**. The
  **label (32px and 25px) is below 12 CSS px** in both variants — it is the one role
  that risks illegibility at normal reel viewing distance.
- **No current size survives the profile-grid thumbnail** at the 9 CSS px cap-height
  bar — even the largest hook (104px) only reaches 8.40px cap height there. Solving
  backward, a hook would need to be ≈**111.5px** to clear 9px cap height on the grid tile
  (9 ÷ 0.1157 ÷ 0.698). That is outside the current 90–104 range, and body/label text
  cannot realistically be sized up to reach it. **Conclusion: the profile grid tile
  is not a legibility target for any text role at these sizes — treat the grid cover
  as a visual/branding frame only, not a place to read a hook.**

## 4. Cyrillic coverage (U+0410–U+044F, from cmap)

| font | covers full Cyrillic A-Ya | missing |
|---|:---:|---:|
| Condensed Bold (hook) | **no** | 64/64 |
| Sans Regular | yes | 0/64 |
| Sans SemiBold | yes | 0/64 |
| Mono Medium | yes | 0/64 |

The hook font (Condensed Bold) has **zero Cyrillic glyphs**. If a Cyrillic hook is ever
needed (Kyiv-market content in Russian/Ukrainian), it cannot use Condensed Bold as-is —
it would fall back to the OS default font, breaking the display style. Body, label and
SemiBold all cover the full range and are safe for Cyrillic today.

## 5. Mono label widths (+0.16em tracking)

| label | 32px | 25px |
|---|---:|---:|
| M2 RADAR | 194.56 | 152.00 |
| M2 BUILDS | 218.88 | 171.00 |
| M2 TEARDOWN | 267.52 | 209.00 |
| KEEP | 97.28 | 76.00 |
| KILL | 97.28 | 76.00 |
| TEST | 97.28 | 76.00 |
| WAS | 72.96 | 57.00 |
| NOW | 72.96 | 57.00 |
| SAVED | 121.60 | 95.00 |

Because Plex Mono is monospaced, **KEEP / KILL / TEST are already pixel-identical**
(all 4 characters → 97.28px @32px, 76.00px @25px) — no manual width juggling needed.
Same for WAS/NOW (3 chars, identical width).

**Chip recommendation**: fixed chip width = widest label + 24px padding each side.
- @32px: 97.28 + 48 = **145px fixed chip width** (24px horizontal padding).
- @25px: 76.00 + 48 = **124px fixed chip width** (24px horizontal padding).

This also covers WAS/NOW/SAVED as long as they're not placed in the same chip row as
KEEP/KILL/TEST at a different width — SAVED (121.6px @32) would need its own chip sized
121.6 + 48 = 170px if it ever shares a row style with the 3-letter set.

## 6. Recommendations

**(a) Does 4:5 need a smaller hook or fewer words?**
4:5 band = 850px. Hook@96/3 lines = 296.6px; hook@96/4 lines = 395.5px.
- 96px/3-line hook + 48px gap + 1-line body(46) = 406.7px → fits (850), 443px slack.
- 96px/3-line hook + 48px gap + 2-line body(46) = 468.8px → fits (850), 381px slack.
- 84px/4-line hook + 48px gap + 1-line body(46) = 456.2px → fits (850), 394px slack.

Arithmetically 96px still fits 4:5 for the realistic 2–3 line hook case. **Do not drop to
84px by default.** But recommendation 2's max-fit-combo shows only 34px slack when a hook
pushes to its worst-case 4 lines on 4:5 — so the real fix is **fewer words on 4:5, not a
smaller font**: cap the 4:5 hook at **6 words** (this corpus's 6-word sample holds 2 lines
at every tested size), rather than allowing the 8-word/90-104px combinations that can
reach 3–4 lines. Reserve 84px as a manual escape hatch only if a specific hook cannot be
shortened below 7–8 words on 4:5.

**(b) Max characters per line (lint constant)**, worst case = smallest chars/line across
the sizes in use per role:
- **Hook: ≤ 20 characters/line** (binding case: 104px, 20 chars/888px).
- **Body: ≤ 38 characters/line** (binding case: 52px, 38 chars/888px).

Use these as hard lint caps in the copy-writing/QA tool; they already include the -0.01em
hook tracking and are column-width-derived, not word-count-derived.

**(c) Caption/subtitle size for burned-in 2-line subtitles**, Plex Sans SemiBold, needs
≥14 CSS px on a 390px-wide phone (scale 0.3611): solving 14 ÷ 0.3611 = **38.77px raw
minimum**.

| candidate px | css px (reel) | ≥14css? |
|---:|---:|:---:|
| 34 | 12.28 | no |
| 36 | 13.00 | no |
| 38 | 13.72 | no |
| 40 | 14.44 | **yes** |
| 42 | 15.17 | **yes** |

**Recommend 40px** (Plex Sans SemiBold) as the caption size — clears the 14 CSS px floor
with a small margin (0.44px) at 40px; 42px gives a safer margin (1.17px) if the subtitle
zone has room. Do not use 38px or below — it fails the floor by a full pixel.

## Method notes / assumptions

- Tracking width = `tracking_em × size_px` added **per character** (including the last),
  matching how most browser text-layout engines compute run advance with letter-spacing.
- Chars-per-line uses the corpus **average** character width; word-boundary line counts
  (task 1's 6w/8w columns, task 2) use actual greedy word-wrap, which is what really
  determines line breaks — the two numbers are reported separately on purpose.
- Cap-height-based legibility (tasks 3) uses OS/2 `sCapHeight` (698 units for all four
  fonts here); "survives" is a threshold call from the brief (9 CSS px), not a
  peer-reviewed readability standard.
- All numbers are reproducible by re-running `type-metrics.py`; none are hand-typed
  into this file independent of that run.
