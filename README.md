# ArchFlow Content Engine

ArchFlow Content Engine is a local-first research, content-strategy, and frame-by-frame previsualization project. Its active North Hux lane focuses on AI-agent integration in business for two product-manager creator accounts: practical PM/integration and governed agent operations.

The project is intentionally separated from the ArchFlow website and product runtime. Its first delivery phase stops before provider-backed video generation. It produces a traceable research corpus, link ledgers, segmented analyses, 10–15 original video plans longer than 15 seconds, storyboard frames, one contact-sheet image per video, captions, and one prompt/report PDF per video. Figma and final media production remain approval-gated.

## Current truth — 26 August 2026

- The deterministic YouTube broad screen is frozen at 10,000 public videos from 1,010 creators. It is not 10,000 qualified competitors; current strategic distributions use 2,949 deterministic analysis-eligible videos.
- A 300-account / 900-video calibration was independently reviewed at `PASS_WITH_LIMITATIONS`; 211/250 reviewed candidates were accepted.
- Public transcript and compact storyboard collection is running with independent denominators, typed gaps, content hashes, and a 15 GiB free-disk reserve.
- Local PostgreSQL migrations through `008` provide evidence attempts, full transcript segments, frame pointers, analysis lineage, strategy releases, ten scripts, 100 shot plans, and validated EDL seams.
- Ten original 30-second YouTube-first scripts and 100 separate 9:16 SVG frame plans are available under `outputs/video-plans/north-hux-youtube-10-v1/`.
- The detailed English market-to-Studio report is generated under `outputs/reports/` and must be regenerated after the terminal evidence freeze.
- Agent Reach currently proves read-only backends only for YouTube (`yt-dlp`), RSS (`feedparser`), and generic web pages (`Jina Reader`). Other named social channels are not yet proved reachable.
- The owner-designated public repository is `mcharniuk1-spec/content_creator`; only a reviewed public-safe package may be pushed.
- OpenMontage, Sherlock, and Open-Generative-AI were assessed as candidate tools or references. None has been cloned, installed, invoked, or embedded here.
- No API key, paid provider, social login, Figma mutation, private media, voice clone, video generation, publication, or deployment has been used.

## Start here

Open a new agent task with this folder as its working directory, then read [the public handoff](docs/handoff/current-public-handoff.md), `AGENTS.md`, and the full system blueprint. Owner credentials and private identity handoffs are intentionally not distributed in Git. The next agent must recover the applicable admission/capability state before any live collection or external mutation.

Core references:

- [Full system blueprint](docs/full-system-blueprint.md)
- [Database backup and restore](docs/database-backup-restore.md)
- [Public repository setup](docs/repository-setup.md)
- [Obsidian and WikiLLM setup](knowledge/obsidian-wikillm-setup.md)
- [Architecture](docs/architecture.md)
- [Hybrid existing-video editing pipeline](docs/hybrid-editing-pipeline.md)
- [Role hierarchy](docs/role-hierarchy.md)
- [Research and analysis contract](docs/research-and-analysis-contract.md)
- [Tool fit and boundaries](docs/tool-fit-and-boundaries.md)
- [Previsualization and Figma](docs/previsualization-and-figma.md)
- [Media production boundary](docs/media-production-boundary.md)
- [ArchFlow context capsule](knowledge/context-capsule.md)
- [Initial topic backlog](knowledge/initial-topic-backlog.md)
- [Channel capability receipt](config/channel-capabilities.json)
- [Source manifest](config/source-manifest.json)

## Folder map

```text
content-engine/
  AGENTS.md
  HANDOFF_PROMPT.md
  config/                 verified capabilities and source registry
  docs/                   architecture, roles, operations, and tool policy
  knowledge/              reviewed local memory and topic hypotheses
  research/               run-local social, video, static, ad, and publication evidence
  schemas/                validation-ready durable object contracts
  templates/              ledgers, analysis forms, contact-sheet and report specs
  outputs/                generated contact sheets, reports, and Figma handoff packages
  runs/                   admissions, task contracts, execution receipts, and reviews
```

## Phase gates

| Phase | Deliverable | Current state |
|---|---|---|
| 0 | Local routing, schemas, capability and source manifests, handoff | Complete with limitations |
| 1 | Bounded public YouTube research and evidence ledgers | 10K cohort frozen; transcript/frame evidence in progress |
| 2 | YouTube topic/format/hook/story/CTA analysis | Implemented; final rerun waits for evidence freeze |
| 3 | Ten original scripts, shot plans, frames, EDLs, and report | Implemented; owner review pending |
| 4 | Figma page/frame delivery | Blocked until identity verification and mutation approval |
| 5 | Provider-backed image/video/audio generation and editing | Blocked until provider, key, budget, rights, and data approvals |
| 6 | Publishing and analytics readback | Separately blocked |
