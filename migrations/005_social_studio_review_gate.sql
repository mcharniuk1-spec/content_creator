-- Harden the social-to-Studio gate with explicit contract and maker/reviewer records.
-- No contract is activated and no social export is created by this migration.

BEGIN;
SET search_path = north_hux, public;

CREATE TABLE IF NOT EXISTS social_studio_contract (
    contract_key text PRIMARY KEY,
    schema_id text NOT NULL CHECK (schema_id = 'signal-to-studio.v1.1'),
    contract_version integer NOT NULL CHECK (contract_version >= 1),
    state text NOT NULL CHECK (state IN ('pending','active','blocked','retired')),
    schema_sha256 text NOT NULL CHECK (schema_sha256 ~ '^sha256:[0-9a-f]{64}$'),
    review_receipt_uri text,
    reviewed_by text,
    activated_at timestamptz,
    retired_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (state <> 'active' OR (activated_at IS NOT NULL AND reviewed_by IS NOT NULL AND review_receipt_uri IS NOT NULL)),
    UNIQUE (schema_id, contract_version)
);

CREATE TABLE IF NOT EXISTS studio_axis_review (
    studio_axis_review_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content_id bigint NOT NULL REFERENCES content_item(content_id),
    classification_id bigint NOT NULL REFERENCES classification(classification_id),
    axis_dimension text NOT NULL CHECK (axis_dimension IN (
        'hook_mechanism', 'viewer_job', 'broll_function', 'proof_form',
        'visual_grammar', 'pacing_profile', 'transition_family',
        'a_roll_integration', 'sound_role', 'text_role', 'cta_exit', 'risk_class'
    )),
    evidence_id bigint NOT NULL REFERENCES evidence_record(evidence_id),
    rights_decision_id bigint NOT NULL REFERENCES rights_decision(rights_decision_id),
    codebook_version text NOT NULL,
    taxonomy_version text NOT NULL CHECK (taxonomy_version = 'studio-shortform@1.0.0'),
    criterion text NOT NULL,
    decision text NOT NULL CHECK (decision IN ('pass','block','uncertain')),
    maker_actor text NOT NULL,
    reviewer_actor text NOT NULL,
    classification_hash text NOT NULL CHECK (classification_hash ~ '^sha256:[0-9a-f]{64}$'),
    reviewed_at timestamptz NOT NULL,
    valid_until timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (maker_actor <> reviewer_actor),
    UNIQUE (content_id, classification_id, axis_dimension, classification_hash, reviewer_actor)
);

CREATE TABLE IF NOT EXISTS studio_content_release_review (
    studio_content_release_review_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content_id bigint NOT NULL REFERENCES content_item(content_id),
    contract_key text NOT NULL REFERENCES social_studio_contract(contract_key),
    classification_set_hash text NOT NULL CHECK (classification_set_hash ~ '^sha256:[0-9a-f]{64}$'),
    decision text NOT NULL CHECK (decision IN ('pass','block','uncertain')),
    maker_actor text NOT NULL,
    reviewer_actor text NOT NULL,
    public_safe boolean NOT NULL DEFAULT false,
    reviewed_at timestamptz NOT NULL,
    valid_until timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (maker_actor <> reviewer_actor),
    UNIQUE (content_id, contract_key, classification_set_hash, reviewer_actor)
);

CREATE INDEX IF NOT EXISTS idx_studio_axis_review_content
    ON studio_axis_review(content_id, axis_dimension, decision, reviewed_at DESC);
CREATE INDEX IF NOT EXISTS idx_studio_release_content
    ON studio_content_release_review(content_id, decision, reviewed_at DESC);

DROP TRIGGER IF EXISTS social_studio_contract_append_only ON social_studio_contract;
CREATE TRIGGER social_studio_contract_append_only
BEFORE UPDATE OR DELETE ON social_studio_contract
FOR EACH ROW EXECUTE FUNCTION reject_collection_observation_mutation();

DROP TRIGGER IF EXISTS studio_axis_review_append_only ON studio_axis_review;
CREATE TRIGGER studio_axis_review_append_only
BEFORE UPDATE OR DELETE ON studio_axis_review
FOR EACH ROW EXECUTE FUNCTION reject_collection_observation_mutation();

