# M2Lab operator guide

Use a pinned checkout. Nothing in this guide authorizes paid collection, provider generation or publishing. The same modules work in the standalone Studio repository and the partner Radar fork. Credentials and research media are not distributed with code.

## Existing export: full deterministic replay

```bash
python3 scripts/run_m2.py --source-dir path/to/export --run-dir .local/run-001 --run-id run-001
python3 -m m2_orchestrator --run-dir .local/run-001 verify
python3 -m m2_orchestrator --run-dir .local/run-001 tasks
```

The export contains `reels.csv`, `accounts.csv`, one `snapshot.json` and optional `transcripts.json`, `cuts.json`, `topics.csv`. The supplied Cyrillic export names are recognized too. The snapshot has `taken`, `accounts` and optional corroborating `rows`. See `m2_signal/engine.py` for the exact field and alias contract. A mismatched JSON/CSV row fails ingestion. Files are frozen under the private run input directory before work starts.

The command executes 12 real local stages: admission, config freeze, inventory, observation ingest, normalization/analysis, all-row audit, metric snapshot, descriptive baselines, candidate ranking and existing transcript/visual/comment attempt inventories. It does **not** make new acquisition attempts or run semantic reviewers automatically. `tasks` exports the remaining explicit role work. Stage completion counts are not evidence or production completeness counts.

## Incremental or bounded custom run

```bash
python3 scripts/run_m2.py --source-dir path/to/snapshot-a --run-dir .local/run-a --run-id run-a --database .local/signal.sqlite --mode incremental
python3 scripts/run_m2.py --source-dir path/to/snapshot-b --run-dir .local/run-b --run-id run-b --database .local/signal.sqlite --mode incremental
python3 scripts/run_m2.py --source-dir path/to/snapshot-b --run-dir .local/run-b --run-id run-b --database .local/signal.sqlite --mode incremental --until rank_candidates
```

Unchanged observations deduplicate in the shared append-only ledger. Each release retains its own membership; older snapshots never silently mix with a current release. A different threshold set uses `--metric-config config/m2-metrics.v1.json` and a new run. Config keys not implemented by the metrics handler are rejected. The shared database path is an operator binding; moving an in-progress run to a different ledger requires a new run or a documented migration, not silently changing its pointer.

Custom subsets must be exported explicitly with their account and Reel scope. `--until` stops after one deterministic stage; it does not bypass prerequisites. A config or input change on resume is refused. The exported task contains the role, expected product and required receipts; dispatch only that task, never all the raw corpus to every agent.

## Existing server database: read-only bridge

```bash
python3 -m m2_signal import-legacy-db --source path/to/radar.db --snapshot-date 2026-09-01 --output .local/export-001
python3 scripts/run_m2.py --source-dir .local/export-001 --run-dir .local/run-001 --run-id run-001 --mode server --database .local/signal.sqlite
```

The importer opens the legacy database read-only, preserves source-native fields and labels date-only capture precision. The legacy database remains untouched. Raw private rows stay under `.local/`; no repository copy or Notion page is a backup of the canonical database.

## Worker completion and review

```bash
python3 -m m2_orchestrator --run-dir .local/run-001 begin transcript_segment --actor text_analyst
python3 -m m2_orchestrator --run-dir .local/run-001 finish transcript_segment --token WORKER_TOKEN --artifact products/transcript-sections.json --limitation "Source audio not independently verified"
python3 -m m2_orchestrator --run-dir .local/run-001 recover transcript_segment
```

Save the token privately from `begin`. Products must be regular files inside the run. `recover` only works after a lease expires. A stale token cannot commit. Review stages require `m2.independent-review.v1` with exact `run_id`, `config_hash`, `stage`, `reviewer`, `subjects` (dependency stage → receipt SHA-256), `verdict`, `scope` and `limitations`. Reviewer identity must differ from the maker. Rejected or mismatched reviews do not unlock downstream steps.

The low-level completion command records a trusted operator's product and checks its integrity. It does not turn arbitrary text into a valid transcript or model result. Stage-specific validators and the independent evidence review remain mandatory. See `skills/m2-stage-worker/SKILL.md`.

## Media cache and transcript/scene workflow

An explicit media map contains `run_id`, every `expected_codes` entry and a bounded `entries` list. Each entry binds the Reel code, safe media ID, relative file path, SHA-256, source kind and rights. Missing entries emit gaps; they never cause HikerAPI, login or cookie access.

```bash
python3 -m m2_studio media-map --root path/to/approved-cache --map .local/media-map.json --output .local/media-attempts
python3 -m m2_studio transcribe --root path/to/approved-cache --media .local/media-record.json --model path/to/cached-whisper-model.pt --output .local/transcript
python3 -m m2_studio cuts --root path/to/approved-cache --media .local/media-record.json --output .local/cuts.json
python3 -m m2_studio scenes --root path/to/approved-cache --media .local/media-record.json --transcript .local/transcript/transcript.json --annotations .local/reviewed-scenes.json --output .local/scenes
```

