-- Additive 10K evidence-attempt, analysis, strategy, script, shot, edit, and backup lineage.
-- Raw transcript/media/frame bytes remain on disk; this schema stores pointers, hashes, and reviewed plans.

BEGIN;

SET search_path = north_hux, public;

CREATE OR REPLACE FUNCTION reject_append_only_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION '% is append-only; insert a superseding version instead', TG_TABLE_NAME;
END;
$$;

CREATE TABLE IF NOT EXISTS artifact_attempt (
    artifact_attempt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES research_run(run_id),
    content_id bigint NOT NULL REFERENCES content_item(content_id),
    stage text NOT NULL CHECK (stage IN ('transcript','frames','comments','metrics','video_analysis','visual_analysis')),
    attempt_number integer NOT NULL CHECK (attempt_number >= 1),
    state text NOT NULL CHECK (state IN ('observed','reused','gap','blocked','failed')),
    method text NOT NULL,
    reason_code text,
    command_receipt_uri text,
    artifact_uri text,
    artifact_sha256 text CHECK (artifact_sha256 IS NULL OR artifact_sha256 ~ '^[0-9a-f]{64}$'),
    captured_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (state NOT IN ('observed','reused') OR artifact_uri IS NOT NULL),
    CHECK (state NOT IN ('gap','blocked','failed') OR reason_code IS NOT NULL),
    UNIQUE (run_id, content_id, stage, attempt_number)
);

