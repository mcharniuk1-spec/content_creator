# Tool Fit and Boundaries

## Agent Reach

Role: channel capability discovery and read-only routing. Run `agent-reach doctor --json` before every multi-platform research run, store a sanitized receipt, and use only `active_backend` values.

Current proved routes are YouTube via `yt-dlp`, RSS via `feedparser`, and generic web pages via Jina Reader. This does not prove LinkedIn, X, Threads, Instagram, TikTok, Reddit, Facebook, Bilibili, ad-library, or publication-database access. Unproved channels are gaps, not substitutes.

Prohibited by default: installing backends, reading/importing browser cookies, authentication, private or logged-in surfaces, posting, commenting, liking, following, messaging, or scheduling.

## Sherlock

Source: `sherlock-project/sherlock`, MIT-licensed public repository.

Fit: public username candidate discovery across many networks for an owner-approved brand, company, or product handle. It can help inventory where a known public brand name may appear.

Not fit: content search, trend detection, post/video retrieval, engagement analysis, account ownership proof, person/prospect enrichment, deanonymization, or private-identity linkage. A hit is an unverified candidate until independently confirmed through the canonical public profile and ownership context. Do not use options that intentionally broaden false positives in production research.

Current phase: reference-only; not cloned or installed.

## OpenMontage

Source: `calesthio/OpenMontage`, AGPL-3.0 public repository.

Observed fit:

- reference-video analysis into transcript, pacing, scenes, keyframes, and style abstractions;
- research → proposal → script → scene plan → assets → edit → compose workflow;
- scene-by-scene living storyboard/contact-sheet approval;
- asset/take registry, prompt/cost/quality lineage;
- pipeline families such as animated explainer, talking head, screen demo, documentary montage, hybrid, and clip repurposing;
- deterministic editing and QA around FFmpeg, Remotion, HyperFrames, captions, audio mixing, probing, and frame sampling.

Recommended role: an optional production-planning, asset/timeline, and deterministic assembly adapter behind the Content Engine control plane. Reuse its ideas and schemas only after a license and architecture review; do not immediately fork it as the governance core.

Risks and gates:

- AGPL obligations may affect linked/modified/network-served use; legal/license review is required before code reuse or hosted deployment.
- Setup requires a nontrivial Python/Node/FFmpeg toolchain and may install dependencies.
- Provider integrations may require keys, transmit media, and incur costs.
- Repository claims such as pipeline/tool counts are project claims, not local readiness.

Current phase: official repository research only. No clone, setup, import, media processing, provider call, or runtime test.

## Open-Generative-AI

Source: `Anil-matcha/Open-Generative-AI`, MIT public repository.

Fit: optional model/provider catalog research, adapter inspiration, or separately audited studio surface. It may help compare model classes once official current provider documentation, costs, rights, data handling, availability, and tests exist.

Boundary: it is never the content-policy, identity, rights, approval, state, or evidence core. The Content Engine explicitly rejects any unrestricted/no-filter premise and keeps all provider calls behind its own Gatekeeper, budget, content-class, rights, and consent controls.

Current phase: reference-only. No installation, model download, MuAPI configuration, face swap, lip sync, likeness, provider key, or media call.

## Owner `content_creator` repository

Source: `mcharniuk1-spec/content_creator`.

Verified on 2026-08-11: public, default branch `main`, HEAD `b2b98aafad3a14abae90d7bd42ab5753c6ce12e2`, and only a 22-byte README containing the repository title and “hey.” The GitHub API reported repository size `0` and no detected language or license.

Interpretation: it is a placeholder target, not a reusable implementation. Do not claim code, workflows, tests, license, or architecture exists there. A future sync or remote setup is a separate Git write requiring exact owner approval and a public-safety/license check.

## Figma

Fit: editable storyboard frames, individual layer structure, componentized text and overlays, per-video sections, and review screenshots. Start with identity verification, then inspect exact target file/page. Mutation requires approval.

If the Figma connector exposes only read operations, create a local import-ready package and record `GAP: callable page/frame creation unavailable`; do not automate the browser or switch accounts without approval.

## GPT Image in Codex

Fit: operator-assisted storyboard stills, base plates, cutaways, backgrounds, and keyframes in an approved visual-generation run. Generate images separately from final typography and deterministic UI.

Distinction: Codex's internal image tool is not an application API. Future automated generation needs a separately approved API adapter, server-side secret handling, cost limits, and job receipts.

## FFmpeg, Remotion, HyperFrames, screen capture, and audio tools

They are planned production tools. FFmpeg is preferred for deterministic probing and assembly; Remotion/HyperFrames may add data-driven compositions. Screen capture is a separate synthetic/local lane. Voice, music, and SFX are separate stems. No runtime availability is claimed until a local capability check and an approved dependency plan exist.