Run `--help` for current exact arguments. The model must already exist locally. Silence and empty ASR are unverified states; a reviewer decides whether there is truly no speech. Semantic annotations must cite transcript timing and actual scene evidence. An edit cut alone is never a semantic scene. Each extracted image has a real timestamp and hash. Files and source collages remain private analysis assets unless rights separately allow public reuse.

## Cards, owner footage and Remotion

```bash
python3 -m m2_studio card-edl --card .local/script-card.json --output .local/edl.json
python3 -m m2_studio validate-edl --edl .local/edl.json
```

Previsualization accepts declared placeholders and visibly labels them. Production requires approved asset bindings: owner take, source range, identity/rights, exact file hash and intended scene. Never replace missing footage with a claim that it was shot. After footage arrival, check duration/codec/audio, align dialogue, review selects, lock timing and rerun production validation.

`studio/remotion/README.md` describes the pinned dependency installation, composition contract and actual renderer invocation. Use local approved assets and an explicitly supplied browser executable. Model outputs and owner footage are immutable assets; the EDL selects takes. Final export review covers caption readability, exact timings, safe zones, audio and visual continuity, frame count, codecs, claims and rights.

## Provider activation

The Studio provider catalog and model assessment distinguish official documentation, adapter fixtures and live execution. Before a paid request, bind an approved job to exact model, prompt, start/end references, output shape/duration, rights and cost ceiling. Keys are injected in the backend environment, never copied into project files. Submit once; persist the job ID; reconcile unknown outcomes before retry. Downloaded outputs must pass file/content/hash/probe review before composition. No global model preference bypasses shot-specific capability checks.

## Partner server integration

The fork ships the same portable packages plus a guarded runner and timer script. Review the Git diff, back up the existing database, run fixtures and read-only import, then use a new pinned checkout. Restore-test before changing the server's selected code path. The existing HikerAPI key can be injected as `HIKER_KEY` or `HIKERAPI_KEY`; no model needs to read the key.

Collection remains a separate explicitly approved adapter. Its config names allowed public accounts, capture date, pagination/request/window limits, timeout, maximum cost, per-request ceiling and price receipt. Default live entry allows a one-request pilot only; larger runs require independently reviewed live response/schema evidence bound to the approval. This run did not call HikerAPI or validate Michael's server environment. A page cap is partial coverage, never exhaustion. Preserve counters and capture times, acquire approved selected media promptly before CDN expiry and create the normalized export before invoking downstream analysis.

The supplied server timer does not install cron or start a service. It does not pull code while running. Scheduled triggers, manual runs and custom subsets invoke the same engine with frozen config. Model/semantic tasks are exported explicitly for an approved executor and reviewer; there is no implicit subscription-backed server agent.

## Notion, backup and knowledge

Use connected Notion MCP in Codex. Read exact targets/schemas first; stage a release-specific projection; preserve owner decisions; use stable keys; reconcile uncertain creates; read back every projected property. Existing legacy tables may remain visible as a separate dated release. `m2_orchestrator/projection.py` provides the local outbox and mismatch/conflict guards, not a hidden live writer.

```bash
python3 -m m2_signal backup --source .local/signal.sqlite --destination .local/backups/signal.sqlite
python3 -m m2_signal restore --source .local/backups/signal.sqlite --destination .local/restore-check.sqlite
```

Restore to a new disposable destination. Retain run inputs, manifests, source/model versions and review receipts alongside the database backup. Verify hashes and SQL integrity, then record the receipt. Restore never overwrites an existing database.

Only independently reviewed conclusions update `knowledge/`, WikiLLM and the scoped Obsidian project notes. Search for duplicates/conflicts, record freshness and allowed uses, and leave raw sources private. Update the handoff and issue backlog when a stage is blocked. A run should remain resumable after the chat ends.


## Implementation upgrades and worker handoff

An executable or dependency change requires a new run directory and ID. The prepared config hashes the shared Python modules, Signal SQL, provider catalog, Remotion source/dependency lock, role skills and curated context. Checkpoints reject changed dependencies. Original frozen run artifacts remain inspectable using their pinned implementation, and source-equivalence receipts can connect a repair release without pretending the release IDs are identical.

`python3 -m m2_orchestrator --run-dir RUN tasks` emits each unfinished state with its exact specialist role contract, bounded context, skill, output budget and authority. Dispatch it through the current interactive agent host or an explicitly authenticated server worker. It does not start an unattended paid model. Return the named artifact to the frozen run, then use the begin/finish receipt commands; reviewers must bind the parent hashes and propagate every limitation.

The Notion planner `m2_orchestrator.notion_payload.build(signal_directory, strategy_directory)` emits a private versioned snapshot package. It requires the strategy source map and transcript artifact hashes, excludes raw transcript text, preserves null counters and labels legacy versus lexical counts. Use `Outbox` to stage each exact action before its MCP call. Numeric readback tolerates integer/float JSON normalization while keeping null, zero and boolean values distinct.
