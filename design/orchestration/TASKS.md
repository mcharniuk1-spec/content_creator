# M2 Lab — brand book + design system: task plan and agent orchestration

Version 1 · 8 September 2026 · owner: Misha · orchestrator: Fable (this session)

Purpose of this file: the step-by-step plan that agents execute in order, the model
assigned to each step, what each step consumes and produces, and the check the
orchestrator runs before the next step may start. Re-running the plan means re-running
the failed step, not the whole chain.

## Roles

| Role | Model | Does | Never does |
|---|---|---|---|
| Orchestrator | Fable 5.1 | Splits work, writes prompts, reviews every output against the acceptance check, integrates into the canonical files, decides on open questions | Delegates a decision Misha already made |
| Builder | Opus | Main creative and structural work: palette, type scale, layout, templates, rules, PDF | Edits files outside its assigned output folder |
| Worker | Sonnet | Research with sources, safe-zone math, contrast checks, rendering, lint runs | Invents numbers |
| Checker | Haiku / Sonnet | Verifies a Builder's output against the spec: values in tokens, contrast, file structure, dead links | Fixes what it finds (reports only) |

Rules for every agent: write only new files in the folder named in the prompt; never
modify `tokens/tokens.json`, `brand/logo/*` or anything in `library/approved/`;
every number has a source or a script; English in all files.

## Decisions fixed before the run (Misha, 8 Sep 2026)

1. Separate folder `~/Desktop/m2lab-brand/`, no git push.
2. Palette: spread slightly further away from the Anthropic default cluster. Recognisability stays.
3. Composition rules sources 01 (technical report), 02 (lab notebook) and 08 (field guide): removed.
   Five remain: engineering drawing, Isotype, Swiss grid, oscilloscope, checklist.
4. Brand book covers identity, voice and positioning; source is
   `source/positioning-playbook.md`.
5. Logo: existing mark (three versions) stays. No new wordmark.
6. Platform: Instagram only. Other platforms are out of scope.
7. PDF language: English.
8. Figma: not now.
9. Photo and video direction: included, people shown as placeholder frames.
10. No intermediate stops; one review at the end.
11. Higgsfield generation allowed if needed; cost is stated before running.

## Phase 0 — Foundation (orchestrator)

| # | Task | Output | Check |
|---|---|---|---|
| 0.1 | Folder skeleton, copy sources from the old `design/` folder | `source/`, `brand/logo/` | Files present |
| 0.2 | IBM Plex Sans, Sans Condensed, Mono — Regular/Medium/SemiBold/Bold, TTF + WOFF2, OFL licence | `assets/fonts/` | Condensed has no Cyrillic (verified with fontTools) |
| 0.3 | This plan | `orchestration/TASKS.md` | — |

## Phase 1 — Research (Workers, parallel)

| # | Task | Model | Output | Check |
|---|---|---|---|---|
| 1.1 | What a brand book consists of, from real brand books | Sonnet | `research/brandbook-anatomy.md` | Every section has a URL; recommended TOC present |
| 1.2 | What a design system consists of, incl. social-content and AI-consumable systems, DTCG format | Sonnet | `research/design-system-anatomy.md` | Numbers quoted match sources; folder tree proposed |
| 1.3 | Instagram safe zones and format specs from Meta first | Sonnet | `research/instagram-safe-zones.md`, `.json` | Each number carries confidence: meta-official / secondary / derived |
| 1.4 | Palette spread: 3 variants with OKLCH, WCAG, colour-blind simulation, cluster distance | Opus | `research/palette-options.*`, `palette-sheet.png` | Script exists and reproduces the numbers; PNG renders |

Gate 1: orchestrator reads all four, picks the palette variant, fixes the safe-zone
numbers that go into tokens, writes the decision into `orchestration/LOG.md`.

## Phase 2 — Brand book content (Builder, sequential)

| # | Task | Output | Check |
|---|---|---|---|
| 2.1 | Positioning and audience, condensed from the playbook: one-line promise, supporting line, method, who we serve, who we do not, credibility boundary | `brand/01-positioning.md`, `brand/02-audience.md` | No claim absent from the playbook |
| 2.2 | Personality and values: 4–5 traits, each with "this, not that" | `brand/03-personality.md` | Traits map to the playbook's "is / is not" |
| 2.3 | Voice and tone: principles, vocabulary we use / avoid, sentence patterns, examples per format (Radar, Builds, Teardowns), captions, bio, replies | `brand/04-voice.md`, `brand/05-vocabulary.md` | Every rule stated positively; forbidden words listed separately for the linter |
| 2.4 | Formats: Radar / Builds / Teardowns — purpose, question, required proof, editorial filter, verdict rule | `brand/06-formats.md` | Matches playbook section 8 |
| 2.5 | Logo rules, migrated and updated to the new palette values | `brand/logo/README.md` | Values reference tokens, not literals |

Gate 2: Checker (Haiku) compares each brand file against the playbook and reports
contradictions. Orchestrator fixes.

## Phase 3 — Design system foundations (Builder, iterative: one topic at a time)

