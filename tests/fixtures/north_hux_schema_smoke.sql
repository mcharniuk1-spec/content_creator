-- Transactional schema smoke test. Every row is rolled back.
\set ON_ERROR_STOP on
BEGIN;
SET search_path = north_hux, public;

INSERT INTO research_run (run_key, status, scope_json, taxonomy_version)
VALUES ('fixture-schema-smoke', 'calibration', '{"fixture":true}'::jsonb, 'north-hux.taxonomy.v1')
RETURNING run_id \gset

INSERT INTO adapter (platform, adapter_name, adapter_version, route_kind, approval_state)
VALUES ('youtube', 'fixture-adapter', '1.0.0', 'public_metadata', 'disabled')
RETURNING adapter_id \gset

INSERT INTO source_registry (run_id, platform, source_type, native_id, canonical_url, source_role, discovery_route, rights_state)
VALUES (:run_id, 'youtube', 'content', 'fixture-video-1', 'https://www.youtube.com/watch?v=fixture-video-1', 'direct', 'fixture', 'metadata_only')
RETURNING source_id \gset

INSERT INTO collection_job (run_id, adapter_id, platform, job_type, target_stratum, status)
VALUES (:run_id, :adapter_id, 'youtube', 'content', 'fixture', 'succeeded')
RETURNING job_id \gset

