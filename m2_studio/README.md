# Studio execution and media evidence

Studio turns a reviewed script into a typed, deterministic Remotion edit. Research media processing is reusable by Signal but does not promote cut scores or ASR output into reviewed scenes. All default execution is local. Provider jobs are disabled until a separate activation packet is approved.

## Executable boundaries

1. `inventory`: approve a bounded local root and a hash/rights map; ffprobe decodes frame timestamps. Emit typed attempts for every supplied item.
2. `transcribe`: select an existing Whisper `.pt` model explicitly. Extract local mono 16 kHz PCM, detect exact digital silence, run CPU Whisper with word timestamps, retain raw and normalized outputs. There is no download fallback. Empty output, absent audio, decode failure, silence, and unavailable media remain different states.
3. `cuts`: FFmpeg scene scores produce timecoded **candidate changes**. Confirmation, source continuity and semantic interpretation belong to separate analyst/reviewer tasks.
4. `scenes`: analyst supplies full-duration scene annotations with an information job, semantic boundary reason, transcript intersections and 2/4/6 sampling choice. Frames use actual decoded PTS and half-open intervals. One collage per scene, maximum 48 source screenshots per video. This is evidence for review; the extractor never approves its own scenes.
5. `card-edl`: original ScriptCard shots, narration segments and optional approved asset bindings become `m2.remotion-edl.v1`. Missing owner recordings are visible preview placeholders. Production rendering rejects placeholders and requires an approved EDL.
6. Remotion composes A-roll, separate split-screen plates, image/demo layers, deterministic editable text/captions and independent audio stems. FFmpeg/ffprobe validate output codecs, dimensions, timing and sample frames. `edit_pipeline/` remains the optional existing FFmpeg-only trimming/normalization fallback.
7. Provider job planning reserves a maximum charge in SQLite. Exact activation binds provider, models, capability receipt, approval, expiry and per-job/run budgets. Single submit, bounded polling, uncertainty reconciliation, output ingestion and billing reconciliation are separate operations. A failed or timed-out request does not prove zero cost.

## Run each state independently

From the repository root:

```sh
python3 -m m2_studio inventory --root APPROVED_MEDIA_ROOT --map media-map.json --output inventory.json
python3 -m m2_studio media-map --root APPROVED_MEDIA_ROOT --map media-map.json --output NEW_ATTEMPT_DIR --model EXISTING_WHISPER_MODEL.pt
python3 -m m2_studio transcribe --root APPROVED_MEDIA_ROOT --media media.json --model EXISTING_WHISPER_MODEL.pt --output NEW_TRANSCRIPT_ATTEMPT --language en
python3 -m m2_studio cuts --root APPROVED_MEDIA_ROOT --media media.json --output cuts.json --threshold 0.32
python3 -m m2_studio scenes --root APPROVED_MEDIA_ROOT --media media.json --transcript transcript.json --annotations scenes.json --output NEW_FRAME_ATTEMPT
python3 -m m2_studio card-edl --card card.json --output edl.json
python3 -m m2_studio card-edl --card card.json --bindings approved-bindings.json --alignment reviewed-speech-alignment.json --output recording-bound-edl.json
python3 -m m2_studio validate-edl --edl edl.json --assets APPROVED_ASSET_ROOT
```

`media.json` is one observed inventory entry. A media-map has `run_id`, `expected_codes` (all canonical corpus codes), and `entries`. Each entry needs `code`, a safe `media_id`, root-relative `path`, exact `sha256`, `source_kind`, and `rights`. Rights need `analysis_allowed: true` plus `receipt_id`; owner recordings also need `owner_consent: true`. `public_display_allowed` is independent and defaults false. Missing entries emit `LOCAL_MEDIA_NOT_SUPPLIED`; nothing queries HikerAPI or follows a URL. Signal imports `m2.signal-media-attempt-export.v1` keyed by `code` and must preserve separate modality states/denominators. Raw media/transcripts stay in private or run-local ignored storage.

Use a new attempt directory after a failed partial decode; the media extractor refuses to overwrite frame/audio evidence. The controller owns attempt IDs, scheduling, leases and cross-engine state; these CLIs own only their stage artifacts. Each successful stage receives the prior artifact hash and returns an output hash to that controller.

An audio file binding alone is not timeline placement. Its binding needs an explicit `stem` object containing `role`, `from_frame`, `duration_frames`, `trim_before_frames`, and `volume`. The adapter creates an audio stem only from that placement; absent or unplaced audio stays in `pending_audio_assets`. Production rejects any pending audio. A speaking card also requires a speech stem and an independently reviewed alignment receipt with `review_state: APPROVED`, `receipt_id`, the exact `source_card_hash`, and `audio_asset_hashes` mapping every used speech asset ID to its verified file hash. The controller verifies that receipt before final approval. Merely adding an audio file or marking the EDL approved cannot produce an accepted silent speaking card.

The current `graphic` layer is explicitly an unbuilt visual-plan description. Production rejects it. Build the actual deterministic diagram/demo as a separately verified image/video asset and bind it, or introduce a separately reviewed implemented-graphic contract. Editable `text` overlays are supported directly; preview descriptions must not be exported as final graphics.

