# M2 Lab heading typeface

Scope: headings, hooks and cover titles only. Body stays IBM Plex Sans, labels stay
IBM Plex Mono. Sheet: `research/heading-font-sheet.html` / `.png`.
Date: 8 September 2026.

## 1 · What the mark is made of

Measured from `brand/logo/m2-mark-color.svg` (1254 unit canvas).

1. **Square lock-up.** The silhouette spans x 225..1029, y 208..1010 — 804 x 802 units,
   1 : 1.00. The mark fills a square, so the heading face must read squarish, not elongated.
2. **Stem 0.239 of the height.** The left arm is 192 units wide against an 802 unit height.
   In a text face that is Black / ExtraBold territory; a 700 Bold looks thin beside it.
3. **Not one curve.** Every edge is a straight segment joined at a hard mitre — the `C`
   commands in the path carry near-zero control offsets. Rules out rounded, humanist and
   geometric-circle faces.
4. **Terminals cut flat and orthogonally.** The stem ends square at y 738 and y 1010.
   No tapers, no angled cuts, no spurs, no ink traps.
5. **Facets at 38–51 degrees.** The Signal wedge edges (620.5,392 / 521,473.5 / 620.5,545.5)
   sit at 50.7 degrees; the arm fold runs near 38 degrees. It reads as a folded ribbon in
   near-isometric projection: flat planes, vertical stress, no optical rounding.

Consequence for type: a squarish grotesk, weight 800–900, flat-sided bowls, horizontally
cut terminals. Anything with round `o`, flared stems or angled terminals fights the mark.

## 2 · Max's repository (github.com/mcharniuk1-spec/content_creator, depth 50)

| Finding | Path |
|---|---|
| No typography was ever collected from the references. "No source video, source frame, camera, edit, **typography**, caption placement... was collected, so visual claims remain `GAP`." | `studio/REAL-SHORTFORM-REFERENCE-ANALYSIS.md:7,29` |
| Previs frames are hard-coded to Arial. 5,746 `font-family="Arial,sans-serif"` occurrences, plus `font-weight="800"` for headings. Colours are `#102019` / `#f8d49d` / `#85d18a` — not our palette. | `studio/framework-library/v1/**/frames/*.svg`, `studio/story-framework-library/v2/**/contact-sheet.svg` |
| North Hux contact sheets are hard-coded to Helvetica. | `outputs/video-plans/north-hux-youtube-10-v1/*/contact-sheet.svg` |
| The Remotion compositor is hard-coded to Arial as well: `fontFamily: 'Arial, sans-serif'`, captions at `fontWeight: 700`, `textAlign: 'center'`, `borderRadius: 18`. Three of those break our lint (`centered-text`, `uniform-radius`, `font-outside-plex`). | `studio/remotion/src/Composition.tsx` |
| He does plan a shared type system, but names no family: "Use auto layout, **shared typography**/color styles, stable frame IDs, and editable text." | `docs/previsualization-and-figma.md:105` |
| He plans to consume our brand pack: "Studio uses reviewed functional principles plus **the M2Lab brand pack**." | `docs/m2-system-architecture.md:9` |
| Consistent rule: keep text as an editable layer, never baked into generated pixels. | `docs/previsualization-and-figma.md:33,38,116`; `studio/SCREENWRITING-GUIDE.md:147` |

Reading: type is unclaimed territory in Max's pipeline. Arial and Helvetica are
placeholders he expects our brand pack to replace. Choosing a display face is therefore
a live dependency for him, not a cosmetic decision.

## 3 · Notion: what the niche actually does with type

