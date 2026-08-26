BEGIN;

ALTER TABLE north_hux.source_registry
    DROP CONSTRAINT IF EXISTS source_registry_platform_native_id_key;

ALTER TABLE north_hux.source_registry
    ADD CONSTRAINT source_registry_platform_source_type_native_id_key
    UNIQUE (platform, source_type, native_id);

COMMIT;
