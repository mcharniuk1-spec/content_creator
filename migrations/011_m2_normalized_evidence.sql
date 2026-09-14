-- Typed, versioned projections. Presence in a source is never review acceptance.
BEGIN;
ALTER TABLE m2_shared.reels ADD CONSTRAINT canonical_instagram_code CHECK(code ~ '^[A-Za-z0-9_-]{11}$');
CREATE SCHEMA m2_evidence;
REVOKE ALL ON SCHEMA m2_evidence FROM PUBLIC;
CREATE TABLE m2_shared.release_source_rows (
 release_id text NOT NULL REFERENCES m2_shared.releases(id), source_id text NOT NULL,
 table_name text NOT NULL, row_key text NOT NULL,
 PRIMARY KEY(release_id,source_id,table_name,row_key),
 FOREIGN KEY(source_id,table_name,row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key)
);
ALTER TABLE m2_shared.release_source_rows ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON m2_shared.release_source_rows FROM PUBLIC;
CREATE TRIGGER immutable_evidence BEFORE UPDATE OR DELETE ON m2_shared.release_source_rows FOR EACH ROW EXECUTE FUNCTION m2_shared.reject_mutation();
CREATE TABLE m2_shared.release_parents (
 release_id text NOT NULL REFERENCES m2_shared.releases(id), parent_release_id text NOT NULL REFERENCES m2_shared.releases(id),
 PRIMARY KEY(release_id,parent_release_id), CHECK(release_id<>parent_release_id)
);
ALTER TABLE m2_shared.release_parents ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON m2_shared.release_parents FROM PUBLIC;
CREATE TRIGGER immutable_evidence BEFORE UPDATE OR DELETE ON m2_shared.release_parents FOR EACH ROW EXECUTE FUNCTION m2_shared.reject_mutation();
CREATE DOMAIN m2_evidence.sha256 AS text CHECK(VALUE ~ '^[0-9a-f]{64}$');
CREATE TABLE m2_evidence.projections (
 id text PRIMARY KEY, release_id text NOT NULL REFERENCES m2_shared.releases(id),
 mapping_sha256 m2_evidence.sha256 NOT NULL,
 input_manifest_sha256 m2_evidence.sha256 NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE m2_evidence.lineage (
 id m2_evidence.sha256 PRIMARY KEY, source_id text NOT NULL,
 source_table text NOT NULL, source_row_key text NOT NULL,
 code text REFERENCES m2_shared.reels(code),
 FOREIGN KEY(source_id,source_table,source_row_key) REFERENCES m2_shared.source_rows(source_id,table_name,row_key),
 UNIQUE(id,code)
);
CREATE TABLE m2_evidence.projection_parents (
 projection_id text NOT NULL REFERENCES m2_evidence.projections(id),
 parent_projection_id text NOT NULL REFERENCES m2_evidence.projections(id),
 PRIMARY KEY(projection_id,parent_projection_id), CHECK(projection_id<>parent_projection_id)
);
CREATE TABLE m2_evidence.projection_members (
 projection_id text REFERENCES m2_evidence.projections(id), lineage_id m2_evidence.sha256 REFERENCES m2_evidence.lineage(id),
 PRIMARY KEY(projection_id,lineage_id)
);
CREATE TABLE m2_evidence.metrics (
 lineage_id m2_evidence.sha256 PRIMARY KEY REFERENCES m2_evidence.lineage(id),
 code text NOT NULL REFERENCES m2_shared.reels(code), snapshot_native_id text,
 snapshot_taken text, capture_precision text NOT NULL CHECK(capture_precision IN ('date','timestamp','unknown')),
 published_unix numeric, provider_account_id text, username_observed text,
 views bigint CHECK(views>=0), likes bigint CHECK(likes>=0), comments bigint CHECK(comments>=0),
 saves bigint CHECK(saves>=0), reshares bigint CHECK(reshares>=0), sends bigint CHECK(sends>=0),
 followers bigint CHECK(followers>=0), duration_seconds double precision CHECK(duration_seconds>=0),
 FOREIGN KEY(lineage_id,code) REFERENCES m2_evidence.lineage(id,code),
 CHECK((snapshot_taken IS NULL) = (capture_precision='unknown'))
);
CREATE TABLE m2_evidence.transcripts (
 lineage_id m2_evidence.sha256 PRIMARY KEY REFERENCES m2_evidence.lineage(id),
 code text NOT NULL REFERENCES m2_shared.reels(code), original_text text,
 text_sha256 m2_evidence.sha256, language_observed text,
 media_hash_declared text, model_observed text,
 state text NOT NULL CHECK(state IN ('source_text_unreviewed','empty','missing')),
 segments_parse_state text NOT NULL CHECK(segments_parse_state IN ('parsed','missing','invalid')),
 UNIQUE(lineage_id,code), FOREIGN KEY(lineage_id,code) REFERENCES m2_evidence.lineage(id,code)
);
CREATE TABLE m2_evidence.segments (
 transcript_id m2_evidence.sha256 NOT NULL, code text NOT NULL,
 ordinal integer CHECK(ordinal>=0), start_seconds double precision CHECK(start_seconds>=0),
 end_seconds double precision, original_text text NOT NULL,
 PRIMARY KEY(transcript_id,ordinal),
 FOREIGN KEY(transcript_id,code) REFERENCES m2_evidence.transcripts(lineage_id,code),
 CHECK(end_seconds>=start_seconds)
);
CREATE TABLE m2_evidence.media_pointers (
 lineage_id m2_evidence.sha256 PRIMARY KEY REFERENCES m2_evidence.lineage(id),
 code text NOT NULL, path_declared text, hash_declared text, bytes_declared bigint,
 state_declared text, FOREIGN KEY(lineage_id,code) REFERENCES m2_evidence.lineage(id,code)
);
CREATE TABLE m2_evidence.frame_pointers (
 lineage_id m2_evidence.sha256 PRIMARY KEY REFERENCES m2_evidence.lineage(id),
 code text NOT NULL, ordinal integer, timestamp_seconds double precision,
 path_declared text, image_hash_declared text, exists_declared integer,
 FOREIGN KEY(lineage_id,code) REFERENCES m2_evidence.lineage(id,code)
);
CREATE TABLE m2_evidence.scene_candidates (
 lineage_id m2_evidence.sha256 PRIMARY KEY REFERENCES m2_evidence.lineage(id),
 code text NOT NULL, native_scene_id text, start_seconds double precision,
 end_seconds double precision, boundary_method text, scene_type_declared text,
 frame_indices_declared jsonb, state text NOT NULL DEFAULT 'source_candidate_unreviewed'
 CHECK(state='source_candidate_unreviewed'),
 FOREIGN KEY(lineage_id,code) REFERENCES m2_evidence.lineage(id,code)
);
CREATE TABLE m2_evidence.asset_checks (
 id m2_evidence.sha256 PRIMARY KEY, code text NOT NULL REFERENCES m2_shared.reels(code),
 kind text NOT NULL CHECK(kind IN ('video','frame','contact_sheet','storyboard')),
 private_path text, actual_sha256 m2_evidence.sha256, byte_size bigint CHECK(byte_size>0),
 media_sha256 m2_evidence.sha256, timestamp_seconds double precision,
 state text NOT NULL CHECK(state IN ('verified_bytes','missing','hash_mismatch','unbound')),
 receipt_sha256 m2_evidence.sha256 NOT NULL, checked_at timestamptz NOT NULL,
 UNIQUE(id,code),
 CHECK(state<>'verified_bytes' OR (actual_sha256 IS NOT NULL AND byte_size IS NOT NULL AND private_path IS NOT NULL)),
 CHECK(kind<>'frame' OR state<>'verified_bytes' OR (media_sha256 IS NOT NULL AND timestamp_seconds>=0))
);
CREATE TABLE m2_evidence.reviews (
 id m2_evidence.sha256 PRIMARY KEY, subject_sha256 m2_evidence.sha256 NOT NULL,
 maker text NOT NULL, reviewer text NOT NULL CHECK(reviewer<>maker),
 scope text NOT NULL, verdict text NOT NULL CHECK(verdict IN ('accepted','rejected','limited')),
 receipt_sha256 m2_evidence.sha256 NOT NULL, reviewed_at timestamptz NOT NULL
);
CREATE TABLE m2_evidence.reviewed_scenes (
 id m2_evidence.sha256 PRIMARY KEY, code text NOT NULL REFERENCES m2_shared.reels(code),
 media_check_id m2_evidence.sha256 NOT NULL, start_seconds double precision NOT NULL CHECK(start_seconds>=0),
 end_seconds double precision NOT NULL CHECK(end_seconds>start_seconds),
 review_id m2_evidence.sha256 NOT NULL REFERENCES m2_evidence.reviews(id),
 description text NOT NULL, UNIQUE(id,code),
 FOREIGN KEY(media_check_id,code) REFERENCES m2_evidence.asset_checks(id,code)
);
CREATE TABLE m2_evidence.scene_alignment (
 scene_id m2_evidence.sha256 NOT NULL, code text NOT NULL, transcript_id m2_evidence.sha256 NOT NULL,
 segment_ordinal integer NOT NULL, review_id m2_evidence.sha256 NOT NULL REFERENCES m2_evidence.reviews(id),
 PRIMARY KEY(scene_id,transcript_id,segment_ordinal),
 FOREIGN KEY(scene_id,code) REFERENCES m2_evidence.reviewed_scenes(id,code),
 FOREIGN KEY(transcript_id,code) REFERENCES m2_evidence.transcripts(lineage_id,code),
 FOREIGN KEY(transcript_id,segment_ordinal) REFERENCES m2_evidence.segments(transcript_id,ordinal)
);
CREATE TABLE m2_evidence.coverage (
 projection_id text REFERENCES m2_evidence.projections(id), code text REFERENCES m2_shared.reels(code),
 transcript_versions integer NOT NULL CHECK(transcript_versions>=0),
 media_state text NOT NULL, frame_state text NOT NULL, cut_state text NOT NULL,
 scene_state text NOT NULL, alignment_state text NOT NULL,
 usable_frames integer NOT NULL CHECK(usable_frames>=0), reviewed_scenes integer NOT NULL CHECK(reviewed_scenes>=0),
 reasons jsonb NOT NULL, receipt_sha256 m2_evidence.sha256 NOT NULL,
 PRIMARY KEY(projection_id,code)
);
CREATE FUNCTION m2_evidence.validate_scene_review() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF NOT EXISTS(SELECT FROM m2_evidence.asset_checks WHERE id=NEW.media_check_id AND code=NEW.code AND kind='video' AND state='verified_bytes') THEN
 RAISE EXCEPTION 'verified original video required'; END IF;
 IF NOT EXISTS(SELECT FROM m2_evidence.reviews WHERE id=NEW.review_id AND subject_sha256=NEW.id AND verdict='accepted' AND scope='whole_video_scene') THEN
 RAISE EXCEPTION 'independent whole-video scene review required'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER reviewed_scene_gate BEFORE INSERT ON m2_evidence.reviewed_scenes FOR EACH ROW EXECUTE FUNCTION m2_evidence.validate_scene_review();
CREATE FUNCTION m2_evidence.validate_alignment_review() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF NOT EXISTS(SELECT FROM m2_evidence.reviews WHERE id=NEW.review_id AND subject_sha256=NEW.scene_id AND verdict='accepted' AND scope='transcript_scene_alignment') THEN
 RAISE EXCEPTION 'independent alignment review required'; END IF;
 IF NOT EXISTS(SELECT FROM m2_evidence.reviewed_scenes s JOIN m2_evidence.segments t ON t.transcript_id=NEW.transcript_id AND t.ordinal=NEW.segment_ordinal
 WHERE s.id=NEW.scene_id AND t.start_seconds<s.end_seconds AND t.end_seconds>s.start_seconds) THEN
 RAISE EXCEPTION 'segment must overlap scene'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER alignment_gate BEFORE INSERT ON m2_evidence.scene_alignment FOR EACH ROW EXECUTE FUNCTION m2_evidence.validate_alignment_review();
DO $$ DECLARE t record; BEGIN
 FOR t IN SELECT tablename FROM pg_tables WHERE schemaname='m2_evidence' LOOP
 EXECUTE format('ALTER TABLE m2_evidence.%I ENABLE ROW LEVEL SECURITY',t.tablename);
 EXECUTE format('REVOKE ALL ON m2_evidence.%I FROM PUBLIC',t.tablename);
 EXECUTE format('CREATE TRIGGER immutable_evidence BEFORE UPDATE OR DELETE ON m2_evidence.%I FOR EACH ROW EXECUTE FUNCTION m2_shared.reject_mutation()',t.tablename);
 END LOOP;
END $$;
COMMIT;
