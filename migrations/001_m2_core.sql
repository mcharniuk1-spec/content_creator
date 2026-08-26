-- Future PostgreSQL mapping for the file-backed M2 contracts. Not executed here.
BEGIN;

CREATE TABLE IF NOT EXISTS m2_source_record (
    reference_id text PRIMARY KEY,
    entity_type text NOT NULL CHECK (entity_type IN ('creator_reference', 'post_reference')),
    platform text NOT NULL,
    exact_url text NOT NULL UNIQUE,
    canonical_url text NOT NULL UNIQUE,
    parent_creator_reference_id text REFERENCES m2_source_record(reference_id),
    source_state text NOT NULL,
    rights_state text NOT NULL,
    raw_hash text NOT NULL CHECK (raw_hash ~ '^sha256:[0-9a-f]{64}$'),
    payload jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS m2_url_alias (
    reference_id text NOT NULL REFERENCES m2_source_record(reference_id),
    exact_url text NOT NULL,
    canonical_url text NOT NULL,
    resolution_state text NOT NULL,
    PRIMARY KEY (reference_id, exact_url)
);

CREATE TABLE IF NOT EXISTS m2_metric_snapshot (
    snapshot_id text PRIMARY KEY,
    post_id text NOT NULL REFERENCES m2_source_record(reference_id),
    collected_at timestamptz NOT NULL,
    provider text NOT NULL,
    metric_semantics_version text NOT NULL,
    raw_hash text NOT NULL CHECK (raw_hash ~ '^sha256:[0-9a-f]{64}$'),
    immutable_hash text NOT NULL UNIQUE CHECK (immutable_hash ~ '^sha256:[0-9a-f]{64}$'),
    metrics jsonb NOT NULL,
    UNIQUE (post_id, collected_at, metric_semantics_version)
);

CREATE TABLE IF NOT EXISTS m2_failure_receipt (
    failure_id text PRIMARY KEY,
    stage text NOT NULL,
    code text NOT NULL,
    record_id text,
    recoverable boolean NOT NULL,
    payload jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS m2_daily_route_collection (
    collection_id text PRIMARY KEY,
    provider_mode text NOT NULL CHECK (provider_mode = 'disabled'),
    selected_route_id text NOT NULL,
    payload jsonb NOT NULL,
    content_hash text NOT NULL UNIQUE
);

COMMIT;
