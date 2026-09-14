-- Workers can lease registered local bundles; no direct evidence/table writes.
BEGIN;
DO $$ BEGIN
 IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='m2_worker') THEN
 CREATE ROLE m2_worker NOLOGIN NOINHERIT;
 END IF;
END $$;
CREATE TABLE m2_shared.execution_bundles (
 sha256 text PRIMARY KEY CHECK(sha256 ~ '^[0-9a-f]{64}$'),
 release_id text NOT NULL REFERENCES m2_shared.releases(id),
 stage text NOT NULL CHECK(stage IN ('asr','frames','render_fixture')),
 manifest jsonb NOT NULL, manifest_canonical text NOT NULL,
 code_sha256 text NOT NULL CHECK(code_sha256 ~ '^[0-9a-f]{64}$'),
 config_sha256 text NOT NULL CHECK(config_sha256 ~ '^[0-9a-f]{64}$'),
 policy_sha256 text NOT NULL CHECK(policy_sha256 ~ '^[0-9a-f]{64}$'),
 CHECK(manifest=manifest_canonical::jsonb),
 CHECK(manifest ?& ARRAY['stage','release_id','code_sha256','config_sha256','policy_sha256','source_manifest_sha256']),
 CHECK(manifest->>'stage'=stage AND manifest->>'release_id'=release_id),
 CHECK(manifest->>'code_sha256'=code_sha256 AND manifest->>'config_sha256'=config_sha256 AND manifest->>'policy_sha256'=policy_sha256),
 CHECK(sha256=encode(sha256(convert_to(manifest_canonical,'UTF8')),'hex'))
);
ALTER TABLE m2_shared.execution_bundles ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON m2_shared.execution_bundles FROM PUBLIC;
CREATE TRIGGER immutable_evidence BEFORE UPDATE OR DELETE ON m2_shared.execution_bundles FOR EACH ROW EXECUTE FUNCTION m2_shared.reject_mutation();
CREATE TABLE m2_shared.worker_outputs (
 job_id text NOT NULL REFERENCES m2_shared.jobs(id), attempt integer NOT NULL CHECK(attempt BETWEEN 1 AND 3),
 bundle_sha256 text NOT NULL REFERENCES m2_shared.execution_bundles(sha256),
 worker_id text NOT NULL, output_sha256 text NOT NULL CHECK(output_sha256 ~ '^[0-9a-f]{64}$'),
 receipt_canonical text NOT NULL, receipt_sha256 text NOT NULL CHECK(receipt_sha256 ~ '^[0-9a-f]{64}$'),
 registered_at timestamptz NOT NULL DEFAULT clock_timestamp(), PRIMARY KEY(job_id,attempt),
 CHECK(receipt_sha256=encode(sha256(convert_to(receipt_canonical,'UTF8')),'hex'))
);
ALTER TABLE m2_shared.worker_outputs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON m2_shared.worker_outputs FROM PUBLIC;
CREATE TRIGGER immutable_evidence BEFORE UPDATE OR DELETE ON m2_shared.worker_outputs FOR EACH ROW EXECUTE FUNCTION m2_shared.reject_mutation();
CREATE FUNCTION m2_shared.assert_worker() RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 IF NOT pg_has_role(session_user,'m2_worker','MEMBER') THEN RAISE EXCEPTION 'worker authorization required'; END IF;
END $$;
CREATE FUNCTION m2_shared.worker_bundle(p_hash text) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE result jsonb; BEGIN
 PERFORM m2_shared.assert_worker();
 SELECT b.manifest INTO result FROM m2_shared.execution_bundles b
 JOIN m2_shared.jobs j ON j.input_sha256=b.sha256
 WHERE b.sha256=p_hash AND j.worker_id=session_user AND j.status='running' AND j.lease_until>clock_timestamp();
 RETURN result;
END $$;
CREATE FUNCTION m2_shared.worker_claim_job(p_worker text,p_seconds integer DEFAULT 300)
RETURNS SETOF m2_shared.jobs LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 PERFORM m2_shared.assert_worker();
 IF p_worker<>session_user OR p_seconds NOT BETWEEN 30 AND 3600 THEN RAISE EXCEPTION 'invalid worker lease'; END IF;
 RETURN QUERY WITH candidate AS (
 SELECT j.id FROM m2_shared.jobs j JOIN m2_shared.execution_bundles b ON j.input_sha256=b.sha256
 WHERE j.status='pending' AND j.attempt<3 AND j.stage=b.stage
 AND j.payload->>'execution_bundle_sha256'=b.sha256 AND j.payload->>'release_id'=b.release_id
 ORDER BY j.id FOR UPDATE OF j SKIP LOCKED LIMIT 1
 ) UPDATE m2_shared.jobs j SET status='running',attempt=attempt+1,worker_id=session_user,
 lease_token=gen_random_uuid(),lease_until=clock_timestamp()+make_interval(secs=>p_seconds),heartbeat_at=clock_timestamp()
 FROM candidate c WHERE j.id=c.id RETURNING j.*;
