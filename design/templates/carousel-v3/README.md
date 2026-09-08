# Carousel template, version 3

Nine slide layouts in one template. Canvas 1080x1350 (`canvas.carousel`), placement `carousel`.
Render: `node templates/render.mjs templates/carousel-v3` from the repo root; contact sheet in
`contact.png`. Version 2 stays as it is: this is a new folder, not an edit of it. Each example
sets one of `is_cover`, `is_statement`, `is_list`, `is_isotype`, `is_before_after`, `is_scheme`,
`is_proof`, `is_verdict`, `is_next` to `"1"`. Chrome: `tag` top left on the indent, one 16 px
`page` square per slide bottom left, `mark` `"1"` for the mono Ink mark bottom right. The cover
drops the squares and sets `counter` instead, `1 / 9` in Mono. **Mark exception:** on the cover
the foot of the slide is the face photo, so the mark moves to the top right of the content area,
on the tag line, at x 888, y 96, 96 by 96. The other eight types keep it bottom right at x 888,
y 1158; `manifest.json` declares the cover box and records the other one in a note on the slot.
The band is x 96 to 984, y 196 to 1094, so 888 by 898: objects on the column guides (96, 324,
552, 780), text on the 24 px indent (x 120), nothing across x 48 or x 1032. The nine examples
fill 94 to 100 per cent of it, measured in the template and written into the title of each
rendered file; the cover is the 94, because its band content stops at y 1041 and the face takes
the foot from y 1050.

## What changed from v2

Every slide carries an object now, not type alone. Sticker components are rebuilt in the
template at 1:1 so strokes stay 2 px and 4 px: 05, 15, 19, 20, 21, 27, 28, 36, 37, 44, 45, 50.
Five slides hold a screenshot placeholder, a hairline frame with its Mono caption in brackets,
to paste a real capture into. The cover takes the reel cover structure: two title lines with the
key phrase on an Ink plate, then the visual, then the caption word, then the presenter. The
presenter is a full-width band, 1080 by 300 at y 1050..1350, edge to edge because it is the
photo, with `[FACE: chest up, centred]` in Mono inside it; `manifest.json` declares only its
Zone A part. The screen card shrinks to 888 by 420 to fit between the title rule and the
caption, and `caption` and `counter` sit under it on the 24 px indent with `space.3` gaps.

## Slots per type

| Type | Slots |
|---|---|
| cover | `hook` (6 words, 20 chars a line), `plate_line` (the hook line that sits on the plate), `screen_title`, `files_html`, `caption`, `face`, `counter` |
| statement | `statement` (72 px SemiBold), `quote_1`, `quote_2`, `quote_by`, `source_1`, `source_2` |
| list | `title`, `items_html`: 3 to 5 `<li>`, class `done`, `blocked` or `pending`, `human_step` |
| isotype | `title`, `unit`, `glyph`, `was_count`, `now_count` (10 or fewer), `was_value`, `now_value`, `saved_value` |
| before_after | `shot_before`, `shot_after`, `before_html`, `after_html` (4 rows a column), `broke_label`, `broken` |
| scheme | `current`, `steps_html`, `ai_layer`, `shot_run`, `verdict_text`, `verdict` |
| proof | `shot_proof`, `call_1`, `call_2`, `proof_line` |
| verdict | `vheader`, `verdict` (KEEP, KILL or TEST), `why`, `conditions_html`, `stamp_html` |
| next | `action`, `shot_next`, `phone_cap`, `file_label`, `file_html`, `source_1`, `source_2` |

## Held here

Values from `tokens/out/tokens.css`. Display is Saira SemiCondensed, Black 900 for the cover
hook at 96 px and ExtraBold 800 for titles and numbers at 72 px. No radius, shadow or gradient,
one accent per slide, a number only inside its WAS, NOW or SAVED frame. Asset paths are doubled
because the renderer writes its HTML into `out/`. On an Ink slide the cover plate turns Signal
with Ink text; all nine examples here are Paper. Example copy and its numbers are illustrative,
written for this test, not measured work. To add a type: new `{{#is_name}}` block, its slots in
`manifest.json` with the band box, one example, render, read the PNG.
