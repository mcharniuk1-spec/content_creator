# M2 Lab brand book and design system

Version 2, 8 September 2026. Owner: Misha. Users: Misha, Max, and any AI agent producing
M2 Lab content. English throughout. Not a git repository by decision.

Start here: `SKILL.md` (router for agents) or `pdf/out/M2-Lab-Brandbook.pdf` (for people).

## What is where

| Folder | What it holds | Edit? |
|---|---|---|
| `brand/` | Brand book content: positioning, audience, personality, voice, vocabulary, formats, messaging, governance; `logo/` with the three marks and their rules | Through the change process in `brand/08-governance.md` |
| `tokens/` | `tokens.json` is the single source of values. `build/build-tokens.mjs` produces `out/tokens.css`, `out/tokens.flat.json`, `out/palette.md` | Only `tokens.json`, by hand, rarely |
| `rules/` | One topic per file: color, typography (Saira SemiCondensed for display), layout, iconography (glyphs inside stickers), imagery, motion | Yes, one rule per file |
| `social/` | Instagram zone model `zones.json`, `instagram.md`, QA overlay masks and `overlays/check-overlay.mjs` | When Meta changes the UI |
| `composition/` | The five visual sources we borrow from, and `not-this.md` (linter input) | Rarely |
| `templates/` | HTML templates with slots, one folder each; `render.mjs` renders examples to PNG and runs the zone check; `README.md` says which version is current | Never edit an approved template; add a variant beside it |
| `stickers/` | 65 SVG graphic components in 11 families (tags, highlights, callouts, verdict, numbers, lists, data, screens, people, meta, Ink variants), `manifest.json`, `sheet.png` | Add new files; never edit an approved sticker |
| `checks/` | `lint.mjs` (visual and copy linter), `contrast.mjs`, `checklist.md`, `lint-rules.json`, fixtures | Yes |
| `pdf/` | The PDF pipeline: `print.css`, `shell.html`, `sections/`, `build.mjs`, `proof.mjs`; output in `pdf/out/` | Sections yes, shell rarely |
| `assets/` | IBM Plex fonts (OFL) in TTF and WOFF2; Lucide icons (symlink to the radar repo copy) | No |
| `research/` | Sources behind the decisions: brand book anatomy, design system anatomy, Instagram safe zones, palette options, type metrics | Append only |
| `orchestration/` | `TASKS.md` (the plan and agent roles), `LOG.md` (decisions with evidence), check reports | Append only |
| `library/` | `approved/` renders and `rejected/` with reasons | Yes |
| `source/` | Copies of the inputs this version was built from (v1 tokens, playbook, research) | No |

## Everyday commands

```
node tokens/build/build-tokens.mjs        # rebuild CSS and JSON from tokens.json
node checks/contrast.mjs                  # contrast table, fails on a failing pair
node templates/render.mjs templates/reel-cover    # render examples, run the zone check
node checks/lint.mjs templates/reel-cover         # visual linter on a folder
node checks/lint.mjs --copy caption.md            # copy linter on text
node pdf/build.mjs                        # rebuild the PDF into pdf/out/
```

## How a new asset is made

1. Pick the template. Fill a JSON example with the slot values. Never touch the template.
2. Render. The zone check runs by itself; a red line means something sits where Instagram covers it.
3. Run the linter on the output folder and the copy linter on the caption.
4. Walk `checks/checklist.md`. Publish, or put the render in `library/rejected/` with one line why.

## How a rule changes

Write the proposal and a one-line reason, agree between Michael and Max, change the value in
`tokens/tokens.json` or the rule file, rebuild, add a dated "was / became" line to the file.
Templates that depend on it are re-rendered, not edited.
