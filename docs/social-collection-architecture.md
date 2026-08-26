# North Hux social collection architecture

Status: `YOUTUBE CALIBRATION LIVE / INSTAGRAM AND TIKTOK GATED / 10–12K NOT CLAIMED`

## Connected now

Agent Reach proves three read routes on this device: YouTube through `yt-dlp`, RSS through `feedparser`, and public web pages through Jina Reader. Only YouTube is a social collection route. It runs without login, cookies, credentials, paid calls, or media download and is bounded to 60 videos and 20 retrieved comments per video for calibration.

The local PostgreSQL database `north_hux` is the system of record. It separates runs, adapters, jobs, source registration, raw objects, creator identities, platform accounts, content, metric definitions and snapshots, interaction coverage, comments, transcripts, media, frames, classifications, evidence, rights, reviews, progress, exports, and the Studio bridge. The raw artifact remains on disk; PostgreSQL stores its pointer, hash, capture time, retention class, and normalized facts.

The Notion page is a public-safe review projection, not the database. Obsidian is the human knowledge and navigation layer, not a replacement for PostgreSQL or raw evidence.

## How one record moves

```text
approved public route
  -> bounded collection job + five-strike receipt
  -> source registry
  -> immutable raw pointer + SHA-256
  -> account/content/metric/comment/transcript normalization
  -> evidence + rights + availability state
  -> qualitative review and taxonomy
  -> public-safe Notion/Obsidian projection
  -> reviewed social Studio candidate
  -> immutable Studio export only after every gate passes
```

Missing counters remain null. A retrieved-comment count is not presented as the platform's total comment count. Shares, reposts, sends, saves, demographic attributes, and audience opinions are stored only when a route directly returns them or a reviewer derives them with an evidence locator and epistemic label.

## Platform decisions

### YouTube

The active `yt-dlp` lane is a calibration tool for public metadata, descriptions, subtitles when exposed, and bounded comments. It is fragile because it extracts the public web surface, so it is not the 10–12K production route. The durable planned route is YouTube Data API v3 for channels, videos, counters, and comments. An API project/key, quota plan, and compliance review are owner gates. Public transcript text, shares/reposts/sends, raw media, and frames are not promised by that API.

### TikTok

TikTok Research API is the strongest documented field match: accounts, videos, views, likes, comments/replies, shares, favorites, voice-to-text, subtitles, and selected liked/pinned/reposted relationships. It is restricted to approved research and requires an eligibility decision, application, client, and token. It is not admitted as a generic commercial competitor-census route. No scraper fallback is authorized.

### Instagram

Meta's official API is scoped to Professional accounts and app/user permissions. It can support an allowlisted Business/Creator cohort, managed comments, hashtagged media, and eligible insights, but it cannot support a broad arbitrary public-account census. Consumer accounts and complete public interaction fields are outside the proved route. A Meta app and exact permission review are owner gates.

## Analysis skeleton

Each retained content record has seven review surfaces:

1. caption and post text;
2. public post statistics with definitions and completeness;
3. transcript and timestamp quality;
4. video type, agentic topic, claim, mechanism, proof, caveat, and CTA;
5. frame sequence, visual hook, OCR, shot changes, text density, proof placement, A-roll/B-roll, and pacing;
6. audience questions, pain, objections, confusion, requests, implementation evidence, buying intent, creator replies, and reviewer opinion;
7. competitive role and relevance to the two product-manager tracks.

The Studio taxonomy is separate. A social content record does not become a Studio pattern because a keyword or platform label looks similar. Eligibility requires a qualified account, passed rights, evidence, all 12 Studio axes, taxonomy review, and rights review. A future social interface contract must accept stable `SIG-SOC-*` identities before any social export is activated.

## Scaling pattern

The 10–12K target is a qualified-account target per platform, not a URL count. Scaling proceeds through a golden cohort, 100–300 account calibration, independent quality review, and only then a bounded census. The owner approved all codebook strata and tightened creator concentration: no account may contribute more than 1% of analyzed content in an aggregate cohort. Qualification requires source identity, relevance, language/region evidence, account archetype, content activity, duplicate resolution, and inspectable content observations. No platform is marked complete merely because discovery returned 10,000 handles.

## Remaining owner gates

- YouTube: create/approve a Google Cloud YouTube Data API project and quota budget.
- TikTok: decide and document Research Tools eligibility; if eligible, approve the application and credential setup through a secret manager.
- Instagram: approve a Professional-account sample frame and Meta app-review setup; accept that it is not a general public census.
- Retention: set exact retention periods, encrypted backup target, restore-test cadence, and deletion workflow for raw comments/transcripts and any future media/frames.
- Studio: review and activate a versioned social Signal-to-Studio contract; keep current social candidates gated until then.

No provider generation, publishing, deployment, social engagement, private access, or paid execution is enabled by this architecture.
