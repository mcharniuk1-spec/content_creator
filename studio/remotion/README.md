# M2 Studio Remotion renderer

This is the primary deterministic composition runtime. It is reproducible from `package-lock.json`; no Remotion dependency is loaded by the Python research process. All assets are local, hash-verified and rights-approved. The renderer uses an explicitly supplied existing Chrome/Chromium executable and never downloads a browser automatically.

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run typecheck
npm test
node render.mjs --edl APPROVED_EDL.json --assets APPROVED_ASSET_ROOT --output REVIEW.mp4 --browser EXISTING_CHROME_BINARY
node storyboards.mjs --edls UNBOUND_PREVIS_EDL_DIRECTORY --output NEW_STORYBOARD_DIRECTORY --browser EXISTING_CHROME_BINARY
```

The renderer bundles only its source and approved local assets into temporary storage. It uses a local rendering server, then removes its own temporary bundle. Source assets remain untouched. A hash-bound receipt accompanies the output. Use `--production` only with `render_mode: PRODUCTION`, an approved EDL and all media bound. A render is still an export for review until picture, sound, claims, captions, rights, owner approval and separate publication gates pass.

Production validation also rejects pending/unplaced audio and unbuilt `graphic` visual-plan layers. Speaking cards require an explicitly placed speech stem and reviewed alignment receipt bound to the source card and speech asset hashes. Silent work must declare `speech_policy: NO_SPEECH`. Final diagrams must be bound as implemented, approved image/video assets; current visual-plan text remains preview-only.

The speech receipt's `alignment_plan_sha256` must match `alignmentPlanHash(edl)` from `contract.mjs` (Python equivalent: `m2_studio.timeline.alignment_plan_hash`). This versioned digest covers card/audio hashes, timebase, every audio stem's placement/trim/role/gain and exact caption timing/text. Both validators reject a changed plan under an old receipt. Unicode captions and gain values are normalized identically across runtimes; approval remains a separate reviewer/controller action.

The free Remotion license covers individuals and organizations of up to three people; larger collaborations require paid licensing under the current terms. Check organization eligibility before sharing the runtime across a growing team. There is no subscription to this orchestration code. See the dated source assessment in the current run's Studio lane.

Composition: 9:16 defaults at 1080×1920/30 fps; A-roll, split-screen, picture-in-picture panels, demo graphics, image inserts, editable captions, speech/music/ambience/SFX stems. Typography and scene animation are deterministic. Generated footage is an ordinary approved asset once received and validated. Captions preserve script time spans; accurate final caption alignment must use the selected owner recording/transcript. Audio stems have explicit gain; advanced ducking, color finishing and loudness normalization can use the existing FFmpeg edit pipeline before final mux.

The synthetic fixture is a reproducible implementation test. Preview placeholders do not demonstrate that footage was shot or generated. Do not serve arbitrary asset URLs, SVGs, executable user components or remote fonts. Do not run npm lifecycle scripts or add packages without review.
