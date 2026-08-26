-- Additive terminal integrity, run/source lineage, and idempotency hardening.

BEGIN;
SET search_path = north_hux, public;

CREATE UNIQUE INDEX IF NOT EXISTS uq_artifact_edge_normalized
    ON artifact_edge (parent_artifact_id, child_artifact_id, edge_type, COALESCE(claim_locator, ''));

CREATE UNIQUE INDEX IF NOT EXISTS uq_collection_job_run_stage
    ON collection_job (run_id, adapter_id, platform, job_type, COALESCE(target_stratum, ''));

CREATE UNIQUE INDEX IF NOT EXISTS uq_metric_snapshot_content_observation
    ON metric_snapshot (content_id, metric_definition_id, observed_at)
    WHERE content_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_metric_snapshot_account_observation
    ON metric_snapshot (account_id, metric_definition_id, observed_at)
    WHERE account_id IS NOT NULL;

DROP INDEX IF EXISTS uq_content_analysis_run_natural;
CREATE UNIQUE INDEX uq_content_analysis_run_natural
    ON content_analysis_artifact (
        run_id, content_id, analyzer_key, analyzer_version, input_bundle_sha256
    );

CREATE TABLE IF NOT EXISTS transcript_identity (
    content_id bigint NOT NULL REFERENCES content_item(content_id),
    transcript_sha256 text NOT NULL CHECK (transcript_sha256 ~ '^[0-9a-f]{64}$'),
    transcript_id bigint NOT NULL REFERENCES transcript(transcript_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (content_id, transcript_sha256),
    UNIQUE (transcript_id)
);

INSERT INTO transcript_identity (content_id, transcript_sha256, transcript_id)
SELECT DISTINCT ON (content_id, transcript_sha256)
    content_id, transcript_sha256, transcript_id
FROM transcript
WHERE transcript_sha256 IS NOT NULL
ORDER BY content_id, transcript_sha256, transcript_id
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS run_source_observation (
    run_source_observation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES research_run(run_id),
    source_id bigint NOT NULL REFERENCES source_registry(source_id),
    source_role text NOT NULL CHECK (source_role IN (
        'direct','adjacent','format_leader','technical_authority','counterexample','noise','owned','official_context'
    )),
    discovery_route text,
    rights_state text NOT NULL CHECK (rights_state IN (
        'pending','metadata_only','commentary_allowed','local_media_allowed','public_projection_allowed','blocked'
    )),
    observed_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_id, source_id)
);

CREATE TABLE IF NOT EXISTS run_terminal_receipt (
    run_terminal_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES research_run(run_id),
    version integer NOT NULL CHECK (version >= 1),
    status text NOT NULL CHECK (status IN ('pass','pass_with_limitations','failed','blocked')),
    cohort_count integer NOT NULL CHECK (cohort_count = 10000),
    transcript_manifest_count integer NOT NULL CHECK (transcript_manifest_count = cohort_count),
    frame_manifest_count integer NOT NULL CHECK (frame_manifest_count = cohort_count),
    cohort_sha256 text NOT NULL CHECK (cohort_sha256 ~ '^[0-9a-f]{64}$'),
    artifact_manifest_sha256 text NOT NULL CHECK (artifact_manifest_sha256 ~ '^[0-9a-f]{64}$'),
    database_backup_sha256 text NOT NULL CHECK (database_backup_sha256 ~ '^[0-9a-f]{64}$'),
    verification_json jsonb NOT NULL,
    maker text NOT NULL,
    reviewer text NOT NULL,
    supersedes_terminal_receipt_id bigint REFERENCES run_terminal_receipt(run_terminal_receipt_id),
    frozen_at timestamptz NOT NULL DEFAULT now(),
    CHECK (maker <> reviewer),
    UNIQUE (run_id, version)
);

DROP TRIGGER IF EXISTS run_source_observation_append_only ON run_source_observation;
CREATE TRIGGER run_source_observation_append_only
BEFORE UPDATE OR DELETE ON run_source_observation
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();

DROP TRIGGER IF EXISTS transcript_identity_append_only ON transcript_identity;
CREATE TRIGGER transcript_identity_append_only
BEFORE UPDATE OR DELETE ON transcript_identity
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();

