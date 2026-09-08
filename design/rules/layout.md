# M2 Lab layout rules

One grid, one indent, one spacing scale. Values from `tokens/tokens.json`; safe zones from `research/instagram-safe-zones.md` sections 1 to 3.

## 1. Canvases

| Canvas | Token | Size | What it is for |
|---|---|---|---|
| Reel | `canvas.reel` | 1080x1920 | Reels and their covers |
| Story | `canvas.story` | 1080x1920 | Stories, same safe zone as Reels |
| Feed portrait | `canvas.feed-portrait` | 1080x1350 | The default feed post, 4:5 |
| Feed tall | `canvas.feed-tall` | 1080x1440 | 3:4 upload, the only size the grid never crops |
| Feed square | `canvas.feed-square` | 1080x1080 | Square posts and swatch sheets |
| Carousel | `canvas.carousel` | 1080x1350 | Every slide of a carousel |
| Avatar | `canvas.avatar` | 1080x1080 | Profile picture, circle cropped |
| Highlight | `canvas.highlight` | 1080x1920 | Highlight covers, circle cropped |

## 2. The grid

- Lay 4 columns (`frame.columns`) of 204 px (`frame.column-width`) with a 24 px gutter
  (`frame.gutter`) inside 96 px side padding (`frame.pad-x`), giving an 888 px text column.
