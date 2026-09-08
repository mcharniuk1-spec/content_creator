# M2 Lab — palette spread options

Generated 2026-09-08 by `research/palette-compute.mjs`. Every number below is computed by that script; nothing is estimated by eye.

## Problem

Anthropic publishes the default clusters its models collapse into (raw source of `github.com/anthropics/skills`, frontend-design skill). Three of them matter to us:

1. Near-black background with **one** bright acid-green or vermilion accent.
2. Cream (~`#F4F1EA`) plus contrasting serif plus terracotta (~`#D97757`).
3. Tinted black (`#0B0B0B` / `#111`) with mono captions.

The approved 4 Sep palette carries all three elements of cluster 1 at once: Ink `#101A17` as the primary surface, Lime `#BFFB4C` as a single acid accent, Stamp `#D8402B` sitting almost exactly on vermilion. The brief is to **spread the palette slightly**, not to redesign it. The mark's geometry is untouchable; only its two colour values may change, and the palette must still be recognisable as the same brand.

Five levers were used, in this order of effect:

- **(a) which surface is primary** — Paper-first vs Ink-first
- **(b) hue shift of the bright accent** away from acid green
- **(c) hue and chroma shift of Stamp** away from vermilion
- **(d) one muted structural colour**, so the system reads "two accents + structure" instead of "one shout"
- **(e) a distinct tint on Ink or Paper** — cool-teal, blue-black or neutral-cool

## Method

- **OKLab / OKLCH.** Ottosson (2020) linear-sRGB ↔ OKLab matrices, implemented in the script; OKLCH is the polar form, `C = hypot(a,b)`, `h = atan2(b,a)` in degrees. Variant colours are authored as OKLCH targets, converted to sRGB with chroma reduced by bisection when out of gamut, then the reported OKLCH is recomputed from the resulting hex so the tables show the true value, not the target.
- **Contrast.** WCAG 2.x: relative luminance `Y = 0.2126R + 0.7152G + 0.0722B` on linear sRGB, ratio `(Y_light + 0.05) / (Y_dark + 0.05)`. Thresholds applied: **4.5:1** for body text, **3:1** for large text and graphical objects.
- **Colour blindness.** Machado, Oliveira & Fernandes (2009), *A physiologically-based model for simulation of color vision deficiency*, IEEE TVCG 15(6) — severity 1.0 matrices for deuteranopia and protanopia, applied in **linear** sRGB.
- **Colour difference.** Euclidean distance in OKLab (`ΔE_OK`). Hue difference is the shortest circular arc.
- **Working threshold.** Two colours count as "separable by lightness alone" at **ΔL ≥ 0.15** in OKLCH. This is a working heuristic chosen here, not a published standard. Verdicts are shape-coded anyway (KEEP filled, KILL outlined, TEST dashed), so this is a second line of defence.
- **Script:** `/Users/mihailampleev/Desktop/m2lab-brand/research/palette-compute.mjs` — no dependencies, `node palette-compute.mjs`.

## Current (approved 4 Sep 2026)

Ink-first, one acid-green accent, one vermilion stamp — all three markers of Anthropic cluster 1.

| Name | HEX | OKLCH (L, C, h) | Role |
|---|---|---|---|
| Ink | `#101A17` | 0.207, 0.016, 174.2° | Text, dark surface, mark |
| Paper | `#E9EAE5` | 0.935, 0.007, 115.7° | Light surface, documents, carousels |
| Stamp | `#D8402B` | 0.591, 0.192, 31.1° | Verdict, risk, KILL. Nothing else |
| Lime | `#BFFB4C` | 0.916, 0.206, 126.7° | Mark, rare data indicator; glows on dark only |
| Graphite | `#69706B` | 0.538, 0.011, 154.9° | Secondary text, lines, labels |
| Rule | `#C3C7C1` | 0.825, 0.009, 134.9° | Hairline on Paper |

**Contrast**

| Pair | Ratio | Needs | |
|---|---|---|---|
| Ink on Paper (body text) | 14.69:1 | 4.5:1 | ok |
| Paper on Ink (body text) | 14.69:1 | 4.5:1 | ok |
| Lime on Ink (graphic/large) | 14.48:1 | 3:1 | ok |
| Lime on Paper (graphic/large) | 1.01:1 | 3:1 | below — by design |
| Stamp on Ink (graphic/large) | 3.97:1 | 3:1 | ok |
| Stamp on Paper (graphic/large) | 3.70:1 | 3:1 | ok |
| Graphite on Paper (secondary text) | 4.20:1 | 4.5:1 | **FAIL** |
| Rule on Paper (hairline) | 1.42:1 | 3:1 | below — by design |

