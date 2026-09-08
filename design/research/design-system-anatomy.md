# Anatomy of a design system — for social content, built for AI agents

Research pass, September 2026. Sources are cited inline; anything without a primary
source is flagged as practice, not fact.

## 1. Canonical layers of a design system

| Layer | Contents | Example systems |
|---|---|---|
| Foundations / tokens | Color, type, spacing, sizing, radius, stroke, motion, elevation as named values | [Material 3 tokens](https://m3.material.io/foundations/design-tokens/overview), [Atlassian tokens](https://atlassian.design/foundations/tokens/design-tokens), [Polaris tokens](https://github.com/Shopify/polaris-tokens) |
| Primitive / reference tokens | Raw values only — `blue-500`, `space-4`. No meaning attached. | Material 3 calls these "reference" tokens; Polaris ships them as the base layer of `@shopify/polaris-tokens` |
| Semantic / system tokens | Primitive value + a role — `color-action-primary`, `color-surface-elevated`. Renaming or reskinning happens here without touching primitives. | Material 3 "system" tokens; Atlassian's token naming (`color.text`, `color.background.brand`) |
| Component tokens | Values scoped to one component, usually aliasing semantic tokens — `button.background.primary` | Material 3 "component" tokens; IBM Carbon component-level tokens |
| Grid / layout | Breakpoints, columns, gutters, container widths | GOV.UK Design System [styles](https://design-system.service.gov.uk/) |
| Components (slots + variants) | Reusable UI blocks with documented props/variants and content slots | GOV.UK [components](https://design-system.service.gov.uk/), Atlassian components, Carbon components |
| Patterns | Best-practice compositions of components for a recurring task, not just a single component | GOV.UK [patterns](https://design-system.service.gov.uk/patterns/) — explicitly defined as "best practice design solutions for specific user-focused tasks and page types" that "use one or more components and explain how to adapt them" |
| Content guidelines | Voice, tone, composition rules, inclusive language, terminology | Atlassian's content foundations (voice and tone, language and composition rules, inclusive language) |
| Accessibility rules | Contrast minimums, testing method, assistive-tech verification | GOV.UK: components are "tested against real assistive technology, not just automated checks," targeting WCAG 2.2 AA; Atlassian runs a dedicated accessibility team inside the design system |
| Governance / versioning / changelog | Ownership, approval process, SemVer release, dated changelog with migration notes | General practice across mature systems (secondary sources); GOV.UK and Carbon both publish changelogs per release |
| Contribution model | Who can propose a component, review bar, deprecation policy | General practice; not tied to one primary source found |

Two-layer (primitive → semantic) token structure is described as "the norm across
modern design systems," and skipping the semantic layer is called out as a common
failure: "when a primitive changes, you have to hunt down every component that
references it instead of updating one semantic token" (secondary source, design-system
best-practice writeups, not a single named primary document — treat as practice
consensus, not a spec requirement).

## 2. What a SOCIAL CONTENT design system needs beyond a UI design system

No W3C or vendor spec covers this — everything below is either read off Instagram's
actual UI behavior (secondary sources measuring it) or agency/Canva practice. Marked
per item.

| Need | Detail | Source status |
|---|---|---|
| Canvas sizes per surface | Reels/Stories 1080×1920 (9:16); feed post and carousel typically 1080×1350 (4:5) or 1080×1080 (1:1); cover/thumbnail same as Reels canvas | Practice — measured by third-party guides, not an Instagram-published spec sheet. "Instagram doesn't publish a single official safe zone spec sheet" (explicit statement from a 2026 sizing guide) |
| Safe zones | Keep text/logos clear of roughly the top ~220px and bottom ~430–450px of a 1080×1920 canvas (UI chrome: caption, username, audio credit, action-button rail on the right ~90px). Net safe area roughly 1080×1300 centered. | Practice, no primary source — multiple independent guides converge on these numbers but Instagram does not publish them, and they "shift when the apps update" |
| Template slots | Named, swappable regions in a template (headline, subhead, cover image, logo lockup, CTA) so batch tools can fill them programmatically | Practice — this is how Canva Brand Kit templates and most automation pipelines (Higgsfield, Bannerbear-style tools) are structured; no formal spec |
| Export pipeline | One source template → automated export to each surface's exact pixel size and format (mp4/png/jpg), stripped of edit-only layers | Practice |
| Batch rendering | Render N variants of one template from a data source (CSV/JSON row → one asset), instead of hand-editing each post | Practice — described in Canva agency material as building "template variations for each content type" to "batch-create an entire week's content in one session" |
| Motion presets for captions | A small fixed set of caption-in animations (e.g., pop, fade, karaoke-highlight) reused across all Reels rather than invented per video | Practice, no primary source |
| Cover/thumbnail rules | Legible at feed-thumbnail size, no critical text past the safe zone, consistent logo/watermark position across the grid | Practice, no primary source |
| Brand kit as system root | Logo variants, color palette, fonts, tone-of-voice held centrally and referenced by every template rather than duplicated per file | Canva's Brand Kit model: "centralize brand elements like logos, fonts, and icons, update brand details at any time" |

Takeaway: a social-content design system is a superset of a UI design system's
foundations layer (tokens for color/type/spacing still apply to graphics) plus a
production layer (canvas, safe zone, slot, export, batch) that UI design systems have
no equivalent of, because UI renders live and doesn't get "exported" to a fixed frame.

## 3. AI-consumable structure — what sources actually say

Direct quotes and numbers, not paraphrase, where available:

- **Atlassian's DESIGN.md field test (2026):** their own DESIGN.md file is
  **"80 KB, or roughly 19,800 LLM tokens (~10,700 without frontmatter),"** which
  already required Atlassian to strip "much of the usage guidance from our 50+
  components" to keep the file usable at all.
- Same test, comparing three ways of giving an agent design context on one login-screen
  task:

  | Approach | Token usage | Time | Avg. turns |
  |---|---|---|---|
  | DESIGN.md alone | 7.21M | 6m 46s | 45.3 |
  | ADS MCP server | 3.75M | 5m 1s | 35.1 |
  | ADS Skill | 4.43M | 5m 23s | 36 |

  Atlassian's own conclusion: **"using DESIGN.md as the sole source of design system
  guidance required ~92% more tokens, took longer to produce results, and had ~2.7x
  the variance in token consumption between runs."**
- Why the MCP/skill approach wins: **"An MCP server is able to load relevant context
  on demand; an agent can perform a tool call such as `ads_plan` to fetch guidance only
  for a specific component."** A flat file cannot do partial/on-demand loading — the
  whole file (or none of it) goes into context.
- Where Atlassian still recommends a flat DESIGN.md file rather than MCP/tokens: "quick
  prototyping in unfamiliar environments," "high-level artistic direction," and
  "customer theming for adaptive UIs" — i.e. environments where the real design-system
  tooling isn't available to the agent.
- Separately, Atlassian reports for its **structured foundations approach** (ADS MCP +
  skills vs. no MCP): **52% accuracy improvement in AI calls, 34% faster on average,
  26% reduction in AI tooling calls, 16% reduction in AI token usage.** (One Atlassian
  post also states "4.9% more accurate code... 11% fewer errors... 34% faster... 16%
  fewer tokens... 26% fewer tool calls" for the same comparison — the two posts give
  slightly different accuracy figures, both attributed to Atlassian; treat the
  structural/speed/token numbers as the load-bearing ones since they repeat, and note
  the accuracy figure is inconsistent between posts.)
- **Figma's own developer docs** on structuring a Figma file for MCP/code generation:
  do **not** give a numeric file-size or rule-count threshold. The concrete guidance
  found is qualitative: avoid "large, heavy frames," break a design into smaller
  logical selections, use real components + Code Connect so "MCP isn't free-handing
  new code patterns but instead pulling from the same system your engineers trust."
  No exact word/line/rule counts are published by Figma — flagged as **unverified
  beyond the qualitative statement**.
- **Google's DESIGN.md spec** (`google-labs-code/design.md`) fixes a two-layer format:
  YAML front matter (machine-readable tokens) + Markdown body (human/agent-readable
  rationale), with the explicit design principle: **"The tokens are the normative
  values. The prose provides context for how to apply them."** It defines a canonical
  section order (Overview, Colors, Typography, Layout, Elevation & Depth, Shapes,
  Components, Do's and Don'ts — all optional except that present sections must follow
  this order) and ships a linter enforcing **11 rules** (errors/warnings/info) —
  broken references, missing primary colors, contrast ratios, orphaned tokens, section
  ordering. It does not itself prescribe a maximum file size or rule count for the
  content — that constraint is empirical (see Atlassian's 80KB experience above), not
  part of the spec.
- **Vercel v0 / AGENTS.md pattern:** the AI-agent convention here is a single
  `AGENTS.md` at the project root that acts "as a system prompt or 'contract' for the
  agent," which "most agents automatically index... to inform their context window."
  Guidance quoted from secondary coverage: rules should be organized as a
  "prioritized hierarchy... categorizing best practices into Impact Levels so the AI
  can triage" — i.e., ranked rules, not a flat list. No numeric size cap found in
  primary Vercel material.
- No source in this research surfaced an explicit rule of "write instructions as
  negatives, not positives" as a named best practice with a citation — flagged as
  **unverified**; do not assert it as sourced guidance.

Net pattern across all three vendors (Figma, Atlassian, Google/Vercel): the direction
is consistently *toward* many small, on-demand-loadable units (tool calls, skill files,
short guideline files) and *away* from one large document, because large flat files
measurably cost more tokens and more turns per task (Atlassian's own A/B numbers above
are the only hard measurement found; Figma and Vercel state the same preference
qualitatively without publishing numbers).

## 4. DTCG token format (Design Tokens Format Module, 2025.10 — first stable W3C
Community Group spec, backed by Adobe, Figma, Google, Microsoft, Shopify, Salesforce)

Source: [designtokens.org format spec](https://www.designtokens.org/tr/drafts/format/).

Minimum valid token:

```json
{
  "color-brand-primary": {
    "$type": "color",
    "$value": { "colorSpace": "srgb", "components": [1, 0, 0] }
  }
}
```

Rules:
- `$value` is required on every token.
- `$type` must be an explicit string from the spec's type list — **tools must not
  guess a type by inspecting the value.** If `$type` is omitted, it must be resolved
  by reference, by inheriting from a parent group, or the file is invalid.
- Groups (objects without `$value`) organize tokens hierarchically and may carry
  `$description`, `$type` (inherited by children), `$extends`, `$deprecated`,
  `$extensions`. A group may hold a reserved `$root` token for its own base value.

`$type` values relevant to M2 Lab:

| `$type` | Shape |
|---|---|
| `color` | Object: `{ colorSpace, components: [r,g,b], alpha?, hex? }` |
| `dimension` | Object: `{ value: number, unit: "px" \| "rem" }` |
| `fontFamily` | String, or array of strings (fallback stack) |
| `fontWeight` | Number 1–1000, or a predefined string (`thin`, `bold`, `black`, …) |
| `number` | Plain JSON number — unitless values like line-height multiplier |
| `duration` | Object: `{ value: number, unit: "ms" \| "s" }` |
| `cubicBezier` | Array of exactly four numbers `[P1x, P1y, P2x, P2y]` |

Aliasing (referencing another token), two syntaxes:

```json
{ "color-action-primary": { "$value": "{color-brand-primary}" } }
```
Curly-brace syntax implicitly resolves to that token's `/$value`.

```json
{
  "hue-only": {
    "$value": { "$ref": "#/color-brand-primary/$value/components/0" }
  }
}
```
JSON Pointer (`$ref`) syntax reaches into a specific sub-field of another token's
value and requires the explicit path.

## 5. Recommended folder structure for M2 Lab's design system

Existing repo already has the right skeleton at
`/Users/mihailampleev/Desktop/m2lab-brand/` (`assets/`, `brand/`, `checks/`,
`composition/`, `library/`, `orchestration/`, `rules/`, `social/`, `source/`, `templates/`,
`tokens/`). Below is how to fill it out so it stays many-small-files, tokens-first,
with a router and lint scripts — following the pattern the research above converges
on (Atlassian: on-demand small units beat one big file; DTCG: tokens as single source;
Google design.md: a linter enforcing structural rules).

```
m2lab-brand/
├── tokens/                  # single source of truth — DTCG-format JSON only, nothing else
│   ├── color.tokens.json    # primitive + semantic color tokens
│   ├── type.tokens.json     # fontFamily, fontWeight, size, line-height tokens
│   ├── space.tokens.json    # spacing, radius, stroke-width tokens
│   ├── motion.tokens.json   # duration, cubicBezier tokens for caption/transition presets
│   └── build/               # generated CSS/JSON exports — never hand-edited
├── rules/                   # short, single-topic markdown rule files (one rule = one file)
│   ├── router.md            # index: "for X, read Y" — the one file an agent reads first
│   ├── color-usage.md
│   ├── typography.md
│   ├── logo-clearspace.md
│   └── content-voice.md
├── templates/                # one social-content template per file, slots named explicitly
│   ├── reel-cover.template.json
│   ├── carousel-slide.template.json
│   └── story.template.json
├── social/                   # canvas/safe-zone/export specs per surface, one file per surface
│   ├── reels.md               # 1080x1920, safe-zone numbers, cover rules
│   ├── carousel.md             # 1080x1350, slot count, swipe-order rule
│   └── stories.md
├── composition/                  # visual composition rules references (composition, motion presets), small files
├── checks/                   # lint/verification scripts, one check = one script
│   ├── check-tokens.mjs       # validates tokens/*.json against DTCG shape
│   ├── check-contrast.mjs     # accessibility contrast pass on color tokens
│   └── check-templates.mjs    # confirms every template slot resolves to a real token
├── library/                   # approved vs rejected asset outputs, for audit trail
│   ├── approved/
│   └── rejected/
├── assets/                    # static brand assets (fonts, icons) referenced by tokens/templates
├── brand/                     # logo source files
├── orchestration/             # scripts that call templates + tokens to batch-render output
└── source/                    # working notes, positioning docs, non-canonical drafts
```

Router file (`rules/router.md`) is the one entry point an agent reads first — it
should be a short index pointing to the specific small file for the task at hand,
mirroring the "load only what's needed" pattern from Atlassian's MCP/skill results
(section 3) rather than asking an agent to read the whole `rules/` folder every time.

## 6. Common mistakes, with sources

- **Skipping the semantic layer.** Wiring components straight to primitive values
  means "when a primitive changes, you have to hunt down every component that
  references it instead of updating one semantic token." (Secondary source,
  design-system best-practice writeup — practice consensus, not a single named spec.)
- **No named owner.** "Libraries without a named owner drift in a predictable
  pattern — components get added but nothing gets removed, naming conventions diverge
  ... and the latest version in Figma starts diverging from what engineering is
  actually using." (Same secondary source.)
- **Treating a flat AI-context file as sufficient at scale.** Atlassian's own DESIGN.md
  needed content cut from 50+ components to fit a usable size, and even so cost ~92%
  more tokens and had 2.7x more run-to-run variance than an MCP/skill approach on the
  same task (section 3, Atlassian, primary source).
- **Guessing token type from its value instead of declaring `$type`.** Explicitly
  disallowed by the DTCG spec: "tools MUST NOT attempt to guess the type of a token by
  inspecting the contents of its value." (Primary source, designtokens.org.)
- **Relying on unpublished platform safe-zone numbers as if they were fixed.** Every
  Instagram safe-zone figure in this document is a third-party measurement, not an
  Instagram spec, and "shifts when the apps update" — a template hard-coded to one
  guide's numbers can silently break after a UI update. (Practice, no primary source —
  flagged explicitly in the source material itself.)
- **Recreating components instead of reusing them when only given prose/markdown
  context.** Atlassian found "DESIGN.md was more likely to re-create ADS components"
  than the MCP/skill routes, which point directly at canonical implementations.
  (Primary source, Atlassian.)

## 7. Sources

- [Design Tokens Format Module, 2025.10 draft](https://www.designtokens.org/tr/drafts/format/) — W3C Design Tokens Community Group
- [DTCG: Design Tokens specification reaches first stable version](https://www.w3.org/community/design-tokens/2025/10/28/design-tokens-specification-reaches-first-stable-version/)
- [design-tokens/community-group GitHub repo](https://github.com/design-tokens/community-group)
- [Material 3 — Design tokens overview](https://m3.material.io/foundations/design-tokens/overview)
- [Atlassian Design System — Design tokens](https://atlassian.design/foundations/tokens/design-tokens)
- [Atlassian Design System — Foundations overview](https://atlassian.design/foundations)
- [Shopify Polaris tokens — GitHub](https://github.com/Shopify/polaris-tokens)
- [GOV.UK Design System — Patterns](https://design-system.service.gov.uk/patterns/)
- [GOV.UK Design System — home](https://design-system.service.gov.uk/)
- [Figma — Structure your Figma file for better code (developer docs)](https://developers.figma.com/docs/figma-mcp-server/structure-figma-file/)
- [Atlassian — DESIGN.md: what we learned testing portable design context in practice](https://www.atlassian.com/blog/how-we-build/atlassians-design-md-is-here-what-we-learned-testing-portable-design-context-in-practice)
- [Atlassian Design System — Building the context engine for the AI era](https://www.atlassian.com/blog/ai-at-work/atlassian-design-system-building-the-context-engine-for-the-ai-era)
- [google-labs-code/design.md — GitHub](https://github.com/google-labs-code/design.md)
- [Vercel — How to prompt v0](https://vercel.com/blog/how-to-prompt-v0)
- [Vercel — How we made v0 an effective coding agent](https://vercel.com/blog/how-we-made-v0-an-effective-coding-agent)
- Secondary, practice-level (no single primary spec): Instagram Reels safe-zone measurement guides (multiple 2026 third-party sizing guides, cross-checked for consistency); Canva agency/brand-kit documentation (canva.com/solutions/agencies, canva.com/learn/how-to-build-a-brand-kit); general design-system best-practice writeups on governance/versioning/token-layer mistakes (onething.design, uxpin.com, figr.design — cited for consensus practice only, not as authoritative specs).

