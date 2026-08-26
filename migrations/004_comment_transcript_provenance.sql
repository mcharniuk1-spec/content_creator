-- Additive provenance for bounded comment/reply and transcript artifacts.

BEGIN;
SET search_path = north_hux, public;

CREATE TABLE IF NOT EXISTS comment_edge_observation (
    comment_edge_observation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    comment_id bigint NOT NULL REFERENCES comment(comment_id),
    relationship_type text NOT NULL CHECK (relationship_type = 'reply'),
    native_parent_comment_id text NOT NULL,
    observed_at timestamptz NOT NULL,
    raw_object_id bigint NOT NULL REFERENCES raw_object(raw_object_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (comment_id, native_parent_comment_id, observed_at)
);

CREATE INDEX IF NOT EXISTS idx_comment_edge_parent
    ON comment_edge_observation(native_parent_comment_id, observed_at DESC);

CREATE OR REPLACE FUNCTION reject_collection_observation_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'collection observation tables are append-only; insert a corrected observation instead';
END;
$$;

DROP TRIGGER IF EXISTS comment_edge_observation_append_only ON comment_edge_observation;
CREATE TRIGGER comment_edge_observation_append_only
BEFORE UPDATE OR DELETE ON comment_edge_observation
FOR EACH ROW EXECUTE FUNCTION reject_collection_observation_mutation();

COMMIT;

