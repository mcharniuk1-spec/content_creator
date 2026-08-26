\set ON_ERROR_STOP on

BEGIN;
SET search_path = north_hux, public;

INSERT INTO research_run (run_key, status, scope_json, taxonomy_version, owner_gate)
VALUES ('smoke-content-engine-v3', 'validation', '{}'::jsonb, 'studio-shortform@1.0.0', 'pending')
RETURNING run_id \gset

INSERT INTO creator_entity (entity_key, entity_kind, display_name)
VALUES ('smoke-content-engine-v3-creator', 'solo_creator', 'Smoke Creator')
RETURNING creator_entity_id \gset

INSERT INTO platform_account (
    creator_entity_id, platform, native_account_id, canonical_url,
    primary_archetype, region_evidence_state, qualification_state
)
VALUES (
    :creator_entity_id, 'youtube', 'smoke-content-engine-v3-account',
    'https://www.youtube.com/channel/smoke-content-engine-v3',
    'mixed', 'unknown', 'qualified'
)
RETURNING account_id \gset

INSERT INTO content_item (
    account_id, platform, native_content_id, canonical_url, content_kind,
    format_evidence_state, title, duration_ms, rights_state
)
VALUES (
    :account_id, 'youtube', 'smoke-content-engine-v3-video',
    'https://www.youtube.com/watch?v=smoke-v3', 'unknown', 'unknown',
    'Smoke video', 27000, 'metadata_only'
)
RETURNING content_id \gset

INSERT INTO artifact_attempt (
    run_id, content_id, stage, attempt_number, state, method,
    artifact_uri, artifact_sha256, captured_at
)
VALUES (
    :run_id, :content_id, 'transcript', 1, 'observed', 'smoke',
    'normalized/transcripts/smoke.json', repeat('0', 64), now()
)
RETURNING artifact_attempt_id \gset

INSERT INTO strategy_release (
    run_id, release_key, version, audience_json, pillar_json,
    evidence_bundle_sha256, strategy_uri, strategy_sha256, state, maker
)
VALUES (
    :run_id, 'smoke-strategy', 1, '{}'::jsonb, '{}'::jsonb,
    repeat('1', 64), 'derived/smoke-strategy.json', repeat('2', 64), 'draft', 'maker'
)
RETURNING strategy_release_id \gset

INSERT INTO script_package (
    strategy_release_id, script_key, version, sequence_position, creator_track,
    primary_platform, target_duration_ms, schema_version, package_uri,
    package_sha256, candidate_set_sha256, claim_state, owner_state
)
VALUES (
    :strategy_release_id, 'smoke-script', 1, 1, 'pm_integration',
    'youtube_shorts', 27000, 'm2.script-package.v1',
    'studio/smoke/script.json', repeat('3', 64), repeat('4', 64),
    'evidence_bound', 'owner_review_pending'
)
RETURNING script_package_id \gset

INSERT INTO shot_plan (
    script_package_id, shot_index, start_ms, end_ms, capture_mode,
    evidence_role, narration, generation_state, rights_state
)
VALUES (
    :script_package_id, 1, 0, 2000, 'creator_aroll',
    'context', 'Smoke narration', 'not_run', 'owner_media_required'
);

INSERT INTO shot_plan (
    script_package_id, shot_index, start_ms, end_ms, capture_mode,
    evidence_role, narration, generation_state, rights_state
)
VALUES (
    :script_package_id, 2, 2000, 4000, 'ai_generated_broll',
    'context', 'Context only', 'blocked_approval', 'provider_review_required'
);

INSERT INTO studio_edit_plan (
    script_package_id, version, edl_uri, edl_sha256, timeline_json,
    provider_generation_state, creator_media_state, resolve_mutation_state,
    final_video_state, publication_state
)
VALUES (
    :script_package_id, 1, 'studio/smoke/edl.json', repeat('5', 64), '{}'::jsonb,
    'not_run', 'not_received', 'not_run', 'not_run', 'not_run'
);

INSERT INTO backup_receipt (
    run_id, backup_key, backup_kind, scope_json, artifact_uri,
    artifact_sha256, byte_size, encryption_state, restore_test_state
)
VALUES (
    :run_id, 'smoke-backup', 'artifact_manifest', '{}'::jsonb,
    'backups/smoke-manifest.json', repeat('6', 64), 1,
    'not_required_local', 'not_run'
);

DO $$
BEGIN
    BEGIN
        INSERT INTO shot_plan (
            script_package_id, shot_index, start_ms, end_ms, capture_mode,
            evidence_role, generation_state, rights_state
        )
        VALUES (
            (SELECT script_package_id FROM script_package WHERE script_key = 'smoke-script' AND version = 1),
            3, 4000, 6000, 'ai_generated_broll',
            'proof', 'blocked_approval', 'provider_review_required'
        );
        RAISE EXCEPTION 'AI B-roll proof constraint unexpectedly passed';
    EXCEPTION WHEN check_violation THEN
        NULL;
    END;

    BEGIN
        UPDATE artifact_attempt
           SET state = 'failed'
         WHERE artifact_attempt_id = (
             SELECT artifact_attempt_id
             FROM artifact_attempt
             WHERE run_id = (SELECT run_id FROM research_run WHERE run_key = 'smoke-content-engine-v3')
               AND content_id = (SELECT content_id FROM content_item WHERE native_content_id = 'smoke-content-engine-v3-video')
               AND stage = 'transcript'
               AND attempt_number = 1
         );
        RAISE EXCEPTION 'append-only artifact attempt update unexpectedly passed';
    EXCEPTION WHEN raise_exception THEN
        NULL;
    END;
END;
$$;

SELECT script_key, shot_count, creator_shots, ai_broll_shots
FROM v_script_production_readiness
WHERE script_package_id = :script_package_id;

ROLLBACK;
