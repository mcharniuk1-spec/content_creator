# Fal queue integration

Status: provider-disabled implementation seam, fixture-tested on 2026-09-14. No Fal request, SDK install, credential file read, or paid generation was performed.

`m2_studio/fal_provider.py` implements `FalQueueTransport`, which satisfies the existing `Transport` protocol and is intended to be passed to `ProviderJobs`. `ProviderJobs` remains responsible for the SQLite reservation, immutable activation envelope, budget ceiling, request hash, and ambiguous-submit reconciliation. The Fal adapter adds provider-specific queue handling without changing that authority.

The adapter accepts an explicit immutable mapping shaped as:

```python
{
    "text_to_video": {
        "fal-ai/approved-model": FalModelSpec(
            "https://queue.fal.run/fal-ai/approved-model",
            build_approved_model_payload,
        )
    }
}
```

Each model supplies its own payload builder. The adapter does not pretend that Fal models share generic fields. The queue URL must be HTTPS, use the exact `queue.fal.run` origin, contain the exact model path, and contain no credentials, query, or fragment. Returned status, response, and optional cancellation URLs are validated against the same origin before they are persisted in the durable provider handle.

The default is disabled. When explicitly enabled after activation, the adapter reads only `FAL_KEY` from the environment unless a secret is injected by the caller. It never reads credential files. The key is sent as the `Authorization: Key ...` header and is never included in an exception or durable handle. HTTP redirects are refused so a key cannot follow an unapproved origin. The adapter performs one POST per logical submit and has no blind submit retry.

Before POST, the full canonical request digest must be present in the frozen `approved_request_hashes` tuple. The provider name, capability, model, and model-specific builder are checked before network I/O. The returned handle contains the model, Fal request ID, and validated queue URLs. A missing or malformed ID/URL fails closed.

Polling maps `IN_QUEUE` and `IN_PROGRESS` to `RUNNING`. `FAILED` and `CANCELLED` remain terminal provider states. `COMPLETED` is checked for Fal `error` or `error_type`; either produces a typed `FAILED` result. A clean `COMPLETED` status triggers a separate GET of the response URL. The returned object is attached as `result` with `media_qa_state: PENDING`. The presence of a `video.url` is not proof that the media is valid, rights-approved, decodable, or suitable for composition. Result ingestion, hashing, probing, rights review, and media QA remain separate stages. Cancellation returns `CANCEL_REQUESTED`; a pending cancel request does not become a final job state.

The focused tests in `tests/test_fal_provider.py` cover disabled operation, exact request-hash gating, model/origin admission, model-specific payloads, sanitized provider errors, redirect refusal, completed-with-error handling, clean completion plus response retrieval, and the separate media-QA state. They use fake HTTP responses only.

Configuration is recorded in `config/m2-fal.v1.json` with execution disabled and no active model mapping. The official queue reference used for the seam is [Fal queue inference documentation](https://fal.ai/docs/documentation/model-apis/inference/queue). Documentation availability does not establish account entitlement, price, reliability, output quality, or production readiness.
# Local credential handoff

The owner-provided `key_fal.yaml` stays ignored and owner-readable only. Its legacy `falai="..."` spelling is not a general YAML configuration format. `python scripts/with_fal_key.py -- <command> ...` safely parses only the known key field and injects `FAL_KEY` into that command's environment without shell evaluation or printing the value. The transport itself reads no credential files. Do not run a generation command until its exact request and model are approved. Shared deployment uses a secret store instead of copying this local file into Git or MCP prompts.
