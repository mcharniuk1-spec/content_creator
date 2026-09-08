# QA — M2 Lab Brandbook v3 (45 pp, A4 landscape, rasterized 72 dpi)

All 45 pages read. Overflow/clipping: none found. Missing images: none (placeholders correctly labelled). Empty/cramped pages: none. Fonts: headings render as one consistent flat-sided, heavy condensed face (Saira SemiCondensed Black/ExtraBold) on every page — no rounder/lighter fallback detected visually. System-violation scan (centred text, rounded corners, shadows, gradients, emoji, arrow glyphs, long dashes in body): none found outside the two approved exceptions.

## Page table

| page | title | issue | severity |
|---|---|---|---|
| 02 | Contents | TOC entry "Personality and the visual formula" (→ p09) does not match p09's actual title/content | blocking |
| 02 | Contents | TOC entry "Editorial filter and cadence" (→ p18) — p18 is titled "The editorial filter" only; cadence content actually lives on p16, not p18 | blocking |
| 01 | Cover | none | none |
| 03 | Part 1 divider | none | none |
| 04 | Purpose and positioning | method chain, role line placement, positioning statement all correct | none |
| 05 | What M2 Lab is, and what it is not | TOC wording differs slightly ("is and is not") | minor |
| 06 | Credibility boundary | none | none |
| 07 | Audience | none | none |
| 08 | What they know, and what they came for | Radar question wording confirmed exact | none |
| 09 | Personality: four traits | title does not match TOC ("...and the visual formula"); confirms only 4 traits, no "Unhurried" | blocking (title/TOC) |
| 10 | Voice: principles 1 to 3 | none | none |
| 11 | Voice: principles 4 to 6 | not separately listed in TOC (reads as continuation of p10 span) | minor |
| 12 | Tone by context | none | none |
| 13 | Sentence patterns | none | none |
| 14 | Naming rules | none | none |
| 15 | Words and constructions we do not publish | TOC shortens title (style-consistent) | minor |
| 16 | Content formats: the three pillars | Teardown question includes "and how" — confirmed; cadence block lives here | none |
| 17 | Structure at 50 to 60 seconds | continuation page, not separately listed in TOC | minor |
| 18 | The editorial filter | owner/champion/user block present; see TOC mismatch above | blocking (title/TOC) |
| 19 | Messaging hierarchy | none | none |
| 20 | The mark | colour mark centred, no background block, no mono-Ink version shown — confirmed correct | none |
| 21 | The mark: what is and is not done with it | continuation, not separately listed in TOC | minor |
| 22 | Part 2 divider | none | none |
| 23 | How the system works | none | none |
| 24 | Composition rules: where things go | "grammar" correctly renamed; matches TOC exactly | none |
| 25 | Colour, the seven values | none | none |
| 26 | Colour rules | continuation of Colour section, not separately listed (consistent w/ doc's own span convention) | minor |
| 27 | Why this palette | none | none |
| 28 | Typography, the specimen | Saira SemiCondensed Black confirmed in spec table | none |
| 29 | Typography rules | continuation, unlisted (consistent convention) | minor |
| 30 | Layout and the grid | none | none |
| 31 | Canvases and the slot map | none | none |
| 32 | Instagram safe zones | none | none |
| 33 | Stickers, the library | "Sixty-five of them" confirmed | none |
| 34 | Sticker placement and glyphs | none | none |
| 35 | Imagery | photo placeholders correctly bracketed, not stock images | none |
| 36 | Motion | none | none |
| 37 | Templates: Reel covers | v2-style covers (title+plate, big visual, face band) confirmed | none |
| 38 | Templates: what goes on top of the video | none | none |
| 39 | Templates: Carousel | nine slide types confirmed (v3) | none |
| 40 | Templates: Profile | none | none |
| 41 | Tokens reference | font.family display = Saira SemiCondensed — correct | none |
| 42 | Gates for agents | matches TOC span "...and the linter" (p42-43 together) | none |
| 43 | The linter | not separately titled in TOC but covered by p42's compound entry | minor |
| 44 | Not this | no Cyrillic, no banned traits found | none |
| 45 | Colophon | **Typefaces section still says "IBM Plex Sans Condensed Bold for display"** — contradicts p28/p41, which correctly specify Saira SemiCondensed Black/ExtraBold for display. Saira is not credited/licensed here either. | blocking |

## Counts

- Blocking: 4 (p02/p09 title-TOC mismatch, p02/p18 title-TOC mismatch, p09 itself, p45 stale typeface description)
- Minor: 8 (p05, p11, p15, p17, p21, p26, p29, p43 — all unlisted/short-titled continuation pages in TOC)
- None: 33

## Fix first

1. **p45 Colophon** — replace "IBM Plex Sans Condensed Bold for display" with Saira SemiCondensed Black/ExtraBold, and add Saira's licence (OFL) alongside IBM Plex's. This is the highest-risk item: it is a durable reference page that currently documents the retired font.
2. **p02 Contents** — retitle the p09 entry to match "Personality: four traits" (or retitle p09 back if "visual formula" content was meant to exist and was dropped).
3. **p02 / p18** — either restore cadence content to p18 or rename the TOC entry to "The editorial filter" to match the actual page.
4. Optional cleanup: TOC does not list p11, p17, p21, p26, p29, p43 individually; harmless if intentional (matches the doc's own "span" convention used for Templates/Colour/Typography), but worth a deliberate decision rather than an accident.
