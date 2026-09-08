# M2 Lab — Not This

Grounded in `source/research-anti-ai-slop.md` (4 Sep 2026) and Anthropic's
`frontend-design` skill — github.com/anthropics/skills, `skills/frontend-design/SKILL.md`,
fetched 8 Sep 2026. Used as linter input; every machine-checkable item repeats at the
bottom as a `lint-rules.json` entry.

## Part A — Defaults of generative models

1. **Warm cream background + terracotta/clay accent** (near `#F4F1EA` / `#D97757`).
   Named directly by Anthropic as the single most common AI-design cluster; `#D97757`
   is literally Claude's own accent, so it reads as a tell on any brief.
   (skills/frontend-design/SKILL.md)
2. **Near-black background + one acid-green or vermilion accent.** Anthropic's second
   named default cluster. (skills/frontend-design/SKILL.md)
3. **Tinted near-black standing in for true black** (`#0B0B0B`, `#111`). Named by
   Anthropic as template chrome that appears "whatever the subject."
   (skills/frontend-design/SKILL.md)
4. **Purple/indigo gradient hero.** Second most-cited profile complaint in the
   47-subreddit corpus (2.0% gradient, 2.3% "AI purple/indigo" of 46,971 posts).
   reddit.com/r/ClaudeCode/comments/1u7g0z5
5. **Any `linear-gradient`/`radial-gradient` wash used as background decoration.**
   Anthropic's "SaaS-card kit" cluster; not one of our five sources, so not earned.
   (skills/frontend-design/SKILL.md)
6. **Uniform rounded corners on every card, one border-radius regardless of
   hierarchy.** Same SaaS-card cluster. (skills/frontend-design/SKILL.md)
7. **Identical soft grey drop shadow under every card** (`rgba(0,0,0,.1)`-style).
   Same cluster. (skills/frontend-design/SKILL.md)
8. **Default sans headline/body fonts** — Inter, Roboto, Open Sans, Lato, Geist, or
   the Space Grotesk/Instrument Serif pairing named in the 1590-landing-page study.
   research-anti-ai-slop.md §3.4, HN 48504912, 12 Jun 2026; reddit corpus 0.4% "Inter,
   Geist." We use IBM Plex exclusively — see `not-this.md` Part B.
9. **Emoji standing in for icons.** 0.5% of profile posts in the reddit corpus.
   reddit.com/r/ClaudeCode/comments/1u7g0z5
10. **Tracked-out ALL-CAPS eyebrow label above every heading.** Anthropic, named
    explicitly as a generated-page tell. (skills/frontend-design/SKILL.md)
11. **Meta strings joined with middle dots** ("A · B · C") **or "WORD — fragment"
    spaced-em-dash labels.** Anthropic, template chrome. (skills/frontend-design/SKILL.md)
12. **A single word or phrase in a headline set in italic, bold, or a different
    colour for emphasis.** Anthropic names this as one of the commonest tells.
    (skills/frontend-design/SKILL.md)
13. **A "→" appended to link or button text.** Anthropic, template chrome.
    (skills/frontend-design/SKILL.md)
14. **Fade-and-slide-up entrance on every section, hover transition on every card.**
    Anthropic's named generic-motion default. (skills/frontend-design/SKILL.md)
15. **Numbered markers (01/02/03) on content that is not actually a sequence.**
    Anthropic. (skills/frontend-design/SKILL.md) — judgment call, not machine-checkable.

## Part B — Deviations from our own system

- Colour outside the token palette (`tokens.json`, once ratified).
- Font outside the IBM Plex family (Plex Sans, Plex Sans Condensed — Latin headlines
  only, no Cyrillic — Plex Mono, Plex Sans for Cyrillic body per the September 4
  rendering finding).
- Type size or spacing value outside the agreed scale.
- Centred text of any kind (Swiss-grid source, item 3 in `references.md`).
- A number shown without its WAS / NOW / SAVED label (oscilloscope source, item 4).
- Filled or duotone icons — outline only.
- Logo placed on a busy photograph.
- Text or mark set inside Instagram Zone C, or a primary element outside Zone A
  (`social/zones.json`: on 1080×1920 Zone A is x 65..1015, y 269..1248).

---

```json
[
  {"id": "cream-terracotta", "description": "Warm cream background with terracotta/clay accent near #F4F1EA / #D97757", "check": {"type": "hex-family", "value": ["#F4F1EA", "#D97757"]}},
  {"id": "near-black-acid-accent", "description": "Near-black background with single acid-green or vermilion accent", "check": {"type": "hex-family", "value": ["acid-green", "vermilion"]}},
  {"id": "fake-black", "description": "Tinted near-black used as true black", "check": {"type": "hex-family", "value": ["#0B0B0B", "#111", "#111111"]}},
  {"id": "purple-gradient-hero", "description": "Purple/indigo gradient used as hero background", "check": {"type": "regex", "value": "(linear|radial)-gradient\\([^)]*#?(6[0-9a-f]{2}|7[0-9a-f]{2}|8[0-9a-f]{2})[0-9a-f]{3}"}},
  {"id": "any-gradient", "description": "Any linear/radial gradient used as decoration", "check": {"type": "css-property", "value": "linear-gradient|radial-gradient"}},
  {"id": "uniform-radius", "description": "Rounded corners applied uniformly regardless of hierarchy", "check": {"type": "css-property", "value": "border-radius > 0"}},
  {"id": "soft-card-shadow", "description": "Identical soft grey drop shadow under every card", "check": {"type": "css-property", "value": "box-shadow"}},
  {"id": "default-sans-fonts", "description": "Default generative-model fonts instead of IBM Plex", "check": {"type": "font-family", "value": ["Inter", "Roboto", "Open Sans", "Lato", "Geist", "Space Grotesk", "Instrument Serif"]}},
  {"id": "emoji-as-icon", "description": "Emoji characters used where an icon is required", "check": {"type": "unicode-range", "value": "U+1F300-1FAFF,U+2600-27BF"}},
  {"id": "allcaps-eyebrow", "description": "Tracked-out all-caps label above a heading", "check": {"type": "css-property", "value": "text-transform: uppercase"}},
  {"id": "middot-metastring", "description": "Meta string joined with middle dots (A · B · C)", "check": {"type": "regex", "value": "\\s·\\s"}},
  {"id": "emdash-label", "description": "Label built as WORD — fragment with spaced em dash", "check": {"type": "regex", "value": "\\s—\\s"}},
  {"id": "arrow-cta", "description": "Arrow glyph appended to link or button text", "check": {"type": "regex", "value": "→\\s*$"}},
  {"id": "color-outside-tokens", "description": "Hex colour literal not referenced through a token", "check": {"type": "regex", "value": "#[0-9a-fA-F]{3,8}(?!.*var\\(--)"}},
  {"id": "font-outside-plex", "description": "Font family other than IBM Plex Sans / Plex Sans Condensed / Plex Mono", "check": {"type": "font-family", "value": "not-ibm-plex"}},
  {"id": "centered-text", "description": "Text-align set to center", "check": {"type": "css-property", "value": "text-align: center"}},
  {"id": "filled-duotone-icon", "description": "Icon variant other than outline", "check": {"type": "regex", "value": "(fill|duotone|solid)-icon"}}
]
```
