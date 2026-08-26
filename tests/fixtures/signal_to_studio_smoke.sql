\set ON_ERROR_STOP on
BEGIN;
SET search_path = north_hux, public;

INSERT INTO research_run (run_key, status, scope_json, taxonomy_version)
VALUES ('fixture-signal-to-studio', 'validation', '{"fixture":true}'::jsonb, 'studio-shortform@1.0.0')
RETURNING run_id \gset

INSERT INTO studio_signal_export (
    run_id, export_id, export_version, signal_record_id, schema_version,
    payload_json, record_hash, taxonomy_version, rights_state, generated_at,
    public_safe, ingestion_source
) VALUES (
    :run_id,
    'SIGEXP-SF-999',
    1,
    'SIG-SF-999',
    'signal-to-studio.v1',
    '{"schema":"signal-to-studio.v1","external_provider_state":"NOT_RUN","pattern":{},"provenance":{"record_hash":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}}'::jsonb,
    'sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    'studio-shortform@1.0.0',
    'metadata_commentary_only',
    now(),
    false,
    'transactional-fixture'
);

SELECT 'signal_export_visible' AS check_name, count(*) AS record_count
FROM v_signal_to_studio_v1
WHERE export_id = 'SIGEXP-SF-999';

ROLLBACK;

