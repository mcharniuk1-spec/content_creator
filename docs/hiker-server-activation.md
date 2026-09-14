# Future HikerAPI server activation

This is an operator procedure for a separately approved future server run. No step here was executed against HikerAPI during this integration. Keep the current `cron.sh` on existing-data analysis until the pilot, budget, source rights, response schema and server secret configuration have been reviewed.

## Prepare a one-request pilot

Copy `config/hiker-pilot.template.json` and `config/hiker-approval.template.json` into a private ignored directory. The templates deliberately fail validation and are not approvals.

Fill the collection config with the exact public account ID/handle and authorized source route, capture date, nullable publication-window lower bound, one-page/one-request maximum, request timeout and explicit cost ceilings. `price_receipt_sha256` identifies a dated tariff/endpoint-cost receipt verified by the operator. Do not assume a price from an old README or count a reservation as an actual charge.

```sh
python3 hiker_server.py --config .local/hiker-pilot.json
```

This command validates a local plan and prints the exact `config_sha256`, account count, request limit and budget. It does not read an API key or call HikerAPI.

The owner approval must record the real approver/event, `approved=true`, the exact printed config hash, timezone-aware expiry and the scope `hikerapi_instagram_reels_collection`. A pilot also requires `live_schema_probe_approved=true`. Do not grant another scope implicitly. Leave `schema_receipt_sha256` null until an independently reviewed actual response package exists.

Provide the existing HikerAPI key through the server's approved secret injection mechanism as `HIKER_KEY` or `HIKERAPI_KEY`. Never paste the value into configuration JSON, command arguments, Markdown, shell history, Git or a task log.

## Execute only after exact authorization

```sh
python3 hiker_server.py --config .local/hiker-pilot.json --private-dir .local/hiker --approval .local/pilot-approval.json --execute
```

A run folder under the private directory binds config, endpoint and execution mode. It contains immutable dispatch reservations, response pages, checkpoints, temporary media references, normalized exports and completion/blocked receipts. Fixture folders cannot be resumed as live folders. Cached responses must match page hashes, expected request parameters and checkpoint pagination; missing or inconsistent records stop before any new request.

Approval, expiry, revocation and any live schema receipt are rechecked immediately before every dispatch. There are no automatic retries after uncertain transport outcomes. A timeout still reserves its declared upper budget until billing/outcome reconciliation. Page caps, budget stops and schema failures are incomplete coverage; they are not source exhaustion. Published-date filtering continues across pages because feeds may contain pinned or out-of-order items.

A stale `collector.lock` means the process may have been interrupted. First check whether the process still runs, then inspect its dispatch/checkpoint receipt. Do not simply delete the lock and blindly repeat the request. Unknown outcomes require operator reconciliation and a separately authorized recovery/new run.

The CLI returns nonzero when collection is blocked. The raw/blocked receipt remains available for diagnosis. A shell scheduler must treat that exit as required attention.

## Review the actual response before wider collection

Use `config/hiker-schema-review.template.json` to prepare a private schema-evidence package. Its `response_path` must remain inside the package and resolve to the actual pilot response; `response_sha256` must match that file. The endpoint, live source declaration, review verdict, expiry, maker and distinct reviewer must be explicit. Current OpenAPI documents the request parameters but does not by itself prove the flat response pagination shape.

After independent review, prepare a new config/run ID with the exact bounded account/page/request/window/budget scope. Obtain a new owner approval binding both the config hash and the exact schema-receipt file hash. Then use `--schema-receipt`. No fixture receipt may be relabeled as live evidence.

[Official OpenAPI](https://api.hikerapi.com/openapi.json) was checked by the integrator on 2026-09-05. Live response/schema, billing and server connectivity remain unverified by this integration.

## Chain a permitted capture into the same offline engine

```sh
python3 hiker_server.py --config .local/approved-collection.json --private-dir .local/hiker --approval .local/collection-approval.json --schema-receipt .local/schema-proof/review.json --execute --then-replay-run-id reviewed-capture-001 --then-replay-run-dir .local/reviewed-capture-001 --database .local/signal.sqlite
```

After successful collection the CLI freezes its collection receipt with the export and invokes the same 12 deterministic local stages used by manual and scheduled replay. This does not activate semantic agents, final Signal release, Notion, provider generation or publishing.

A blocked capture does not chain by default. If a partial diagnostic analysis is explicitly useful, add `--allow-partial-replay`; the receipt remains marked partial and the command still returns a nonzero blocked-collection exit. Partial analysis cannot establish collection completeness or final Best-Reel acceptance.

An already completed export can instead be analyzed separately:

```sh
python3 run.py --yes --source-dir .local/hiker/APPROVED_RUN_ID/export --run-id replay-001 --run-dir .local/replay-001 --database .local/signal.sqlite --mode incremental
```

The collector saves short-lived signed media references privately. The Python adapter supports an immediate separately approved `on_media` callback; this CLI does not download media. Before attaching an automated media-acquisition worker, define its URL/download limits, source rights, data retention, file/hash/probe receipt and callback approval scope. Until then, transcript/scene acquisition remains an explicit pending task. A canonical Reel URL or saved CDN reference is not proof of decoded media.

Only after the reviewed pilot and a bounded end-to-end server check should Michael choose whether and how to schedule this separate collector entry. No Git pull, install, service change or timer activation occurs as a side effect of these files.
