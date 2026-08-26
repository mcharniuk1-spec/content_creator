BEGIN;
SET search_path = north_hux, public;

DO $$
DECLARE
    candidate_count bigint;
    eligible_count bigint;
BEGIN
    SELECT count(*), count(*) FILTER (WHERE studio_candidate_state = 'eligible')
      INTO candidate_count, eligible_count
      FROM v_social_studio_candidate_v1;

    IF candidate_count <> 64 THEN
        RAISE EXCEPTION 'expected 64 social candidates, observed %', candidate_count;
    END IF;
    IF eligible_count <> 0 THEN
        RAISE EXCEPTION 'expected zero eligible social candidates, observed %', eligible_count;
    END IF;

    INSERT INTO social_studio_contract (
        contract_key, schema_id, contract_version, state, schema_sha256
    ) VALUES (
        'smoke-signal-to-studio-v1.1',
        'signal-to-studio.v1.1',
        999999,
        'pending',
        'sha256:0000000000000000000000000000000000000000000000000000000000000000'
    );

    BEGIN
        UPDATE social_studio_contract
           SET state = 'blocked'
         WHERE contract_key = 'smoke-signal-to-studio-v1.1';
        RAISE EXCEPTION 'append-only contract update unexpectedly succeeded';
    EXCEPTION
        WHEN raise_exception THEN NULL;
    END;

    IF NOT EXISTS (
        SELECT 1 FROM social_studio_contract
         WHERE contract_key = 'smoke-signal-to-studio-v1.1' AND state = 'pending'
    ) THEN
        RAISE EXCEPTION 'append-only contract state was not preserved';
    END IF;
END;
$$;

ROLLBACK;
