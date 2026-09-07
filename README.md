# M2 Lab Radar: Signal and Studio

This fork contains a shared, traceable content workflow: Signal audits Instagram evidence and produces reviewed insights; Studio develops original scripts, shot plans and Remotion compositions. The local runner processes existing exports or a completed database snapshot. Collection, video generation and external writeback have separate explicit entry gates.

Start with [START-HERE.md](START-HERE.md), then the [architecture](docs/m2-system-architecture.md) and [operator guide](docs/m2-operator-guide.md). The existing [POSITIONING.md](POSITIONING.md) is preserved. The current derived [writer context](knowledge/m2-positioning.md) states its review status and the intended nontechnical small-business audience.

## First commands

```sh
python3 run.py
python3 scripts/test_local.py
python3 run.py --yes --source-dir path/to/export --run-id run-001 --run-dir .local/run-001
python3 -m m2_orchestrator --run-dir .local/run-001 verify
python3 -m m2_orchestrator --run-dir .local/run-001 tasks
```

`run.py` without `--yes` prints a plan and makes zero external calls. Local replay requires Python 3.10+ and its standard library. Twelve deterministic stages freeze the inputs/config, ingest observations, calculate audits/diagnostics and inventory transcript/media/comment evidence. Missing material becomes a typed gap. Semantic analysis, independent review, ScriptCards and production remain explicit downstream work.

## Existing Radar database and incremental history

```sh
python3 run.py --yes --legacy-db data/radar.db --snapshot-date YYYY-MM-DD --run-id snapshot-001 --run-dir .local/snapshot-001 --database .local/signal.sqlite --mode incremental
```

The bridge opens the legacy database read-only and accepts a completed snapshot. The shared SQLite ledger retains immutable history and separate release membership. New source/config/implementation versions use a new run. Existing raw counters, nulls and capture dates survive. A descriptive ranking is a review queue; it is not proof of a final Best Reel, a causal mechanism or future performance.

## Server timer

Review `config/server-replay.example.json` and save the actual configuration privately. The explicit `latest_completed` selector reads the newest completed legacy snapshot; `{snapshot_date}` in the configured run ID and directory creates a separate frozen run for each capture. Repeated timer calls for the same snapshot resume without recollection.

```sh
M2_RUN_CONFIG=.local/server-config.json bash cron.sh
```

The timer invokes the same engine. It does not pull Git, install dependencies, change cron, call HikerAPI, run an LLM or publish. `install-cron.sh` prints deployment guidance only. Michael retains control of server activation and the separate collection schedule.

The updated timer requires explicit `private_run_root` and `private_source_roots` in its private configuration. An optional `media_job_config` enables retained-media acquisition, local CPU transcription and regular/change frames after a verified complete replay. It remains off by default. Read [the partner media integration guide](integrations/radar/README.md) before migrating the timer configuration. A partner-host media smoke test is still required.

## Future HikerAPI pilot

```sh
python3 hiker_server.py --config .local/hiker-pilot.json
python3 hiker_server.py --config .local/hiker-pilot.json --private-dir .local/hiker --approval .local/pilot-approval.json --execute
```

The first command validates a plan without reading a key or making a request. The second is a separately approved server action. Use one request while the flat response schema remains unverified. The exact config requires public account scope, date/window, page/request limits, timeout, a dated price receipt and cost ceilings. Approval binds the config hash, owner event, scope and expiry. The key is injected only through `HIKER_KEY` or `HIKERAPI_KEY`. No Desktop MCP file, `.env` parsing, browser cookie or secret argument is used by this entry.

A larger run also requires `--schema-receipt` with an independently reviewed, hash-bound actual response from the approved pilot. See [the activation procedure and templates](docs/hiker-server-activation.md) and [Signal's adapter contract](m2_signal/README.md). Fixture tests here do not establish live schema, billing, connectivity or media availability. The legacy `collect_snapshot.py` and `lib/hiker.py` are retained for history and compatibility review; they are not invoked by current runners.

## Studio and media

The shared [Studio package](m2_studio/README.md) validates approved media, local transcription, cut candidates, semantic-scene timing, deterministic 2/4/6 sampling and EDL assets. [Remotion sources](studio/remotion/README.md) provide deterministic composition and rendering. The [dated provider assessment](docs/m2-provider-assessment.md) records documented capabilities and execution gaps. Renderer dependencies and browser setup are a separate operator step; no dependency is installed by the Python or timer entries. Optional generated inserts require exact provider/model/reference/rights/budget approval, and fixtures are distinct from actual provider execution.

Script/strategy workers use `agents/m2-roles.json`, `skills/m2-stage-worker/SKILL.md`, and `skills/m2-script-writer/SKILL.md`. Makers cannot review themselves. Owner-recorded footage, model authentication/payment and final publication are explicit later gates.

## Safety and provenance

The 6 September media recovery foundation adds an uncapped identity manifest, resumable per-Reel/modality SQLite traces, bounded local workers, a reviewed semantic task/review queue, and coverage-aware feature exports. The real full-corpus run is still in progress; shipping this code is not a completion or generation-quality claim. Loore AI remains optional. Tests for the optional stack require the declared test environment; the standard-library replay remains available independently.

Keep exports, SQLite files, source media, raw transcripts, signed CDN URLs, API responses, approval files and secrets in private ignored directories. No raw corpus or account-specific ranking is distributed with these shared packages. Notion is a reconciled review projection with owner-edit preservation and exact readback, not analytical authority. Knowledge files contain reviewed methods and constrained context; raw founder/creator expression stays run-local.

The source tree is pinned during execution. `docs/shared-engine-sync.json` records the exact shipped shared files. Historical documentation under `docs/legacy/` describes the earlier implementation and must not be read as current authorization, billing or production evidence.

## Reviewed ten-card release

See [the ten-card handoff](docs/m2-ten-card-release.md) for five introductions, five regular scripts, original storyboards, validation and the owner-footage handoff. The [example slate](examples/ten-card-20260907/manifest.json) compiles through the existing Studio timeline route. Private source transcripts and Notion targets stay outside Git.