- Snap every element to a column guide and set text 24 px right of it (`frame.indent`), never
  flush [Swiss grid, owner's correction].
- Align everything to the left edge and centre nothing, on any canvas [Swiss grid].
- Take every gap from the 8 px scale (`space.1` 8 through `space.16` 128: 8, 16, 24, 32, 48,
  64, 96, 128) and use no value between the steps.

## 3. Vertical structure

**9:16, Reels and Stories.** Zone A, always safe, runs y 272 (`frame.pad-top-reel`) to y 1248
(1920 minus `frame.pad-bottom-reel` 672); hook, mark, format tag, claim bar and Verdict Card
live there only. Zone B reaches y 1470 and is organic only: burned-in subtitles, nothing else.
The 130 px right rail (`safe.reel.right-rail`) stays empty below y 1000.

```
        x0   x96                                    x984  x1080
  y0    +--------------------------------------------------+
        |  Zone C   Instagram chrome, no content            |
  y272  +==================================================+  Zone A ceiling
        |  format tag  36 px                                |
        |  hook  96 px, up to 3 lines                       |
        |  4 px rule                                        |
        |  proof block, or deliberate empty space           |
 y1000  |- - - - - - - - - - - - - - - - - -+  right rail   |
        |  instrument band                   |  130 px      |
        |  mark 120 px, bottom left          |  kept empty  |
 y1248  +==================================================+  Zone A floor
        |  Zone B   organic only, subtitles to y 1470       |
 y1470  +--------------------------------------------------+
        |  Zone C   caption, action buttons                 |
 y1920  +--------------------------------------------------+
```

**4:5, 3:4 and 1:1.** Pad 96 px all round (`frame.pad-x`, `frame.pad-y-feed`). Keep what must
survive the 3:4 profile grid inside the crop margins: 34 px per side on 4:5
(`safe.feed-portrait.grid-crop-side`), 135 px per side on 1:1
(`safe.feed-square.grid-crop-side`), none on 3:4, which the grid shows whole.

**9:16 as a grid tile.** The tile keeps y 240 to 1660 (`safe.reel.grid-crop-top` 240,
`safe.reel.grid-crop-bottom` 260); Zone A already sits inside it.

**Circle crops.** Keep avatar and highlight content 54 px (`safe.circle-inset`) inside the 1080 square, and a highlight subject inside the centred 1080x1080 of its 9:16 canvas.

## 4. Slot map, standard cover

| Slot | Position |
|---|---|
| Format tag | Top left of Zone A, on the indent x 120, y 272, 36 px Mono caps; the episode sits on the third column guide, x 576 |
| Title | y 324 to 586, on the indent, two lines of Display 96, 20 characters a line; the key phrase sits on a plate, Ink on Paper and Signal on Ink, Oxide only when the phrase names something broken |
| Visual band | x 96, y 610 to 1102, 840x492, on the column guide. One dominant element rebuilt from a sticker at 1.5x to 2x, painted box covering at least 85 per cent of the width and 80 per cent of the height, plus at most one supporting sticker |
| Caption word | y 1126, on the indent, one lowercase word in the display face at 72 px |
| Mark | Bottom right of Zone A, a 96 px mark inside a 144 px box at x 780, y 1104, so its clear space lands on the Zone A floor y 1248 |
| Face | From y 1248 to the bottom edge, the placeholder centred at x 248, 584 wide. Secondary, the only thing in Zone B, and it continues into Zone C because it stands in for the photo |
| Verdict Card | Instrument band, the 888 column on the 96 guide, card bottom on y 1000; chips 160x56 (`chip.width`, `chip.height`) |
| Claim bar, lower third | Instrument band, left on the indent, one line per beat; the lower third is two lines, name over role |
| Subtitles | Zone A floor for cross-posted pieces, down to y 1470 when organic only |

- Everything carrying meaning sits above y 1248, the top 65 per cent of the frame. The face is
  the exception, and it sits there because the caption, the handle and the action rail overlap
  that band and a face is not information [Swiss grid].
- The title block always reserves two lines, so the visual band holds its position whatever the
  title says; the band is 840 and not 888, because it runs past y 1000 where the 130 px right
  rail stays empty [engineering drawing].
- Show one instrument at a time in the band below y 1000, so the claim bar, the Verdict Card
  and the lower third never share a frame [oscilloscope]; the mark and the format tag stay on
  their slots for the whole piece [Swiss grid].

## 5. Carousel

- Build 2 to 10 slides, all at 1080x1350 (`canvas.carousel`) and all identical in pixel size,
  because the first slide sets the ratio and later slides are cropped to match without warning.
- Place the page indicator bottom left on the indent as Isotype dots: one identical 16 px dot
  per slide (`space.2`), 8 px apart (`space.1`), current filled, rest outlined [Isotype].
- Use nine slide types and no eighth: cover, statement, list, Isotype data, before and after,
  verdict, next step.

## 6. Elements on the grid

- Snap images and screenshots to column edges, top edge on a grid line, scaled down from
  native capture only [Swiss grid, engineering drawing].
- Set a label outside the object it names and connect it with a 2 px leader line
  (`stroke.hairline`) ending in a dot exactly on the point [engineering drawing].
- Give every list one item per line, and never wrap an item across two lines [checklist].

## 7. Surfaces of shapes

- Draw every corner square and every plate flat: `banned.radius` 0px, `banned.shadow` none,
  `banned.gradient` none.
- Use two stroke widths only: 2 px (`stroke.hairline`) for lines, leader lines and icon
  strokes, 4 px (`stroke.emphasis`) for a KILL outline and the rule under the hook. The dashed
  TEST outline uses `stroke.dash` 12px 8px at hairline width.

## 8. Reject if

- An element sits off the 8 px scale or off a column guide.
- Text, the mark or a verdict crosses out of Zone A on a 9:16 canvas.
- Anything other than a subtitle sits in Zone B.
- Content sits in the 130 px right rail below y 1000.
- Text is centred, or set flush to its guide without the 24 px indent.
- A carousel mixes slide sizes, or runs to fewer than 2 or more than 10 slides.
- A radius, a shadow or a gradient appears on any shape.
- A stroke is used at a width other than 2 px or 4 px.
- A leader line ends without a dot, or a label sits on the object it names.

## Proposed additions

- `safe.reel.right-rail-top: 1000px`. The rail rule needs a start line as well as a width:
  `safe.reel.right-rail` gives 130 px but no y value, and y 1000 comes from the zone model
  decision of 8 September 2026.

## Traceability

- [Swiss grid] Four columns, left alignment with a 24 px indent, nothing centred, fixed slots.
- [engineering drawing] Labels outside the object, leader lines ending in a dot, flat shapes.
- [oscilloscope] One callout at a time; the frame changes only when the evidence changes.
- [Isotype] Page indicator as repeated identical dots, never a scaled one.
- [checklist] One item per line in every list block.
