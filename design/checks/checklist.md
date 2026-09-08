# Pre-publish checklist

## Before anything is published

1. Can the topic and the verdict be understood with the sound off?
2. Is it recognizable as M2 with the handle hidden?
3. Is the proof ours?
4. Is a human review step named?
5. Does the closing line give an action the viewer can take alone?

## Mechanical checks

1. `node checks/lint.mjs templates/<name>/`
2. `node checks/contrast.mjs`
3. `node social/overlays/check-overlay.mjs <placement-id>`

## Sampling rule for batches

When more than 10 assets are rendered in one batch: inspect a fixed 10% sample,
chosen by every k-th file (k = batch size / 10, rounded down, minimum 1), decided
before rendering — not after seeing results — plus every asset whose hook hit the
character cap (tokens.json measure.hook-chars, 20/line).
