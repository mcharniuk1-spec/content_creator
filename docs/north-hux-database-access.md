# North Hux Local Database Access

## Current state

- Engine: PostgreSQL 18.6.
- Database: `north_hux`.
- Port: `55432`.
- Schema: `north_hux`.
- Data: calibration is loaded. Current totals are 76 registered sources, 224 raw objects, 49 platform-account records, 64 content records, 660 comments, 94 transcripts, 111 observed reply edges, and 60 immutable Studio exports.
- Scope: local-only. No external database or network exposure is configured.

## Reach it

From the Content Engine project directory:

```bash
pg_isready -h 127.0.0.1 -p 55432
psql -h 127.0.0.1 -p 55432 -d north_hux
```

Useful first queries:

```sql
\dt north_hux.*
SELECT * FROM north_hux.v_platform_progress ORDER BY platform, category;
SELECT * FROM north_hux.v_public_safe_account_summary LIMIT 50;
SELECT * FROM north_hux.v_social_studio_candidate_v1 ORDER BY studio_candidate_state, platform;
SELECT export_id, signal_record_id, record_hash FROM north_hux.v_signal_to_studio_v1;
```

The local cluster can be started and stopped with:

```bash
pg_ctl -D .local/postgres -l .local/postgres/server.log -o '-p 55432' start
pg_ctl -D .local/postgres stop
```

## How it is constructed

The base migration is `migrations/002_north_hux_market_intelligence.sql`. `003_signal_to_studio.sql` adds the append-only Studio mirror and initial social-candidate view. `004_comment_transcript_provenance.sql` adds append-only reply-edge provenance. `005_social_studio_review_gate.sql` replaces the candidate gate with explicit 12-axis evidence reviews, maker/reviewer separation, a versioned social contract, and a public-safe content release review. Every major table uses a generated identity primary key; portable social candidate identities use a versioned SHA-256 formula instead of database sequences. Natural uniqueness is enforced separately for platform/native IDs and canonical URLs. Foreign keys preserve the research chain.

| Layer | Tables | Purpose |
|---|---|---|
| Run and collection | `research_run`, `adapter`, `collection_job` | run identity, route state, cursor/failure state, five-strike count |
| Provenance | `source_registry`, `raw_object` | canonical source, immutable payload pointer, hash, capture time, retention/redaction |
| Accounts | `creator_entity`, `platform_account`, `account_alias`, `account_snapshot` | creator form, platform identity, aliases, follower/content snapshots |
| Content | `content_item`, `content_relationship` | post identity, caption/title, format, duration, repost/remix/cross-post links |
| Metrics | `metric_definition`, `metric_snapshot` | platform-native metric semantics, denominator, timestamp, observed/not-exposed state |
| Interaction | `interaction_coverage`, `comment`, `interaction_event` | reported versus retrieved counts, comments, replies, likes, shares, reposts, sends, saves, and follow events |
| Language/media | `transcript`, `transcript_segment`, `media_asset`, `frame_artifact`, `visual_event` | captions/transcripts, timestamped segments, rights-aware assets, frame references and visual events |
| Analysis | `taxonomy_version`, `classification`, `evidence_record` | versioned labels, epistemic state, evidence locators and confidence |
| Governance | `rights_decision`, `review_task`, `review_decision` | rights/use decisions, Sol/reviewer gates, maker-checker decisions |
| Reporting | `analysis_progress`, `export_artifact` | category progress and immutable export pointers |
| Studio bridge | `studio_signal_export`, `social_studio_contract`, `studio_axis_review`, `studio_content_release_review`, `v_signal_to_studio_v1`, `v_social_studio_candidate_v1` | immutable current Studio exports and evidence/rights/review-gated social candidates |
| Reply provenance | `comment_edge_observation` | observed native parent-child reply edges without pretending the bounded sample is complete |

## Interaction completeness rule

The database does not pretend that every platform exposes every interaction. For each interaction type it stores the platform-reported count, retrieved count, pagination completion, sampling method, endpoint limit, gap reason, and capture time. A missing field is `NULL` or an explicit unavailable state; it is never converted into zero. Individual likers or private senders are not inferred.

## Evidence and dashboard split

Postgres is the relational system of record after ingestion. Raw JSON/JSONL payloads and transcript files remain separate immutable artifacts referenced by URI and SHA-256. No social media/audio/image/frame bytes were downloaded in the current run. Notion receives only a redacted projection of progress, reference links, dated public metrics, and owner questions. Obsidian receives curated run/cohort/decision summaries, not raw comments or thousands of creator notes.

## Saving and recovery plan

The database currently persists inside the project-local PostgreSQL data directory. This is local persistence, not yet a verified backup. The next storage gate is an encrypted, versioned backup outside the live cluster plus a restore drill. The recommended minimum is daily custom-format `pg_dump`, a SHA-256 manifest, retention tiers (daily/weekly/monthly), and a quarterly restore test into a disposable database. Raw artifacts need their own encrypted file backup and deletion manifest because `pg_dump` stores pointers and normalized text, not every run-local file byte.

Do not place database passwords, API keys, cookies, or tokens in this guide, Obsidian, Notion, Git, or run receipts. Use local peer/keychain or explicitly approved environment injection.

## Verification

The base migration receipt is in `runs/20260825-m2-market-analysis-design-v1/postgres-receipt.json`. The current social-adapter verification is `runs/20260825-north-hux-social-adapters-v1/verification-receipt.json`. Both the base schema smoke and Signal-to-Studio smoke execute transactionally and roll back. The current verifier reports no metric null-semantics violations, no comment-pseudonym violations, no missing run raw pointers, 60 current Studio exports, 64 gated social candidates, and zero eligible social exports.
