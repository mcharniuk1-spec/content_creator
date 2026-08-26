-- Shared artifact lineage and corrected append-only Studio current-state gates.
-- This migration is additive: v1 views remain available for historical receipts.

BEGIN;
SET search_path = north_hux, public;

CREATE TABLE IF NOT EXISTS artifact (
    artifact_id text PRIMARY KEY,
    run_id bigint REFERENCES research_run(run_id),
    content_id bigint REFERENCES content_item(content_id),
    artifact_type text NOT NULL,
    schema_id text NOT NULL,
    schema_version text NOT NULL,
    artifact_uri text NOT NULL,
    artifact_sha256 text NOT NULL CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
    source_hashes jsonb NOT NULL DEFAULT '[]'::jsonb,
    tool_key text NOT NULL,
    tool_version text NOT NULL,
    epistemic_state text NOT NULL CHECK (epistemic_state IN (
        'observed','derived','classified','inferred','hypothesized','gap','planned'
    )),
    rights_state text NOT NULL,
    maker_actor text NOT NULL,
    reviewer_actor text,
    review_state text NOT NULL CHECK (review_state IN (
        'unreviewed','passed','passed_with_limitations','failed','blocked','owner_review_pending'
    )),
    public_safe boolean NOT NULL DEFAULT false,
    supersedes_artifact_id text REFERENCES artifact(artifact_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (reviewer_actor IS NULL OR reviewer_actor <> maker_actor),
    UNIQUE (artifact_type, artifact_sha256)
);

CREATE TABLE IF NOT EXISTS artifact_edge (
    artifact_edge_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    parent_artifact_id text NOT NULL REFERENCES artifact(artifact_id),
    child_artifact_id text NOT NULL REFERENCES artifact(artifact_id),
    edge_type text NOT NULL CHECK (edge_type IN (
        'derived_from','normalizes','analyzes','supports_claim','selects','plans','renders','edits','exports','supersedes'
    )),
    claim_locator text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (parent_artifact_id <> child_artifact_id),
    UNIQUE (parent_artifact_id, child_artifact_id, edge_type, claim_locator)
);

CREATE TABLE IF NOT EXISTS social_studio_contract_version (
    social_studio_contract_version_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contract_key text NOT NULL,
    contract_version integer NOT NULL CHECK (contract_version >= 1),
    schema_id text NOT NULL CHECK (schema_id = 'signal-to-studio.v1.1'),
    state text NOT NULL CHECK (state IN ('pending','active','blocked','retired')),
    schema_sha256 text NOT NULL CHECK (schema_sha256 ~ '^sha256:[0-9a-f]{64}$'),
    review_receipt_uri text,
    reviewed_by text,
    effective_at timestamptz NOT NULL,
    supersedes_contract_version_id bigint REFERENCES social_studio_contract_version(social_studio_contract_version_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (state <> 'active' OR (reviewed_by IS NOT NULL AND review_receipt_uri IS NOT NULL)),
    UNIQUE (contract_key, contract_version)
);

CREATE TABLE IF NOT EXISTS edit_decision_list (
    edit_decision_list_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    script_package_id bigint NOT NULL REFERENCES script_package(script_package_id),
    version integer NOT NULL CHECK (version >= 1),
    edl_uri text NOT NULL,
    edl_sha256 text NOT NULL CHECK (edl_sha256 ~ '^[0-9a-f]{64}$'),
    timeline_duration_ms integer NOT NULL CHECK (timeline_duration_ms > 0),
    state text NOT NULL CHECK (state IN ('planned','validated','owner_review','approved','rendered','blocked','superseded')),
    supersedes_edl_id bigint REFERENCES edit_decision_list(edit_decision_list_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (script_package_id, version)
);

CREATE TABLE IF NOT EXISTS edl_segment (
    edl_segment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    edit_decision_list_id bigint NOT NULL REFERENCES edit_decision_list(edit_decision_list_id),
    shot_plan_id bigint REFERENCES shot_plan(shot_plan_id),
    segment_index integer NOT NULL CHECK (segment_index >= 1),
    timeline_start_ms integer NOT NULL CHECK (timeline_start_ms >= 0),
    timeline_end_ms integer NOT NULL CHECK (timeline_end_ms > timeline_start_ms),
    source_in_ms integer CHECK (source_in_ms IS NULL OR source_in_ms >= 0),
    source_out_ms integer CHECK (source_out_ms IS NULL OR source_out_ms > source_in_ms),
    asset_artifact_id text REFERENCES artifact(artifact_id),
    transition_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (edit_decision_list_id, segment_index)
);

CREATE OR REPLACE FUNCTION reject_timeline_overlap()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM edl_segment existing
        WHERE existing.edit_decision_list_id = NEW.edit_decision_list_id
          AND int4range(existing.timeline_start_ms, existing.timeline_end_ms, '[)')
              && int4range(NEW.timeline_start_ms, NEW.timeline_end_ms, '[)')
    ) THEN
        RAISE EXCEPTION 'EDL segment overlaps an existing segment';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS edl_segment_no_overlap ON edl_segment;
CREATE TRIGGER edl_segment_no_overlap
BEFORE INSERT ON edl_segment
FOR EACH ROW EXECUTE FUNCTION reject_timeline_overlap();

DROP TRIGGER IF EXISTS artifact_append_only ON artifact;
CREATE TRIGGER artifact_append_only
BEFORE UPDATE OR DELETE ON artifact
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();

DROP TRIGGER IF EXISTS artifact_edge_append_only ON artifact_edge;
CREATE TRIGGER artifact_edge_append_only
BEFORE UPDATE OR DELETE ON artifact_edge
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();

DROP TRIGGER IF EXISTS social_studio_contract_version_append_only ON social_studio_contract_version;
CREATE TRIGGER social_studio_contract_version_append_only
BEFORE UPDATE OR DELETE ON social_studio_contract_version
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();

DROP TRIGGER IF EXISTS edit_decision_list_append_only ON edit_decision_list;
CREATE TRIGGER edit_decision_list_append_only
BEFORE UPDATE OR DELETE ON edit_decision_list
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();

DROP TRIGGER IF EXISTS edl_segment_append_only ON edl_segment;
CREATE TRIGGER edl_segment_append_only
BEFORE UPDATE OR DELETE ON edl_segment
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();

CREATE OR REPLACE VIEW v_current_artifact AS
SELECT candidate.*
FROM artifact candidate
WHERE NOT EXISTS (
    SELECT 1 FROM artifact successor
    WHERE successor.supersedes_artifact_id = candidate.artifact_id
);

CREATE OR REPLACE VIEW v_current_social_studio_contract AS
SELECT DISTINCT ON (contract_key)
    social_studio_contract_version_id,
    contract_key,
    contract_version,
    schema_id,
    state,
    schema_sha256,
    review_receipt_uri,
    reviewed_by,
    effective_at
FROM social_studio_contract_version
ORDER BY contract_key, effective_at DESC, social_studio_contract_version_id DESC;

CREATE OR REPLACE VIEW v_latest_studio_axis_review AS
SELECT DISTINCT ON (content_id, axis_dimension)
    review.*
FROM studio_axis_review review
ORDER BY content_id, axis_dimension, reviewed_at DESC, studio_axis_review_id DESC;

CREATE OR REPLACE VIEW v_latest_content_rights_decision AS
SELECT DISTINCT ON (COALESCE(content_id, 0), COALESCE(source_id, 0), allowed_use)
    decision.*
FROM rights_decision decision
ORDER BY COALESCE(content_id, 0), COALESCE(source_id, 0), allowed_use,
         decided_at DESC, rights_decision_id DESC;

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
              AND (rights.expires_at IS NULL OR rights.expires_at > now())
        ) AS passing_axis_count,
        count(*) FILTER (
            WHERE review.decision IN ('block','uncertain')
               OR (review.valid_until IS NOT NULL AND review.valid_until <= now())
               OR rights.decision <> 'pass'
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
         AND COALESCE(latest_release.decision = 'pass' AND latest_release.public_safe, false)
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
