# M2 Lab colour rules

Seven colours, one source: `tokens/tokens.json`. Contrast figures are computed in
`research/palette-options.md`, variant A (Oxide, Paper-first).

## 1. The seven colours

| Role | Token | Hex | What it does | What it never does |
|---|---|---|---|---|
| Paper | `color.base.paper` | `#E4E9EA` | Carries the primary surface of covers, carousels, documents and the avatar. | Never sits as a text colour on a light surface. |
| Ink | `color.base.ink` | `#0C1D1D` | Sets all text on Paper, and forms the dark surface for Reel covers, plates and the Verdict Card. | Never becomes the default page ground for feed and carousel work. |
| Signal | `color.base.signal` | `#7DD774` | Lights data and the KEEP state on Ink, and colours the mark. | Never appears as text, and never appears on Paper outside the mark. |
| Oxide | `color.base.oxide` | `#BB4347` | Marks what is broken, at risk, or KILL. | Never carries a mood, a heading, a chart series or a decorative fill. |
| Blueprint | `color.base.blueprint` | `#1E4A80` | Draws structure: arrows, boxes, leader lines, the second chart series. | Never states a verdict or a value judgement. |
| Graphite | `color.base.graphite` | `#5C6565` | Sets secondary text and metadata on Paper; on Ink only muted grid lines. | Never sets text on Ink (2.9:1). Never sets a hook, a claim or a number. |
| Rule | `color.base.rule` | `#BEC6C7` | Draws the hairline divider on Paper. | Never carries text or an icon stroke. |

## 2. Surface rule

- Build every artefact on Paper first, because the light surface is what takes the system off
  the near-black-plus-one-accent cluster [Swiss grid; palette decision 8 Sep 2026].
- Reserve Ink surfaces for three jobs: Reel covers, flat plates sized to a text block placed
  over video or photo, and the Verdict Card on video [engineering drawing].

| Artefact | Surface ratio |
|---|---|
| Feed cover, 4:5 and 1:1 | Paper ground throughout; Ink appears only as type, rule and the mark. |
| Reel cover, 9:16 | Ink ground permitted in full; Signal is allowed here and nowhere else. |
| Carousel, 10 slides | Paper on every slide; at most one Ink slide, and it is the verdict slide. |
| Story | Paper ground by default; Ink appears only as a plate under text over footage. |
| Avatar | Paper ground with the monochrome Ink mark, since the colour mark returns 1.45:1 on Paper. |
| Highlight cover | Paper ground, Ink icon, content inside the 54 px circle inset (`safe.circle-inset`). |

## 3. Allowed pairs

**Text pairs** (need 4.5:1)

| Foreground | Background | Ratio |
|---|---|---|
| Ink `color.text.on-light` | Paper | 14.18:1 |
| Paper `color.text.on-dark` | Ink | 14.18:1 |
| Graphite `color.text.secondary` | Paper | 4.89:1 |
| Rule `color.text.secondary-on-dark` | Ink | 10:1 |

**Graphic pairs** (need 3:1)

| Foreground | Background | Ratio |
|---|---|---|
| Signal `color.accent.data` | Ink | 9.80:1 |
| Blueprint `color.accent.structure` | Paper | 7.31:1, Paper only (1.94:1 on Ink) |
| Rule `color.line.on-dark` | Ink | 10:1, lines and leader lines on dark |
| Oxide `color.accent.alert` | Paper | 4.28:1 |
| Oxide `color.accent.alert` | Ink | 3.31:1, so use it at `stroke.emphasis` 4 px or wider |

**Forbidden pairs**

| Pair | Reason |
|---|---|
| Signal as text on Paper | 1.45:1. Signal is a fill that carries Ink text on top, never type itself. |
| Oxide as text on Ink | 3.31:1 clears the graphic threshold only, so it stays an outline or a fill, never a letterform. |
| Signal as text anywhere | Signal states data and the mark; letters set in Signal turn an accent into a voice. |

## 4. What each colour means

- Let Oxide mean broken, out of tolerance or KILL, and nothing else in any frame
  [engineering drawing].
- Let Signal mean lit data on a dark field, plus the mark itself [oscilloscope].
- Let Blueprint mean structure: arrows, process boxes, leader lines and second-level fills
  [engineering drawing].
- Build hierarchy with size, weight and position, and let colour carry meaning instead, one
  meaning per colour for the whole piece [Swiss grid].

## 5. Verdict colours

Shape first, colour second. The reader gets the state from the plate before any hue arrives
[checklist].

| Verdict | On Paper | On Ink | Tokens |
|---|---|---|---|
| KEEP | Solid Ink plate, Paper label | Solid Signal plate, Ink label | `verdict.keep.fill`, `verdict.keep.fill-on-dark` |
| KILL | Transparent plate, Oxide outline 4 px, Ink label | Transparent plate, Oxide outline 4 px, Paper label | `verdict.kill.stroke`, `stroke.emphasis` 4px |
| TEST | Transparent plate, Ink dashed outline 2 px, Ink label | Transparent plate, Paper dashed outline 2 px, Paper label | `verdict.test.stroke`, `stroke.hairline` 2px, `stroke.dash` 12px 8px |

## 6. Colour blindness

Machado 2009 at severity 1.0, Oxide against Signal:

| Vision | Oxide reads as | Signal reads as | Lightness gap | Separable by lightness |
|---|---|---|---|---|
| normal | `#BB4347` | `#7DD774` | 0.249 | yes |
| deuteranopia | `#807644` | `#CEBF7A` | 0.239 | yes |
| protanopia | `#625C46` | `#DBC86C` | 0.355 | yes |

- Encode every state in the shape of its frame, so it survives when the hues collapse into one [checklist].

## 7. Why this palette

- The approved 4 September palette carried all three markers of the near-black-plus-one-accent
  cluster that generative models fall into [not-this.md A2].
- The surface moved first: Paper became primary, which removes the cluster silhouette before
  any hue argument is needed.
- Signal stayed green and lost chroma and lightness, so the mark is still recognisable and no
  longer reads as neon.
- Oxide moved 7.2 degrees off vermilion and dropped chroma, so risk reads as a stamped ink.
- Blueprint was added, so the system reads as two accents plus structure rather than one shout.

## 8. Reject if

- A hex value appears that is not in `tokens.json`.
- Ink is used as the ground of a feed post or a carousel slide by default.
- Signal appears as text, or appears on Paper outside the mark.
- Oxide appears on anything that is not broken, at risk, or KILL.
- Oxide sits on Ink thinner than 4 px.
- A heading, a step or a state is distinguished by colour alone.
- A gradient, a shadow or a tint outside the seven colours appears anywhere in the frame.

## Traceability

- [Swiss grid] Hierarchy by size and weight, never by colour; left-aligned Paper-first page.
- [engineering drawing] Red reserved for what is broken; labels outside the object; Blueprint as structure.
- [oscilloscope] Accent reserved for lit data on a dark field.
- [checklist] State encoded in shape, so it survives colour-vision deficiency.
