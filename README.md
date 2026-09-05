# M2Lab Content Engine

Two connected engines turn Instagram research into original, reviewable videos. **Signal** audits observations and produces scoped descriptive evidence. **Studio** develops scripts and shooting plans, waits for owner footage, then composes approved assets with Remotion.

Start with [the current architecture](docs/m2-system-architecture.md), [the operator guide](docs/m2-operator-guide.md), and [the public handoff](docs/handoff/current-public-handoff.md). The explicit state DAG lives in `m2_orchestrator/policy.py`; the stage-worker skill and role registry define bounded agent execution.

## Run existing data without HikerAPI

```bash
python3 scripts/run_m2.py --source-dir path/to/export --run-dir .local/run-001 --run-id run-001
python3 -m m2_orchestrator --run-dir .local/run-001 status
python3 -m m2_orchestrator --run-dir .local/run-001 tasks
python3 -m m2_orchestrator --run-dir .local/run-001 verify
```

Same inputs resume completed stages after hash verification. New snapshots/configs use a new run ID; pass `--database .local/signal.sqlite --mode incremental` to share immutable historical observations. The engine never turns a missing metric into zero. It stops semantic work at explicit role/review boundaries.

## Runtime boundaries

- Python standard library supplies the controller, Signal database and descriptive metrics.
- FFmpeg/ffprobe and local ASR provide the optional media evidence path.
- `studio/remotion/` contains pinned composition/renderer dependencies and local fixture tests.
- HikerAPI is a separately approved server collector. Replay never checks its balance or reads its key.
- Provider generation requires an exact shot, model, references, rights and budget approval.
- Notion is a versioned review projection. WikiLLM/Obsidian receive curated reviewed knowledge.
- Model execution on a subscription is an interactive operator capability, not an unattended free API.

## Current evidence boundary

The September 4 accepted foundation has 2,363 observations resolving to 2,352 Reels and 100 accounts. It is not a fully evidenced market/production release. Current execution status and precise checks belong in the dated delivery handoff. Source media, geography, rights, comments, transcript fidelity and strategic review retain separate denominators.

Instagram Reels is the only active research platform. YouTube runs, old North Hux outputs and legacy methods are archived evidence, never current M2Lab rankings or script support. Existing sources and accepted runs are preserved.

## Main folders

| Path | Purpose |
|---|---|
| `m2_orchestrator/` | State transitions, role tasks, offline handlers and projection outbox |
| `m2_signal/` | Immutable evidence database, audits, metrics and server collection adapter |
| `m2_studio/` | Local media/scene pipeline, EDL and provider job contracts |
| `studio/remotion/` | Deterministic vertical composition and render validation |
| `agents/`, `skills/`, `config/` | Roles, executable defaults, stage policy and hooks |
| `knowledge/` | Reviewed portable project brain |
| `docs/`, `tests/` | Architecture, operating instructions and checks |
| `runs/`, `.local/` | Private/ignored source evidence, artifacts and execution receipts |

Only an explicit reviewed public-safe package belongs in Git. Source exports, founder transcripts, credentials, media and mutable databases do not.
