# Content Engine Studio — Short-form Previsualization

Status: `PROVIDER-DISABLED / LOCAL PREVISUALIZATION / NO FINAL VIDEO`

This Studio lane turns bounded Signal evidence into original, reusable short-form hook, intro, and B-roll plans. It does not copy source media or creator expression. The current persistence interface is file-backed because no live database has been proven.

## Sequential story library v2

The additive v2 library lives in `story-framework-library/v2/`. It contains exactly 50 causal micro-story packages and 300 ordered one-second SVG frames. Start with `SCREENWRITING-GUIDE.md`, `REAL-SHORTFORM-REFERENCE-ANALYSIS.md`, `STORY-FRAMEWORK-TAXONOMY-V2.md`, and the library `CATALOG.md`.

Build and validate:

```bash
python3 studio/build_story_framework_library.py
python3 studio/validate_story_framework_library.py
```

V2 preserves v1. External image/video/audio providers remain `NOT_RUN`; frame prompts are future provider-neutral replacement instructions.

## Current outputs

- `framework-library/v1/` — 60 six-second packages, 360 lightweight SVG frames.
- `ANALYSIS-METHOD.md` — how to analyze source videos and abstract clean-room patterns.
- `FRAMEWORK-TAXONOMY.md` — controlled hook/B-roll/editing axes and duplicate rules.
- `DATABASE-INTERFACE.md` — Signal ownership, Studio ownership, and file-backed/PostgreSQL mapping.
- `build_framework_library.py` — deterministic generator.
- `validate_framework_library.py` — timing, lineage, uniqueness, file, hash, and safety validator.

The production path is deliberately separate: approved source observation → Signal export → Studio template → owner review → later approved assets/video provider or deterministic edit. Figma remains pending and is not mutated by this run.

## Photorealistic reference library v3

`story-framework-library/v3-realistic/` adds 50 fictional clean-room visual references: one six-shot generated source sheet, six 540×960 review frames, prompts, metadata, hashes, and a compact review sheet per story. These approximate natural phone-shot social-video language; they are not reconstructions of observed creators or proof of performance. The admitted database contains zero source frames, so direct visual benchmarking remains a documented gap.

Run `python3 studio/finalize_realistic_frame_library.py` and `python3 studio/validate_realistic_frame_library.py`. Use `REALISTIC-SOCIAL-VIDEO-STYLE-BIBLE.md` for casting, framing, lighting, motion, emotion, overlay, and safety rules.
