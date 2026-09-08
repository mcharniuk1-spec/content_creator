# M2 Lab typography rules

Two families, five cuts, five roles. Sizes come from `tokens/tokens.json`; the measurements behind them are in `research/type-metrics.md` and `research/heading-font.md`, run against the real font files.

## 1. Family and cuts

| Use | Cut | Token | File |
|---|---|---|---|
| Display, hook and title | Saira SemiCondensed Black 900 | `font.family.display`, `font.weight.display` | `assets/fonts/ttf/SairaSemiCondensed-Black.ttf` |
| Display, secondary lines | Saira SemiCondensed ExtraBold 800 | `font.family.display`, `font.weight.extrabold` | `assets/fonts/ttf/SairaSemiCondensed-ExtraBold.ttf` |
| Body | IBM Plex Sans Regular 400 | `font.family.text`, `font.weight.regular` | `assets/fonts/ttf/IBMPlexSans-Regular.ttf` |
| Subtitles, emphasis | IBM Plex Sans SemiBold 600 | `font.family.text`, `font.weight.semibold` | `assets/fonts/ttf/IBMPlexSans-SemiBold.ttf` |
| Labels, numbers, chips | IBM Plex Mono Medium 500 | `font.family.mono`, `font.weight.medium` | `assets/fonts/ttf/IBMPlexMono-Medium.ttf` |

- Saira SemiCondensed replaced IBM Plex Sans Condensed Bold for display on 8 Sep 2026 (`research/heading-font.md`). Its flat-sided bowls and horizontally cut terminals match the mark's mitred, faceted geometry, where the old Condensed cut read rounder and thinner. It also holds 21.2 characters per 888 px line at 96px against Plex Condensed's 21.3, so every size token and the 20-character lint constant carry over unchanged.
- IBM Plex Sans Condensed now appears only as the fallback cut inside `font.family.display`; it is never chosen as a cut on its own.
- Load woff2 from `assets/fonts/woff2/` for web and Remotion, ttf for Figma, same metrics. Licence for Saira: SIL OFL, `assets/fonts/LICENSE-OFL-Saira.txt`. Licence for Plex: `assets/fonts/LICENSE-OFL.txt`.

## 2. Roles

| Role | Token | Size | Leading | Tracking | Weight | Case | Max chars per line | Max lines | Used on |
|---|---|---|---|---|---|---|---|---|---|
| Hook | `size.hook.default` | 96px | 1.03 | -0.01em | Black 900 SemiCondensed | Sentence | 20 | 3 | Covers, first carousel slide, reel opening frame |
| Hook, maximum | `size.hook.max` | 104px | 1.03 | -0.01em | Black 900 SemiCondensed | Sentence | 20 | 2 | Short hook, three words or fewer |
| Hook, 4:5 fallback | `size.hook.fallback-4x5` | 84px | 1.03 | -0.01em | Black 900 SemiCondensed | Sentence | 20 | 4 | 1080x1350 only, manual escape hatch |
| Title | `size.title.default` | 72px | 1.03 | -0.01em | ExtraBold 800 SemiCondensed | Sentence | 20 | 2 | Carousel slide titles, statements, lower-third names |
| Body, lead | `size.body.lead` | 52px | 1.35 | 0em | Regular 400 | Sentence | 38 | 4 | Opening paragraph of a statement slide |
| Body, default | `size.body.default` | 46px | 1.35 | 0em | Regular 400 | Sentence | 38 | 6 | List slides, proof lines, carousel body |
| Body, small | `size.body.small` | 42px | 1.35 | 0em | Regular 400 | Sentence | 38 | 8 | Sources, footnotes, dense list slides |
| Subtitle | `size.caption.default` | 40px | 1.2 | 0em | SemiBold 600 | Sentence | 38 | 2 | Burned-in subtitles on reels and stories |
| Label | `size.label.default` | 36px | 1.0 | 0.16em | Mono Medium 500 | Caps | 20 | 1 | Format tags, verdict chips, axis labels |
| Label, small | `size.label.small` | 32px | 1.0 | 0.16em | Mono Medium 500 | Caps | 20 | 1 | Episode numbers and metadata only |

A statement slide may set its title in Plex Sans SemiBold 600 at the same `size.title.default` 72px instead of the display family, with the same size, leading, tracking and max chars. Title borrows the hook's leading and tracking; no separate title token exists.

Set hooks and titles in sentence case by default on screen, and reserve caps for tags and stickers only. The niche's own caps habit is noted in the research, but our hierarchy comes from size and weight, not case.

## 3. Hook

