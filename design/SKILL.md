---
name: m2lab-design-system
description: Use before producing any visual or written asset for M2 Lab (Instagram covers, carousels, overlays, captions, documents). Routes to the one small rule file the task needs; values come only from tokens.
---

# M2 Lab design system: router

The law in one line: **reusable things are parameterised, never edited; values come from
`tokens/tokens.json`; anything with letters or the mark is built from a template.**

Five active rules. Load one file below for anything beyond them.

1. Colours, sizes, spacing and fonts are token values (`tokens/out/tokens.css`, `var(--m2-...)`). Nothing is picked "to look similar".
2. Paper is the primary surface. Ink is for Reel covers and plates on video. Oxide means broken. Signal means lit data on dark or the mark.
3. Everything is left-aligned on the 4-column grid with a 24 px indent from the guide. Hierarchy by size and weight.
4. Primary elements (hook, mark, verdict, format tag) sit inside Zone A of the placement (`social/zones.json`). Subtitles may use Zone B. Nothing in Zone C.
5. Verdicts are shape-coded: KEEP filled, KILL 4 px outline, TEST dashed. Numbers are never naked: WAS / NOW / SAVED.

| Task | Load |
|---|---|
| Writing any sentence, caption, hook, reply | `brand/04-voice.md`, then `brand/05-vocabulary.md` |
| Checking a claim or the promise wording | `brand/01-positioning.md` |
| Planning a week or structuring a Reel | `brand/06-formats.md` |
| Choosing or pairing colours | `rules/color.md` |
| Setting type, sizes, line lengths | `rules/typography.md` |
| Placing elements, canvases, grid, safe zones | `rules/layout.md`, `social/instagram.md` |
| Stickers (tags, plates, callouts, cards, chips) for covers and slides | `stickers/README.md`, then `stickers/manifest.json` |
| Glyphs inside stickers, verdict shapes | `rules/iconography.md` |
| Shooting, screens, generated backgrounds | `rules/imagery.md` |
| Captions, transitions, Verdict Card timing | `rules/motion.md` |
| Using the mark | `brand/logo/README.md` |
| Deciding if a visual idea is allowed | `composition/rules.md`, then `composition/not-this.md` |

Templates live in `templates/<name>/` (fill `examples/*.json`, run `node templates/render.mjs templates/<name>`). Current: `reel-cover-v2`, `carousel-v3`, `claim-bar`, `lower-third`, `verdict-card`, `highlight-cover`, `avatar`; see `templates/README.md`.
Before anything is published: `checks/checklist.md`, `node checks/lint.mjs <path>`, `node checks/contrast.mjs`.

Rejected work goes to `library/rejected/` with a one-line reason. Approved renders go to `library/approved/`.
