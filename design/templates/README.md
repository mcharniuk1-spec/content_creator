# Templates

One folder per template: `template.html` with `{{slot}}` placeholders, `manifest.json` with the
canvas, placement and slot boxes, `examples/*.json`, `out/` renders. Render with
`node templates/render.mjs templates/<name>`; the Instagram zone check runs by itself.

| Template | Status (8 Sep 2026, iteration 2) | Notes |
|---|---|---|
| `reel-cover-v2` | current | Kallaway structure: tag, title with the key phrase on a plate, one dominant sticker visual, caption word, face band. Saira Black |
| `reel-cover` | superseded by v2 | kept for the record, never edited |
| `carousel-v3` | current | nine slide types, screenshot placeholder frames, stickers, cover in the reel structure |
| `carousel` | superseded by v3 | version 2 of the carousel, kept |
| `claim-bar`, `lower-third`, `verdict-card` | current | overlays for video, transparent PNG |
| `highlight-cover`, `avatar` | current | Saira for the words; avatars use the colour mark on Paper, mono Paper on Ink |

Stickers used inside visuals live in `../stickers/` (65 files; pick the variant by surface).
A template is never edited once approved; a change is a new folder beside it.
