# M2Lab Signal: local evidence replay and server adapter

Signal turns a declared Instagram export snapshot into immutable observations, normalized metric tables, per-Reel/per-Account diagnostics and explicit evidence attempts. Python 3.10+ and its standard library are sufficient. No package install, browser, provider key or network connection is needed for replay.

The local portable SQLite file is the authority for this release. It does not claim to replace a deployed PostgreSQL authority. Notion is a separately reconciled review projection. Studio must use an accepted, immutable evidence release before representing a script as supported by competitor evidence.

## Local execution

```sh
python3 -m m2_signal replay --source-dir local-data/export --output local-data/run-output
python3 -m m2_signal replay --source-dir local-data/next-export --output local-data/next-output --database local-data/signal.sqlite
python3 -m m2_signal analyze --database local-data/signal.sqlite --release-id SIGNAL_RELEASE_ID --output local-data/analysis-output
python3 -m m2_signal backup --source local-data/signal.sqlite --destination local-data/backup.sqlite
python3 -m m2_signal restore --source local-data/backup.sqlite --destination local-data/restored.sqlite
python3 -m unittest discover -s tests -p 'test_m2_signal*.py' -v
```

An output folder belongs to one release. Use a new output folder when source, config or implementation changes; reuse the same SQLite ledger to retain history. Backup and restore targets must be new files. The backup uses SQLite's online backup API and verifies integrity and foreign keys; it does not blindly copy a live database file.

The source folder contains `reels.csv`, `accounts.csv` and one `snapshot.json`, plus optional `transcripts.json`, `cuts.json`, and `topics.csv`. Supplied legacy filenames are recognized by normalized Unicode aliases. Ambiguous aliases fail. `snapshot.json` requires `taken` as an ISO capture date; optional `accounts` and `rows` must corroborate the CSV. Empty numeric fields remain null. Observed zero remains zero.

`reels.csv` requires `code,user,play,like,comment,reshare,save,duration_s,ts`. Optional `url,caption` preserve source context. `accounts.csv` requires `username`. Optional profile counters, category and biography remain source evidence. JSON transcript values are keyed by Reel code and contain `words` and `segments` with `s,e,t`. Cut values contain `cuts`. A cut count alone is never a shot or semantic scene.

Only video files inside the explicitly supplied export directory are inventoried. A filename matching a Reel code is a candidate local media association. Its bytes and relative path are recorded, but the file is not decoded and is not thereby a verified video. Frame/shot/scene evidence remains missing until the separate media lane proves it.

Python APIs:

```python
from m2_signal import ingest_export, analyze, import_legacy_db

receipt = ingest_export(database_path, source_directory, config=None)
summary = analyze(database_path, receipt['release_id'], output_directory)
```

`config` is a dictionary of overrides from `metrics.DEFAULT_CONFIG`. Unknown keys fail; active platform is Instagram Reels and replay collection is always disabled. Default exposure, robust-z, component-coverage selector and Wilson interval parameters reproduce the accepted September 4 descriptive release. The resulting `metrics-definition.json` is the exact per-release formula/parameter contract.

## Immutable data model

| Table | Grain and purpose |
|---|---|
| `releases` | Corpus, config, implementation hashes and capture date |
| `sources` / `release_sources` | Content-addressed source files and release memberships |
| `observations` | Immutable snapshot/kind/entity/value records; raw source payload retained locally |
| `release_observations` | Every source-row membership, including duplicate rows |
| `metric_observations` | Source counter name, typed integer/null, observation state and unit |
| `reel_analysis` / `account_analysis` | Release-scoped audit and derived diagnostic payloads |
| `reel_metric_values` | One typed metric value/unit/denominator/formula per release and Reel |
| `evidence_attempts` | One transcript, cut, media, frame, shot, scene and comment attempt per Reel |

SQL triggers reject updates and deletion of evidence/analysis rows. Identical duplicate values share an immutable observation, while all source-row memberships survive. Conflicting values for the same identity in one snapshot are quarantined. Different snapshots remain distinct measurements; they never create an implicit latest-row overwrite or cross-snapshot baseline.

Null counters, invalid values, missing media, insufficient baseline, identity conflicts, unreviewed source rights and strategic gaps remain separate facts. Code and configuration hashes are part of release identity; a changed implementation must ingest a new release before analysis. Repeated identical imports add zero observations and reproduce identical JSON/CSV.

## Outputs and interpretation

