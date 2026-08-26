# North Hux Content Engine — public-safe handoff

Status: `IMPLEMENTED / EVIDENCE_COLLECTION_ACTIVE / PASS_WITH_LIMITATIONS`

## Delivered

- Frozen YouTube broad screen: 10,000 public videos across 1,010 creators, with 4–10 videos per creator and a maximum creator contribution of 0.1%.
- Deterministic strategic subset: 2,949 relevance-positive videos. It is the denominator for topic, format, hook, storytelling, CTA, and descriptive public-metric distributions.
- Prior calibration: 300 accounts / 900 videos; independent review accepted 211/250 sampled candidates.
- Evidence layer: content-addressed transcript and frame attempts, de-rolled timestamped speech, typed gaps, local-only storyboard frames, public metric snapshots, and bounded calibration comments.
- Database: PostgreSQL migrations through `009`, shared artifact lineage, canonical transcript identity, run/source observations, corrected current-state Studio gates, terminal freeze receipts, transcript segments, frame pointers, analysis artifacts, strategy, scripts, shots, and EDL segments.
- Strategy: two product-manager creator tracks, eight search territories, seven recurring franchises, and a ten-episode sequence.
- Studio package: ten original 30-second scripts, 100 timecoded shots, 100 separate 9:16 SVG frame files, ten contact indexes, and ten validated EDL plans.
- Report: 42-page English market-to-Studio PDF, rendered and visually inspected; terminal regeneration waits for the evidence freeze.
- Notion: owner-facing dashboard, Kanban, execution detail, and human-review views with public-safe aggregates and explicit gates.

## Truth boundaries

- The 10K cohort is a search-ranked broad screen, not 10,000 qualified competitors or a probability sample.
- YouTube short-duration metadata does not prove native Shorts placement.
- Transcript, frame, comment, and native-Short evidence have independent denominators.
- Public competitor metrics do not expose complete shares, sends, saves, retention, impressions, conversion, or viewer demographics through the admitted route.
- Source transcripts, comments, media, frames, raw responses, credentials, database files, and backups are local-only and excluded from this repository.

## Human gates

1. Review the ten scripts, assign presenters, and choose the first three episodes.
2. Approve the owned proof/UI surface for each selected episode.
3. Approve or reject the optional two-second AI context insert; it can be replaced by creator footage.
4. Record four A-roll windows per selected episode, two takes each, plus room tone.
5. Approve any provider, cost, prompt, rights, and retention packet separately.
6. Approve the exact editing mutation packet after owner media is received.
7. Review each rough cut and authorize publication separately.
8. Approve the exact external Obsidian target-note correction packet before vault mutation.

## Start here

- `docs/full-system-blueprint.md`
- `docs/database-backup-restore.md`
- `docs/repository-setup.md`
- `knowledge/obsidian-wikillm-setup.md`
- `outputs/video-plans/north-hux-youtube-10-v1/campaign-manifest.json`

Run tests before operating live adapters. Provider-backed generation, final editing, publishing, deployment, and social engagement are not part of the provider-disabled research package.
