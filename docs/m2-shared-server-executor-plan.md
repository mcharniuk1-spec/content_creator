# Shared-server execution plan — deployment deferred

Owner decision: use Supabase plus Cloudflare after local validation. Keep the existing Contabo VPS as a candidate worker host; it is not necessary to move everything into Cloudflare Workers. The supplied 6-core/12-GB/200-GB specification is sufficient to benchmark CPU ASR and bounded FFmpeg work, but it is not a measured throughput guarantee or a GPU generation host.

## Phase A — recover and reconcile before migration

1. Michael's executor records deployed commit, SQLite schema version, running job IDs and last successful/partial/failed run receipts. Do not expose `.env` or credential values.
2. Take a transaction-consistent SQLite backup using Python `sqlite3.Connection.backup` or SQLite `.backup`, then `PRAGMA quick_check`, table counts and SHA-256. Copy frame/transcript manifests and referenced artifacts separately. A raw copy of a live WAL database without WAL reconciliation is not sufficient.
3. Deliver the private backup to Max through a protected channel or existing SSH. Run the reconciliation exporter against it and the retained local corpus. Join code identities, inventory missing codes, overlaps, text conflicts, orphan analyses and missing frame bytes. Preserve both originals.
4. Select evidence by provenance and quality, not by newest timestamp alone. Imported local ASR must retain detected language, model, media hash and suspicious timing flags. Rebuild the English and relevance cohorts. Never label all 1,062 imported attempts usable automatically.
5. Run one deterministic, provider-disabled replay. Assert cardinalities, foreign keys, null handling, stable IDs and repeat-import idempotency. Independently audit original-audio accuracy on a stratified sample and all intended script references.

## Phase B — one shared infrastructure project

Create a shared organization/project with separate member accounts for Max and Michael; do not share one password. Git remains code/config/migrations, Supabase stores normalized relational metadata and job state, and private object storage stores media/artifact bytes. Choose R2 as the main media bucket to avoid duplicating the corpus in two object stores. Supabase Auth/RLS governs project access; server credentials stay on workers.

Suggested relational entities: projects, creators, roster_versions, reels, collection_runs, metric_observations, media_assets, processing_attempts, transcripts, transcript_segments, language_decisions, frames, annotations, analysis_releases, findings, references, scripts, shots, generation_jobs, renders, reviews and projection_receipts. Every derived row references its source version and processing run. Idempotency keys use stage + input hash + configuration/version; attempts are append-only.

Cloudflare serves the interface/API gateway, access control, lightweight webhooks and scheduling. CPU ASR, FFmpeg and Remotion run on a VPS/container worker with disk, process supervision and bounded concurrency. Workers have a 128-MB memory limit; they are not the place to load Whisper. See [Workers limits](https://developers.cloudflare.com/workers/platform/limits/).

Use short-lived signed R2 access for specific artifacts; never place signed URLs in Git, public reports or permanent identity fields. See [R2 signed URLs](https://developers.cloudflare.com/r2/api/s3/presigned-urls/). Database backups and media backups are separate: Supabase's database backup does not include Storage object bytes. See [Supabase backups](https://supabase.com/docs/guides/platform/backups).

## Phase C — unattended workers and shared agent access

Use a systemd service/container restart policy plus a scheduler, durable queue leases, heartbeats and per-stage deadlines. Deterministic collection, download, language detection, ASR, frame extraction and aggregation need no continuously open Codex/Claude session. Semantic analysis needs an explicitly configured model executor and bounded inputs/costs; a scheduler alone does not provide that reasoning.

Each job records planned/started/heartbeat/finished timestamps, accepted/rejected outputs, error class, retry count, input/output hashes and resource cost. Reclaim only expired leases, not every job older than an arbitrary age. Distinguish PARTIAL, FAILED, EXCLUDED and DONE. Resume the same input version; changed code/config creates a new attempt. An LLM process exit code is not evidence that all expected files exist or validate.

Expose one authenticated project API and a narrow MCP adapter for Codex and Claude: inspect corpus/release, read evidence, submit a bounded job, inspect results, propose script and request review. Keep provider credentials in the server secret store; agents receive identifiers and scoped capabilities, not secrets. Avoid giving the project-manager model unrestricted shell access. Supabase Git integration does not import an existing SQLite corpus or implement these workers automatically.

## Phase D — migration acceptance and cutover

Rehearse into a separate Supabase schema/project and private bucket. Verify record counts by stage, exact artifact hashes, original transcript preservation, retry idempotency, language exclusions, interrupted-run recovery, scoped access and database-plus-media restoration. Run the same analytical release locally and remotely; compare outputs by hash or a documented floating-point tolerance. Then switch one scheduler, disable the old one to prevent duplicate collection, and keep a rollback snapshot.

No deployment occurred in this review. Missing before execution: actual server backup/access, chosen Supabase project/R2 bucket and shared members, media retention budget, semantic model execution budget and an accepted end-to-end replay.

## Time estimates — assumptions, not a promise

The September 14 partner handoff reports roughly 114 seconds per Reel on its recent run. At that measured example, 300 Reels consume about 9.5 serial hours and 1,000 about 31.7 hours before retries; this is not a forecast for every video or the local model. Early non-English rejection reduces work. Existing media and transcripts should be reconciled before paying that time again. Benchmark 20–30 varied clips, measure median/p90 download, detection, ASR and frame time separately, then estimate the actual eligible backlog with bounded concurrency. Allow separate time for acoustic/reference review and schema migration; do not multiply cores into a speed guarantee.

Suggested implementation sequence after access: one day for backup/join audit and sample review; one to three working days for import/gate corrections and replay; one to two days for migration rehearsal and recovery tests. These are planning ranges contingent on corpus size, defects and access, not completed work or a committed delivery date.
