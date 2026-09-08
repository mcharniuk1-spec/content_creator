# M2 Lab brand book and design system: handoff

State after iteration 2, 8 September 2026. Read this first in a new session; everything else
opens from here. English so agents can load it; the Russian summary is in the chat.

## What exists

One folder, `~/Desktop/m2lab-brand/`, not a git repository.

| Deliverable | Where | Status |
|---|---|---|
| PDF, brand book pages 4 to 21, design system pages 23 to 45, A4 landscape, English | `~/Desktop/M2-Lab-Brandbook.pdf`, source `pdf/` | version 3, QA in `orchestration/QA-pdf-v3.md` |
| Brand book content | `brand/` (8 files; profile, highlights, channel and governance are working files, not in the book) | revised per Misha's review |
| Tokens, 132 values, build, contrast check | `tokens/`, `checks/contrast.mjs` | all pairs pass |
| Rules, one topic per file | `rules/` | typography rewritten for Saira |
| Composition rules (was "grammar") | `composition/` | renamed, plain wording |
| Instagram zone model, overlays, checker | `social/` | unchanged |
| Stickers, 65 SVG components, 11 families | `stickers/` | new in iteration 2 |
| Templates | `templates/` (`README.md` says which is current) | `reel-cover-v2`, `carousel-v3` new; overlays, highlight, avatar re-set in Saira |
| Linter, checklist, contrast | `checks/` | linter accepts `var(--m2-font-family-*)` |
| Router for agents | `SKILL.md` | updated |
| Plan, decisions, QA reports | `orchestration/` | `LOG.md` has both iterations |
| Research | `research/` | plus `heading-font.md` and its sheet |

## Misha's review of version 2 and what was done (8 Sep, iteration 2)

| Page (v2) | Feedback | Done |
|---|---|---|
| 4, everywhere | method step "process map" to "fragmentation"; "one repeated task" to "one repeated workflow" | applied across brand files, stickers, pages |
| 9 | drop "Unhurried" | four traits |
| 10, 15, 22, 23, 24, 25 | delete pages | removed from the book; files kept in `brand/` and `library/removed-pages/` |
| 12 | principle 4 "Responsibility is not a burden" | rewritten |
| 13, 19 | keep, but update with new knowledge | marked living sections with a date and a review rule |
| 16, 21 | drop the role line and the format lines | removed |
| 18 | Radar "Is this solution relevant to me?", Teardown adds "and how" | applied |
| 20 | owner engaged, champion informed, user shown simply | block "one piece, three readers" |
| 26 | colour mark centred, no blocks, no mono Ink | done; mono Paper stays for dark surfaces |
| 29–30 | "grammar" not understood | renamed "Composition rules: where things go" |
| 31 | Blueprint more focused | `#1E4A80`, 7.31:1 on Paper |
| 34 | heading font close to the logo, informed by competitors and Max's repo | Saira SemiCondensed Black, `research/heading-font.md` |
| 35 | drop Cyrillic | removed everywhere |
| 36 | re-check the grid | numbers verified against tokens, diagram measured |
| 39 | icons too simple, stickers | 65 stickers, sheet, manifest, pages 33–34 |
| 41 | motion not informative | timeline diagram |
| 42 | covers give no reason to stop | `reel-cover-v2` in the Kallaway structure, our palette, no glow or radius |
| 43 | overlays not understood | shown on a frame with a presenter block and a timeline |
| 44 | carousel too dry | `carousel-v3`, screenshot frames, stickers, nine slide types |

## Decisions the orchestrator made (Misha can overturn)

- Key-phrase highlight is a plate: Ink on Paper, Signal on Ink, Oxide only for something broken.
  No italic serif accent, no glow, no arrow glyphs.
- Mark on covers: 96 px bottom-right of Zone A; on carousel slides bottom-right, except the
  cover slide (top-right, the bottom is the face band).
- Face on covers is a placeholder band; real stills go in later, provenance recorded.
- Stickers: pick the surface variant, never recolour by hand. Structural stickers have Ink
  variants 51 to 65.
- The linter skips the profile bio; the approved bio keeps its middle dots and arrow until
  Misha decides.

## What Misha checks first

1. Pages 37 to 40: covers, overlays on a frame, carousel. Contact sheets in `library/approved/`.
2. Page 28: the new heading face next to the mark; the comparison is `research/heading-font-sheet.png`.
3. Pages 33 to 34: the sticker library.
4. Page 4 and 18: the method chain and the three-readers block.

## Open items

| Item | Who | Note |
|---|---|---|
| Bio middle dots and arrow | Misha | keep as approved or rewrite two lines |
| Bio third line | Misha and Max | the role line was removed; the line is open |
| Oxide on Ink 3.31:1 | Misha, on a phone | tight but passes |
| Ownership split | Misha and Max | `brand/08-governance.md`, working file |
| Original vector of the mark | Max | rebuild from it if it exists |
| Max's previs uses Arial, centred text, radius | Max | his Remotion code needs this pack (`research/heading-font.md`) |
| Real stills and screenshots into the placeholder frames | Misha | templates take them as slots |

## How to rebuild anything

```
node tokens/build/build-tokens.mjs && node checks/contrast.mjs
node templates/render.mjs templates/<name>
node checks/lint.mjs templates/<name>
node pdf/build.mjs
```

## Traps

- Template asset paths are `../../../` (HTML is written into `out/`).
- Overlay templates need `"transparent": true` in the manifest for alpha PNGs.
- The PDF page does not reflow; proof every page with `node pdf/proof.mjs <file>`; 12 mm above the footer.
- PyMuPDF rasterizes all pages; `sips` only page 1; `pdftoppm` is absent.
- Saira SemiCondensed is Latin only, like Plex Condensed was; the system has no Cyrillic by decision.
- Structural stickers drawn in Ink vanish on Ink; use the `-ink` variants.