INSERT INTO raw_object (run_id, job_id, source_id, platform, native_object_type, native_object_id, payload_uri, payload_json, sha256, captured_at, retention_class, redaction_state)
VALUES (:run_id, :job_id, :source_id, 'youtube', 'video', 'fixture-video-1', 'local://fixture.json', '{"views":42}'::jsonb, 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', now(), 'metadata', 'approved')
RETURNING raw_object_id \gset

INSERT INTO creator_entity (entity_key, entity_kind, display_name)
VALUES ('fixture-company', 'company', 'Fixture Company')
RETURNING creator_entity_id \gset

INSERT INTO platform_account (creator_entity_id, source_id, platform, native_account_id, handle, canonical_url, primary_archetype, language_code, region_code, region_evidence_state, size_band, relevance_class, qualification_state)
VALUES (:creator_entity_id, :source_id, 'youtube', 'fixture-channel-1', 'fixture-channel', 'https://www.youtube.com/@fixture-channel', 'product_company_operator', 'en', 'US', 'self_declared', 'small', 'direct', 'qualified')
RETURNING account_id \gset

INSERT INTO content_item (account_id, source_id, platform, native_content_id, canonical_url, content_kind, title, caption, publish_at, duration_ms, language_code, rights_state)
VALUES (:account_id, :source_id, 'youtube', 'fixture-video-1', 'https://www.youtube.com/watch?v=fixture-video-1', 'short', 'Fixture video', 'Fixture caption', now(), 12000, 'en', 'metadata_only')
RETURNING content_id \gset

INSERT INTO metric_definition (platform, native_name, canonical_name, visibility_class, metric_definition_version, unit, denominator)
VALUES ('youtube', 'view_count', 'views', 'public', 'v1', 'count', 'content_item')
RETURNING metric_definition_id \gset

INSERT INTO metric_snapshot (content_id, metric_definition_id, raw_object_id, observed_at, metric_value, availability_state)
VALUES (:content_id, :metric_definition_id, :raw_object_id, now(), 42, 'observed')
RETURNING metric_snapshot_id \gset

INSERT INTO interaction_coverage (content_id, interaction_type, observed_at, reported_count, retrieved_count, pagination_complete, sampling_method)
VALUES (:content_id, 'comment', now(), 1, 1, true, 'fixture')
RETURNING interaction_coverage_id \gset

INSERT INTO comment (content_id, native_comment_id, text_body, author_pseudonym, created_at, like_count, reply_count)
VALUES (:content_id, 'fixture-comment-1', 'Fixture comment', 'pseudonym-1', now(), 1, 0)
RETURNING comment_id \gset

INSERT INTO transcript (content_id, source_kind, language_code, quality_state, transcript_uri)
VALUES (:content_id, 'native_subtitle', 'en', 'usable', 'local://fixture-transcript.json')
RETURNING transcript_id \gset

INSERT INTO transcript_segment (transcript_id, segment_index, start_ms, end_ms, text_body, confidence)
VALUES (:transcript_id, 0, 0, 12000, 'Fixture transcript segment', 0.99)
RETURNING transcript_segment_id \gset

INSERT INTO media_asset (content_id, asset_kind, asset_uri, sha256, byte_size, duration_ms, width, height, rights_state)
VALUES (:content_id, 'thumbnail', 'local://fixture-thumbnail.jpg', 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 10, 12000, 1080, 1920, 'metadata_only')
RETURNING media_asset_id \gset

INSERT INTO frame_artifact (media_asset_id, frame_index, timestamp_ms, frame_uri, sha256)
VALUES (:media_asset_id, 0, 0, 'local://fixture-frame-000.jpg', 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc')
RETURNING frame_artifact_id \gset

INSERT INTO visual_event (content_id, frame_artifact_id, start_ms, end_ms, event_type, value_json, epistemic_state, reviewer_state)
VALUES (:content_id, :frame_artifact_id, 0, 12000, 'opening_frame', '{"layout":"vertical"}'::jsonb, 'classified', 'passed')
RETURNING visual_event_id \gset

INSERT INTO taxonomy_version (taxonomy_key, version, definition_json)
VALUES ('content_taxonomy', 'v1', '{"labels":["tutorial"]}'::jsonb)
RETURNING taxonomy_version_id \gset

INSERT INTO classification (taxonomy_version_id, content_id, dimension, label, epistemic_state, method, confidence, evidence_locator)
VALUES (:taxonomy_version_id, :content_id, 'content_type', 'tutorial', 'classified', 'fixture', 0.99, 'fixture-frame-000')
RETURNING classification_id \gset

INSERT INTO evidence_record (run_id, source_id, raw_object_id, transcript_segment_id, frame_artifact_id, evidence_class, locator, statement, confidence)
VALUES (:run_id, :source_id, :raw_object_id, :transcript_segment_id, :frame_artifact_id, 'public_observation', 'fixture', 'Fixture evidence chain is complete.', 0.99)
RETURNING evidence_id \gset

INSERT INTO rights_decision (run_id, source_id, content_id, allowed_use, decision, basis, reviewer)
VALUES (:run_id, :source_id, :content_id, 'metadata_only', 'pass', 'Transactional fixture only.', 'fixture')
RETURNING rights_decision_id \gset

INSERT INTO review_task (run_id, platform, object_type, object_id, review_type, assigned_reviewer, status, question_set_version)
VALUES (:run_id, 'youtube', 'content', :content_id, 'stats', 'fixture', 'passed_with_limitations', 'north-hux.review.v1')
RETURNING review_task_id \gset

INSERT INTO review_decision (review_task_id, criterion, decision, rationale, evidence_id, reviewer)
VALUES (:review_task_id, 'metric_semantics', 'pass', 'Fixture metric has a definition and denominator.', :evidence_id, 'fixture');

INSERT INTO analysis_progress (run_id, platform, category, target_count, eligible_count, admitted_count, completed_count, reviewed_count)
VALUES (:run_id, 'youtube', 'stats', 1, 1, 1, 1, 1);

INSERT INTO export_artifact (run_id, export_kind, artifact_uri, sha256, public_safe)
VALUES (:run_id, 'json', 'local://fixture-export.json', 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd', false);

SELECT 'fixture_chain_ok' AS check_name,
       (SELECT metric_value FROM metric_snapshot WHERE metric_snapshot_id = :metric_snapshot_id) AS metric_value,
       (SELECT label FROM classification WHERE classification_id = :classification_id) AS classification_label,
       (SELECT completion_percent FROM v_platform_progress WHERE run_id = :run_id AND platform = 'youtube' AND category = 'stats') AS completion_percent;

ROLLBACK;