| # | Claim | Source |
|---|---|---|
| 1 | **No font-level research exists in the workspace.** `font`, `typeface`, `typography`, `italic`, `serif`, `highlight bar`, `condensed` appear zero times across the release page and all ten cards. No font is ever named. | audit of all pages below |
| 2 | One headline at the top of frame, over a presenter or a diagram — the recurring pattern across all 18 reviewed reels. Never a two-tier headline. | 14 reel pages under "M2 Signal + Studio · 7 September", e.g. `.../3d20bd21ed6a81159afbfd1aaafe6ae8` (@hamza_automates), `.../3d20bd21ed6a811b9a7ed4001e9dc141` (@heystevetan) |
| 3 | The **only** emphasis device observed anywhere: "colored outlines and red annotation" on one reel. No italic serif, no highlight bar, no colour-word. | `.../3d20bd21ed6a81159afbfd1aaafe6ae8` |
| 4 | The only hierarchy device observed inside graphics: short caps labels — `Level 1/2/3`, `Tier 1`, `PHASE 1`, `overrated/underrated`. | @joestoltelive `.../3d20bd21ed6a8133b75df953bf6c8d36`, @builders.central `.../3d20bd21ed6a81788a60fe82036b6c14`, @olivermerrick___ `.../3d20bd21ed6a81a589b6e4b16fe338b8` |
| 5 | Caption rule repeated verbatim on all ten shooting cards: "Editable sentence captions, **maximum two short lines**." | M2-I01 `.../3d40bd21ed6a81e1bc09cc3c84e8f16f` and nine siblings |
| 6 | **ALL CAPS is already the de-facto convention:** all 70 "On-screen element" strings across the ten cards are set in caps. Never written down as a rule. | all ten card pages |
| 7 | Longest on-screen string in the whole slate is 7 words; typical is 1–4 words, one string per scene, never stacked. | M2-I04 `.../3d40bd21ed6a81378c9eccab000b7f22` |
| 8 | "The **first frame should identify the object or problem without audio**." | creator-techniques handbook `.../3d40bd21ed6a81749d94c0e9f6478590` |
| 9 | The handbook's nine techniques are all about writing structure. It contains no font, weight, case, colour or emphasis guidance. | same |
| 10 | "Text density" is a tracked analysis field, but the Instagram frame analysis never ran (0 frames collected). | Control Dashboard `.../3c70bd21ed6a811a8d9fc1f8312cd8fa` |
| 11 | "M2 Lab — Radar" is an empty tombstone: "Moved. The radar now lives on its own page." No competitor data. | `.../3d00bd21ed6a8165b1f4d3520940b65a` |
| 12 | "Content Engine Tool" has no typography content; closest is "caption and hook devices" as a derived Reel field. | `.../3d00bd21ed6a800fb0ffda652e539ef1` |

**Caution on this evidence.** Every reel page carries `Frame observation: NOT_VIEWED` /
`Frames: MISSING_SOURCE_MEDIA`. The observations come from contact-sheet stills, not the
videos, and the pages say a still "shows composition, not delivery". The two biggest
outliers (@hamza_automates 156x median, @rence_ur_hands 322x median) had 8 and a handful
of samples reviewed. Treat as direction, not as measurement.

**Answers to the brief's questions:** weights — not recorded anywhere; case — caps, by
habit, in 70/70 of our own planned strings; families per cover — one, no second family
observed; italic serif accent — **no, never observed in this niche**; highlight bars —
no, only one instance of red annotation. Kallaway's italic serif and glow are his devices,
not the niche's, and both are named tells in `composition/not-this.md` (items 12 and 7).

**One conflict to flag.** The brief asked for a 12 px Oxide bar behind the key phrase, and
the sheet shows it. It breaks two of our own rules: `tokens.json` says Oxide is "KILL,
broken, risk. Nothing else", and `composition/rules.md` §3 says "build hierarchy with size
and weight only, never with colour". `not-this.md` item 12 also bans a single word in a
headline set in a different colour. Recommendation: keep the Kallaway *structure*, drop
the bar, and carry the emphasis on size and weight, which is what the weight ladder in the
sheet demonstrates.

## 4 · Shortlist and rejections

Shortlisted five: Archivo, Saira SemiCondensed, Big Shoulders Display, Chakra Petch,
Familjen Grotesk. Also measured: Archivo Black, Archivo at seven widths, Saira at five
widths, Saira Condensed, Barlow Condensed, Anton, Unbounded.

