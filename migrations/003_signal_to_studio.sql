-- Append-only PostgreSQL bridge for the validated Signal-to-Studio v1 contract.
-- This migration persists existing immutable exports and exposes social candidates,
-- but deliberately does not invent missing Studio classifications.

BEGIN;

SET search_path = north_hux, public;

CREATE TABLE IF NOT EXISTS studio_signal_export (
    studio_signal_export_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES research_run(run_id),
    source_content_id bigint REFERENCES content_item(content_id),
    export_id text NOT NULL UNIQUE,
    export_version integer NOT NULL CHECK (export_version > 0),
    signal_record_id text NOT NULL,
    schema_version text NOT NULL,
    payload_json jsonb NOT NULL,
    record_hash text NOT NULL UNIQUE CHECK (record_hash ~ '^sha256:[0-9a-f]{64}$'),
    taxonomy_version text NOT NULL,
    rights_state text NOT NULL CHECK (rights_state IN ('metadata_commentary_only','original_local_previsualization','blocked')),
    generated_at timestamptz NOT NULL,
    supersedes_export_id text REFERENCES studio_signal_export(export_id),
    public_safe boolean NOT NULL DEFAULT false,
    ingestion_source text NOT NULL,
    inserted_at timestamptz NOT NULL DEFAULT now(),
    CHECK (export_id <> COALESCE(supersedes_export_id, '')),
    CHECK (payload_json ? 'schema' AND payload_json->>'schema' = 'signal-to-studio.v1'),
    CHECK (payload_json ? 'external_provider_state' AND payload_json->>'external_provider_state' = 'NOT_RUN'),
    CHECK (payload_json ? 'pattern'),
    CHECK (payload_json #>> '{provenance,record_hash}' = record_hash)
);

CREATE INDEX IF NOT EXISTS idx_studio_signal_source_content
    ON studio_signal_export(source_content_id, generated_at DESC);

CREATE OR REPLACE FUNCTION reject_studio_signal_export_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'studio_signal_export is append-only; insert a superseding export instead';
END;
$$;

DROP TRIGGER IF EXISTS studio_signal_export_append_only ON studio_signal_export;
CREATE TRIGGER studio_signal_export_append_only
BEFORE UPDATE OR DELETE ON studio_signal_export
FOR EACH ROW EXECUTE FUNCTION reject_studio_signal_export_mutation();

CREATE OR REPLACE VIEW v_signal_to_studio_v1
WITH (security_barrier = true)
AS
SELECT
    current_export.export_id,
    current_export.signal_record_id,
    current_export.export_version,
    current_export.source_content_id,
    current_export.schema_version,
    current_export.record_hash,
    current_export.taxonomy_version,
    current_export.rights_state,
    current_export.generated_at,
    current_export.public_safe,
    current_export.payload_json
FROM studio_signal_export AS current_export
WHERE NOT EXISTS (
    SELECT 1
    FROM studio_signal_export AS successor
    WHERE successor.supersedes_export_id = current_export.export_id
);

CREATE OR REPLACE VIEW v_social_studio_candidate_v1
WITH (security_barrier = true)
AS
WITH classification_coverage AS (
    SELECT
        classification.content_id,
        count(DISTINCT classification.dimension) FILTER (
            WHERE classification.dimension IN (
                'hook_mechanism', 'viewer_job', 'broll_function', 'proof_form',
                'visual_grammar', 'pacing_profile', 'transition_family',
                'a_roll_integration', 'sound_role', 'text_role', 'cta_exit',
                'risk_class'
            )
            AND classification.epistemic_state IN ('observed','derived','classified')
        ) AS reviewed_axis_count
    FROM classification
    GROUP BY classification.content_id
), evidence_coverage AS (
    SELECT
        content.content_id,
        count(DISTINCT evidence.evidence_id) AS evidence_count
    FROM content_item AS content
    LEFT JOIN evidence_record AS evidence
      ON evidence.source_id = content.source_id
      OR evidence.raw_object_id IN (
          SELECT raw.raw_object_id FROM raw_object AS raw WHERE raw.source_id = content.source_id
      )
      OR evidence.transcript_segment_id IN (
          SELECT segment.transcript_segment_id
          FROM transcript_segment AS segment
          JOIN transcript ON transcript.transcript_id = segment.transcript_id
          WHERE transcript.content_id = content.content_id
      )
      OR evidence.frame_artifact_id IN (
          SELECT frame.frame_artifact_id
          FROM frame_artifact AS frame
          JOIN media_asset AS media ON media.media_asset_id = frame.media_asset_id
          WHERE media.content_id = content.content_id
      )
    GROUP BY content.content_id
), gate_state AS (
    SELECT
        content.content_id,
        content.platform,
        content.native_content_id,
        content.canonical_url,
        account.account_id,
        account.handle,
        account.qualification_state,
        COALESCE(classification_coverage.reviewed_axis_count, 0) AS reviewed_axis_count,
        COALESCE(evidence_coverage.evidence_count, 0) AS evidence_count,
        EXISTS (
            SELECT 1 FROM rights_decision
            WHERE rights_decision.content_id = content.content_id
              AND rights_decision.decision = 'pass'
              AND rights_decision.allowed_use IN ('metadata_only','commentary','transcript','public_projection')
        ) AS rights_pass,
        EXISTS (
            SELECT 1 FROM review_task
            WHERE review_task.object_type = 'content'
              AND review_task.object_id = content.content_id
              AND review_task.review_type = 'taxonomy'
              AND review_task.status IN ('passed','passed_with_limitations')
        ) AS taxonomy_review_pass,
        EXISTS (
            SELECT 1 FROM review_task
            WHERE review_task.object_type = 'content'
              AND review_task.object_id = content.content_id
              AND review_task.review_type = 'rights'
              AND review_task.status IN ('passed','passed_with_limitations')
        ) AS rights_review_pass
    FROM content_item AS content
    JOIN platform_account AS account ON account.account_id = content.account_id
    LEFT JOIN classification_coverage ON classification_coverage.content_id = content.content_id
    LEFT JOIN evidence_coverage ON evidence_coverage.content_id = content.content_id
)
SELECT
    gate_state.*,
    'SIG-SOC-' || upper(gate_state.platform) || '-' || upper(substr(encode(sha256(convert_to(
        gate_state.platform || chr(31) || gate_state.native_content_id || chr(31) || gate_state.canonical_url,
        'UTF8'
    )), 'hex'), 1, 32)) AS candidate_signal_record_id,
    CASE
        WHEN gate_state.qualification_state = 'qualified'
         AND gate_state.rights_pass
         AND gate_state.reviewed_axis_count = 12
         AND gate_state.evidence_count > 0
         AND gate_state.taxonomy_review_pass
         AND gate_state.rights_review_pass
        THEN 'eligible'
        ELSE 'gated'
    END AS studio_candidate_state,
    array_remove(ARRAY[
        CASE WHEN gate_state.qualification_state <> 'qualified' THEN 'account_not_qualified' END,
        CASE WHEN NOT gate_state.rights_pass THEN 'rights_not_passed' END,
        CASE WHEN gate_state.reviewed_axis_count <> 12 THEN 'studio_axes_incomplete' END,
        CASE WHEN gate_state.evidence_count = 0 THEN 'evidence_missing' END,
        CASE WHEN NOT gate_state.taxonomy_review_pass THEN 'taxonomy_review_missing' END,
        CASE WHEN NOT gate_state.rights_review_pass THEN 'rights_review_missing' END
    ], NULL) AS missing_gates
FROM gate_state;

COMMIT;
