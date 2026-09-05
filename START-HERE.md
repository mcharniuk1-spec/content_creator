# Start here

The current entry processes existing Instagram evidence using the same Signal, state controller and Studio code as the Content Engine. It records what happened, what remains missing and which role owns the next stage.

1. Read [README.md](README.md), the [architecture](docs/m2-system-architecture.md), the [operator guide](docs/m2-operator-guide.md), and [knowledge routing](knowledge/index.md).
2. Run `python3 run.py` for the zero-call plan and `python3 scripts/test_local.py` for clean-checkout checks. No private database or dependency installation is required for the core tests. Optional FFmpeg tests report a skip if binaries are unavailable.
3. Back up the existing Radar database, restore it to a disposable new path, and verify it before changing the selected server checkout. Keep the original database unchanged.
4. Select an existing export or an exact completed legacy snapshot. Execute `run.py --yes` with an explicit run ID/directory; optionally use a shared `--database` for immutable incremental history and `--until` for a bounded stop.
5. Verify the state trace and export remaining role tasks. Review the text, actual source scenes and strategic context before accepting a Signal release. A completed audit does not prove complete transcript or frame coverage.
6. Create original ScriptCard candidates, review claims and shot plans, select the presenter and wait for recorded footage. Bind approved takes before final composition. Generation is optional and separately approved.
7. Activate the server timer only after local review and a pinned-code handoff. Its explicit configuration may choose the latest completed snapshot; it will never launch the paid collector on its own.

HikerAPI remains Michael's server route. `hiker_server.py` provides an explicit plan and separately approved single-request pilot. It preserves null counters, reserves budget before dispatch, writes immutable checkpoints and stops on uncertain outcomes. Broad collection requires a reviewed actual schema receipt. No Hiker request was made while preparing this integration.

`POSITIONING.md`, `SPEC.md`, `RULES.md`, `PLAN.md` and the legacy scripts remain available as project history. Current execution boundaries come from the shared architecture, role/skill contracts and guarded entrypoints. Prior statements about schedules, tariffs, automatic production or model quality are not fresh runtime proof.

The portable brain starts in `knowledge/index.md`; the raw founder transcript and competitor media are not part of that portable context. Pending-review capsules state their status and may not be promoted as accepted evidence merely because they are present in the repository.
