# 🛰️ North Hux M2 Market Intelligence — Control Dashboard

- Notion URL: https://app.notion.com/p/3c70bd21ed6a811a8d9fc1f8312cd8fa?pvs=204
- Page path: AI Startup Workspace / Content Engine
- Last edited: 2026-08-26T15:26:53.495Z
- Note: Standalone dashboard named directly in the audit brief. Contains four linked/inline databases dumped separately: "North Hux — Progress by Platform and Category" (collection://bffc0e55-d548-43eb-8564-dce78336c02c), "North Hux — Best References and Category Review" (collection://f101a131-92c4-4c61-aba0-c39a80862876), "North Hux — Sol Review Queue" (collection://d2e55829-07c0-40a4-951e-96d2427ab289), "North Hux — Content Engine Delivery Board" (collection://b841a493-8ea5-4bbd-90e8-73814250c75f). Also references a report page https://app.notion.com/p/3c70bd21ed6a81a68411f4ee974582b7 and a PDF attachment (north-hux-youtube-10k-market-and-studio-report.pdf).

---

> **North Hux M2 is the controlled research and evidence layer for ArchFlow.** This dashboard separates Instagram, TikTok, and YouTube Shorts and tracks account discovery, posts, public metrics, captions, comments, transcripts, video analysis, frame analysis, review, and projection status.

## Owner and operating model
- **Execution owner:** Codex — adapters, local PostgreSQL, raw/evidence storage, five-strike QA, mechanical consistency, exports, and dashboard synchronization.
- **Strategic reviewer:** Sol — review questions, pattern interpretation, competitor classification, qualitative codebook, and recommendation blocking.
- **Target frame:** 10,000–12,000 qualified platform accounts per platform; separate platform denominators.
- **Audience:** U.S. and English-speaking audiences first; UK, Canada, Australia, Ireland, New Zealand, and relevant English-language European segments.
- **Primary content:** product/company operators, solo creators, creator groups, agile building, AI-agent integration, business adaptation, governed workflows, and modern operating models.

## Evidence rule
A platform count, audience signal, transcript, frame, or demographic is only published with its platform, source route, observation time, field semantics, and evidence state. Missing is null, not zero. Public competitor metrics are not treated as owned analytics.

## Analysis sections per content item
1. **Caption** — caption text, hook, hashtags, mentions, CTA, offer, language, and caption evidence.
2. **Post stats** — views, likes, comments, shares, reposts, saves/favourites, followers, snapshot time, metric definition, and completeness.
3. **Transcript** — native captions/subtitles first, provider transcript second, local ASR only when approved; timestamped segments and quality.
4. **Video** — content type, narrative beats, claim/proof/caveat, voice, screen, B-roll, audio, pacing, and creator response.
5. **Framing** — frame sequence, OCR, shot boundaries, visual hook, text density, proof placement, cut map, and frame rights.
6. **Audience** — questions, pain, objections, confusion, requests, implementation evidence, buying intent, creator replies, and reviewer opinion.
7. **Decision** — direct competitor, adjacent, technical authority, format leader, counterexample, or noise; plus PM-A/PM-B relevance.

## Progress meaning
Progress is reported separately by platform and category. Verified means records passed the adapter/schema/evidence/review gate, not merely that a URL was seen. Blocked means an external, rights, access, or owner gate prevented work. Partial means the platform returned incomplete fields and the missingness is recorded.

## Next gate
Run the 20-URL golden cohort and 100–300 account calibration before any 10k–12k expansion. Instagram and TikTok remain access-gated until their approved routes are proven.

Linked databases (see separate dumps):
- https://app.notion.com/p/4924bfe3640e429baee4f986e155f409 — North Hux — Progress by Platform and Category (collection://bffc0e55-d548-43eb-8564-dce78336c02c)
- https://app.notion.com/p/1388b98281cf4bc1ae276f4afe48e7e1 — North Hux — Best References and Category Review (collection://f101a131-92c4-4c61-aba0-c39a80862876)
- https://app.notion.com/p/d1562d73ec994e07b0495d12e9398d3d — North Hux — Sol Review Queue (collection://d2e55829-07c0-40a4-951e-96d2427ab289)

## Local source of truth
The machine-readable source of truth will be the local North Hux PostgreSQL schema, with raw objects and permitted media/frame artifacts stored separately. This page is a review and presentation projection. It must never be treated as the only copy of the dataset.

## Current gate
The next execution gate is a 20-URL golden cohort followed by 100–300 account calibration. A 10,000–12,000 account frame is not claimed until platform routes, rights, metric semantics, duplicate controls, transcript quality, and human review gates pass.

## 2026-08-25 collection run — owner scope confirmed
The owner-confirmed research scope is now frozen: 10,000–12,000 qualified accounts per platform (Instagram, TikTok, YouTube); United States, Canada, United Kingdom, Australia, New Zealand, Ireland, and all current EU member states; English preferred but relevant non-English records may remain with language recorded; no quotas; local retention approved for comments, transcripts, permitted media, and frame artifacts; public Notion projection approved by the owner.

EU reference: [European Union — EU countries](https://european-union.europa.eu/principles-countries-history/eu-countries_en). The EU list is maintained separately from the United States, Canada, United Kingdom, Australia, and New Zealand comparison markets.

### Current evidence progress

| Category | Instagram | TikTok | YouTube | State |
|---|---|---|---|---|
| Candidate accounts | 12 | 0 | 10 channel IDs | observed seeds/metadata |
| Candidate posts | 14 | 0 | 12 metadata records | observed, not census |
| Public view counts | unavailable | unavailable | 12 | observed where returned |
| Likes/comments/shares/reposts/sends | null/gap | null/gap | null/gap except no returned fields | never converted to zero |
| Captions/descriptions | not collected | not collected | 12 descriptions present | metadata-only |
| Transcripts/comments | 0 | 0 | 0 | blocked/not admitted |
| Video/media/frames | 0 | 0 | 0 | independently rights/route-gated |
| Qualified accounts | 0 | 0 | 0 | calibration not complete |

The three execution lanes produced: (1) YouTube local metadata audit; (2) Instagram/TikTok official-route and seed-admission audit; and (3) local corpus quality/taxonomy audit. The current PostgreSQL calibration layer contains 38 registered sources, 50 raw objects, 23 platform-account records, and 26 content records. It is a local source of truth; this page is a redacted dashboard projection.

### Operating decision
PASS_WITH_LIMITATIONS for schema, provenance, null semantics, taxonomy, and bounded seed/metadata calibration. BLOCKED for representative market claims, 10–12K completion, cross-platform performance comparison, complete comments/reposts/sends, transcript coverage, full-video analysis, and frame-by-frame reference coverage.

No social login, cookies, private access, unofficial scraping, publishing, deployment, provider generation, or paid execution occurred. The dashboard is owner-approved for public projection; the connector does not independently expose its sharing permission state.

### Next approval gates
1. Admit an official Instagram route for the intended public competitor scope, if an eligible route exists.
2. Confirm TikTok Research API eligibility, field catalog, token handling, rate limits, terms, and retention.
3. Admit a Shorts-specific YouTube public route and replay a 20–50 URL golden cohort.
4. Confirm the exact local retention period and backup/encryption policy for comments, transcripts, media, and frames.
5. Review Sol's strategic decision memo before expanding beyond calibration.

## 2026-08-25 social-adapter calibration — current verified state
> **CALIBRATION / NOT REPRESENTATIVE.** This run proves collection, evidence, database, review, and Studio-gate mechanics. It does not prove platform prevalence, demographics, trends, winners, demand, ROI, or a completed 10–12K census.

### What was collected

| Measure | YouTube result | Evidence boundary |
|---|---|---|
| Observed videos | 41 | Six overlapping public search queries; 30 returned channel IDs |
| Short-form state | 9 duration candidates | No native Shorts URL; duration alone does not prove Shorts |
| Comments | 660 rows / 111 replies | Maximum 20 per video; incomplete pagination; not audience prevalence |
| Subtitle artifacts | 94 across 41 videos | Local analysis only; four alternate-track HTTP 429 gaps recorded |
| Media and frames | 0 | No video, audio, image, or frame bytes downloaded |
| Qualified accounts | 0 | Qualification and independent review remain open |

### Local source of record and Studio boundary
The local PostgreSQL layer now contains 76 registered sources, 224 raw objects, 49 platform-account records, 64 content records, 660 comments with pseudonymized author storage, 94 transcripts, 111 reply edges, and 60 immutable Studio exports. Sixty-four social content records are visible as Studio candidates; zero are eligible. Social export remains closed until content-specific evidence, all 12 Studio axes, current rights, maker/reviewer separation, an active independently reviewed `signal-to-studio.v1.1` contract, and a separate public-safe release review pass.

### Platform route decision
- **YouTube:** bounded public `yt-dlp` calibration is working. The durable proposed route is [YouTube Data API v3](https://developers.google.com/youtube/v3/docs), subject to an owner-approved API project, quota, compliance, and secret-storage fixture.
- **TikTok:** the official [Research API](https://developers.tiktok.com/docs/en/about-research-api) has the richest documented fields but is eligibility, approval, purpose, and terms gated. No scraper fallback is approved.
- **Instagram:** Meta's [Instagram Platform](https://developers.facebook.com/docs/instagram-platform/overview) is Professional-account and permission scoped; it cannot support the originally requested arbitrary public-account census.

### Sol independent review
Verdict: **PASS_WITH_LIMITATIONS** for provider-disabled calibration and fail-closed architecture. Blocked for representative findings, 10–12K scaling, social-to-Studio activation, and any public performance/winner claim.

Sol recommends two distinct tracks:
1. `PM_AI_INTEGRATION` — practical agent-enabled product and business workflows, integration, adoption, measurement, and recovery.
2. `GOVERNED_AGENT_OPERATIONS` — ArchFlow-like provenance, permissions, evaluation, human gates, observability, rollback, and knowledge promotion.

The 12 current owner decisions are now in the Sol Review Queue. The best-reference table contains 15 observed links ranked only for review priority; raw views are not presented as strategic winners.

### Verification
- Collection validator: `PASS_WITH_GAPS`.
- Integrated run verifier: `PASS_WITH_LIMITATIONS`; 361-file hash manifest at final verification.
- PostgreSQL: no metric null-semantics violations, no comment-pseudonym violations, no missing run raw pointers.
- Python suite: 40/40.
- Studio library: 60 frameworks, 390 frames, and 120 schema validations.
- External provider generation, publication, deployment, social engagement, login/cookies, private access, paid execution, and source-media download: **not run**.

The connector can verify page/database writes but cannot independently prove anonymous sharing permissions. An unauthenticated readback remains an explicit owner gate before treating this page as a verified public release.

## 2026-08-25 owner access decisions — approved
- **OD-02 passed:** retain 10,000–12,000 qualified accounts as the terminal target per platform. The 100–300 account calibration and independent quality gate still precede scale.
- **OD-03 passed:** official YouTube Data API v3 fixture approved. Owner Google Cloud setup and a restricted Keychain-stored API key remain pending.
- **OD-07 passed:** all codebook strata approved. No account may contribute more than 1% of analyzed content items to an aggregate cohort.

### Platform access decision
- **YouTube:** official [YouTube Data API v3 setup](https://developers.google.com/youtube/v3/getting-started) is the scalable route.
- **TikTok:** [Research Tools](https://developers.tiktok.com/products/research-api/) can support broad public research data but explicitly require independent non-commercial/public-interest eligibility. For this commercial competitor objective, the viable broad route is a contractually reviewed licensed data provider. [Display API](https://developers.tiktok.com/docs/en/display-api-overview) is creator-consent based; [Commercial Content API](https://developers.tiktok.com/products/commercial-content-api) covers ads and is supplementary.
- **Instagram:** the official [Meta Instagram API](https://www.postman.com/meta/workspace/instagram/documentation/23987686-9386f468-7714-490f-9bfc-9442db5c8f00) supports Business/Creator accounts and Business Discovery/Hashtag Search, not personal accounts or every competitor interaction. Eligible institutional researchers may separately consider [Meta Content Library](https://www.icpsr.umich.edu/sites/somar/meta-content-library).

Credentials, tokens, cookies, app secrets, and account identifiers must not be placed on this page. Provider readiness is recorded only as yes/no state.

## YouTube census execution update — 25 August 2026
> **Official route verified:** one secret-safe YouTube Data API `search.list` fixture passed. Its raw artifact is content-addressed and a repeat check resumed locally without another API request.

> **Scale is blocked by terminal review:** after three repair loops, the collector still lacks a real content-level 1% contribution gate and an enforced single-writer/atomic terminal-strike boundary. No 10K crawl, transcript batch, or media/frame batch ran.

### Current denominators

| Stage | Target | Completed | State |
|---|---|---|---|
| Official API fixture | 1 | 1 | Verified |
| Calibration accounts | 100–300 | 0 | Blocked pending collector PASS |
| Qualified account frame | 10,000–12,000 | 0 new | Blocked |
| Top reference transcripts | 100 | 0 new | Blocked after qualification |
| Top reference framing sets | 100 | 0 new | Blocked after rights and qualification |

### Reviewed method now frozen
- Channel-first discovery with separate search, enrichment, qualification, analysis, and top-100 stages.
- Sixteen multi-label agentic/business content categories; one primary category only for allocation.
- Transcript precedence: human/native subtitle → native automatic caption → separately approved provider transcript → rights-approved local ASR → explicit gap.
- Format states remain separate: native Short, duration candidate, non-Short, and unknown.
- Public Notion keeps only aggregate progress, methods, reviewed links, and blockers. Secrets, raw responses, comments, transcripts, media, and frames stay local.

### Next safe packet
1. Enforce one collector process per run and prove no request can pass a terminal strike/block.
2. Apply the 1% rule to actual content-analysis rows and prove one-post-per-creator for the top 100.
3. Re-run independent terminal review.
4. Only after PASS: execute 100–300 calibration, measure precision/duplicates/strata, then expand in 1K → 3K → 10K stages.

## YouTube 300-account calibration complete — corrected final state, 26 August 2026
> **PASS_WITH_LIMITATIONS:** 300 broad-screen accounts / 900 videos are complete, with repaired transcript normalization, independent relevance calibration, and run-scoped provenance verification. The terminal 10–12K census is not claimed.

- **Accounts/videos:** 300 / 900, exactly three videos per creator; maximum creator contribution 0.33%.
- **Format:** 872 duration candidates; 0 native Shorts claims proved.
- **Transcripts:** 772 sources / 128 gaps; 73,339 preserved raw caption cues and 38,960 de-rolled speech increments. Transcript-derived analysis was regenerated after a 2.91× median rolling-caption expansion was identified.
- **Independent review:** Sol reviewed all top 100 plus 150 stratified non-top videos. 211/250 (84.4%) were accepted as direct, technical-authority, or adjacent relevance; 11 were format-only, 27 excluded, and 1 unresolved.
- **Comments:** 898 rows across 204 videos; 16 endpoint gaps; first relevance page only. Comment rows now link to their own comment-page raw evidence.
- **Visuals:** 100 sets / 943 frames: 60 full public-media and 40 storyboard fallbacks; 71 vertical, 27 horizontal, 2 square/unknown; all local-only.
- **Database:** run-scoped PostgreSQL readback covers raw and de-rolled transcripts, comment-page provenance, 250 reviewer classifications, metrics, media, and frames.
- **Report:** page https://app.notion.com/p/3c70bd21ed6a81a68411f4ee974582b7 (not fetched in this pass — see INDEX.md "could not fetch" list, out of the requested scope but flagged for completeness).
- **Reference table:** all 100 rows now carry Sol relevance tier, refreshed de-rolled topic/hook/story labels, and pass/limited/blocked status.
- **PDF:** 35 A4 pages with topics, video types, hooks, storytelling, audience evidence, visual framing, two-account strategy, 15-video sequence, three detailed scripts, database architecture, and owner gates.

Next safe action: owner reviews the report, scripts, and 100 references. Any further YouTube expansion must tighten admission using the measured 15.6% non-acceptance pattern. Backup, production, publishing, and owned analytics remain separate approvals.

Linked database: https://app.notion.com/p/026770cd3ac24f26819e3f7e90e88174 — North Hux — Content Engine Delivery Board (collection://b841a493-8ea5-4bbd-90e8-73814250c75f)

## 2026-08-26 Content Engine integration and delivery control
> **Execution is terminally frozen with limitations.** The 10,000-video evidence set, aggregate analysis, ten scripts, 100 shot plans, PostgreSQL load, restore proof, final PDF, Git delivery, and Notion projection are complete. Provider generation, personal-media ingestion, editing mutation, publishing, and owned analytics remain separate owner gates.

- North Hux — Content Engine Delivery Board — Kanban, execution detail, and human-review views with explicit done/how/needed/human-action fields.
- Frozen cohort: **10,000 public YouTube videos / 1,010 creators**, including the immutable 900-video calibration baseline; maximum creator contribution is **0.1%**.
- Strategic position: two complementary product-manager creators own the missing operating layer between an AI demo and a dependable business workflow—workflow diagnosis and integration on one account; authority, evidence, evaluation, and recovery on the other.
- Visual rule: creator A-roll and deterministic UI/evidence carry the proof. AI-generated B-roll is optional, limited, and never treated as evidence.
- Local PostgreSQL and run artifacts remain the source of record. Notion contains only public-safe aggregates, methods, reviewed links, statuses, and decisions.

## 2026-08-26 market → Studio implementation checkpoint
> **The multi-engine path is now implemented and reviewable.** A 10,000-video YouTube broad screen feeds a 2,949-video deterministic strategic subset, a two-account content strategy, ten original scripts, 100 separate frame plans, ten EDLs, and local PostgreSQL lineage.

| Layer | Implemented state | Truth boundary / next gate |
|---|---|---|
| Market | 10,000 videos / 1,010 creators; topics, formats, hooks, story, CTAs, top 100 | Broad screen, not 10,000 qualified competitors; terminal transcript/frame attempt identities are frozen |
| Strategy | Creator A: PM/integration. Creator B: governed agent operations. Eight territories and seven franchises. | Owner assigns presenters, tone, and first three launch episodes |
| Scripts and Studio | Ten original 30-second packages, 100 separate 9:16 frame files, ten validated EDLs | Owner review pending; creator footage, provider generation, editing mutation, and publishing are separate gates |
| Database | 10K content and analysis rows; transcript text segments; frame pointers; artifact lineage; strategy, scripts, shots and EDLs | Terminal load, 12-table restore proof, and freeze receipt passed |
| Report | 42-page English market and Studio report visually inspected | Terminal report regenerated and attached below |

### Production grammar
- **40% creator A-roll** — original presenter recording and interpretation.
- **40% deterministic UI/evidence** — owned or synthetic-data proof surface.
- **6.7% optional AI B-roll** — context only; never proof, results, UI, people, or likeness.
- **13.3% end card** — one useful next action.

### Owner decisions now
1. Review the ten scripts and assign Creator A / Creator B.
2. Select the first three launch episodes.
3. Approve each owned proof/UI demonstration.
4. Approve or reject the optional two-second AI context slot per episode.
5. Record the four specified A-roll windows per selected episode.
6. Approve provider generation, Resolve mutation, and publication only through their separate packets.

## 2026-08-26 terminal YouTube 10K delivery
> **PASS_WITH_LIMITATIONS / TERMINALLY FROZEN.** The evidence, database, backup, report, and current Studio release now have matching terminal receipts. The run rejects further analyzer or loader mutation.

- **Market corpus:** 10,000 public YouTube videos across 1,010 creators; maximum creator contribution 0.1%. This is a search-ranked broad screen, not 10,000 qualified competitors or a probability sample.
- **Strategic denominator:** 2,949 deterministic analysis-eligible videos.
- **Transcripts:** 10,000 canonical attempts; 7,677 observed and 2,323 typed gaps; 829,490 de-rolled speech segments.
- **Visuals:** 10,000 canonical attempts; 120 observed compact storyboard sets / 1,042 frames; 9,880 typed gaps. No full videos or audio retained.
- **Current Studio release:** two PM creator tracks, ten scripts, 100 shots, and ten edit plans. Optional AI B-roll is context only and never evidence.
- **Database:** exact 10K current analysis and attempt identities; 42 MiB local PostgreSQL dump; disposable restore matched 12/12 critical table counts.
- **Integrity:** 47,266 local-only run files hashed; terminal receipt version 1; 140 tests plus 9 subtests; independent Spark review PASS.
- **GitHub:** [public-safe repository at commit 6790715](https://github.com/mcharniuk1-spec/content_creator/commit/6790715).
- **Report SHA-256:** `8edd1d0551347fe3c324984f1d195073ae6d78c41743710b1e5f50b9477144f8`.

### Final report
PDF attachment (not downloaded — is a .pdf, outside the download rule which allows only .csv/.md under 20 MB): `north-hux-youtube-10k-market-and-studio-report.pdf` (attachment id eb0c9971-0267-481d-b2ec-e7b47ee1ed2f).

### Human actions still required
1. Assign Creator A and Creator B; approve or revise the ten scripts.
2. Select the first three launch episodes.
3. Approve each owned proof/UI demonstration.
4. Approve or reject each optional two-second AI context slot.
5. Record the specified A-roll windows, two takes each, plus room tone.
6. Separately approve any provider, budget, prompt, rights, and retention packet.
7. Separately approve Resolve/editing mutation and publication after rough-cut QA.
8. Approve the exact seven-file Obsidian correction packet before external vault mutation.