The speech receipt also requires `alignment_plan_sha256`, computed with Python `alignment_plan_hash(edl)` or Node `alignmentPlanHash(edl)`. The versioned canonical plan binds the source-card hash, timebase, all used audio hashes, ordered stem roles/placement/trims/gain, and exact caption timing/text. UTF-8 sorted JSON plus float64 gain bytes produces identical digests across both runtimes. Any timing, caption, stem or audio change needs a new independently reviewed receipt; recalculating a digest alone is not approval.

## Scene annotation shape

```json
{
  "scene_id": "scene-01", "start_ms": 0, "end_ms": 4200,
  "sample_count": 4, "maker": "scene-analyst",
  "information_job": "Demonstrate the changed state after the action",
  "boundary_reasons": ["proof"],
  "transcript_segment_ids": ["T00001"]
}
```

Pass an array of these objects. `align_scenes` verifies exact transcript intersection; it does not invent semantics. Annotators can use cut candidates plus transcript arguments to find useful boundaries, then inspect sampled evidence. If a cut candidate is the only reason, validation fails. Word timings are emitted only when observed. OCR, confirmed shots, manual transcript correction, semantic review and scene acceptance require explicit additional agent artifacts; they are not inferred by the local extractor.

The transcript's `source_media_hash` must equal the observed inventory media hash before alignment or extraction. Direct Python callers supply `source_media_hash` to `align_scenes` and the exact `transcript` to `extract_scenes`; the CLI passes both explicitly. Scene candidates and the final scene-evidence artifact retain `transcript_sha256` (the canonical JSON artifact digest) and `transcript_source_media_hash`. Reusing another video's transcript or changing it after alignment fails before frame output is created.

The accepted September 4 contract uses half-open intervals. The historical `studio/validate_scene_segmentation.py` expects an inclusive end-frame locator, so it must not validate the new `m2.scene-evidence.v1`. An end sample is the last decoded frame **inside** the scene, not a frame at `end_ms` in the following scene. Raw PTS, normalization offset and VFR evidence are retained.

## Provider activation

`ProviderJobs` is tested with fake transports only. `RunwayImageTransport` is implemented against current official SDK types for `seedance2_5`, `veo3.1`, `veo3.1_fast`, and `gen4.5`. It accepts an injected Runway client and approved reference-byte resolver. It is disabled by default, forces SDK retries to zero, verifies the official HTTPS origin, hashes reference bytes, sends only approved image references and limits insert duration. It does not weaken content moderation or support identity/voice generation. The Runway SDK is optional and was not installed in this run; activation requires a pinned SDK installation and live smoke test after payment/approval.

Direct payment is to the chosen generation API account. Local Python, SQLite, FFmpeg and eligible Remotion rendering need no orchestration subscription. Third-party models through Runway are gateway billing; direct Google billing is an alternative requiring its own adapter and acceptance test. Neither path means zero generation charges. Choose on tested shot-specific quality, failure-adjusted cost and latency, not marketing rankings.

For activation, supply the exact provider/account route, model and version receipt, approved shot/script/reference hashes, content/rights/retention terms, named secret-store injection, currency and maximum spend, maximum one paid submit, bounded polling, failure/refund reconciliation, output retention and reviewer. No key is needed to review or run the local pipeline. Provider output URLs, credentials and raw requests must not be projected to Notion or Git.

Activation requires an explicit `approved_request_hashes` array of reviewed full-request digests computed with `m2_studio.media.object_hash`. Each digest binds every field, including run/card/shot, prompt, ordered reference hashes, rights receipt, all parameters, approval/capability receipts and maximum cost. The worker snapshots that approval envelope and recomputes the stored request digest at both submit and poll; it also verifies the digest equals the immutable job ID. Missing or wildcard digests, modified requests and mutated caller-side approval lists fail before transport execution. Reusing an approval ID never approves a different prompt, asset, right or parameter. A changed request needs its own exact owner-approved digest.

When a submit times out or the worker crashes in `SUBMITTING`, retain reservation and stop at `SUBMIT_UNKNOWN`/reconciliation; never resubmit automatically. A later reconciler can attach the actual provider job ID and billing receipt. Failed/cancelled jobs retain their reservation until a billing receipt proves the actual charge. Refunds and costs must be reconciled explicitly. Paid-output ingestion/QA remains a separate required adapter; do not claim a completed job is a usable asset.

## Tests

```sh
python3 -m unittest discover -s tests -p 'test_m2_studio*.py' -v
python3 -m m2_studio.fixtures --output NEW_SYNTHETIC_FIXTURE_DIR
```

Tests cover actual FFmpeg decoding and 12 sampled source frames, rights/hash/path/clock failures, silence protection, exact scene/transcript binding, missing corpus attempts, provider disablement/reservations/ambiguous submission/reconciliation, model capabilities and timeline production gates. Real competitor media coverage, final script approval, paid generation and real owner footage are independent readiness claims.
