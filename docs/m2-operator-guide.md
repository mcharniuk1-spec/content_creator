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

## Full-corpus local media recovery

The active completeness route processes every existing Reel identity. Michael's
candidate selection (100 videos, per-account cap, card pool) is a presentation
choice, not an acquisition or transcription limit. Build the private media
manifest with `scripts/build_m2_media_manifest.py` from the canonical Reels
JSONL. It reads cached clip responses directly and never constructs a HikerAPI
client. Cache misses remain explicit; the optional anonymous public resolver
requires a pinned installed executable and its tested restricted network broker.

Retain each recovered video. The local sequence is validated media/audio →
multilingual CPU transcription → regular decoded frames and visual-change
samples → independent transcript and scene review. Text, word timing, cuts,
shots and semantic scenes have separate statuses. A zero-duration ASR word
remains in raw and unaligned evidence; no duration is invented. Absent audio,
exact digital silence, empty ASR, interrupted inference and unavailable media
must remain distinct. Frame processing continues when ASR fails.

Use one media/model worker and two CPU threads. Validate model file hashes
before offline inference. Record time, sampled peak memory, retries, source
hashes and each modality's errors in the per-Reel ledger. Sampled memory
watchdogs are not hard operating-system caps. Preserve the configured free
disk reserve; stop safely on a storage limit instead of deleting evidence.
Run a real representative pilot and review its output before corpus expansion.

Loore is optional and does not gate the local workflow. The correct service is
`loore.ai`; the older `loore.io` assumption was incorrect. The disabled route in
`config/m2-loore-optional.v1.json` records the verified public API contract.
Published API availability does not establish authenticated execution. Bind
any later Loore call to exact source identity, operation, available authorized
credits and an idempotency key; retain vendor findings separately from reviewed
local evidence. Do not activate tracking or paid requests implicitly.

### Portable corpus invocation

Read `docs/m2-corpus-worker-contract.md` for worker roles, independent review,
failure handling and the distinction between preview frames and semantic scenes.
The optional Python dependencies are pinned in `requirements-m2-media.txt`.
The actual run used macOS with Python 3.12.9 and installed FFmpeg/ffprobe; a
partner Linux host still needs its own bounded smoke test. Use a dedicated
environment with those dependencies, FFmpeg/ffprobe on PATH, and a local
Faster-Whisper small model bundle. Do not use the legacy `deep.py` cleanup or
candidate-selection loop for full-corpus completeness.

Download model weights outside Git from `Systran/faster-whisper-small`, revision
`536b0662742c02347bc0e980a01041f333bce120`. The tested `model.bin` SHA-256 is
`3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671`.
The private model directory must contain `model-hash-manifest.json` with a
`files` array of relative `path` and `sha256` entries covering every regular
file except the manifest itself. Freeze the tokenizer/config as well as the
weights; the worker rejects missing, altered or unlisted files. Model download
and dependency installation are setup actions, not hidden side effects of a run.

Build a fresh private manifest from the normalized full Reel export. Supply
Michael's actual cache directory with `--cache-root` when available; it is
read directly and never falls through to HikerAPI. Supply existing media roots
explicitly. Do not add `--pilot-code` to the full-corpus manifest.

```bash
python scripts/build_m2_media_manifest.py \
  --reels .local/signal/reels.jsonl \
  --cache-root .local/partner-clips-cache \
  --media-root .local/retained-media \
  --public-fallback --output .local/media-manifest.json

python scripts/run_m2_corpus_media.py \
  --manifest .local/media-manifest.json \
  --run-root .local/corpus-run-001 \
  --model-dir /absolute/path/to/frozen-whisper-small \
  --python-executable /absolute/path/to/media-venv/bin/python \
  --media-root .local/retained-media \
  --rights-receipt your-recorded-existing-corpus-research-authority \
  --resolver-executable /absolute/path/to/media-venv/bin/yt-dlp \
  --resolver-sha256 SHA256_OF_YOUR_INSTALLED_ENTRYPOINT \
  --max-items 8 --network
```

The paths and authority/hash arguments above are explicit placeholders. The
resolver uses a restricted public-host broker and no browser cookies. Its
entrypoint digest is one provenance check; retain the installed package
version and dependency lock too. The network switch authorizes this configured
public acquisition path and is required by the corpus dispatcher, including
when the current batch happens to resolve from local media.

Review the real first tranche, then resume the identical command without
`--max-items 8` to process remaining identities in serial batches. A later
`--max-items N` limits work in that invocation, not the full population.
The default source cache cap is 8 GiB and the disk reserve is 5 GiB. Choose
larger storage limits only after checking available space; bind any changed
limit to a new run. Do not edit executing modules, replace artifacts, run
multiple media workers or delete retained sources to bypass a storage stop.

