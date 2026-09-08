# M2 Lab palette

Generated from tokens/tokens.json. Do not edit.

## Base colours

| Token | Hex | Description |
|---|---|---|
| `color.base.paper` | `#E4E9EA` | Primary surface. Covers, carousels, documents, avatar |
| `color.base.ink` | `#0C1D1D` | Text on Paper. Dark surface for Reel covers and plates |
| `color.base.signal` | `#7DD774` | The mark, KEEP, lit data on Ink. Never text. Never on Paper except inside the mark |
| `color.base.oxide` | `#BB4347` | KILL, broken, risk. Nothing else. On Ink only as a 4 px outline or larger |
| `color.base.blueprint` | `#1E4A80` | Diagrams, leader lines, arrows, second chart series, structural fills. Paper surfaces only. Darkened 8 Sep (was #1E4A80, Misha: more focused and contrast) |
| `color.base.graphite` | `#5C6565` | Secondary text and labels on Paper. On Ink only for muted grid lines |
| `color.base.rule` | `#BEC6C7` | Hairline on Paper |

## Semantic aliases

| Token | Resolves to | Hex | Description |
|---|---|---|---|
| `color.surface.primary` | `color.base.paper` | `#E4E9EA` | Default surface. Paper-first is the decision that moves us off the dark-plus-one-accent cluster |
| `color.surface.dark` | `color.base.ink` | `#0C1D1D` | Reel covers, caption plates, Verdict Card on video |
| `color.surface.plate` | `color.base.ink` | `#0C1D1D` | Plate under text placed over video or photo |
| `color.text.on-light` | `color.base.ink` | `#0C1D1D` |  |
| `color.text.on-dark` | `color.base.paper` | `#E4E9EA` |  |
| `color.text.secondary` | `color.base.graphite` | `#5C6565` | On Paper only. 4.89:1 |
| `color.text.secondary-on-dark` | `color.base.rule` | `#BEC6C7` | Secondary text and labels on Ink. Graphite on Ink is 2.9:1 and fails text |
| `color.accent.data` | `color.base.signal` | `#7DD774` | Only on Ink and only on data or the mark |
| `color.accent.alert` | `color.base.oxide` | `#BB4347` | Only what is broken |
| `color.accent.structure` | `color.base.blueprint` | `#1E4A80` | Diagram lines, arrows, process boxes on Paper only. On Ink diagrams are drawn in Paper lines |
| `color.line.on-light` | `color.base.rule` | `#BEC6C7` |  |
| `color.line.on-dark` | `color.base.rule` | `#BEC6C7` | Lines and leader lines on Ink. Graphite on Ink fails the 3:1 graphic threshold |
| `color.line.diagram` | `color.base.blueprint` | `#1E4A80` |  |
| `color.line.on-dark-muted` | `color.base.graphite` | `#5C6565` | De-emphasised grid lines on Ink only, never for meaning |
