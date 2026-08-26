-- North Hux / ArchFlow market-intelligence schema.
-- Design-only until PostgreSQL is explicitly provisioned and this migration is applied.
-- No secrets, credentials, media bytes, or private identifiers belong in this file.

BEGIN;

CREATE SCHEMA IF NOT EXISTS north_hux;
SET search_path = north_hux, public;

CREATE TABLE IF NOT EXISTS research_run (
    run_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_key text NOT NULL UNIQUE,
    status text NOT NULL CHECK (status IN ('planned','calibration','pilot','validation','scale','frozen','blocked','closed')),
    scope_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    admission_receipt_uri text,
    taxonomy_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    ended_at timestamptz,
    owner_gate text NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS adapter (
    adapter_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    platform text NOT NULL CHECK (platform IN ('instagram','tiktok','youtube','web','rss')),
    adapter_name text NOT NULL,
    adapter_version text NOT NULL,
    route_kind text NOT NULL,
    approval_state text NOT NULL CHECK (approval_state IN ('disabled','pending','approved','expired','blocked')),
    terms_uri text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (platform, adapter_name, adapter_version)
);

CREATE TABLE IF NOT EXISTS collection_job (
    job_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES research_run(run_id),
    adapter_id bigint REFERENCES adapter(adapter_id),
    platform text NOT NULL,
    job_type text NOT NULL CHECK (job_type IN ('discovery','account','content','metrics','comments','transcript','media','frames','export')),
    target_stratum text,
    status text NOT NULL CHECK (status IN ('queued','running','succeeded','partial','failed','quarantined','blocked')),
    strike_count integer NOT NULL DEFAULT 0 CHECK (strike_count BETWEEN 0 AND 5),
    cursor_state jsonb NOT NULL DEFAULT '{}'::jsonb,
    started_at timestamptz,
    ended_at timestamptz,
    failure_code text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS source_registry (
    source_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES research_run(run_id),
    platform text NOT NULL,
    source_type text NOT NULL CHECK (source_type IN ('account','content','comment','official_doc','trend_surface','owned_analytics','seed','rejection')),
    native_id text,
    canonical_url text,
    source_role text NOT NULL CHECK (source_role IN ('direct','adjacent','format_leader','technical_authority','counterexample','noise','owned','official_context')),
    discovery_route text,
    rights_state text NOT NULL CHECK (rights_state IN ('pending','metadata_only','commentary_allowed','local_media_allowed','public_projection_allowed','blocked')),
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz,
    UNIQUE (platform, native_id),
    UNIQUE (canonical_url)
);

CREATE TABLE IF NOT EXISTS raw_object (
    raw_object_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES research_run(run_id),
    job_id bigint REFERENCES collection_job(job_id),
    source_id bigint REFERENCES source_registry(source_id),
    platform text NOT NULL,
    native_object_type text NOT NULL,
    native_object_id text,
    payload_uri text,
    payload_json jsonb,
    sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    captured_at timestamptz NOT NULL,
    retention_class text NOT NULL CHECK (retention_class IN ('metadata','restricted','rights_review','deletion_pending','expired')),
    redaction_state text NOT NULL DEFAULT 'unreviewed' CHECK (redaction_state IN ('unreviewed','redacted','approved','blocked')),
    UNIQUE (platform, native_object_type, native_object_id, captured_at)
);

CREATE TABLE IF NOT EXISTS creator_entity (
    creator_entity_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_key text NOT NULL UNIQUE,
    entity_kind text NOT NULL CHECK (entity_kind IN ('solo_creator','creator_group','company','publisher','authority','unknown')),
    display_name text,
    merge_confidence numeric(5,4) CHECK (merge_confidence BETWEEN 0 AND 1),
    merge_rationale text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS platform_account (
    account_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    creator_entity_id bigint REFERENCES creator_entity(creator_entity_id),
    source_id bigint REFERENCES source_registry(source_id),
    platform text NOT NULL CHECK (platform IN ('instagram','tiktok','youtube')),
    native_account_id text NOT NULL,
    handle text,
    canonical_url text NOT NULL,
    account_type text,
    primary_archetype text CHECK (primary_archetype IN ('product_company_operator','agent_builder_operator','mixed','unknown')),
    language_code text,
    region_code text,
    region_evidence_state text NOT NULL DEFAULT 'unknown' CHECK (region_evidence_state IN ('self_declared','official','owned','inferred','unknown')),
    size_band text,
    relevance_class text CHECK (relevance_class IN ('direct','adjacent_topic','format_leader','technical_authority','counterexample','noise','unknown')),
    qualification_state text NOT NULL DEFAULT 'candidate' CHECK (qualification_state IN ('candidate','qualified','rejected','needs_review','blocked')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (platform, native_account_id),
    UNIQUE (platform, canonical_url)
);

CREATE TABLE IF NOT EXISTS account_alias (
    account_alias_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id bigint NOT NULL REFERENCES platform_account(account_id),
    alias_type text NOT NULL CHECK (alias_type IN ('handle','url','canonical_link','declared_cross_platform','candidate_cross_platform')),
    alias_value text NOT NULL,
    evidence_id bigint,
    confidence numeric(5,4) CHECK (confidence BETWEEN 0 AND 1),
    UNIQUE (account_id, alias_type, alias_value)
);

CREATE TABLE IF NOT EXISTS account_snapshot (
    account_snapshot_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id bigint NOT NULL REFERENCES platform_account(account_id),
    raw_object_id bigint REFERENCES raw_object(raw_object_id),
    observed_at timestamptz NOT NULL,
    collected_at timestamptz NOT NULL DEFAULT now(),
    follower_count bigint CHECK (follower_count IS NULL OR follower_count >= 0),
    following_count bigint CHECK (following_count IS NULL OR following_count >= 0),
    content_count bigint CHECK (content_count IS NULL OR content_count >= 0),
    bio_text text,
    public_fields_state text NOT NULL DEFAULT 'observed',
    UNIQUE (account_id, observed_at, raw_object_id)
);

CREATE TABLE IF NOT EXISTS content_item (
    content_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id bigint NOT NULL REFERENCES platform_account(account_id),
    source_id bigint REFERENCES source_registry(source_id),
    platform text NOT NULL CHECK (platform IN ('instagram','tiktok','youtube')),
    native_content_id text NOT NULL,
    canonical_url text NOT NULL,
    content_kind text NOT NULL CHECK (content_kind IN ('reel','tiktok_video','short','unknown')),
    format_evidence_state text NOT NULL DEFAULT 'platform_declared' CHECK (format_evidence_state IN ('platform_declared','inferred','unknown')),
    title text,
    caption text,
    hashtags jsonb NOT NULL DEFAULT '[]'::jsonb,
    mentions jsonb NOT NULL DEFAULT '[]'::jsonb,
    publish_at timestamptz,
    duration_ms integer CHECK (duration_ms IS NULL OR duration_ms >= 0),
    aspect_ratio numeric(8,4),
    language_code text,
    media_sha256 text CHECK (media_sha256 IS NULL OR media_sha256 ~ '^[0-9a-f]{64}$'),
    rights_state text NOT NULL DEFAULT 'pending',
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (platform, native_content_id),
    UNIQUE (platform, canonical_url)
);

CREATE TABLE IF NOT EXISTS content_relationship (
    content_relationship_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    parent_content_id bigint NOT NULL REFERENCES content_item(content_id),
    child_content_id bigint NOT NULL REFERENCES content_item(content_id),
    relationship_type text NOT NULL CHECK (relationship_type IN ('repost','remix','duet','stitch','reply','clip','translation','cross_post','mirror')),
    confidence numeric(5,4) CHECK (confidence BETWEEN 0 AND 1),
    evidence_id bigint,
    UNIQUE (parent_content_id, child_content_id, relationship_type)
);

CREATE TABLE IF NOT EXISTS metric_definition (
    metric_definition_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    platform text NOT NULL,
    native_name text NOT NULL,
    canonical_name text NOT NULL,
    visibility_class text NOT NULL CHECK (visibility_class IN ('public','owned','research_only','estimated')),
    metric_definition_version text NOT NULL,
    unit text NOT NULL,
    denominator text,
    valid_from date,
    valid_to date,
    notes text,
    UNIQUE (platform, native_name, metric_definition_version)
);

CREATE TABLE IF NOT EXISTS metric_snapshot (
    metric_snapshot_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content_id bigint REFERENCES content_item(content_id),
    account_id bigint REFERENCES platform_account(account_id),
    metric_definition_id bigint NOT NULL REFERENCES metric_definition(metric_definition_id),
    raw_object_id bigint REFERENCES raw_object(raw_object_id),
    observed_at timestamptz NOT NULL,
    collected_at timestamptz NOT NULL DEFAULT now(),
    metric_value numeric,
    availability_state text NOT NULL CHECK (availability_state IN ('observed','not_exposed','not_requested','suppressed','error','inapplicable')),
    is_estimated boolean NOT NULL DEFAULT false,
    supersedes_metric_snapshot_id bigint REFERENCES metric_snapshot(metric_snapshot_id),
    CHECK ((content_id IS NOT NULL) <> (account_id IS NOT NULL)),
    CHECK (availability_state <> 'observed' OR metric_value IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS interaction_coverage (
    interaction_coverage_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content_id bigint NOT NULL REFERENCES content_item(content_id),
    interaction_type text NOT NULL CHECK (interaction_type IN ('comment','reply','like','share','repost','send','save','favorite')),
    observed_at timestamptz NOT NULL,
    reported_count bigint CHECK (reported_count IS NULL OR reported_count >= 0),
    retrieved_count bigint NOT NULL DEFAULT 0 CHECK (retrieved_count >= 0),
    pagination_complete boolean NOT NULL DEFAULT false,
    sampling_method text,
    endpoint_limit text,
    gap_reason text,
    raw_object_id bigint REFERENCES raw_object(raw_object_id)
);

CREATE TABLE IF NOT EXISTS comment (
    comment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content_id bigint NOT NULL REFERENCES content_item(content_id),
    native_comment_id text NOT NULL,
    parent_comment_id bigint REFERENCES comment(comment_id),
    native_parent_comment_id text,
    text_body text,
    author_pseudonym text,
    created_at timestamptz,
    like_count bigint CHECK (like_count IS NULL OR like_count >= 0),
    reply_count bigint CHECK (reply_count IS NULL OR reply_count >= 0),
    is_pinned boolean,
    is_deleted boolean NOT NULL DEFAULT false,
    raw_object_id bigint REFERENCES raw_object(raw_object_id),
    UNIQUE (content_id, native_comment_id)
);

CREATE TABLE IF NOT EXISTS interaction_event (
    interaction_event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content_id bigint NOT NULL REFERENCES content_item(content_id),
    native_event_id text,
    event_type text NOT NULL CHECK (event_type IN ('comment','reply','like','share','repost','send','save','favorite','follow')),
    actor_pseudonym text,
    observed_at timestamptz,
    raw_object_id bigint REFERENCES raw_object(raw_object_id),
    event_state text NOT NULL DEFAULT 'observed' CHECK (event_state IN ('observed','redacted','deleted','unavailable')),
    UNIQUE (content_id, native_event_id, event_type)
);

CREATE TABLE IF NOT EXISTS transcript (
    transcript_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content_id bigint NOT NULL REFERENCES content_item(content_id),
    source_kind text NOT NULL CHECK (source_kind IN ('post_caption','native_caption','native_subtitle','provider_transcript','local_asr','ocr')),
    language_code text,
    model_name text,
    model_version text,
    quality_state text NOT NULL CHECK (quality_state IN ('not_run','usable','review','failed','blocked')),
    transcript_uri text,
    transcript_sha256 text CHECK (transcript_sha256 IS NULL OR transcript_sha256 ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS transcript_segment (
    transcript_segment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transcript_id bigint NOT NULL REFERENCES transcript(transcript_id),
    segment_index integer NOT NULL CHECK (segment_index >= 0),
    start_ms integer NOT NULL CHECK (start_ms >= 0),
    end_ms integer NOT NULL CHECK (end_ms >= start_ms),
    text_body text NOT NULL,
    confidence numeric(5,4) CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    evidence_state text NOT NULL DEFAULT 'observed',
    UNIQUE (transcript_id, segment_index)
);

CREATE TABLE IF NOT EXISTS media_asset (
    media_asset_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content_id bigint NOT NULL REFERENCES content_item(content_id),
    asset_kind text NOT NULL CHECK (asset_kind IN ('video','audio','thumbnail','preview','contact_sheet')),
    asset_uri text NOT NULL,
    sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    byte_size bigint CHECK (byte_size IS NULL OR byte_size >= 0),
    duration_ms integer CHECK (duration_ms IS NULL OR duration_ms >= 0),
    width integer CHECK (width IS NULL OR width > 0),
    height integer CHECK (height IS NULL OR height > 0),
    rights_state text NOT NULL,
    retention_until timestamptz,
    UNIQUE (content_id, asset_kind, sha256)
);

CREATE TABLE IF NOT EXISTS frame_artifact (
    frame_artifact_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    media_asset_id bigint NOT NULL REFERENCES media_asset(media_asset_id),
    frame_index integer NOT NULL CHECK (frame_index >= 0),
    timestamp_ms integer NOT NULL CHECK (timestamp_ms >= 0),
    frame_uri text NOT NULL,
    sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    ocr_text text,
    public_display_allowed boolean NOT NULL DEFAULT false,
    UNIQUE (media_asset_id, frame_index)
);

CREATE TABLE IF NOT EXISTS visual_event (
    visual_event_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content_id bigint NOT NULL REFERENCES content_item(content_id),
    frame_artifact_id bigint REFERENCES frame_artifact(frame_artifact_id),
    start_ms integer NOT NULL CHECK (start_ms >= 0),
    end_ms integer CHECK (end_ms IS NULL OR end_ms >= start_ms),
    event_type text NOT NULL,
    value_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    epistemic_state text NOT NULL CHECK (epistemic_state IN ('observed','derived','classified','inferred','hypothesized','gap')),
    reviewer_state text NOT NULL DEFAULT 'unreviewed'
);

CREATE TABLE IF NOT EXISTS taxonomy_version (
    taxonomy_version_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    taxonomy_key text NOT NULL,
    version text NOT NULL,
    definition_json jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (taxonomy_key, version)
);

CREATE TABLE IF NOT EXISTS classification (
    classification_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    taxonomy_version_id bigint NOT NULL REFERENCES taxonomy_version(taxonomy_version_id),
    account_id bigint REFERENCES platform_account(account_id),
    content_id bigint REFERENCES content_item(content_id),
    comment_id bigint REFERENCES comment(comment_id),
    dimension text NOT NULL,
    label text NOT NULL,
    epistemic_state text NOT NULL CHECK (epistemic_state IN ('observed','derived','classified','inferred','hypothesized','gap')),
    method text NOT NULL,
    confidence numeric(5,4) CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    evidence_locator text,
    CHECK (num_nonnulls(account_id, content_id, comment_id) = 1)
);

CREATE TABLE IF NOT EXISTS evidence_record (
    evidence_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES research_run(run_id),
    source_id bigint REFERENCES source_registry(source_id),
    raw_object_id bigint REFERENCES raw_object(raw_object_id),
    transcript_segment_id bigint REFERENCES transcript_segment(transcript_segment_id),
    frame_artifact_id bigint REFERENCES frame_artifact(frame_artifact_id),
    evidence_class text NOT NULL CHECK (evidence_class IN ('first_party','official_public','public_observation','derived','reviewer','hypothesis','gap')),
    locator text,
    statement text NOT NULL,
    confidence numeric(5,4) CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (num_nonnulls(source_id, raw_object_id, transcript_segment_id, frame_artifact_id) >= 1)
);

CREATE TABLE IF NOT EXISTS rights_decision (
    rights_decision_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES research_run(run_id),
    source_id bigint REFERENCES source_registry(source_id),
    content_id bigint REFERENCES content_item(content_id),
    allowed_use text NOT NULL CHECK (allowed_use IN ('metadata_only','commentary','transcript','local_media','frame_reference','public_projection','blocked')),
    decision text NOT NULL CHECK (decision IN ('pending','pass','block','expired')),
    basis text NOT NULL,
    reviewer text NOT NULL,
    decided_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz
);

CREATE TABLE IF NOT EXISTS review_task (
    review_task_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES research_run(run_id),
    platform text,
    object_type text NOT NULL,
    object_id bigint,
    review_type text NOT NULL CHECK (review_type IN ('relevance','taxonomy','transcript','frame','stats','rights','projection','independent')),
    assigned_reviewer text NOT NULL,
    status text NOT NULL CHECK (status IN ('queued','in_progress','passed','passed_with_limitations','failed','blocked')),
    question_set_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz
);

CREATE TABLE IF NOT EXISTS review_decision (
    review_decision_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    review_task_id bigint NOT NULL REFERENCES review_task(review_task_id),
    criterion text NOT NULL,
    decision text NOT NULL CHECK (decision IN ('pass','fail','uncertain','not_applicable')),
    rationale text NOT NULL,
    evidence_id bigint REFERENCES evidence_record(evidence_id),
    reviewer text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analysis_progress (
    progress_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES research_run(run_id),
    platform text NOT NULL CHECK (platform IN ('instagram','tiktok','youtube','all')),
    category text NOT NULL CHECK (category IN ('accounts','posts','stats','captions','comments','transcripts','video','frames','taxonomy','review','notion_projection','obsidian_projection')),
    target_count bigint NOT NULL DEFAULT 0 CHECK (target_count >= 0),
    eligible_count bigint NOT NULL DEFAULT 0 CHECK (eligible_count >= 0),
    admitted_count bigint NOT NULL DEFAULT 0 CHECK (admitted_count >= 0),
    completed_count bigint NOT NULL DEFAULT 0 CHECK (completed_count >= 0),
    reviewed_count bigint NOT NULL DEFAULT 0 CHECK (reviewed_count >= 0),
    failed_count bigint NOT NULL DEFAULT 0 CHECK (failed_count >= 0),
    blocked_count bigint NOT NULL DEFAULT 0 CHECK (blocked_count >= 0),
    last_updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_id, platform, category)
);

CREATE TABLE IF NOT EXISTS export_artifact (
    export_artifact_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES research_run(run_id),
    export_kind text NOT NULL CHECK (export_kind IN ('csv','parquet','json','markdown','notion','obsidian','canvas','base','dashboard')),
    artifact_uri text NOT NULL,
    sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    public_safe boolean NOT NULL DEFAULT false,
    generated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_id, export_kind, artifact_uri)
);

CREATE INDEX IF NOT EXISTS idx_account_platform_relevance ON platform_account(platform, relevance_class, qualification_state);
CREATE INDEX IF NOT EXISTS idx_content_platform_publish ON content_item(platform, publish_at DESC);
CREATE INDEX IF NOT EXISTS idx_metric_content_observed ON metric_snapshot(content_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_comment_content_created ON comment(content_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_review_queue ON review_task(run_id, status, review_type);
CREATE INDEX IF NOT EXISTS idx_progress_platform_category ON analysis_progress(run_id, platform, category);

CREATE OR REPLACE VIEW v_platform_progress AS
SELECT
    run_id,
    platform,
    category,
    target_count,
    eligible_count,
    admitted_count,
    completed_count,
    reviewed_count,
    failed_count,
    blocked_count,
    CASE WHEN target_count = 0 THEN 0::numeric
         ELSE round((completed_count::numeric / target_count::numeric) * 100, 2)
    END AS completion_percent,
    last_updated_at
FROM analysis_progress;

CREATE OR REPLACE VIEW v_public_safe_account_summary AS
SELECT
    pa.platform,
    pa.handle,
    pa.canonical_url,
    pa.primary_archetype,
    pa.language_code,
    pa.region_code,
    pa.size_band,
    pa.relevance_class,
    pa.qualification_state
FROM platform_account pa
WHERE pa.qualification_state = 'qualified';

COMMIT;
