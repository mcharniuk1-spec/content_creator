# M2 Lab Brandbook — Print QA (50 pages, A4 landscape, 72 dpi render)

Method: read every page image p01–p50 in full, checked against the 7 criteria in the brief. Palette hexes verified pixel-adjacent to the swatch labels on p31. Font checked against known-good p01 baseline (IBM Plex Sans double-storey "a" present throughout, no Arial/Helvetica/Times fallback seen on any page).

| Page | Title (as printed) | Issue | Severity |
|---|---|---|---|
| 01 | M2 Lab / Brand book and design system (cover) | none | none |
| 02 | Contents | No Part-label above title — but this is front matter (nav page), likely intentional, matches p50 pattern | none |
| 03 | Part 1 — Brand book (divider) | none | none |
| 04 | Purpose and positioning | none — TOC page-04 spot check matches | none |
| 05 | What M2 Lab is, and what it is not | none | none |
| 06 | Credibility boundary | none | none |
| 07 | Audience | none | none |
| 08 | What they know, and what they came for | Content fills only ~half the page; bottom is empty white space | minor |
| 09 | Personality: five traits | none | none |
| 10 | The visual formula | none | none |
| 11 | Voice: principles 1 to 3 | none — TOC "Voice principles" page-11 spot check matches | none |
| 12 | Voice: principles 4 to 6 | none | none |
| 13 | Tone by context | none | none |
| 14 | Sentence patterns | none | none |
| 15 | Words and constructions we use | none | none |
| 16 | Naming rules | none | none |
| 17 | Words and constructions we do not publish | none | none |
| 18 | Content formats: the three pillars | none | none |
| 19 | Structure at 50 to 60 seconds | none | none |
| 20 | The editorial filter | none | none |
| 21 | Messaging hierarchy | none | none |
| 22 | Profile system, and where each level is used | none | none |
| 23 | Highlights and pinned posts | none | none |
| 24 | The broadcast channel | Heading reads "M2 Lab — the workshop": uses an em dash, contradicting the book's own rule (p17/p48: "no long dash — use a comma or a full stop"). Also content fills only ~half the page | minor |
| 25 | Governance | none | none |
| 26 | The mark: three versions | none | none |
| 27 | The mark: what is and is not done with it | none | none |
| 28 | Part 2 — Design system (divider) | none | none |
| 29 | How the system works | none | none |
| 30 | Composition rules, the five sources | none | none |
| 31 | Colour, the seven values | Hexes verified: Paper #E4E9EA, Ink #0C1D1D, Signal #7DD774, Oxide #BB4347, Blueprint #33587D, Graphite #5C6565, Rule #BEC6C7 — all 7 match spec exactly | none |
| 32 | Colour rules | none | none |
| 33 | Why this palette | none | none |
| 34 | Typography, the specimen | none | none |
| 35 | Typography rules | none | none |
| 36 | Layout and the grid | none | none |
| 37 | Canvases and the slot map | none | none |
| 38 | Instagram safe zones | none | none |
| 39 | Iconography and the verdict | Icon sheet zoomed and checked: outline glyphs render correctly, no broken-image icons, no emoji | none |
| 40 | Imagery | Placeholder photo frames correctly labelled "[PHOTO: ...]", not swapped for stock — matches Never-rules | none |
| 41 | Motion | none | none |
| 42 | Templates: Reels, cover and verdict card | none — mockups zoomed, KEEP/KILL/TEST chips render correctly | none |
| 43 | Templates: Reels, claim bar and lower third | none | none |
| 44 | Templates: Carousel | none | none |
| 45 | Templates: Profile | none | none |
| 46 | Tokens reference | Dense six-column table but text stays inside margins, no clipping | none |
| 47 | Gates for agents | none | none |
| 48 | The linter | none | none |
| 49 | Not this | none — TOC page-49 spot check matches | none |
| 50 | Colophon | Missing the "PART 2 / DESIGN SYSTEM" mono label above the title — every other Part 2 content page carries it. TOC page-50 spot check matches title/number otherwise | minor |

## Consistency / spot checks performed
- Footer folio increments correctly 02→50 across all content pages; no repeats or skips found.
- 5 TOC spot-checks (Purpose and positioning→04, Voice principles→11, Colour→31, Iconography and the verdict→39, Colophon→50): all 5 match the actual page title and number.
- No rounded corners, drop shadows, gradients, emoji, arrow-as-CTA glyphs, or centred text found on any page.
- Palette on p31 matches the required 7 hexes exactly.

## Summary
- Blocking: 0
- Minor: 3 (p08, p24, p50)
- None: 47
- Fix first: p24 (em dash in a heading contradicts the book's own punctuation rule — easiest to fix, most visible self-contradiction), p50 (add the missing Part 2 label for consistency), p08 (consider tightening layout — noticeably sparse vs. neighboring pages).
