BEGIN;
CREATE TABLE m2_evidence.projection_assets (
 projection_id text NOT NULL REFERENCES m2_evidence.projections(id),
 asset_check_id m2_evidence.sha256 NOT NULL REFERENCES m2_evidence.asset_checks(id),
 PRIMARY KEY(projection_id,asset_check_id)
);
ALTER TABLE m2_evidence.projection_assets ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON m2_evidence.projection_assets FROM PUBLIC;
CREATE TRIGGER immutable_evidence BEFORE UPDATE OR DELETE ON m2_evidence.projection_assets FOR EACH ROW EXECUTE FUNCTION m2_shared.reject_mutation();
COMMIT;