```bash
python scripts/report_m2_corpus_progress.py \
  --run-root .local/corpus-run-001 \
  --output .local/progress/checkpoint-001
```

Each new checkpoint includes all identities in CSV and separate modality
counts. The optional local Apple Vision OCR helper is macOS-specific; the
portable core path is FFmpeg plus CPU ASR. OCR text remains separate from
speech transcripts. The corpus runner does not invoke Notion, an LLM API,
generation, server deployment or publication automatically.

## Radar v2 media overlay (review pending)

The staged v2 overlay adds a read-only eligibility inventory, bounded scene candidate extraction, and an optional offline transcript recovery route. It is an integration candidate; it does not activate the timer, change the frozen corpus ledger, or claim full-corpus completion. Keep the existing shared-engine checkout and copy these relative paths into the matching package locations only after independent review.

### Eligibility inventory

Run against one frozen feature checkpoint and its exact contract and field dictionary. The command preserves every input row and writes a new private output directory.

```bash
python3 -m m2_signal.analysis_eligibility \
  --features <PRIVATE_INPUT_ROOT>/feature-checkpoint0001.jsonl \
  --contract <PRIVATE_INPUT_ROOT>/analysis-contract.json \
  --field-dictionary <PRIVATE_INPUT_ROOT>/field-dictionary.json \
  --output <PRIVATE_RUN_ROOT>/analysis-eligibility-r3 \
  --expected-features-sha256 <FEATURE_SHA256> \
  --expected-contract-sha256 <CONTRACT_SHA256> \
  --expected-field-dictionary-sha256 <DICTIONARY_SHA256> \
  --expected-rows 2352
```

This route does no fitting, network access, media decode, or semantic promotion. Missing values remain missing; likes and comments have their own outcome gates. The status is `ELIGIBILITY_COMPLETE_FIT_PENDING_REVIEWED_EVIDENCE`; later fitting requires the accepted analysis contract and a separate evidence review.

### Scene candidate extraction

Call `m2_orchestrator.scene_media.extract_scene_media` from the reviewed scene stage with a bound observed media record, transcript, and reviewed scene annotations. The output directory must be fresh and private. The extractor is capped at 48 decoded frames, 16 MiB per collage, and 64 MiB total scene output; it performs one indexed decode for the requested union, preserves decoded PTS and hashes, and retains partial failures. The 64-frame coarse semantic review in the accompanying receipt is evidence for candidate extraction only.

```bash
python3 -m pytest -q tests/test_scene_media.py
```

Do not expose collages, source media, transcripts, or signed URLs. A technical frame receipt is not a confirmed shot or accepted semantic scene.

### Optional transcript recovery

Recovery is an explicit offline operator action for one retained source record. Preflight is the default and does not launch a worker. Use a fresh private output directory, a frozen local model bundle, and an absolute interpreter path. The parent invokes at most one chunk worker at a time; each core window is at most 30 seconds with at most 1 second context on each side, two CPU threads, one worker, 900-second child timeout, 1.5 GiB sampled parent RSS watchdog, and 512 MiB sampled FFmpeg RSS watchdog. Audio output is bounded and hash-bound.

```bash
python3 scripts/run_m2_transcription_recovery.py \
  --record-json <PRIVATE_INPUT_ROOT>/media-record.json \
  --source-root <PRIVATE_MEDIA_ROOT> \
  --model-dir <FROZEN_MODEL_DIR> \
  --output-dir <PRIVATE_RUN_ROOT>/transcription-recovery-r7 \
  --python-executable <ABSOLUTE_MEDIA_PYTHON> \
  --run
```

Use `--run` only after separate operator approval and a paused reviewed checkpoint; omit `--run` for preflight-only validation. Recovery remains optional and review pending. The bounded R7 pilot completed with one retried chunk; its aggregate remains `SUSPICIOUS_TIMINGS` with `analysis_ready=false` and `approved=false`. Multi-window overlap is retained as non-additive evidence and cannot become `analysis_ready` without independent timing, boundary, and acoustic review. Empty output, unknown audio, partial chunks, and decode or ASR failures remain explicit states. No HikerAPI client, URL fallback, model download, package install, or deletion is performed.

```bash
python3 -m pytest -q tests/test_transcription_recovery.py tests/test_transcription_chunk_worker.py
```

The v2 delivery review receipt records the exact pending status and excludes all run-specific media, transcript text, identities, secrets, and absolute private paths.