| Rejected | Reason |
|---|---|
| Inter, Roboto, Open Sans, Lato, Geist, Space Grotesk, Instrument Serif | Named tells, `lint-rules.json#default-sans-fonts` |
| Montserrat, Poppins | Geometric-circle skeleton, directly against mark rule 3; overused |
| Anton | 22.5 ch, good width — but one weight only, so no hierarchy without colour (breaks `composition/rules.md` §3); and the default face of creator thumbnails |
| Bebas Neue | Caps only, no lowercase for the caption word; single weight |
| Oswald | Rounded shoulders, softened terminals, heavily overused |
| Unbounded | 13.9 ch at 96 px — needs 66.7 px to fit 20 chars, wrecks the whole size scale |
| Archivo Black (static) | 16.4 ch; too wide, single weight |
| Barlow Condensed | Rounded corners and soft joins, against mark rules 3 and 4 |
| Chakra Petch | Clipped corners fit the mark, but tops out at Bold 700 (stem too light vs the mark's 0.239) and reads as gaming/tech |
| Familjen Grotesk | Tops out at 700; humanist quirks (angled `t`, flared `a`) fight the flat facets |
| Sora, Manrope, Plus Jakarta, Public Sans, Red Hat Display, Hanken, Schibsted, Bricolage | Soft or rounded, generic SaaS grotesks; none echo the flat facets |
| Rajdhani, Michroma, Syne | Rajdhani too light, Michroma single-weight mono-width, Syne too eccentric |

## 5 · The three candidates

All OFL 1.1, Latin plus more, from the Google Fonts GitHub repo
(`raw.githubusercontent.com/google/fonts/main/ofl/<family>/`). Downloaded with their
`OFL.txt` into `assets/fonts/candidates/<family>/`. The `.instance.ttf` files were cut
from the variable fonts with `fontTools.varLib.instancer` and are what the sheet renders.

| Candidate | Files | Source |
|---|---|---|
| **Saira SemiCondensed** Bold 700 / ExtraBold 800 / Black 900 | `saira-semicondensed/SairaSemiCondensed-{Bold,ExtraBold,Black}.ttf` | `ofl/sairasemicondensed/`, Omnibus-Type |
| **Archivo** variable wght 100–900, wdth 62–125 (+ ExtraBold at wdth 85 instance) | `archivo/Archivo[wdth,wght].ttf`, `Archivo-ExtraBold-wdth85.instance.ttf` | `ofl/archivo/`, Omnibus-Type |
| **Big Shoulders Display** variable wght 100–900 (+ ExtraBold instance) | `big-shoulders-display/BigShouldersDisplay[wght].ttf`, `BigShouldersDisplay-ExtraBold.instance.ttf` | `ofl/bigshouldersdisplay/`, XOTypeCo |

### Measurements

fontTools advance widths, summed over three sentence-case hooks, in an 888 px column.
"20 ch size" is the size at which a 20-character line exactly fills 888 px — the
`tokens.json#measure.hook-chars` lint constant.

| Face | avg adv (em) | ch / 888 px at 96 px | 20 ch size | caps: ch at 96 px / 20 ch size | cap ht | x-ht |
|---|---|---|---|---|---|---|
| IBM Plex Sans Cond Bold (current) | 0.4352 | **21.3** | 102.0 px | 17.7 / 84.8 px | 0.698 | 0.525 |
| Saira SemiCondensed Black | 0.4354 | **21.2** | **102.0 px** | 18.6 / 89.3 px | 0.688 | 0.510 |
| Archivo ExtraBold wdth 85 | 0.4393 | **21.1** | 101.1 px | 17.0 / 81.5 px | 0.686 | 0.526 |
| Big Shoulders Display ExtraBold | 0.3839 | **24.1** | 115.7 px | 23.8 / 114.4 px | 0.800 | 0.600 |

Reconciles with `research/type-metrics.md` §1, which measured 21 chars/line for Plex Sans
Condensed Bold at 96 px with -0.01em tracking; the table above is untracked, so all four
faces are compared on the same basis. §3 of that file also fixes the phone size: a 96 px
hook on a 1080 canvas renders at 34.67 CSS px in-feed, which is the 34 px row on the sheet.

### Why each one

**Saira SemiCondensed Black.** The skeleton is the mark's skeleton: flat-sided bowls on
`o`, `e`, `s`, joins that meet at hard mitres, terminals cut horizontally, counters that
are near-rectangles. It is the only shortlisted face whose curves are visibly straightened
rather than merely tightened, which is exactly what the folded-facet construction of the
mark does. Weight 900 gives a stem close to the mark's 0.239 ratio; 700 and 800 give a
three-step ladder so hierarchy runs on size and weight alone. Static files, no variable
axis for Remotion, Figma or Instagram tooling to mishandle.

**Archivo ExtraBold, width 85.** A cleaner, more neutral squarish grotesk with a `wdth`
axis, so the measure can be tuned per canvas instead of per size. Slightly rounder bowls
than Saira, so it ties to the mark less tightly, but it is the more comfortable long-form
face and would carry a website as well as covers. Cost: a variable axis in the pipeline.

**Big Shoulders Display ExtraBold.** The most chiselled of the three — diagonal-cut joins
and a genuinely faceted feel, closest in *attitude* to the mark. It buys 13 percent more
characters per line. But cap height 0.800 against Plex's 0.698 means every vertical size
token has to be retuned, and at 34 CSS px on a phone the tight apertures start to close up.
Keep as the poster/limited-use option, not the system default.

## 6 · Recommendation

**Saira SemiCondensed Black for display, with Bold 700 and ExtraBold 800 available.**

Strongest reason: it is the only candidate that is simultaneously the closest geometric
match to the mark and metrically a drop-in. 21.2 characters per 888 px line at 96 px
against Plex Sans Condensed Bold's 21.3 — within 0.5 percent. The 20-character lint
constant, the 96 px hook size and every existing size token stay exactly as they are. And
because Saira's caps are *narrower* relative to Plex's (18.6 ch vs 17.7 ch at 96 px), the
all-caps convention already running in the ten shooting cards gets 5 percent more room,
not less.

Second reason: it is the answer to the niche findings rather than to Kallaway. The niche
runs one headline, one family, no italic accent and no highlight bar; hierarchy comes from
short caps labels. A face with a real 700/800/900 ladder and a rectangular skeleton does
that job. Anton and Bebas — the faces this niche drifts to — cannot, because they have one
weight.

## 7 · Token changes

```jsonc
// tokens/tokens.json
"font.family.display.$value": [
  "Saira SemiCondensed",          // was: IBM Plex Sans Condensed
  "IBM Plex Sans Condensed",      // fallback, near-identical metrics
  "Arial Narrow",
  "sans-serif"
]
"font.weight": add "extrabold": 800, "black": 900   // display ladder, 700 stays for body
```

- **No size adjustment.** 20 characters fill 888 px at 102.0 px in both Saira SemiCondensed
  Black and Plex Sans Condensed Bold. The hook stays at 96 px.
- If the hook is ever set in **all caps**, the ceiling is **88 px** (20 caps characters fill
  888 px at 89.3 px). Plex's ceiling was 84.8 px, so this is a gain.
- Saira's x-height is 0.510 against Plex's 0.525, 2.9 percent smaller. Optional optical
  correction: set display at 99 px where it sits directly beside Plex Sans body text. Not
  needed on covers, where nothing sits beside it.
- `lint-rules.json#font-outside-plex` and `default-sans-fonts` must be updated to admit
  Saira SemiCondensed for display only; body and labels stay Plex, so the rule becomes
  per-role rather than per-file.
- Latin only, matching the current display token. Saira has no Cyrillic in the
  SemiCondensed cut, same constraint as Plex Sans Condensed — Cyrillic keeps falling back
  to Plex Sans, which is already the documented behaviour.
- Hand Max the three static TTFs plus this file: `studio/remotion/src/Composition.tsx` and
  the previs SVG generators still write `Arial` / `Helvetica`.
