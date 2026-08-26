# Hybrid existing-video editing pipeline

Status: `schema-checked` and `locally tested with deterministic fixtures`; provider execution and real-media execution remain gated.

## Control flow

```text
approved local source
  -> ffprobe metadata + SHA-256
  -> Codex/AI analysis artifact (timecoded candidates, transcript/visual notes)
  -> human/reviewer selection
  -> canonical JSON Edit Decision List (EDL)
  -> validation: rights, path roots, source hash, timecodes, captions, provider gates
  -> FFmpeg render: trim/concat, aspect/crop, conservative color, audio leveling, captions
  -> ffprobe output validation + render manifest
  -> optional OTIO export
  -> optional Resolve human finishing
```

The EDL is the authority for execution. AI proposes decisions; it does not directly mutate media. FFmpeg is the deterministic worker. Resolve is a finishing handoff and is not driven by this pipeline.

## CLI

From the project root:

```bash
# Read-only probe and baseline candidate map for Codex review
python3 -m edit_pipeline.cli analyze INPUT.mp4 analysis.json

# Convert Codex-selected candidate IDs into the canonical EDL
python3 -m edit_pipeline.cli plan --case case.json --analysis analysis.json \
  --select shot-001,shot-003 --output edit-decision-list.json \
  --captions captions.json

# Validate a reviewed EDL before rendering
python3 -m edit_pipeline.cli validate edit-decision-list.json

# Render only when the case rights/path/approval gates pass
python3 -m edit_pipeline.cli render edit-decision-list.json OUTPUT.mp4 --case case.json

# Export OTIO only if OpenTimelineIO is already installed
python3 -m edit_pipeline.cli otio edit-decision-list.json timeline.otio

# Reproduce the safe local integration fixture
python3 -m edit_pipeline.cli fixture runs/<run-id>/fixture
```

## Contract and safety rules

- `schemas/edit-decision-list.schema.json` defines source hashes, ordered timecoded segments, timeline geometry, color/audio presets, captions, and policy state.
- `schemas/edit-pipeline-case.schema.json` defines rights, consent, allowed media/output roots, local-render approval, Resolve finishing, and provider/repair policy.
- `templates/edit-pipeline-case.example.json` and `templates/edit-captions.example.json` provide the starting input shapes.
- Only `synthetic_fixture`, `owner_owned_approved`, or `licensed_approved` sources may render.
- Paths must stay inside the case's explicit roots; source hash drift blocks rendering.
- Generative repair is disabled by default. A repair entry requires an exceptional approval and still cannot turn provider execution on.
- Captions are embedded as an MP4 `mov_text` track; a sidecar SRT is generated in the render work directory.
- OTIO is optional and never installed implicitly. When unavailable, the JSON EDL remains the truthful portable timeline and a `NOT_AVAILABLE` receipt is written.

## Resolve handoff

Resolve remains an optional human-finishing step after the deterministic render. The pipeline does not import media, create timelines, or call the Resolve MCP. A future handoff may pass the render manifest and OTIO file to the owner for review.

## Generative repair lane

Shot-level repair is an exception, not the assembly path. The current implementation records repair policy and refuses unapproved repair entries. Any future provider activation needs a separate admission covering the exact provider/model, media sent, rights/consent, retention, cost, fallback, and reviewer verdict.
