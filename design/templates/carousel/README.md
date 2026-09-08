# Carousel template

Eight slide layouts in one template. Canvas 1080x1350 (`canvas.carousel`), placement `carousel`.
Render: `node templates/render.mjs templates/carousel` from the repo root; renders in `contact.png`.
Each example sets exactly one of `is_cover`, `is_statement`, `is_list`, `is_isotype`,
`is_before_after`, `is_scheme`, `is_verdict`, `is_next` to `"1"`. Shared chrome on every slide:
`tag` top left on the indent, mono caps 36 (`TEARDOWN / 05`); `page` and `pages` bottom left, one
16 px square per slide filled to the current page [Isotype, checklist], with `swipe` set beside
them on the same line; `mark` set to `"1"` puts the mono Ink mark bottom right at 96 px, 96 px
from both edges.

## The band

Everything between the tag and the page dots is one box: x 96 to 984, y 196 to 1094, so 888 by
898. Every layout is a flex column that fills it. Title or hook at the top, the main block grown
in the middle, the closing line (source, saved, channel, conditions) anchored at the foot. On the
current examples the content spans 90 to 100 per cent of the band height on all eight slides.

## Slots per type

| Type | Slots |
|---|---|
| cover | `hook` (6 words, 20 chars a line, 96 px), `kicker`, `episode` (2 chars), `swipe` |
| statement | `statement` (4 lines at 72 px), `source` |
| list | `title` (72 px), `items_html`: 3 to 5 `<li>`, class `done`, `blocked` or `pending` |
| isotype | `title`, `unit`, `glyph`, `was_count`, `now_count` (10 or fewer), `saved_text` |
| before_after | `before_html`, `after_html` (`<li>`, 4 rows a column), `broken`: one AFTER item, Oxide |
| scheme | `current`, `ai_layer`, `verdict_text` (8 lines each at 46 px), `verdict` |
| verdict | `verdict` (KEEP, KILL or TEST), `why` (2 lines at 52 px), `conditions_html`: 2 or 3 `<li>`, each `<span class="n">01</span><span>text</span>` |
| next | `action` (4 lines at 72 px), `channel` |

## Rules the template holds you to

- Values come from `tokens/out/tokens.css`. Slide titles use `size.title.default` (72 px):
  display family on the list and isotype titles, text family SemiBold on the statement and the
  next action. The cover hook stays at `size.hook.default` (96 px). The one value with no token
  is the 400 px cover figure.
- Text sits on the 24 px indent (x 120), objects on the column guides (96, 324, 552, 780).
  Nothing crosses x 48 or x 1032, so the 3:4 profile grid loses nothing.
- Isotype glyph is 64 px at `stroke-width` 0.75, the 64 px row of `rules/iconography.md`
  section 2. Ten glyphs with 24 px gaps measure 856 px, inside the 888 column, so WAS and NOW
  sit above their rows on the guide rather than beside them. Removed units keep the same glyph
  in Rule grey, with a Blueprint leader line running from the first one down to the saved line
  [Isotype, engineering drawing]. `glyph` picks from the icons inlined in the template script:
  clock, file-text, user, circle-dollar-sign, wrench.
- The list, the before and after columns and the verdict conditions are all ruled with hairlines,
  so a row is a row of a schedule and the rows reach the foot of the band.
- Statement and next carry a 4 px Ink bar on the guide running the band height, so one spoken
  line holds the sheet without a hole under it.
- Verdict is shape first: KEEP filled Ink, KILL 4 px Oxide, TEST dashed 12/8 [checklist]. On this
  slide the shape is the full 888 by 160 field with the word at 96 px.
- The cover figure is the episode number set at 400 px Condensed in Graphite under a hairline at
  the foot of the band. Nothing is set over it. Leave `episode` empty and the block disappears.
- The renderer does not nest `{{#blocks}}`; optional inner slots hide via `.opt:empty` and, where
  a wrapper carries a label, via `:has()`. Asset paths use `../../../` because the renderer
  writes its HTML into `out/`.
- Example copy and its numbers are illustrative, written for this test, not measured work.
- To add a slide type: new `{{#is_name}}` block, its slots in `manifest.json` with the main-band
  box, one `examples/NN-name.json`, render, read the PNG. Never edit an approved type in place;
  a new layout is a new type.