DROP TRIGGER IF EXISTS studio_content_release_review_append_only ON studio_content_release_review;
CREATE TRIGGER studio_content_release_review_append_only
BEFORE UPDATE OR DELETE ON studio_content_release_review
FOR EACH ROW EXECUTE FUNCTION reject_collection_observation_mutation();

DROP VIEW IF EXISTS v_social_studio_candidate_v1;

CREATE VIEW v_social_studio_candidate_v1
WITH (security_barrier = true)
AS
WITH axis_coverage AS (
    SELECT
        axis_review.content_id,
        count(DISTINCT axis_review.axis_dimension) AS reviewed_axis_count
    FROM studio_axis_review AS axis_review
    JOIN classification
      ON classification.classification_id = axis_review.classification_id
     AND classification.content_id = axis_review.content_id
     AND classification.dimension = axis_review.axis_dimension
    JOIN evidence_record AS evidence ON evidence.evidence_id = axis_review.evidence_id
    JOIN rights_decision AS rights ON rights.rights_decision_id = axis_review.rights_decision_id
    JOIN content_item AS content ON content.content_id = axis_review.content_id
    WHERE axis_review.decision = 'pass'
      AND (axis_review.valid_until IS NULL OR axis_review.valid_until > now())
      AND axis_review.maker_actor <> axis_review.reviewer_actor
      AND rights.decision = 'pass'
      AND rights.allowed_use IN ('metadata_only','commentary','transcript','public_projection')
      AND (rights.expires_at IS NULL OR rights.expires_at > now())
      AND (rights.content_id = content.content_id OR rights.source_id = content.source_id)
      AND (
          evidence.source_id = content.source_id
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
      )
    GROUP BY axis_review.content_id
), release_state AS (
    SELECT DISTINCT ON (release.content_id)
        release.content_id,
        release.decision = 'pass'
          AND release.public_safe
          AND release.maker_actor <> release.reviewer_actor
          AND (release.valid_until IS NULL OR release.valid_until > now())
          AND contract.state = 'active'
          AND contract.activated_at IS NOT NULL
          AND contract.reviewed_by IS NOT NULL
          AND contract.review_receipt_uri IS NOT NULL AS release_pass,
        contract.state = 'active' AS contract_active
    FROM studio_content_release_review AS release
    JOIN social_studio_contract AS contract ON contract.contract_key = release.contract_key
    ORDER BY release.content_id, release.reviewed_at DESC, release.studio_content_release_review_id DESC
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
        COALESCE(axis_coverage.reviewed_axis_count, 0) AS reviewed_axis_count,
        COALESCE(evidence_coverage.evidence_count, 0) AS evidence_count,
        COALESCE(release_state.release_pass, false) AS release_pass,
        COALESCE(release_state.contract_active, false) AS contract_active,
        EXISTS (
            SELECT 1 FROM rights_decision
            WHERE rights_decision.content_id = content.content_id
              AND rights_decision.decision = 'pass'
              AND rights_decision.allowed_use IN ('metadata_only','commentary','transcript','public_projection')
              AND (rights_decision.expires_at IS NULL OR rights_decision.expires_at > now())
        ) AS rights_pass
    FROM content_item AS content
    JOIN platform_account AS account ON account.account_id = content.account_id
    LEFT JOIN axis_coverage ON axis_coverage.content_id = content.content_id
    LEFT JOIN evidence_coverage ON evidence_coverage.content_id = content.content_id
    LEFT JOIN release_state ON release_state.content_id = content.content_id
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
         AND gate_state.contract_active
         AND gate_state.release_pass
        THEN 'eligible'
        ELSE 'gated'
    END AS studio_candidate_state,
    array_remove(ARRAY[
        CASE WHEN gate_state.qualification_state <> 'qualified' THEN 'account_not_qualified' END,
        CASE WHEN NOT gate_state.rights_pass THEN 'rights_not_passed_or_expired' END,
        CASE WHEN gate_state.reviewed_axis_count <> 12 THEN 'axis_reviews_incomplete' END,
        CASE WHEN gate_state.evidence_count = 0 THEN 'content_evidence_missing' END,
        CASE WHEN NOT gate_state.contract_active THEN 'social_interface_contract_inactive' END,
        CASE WHEN NOT gate_state.release_pass THEN 'content_release_review_missing' END
    ], NULL) AS missing_gates
FROM gate_state;

COMMIT;
