-- Shared Reels pipeline; independent of frozen historical YouTube migrations.
BEGIN;
CREATE SCHEMA m2_shared;
REVOKE ALL ON SCHEMA m2_shared FROM PUBLIC;
CREATE TABLE m2_shared.sources (
 id text PRIMARY KEY CHECK (id ~ '^[0-9a-f]{64}$'),
 label text NOT NULL, captured_at timestamptz, capture_precision text NOT NULL,
 manifest jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_shared.source_rows (
 source_id text NOT NULL REFERENCES m2_shared.sources(id),
 table_name text NOT NULL, row_key text NOT NULL,
 payload_sha256 text NOT NULL CHECK(payload_sha256 ~ '^[0-9a-f]{64}$'),
 payload jsonb NOT NULL, PRIMARY KEY(source_id,table_name,row_key)
);
CREATE TABLE m2_shared.reels (
 code text PRIMARY KEY CHECK(code ~ '^[A-Za-z0-9_-]+$')
);
CREATE TABLE m2_shared.accounts (
 id text PRIMARY KEY, provider text NOT NULL, provider_identity text NOT NULL,
 UNIQUE(provider,provider_identity)
);
CREATE TABLE m2_shared.reel_account_observations (
 source_id text NOT NULL, table_name text NOT NULL, row_key text NOT NULL,
 code text NOT NULL REFERENCES m2_shared.reels(code), account_id text NOT NULL REFERENCES m2_shared.accounts(id),
 PRIMARY KEY(source_id,table_name,row_key,code,account_id),
 FOREIGN KEY(source_id,table_name,row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key)
);
CREATE TABLE m2_shared.artifacts (
 sha256 text PRIMARY KEY CHECK(sha256 ~ '^[0-9a-f]{64}$'),
 kind text NOT NULL, byte_size bigint CHECK(byte_size>=0),
 private_object_key text, storage_state text NOT NULL CHECK(storage_state IN ('local_only','uploaded','missing','quarantined')),
 metadata jsonb NOT NULL DEFAULT '{}'
);
CREATE TABLE m2_shared.releases (
 id text PRIMARY KEY, manifest_sha256 text NOT NULL,
 status text NOT NULL CHECK(status IN ('draft','candidate','accepted','rejected','superseded')),
 limitations jsonb NOT NULL DEFAULT '[]'
);
CREATE TABLE m2_shared.roster_versions (
 id text PRIMARY KEY, code text REFERENCES m2_shared.reels(code),
 source_id text REFERENCES m2_shared.sources(id),
 artifact_sha256 text REFERENCES m2_shared.artifacts(sha256),
 release_id text REFERENCES m2_shared.releases(id),
 parent_id text, source_table text, source_row_key text,
    payload jsonb NOT NULL,
    FOREIGN KEY(source_id,source_table,source_row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key),
    CHECK(source_id IS NOT NULL OR artifact_sha256 IS NOT NULL),
    CHECK ((source_table IS NULL) = (source_row_key IS NULL)),
    legacy_lineage_gap text, payload_version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_shared.collection_runs (
 id text PRIMARY KEY, code text REFERENCES m2_shared.reels(code),
 source_id text REFERENCES m2_shared.sources(id),
 artifact_sha256 text REFERENCES m2_shared.artifacts(sha256),
 release_id text REFERENCES m2_shared.releases(id),
 parent_id text, source_table text, source_row_key text,
    payload jsonb NOT NULL,
    FOREIGN KEY(source_id,source_table,source_row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key),
    CHECK(source_id IS NOT NULL OR artifact_sha256 IS NOT NULL),
    CHECK ((source_table IS NULL) = (source_row_key IS NULL)),
    legacy_lineage_gap text, payload_version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_shared.metric_observations (
 id text PRIMARY KEY, code text REFERENCES m2_shared.reels(code),
 source_id text REFERENCES m2_shared.sources(id),
 artifact_sha256 text REFERENCES m2_shared.artifacts(sha256),
 release_id text REFERENCES m2_shared.releases(id),
 parent_id text, source_table text, source_row_key text,
    payload jsonb NOT NULL,
    FOREIGN KEY(source_id,source_table,source_row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key),
    CHECK(source_id IS NOT NULL OR artifact_sha256 IS NOT NULL),
    CHECK ((source_table IS NULL) = (source_row_key IS NULL)),
    legacy_lineage_gap text, payload_version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_shared.media (
 id text PRIMARY KEY, code text REFERENCES m2_shared.reels(code),
 source_id text REFERENCES m2_shared.sources(id),
 artifact_sha256 text REFERENCES m2_shared.artifacts(sha256),
 release_id text REFERENCES m2_shared.releases(id),
 parent_id text, source_table text, source_row_key text,
    payload jsonb NOT NULL,
    FOREIGN KEY(source_id,source_table,source_row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key),
    CHECK(source_id IS NOT NULL OR artifact_sha256 IS NOT NULL),
    CHECK ((source_table IS NULL) = (source_row_key IS NULL)),
    legacy_lineage_gap text, payload_version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_shared.attempts (
 id text PRIMARY KEY, code text REFERENCES m2_shared.reels(code),
 source_id text REFERENCES m2_shared.sources(id),
 artifact_sha256 text REFERENCES m2_shared.artifacts(sha256),
 release_id text REFERENCES m2_shared.releases(id),
 parent_id text, source_table text, source_row_key text,
    payload jsonb NOT NULL,
    FOREIGN KEY(source_id,source_table,source_row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key),
    CHECK(source_id IS NOT NULL OR artifact_sha256 IS NOT NULL),
    CHECK ((source_table IS NULL) = (source_row_key IS NULL)),
    legacy_lineage_gap text, payload_version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_shared.transcripts (
 id text PRIMARY KEY, code text REFERENCES m2_shared.reels(code),
 source_id text REFERENCES m2_shared.sources(id),
 artifact_sha256 text REFERENCES m2_shared.artifacts(sha256),
 release_id text REFERENCES m2_shared.releases(id),
 parent_id text, source_table text, source_row_key text,
    payload jsonb NOT NULL,
    FOREIGN KEY(source_id,source_table,source_row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key),
    CHECK(source_id IS NOT NULL OR artifact_sha256 IS NOT NULL),
    CHECK ((source_table IS NULL) = (source_row_key IS NULL)),
    legacy_lineage_gap text, payload_version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_shared.segments (
 id text PRIMARY KEY, code text REFERENCES m2_shared.reels(code),
 source_id text REFERENCES m2_shared.sources(id),
 artifact_sha256 text REFERENCES m2_shared.artifacts(sha256),
 release_id text REFERENCES m2_shared.releases(id),
 parent_id text, source_table text, source_row_key text,
    payload jsonb NOT NULL,
    FOREIGN KEY(source_id,source_table,source_row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key),
    CHECK(source_id IS NOT NULL OR artifact_sha256 IS NOT NULL),
    CHECK ((source_table IS NULL) = (source_row_key IS NULL)),
    legacy_lineage_gap text, payload_version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_shared.language_decisions (
 id text PRIMARY KEY, code text REFERENCES m2_shared.reels(code),
 source_id text REFERENCES m2_shared.sources(id),
 artifact_sha256 text REFERENCES m2_shared.artifacts(sha256),
 release_id text REFERENCES m2_shared.releases(id),
 parent_id text, source_table text, source_row_key text,
    payload jsonb NOT NULL,
    FOREIGN KEY(source_id,source_table,source_row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key),
    CHECK(source_id IS NOT NULL OR artifact_sha256 IS NOT NULL),
    CHECK ((source_table IS NULL) = (source_row_key IS NULL)),
    legacy_lineage_gap text, payload_version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_shared.frames (
 id text PRIMARY KEY, code text REFERENCES m2_shared.reels(code),
 source_id text REFERENCES m2_shared.sources(id),
 artifact_sha256 text REFERENCES m2_shared.artifacts(sha256),
 release_id text REFERENCES m2_shared.releases(id),
 parent_id text, source_table text, source_row_key text,
    payload jsonb NOT NULL,
    FOREIGN KEY(source_id,source_table,source_row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key),
    CHECK(source_id IS NOT NULL OR artifact_sha256 IS NOT NULL),
    CHECK ((source_table IS NULL) = (source_row_key IS NULL)),
    legacy_lineage_gap text, payload_version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_shared.scenes (
 id text PRIMARY KEY, code text REFERENCES m2_shared.reels(code),
 source_id text REFERENCES m2_shared.sources(id),
 artifact_sha256 text REFERENCES m2_shared.artifacts(sha256),
 release_id text REFERENCES m2_shared.releases(id),
 parent_id text, source_table text, source_row_key text,
    payload jsonb NOT NULL,
    FOREIGN KEY(source_id,source_table,source_row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key),
    CHECK(source_id IS NOT NULL OR artifact_sha256 IS NOT NULL),
    CHECK ((source_table IS NULL) = (source_row_key IS NULL)),
    legacy_lineage_gap text, payload_version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_shared.annotations (
 id text PRIMARY KEY, code text REFERENCES m2_shared.reels(code),
 source_id text REFERENCES m2_shared.sources(id),
 artifact_sha256 text REFERENCES m2_shared.artifacts(sha256),
 release_id text REFERENCES m2_shared.releases(id),
 parent_id text, source_table text, source_row_key text,
    payload jsonb NOT NULL,
    FOREIGN KEY(source_id,source_table,source_row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key),
    CHECK(source_id IS NOT NULL OR artifact_sha256 IS NOT NULL),
    CHECK ((source_table IS NULL) = (source_row_key IS NULL)),
    legacy_lineage_gap text, payload_version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_shared.findings (
 id text PRIMARY KEY, code text REFERENCES m2_shared.reels(code),
 source_id text REFERENCES m2_shared.sources(id),
 artifact_sha256 text REFERENCES m2_shared.artifacts(sha256),
 release_id text REFERENCES m2_shared.releases(id),
 parent_id text, source_table text, source_row_key text,
    payload jsonb NOT NULL,
    FOREIGN KEY(source_id,source_table,source_row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key),
    CHECK(source_id IS NOT NULL OR artifact_sha256 IS NOT NULL),
    CHECK ((source_table IS NULL) = (source_row_key IS NULL)),
    legacy_lineage_gap text, payload_version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_shared.references (
 id text PRIMARY KEY, code text REFERENCES m2_shared.reels(code),
 source_id text REFERENCES m2_shared.sources(id),
 artifact_sha256 text REFERENCES m2_shared.artifacts(sha256),
 release_id text REFERENCES m2_shared.releases(id),
 parent_id text, source_table text, source_row_key text,
    payload jsonb NOT NULL,
    FOREIGN KEY(source_id,source_table,source_row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key),
    CHECK(source_id IS NOT NULL OR artifact_sha256 IS NOT NULL),
    CHECK ((source_table IS NULL) = (source_row_key IS NULL)),
    legacy_lineage_gap text, payload_version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_shared.scripts (
 id text PRIMARY KEY, code text REFERENCES m2_shared.reels(code),
 source_id text REFERENCES m2_shared.sources(id),
 artifact_sha256 text REFERENCES m2_shared.artifacts(sha256),
 release_id text REFERENCES m2_shared.releases(id),
 parent_id text, source_table text, source_row_key text,
    payload jsonb NOT NULL,
    FOREIGN KEY(source_id,source_table,source_row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key),
    CHECK(source_id IS NOT NULL OR artifact_sha256 IS NOT NULL),
    CHECK ((source_table IS NULL) = (source_row_key IS NULL)),
    legacy_lineage_gap text, payload_version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_shared.shots (
 id text PRIMARY KEY, code text REFERENCES m2_shared.reels(code),
 source_id text REFERENCES m2_shared.sources(id),
 artifact_sha256 text REFERENCES m2_shared.artifacts(sha256),
 release_id text REFERENCES m2_shared.releases(id),
 parent_id text, source_table text, source_row_key text,
    payload jsonb NOT NULL,
    FOREIGN KEY(source_id,source_table,source_row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key),
    CHECK(source_id IS NOT NULL OR artifact_sha256 IS NOT NULL),
    CHECK ((source_table IS NULL) = (source_row_key IS NULL)),
    legacy_lineage_gap text, payload_version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_shared.generation_jobs (
 id text PRIMARY KEY, code text REFERENCES m2_shared.reels(code),
 source_id text REFERENCES m2_shared.sources(id),
 artifact_sha256 text REFERENCES m2_shared.artifacts(sha256),
 release_id text REFERENCES m2_shared.releases(id),
 parent_id text, source_table text, source_row_key text,
    payload jsonb NOT NULL,
    FOREIGN KEY(source_id,source_table,source_row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key),
    CHECK(source_id IS NOT NULL OR artifact_sha256 IS NOT NULL),
    CHECK ((source_table IS NULL) = (source_row_key IS NULL)),
    legacy_lineage_gap text, payload_version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_shared.renders (
 id text PRIMARY KEY, code text REFERENCES m2_shared.reels(code),
 source_id text REFERENCES m2_shared.sources(id),
 artifact_sha256 text REFERENCES m2_shared.artifacts(sha256),
 release_id text REFERENCES m2_shared.releases(id),
 parent_id text, source_table text, source_row_key text,
    payload jsonb NOT NULL,
    FOREIGN KEY(source_id,source_table,source_row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key),
    CHECK(source_id IS NOT NULL OR artifact_sha256 IS NOT NULL),
    CHECK ((source_table IS NULL) = (source_row_key IS NULL)),
    legacy_lineage_gap text, payload_version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_shared.reviews (
 id text PRIMARY KEY, code text REFERENCES m2_shared.reels(code),
 source_id text REFERENCES m2_shared.sources(id),
 artifact_sha256 text REFERENCES m2_shared.artifacts(sha256),
 release_id text REFERENCES m2_shared.releases(id),
 parent_id text, source_table text, source_row_key text,
    payload jsonb NOT NULL,
    FOREIGN KEY(source_id,source_table,source_row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key),
    CHECK(source_id IS NOT NULL OR artifact_sha256 IS NOT NULL),
    CHECK ((source_table IS NULL) = (source_row_key IS NULL)),
    legacy_lineage_gap text, payload_version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_shared.projection_receipts (
 id text PRIMARY KEY, code text REFERENCES m2_shared.reels(code),
 source_id text REFERENCES m2_shared.sources(id),
 artifact_sha256 text REFERENCES m2_shared.artifacts(sha256),
 release_id text REFERENCES m2_shared.releases(id),
 parent_id text, source_table text, source_row_key text,
    payload jsonb NOT NULL,
    FOREIGN KEY(source_id,source_table,source_row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key),
    CHECK(source_id IS NOT NULL OR artifact_sha256 IS NOT NULL),
    CHECK ((source_table IS NULL) = (source_row_key IS NULL)),
    legacy_lineage_gap text, payload_version integer NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_shared.reel_assessments (
 code text NOT NULL REFERENCES m2_shared.reels(code),
 release_id text NOT NULL REFERENCES m2_shared.releases(id),
 disposition text NOT NULL CHECK(disposition IN ('attempted','missing','excluded','failed','review_needed','accepted')),
 reason text NOT NULL, evidence jsonb NOT NULL,
 PRIMARY KEY(code,release_id)
);
CREATE TABLE m2_shared.release_events (
 release_id text NOT NULL REFERENCES m2_shared.releases(id),
 event_id text NOT NULL, status text NOT NULL CHECK(status IN ('candidate','accepted','rejected','superseded')),
 review_artifact_sha256 text NOT NULL REFERENCES m2_shared.artifacts(sha256),
 created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(release_id,event_id)
);
ALTER TABLE m2_shared.segments ADD COLUMN transcript_id text REFERENCES m2_shared.transcripts(id);
ALTER TABLE m2_shared.frames ADD COLUMN media_id text REFERENCES m2_shared.media(id);
ALTER TABLE m2_shared.scenes ADD COLUMN media_id text REFERENCES m2_shared.media(id);
ALTER TABLE m2_shared.transcripts ADD COLUMN attempt_id text REFERENCES m2_shared.attempts(id);
ALTER TABLE m2_shared.language_decisions ADD COLUMN attempt_id text REFERENCES m2_shared.attempts(id);
ALTER TABLE m2_shared.shots ADD COLUMN script_id text REFERENCES m2_shared.scripts(id);
ALTER TABLE m2_shared.renders ADD COLUMN script_id text REFERENCES m2_shared.scripts(id);
ALTER TABLE m2_shared.reviews ADD COLUMN subject_artifact_sha256 text REFERENCES m2_shared.artifacts(sha256);
CREATE TABLE m2_shared.jobs (
 id text PRIMARY KEY, stage text NOT NULL, input_sha256 text NOT NULL,
 status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','running','partial','failed','excluded','done')),
 attempt integer NOT NULL DEFAULT 0 CHECK(attempt BETWEEN 0 AND 3),
 lease_token uuid, lease_until timestamptz, worker_id text,
 heartbeat_at timestamptz, output_sha256 text, error_code text,
 payload jsonb NOT NULL DEFAULT '{}',
 UNIQUE(stage,input_sha256),
 CHECK ((status='running') = (lease_token IS NOT NULL AND lease_until IS NOT NULL))
);
CREATE FUNCTION m2_shared.claim_job(p_worker text, p_seconds integer DEFAULT 300)
RETURNS SETOF m2_shared.jobs LANGUAGE plpgsql SET search_path=m2_shared,pg_temp AS $$
BEGIN
 IF p_worker IS NULL OR length(p_worker)=0 OR p_seconds NOT BETWEEN 30 AND 3600 THEN RAISE EXCEPTION 'invalid lease'; END IF;
 RETURN QUERY WITH candidate AS (
 SELECT id FROM m2_shared.jobs WHERE status='pending' AND attempt<3 ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1
 ) UPDATE m2_shared.jobs j SET status='running',attempt=attempt+1,worker_id=p_worker,
 lease_token=gen_random_uuid(),lease_until=clock_timestamp()+make_interval(secs=>p_seconds),heartbeat_at=clock_timestamp()
 FROM candidate c WHERE j.id=c.id RETURNING j.*;
END $$;
CREATE FUNCTION m2_shared.finish_job(p_id text,p_token uuid,p_status text,p_output text)
RETURNS boolean LANGUAGE plpgsql SET search_path=m2_shared,pg_temp AS $$
BEGIN
 IF p_status NOT IN ('partial','failed','excluded','done') THEN RAISE EXCEPTION 'invalid terminal status'; END IF;
 IF p_status='done' AND (p_output IS NULL OR p_output !~ '^[0-9a-f]{64}$') THEN RAISE EXCEPTION 'output hash required'; END IF;
 UPDATE m2_shared.jobs SET status=p_status,output_sha256=p_output,lease_token=NULL,lease_until=NULL
 WHERE id=p_id AND lease_token=p_token AND status='running' AND lease_until>clock_timestamp();
 RETURN FOUND;
END $$;
CREATE FUNCTION m2_shared.heartbeat_job(p_id text,p_token uuid,p_seconds integer DEFAULT 300)
RETURNS boolean LANGUAGE plpgsql SET search_path=m2_shared,pg_temp AS $$
BEGIN
 IF p_seconds NOT BETWEEN 30 AND 3600 THEN RAISE EXCEPTION 'invalid lease'; END IF;
 UPDATE m2_shared.jobs SET heartbeat_at=clock_timestamp(),lease_until=clock_timestamp()+make_interval(secs=>p_seconds)
 WHERE id=p_id AND lease_token=p_token AND status='running' AND lease_until>clock_timestamp();
 RETURN FOUND;
END $$;
CREATE FUNCTION m2_shared.recover_job(p_id text)
RETURNS boolean LANGUAGE plpgsql SET search_path=m2_shared,pg_temp AS $$
BEGIN
 UPDATE m2_shared.jobs SET status=CASE WHEN attempt>=3 THEN 'failed' ELSE 'pending' END,
 lease_token=NULL,lease_until=NULL,error_code='LEASE_EXPIRED'
 WHERE id=p_id AND status='running' AND lease_until<=clock_timestamp();
 RETURN FOUND;
END $$;
CREATE FUNCTION m2_shared.reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable evidence: create a new version'; END $$;
CREATE TRIGGER source_rows_immutable BEFORE UPDATE OR DELETE ON m2_shared.source_rows FOR EACH ROW EXECUTE FUNCTION m2_shared.reject_mutation();
CREATE TRIGGER sources_immutable BEFORE UPDATE OR DELETE ON m2_shared.sources FOR EACH ROW EXECUTE FUNCTION m2_shared.reject_mutation();
DO $$ DECLARE t record; BEGIN
 FOR t IN SELECT tablename FROM pg_tables WHERE schemaname='m2_shared' LOOP
 EXECUTE format('ALTER TABLE m2_shared.%I ENABLE ROW LEVEL SECURITY',t.tablename);
 EXECUTE format('REVOKE ALL ON m2_shared.%I FROM PUBLIC',t.tablename);
 IF t.tablename NOT IN ('jobs','source_rows','sources') THEN
 EXECUTE format('CREATE TRIGGER immutable_evidence BEFORE UPDATE OR DELETE ON m2_shared.%I FOR EACH ROW EXECUTE FUNCTION m2_shared.reject_mutation()',t.tablename);
 END IF;
 END LOOP;
END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA m2_shared FROM PUBLIC;
COMMIT;