**Colour blindness (Machado 2009, severity 1.0)**

Pair checked: **Stamp** vs **Lime**. Threshold for "separable by lightness alone": ΔL ≥ 0.15.

| Vision | Stamp → | Accent → | ΔL | ΔE_OK | Separable by L |
|---|---|---|---|---|---|
| normal | `#D8402B` | `#BFFB4C` | 0.325 | 0.439 | yes |
| deuteranopia | `#938324` | `#FFE75B` | 0.315 | 0.319 | yes |
| protanopia | `#6D6227` | `#FFEA2E` | 0.432 | 0.445 | yes |

**Distance from the Anthropic clusters**

| Comparison | Δh | ΔC | ΔL |
|---|---|---|---|
| Lime vs acid green `#BFFB4C` | 0° | 0 | 0 |
| Stamp vs vermilion `#E34234` | 2° | -0.008 | -0.022 |
| Stamp vs terracotta `#D97757` | 7.7° | 0.061 | -0.081 |

ΔE_OK Paper vs cream `#F4F1EA`: **0.024** · ΔE_OK Ink vs tinted black `#0B0B0B`: **0.059**

**What changes, what breaks**

- Reads as the default "dark lab terminal" — the exact silhouette models fall into.
- Lime and Stamp are both maximum-chroma, so the system has two shouts and no speaking voice.
- Lime L is within 0.01 of Paper L: the mark all but disappears on the light surface.
- No structural mid-tone, so diagrams are built from Graphite alone and read flat.
- Recognisable and confident on dark; indistinguishable from a hundred AI-brand decks.

## A — Oxide (Paper-first)

Smallest true move: flip the primary surface to Paper, de-neon the green, pull Stamp from vermilion to oxide, add a structural blueprint blue.

| Name | HEX | OKLCH (L, C, h) | Role |
|---|---|---|---|
| Paper | `#E4E9EA` | 0.93, 0.006, 211° | PRIMARY surface — carousels, covers, documents |
| Ink | `#0C1D1D` | 0.216, 0.023, 195.6° | Text on Paper; dark surface for accent frames only |
| Signal | `#7DD774` | 0.8, 0.16, 142° | Mark, positive verdict, data highlight |
| Oxide | `#BB4347` | 0.551, 0.155, 21.9° | Verdict, risk, KILL. Nothing else |
| Blueprint | `#33587D` | 0.45, 0.074, 249.8° | Diagrams, arrows, second-level fills, chart series 2 |
| Graphite | `#5C6565` | 0.499, 0.011, 196.8° | Secondary text, labels |
| Rule | `#BEC6C7` | 0.821, 0.009, 205.9° | Hairline on Paper |

**Contrast**

| Pair | Ratio | Needs | |
|---|---|---|---|
| Ink on Paper (body text) | 14.18:1 | 4.5:1 | ok |
| Paper on Ink (body text) | 14.18:1 | 4.5:1 | ok |
| Signal on Ink (graphic/large) | 9.80:1 | 3:1 | ok |
| Signal on Paper (graphic/large) | 1.45:1 | 3:1 | below — by design |
| Oxide on Ink (graphic/large) | 3.31:1 | 3:1 | ok |
| Oxide on Paper (graphic/large) | 4.28:1 | 3:1 | ok |
| Blueprint on Paper (graphic/large) | 6.05:1 | 3:1 | ok |
| Graphite on Paper (secondary text) | 4.89:1 | 4.5:1 | ok |
| Rule on Paper (hairline) | 1.42:1 | 3:1 | below — by design |

**Colour blindness (Machado 2009, severity 1.0)**

Pair checked: **Oxide** vs **Signal**. Threshold for "separable by lightness alone": ΔL ≥ 0.15.

| Vision | Stamp → | Accent → | ΔL | ΔE_OK | Separable by L |
|---|---|---|---|---|---|
| normal | `#BB4347` | `#7DD774` | 0.249 | 0.369 | yes |
| deuteranopia | `#807644` | `#CEBF7A` | 0.239 | 0.239 | yes |
| protanopia | `#625C46` | `#DBC86C` | 0.355 | 0.364 | yes |