- Write 6 to 8 words on 9:16 (`measure.hook-words-reel` 8) and 6 words on 4:5 (`measure.hook-words-4x5` 6), because the 4:5 band leaves only 34 px of slack at four lines.
- Hold every line to 20 characters (`measure.hook-chars` 20), measured against the 888 px text column; this is the binding constraint, not the word count.
- Cut words when the hook does not fit, and keep the size at or above `size.hook.min` 90px.
- Use `size.hook.fallback-4x5` 84px only on 1080x1350, and only when a specific hook cannot be shortened to 6 words.
- Set the hook left-aligned on the grid with the 24 px indent (`frame.indent`), never flush to the guide and never centred [Swiss grid].
- Draw one 4 px rule (`stroke.emphasis`) under the hook block as the single permitted ornament on a cover [engineering drawing].
- Put the key phrase of a hook on a plate when it needs a second beat of attention: an Ink plate with Paper text on Paper surfaces, a Signal plate with Ink text on Ink surfaces, an Oxide plate only when the phrase names something broken. The plate is a shape behind the words, not a colour change to the text, so it does not count as colour hierarchy. Never set the phrase in italics or in a second family.

## 4. Body and subtitles

- Use `size.body.default` 46px as the working size, `size.body.lead` 52px for an opening paragraph, and `size.body.small` 42px for sources and dense lists.
- Hold every body line to 38 characters (`measure.body-chars` 38) in the 888 px column.
- Set burned-in subtitles at `size.caption.default` 40px SemiBold, 2 lines, Paper text on an Ink plate with 24 px padding on all four sides.
- Carry emphasis by moving one word from SemiBold to Bold, and keep the line one colour and one size [Swiss grid].

## 5. Labels

- Set every label in Plex Mono Medium, caps, at `tracking.label` 0.16em and `leading.label` 1.0.
- Use `size.label.default` 36px for format tags and chips, and `size.label.small` 32px only for episode numbers and metadata.
- Write a format tag as the format name, a slash, and the episode number, for example `RADAR / 04`, placed on its own grid position and held there for the whole piece.
- Draw KEEP, KILL and TEST chips at `chip.width` 160px by `chip.height` 56px with `chip.pad-x` 24px and `chip.gap` 16px; Plex Mono is monospaced, so the three labels match in width.

**Label against the eyebrow tell.** A tracked-out caps line sitting above every heading as decoration is a named generated-page tell and does not appear here [not-this.md A10]. Our labels are a different object: a format tag with a number, an axis label or a verdict chip, each on its own grid slot and each appearing once, because it identifies the frame.

## 6. Numbers

- Set every number in Plex Mono, so figures line up in a column and read as measurements [oscilloscope].
- Give every number its WAS, NOW or SAVED label at `size.label.default` 36px, including numbers that are part of a captured screen; a bare number does not ship [oscilloscope].

## 7. Legibility, measured

Reel viewed in feed on a 390 px phone, scale 0.3611 from the 1080 px canvas:

| Role | Size | On-phone CSS px |
|---|---|---|
| Hook | 96px | 34.67 |
| Body lead | 52px | 18.78 |
| Body default | 46px | 16.61 |
| Body small | 42px | 15.17 |
| Subtitle | 40px | 14.44, clears the 14 px subtitle floor |
| Label | 36px | 13.00, clears the 12 px floor |
| Label small | 32px | 11.56, the smallest size the system allows |

- Treat the 3:4 grid tile as a visual frame, not something to read: even a 104px hook reaches only 8.40 CSS px of cap height there, below the 9 px bar. Shape, surface and the mark carry it.
- These CSS px facts hold unchanged under Saira: it was measured at 21.2 characters per 888 px line at 96px (`research/heading-font.md`), within 0.5 percent of the old Plex Condensed cut, so the sizes and the lint constants above stand as they are.

## 8. Punctuation

- Write published copy with commas and full stops, and keep long dashes out of it.
- Join meta information with a slash and a space; middle dots stay out [not-this.md A11].
- End a button with its own words; arrow glyphs stay out of text [not-this.md A13].
- Set an emphasised word in a heavier weight of the same face, never in italic and never in a second colour [not-this.md A12].

## 9. Reject if

- A size, leading or tracking value appears that is not in `tokens.json`.
- A hook or title line runs past 20 characters, or a body line past 38.
- A hook on 4:5 runs past 6 words, or drops below 90px outside the 4:5 escape hatch.
- A subtitle is set below 40px, or runs to three lines.
- A label is set below 32px, or set in a face other than Plex Mono.
- A caps label sits above a heading as decoration rather than as a format tag on its slot.
- A number appears without WAS, NOW or SAVED.
- A hook or title is set in caps rather than sentence case, outside a tag or a sticker.
- A key-phrase plate is drawn in a colour other than Ink, Paper or Signal, or Oxide on a phrase that is not about something broken.
- Any text is centred, or set flush to the guide without the 24 px indent.
- A long dash, a middle dot or an arrow glyph appears in on-screen copy.

## Traceability

- [Swiss grid] Left alignment with a visible indent; hierarchy by size and weight; emphasis by weight.
- [engineering drawing] The 4 px rule under the hook as the only ornament; labels pulled off the object.
- [oscilloscope] Numbers set in Mono and framed as WAS / NOW / SAVED.
- [checklist] One line per item; a subtitle line never wraps into a third line.
- `research/heading-font.md` The Saira SemiCondensed decision, mark geometry match and the character-per-line measurement that keeps every size token unchanged.
- `orchestration/LOG.md`, 8 Sep 2026 iteration 2, the typeface decision and the key-phrase plate as the approved highlight device, in place of an italic accent or a glow.
