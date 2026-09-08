# M2 Lab stickers

## What a sticker is

A sticker is a small graphic component that carries one job: name a format, mark a
state, point at a step, frame a number, stand in for a screen. It is not an icon and
not an illustration. Lucide glyphs appear only inside a sticker, at glyph size, under
the stroke rule in `rules/iconography.md`.

65 stickers: 50 in 10 families of 5 (tags, highlights, callouts, verdict and state,
numbers, lists, data, screens, people and roles, meta), plus 15 Ink surface variants,
51 to 65, of the structural set. Every file is a plain SVG at its natural canvas size,
drawn for the 1080 px canvas, with live editable text.

Index: `manifest.json`. Proof sheet: `sheet.png`, source `sheet.html`.

## How to place one

- **Grid.** Snap the left edge of a sticker to a guide of the four column grid
  (`tokens.json` `frame.columns`), then push it off the guide by the 24 px indent.
  Nothing is centred and nothing is flush to the guide.
- **Size relative to the canvas.** On the 1080 px canvas: a tag or a chip is 6 to 12
  percent of the canvas height, a card or a screen is 30 to 45 percent, a highlight
  bar spans 60 to 90 percent of the text column. Place at 100 percent scale where the
  file already fits; scale a whole sticker, never one part of it.
- **One accent per frame.** A frame carries either Signal or Oxide, never both, and
  never twice. Blueprint is structure and does not count as an accent.
- **Oxide only for what is broken.** `06-highlight-bar-oxide`, `17-verdict-kill`,
  `20-marker-broke-here` and `56-verdict-kill-ink` are the only Oxide stickers, and
  they only go on a step that actually failed or a call that was actually killed.
- **Surfaces.** `manifest.json` gives `surfaces` per sticker. Signal appears in 01,
  05, 07, 23, 31, 33, 35, 40, 41, 55 and 58, and every one of those is an Ink surface
  sticker, because Signal never appears on Paper outside the mark.
- **Pick the variant by surface, never recolour a sticker by hand.** 11, 13, 14, 15,
  16, 17, 18, 21, 22, 26, 27, 28, 29, 30 and 34 are drawn in Ink and go blind on an Ink
  ground. On Ink, take the matching file 51 to 65 instead: same geometry, same slots,
  lines and text in Paper, secondary text in Rule, muted lines in Graphite, Signal only
  on lit data and the KEEP plate, Oxide only on KILL. Recolouring a sticker in place
  breaks the match with the file it came from and with every frame already published.
- **Numbers.** A number ships inside 21, 22, 23, 25 or with the source plate 50.
  A bare number does not ship.
- **Stacking.** Two stickers in one frame keep a 24 px gutter and share a left edge.
  Three or more in one frame means the frame is doing too much.

## How to edit the text

Every editable string is a `<text>` element with `id="slot-<name>"`. Open the SVG in
any editor and replace the string inside the element. The text is live, not outlined,
so the font stays live and the file stays diffable: body and mono copy stay IBM Plex,
big display words (highlights, numerals) stay Saira SemiCondensed at weight 900. Slot
names per sticker are in `manifest.json` and in the two header lines of each file.

After editing, check the width by eye: plates are sized to the string they shipped
with. A longer string needs the plate widened by the same amount, in the file.

## How to add one

- Add a new file, `svg/<nn>-<name>.svg`, with the next free number. Never edit an
  approved sticker in place: a new variant is a new file, so anything already used in
  a published frame keeps rendering the way it was approved.
- Two header lines at the top of the file: purpose, then slots.
- Palette only, from `tokens/tokens.json`. Strokes are 2 px or 4 px. Dashes are 12 8.
  No radius, no shadow, no gradient, no filter, no emoji, no arrow glyph. A pointer is
  a leader line ending in a square dot.
- Add the entry to `manifest.json`, rebuild `sheet.html`, then run
  `node checks/lint.mjs stickers/` from the repo root and clear every error.