**Distance from the Anthropic clusters**

| Comparison | Δh | ΔC | ΔL |
|---|---|---|---|
| Signal vs acid green `#BFFB4C` | 15.3° | -0.046 | -0.116 |
| Oxide vs vermilion `#E34234` | 7.2° | -0.045 | -0.062 |
| Oxide vs terracotta `#D97757` | 16.9° | 0.024 | -0.121 |

ΔE_OK Paper vs cream `#F4F1EA`: **0.031** · ΔE_OK Ink vs tinted black `#0B0B0B`: **0.07**

**What changes, what breaks**

- Feels like a printed lab report rather than a terminal — the dark frame becomes a guest, not the host.
- Signal drops 0.116 in L and 0.046 in C, so the accent stops reading as neon — but it is still a fill on Paper, not a text colour.
- Oxide is a stamped ink, not a warning light; risk now looks archival instead of alarming.
- Blueprint gives diagrams a second structural voice, so the system reads "two accents + structure".
- BREAKS: every Ink-background template must be re-cut for Paper; the mark loses its glow on dark, and Signal at 0.80 L no longer halates against Ink the way Lime did.

## B — Amber (Ink-first)

Keeps the dark surface but changes what shouts: amber becomes the primary signal, green is demoted to a quiet data tint, Stamp moves to crimson away from both vermilion and terracotta.

| Name | HEX | OKLCH (L, C, h) | Role |
|---|---|---|---|
| Ink | `#0F141D` | 0.191, 0.02, 262° | PRIMARY surface — blue-black, not green-black |
| Paper | `#E2E7EA` | 0.925, 0.007, 233.6° | Text on Ink; light surface for documents |
| Amber | `#F2BB31` | 0.82, 0.155, 85° | Primary signal — mark, headline accent, KEEP |
| Mint | `#83E7A8` | 0.85, 0.13, 154.9° | Data indicator only — charts, deltas, the mark's wedge |
| Crimson | `#C72C4C` | 0.549, 0.19, 15.1° | Verdict, risk, KILL. Nothing else |
| Slate | `#525E72` | 0.479, 0.036, 260.6° | Diagrams, dividers, secondary fills |
| Rule | `#B9BEC4` | 0.799, 0.01, 252.8° | Hairline on Paper; also line on Ink at low opacity |

**Contrast**

| Pair | Ratio | Needs | |
|---|---|---|---|
| Ink on Paper (body text) | 14.81:1 | 4.5:1 | ok |
| Paper on Ink (body text) | 14.81:1 | 4.5:1 | ok |
| Amber on Ink (graphic/large) | 10.48:1 | 3:1 | ok |
| Amber on Paper (graphic/large) | 1.41:1 | 3:1 | below — by design |
| Mint on Ink (graphic/large) | 12.27:1 | 3:1 | ok |
| Mint on Paper (graphic/large) | 1.21:1 | 3:1 | below — by design |
| Crimson on Ink (graphic/large) | 3.42:1 | 3:1 | ok |
| Crimson on Paper (graphic/large) | 4.33:1 | 3:1 | ok |
| Slate on Paper (graphic/large) | 5.26:1 | 3:1 | ok |
| Slate on Paper (secondary text) | 5.26:1 | 4.5:1 | ok |
| Rule on Paper (hairline) | 1.50:1 | 3:1 | below — by design |

**Colour blindness (Machado 2009, severity 1.0)**

Pair checked: **Crimson** vs **Mint**. Threshold for "separable by lightness alone": ΔL ≥ 0.15.

| Vision | Stamp → | Accent → | ΔL | ΔE_OK | Separable by L |
|---|---|---|---|---|---|
| normal | `#C72C4C` | `#83E7A8` | 0.301 | 0.426 | yes |
| deuteranopia | `#807648` | `#D7CEAC` | 0.286 | 0.287 | yes |
| protanopia | `#58564C` | `#E7D9A4` | 0.432 | 0.435 | yes |

**Distance from the Anthropic clusters**

| Comparison | Δh | ΔC | ΔL |
|---|---|---|---|
| Amber vs acid green `#BFFB4C` | 41.7° | -0.051 | -0.096 |
| Mint vs acid green `#BFFB4C` | 28.2° | -0.076 | -0.066 |
| Crimson vs vermilion `#E34234` | 14° | -0.01 | -0.064 |
| Crimson vs terracotta `#D97757` | 23.7° | 0.059 | -0.123 |

