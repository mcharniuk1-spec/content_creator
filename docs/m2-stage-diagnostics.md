# Stage diagnostics and incremental delivery

## Local device operating limit

Run one local job at a time. Keep local generative-model inference disabled on
the owner's device until a separate bounded resource test passes. Do not run
multiple model pipelines, renderers or ASR workers together. The interrupted
AnimateDiff/MPS test is not a usable backend or a completed video proof.

For this delivery, validation uses small fixtures and existing SQLite/JSON
files. No large model remains running. Cached weights do not imply an active
process and are not installed into the project environment. A future media
worker must use an explicit timeout, a memory budget appropriate to its host,
one-file-at-a-time processing and an interrupt/cleanup path. Use an OS/container
memory limit for a hard cap; an advisory profile or Python timeout cannot
guarantee total-device RAM limits. Inspect peak resident memory before raising
concurrency. The server's resource budget is separate from this local device.

The controller SQLite database is the execution authority. Signal's append-only
SQLite ledger is the research authority. Notion is a reviewed projection of a
dated release. A stage marked `PASS_WITH_LIMITATIONS` is not proof of full media
coverage or of a production-ready script.

## Inspect a frozen run without modifying it

```bash
python3 -m m2_orchestrator.diagnostics \
  --state .local/run-001/state.sqlite \
  --signal .local/signal.sqlite \
  --output .local/diagnostics/run-001.sqlite
```

Use a separate output file. Both source databases are opened with SQLite
`mode=ro`, `query_only` and a read transaction. Output paths that alias either
source, including hard links, are rejected. Each source is read consistently;
the two independent databases are not an atomic distributed snapshot. Export
only after the source release has been frozen, and verify the release binding.

The `m2.diagnostic-v2` export contains:

| Table | Meaning and required interpretation |
| --- | --- |
| diagnostic_exports | Run/config/policy identity and logical SQL hashes of the transaction snapshots. These hashes include committed WAL content; they are not physical file hashes. |
| diagnostic_stages | Actual recorded state, role actor, attempt count, output goal, limitation count and receipt/artifact provenance. Unstarted stages remain unstarted. Goals come from the installed policy; use the run's pinned policy bundle. |
| diagnostic_events | Ordered event trace and direct source-chain validation. Credential keys and worker tokens are masked after validation; the masked payload cannot recompute the original event hash. |
| diagnostic_stage_artifacts | Expected and observed SHA-256 for each bound file, with missing, changed and unsafe-path states. |
| diagnostic_metrics | Actual supplied Reel metrics and compatible account metrics, including unit, denominator, observed count, formula version, null flag and validation findings. Missing optional account tables do not produce invented metrics. |
| diagnostic_issues | Errors, proposed remedies and opening/resolution event evidence. A remedy is a proposed next step until a later completion proves resolution. |

Repeated exports revalidate source snapshots and all artifact bytes before
reporting idempotence. They regenerate the diagnostic rows, so a cached result
cannot hide a changed artifact. Inspect `state_events_ok`, artifact validation,
metric validation and open issues separately. Export success means the report
was written; it does not mean every stage or metric passed. Diagnostics never
unlocks a downstream controller gate and never changes a source-stage state.

## Incremental Notion procedure

Keep the versioned full release in the local ledger and downloadable CSV. Keep
the report's main linked views filtered to the reviewed candidate selection.
The first existing-data projection may retain a complete backing database for
audit; hiding rows in a view does not delete evidence.

For a later run:

1. Freeze a new source release and run its numeric and evidence checks. Export
   its full CSV and dictionary, with explicit null and formula semantics.
2. Reuse the verified target mapping for each stable Reel code, Account username
   and ScriptCard ID. Fetch current properties before preparing an update.
3. Call `projection.plan(new_release, stable_object_id, desired_engine_fields,
   existing=current_properties, previous_engine_fields=last_verified_fields)`.
   The action key identifies the release/action; the stable target mapping
   identifies the existing Notion page. Do not treat a new release as a reason
   to create the same entity again.
4. Stage the exact action in `Outbox`. Resolve conflicts with newer human edits.
   Preserve owner Status, Lead, Priority and decision fields. Bind the current
   property hash before dispatch and read back every projected field afterward.
5. Create only genuinely new entities. Reconcile uncertain creates by their
   stable identity before retrying. Do not retry an uncertain create blindly.
6. Refresh the selected views from the reviewed selection file. Keep excluded
   entities in the local release/export and historical reports. Do not delete
   existing Notion pages or owner notes as a selection side effect.
7. Attach the full CSV, complete dictionary, dated dashboard and review receipt
   to the run report. Record attachment hashes and read back the page.

The operator uses the connected Notion MCP. The modules do not hide browser
authentication or send writes automatically. `NULL` in the CSV represents a
missing value; missing derived metrics may also reflect validity or support
gates. Formula-like strings are escaped for spreadsheet import. Split CSV parts
each have a header; concatenate their data rows and keep one header to rebuild
the complete export. Never concatenate all repeated headers as data.

## Media completeness and restart

The source map must enumerate every expected Reel, including missing entries.
Report separate denominators for source files, audible speech, ASR output,
reviewed transcript, timed rhetorical sections, decoded frame sets, reviewed
semantic scenes and complete multimodal evidence. Empty ASR is not verified
silence. ASR segment boundaries are not rhetorical or scene boundaries.

When source media arrives, bind local relative paths, SHA-256, source and rights
state; start a new implementation-bound run using the existing ledger. Do not
rewrite a frozen evidence release or mark previously unobserved media complete.
Dispatch ASR quality and structural review to separate agents, retain failures
and repair receipts, then repeat the statistical benchmark and card review.

## Local generative-model test boundary

A valid MP4 is only a container check. A local model is usable only after output
frames pass prompt adherence and motion review, latent values remain finite,
and the output passes media QA. Failed visual tests remain failed even when
inference returned normally. A local test requires cached pinned weights and
local compute; it has no hosted inference token charge. Commercial provider
activation and first/last-frame control require separate capability evidence.