- `signal.sqlite`: run-local raw and normalized authority; private data artifact.
- `reels.jsonl` / `.csv`, `accounts.jsonl` / `.csv`: complete audit, metrics, component coverage, uncertainty and blocked Best gates.
- `candidate-ranking.csv`: descriptive review queue, prioritizing component coverage before diagnostic score. It is not a final Best-Reel decision.
- `evidence-attempts.jsonl`: independent modality denominators, provenance references and typed gaps.
- `quarantine.jsonl`: conflicting or invalid identities, without silently selecting a winning source row.
- `source-media-inventory.json`: bounded file inventory; no decoded video proof.
- `evidence-job-queue.json`: scoreable evidence-acquisition priorities and a pointer to all-Reel missing-media attempts.
- `summary.json`, `source-manifest.json`, `metrics-definition.json`, `artifact-manifest.json`: reviewable release context and content hashes.

The descriptive Account baseline includes the focal Reel. Counters come from a date-only capture with unknown provider semantics and unequal post ages. Account followers are not a valid historical same-age denominator. Current diagnostic results cannot establish causation, representative prevalence, demand, ROI or a prediction of performance. A future decision-grade model needs a separately reviewed goal, eligibility policy, temporal controls and independent evidence release.

## Partner Radar database import

```sh
python3 -m m2_signal import-legacy-db --source local-data/radar.db --snapshot-date YYYY-MM-DD --output local-data/imported-snapshot
python3 -m m2_signal replay --source-dir local-data/imported-snapshot --database local-data/signal.sqlite --output local-data/signal-release
```

The adapter uses a read-only SQLite transaction and allowlisted evidence columns. It accepts only an explicitly selected completed snapshot and verifies its stored row count. It does not import secrets, spending, internal tool notes, original Cards, own-account metrics, or legacy composite scores. It preserves null counters and per-Reel snapshot followers. Current account profiles are explicitly marked as current database values, not historical snapshot measurements. Historical accounts without Reels cannot be reconstructed from the present account table. Unversioned transcripts remain unverified for the selected snapshot.

## HikerAPI on the partner's server

`m2_signal.hiker_adapter` is a separate gated adapter. Replay never activates it. The official OpenAPI 1.8.1 documents `GET /gql/user/clips` parameters (`user_id`, `max_id`, `flat`, `sort_by_views`), while the flat `items/max_id/more_available` response remains a legacy contract candidate. Current capability is **LIVE_SCHEMA_UNVERIFIED**; tests use injected fixtures only.

```python
from m2_signal.hiker_adapter import collect

receipt = collect(
    config, private_directory,
    execute_live=True,
    approval_path=exact_owner_approval,
    schema_receipt_path=reviewed_live_schema_receipt,  # omit only for approved one-request pilot
    on_media=approved_immediate_media_callback,       # optional; requires separate scope
)
```

The adapter reads only `HIKER_KEY` or `HIKERAPI_KEY` from the process environment. It does not read Desktop MCP files, `.env`, browser cookies or command-line secrets. Server/service secret injection remains the operator's responsibility. Redirects are disabled, exception text is sanitized and no credential is serialized.

The exact config requires: `run_id`, `snapshot_date`, an explicit `accounts` allowlist (`user_id,username,followers,public_source_authorized`), `max_pages_per_account`, `max_requests`, `request_timeout_seconds`, `maximum_cost_usd`, `request_cost_ceiling_usd`, a dated owner-verified `price_receipt_sha256`, and nullable `earliest_published_epoch_seconds`. There is no assumed current tariff.

A live approval requires `approved=true`, `approval_id`, `approved_by`, timezone-aware `expires_at`, exact `config_sha256` and `scopes` containing `hikerapi_instagram_reels_collection`. A callback additionally requires `immediate_media_acquisition`. With no verified response receipt, only one request and `live_schema_probe_approved=true` are admitted. Broader runs need a package-local actual response file, its hash, endpoint, `evidence_source=LIVE`, distinct maker/reviewer, `review_state=APPROVED`, expiry, and an approval binding that schema receipt's hash. These receipts must come from a real separately approved pilot, never from the fixture tests.

Every request reserves its declared maximum cost before dispatch. This is a budget reservation, not an invoice or measured charge. Timeouts, transport failures, malformed pagination and ambiguous prior dispatches stop without automatic billable retries. Cursor loops are blocked. A page cap and budget cap are distinct from source exhaustion. The publication lower bound filters rows; it does not assume pinned or reordered feeds are chronologically sorted.

Raw pages, dispatch records, checkpoints, temporary signed media references and exports stay in the operator-designated private run directory with restricted permissions. Keep this directory outside Git, dashboards, Notion and durable knowledge. The optional callback receives fresh media references immediately after a successful page; callback output still needs the Studio/media lane's own provenance and QA. This adapter does not itself download or decode media.

A retained `collector.lock` indicates an interrupted process. Inspect its dispatch/checkpoint records before removing a stale lock; an uncertain dispatch cannot be silently retried. A failed/partial run requires reconciliation and a new exact run/config authorization to expand its budget.

Official reference: [HikerAPI OpenAPI](https://api.hikerapi.com/openapi.json). Operational compatibility and billing on the partner's server remain untested by this local run.