ΔE_OK Paper vs cream `#F4F1EA`: **0.037** · ΔE_OK Ink vs tinted black `#0B0B0B`: **0.046**

**What changes, what breaks**

- Keeps the current silhouette so nothing has to be re-cut, but the accent hue is ~45 degrees away from acid.
- Amber on blue-black reads as instrumentation and sodium light rather than as a chemical.
- Mint keeps the mark legible as "the M2 green" while removing its neon claim.
- Crimson separates cleanly from both vermilion and terracotta, so cluster 2 is off the table too.
- BREAKS: three chromatic colours is one more than the system wants; discipline is required or covers turn into traffic lights. The dark surface still matches cluster 1 geometry — only the hue argues against it.

## C — Instrument (dual-surface, cyan)

Boldest of the three: the bright accent leaves green entirely for cyan, green survives as a deep viridian data colour, and a muted sage carries structure.

| Name | HEX | OKLCH (L, C, h) | Role |
|---|---|---|---|
| Paper | `#E5EBEB` | 0.936, 0.006, 197° | Primary surface for documents and carousels |
| Ink | `#061B22` | 0.209, 0.03, 222.6° | Text on Paper; surface for Reel covers |
| Cyan | `#4DD4DB` | 0.8, 0.115, 200° | Primary signal — mark, KEEP, highlight |
| Viridian | `#3F9B65` | 0.62, 0.12, 154.8° | Data / positive green, legible on Paper |
| Signal Red | `#CC415E` | 0.581, 0.175, 12.2° | Verdict, risk, KILL. Nothing else |
| Sage | `#616A59` | 0.511, 0.028, 130.2° | Diagrams, grid, secondary fills |
| Rule | `#C0C5C5` | 0.82, 0.006, 197° | Hairline on Paper |

**Contrast**

| Pair | Ratio | Needs | |
|---|---|---|---|
| Ink on Paper (body text) | 14.66:1 | 4.5:1 | ok |
| Paper on Ink (body text) | 14.66:1 | 4.5:1 | ok |
| Cyan on Ink (graphic/large) | 9.90:1 | 3:1 | ok |
| Cyan on Paper (graphic/large) | 1.48:1 | 3:1 | below — by design |
| Viridian on Ink (graphic/large) | 5.13:1 | 3:1 | ok |
| Viridian on Paper (graphic/large) | 2.86:1 | 3:1 | below — by design |
| Signal Red on Ink (graphic/large) | 3.78:1 | 3:1 | ok |
| Signal Red on Paper (graphic/large) | 3.88:1 | 3:1 | ok |
| Sage on Paper (graphic/large) | 4.69:1 | 3:1 | ok |
| Sage on Paper (secondary text) | 4.69:1 | 4.5:1 | ok |
| Rule on Paper (hairline) | 1.45:1 | 3:1 | below — by design |

**Colour blindness (Machado 2009, severity 1.0)**

Pair checked: **Signal Red** vs **Viridian**. Threshold for "separable by lightness alone": ΔL ≥ 0.15.

| Vision | Stamp → | Accent → | ΔL | ΔE_OK | Separable by L |
|---|---|---|---|---|---|
| normal | `#CC415E` | `#3F9B65` | 0.039 | 0.283 | no |
| deuteranopia | `#877E5B` | `#8E8768` | 0.029 | 0.03 | NO |
| protanopia | `#63625E` | `#9B8F62` | 0.154 | 0.164 | yes |

**Distance from the Anthropic clusters**

| Comparison | Δh | ΔC | ΔL |
|---|---|---|---|
| Cyan vs acid green `#BFFB4C` | 73.3° | -0.091 | -0.116 |
| Viridian vs acid green `#BFFB4C` | 28.1° | -0.086 | -0.296 |
| Signal Red vs vermilion `#E34234` | 16.9° | -0.025 | -0.032 |
| Signal Red vs terracotta `#D97757` | 26.6° | 0.044 | -0.091 |

ΔE_OK Paper vs cream `#F4F1EA`: **0.027** · ΔE_OK Ink vs tinted black `#0B0B0B`: **0.066**

**What changes, what breaks**

