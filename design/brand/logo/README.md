# M2 Lab mark: clear space, size, use

Values come from `tokens/tokens.json`, group `logo` and `color.base`. This file
covers only how to apply the mark; change numbers there, not here.

## Two files and when each is used

| File | Used on |
|---|---|
| `m2-mark-color.svg` | Paper `#E4E9EA` and light photos. The primary version. |
| `m2-mark-mono-paper.svg` | Ink `#0C1D1D`, photo, video, any dark surface. |

The colour mark on Ink is invisible: its silhouette is the same colour as the
background. On any dark surface, always use the mono Paper version instead.

## Colour values inside the SVGs

- `m2-mark-color.svg` uses Ink `#0C1D1D`, Signal `#7DD774`, Paper `#E4E9EA`.
- `m2-mark-mono-paper.svg` uses Paper `#E4E9EA` only.

Geometry is untouchable. Only the colour values follow the tokens; the paths
themselves never change between the two files.

## Clear space

A quarter of the mark's height, kept on all four sides. Nothing enters this
zone: no text, no line, no frame edge, no other logo.

```
        <- 0.25 h ->
      +---------------+
      |   +-------+   |  ^
      |   |  mark |   |  h
      |   +-------+   |  v
      +---------------+
```

Worked examples:
- Mark height 96 px (the cover size token, `logo.size-reel`): clear space is 24 px on every side.
- Mark height 620 px (`logo.size-avatar`): clear space is 155 px on every side.

## Minimum sizes

| Version | Minimum | Below it |
|---|---|---|
| Colour | 32 px wide (`logo.min-width-color`) | switch to mono |
| Mono | 20 px wide (`logo.min-width-mono`) | do not place the mark at all |

The Signal wedge turns to mud below 32 px wide, which sets the colour floor.
Below 20 px the mono version stops reading as the mark, so nothing is placed.

## Placement on standard canvases

- Reel and Story cover (1080x1920): mark height `logo.size-reel`, 96 px, bottom-right of Zone A.
- Feed canvases: mark height `logo.size-feed`, 96 px.
- Avatar (1080x1080 circle): mark height `logo.size-avatar`, 620 px.

On 9:16, place the mark bottom-right, inside Zone A (reel-cover-v2). Use the frame's own
padding (`frame.pad-x` 96 px, `frame.pad-bottom-reel` 672 px) as the origin;
both paddings already exceed the mark's own clear space at 96 px (24 px), so
the clear space is kept for free and no extra margin is added on top of it.

## What is not done with the mark

The mark is always:
- scaled proportionally on both axes, never stretched
- upright, never rotated, tilted, outlined, or boxed in a frame
- one of the two approved versions above, never a third colour
- placed on a flat tone or an Ink plate, never directly on a busy part of a photo
- flat like the rest of the system: no shadow, no glow, no rounded corners

Reject if:
- proportions are not uniform
- the mark is rotated, tilted, outlined, or framed
- a colour outside the two files above is used
- it sits on a busy photo area with no flat tone or Ink plate behind it
- a shadow, glow, or rounded corner has been added

## Withdrawn version

The mono Ink version was withdrawn on 8 Sep 2026. It is not part of the system and
is not used anywhere. The file `m2-mark-mono-ink.svg` stays in this folder, unused.

## Rejected version

An inverse version was rejected on 4 Sep 2026: Misha did not like it visually,
and its function is already covered by the mono Paper version. It lives at
`library/rejected/m2-mark-inverse.md` (rationale) and the matching SVG there.

## Provenance

The supplied SVG was an autotrace of a raster: one black shape, light facets
as holes, no Signal wedge in the file. The mark was rebuilt in layers
(silhouette, facets, wedge), with contours inherited from the trace. If Max
finds the original vector, rebuild the mark from it so the curves are clean
and the wedge is a true shape.

## Wordmark

There is no wordmark. Decision: 8 Sep 2026.

Setting "M2 Lab" as text next to the mark is never used as a substitute logo.
The name appears in copy only, as running text.
