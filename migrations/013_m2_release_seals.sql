-- Freeze admitted source membership after complete import, allowing exact replay.
BEGIN;
CREATE TABLE m2_shared.release_seals (
 release_id text PRIMARY KEY REFERENCES m2_shared.releases(id),
 manifest_sha256 text NOT NULL CHECK(manifest_sha256 ~ '^[0-9a-f]{64}$'),
 source_row_count bigint NOT NULL CHECK(source_row_count>0),
 cohort_sha256 text NOT NULL CHECK(cohort_sha256 ~ '^[0-9a-f]{64}$'),
 sealed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
ALTER TABLE m2_shared.release_seals ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON m2_shared.release_seals FROM PUBLIC;
CREATE TRIGGER immutable_evidence BEFORE UPDATE OR DELETE ON m2_shared.release_seals FOR EACH ROW EXECUTE FUNCTION m2_shared.reject_mutation();
CREATE FUNCTION m2_shared.guard_sealed_membership() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 -- The same release lock serializes sealing with new membership inserts.
 PERFORM 1 FROM m2_shared.releases WHERE id=NEW.release_id FOR UPDATE;
 IF EXISTS(SELECT FROM m2_shared.release_seals WHERE release_id=NEW.release_id) THEN
  IF TG_TABLE_NAME='release_source_rows' THEN
   IF NOT EXISTS(SELECT FROM m2_shared.release_source_rows WHERE release_id=NEW.release_id
    AND source_id=NEW.source_id AND table_name=NEW.table_name AND row_key=NEW.row_key) THEN
    RAISE EXCEPTION 'sealed release membership';
   END IF;
  ELSE
   IF NOT EXISTS(SELECT FROM m2_shared.release_parents WHERE release_id=NEW.release_id AND parent_release_id=NEW.parent_release_id) THEN
    RAISE EXCEPTION 'sealed release parents';
   END IF;
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER sealed_membership BEFORE INSERT ON m2_shared.release_source_rows FOR EACH ROW EXECUTE FUNCTION m2_shared.guard_sealed_membership();
CREATE TRIGGER sealed_parents BEFORE INSERT ON m2_shared.release_parents FOR EACH ROW EXECUTE FUNCTION m2_shared.guard_sealed_membership();
CREATE FUNCTION m2_shared.seal_release(p_release text) RETURNS text LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE manifest text; n bigint; cohort text; existing m2_shared.release_seals;
BEGIN
 SELECT manifest_sha256 INTO STRICT manifest FROM m2_shared.releases WHERE id=p_release FOR UPDATE;
 SELECT count(*),encode(sha256(convert_to(string_agg(
  jsonb_build_array(c.source_id,c.table_name,c.row_key,r.payload_sha256)::text,E'\n'
  ORDER BY c.source_id,c.table_name,c.row_key),'UTF8')),'hex') INTO n,cohort
 FROM m2_shared.release_source_rows c JOIN m2_shared.source_rows r USING(source_id,table_name,row_key) WHERE c.release_id=p_release;
 IF n=0 THEN RAISE EXCEPTION 'empty release cohort'; END IF;
 INSERT INTO m2_shared.release_seals(release_id,manifest_sha256,source_row_count,cohort_sha256)
 VALUES(p_release,manifest,n,cohort) ON CONFLICT DO NOTHING;
 SELECT * INTO existing FROM m2_shared.release_seals WHERE release_id=p_release;
 IF existing.manifest_sha256<>manifest OR existing.source_row_count<>n OR existing.cohort_sha256<>cohort THEN
  RAISE EXCEPTION 'release seal mismatch';
 END IF;
 RETURN cohort;
END $$;
REVOKE ALL ON FUNCTION m2_shared.seal_release(text),m2_shared.guard_sealed_membership() FROM PUBLIC;
COMMIT;
