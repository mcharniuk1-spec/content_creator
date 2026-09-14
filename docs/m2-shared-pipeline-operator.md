# Shared M2 pipeline: execution and recovery

The shared database schema has been rehearsed with a dated private source packet. Source preservation, semantic acceptance, original-audio accuracy, deployment and publication are separate gates.

## Source backup from the existing worker

Run the existing collector's maintenance procedure first and record its pinned Git commit and scheduler state. Do not copy a live WAL database with a plain file copy. With the actual database path and a new destination:

```bash
python3 scripts/backup_m2_source.py --source /approved/path/radar.db --destination /approved/new/backup.db --manifest /approved/new/manifest.json
```

The backup uses SQLite's consistent backup API. Transfer the backup, manifest and explicitly referenced media/transcript/frame artifacts through the existing protected channel. No credential values belong in manifests. Do not delete application lock files or stop collectors without verifying their ownership and the approved cutover plan.

## Supabase schema and private import

`migrations/010_m2_shared_pipeline.sql` creates an isolated schema. It is a one-time migration, not a rerunnable setup script. It does not depend on the frozen YouTube migrations. All tables use RLS and no client grants; the initial schema is intentionally inaccessible to ordinary web clients. Access policies must be reviewed against actual authenticated members before service activation.

`reels` stores stable identities. `reel_assessments` stores release-specific dispositions. Source rows retain every original value and source version. `releases.status` records its initial status; later states belong in append-only `release_events`. Typed media/transcript/scene/script tables are available but remain unpopulated until reviewed projections establish their relationships. Nullable legacy links are not evidence acceptance.

Inject `M2_DATABASE_DSN` securely into the process environment, then run:

```bash
python3 scripts/import_m2_shared.py --packet /approved/private/reconciliation --review /approved/private/data-review.json --release shared-YYYYMMDD-v1 --receipt /approved/private/import-receipt.json
```

The importer requires the independent review's exact packet hashes, checks row payload hashes, rejects changed immutable inputs, preserves native schemas and empty-table definitions, and reads back all imported rows. Repeat the same import to verify idempotency. A changed packet requires a new review and release. This imports the source-preservation layer and identity assessments; it does not pretend to normalize every downstream product or upload media.

Storage remains private. Select retention, approved members and the actual bucket before uploading media. Never enable public bucket access for the research corpus. Supabase's storage API owns object writes; SQL metadata insertion alone is not an uploaded object.

## Gateway and worker host

`integrations/cloudflare/worker.mjs` is a bounded gateway candidate. Configure secrets `GATEWAY_TOKEN` and `WORKER_TOKEN` with the provider's secret store, and configure `WORKER_ORIGIN` to the approved HTTPS worker. No value belongs in Git. The endpoint accepts only a stage, immutable execution-bundle hash and release ID. It has no scheduling trigger and cannot request paid generation or publication.

`input_sha256` must hash the complete frozen execution bundle: source manifests, configuration, implementation, release ID and rights/approval inputs. It is never just the media hash. A changed release/config/code must yield a different job identity. The host must resolve and verify this bundle before admitting a job; this gateway does not implement that host-side verification.

CPU ASR, FFmpeg and Remotion execute on the approved worker host. Ordinary Workers have bounded CPU and memory; queue delivery can repeat. The worker must enforce job identity, approved source manifests, stage rights, token leases, heartbeats, bounded retries and result hashes in Postgres. `claim_job`, `heartbeat_job`, `finish_job` and `recover_job` provide transaction-safe lease primitives; they are not a complete host service or authenticated membership system.

Keep exactly one scheduler. Before cutover: record old timer, pause through the operator-approved maintenance procedure, confirm no running collection, freeze database/artifacts, restore-test, pin new code, run one fixture, then one bounded approved live job. If anything fails, leave the new scheduler disabled and restore the old pinned code/snapshot through the reviewed recovery plan. Do not automatically install cron, pull latest code or retry a paid unknown outcome.

## Rollback and truth states

The initial live change is schema-only with no client grants or corpus rows. Rollback can leave that isolated unused schema in place; no destructive deletion is needed. Before any populated deployment, create a database dump plus artifact manifest, restore to a separate destination, compare every source count/hash and verify private access. Never drop a populated schema as an automatic rollback.

A local import and restore prove database portability for the tested packet. They do not establish current-server completeness, accepted English references, shared worker operation or media restoration. New ASR outputs remain unreviewed attempts until checked against original audio. Script candidates remain editorial hypotheses until exact reference gates pass.

Official capability references checked 2026-09-14:

- [Workers limits](https://developers.cloudflare.com/workers/platform/limits/)
- [Queues delivery guarantees](https://developers.cloudflare.com/queues/reference/delivery-guarantees/)
- [Supabase private storage](https://supabase.com/docs/guides/storage/buckets/fundamentals)
