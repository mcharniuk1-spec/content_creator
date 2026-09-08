# M2 Lab iconography rules

Since 8 September 2026 the visible iconography layer is the sticker library (`stickers/`): tags, plates, callouts, cards and chips. Lucide glyphs appear only inside stickers, at the sizes and strokes below. Pick a sticker before drawing a bare icon.

Icons mark a category or a state. They never decorate.

## 1. Set, licence, files

- Set: **Lucide 1.41.0**, ISC licence (`assets/icons/lucide/LICENSE`). Outline only — no
  filled or duotone variants, no emoji as icons.
- Files: `assets/icons/lucide/` (symlink) holds `svg/` (~2066 icons), `sprite.svg`,
  `tags.json`, a webfont. Pull single SVGs from `svg/` — a font glyph can't carry the per-size stroke correction below.
- Find an icon: `python3 assets/icons/find-icon.py <word>`.

## 2. The grid problem and the size scale

Lucide draws on a 24×24 grid with `stroke-width="2"` (1/12 of the icon size). Resizing the `<svg>` scales the stroke with it: `visual stroke = stroke-width × size / 24`. Uncorrected, a 96px icon carries an 8px stroke, heavier than emphasis — so recompute `stroke-width` per size.

| Size | Use | Hairline (2px) stroke-width | Arithmetic |
|---|---|---|---|
| 32 px | inline with text, list markers | 1.5 | 2 × 24 / 32 |
| 48 px | card headers, small tools | 1.0 | 2 × 24 / 48 |
| 64 px | section markers | 0.75 | 2 × 24 / 64 |
| 96 px | hero / cover icon | 0.5 | 2 × 24 / 96 |
| 96 px (emphasis) | one dominant mark only | 1.0 | 4 × 24 / 96 |

Proof: `rules/icon-sheet.png` — row 1 is 8 icons at all four sizes with uncorrected `stroke-width="2"` (stroke thickens with size); row 2 is the same icons with this table (stroke holds at 2px visual at every size).

## 3. Minimum size for phone viewing

Our canvas exports at 1080px wide; on a phone that renders near 390 CSS px, a scale of about 0.36. A 2px canvas hairline becomes **0.72 CSS px** — under the floor for a crisp phone stroke. Hold to **≥3px canvas (≈1.1 CSS px)** instead:

- No icon below **32px** on the canvas — use text or a dot there instead.
- At **32px and 48px**, skip the pure hairline value for the 3px-canvas floor: 32px → stroke-width 2.25 (3 × 24 / 32), 48px → stroke-width 1.5 (3 × 24 / 48).
- At **64px and 96px**, the hairline table in Section 2 already clears the floor.

## 4. Colour

By role, from `tokens.json`, never by hex: on Paper, Ink or Graphite; on Ink, Paper or Graphite. The accent (Oxide) never colours an icon — it only outlines the KILL shape (`color.md` §4). `icon-sheet.png` uses placeholder hex to prove the arithmetic only; `color.md` sets colour policy.

## 5. Alignment

An icon sits on the baseline of the label it accompanies, not centred on the label's line-height box. Align by optical centre, not bounding box — a circle (`clock`) or triangle (`flask-conical`) needs a 1–2px nudge against a square glyph (`file-text`) to look level.

## 6. When an icon is used, and the isotype rule

Only to mark a category or a state — never decoration, never to fill space. At most one icon per line of text. Never show quantity by resizing one icon: repeat one identical glyph at one identical size instead. Three cost units are three identical coin icons, not one big coin — bigger reads as "more important," not "more of."

## 7. Verdict shape chips

Fixed 160×56 px, independent of icon size — shapes, not icons; the verdict lives in the form (`color.md` §5).

| Verdict | Fill | Stroke | Label |
|---|---|---|---|
| KEEP | Ink solid | none | Paper, monospace 36px, centred, 24px side padding |
| KILL | none | Oxide, 4px | Ink, monospace 36px |
| TEST | none | Ink, 2px, dash 12 gap 8 | Ink, monospace 36px |

## 8. Twelve recurring meanings

Full map in `rules/icon-map.json`.

| Meaning | Icon | Meaning | Icon |
|---|---|---|---|
| Process step | `workflow` | Tool | `wrench` |
| Input | `arrow-right-to-line` | Broken | `unplug` |
| Output | `arrow-right-from-line` | Test | `flask-conical` |
| Human review | `user-check` | Keep | `check` |
| Time | `clock` | Kill | `x` |
| Cost | `circle-dollar-sign` | Document | `file-text` |

## 9. Reject if

- A filled or duotone icon, or an emoji standing in for one, appears anywhere.
- `stroke-width` is left at the Lucide default (2) at any size but the native 24px grid.
- An icon under 32px appears on the canvas.
- 32px or 48px uses the pure hairline stroke-width instead of the 3px-canvas floor.
- Oxide colours an icon glyph instead of only outlining a KILL shape.
- A quantity is shown by resizing one icon instead of repeating it.
- More than one icon sits on a single line of text.
- A verdict chip departs from 160×56 px or the stroke table in Section 7.
