# Signal-to-Studio Database Interface v1

Status: `FILE-BACKED SOURCE CONTRACT / VERIFIED LOCAL POSTGRESQL MIRROR`

## Current truth

The active portable contract remains the hashed JSONL export. A local PostgreSQL 18 instance is verified at database `north_hux`; migrations `002_north_hux_market_intelligence.sql`, `003_signal_to_studio.sql`, `004_comment_transcript_provenance.sql`, and `005_social_studio_review_gate.sql` are applied. The 60 validated file-backed exports are mirrored in `north_hux.studio_signal_export` and exposed through `north_hux.v_signal_to_studio_v1`. Database credentials are intentionally not stored in this document.

## Ownership boundary

Signal owns source registry, raw-object pointers, evidence, rights, freshness, taxonomy versions, epistemic state, metric semantics, and immutable hashes. Studio consumes immutable exports and owns viewer job, hook, timing, A-roll/B-roll plan, composition, captions, transitions, audio role, prompts, and acceptance checks. Studio never rewrites Signal facts or expands rights.

## Current file-backed connection

```text
runs/.../source/evidence/rights artifacts
          ↓
outputs/signal-to-studio/v1/records.jsonl
          ↓
studio/framework-library/v1/*/signal-export.json
          ↓
studio/framework-library/v1/*/framework.json + frames/*.svg
```

The contract schema is `schemas/signal-to-studio.schema.json`. Stable cross-system IDs are strings (`SIG-`, `SIGEXP-`, `SRC-`, `EVID-`, `RIGHTS-`); internal SQL identity integers must never become the portable interface.

## Hash and null rules

- Use canonical UTF-8 JSON with sorted keys and no insignificant whitespace for record hashes.
- Preserve `sha256:` prefixes at the file boundary; normalize SQL's inconsistent bare-hash fields explicitly and reversibly.
- `null` means unavailable, unreturned, unauthorized, or inapplicable. It never means zero.
- `provenance.raw_object_state` disambiguates `AVAILABLE` from `NOT_AVAILABLE`; an empty source-hash array is valid only when no raw object was admitted.
- `signal_input.source_rights_state` describes the observed source boundary; top-level framework `rights_state` describes the original local Studio output.
- Exports are append-only snapshots. Corrections use `supersedes_export_id`; no in-place historical rewrite.
- Rights default to restrictive. `metadata_commentary_only` never authorizes media download, frame reuse, transcript publication, identity reuse, or source-expression copying.

## Verified PostgreSQL mapping

`north_hux.studio_signal_export` is append-only: corrections are new rows linked through `supersedes_export_id`; update and delete operations are rejected by a database trigger. `north_hux.v_signal_to_studio_v1` returns only current, non-superseded exports. `studio/load_file_signal_exports.py` validates every record against the local schema before idempotent insertion.

`north_hux.v_social_studio_candidate_v1` is the social-analysis staging boundary. Migration `005_social_studio_review_gate.sql` hardens eligibility: the account must be qualified; rights must pass and be unexpired; every one of the 12 axes needs an explicit content-bound evidence and rights review with maker/reviewer separation; a reviewed `signal-to-studio.v1.1` social contract must be active; and a separate public-safe content release review must pass. Current calibration social records remain gated, and no active social contract row exists. The database does not infer or fill missing creative axes.

Do not put Studio timing/composition fields into Signal source entities. Migration parity on another machine, least-privilege database roles, automated backups/restore drills, and a production service boundary remain gaps. This local mirror does not authorize provider generation, media reuse, publishing, deployment, or external writeback.

## Scene-first v3 mapping

For transcript-aligned video analysis use `schemas/video-scene-segmentation.schema.json`. Keep the database hierarchy explicit:

```text
video/content
  └─ transcript + transcript_segment
       └─ scene_unit (start/end ms + start/end frame bounds + boundary reason)
            ├─ sampled source screenshots (2/4/6, each pointer + hash + role)
            ├─ one scene collage (pointer + hash + rights state)
            ├─ shot/asset layers and production route
            ├─ voice/audio/subtitle plans
            └─ edit/compositing/transition handoff
```

`frame_artifact` stores source screenshot pointers and hashes; `visual_event` stores cut/angle/overlay/effect observations; `transcript_segment` stores the language interval; the scene-unit record joins them without copying raw media into the database. Generated storyboard frames stay in Studio's separate asset lineage. A `creator_replica` route is represented only as an explicitly gated request with identity, consent, disclosure, provider, retention/deletion, and owner approval fields; it is blocked by default.