END $$;
CREATE FUNCTION m2_shared.worker_heartbeat_job(p_id text,p_token uuid,p_seconds integer DEFAULT 300)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 PERFORM m2_shared.assert_worker();
 IF NOT EXISTS(SELECT FROM m2_shared.jobs WHERE id=p_id AND worker_id=session_user) THEN RETURN false; END IF;
 RETURN m2_shared.heartbeat_job(p_id,p_token,p_seconds);
END $$;
CREATE FUNCTION m2_shared.worker_finish_job(p_id text,p_token uuid,p_status text,p_output text,p_error text DEFAULT NULL)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
BEGIN
 PERFORM m2_shared.assert_worker();
 IF p_error IS NOT NULL AND p_error !~ '^[A-Z0-9_]{1,80}$' THEN RAISE EXCEPTION 'invalid error code'; END IF;
 IF NOT EXISTS(SELECT FROM m2_shared.jobs WHERE id=p_id AND worker_id=session_user) THEN RETURN false; END IF;
 IF p_status='done' AND NOT EXISTS(
 SELECT FROM m2_shared.worker_outputs o JOIN m2_shared.jobs j ON j.id=o.job_id AND j.attempt=o.attempt
 WHERE j.id=p_id AND o.output_sha256=p_output AND o.worker_id=session_user AND o.bundle_sha256=j.input_sha256
 ) THEN RETURN false; END IF;
 IF NOT m2_shared.finish_job(p_id,p_token,p_status,p_output) THEN RETURN false; END IF;
 UPDATE m2_shared.jobs SET error_code=p_error WHERE id=p_id;
 RETURN true;
END $$;
CREATE FUNCTION m2_shared.worker_register_output(p_id text,p_token uuid,p_receipt text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE j m2_shared.jobs; r jsonb; expected_kind text; saved text;
BEGIN
 PERFORM m2_shared.assert_worker();
 SELECT * INTO j FROM m2_shared.jobs WHERE id=p_id AND worker_id=session_user
 AND lease_token=p_token AND status='running' AND lease_until>clock_timestamp() FOR UPDATE;
 IF NOT FOUND THEN RETURN false; END IF;
 IF octet_length(p_receipt)>16384 THEN RAISE EXCEPTION 'invalid output receipt'; END IF;
 r:=p_receipt::jsonb;
 expected_kind:=CASE j.stage WHEN 'asr' THEN 'asr_json' WHEN 'frames' THEN 'frame_image' WHEN 'render_fixture' THEN 'fixture_bytes' END;
 IF jsonb_typeof(r)<>'object' OR (SELECT count(*) FROM jsonb_object_keys(r))<>6
 OR NOT r ?& ARRAY['job_id','attempt','output_sha256','byte_size','kind','private_path']
 OR jsonb_typeof(r->'attempt')<>'number' OR jsonb_typeof(r->'byte_size')<>'number'
 OR r->>'job_id' IS DISTINCT FROM j.id OR r->>'attempt' IS DISTINCT FROM j.attempt::text
 OR r->>'kind' IS DISTINCT FROM expected_kind OR coalesce(r->>'output_sha256','') !~ '^[0-9a-f]{64}$'
 OR coalesce(r->>'byte_size','') !~ '^[1-9][0-9]{0,17}$'
 OR jsonb_typeof(r->'private_path')<>'string' OR length(r->>'private_path') NOT BETWEEN 1 AND 2048
 OR r->>'private_path' ~ '(^/|(^|/)\.\.(/|$)|[[:cntrl:]]|\\)'
 THEN RAISE EXCEPTION 'invalid output receipt'; END IF;
 INSERT INTO m2_shared.worker_outputs(job_id,attempt,bundle_sha256,worker_id,output_sha256,receipt_canonical,receipt_sha256)
 VALUES(j.id,j.attempt,j.input_sha256,session_user,r->>'output_sha256',p_receipt,encode(sha256(convert_to(p_receipt,'UTF8')),'hex'))
 ON CONFLICT DO NOTHING;
 SELECT receipt_canonical INTO saved FROM m2_shared.worker_outputs WHERE job_id=j.id AND attempt=j.attempt;
 IF saved IS DISTINCT FROM p_receipt THEN RAISE EXCEPTION 'immutable output conflict'; END IF;
 RETURN true;
END $$;
CREATE FUNCTION m2_shared.worker_recover_job(p_id text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE result text; BEGIN
 PERFORM m2_shared.assert_worker();
 IF NOT EXISTS(SELECT FROM m2_shared.jobs WHERE id=p_id AND worker_id=session_user) THEN RETURN NULL; END IF;
 IF NOT m2_shared.recover_job(p_id) THEN RETURN NULL; END IF;
 SELECT status INTO result FROM m2_shared.jobs WHERE id=p_id;
 RETURN result;
END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA m2_shared FROM PUBLIC;
GRANT USAGE ON SCHEMA m2_shared TO m2_worker;
GRANT EXECUTE ON FUNCTION m2_shared.worker_bundle(text),m2_shared.worker_claim_job(text,integer),
 m2_shared.worker_heartbeat_job(text,uuid,integer),m2_shared.worker_finish_job(text,uuid,text,text,text),
 m2_shared.worker_recover_job(text),m2_shared.worker_register_output(text,uuid,text) TO m2_worker;
COMMIT;
