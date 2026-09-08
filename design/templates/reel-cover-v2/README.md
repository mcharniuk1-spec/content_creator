# reel-cover-v2

1080x1920, placement `reel`. The reference structure in our palette and type: no glow, no radius, no italic. v1 stays untouched in `templates/reel-cover/`.

## Structure
| Band | y | What sits there |
|---|---|---|
| Tag line | 272 | Format tag on the indent, episode on the third column guide |
| Title | 324 to 586 | Two lines, Saira SemiCondensed Black 96, key phrase on a plate |
| Visual | 610 to 1102 | 840x492, one dominant element plus at most one supporter |
| Caption | 1126 | One lowercase word in the display face, 72 |
| Mark | 1104 to 1248 | 96 px mark with its clear space, bottom right of Zone A |
| Face | 1248 to 1920 | Placeholder frame, centred, secondary in Zone B, photo below |

## Slots
`surface` light (Paper) or dark (Ink). `plate` empty, or `oxide` when the key phrase names
something broken. `tag`, `episode`, `title_before`, `title_key`, `title_after` (`\n` breaks
the line, the key phrase carries the plate), `visual_html` (raw HTML), `caption_word`, `mark`,
`face_frame`. Title: 6 to 8 words, sentence case, 20 characters a line, two lines.

## Composing a visual

**One dominant element.** The visual is the loudest thing on the cover, not a footnote under
the title. Exactly one element carries it, redrawn at 1.5x to 2x of the sticker it came from,
and it fills the band: the composition's painted bounding box covers at least 85 % of the 840
width and 80 % of the 492 height. Under it sits at most one supporting sticker, a callout, a
chip or a badge. Never three equal things.

- Scale by rewriting the inlined SVG, not by wrapping it in a transform: keep the text live,
  move every coordinate, and let strokes go to 3 or 4 px. That thickness is the emphasis, and
  it is the only place the system leaves the 2 px hairline.
- Pick from the stickers that already carry a plate and big type: numbers 21, 22, 23, 25,
  chart and bar cards 31, 32, 35, screens 36, 37, 38, 40, step chain 28, checklist 27, verdict
  chips 16 to 18 at 2x. Big numerals are Saira SemiCondensed Black 900, the display stack in
  tokens.css. Plex Condensed is a fallback in that stack, never the thing you set.
- Contrast is what stops the scroll. On Paper the dominant element gets a full-width Ink plate
  or a 4 px Ink frame, so it reads as an object; nothing light grey ever carries the frame. On
  Ink it gets a 4 px Paper frame with a Paper header strip, and the data inside is Signal:
  a Paper sticker drawn in Ink disappears on Ink.
- Inline the sticker SVG from `stickers/svg/` into `visual_html` and place it with
  `style="left:Npx;top:Npx"` in the 840x492 band. Widen the viewBox to the right when a string
  runs longer than the one it shipped with, and check the render: mono at 40 px runs about
  30 px a character, so a line that fit at 1x will spill off a plate at 2x.
- Shared left edge, a 24 to 32 px gutter between the dominant element and its supporter, one
  accent per frame. The key-phrase plate is a shape behind the words, so it does not spend the
  accent. Oxide is the accent only when something broke, and then Signal stays off the cover.

## Rules held here
Four columns of 204 with 24 gutters inside 96 padding; text on the 96 guide plus the 24
indent, objects on the guide. Title lines carry one `space.4` step of clear space, because the
plate is an object and would otherwise run into the line above. The visual band is 840, not
888: it runs past y 1000, where the 130 px right rail stays empty. Everything with meaning
sits above y 1248; the face placeholder is the only thing in Zone B and continues into Zone C,
because it stands in for the photo.

Render: `node templates/render.mjs templates/reel-cover-v2`. Contact sheet: `contact.png`,
source `contact.html`, six covers at 270x480 over the same covers as 3:4 grid tiles.