- Reads as an oscilloscope and a measuring instrument; the laboratory metaphor gets literal.
- Cyan is the furthest any of the three variants gets from the acid-green cluster in hue.
- Viridian is the first green in the system that is actually readable as text on Paper.
- Sage keeps structure warm-neutral so the page does not turn into a single blue wash.
- BREAKS: the mark stops being "the lime one". Recognisability against the approved 4 Sep palette is the weakest here, and Max would need the logo re-exported with a hue nobody has seen yet.

## Comparison

| Variant | Colours | Paper / Ink | Accent Δh from acid green | Stamp Δh from vermilion / terracotta | Paper ΔE_OK from cream | Blocking contrast failures | CVD-separable |
|---|---|---|---|---|---|---|---|
| current | 6 | #E9EAE5 / #101A17 | 0° | 2° / 7.7° | 0.024 | 1 | yes |
| A | 7 | #E4E9EA / #0C1D1D | 15.3° | 7.2° / 16.9° | 0.031 | 0 | yes |
| B | 7 | #E2E7EA / #0F141D | 41.7° | 14° / 23.7° | 0.037 | 0 | yes |
| C | 7 | #E5EBEB / #061B22 | 73.3° | 16.9° / 26.6° | 0.027 | 0 | no |

Two pair types are listed in the tables but excluded from the blocking count, in every variant including the approved one: a bright accent on Paper (it is a fill that carries Ink text on top, never text itself) and Rule on Paper (a hairline held to 3:1 stops being a hairline). Everything else is counted.

## Recommendation — Variant A

**Take A (Oxide, Paper-first).** Reasons, in order:

1. **It attacks the strongest cluster marker first — the surface.** Cluster 1 is defined by a near-black page. Flipping the primary surface to Paper removes the silhouette before any hue argument is needed, and it costs nothing conceptually: "laboratory journal" is a paper object, not a terminal.
2. **It keeps the mark green.** Signal stays in the green family, so recognisability against the approved palette survives. The change is one of chroma and lightness, not identity.
3. **It de-neons the accent measurably, and keeps it strong where it is actually used.** Signal drops chroma from C 0.206 to C 0.16 and lightness from L 0.916 to L 0.8. On Ink it still returns 9.80:1, far above any threshold. It does **not** fix the colour mark on Paper — that pair moves only from 1.01:1 to 1.45:1, so the monochrome Ink mark stays mandatory on light surfaces. What A fixes is the secondary-text colour: Graphite goes from 4.20:1 (below the 4.5:1 text threshold in the approved palette) to 4.89:1.
4. **Two accents plus structure.** Blueprint gives diagrams a voice that is neither Signal nor Oxide, which is what stops a page from reading as "one bright thing on black".
5. **It is the smallest move that works.** B keeps the dark surface, so it only argues with the cluster by hue. C is a genuine redesign of the mark's colour and was not asked for.

Variant B is the fallback if the Ink-first surface turns out to be non-negotiable for Reel covers. Variant C is documented so the direction is on record, not proposed.

## Risks

- **Every existing Ink-background template must be re-cut for Paper.** This is the real cost of A and it is a production cost, not a design one.
- **Signal on Paper is a fill colour, not a text colour.** At 1.45:1 it must always carry Ink text on top, never sit as text itself.
- **The mark loses its halation on dark.** Lime at L 0.916 glowed against Ink; Signal at L 0.8 does not. If that glow is what Max recognises the brand by, this is the thing he will object to.
- **Logo minimum size is NOT improved.** The colour mark against Paper is still effectively invisible (1.45:1). The 32 px minimum and the monochrome-Ink-on-Paper rule in `brand/logo/clearspace.md` both stand unchanged. If the colour mark is wanted on Paper at all, Signal has to drop to roughly L 0.60, which is a different proposal from this one.
- **Oxide sits close to Stamp in lightness** (L 0.551 vs 0.591) but 7.2° off vermilion and at lower chroma, so on a phone at feed size it reads as a stamped brick red rather than a warning light. That is the intent, and it is also the thing most likely to be called "washed out". Its margin on Ink is 3.31:1 — clears 3:1, but only just. Verify on a real device before approval; raising L to ~0.60 buys margin at the cost of moving back toward vermilion.
- **Instagram compression.** All numbers here are computed on clean sRGB. Instagram re-encodes; saturated reds and greens shift first. The swatch sheet PNG must be checked after a round-trip through the platform, not only in the browser.
- **The cluster list can change.** These distances are measured against the clusters documented today. If the published defaults move, the argument for these hues moves with them.