DROP TRIGGER IF EXISTS run_terminal_receipt_append_only ON run_terminal_receipt;
CREATE TRIGGER run_terminal_receipt_append_only
BEFORE UPDATE OR DELETE ON run_terminal_receipt
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();

CREATE OR REPLACE VIEW v_social_studio_candidate_v2
WITH (security_barrier = true)
AS
WITH latest_axes AS (
    SELECT
        review.content_id,
        count(*) FILTER (
            WHERE review.decision = 'pass'
              AND (review.valid_until IS NULL OR review.valid_until > now())
              AND rights.decision = 'pass'
              AND rights.allowed_use IN ('metadata_only','commentary','transcript','public_projection')
              AND (rights.expires_at IS NULL OR rights.expires_at > now())
        ) AS passing_axis_count,
        count(*) FILTER (
            WHERE review.decision IN ('block','uncertain')
               OR (review.valid_until IS NOT NULL AND review.valid_until <= now())
               OR rights.decision <> 'pass'
               OR rights.allowed_use NOT IN ('metadata_only','commentary','transcript','public_projection')
               OR (rights.expires_at IS NOT NULL AND rights.expires_at <= now())
        ) AS nonpassing_axis_count
    FROM v_latest_studio_axis_review review
    JOIN v_latest_content_rights_decision rights
      ON rights.rights_decision_id = review.rights_decision_id
    GROUP BY review.content_id
), latest_release AS (
    SELECT DISTINCT ON (content_id)
        release.*
    FROM studio_content_release_review release
    ORDER BY content_id, reviewed_at DESC, studio_content_release_review_id DESC
), current_contract AS (
    SELECT * FROM v_current_social_studio_contract
), latest_rights AS (
    SELECT
        content.content_id,
        bool_or(
            rights.decision = 'pass'
            AND rights.allowed_use IN ('metadata_only','commentary','transcript','public_projection')
            AND (rights.expires_at IS NULL OR rights.expires_at > now())
        ) AS rights_pass
    FROM content_item content
    LEFT JOIN v_latest_content_rights_decision rights
      ON rights.content_id = content.content_id OR rights.source_id = content.source_id
    GROUP BY content.content_id
)
SELECT
    content.content_id,
    content.platform,
    content.native_content_id,
    content.canonical_url,
    account.account_id,
    account.handle,
    account.qualification_state,
    COALESCE(latest_axes.passing_axis_count, 0) AS passing_axis_count,
    COALESCE(latest_axes.nonpassing_axis_count, 0) AS nonpassing_axis_count,
    COALESCE(latest_rights.rights_pass, false) AS rights_pass,
    COALESCE(current_contract.state = 'active', false) AS contract_active,
    COALESCE(
        latest_release.decision = 'pass'
        AND latest_release.public_safe
        AND latest_release.maker_actor <> latest_release.reviewer_actor
        AND (latest_release.valid_until IS NULL OR latest_release.valid_until > now()),
        false
    ) AS release_pass,
    CASE
        WHEN account.qualification_state = 'qualified'
         AND COALESCE(latest_axes.passing_axis_count, 0) = 12
         AND COALESCE(latest_axes.nonpassing_axis_count, 0) = 0
         AND COALESCE(latest_rights.rights_pass, false)
         AND COALESCE(current_contract.state = 'active', false)
         AND COALESCE(
             latest_release.decision = 'pass'
             AND latest_release.public_safe
             AND latest_release.maker_actor <> latest_release.reviewer_actor
             AND (latest_release.valid_until IS NULL OR latest_release.valid_until > now()),
             false
         )
        THEN 'eligible'
        ELSE 'gated'
    END AS studio_candidate_state
FROM content_item content
JOIN platform_account account ON account.account_id = content.account_id
LEFT JOIN latest_axes ON latest_axes.content_id = content.content_id
LEFT JOIN latest_rights ON latest_rights.content_id = content.content_id
LEFT JOIN latest_release ON latest_release.content_id = content.content_id
LEFT JOIN current_contract ON current_contract.contract_key = latest_release.contract_key;

COMMIT;