CREATE TABLE IF NOT EXISTS content_analysis_artifact (
    content_analysis_artifact_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES research_run(run_id),
    content_id bigint NOT NULL REFERENCES content_item(content_id),
    analyzer_key text NOT NULL,
    analyzer_version text NOT NULL,
    input_bundle_sha256 text NOT NULL CHECK (input_bundle_sha256 ~ '^[0-9a-f]{64}$'),
    analysis_uri text NOT NULL,
    analysis_sha256 text NOT NULL CHECK (analysis_sha256 ~ '^[0-9a-f]{64}$'),
    epistemic_state text NOT NULL CHECK (epistemic_state IN ('observed','derived','classified','inferred','hypothesized','gap')),
    review_state text NOT NULL CHECK (review_state IN ('unreviewed','passed','passed_with_limitations','failed','blocked')),
    supersedes_analysis_id bigint REFERENCES content_analysis_artifact(content_analysis_artifact_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (content_id, analyzer_key, analyzer_version, input_bundle_sha256)
);

CREATE TABLE IF NOT EXISTS strategy_release (
    strategy_release_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES research_run(run_id),
    release_key text NOT NULL,
    version integer NOT NULL CHECK (version >= 1),
    audience_json jsonb NOT NULL,
    pillar_json jsonb NOT NULL,
    evidence_bundle_sha256 text NOT NULL CHECK (evidence_bundle_sha256 ~ '^[0-9a-f]{64}$'),
    strategy_uri text NOT NULL,
    strategy_sha256 text NOT NULL CHECK (strategy_sha256 ~ '^[0-9a-f]{64}$'),
    state text NOT NULL CHECK (state IN ('draft','review','owner_review','approved','rejected','superseded')),
    maker text NOT NULL,
    reviewer text,
    review_verdict text CHECK (review_verdict IS NULL OR review_verdict IN ('pass','pass_with_limitations','fail','blocked')),
    supersedes_strategy_release_id bigint REFERENCES strategy_release(strategy_release_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (reviewer IS NULL OR reviewer <> maker),
    UNIQUE (release_key, version)
);

CREATE TABLE IF NOT EXISTS script_package (
    script_package_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    strategy_release_id bigint NOT NULL REFERENCES strategy_release(strategy_release_id),
    script_key text NOT NULL,
    version integer NOT NULL CHECK (version >= 1),
    sequence_position integer NOT NULL CHECK (sequence_position BETWEEN 1 AND 1000),
    creator_track text NOT NULL CHECK (creator_track IN ('pm_integration','governed_agent_operations','shared')),
    primary_platform text NOT NULL CHECK (primary_platform IN ('youtube_shorts','instagram_reels','tiktok')),
    target_duration_ms integer NOT NULL CHECK (target_duration_ms > 15000),
    schema_version text NOT NULL,
    package_uri text NOT NULL,
    package_sha256 text NOT NULL CHECK (package_sha256 ~ '^[0-9a-f]{64}$'),
    candidate_set_sha256 text NOT NULL CHECK (candidate_set_sha256 ~ '^[0-9a-f]{64}$'),
    claim_state text NOT NULL CHECK (claim_state IN ('evidence_bound','hypothesis_labeled','needs_review','blocked')),
    owner_state text NOT NULL CHECK (owner_state IN ('owner_review_pending','approved','rejected','superseded')),
    supersedes_script_package_id bigint REFERENCES script_package(script_package_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (script_key, version),
    UNIQUE (strategy_release_id, sequence_position)
);

CREATE TABLE IF NOT EXISTS shot_plan (
    shot_plan_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    script_package_id bigint NOT NULL REFERENCES script_package(script_package_id),
    shot_index integer NOT NULL CHECK (shot_index >= 1),
    start_ms integer NOT NULL CHECK (start_ms >= 0),
    end_ms integer NOT NULL CHECK (end_ms > start_ms),
    capture_mode text NOT NULL CHECK (capture_mode IN (
        'creator_aroll','creator_insert','screen_demo','deterministic_overlay',
        'ai_generated_broll','stock_or_licensed','source_reference_only',
        'transition_card','end_card','audio_only'
    )),
    evidence_role text NOT NULL CHECK (evidence_role IN ('proof','context','none','prohibited')),
    narration text,
    on_screen_text text,
    visual_spec_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    transition_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    audio_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    source_evidence_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
    asset_requirement_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    generation_state text NOT NULL CHECK (generation_state IN ('not_run','blocked_approval','approved_not_run','generated','failed')),
    rights_state text NOT NULL CHECK (rights_state IN ('original_plan','owner_media_required','licensed_required','provider_review_required','blocked')),
    acceptance_checks jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (capture_mode <> 'ai_generated_broll' OR evidence_role <> 'proof'),
    CHECK (capture_mode <> 'source_reference_only' OR evidence_role = 'prohibited'),
    UNIQUE (script_package_id, shot_index)
);

CREATE TABLE IF NOT EXISTS studio_edit_plan (
    studio_edit_plan_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    script_package_id bigint NOT NULL REFERENCES script_package(script_package_id),
    version integer NOT NULL CHECK (version >= 1),
    edl_uri text NOT NULL,
    edl_sha256 text NOT NULL CHECK (edl_sha256 ~ '^[0-9a-f]{64}$'),
    timeline_json jsonb NOT NULL,
    provider_generation_state text NOT NULL CHECK (provider_generation_state IN ('not_run','blocked_approval','approved_not_run','complete','failed')),
    creator_media_state text NOT NULL CHECK (creator_media_state IN ('not_received','partial','received','reviewed','blocked')),
    resolve_mutation_state text NOT NULL CHECK (resolve_mutation_state IN ('not_run','blocked_approval','approved_not_run','complete','failed')),
    final_video_state text NOT NULL CHECK (final_video_state IN ('not_run','rough_cut','review','approved','rejected')),
    publication_state text NOT NULL CHECK (publication_state IN ('not_run','blocked_approval','approved_not_run','published','failed')),
    supersedes_edit_plan_id bigint REFERENCES studio_edit_plan(studio_edit_plan_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (script_package_id, version)
);

CREATE TABLE IF NOT EXISTS backup_receipt (
    backup_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint REFERENCES research_run(run_id),
    backup_key text NOT NULL,
    backup_kind text NOT NULL CHECK (backup_kind IN ('postgres_custom','postgres_plain','artifact_manifest','artifact_archive','knowledge_export')),
    scope_json jsonb NOT NULL,
    artifact_uri text NOT NULL,
    artifact_sha256 text NOT NULL CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
    byte_size bigint NOT NULL CHECK (byte_size >= 0),
    encryption_state text NOT NULL CHECK (encryption_state IN ('not_required_local','encrypted','not_encrypted','blocked')),
    retention_until timestamptz,
    restore_test_state text NOT NULL CHECK (restore_test_state IN ('not_run','passed','failed','blocked')),
    restore_receipt_uri text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (backup_key)
);

CREATE INDEX IF NOT EXISTS idx_artifact_attempt_run_stage_state
    ON artifact_attempt(run_id, stage, state);
CREATE INDEX IF NOT EXISTS idx_content_analysis_run_review
    ON content_analysis_artifact(run_id, review_state, analyzer_key);
CREATE INDEX IF NOT EXISTS idx_script_package_strategy_sequence
    ON script_package(strategy_release_id, sequence_position);
CREATE INDEX IF NOT EXISTS idx_shot_plan_script_time
    ON shot_plan(script_package_id, start_ms, end_ms);
CREATE INDEX IF NOT EXISTS idx_backup_receipt_run_created
    ON backup_receipt(run_id, created_at DESC);

DROP TRIGGER IF EXISTS artifact_attempt_append_only ON artifact_attempt;
CREATE TRIGGER artifact_attempt_append_only
BEFORE UPDATE OR DELETE ON artifact_attempt
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();

DROP TRIGGER IF EXISTS content_analysis_artifact_append_only ON content_analysis_artifact;
CREATE TRIGGER content_analysis_artifact_append_only
BEFORE UPDATE OR DELETE ON content_analysis_artifact
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();

DROP TRIGGER IF EXISTS strategy_release_append_only ON strategy_release;
CREATE TRIGGER strategy_release_append_only
BEFORE UPDATE OR DELETE ON strategy_release
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();

DROP TRIGGER IF EXISTS script_package_append_only ON script_package;
CREATE TRIGGER script_package_append_only
BEFORE UPDATE OR DELETE ON script_package
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();

DROP TRIGGER IF EXISTS shot_plan_append_only ON shot_plan;
CREATE TRIGGER shot_plan_append_only
BEFORE UPDATE OR DELETE ON shot_plan
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();

DROP TRIGGER IF EXISTS studio_edit_plan_append_only ON studio_edit_plan;
CREATE TRIGGER studio_edit_plan_append_only
BEFORE UPDATE OR DELETE ON studio_edit_plan
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();

DROP TRIGGER IF EXISTS backup_receipt_append_only ON backup_receipt;
CREATE TRIGGER backup_receipt_append_only
BEFORE UPDATE OR DELETE ON backup_receipt
FOR EACH ROW EXECUTE FUNCTION reject_append_only_mutation();

CREATE OR REPLACE VIEW v_run_evidence_completeness AS
SELECT
    run_id,
    stage,
    count(*) AS attempts,
    count(*) FILTER (WHERE state IN ('observed','reused')) AS observed_or_reused,
    count(*) FILTER (WHERE state = 'gap') AS gaps,
    count(*) FILTER (WHERE state = 'blocked') AS blocked,
    count(*) FILTER (WHERE state = 'failed') AS failed,
    round(
        count(*) FILTER (WHERE state IN ('observed','reused'))::numeric
        / greatest(count(*), 1)::numeric * 100,
        2
    ) AS observed_percent
FROM artifact_attempt
GROUP BY run_id, stage;

CREATE OR REPLACE VIEW v_script_production_readiness AS
SELECT
    package.script_package_id,
    package.script_key,
    package.version,
    package.sequence_position,
    package.creator_track,
    package.owner_state,
    count(shot.shot_plan_id) AS shot_count,
    count(*) FILTER (WHERE shot.capture_mode IN ('creator_aroll','creator_insert')) AS creator_shots,
    count(*) FILTER (WHERE shot.capture_mode = 'screen_demo') AS screen_demo_shots,
    count(*) FILTER (WHERE shot.capture_mode = 'ai_generated_broll') AS ai_broll_shots,
    count(*) FILTER (WHERE shot.generation_state IN ('blocked_approval','approved_not_run')) AS provider_gated_shots,
    count(*) FILTER (WHERE shot.rights_state = 'blocked') AS rights_blocked_shots
FROM script_package AS package
LEFT JOIN shot_plan AS shot ON shot.script_package_id = package.script_package_id
GROUP BY package.script_package_id;

COMMIT;
