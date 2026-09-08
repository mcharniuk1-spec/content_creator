# Orchestration log

Decisions taken by the orchestrator during the run, with the evidence. Newest last.

## 2026-09-08

- **Folder.** Work happens in `~/Desktop/m2lab-brand/`, not in the radar repo. Misha did not
  remember what the old `design/` folder held, so the approved v1 pieces were copied into
  `source/` and rebuilt here. No git push.
- **Composition rules.** Sources 01 technical report, 02 lab notebook, 08 field guide removed by Misha.
  Five remain; renumbered 1–5 in `composition/rules.md`. Carousel templates get their own
  layouts instead of the "report" look.
- **Safe zones.** Meta's live ad spec (accessed 8 Sep 2026) gives Reels and Stories one safe
  zone: top 14 %, bottom 35 %, sides 6 %. On 1080×1920 that is 269 / 672 / 65 px. The old
  frame paddings (180 top, 320 bottom) are inside the covered area, so they are replaced.
  Zone model: A = always safe (Meta official), B = organic-only band (secondary consensus,
  y 1248–1470, without the right rail 130 px), C = never. Hook, mark, verdict live in A only.
- **Type scale, measured** (`research/type-metrics.md`): labels at 32/25 px fall below 12 CSS px
  on a phone, so labels move to 36 default / 32 small. Burned-in subtitles get their own size,
  40 px Plex Sans SemiBold (≥ 14 CSS px). Lint constants: hook ≤ 20 chars per line, body ≤ 38.
  4:5 canvas: hook capped at 6 words, size unchanged. Nothing is legible on the 3:4 grid tile
  at these sizes, so covers are designed as a visual frame there, not as text to read.
- **DTCG.** The 2025.10 stable format encodes colours as objects. We keep the hex-string
  form of the earlier draft because our build script is our own and templates read hex
  directly. Noted so nobody "fixes" it by accident.
- **Brand content check** (`check-brand-vs-playbook.md`): PASS WITH NOTES. Two unsupported
  claims removed by the orchestrator: "at least three traits per publication" and "Teardowns
  are the format people save and forward". Cadence 5/week comes from the 1 Sep decision.
- **Linter vs approved copy.** The approved bio uses middle dots ("Automation · agents ·
  lead research · ops") and an arrow ("build → test → verdict"). Both are named by Anthropic
  as generated-text tells. The visual linter therefore checks on-screen graphics only, not
  the profile bio. Open for Misha: keep the bio as approved or rewrite the two lines.
- **Label style vs the "eyebrow" tell.** Tracked caps labels above headings are a named tell.
  Our mono caps labels are format tags with a number (`RADAR / 04`), placed on the grid, never
  as a decorative eyebrow above every heading. Rule written into `rules/typography.md`; the
  `allcaps-eyebrow` lint rule is dropped from the machine list.
- **Palette decision.** Variant A "Oxide, Paper-first" adopted (`research/palette-options.md`).
  Paper `#E4E9EA` primary surface, Ink `#0C1D1D`, Signal `#7DD774` (was Lime), Oxide `#BB4347`
  (was Stamp), Blueprint `#33587D` new structural colour, Graphite `#5C6565`, Rule `#BEC6C7`.
  Smallest move that leaves the Anthropic cluster: the surface flips, the green loses neon,
  the red leaves vermilion, one structural colour is added. The mark keeps its geometry;
  three colour values inside the SVGs follow the tokens (Ink, Paper, Signal).
- **Contrast fix after the first build.** Graphite on Ink is 2.9:1 and Blueprint on Ink is
  2.34:1. Both are Paper-surface colours now: on Ink, secondary text and lines use Rule
  (`text.secondary-on-dark`, `line.on-dark`, both 10:1). Blueprint is Paper-only. All
  thresholded pairs pass (`checks/out/contrast.json`).
- **Motion tokens** added from `rules/motion.md`: 0 / 120 / 200 / 400 ms, Isotype step 80 ms,
  verdict on screen at least 3000 ms, single easing linear.
- **New size token `size.title.default = 72px`.** The scale had nothing between the 96 px
  hook and the 52 px lead body, so carousel titles were set in 52 px and the slides sat
  empty in their lower half (first carousel render). 72 px fills the 4:5 slide and is still
  under the hook. Carousel re-cut with it.

## 2026-09-08, iteration 2 (Misha's review of PDF v2)

- Misha's page-by-page feedback received; answers to the 11 clarifying questions recorded in
  `orchestration/TASKS.md` phase 8. Decisions: method chain becomes
  `repeated workflow -> fragmentation -> AI boundary -> human review -> first test` everywhere;
  "one repeated task" becomes "one repeated workflow" everywhere; Radar question
  "Is this solution relevant to me?"; Teardown question gains "and how"; editorial filter gains
  the block "one piece, three readers" (owner engaged, champion informed, user shown simply);
  trait Unhurried removed; role line removed from content; pages 10, 15, 22, 23, 24, 25 leave the
  PDF (files stay in `brand/`); "grammar" renamed "composition rules" (folder `composition/`);
  heading typeface to be chosen near the mark's geometry, headings only; 50 stickers replace
  plain icons as the iconography layer; reel covers and carousel covers take the Kallaway
  structure (title with highlighted key phrase, big central visual, face at the bottom, one-word
  caption) in our palette without glow or radius; carousel keeps placeholder frames for
  screenshots; overlays stay, shown on a frame; Blueprint darkened to `#1E4A80` (7.31:1 on Paper).
- Linter now accepts `var(--m2-font-family-*)` in font-family so templates can follow a font
  change through tokens.
- **Heading typeface: Saira SemiCondensed Black (OFL)** replaces IBM Plex Sans Condensed Bold
  for hooks and titles (`research/heading-font.md`, sheet `research/heading-font-sheet.png`).
  Reasons: closest match to the mark's flat-sided, mitred geometry; 21.2 characters per 888 px
  line at 96 px against Plex Condensed's 21.3, so every size token and the 20-char lint constant
  stay. Body stays Plex Sans, labels Plex Mono. Niche finding: no competitor documents type; Max's
  previs is hard-coded to Arial and centred text, so he needs this pack.
- **Highlight device.** The Kallaway structure's key-phrase highlight is kept as a shape: an Ink
  plate with Paper text on light covers, a Signal plate with Ink text on dark covers. Oxide only
  when the phrase is about something broken. No italic serif accent, no glow.
- **Templates, iteration 2.** `reel-cover-v2` accepted after one revision (first cut had a small,
  light visual; now one dominant sticker element fills 100 % of the band width, 4 px strokes,
  Ink plate on Paper, Paper frame on Ink). `carousel-v3` accepted with one fix pending on the
  cover slide (face as a full-width bottom band, mark top-right on that slide only). Stickers
  grew from 50 to 65: structural stickers vanished on Ink covers, so 15 Ink-surface variants were
  added (family k). Rule: pick the variant by surface, never recolour a sticker by hand.
- **PDF version 3 built:** 45 pages (brand book 4–21, design system 23–45). QA
  (`orchestration/QA-pdf-v3.md`): all review items verified present; the colophon and two
  contents titles corrected after QA; no overflow, no missing images, no wrong fonts.
  Copied to `~/Desktop/M2-Lab-Brandbook.pdf`.
