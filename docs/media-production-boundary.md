# Media Production Boundary

This document specifies future execution; it does not authorize it.

## Phase 1: now

Allowed: research, text analysis, prompt design, plot, captions, frame/shot manifests, local storyboard previews under an approved image-generation task, contact sheets, PDF reports, screen-recording scripts, audio plans, OpenMontage-compatible manifests, and Figma delivery plans.

Disabled: provider-backed video, paid image/audio calls, dependency installation, private media, real-person voice/likeness, screen recording of authenticated/private systems, final montage runtime, publishing, and analytics account access.

## Future generation split

### GPT Image / image provider

Use for base plates, keyframes, backgrounds, illustrations, cutaways, and repair plates. Generate editable text/UI/chart overlays separately. Keep prompt, model/tool route, source/reference rights, seed/reference information when available, and output hash.

### Video provider classes

Route per shot, never by a global “best model” label:

- text-to-video for nonidentity atmospherics and abstract motion;
- image-to-video for continuity from approved keyframes;
- start/end-frame control for deliberate transitions;
- product/UI motion through deterministic composition or screen capture rather than hallucinated interfaces;
- talking head only with exact identity, consent, disclosure, and provider approval.

Every shot has duration, start/end references, subject/product IDs, camera/motion, required and forbidden changes, dialogue timing, cost ceiling, fallback, and acceptance checks.

### Screen capture

Treat as a separate lane before final assembly:

1. exact app/route/account/data approval;
2. synthetic or approved demo data;
3. fixed viewport and build identity;
4. scripted cursor/click/type/pause choreography;
5. notifications and unrelated windows closed;
6. preflight for secrets, customer data, IDs, and private URLs;
7. clean master capture;
8. segment review and redaction;
9. route/script/timestamp/hash receipt.

Never perform or record production writes for marketing footage.

### Voice, music, ambience, and SFX

Keep separate stems. Lock narration timing before generation. Prefer owner-recorded narration or approved neutral TTS. Voice cloning or likeness based on owner videos is blocked until exact consent, identities, permitted scripts/channels, provider, data retention/deletion, revocation, disclosure, and misuse controls are approved.

### OpenMontage and deterministic edit

The Content Engine remains the governance/state/evidence layer. OpenMontage may later receive an approved scene plan, asset manifest, takes, and prompts and return timeline/edit artifacts and QA receipts. FFmpeg should probe, normalize, trim, scale, crop, concatenate, mix, caption, mux, and validate. Remotion/HyperFrames may create typed motion graphics and contact-sheet/timeline compositions after dependency and license review.

Suggested production order:

1. freeze approved candidate and shot manifest;
2. generate/approve keyframes and static layers;
3. capture deterministic screen segments;
4. generate only the required short video shots;
5. record/generate narration;
6. generate/license music and SFX stems;
7. assemble rough cut from immutable timeline manifest;
8. picture lock;
9. dialogue edit, music/SFX mix, captions, graphics, and color normalization;
10. export 9:16 master and separately recomposed 4:5/1:1/16:9 variants as needed;
11. independent factual, visual, audio, accessibility, rights, and codec QA;
12. owner finalization gate;
13. separate publication approval and readback.

## Approval packet before API keys

The next agent must not ask for generic API keys. It must first present an exact packet containing:

- provider and official documentation;
- exact capability/model at the time of activation;
- intended content class and one bounded prompt/shot;
- data sent, region, retention, training policy, deletion path, and commercial rights;
- credential storage path and masked key name;
- expected cost ceiling, retry/polling/cancellation policy;
- fallback provider or deterministic alternative;
- consent/identity/rights status;
- independent reviewer verdict.

Only after owner approval may the key be configured through an approved secret store. Keys never enter Markdown, logs, prompts, Git, screenshots, or browser-visible client code.