| # | Iteration | Output | Check |
|---|---|---|---|
| 3.1 | Colour: base + semantic tokens, roles, allowed pairs, ratios (Paper-first), what each colour never does | `tokens/tokens.json` (colour groups), `rules/color.md` | Contrast table generated by script; mark colours updated (two values only) |
| 3.2 | Typography: families, weights, roles, scale for 1080×1920 and 1080×1350, line length, Cyrillic rule | `tokens/tokens.json` (font, size, leading, tracking), `rules/typography.md` | Scale values reproduce in a rendered specimen |
| 3.3 | Spacing and grid: 4-column grid, gutter, indent, frame paddings per canvas, spacing scale | `tokens/tokens.json` (frame, space), `rules/layout.md` | Paddings ≥ safe zones from 1.3 |
| 3.4 | Instagram safe zones as tokens per placement (reel, story, feed 4:5, 1:1, grid 3:4, carousel, avatar, highlight) | `tokens/tokens.json` (canvas, safe), `social/instagram.md`, `social/overlays/*.svg` | Overlay SVGs render on a 1080×1920 test frame and match the JSON |
| 3.5 | Iconography and verdict: Lucide rules, stroke, sizes; KEEP/KILL/TEST shape coding | `rules/iconography.md`, `rules/verdict.md` | Rendered chip sheet |
| 3.6 | Imagery and motion: shooting direction, B-roll and generated-background rules, caption motion presets | `rules/imagery.md`, `rules/motion.md` | Rules trace to a composition sources |
| 3.7 | Composition rules: five sources with techniques; `not-this.md` as linter input | `composition/rules.md`, `composition/not-this.md` | No reference to removed sources |
| 3.8 | Build script: tokens → CSS, flat JSON, overlay SVGs | `tokens/build/build-tokens.mjs`, `tokens/out/` | `node tokens/build/build-tokens.mjs` exits 0 |

Gate 3: Checker runs the build, the specimen render and the contrast script; reports.

## Phase 4 — Templates (Builder)

Each template is an HTML file with slots, rendered to PNG with headless Chrome at the
exact canvas size. Slots are filled from a JSON example. No template contains a literal
colour or size: everything comes from `tokens/out/tokens.css`.

| # | Template | Canvas | Output |
|---|---|---|---|
| 4.1 | Reel cover (hook + format label + mark), dark and light | 1080×1920 | `templates/reel-cover/` |
| 4.2 | Claim bar (persistent statement plate) | 1080×1920 overlay | `templates/claim-bar/` |
| 4.3 | Verdict Card KEEP / KILL / TEST | 1080×1920 overlay | `templates/verdict-card/` |
| 4.4 | Lower third (name + role) | 1080×1920 overlay | `templates/lower-third/` |
| 4.5 | Carousel set: cover slide, statement slide, list slide, Isotype slide, before/after slide, verdict slide, CTA slide | 1080×1350 | `templates/carousel/` |
| 4.6 | Highlight covers (5) | 1080×1920, circular safe area | `templates/highlight-cover/` |
| 4.7 | Avatar (mark on Paper, circle-safe) | 1080×1080 | `templates/avatar/` |

Gate 4: Checker overlays the Instagram UI masks on every render and reports any text
or mark inside a covered zone; runs the linter on the template CSS.

## Phase 5 — Gates for agents

| # | Task | Output | Check |
|---|---|---|---|
| 5.1 | `SKILL.md` router: the law in one line, five active rules, links | `SKILL.md` | ≤ 40 lines |
| 5.2 | Linter: fails on colour outside palette, font outside Plex, radius ≠ 0, shadow, gradient, emoji, forbidden words | `checks/lint.mjs` | Fails on a planted bad file, passes on templates |
| 5.3 | Pre-publish checklist, five questions | `checks/checklist.md` | — |

## Phase 6 — PDF (Builder, then Checker)

| # | Task | Output | Check |
|---|---|---|---|
| 6.1 | Brand book HTML: cover, contents, positioning, audience, personality, voice, vocabulary, formats, logo | `pdf/brandbook.html` | All text from `brand/` |
| 6.2 | Design system HTML: colour, typography, layout, safe zones, iconography, verdict, imagery, motion, templates gallery, tokens reference, how agents use it | `pdf/design-system.html` | All values from `tokens/out/` |
| 6.3 | Render both to one PDF with headless Chrome, A4 landscape | `~/Desktop/M2-Lab-Brandbook.pdf` | Page count, fonts embedded, every image present |
| 6.4 | Visual QA: Checker renders each PDF page to PNG and looks for overflow, missing images, wrong fonts | `orchestration/QA.md` | Zero blocking issues |

## Phase 7 — Handoff

| # | Task | Output |
|---|---|---|
| 7.1 | `README.md`: what is where, how to use, how to rebuild | `README.md` |
| 7.2 | `HANDOFF.md`: decisions, open items, what Misha checks first | `HANDOFF.md` |
| 7.3 | Memory update | agent memory |

## Acceptance for the whole run

- PDF opens, brand book first, design system second, English, fonts are IBM Plex.
- `node tokens/build/build-tokens.mjs` and `node checks/lint.mjs templates/` both exit 0.
- Every template render passes the Instagram overlay check.
- Misha can open the PDF and review without asking where anything is.
