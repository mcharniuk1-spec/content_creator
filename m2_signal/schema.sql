PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS releases (
 release_id TEXT PRIMARY KEY, corpus_sha256 TEXT NOT NULL, config_sha256 TEXT NOT NULL,
 implementation_sha256 TEXT NOT NULL, snapshot_date TEXT NOT NULL,
 config_json TEXT NOT NULL CHECK(json_valid(config_json)), manifest_json TEXT NOT NULL CHECK(json_valid(manifest_json))
);
CREATE TABLE IF NOT EXISTS sources (
 sha256 TEXT PRIMARY KEY, logical_name TEXT NOT NULL, size_bytes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS release_sources (
 release_id TEXT NOT NULL REFERENCES releases(release_id), logical_name TEXT NOT NULL,
 source_sha256 TEXT NOT NULL REFERENCES sources(sha256), PRIMARY KEY(release_id,logical_name)
);
CREATE TABLE IF NOT EXISTS observations (
 observation_id TEXT PRIMARY KEY, snapshot_date TEXT NOT NULL, kind TEXT NOT NULL,
 entity_key TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
 payload_json TEXT NOT NULL CHECK(json_valid(payload_json))
);
CREATE TABLE IF NOT EXISTS release_observations (
 release_id TEXT NOT NULL REFERENCES releases(release_id), kind TEXT NOT NULL,
 source_sha256 TEXT NOT NULL REFERENCES sources(sha256), source_row INTEGER NOT NULL,
 observation_id TEXT NOT NULL REFERENCES observations(observation_id),
 PRIMARY KEY(release_id,kind,source_row)
);
CREATE TABLE IF NOT EXISTS reel_analysis (
 release_id TEXT NOT NULL REFERENCES releases(release_id), reel_id TEXT NOT NULL,
 account_username TEXT, eligibility_state TEXT NOT NULL CHECK(eligibility_state IN ('PASS','FAIL','UNKNOWN','NOT_APPLICABLE')),
 payload_json TEXT NOT NULL CHECK(json_valid(payload_json)), PRIMARY KEY(release_id,reel_id)
);
CREATE TABLE IF NOT EXISTS account_analysis (
 release_id TEXT NOT NULL REFERENCES releases(release_id), account_username TEXT NOT NULL,
 payload_json TEXT NOT NULL CHECK(json_valid(payload_json)), PRIMARY KEY(release_id,account_username)
);
CREATE TABLE IF NOT EXISTS evidence_attempts (
 release_id TEXT NOT NULL REFERENCES releases(release_id), reel_id TEXT NOT NULL,
 modality TEXT NOT NULL, observation_state TEXT NOT NULL,
 payload_json TEXT NOT NULL CHECK(json_valid(payload_json)), PRIMARY KEY(release_id,reel_id,modality)
);
CREATE INDEX IF NOT EXISTS observations_by_entity ON observations(kind,entity_key,snapshot_date);
CREATE INDEX IF NOT EXISTS release_members ON release_observations(release_id,kind);
CREATE TABLE IF NOT EXISTS metric_observations (
 observation_id TEXT NOT NULL REFERENCES observations(observation_id),
 metric_name TEXT NOT NULL, native_field_name TEXT NOT NULL,
 value_integer INTEGER, observation_state TEXT NOT NULL,
 reason_code TEXT, unit TEXT NOT NULL DEFAULT 'count',
 semantics_state TEXT NOT NULL DEFAULT 'LEGACY_EXPORT_UNVERSIONED',
 PRIMARY KEY(observation_id,metric_name)
);
CREATE TABLE IF NOT EXISTS reel_metric_values (
 release_id TEXT NOT NULL, reel_id TEXT NOT NULL, metric_name TEXT NOT NULL,
 value REAL, observed_n INTEGER, denominator REAL, unit TEXT NOT NULL,
 formula_version TEXT NOT NULL,
 PRIMARY KEY(release_id,reel_id,metric_name),
 FOREIGN KEY(release_id,reel_id) REFERENCES reel_analysis(release_id,reel_id)
);
CREATE INDEX IF NOT EXISTS reel_metric_by_release_name ON reel_metric_values(release_id,metric_name);
