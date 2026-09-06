from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from m2_signal.corpus_features import FeatureJoinError, build_feature_dataset, build_feature_dataset_from_files, load_canonical_manifest


def _write_json(root: Path, relative: str, value: dict) -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_db(root: Path, rows: list[dict], *, manifest_sha256: str = "manifest-hash") -> Path:
    path = root / "corpus.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE binding (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE reels (
          reel_id TEXT PRIMARY KEY, code TEXT UNIQUE NOT NULL, identity_index INTEGER NOT NULL,
          acquisition_state TEXT NOT NULL, transcript_state TEXT NOT NULL, frames_state TEXT NOT NULL,
          scene_review_state TEXT NOT NULL, acquisition_artifact TEXT, transcript_artifact TEXT, frames_artifact TEXT
        );
        CREATE TABLE attempts (
          id INTEGER PRIMARY KEY, reel_id TEXT NOT NULL, stage TEXT NOT NULL, attempt INTEGER NOT NULL,
          state TEXT NOT NULL, error TEXT, started REAL NOT NULL, finished REAL, artifacts_json TEXT, resources_json TEXT
        );
        """
    )
    conn.executemany("INSERT INTO binding(key,value) VALUES(?,?)", [("manifest_sha256", manifest_sha256), ("config_sha256", "config-hash")])
    for row in rows:
        conn.execute(
            "INSERT INTO reels VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                row["reel_id"], row["code"], row["identity_index"], row["acquisition_state"],
                row["transcript_state"], row["frames_state"], row["scene_review_state"],
                json.dumps(row.get("acquisition_artifact")), json.dumps(row.get("transcript_artifact")), json.dumps(row.get("frames_artifact")),
            ),
        )
        for stage, state in row.get("attempts", {}).items():
                conn.execute("INSERT INTO attempts VALUES(NULL,?,?,?,?,?,?,?,?,?)", (row["reel_id"], stage, 1, state, None, 1.0, 2.0, "{}", "{}"))
    conn.commit()
    conn.close()
    return path


class CorpusFeatureTests(unittest.TestCase):
    def test_keeps_canonical_population_and_explicit_missingness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            media_path = root / "acquisition/A.mp4"
            media_path.parent.mkdir(parents=True, exist_ok=True)
            media_path.write_bytes(b"media-a")
            media_hash = hashlib.sha256(media_path.read_bytes()).hexdigest()
            acq_hash = _write_json(root, "acquisition/A.media.json", {"schema": "m2.acquired-media.v1", "duration_ms": 12000, "has_audio": True, "sha256": media_hash})
            tx_hash = _write_json(root, "transcripts/A/transcription.json", {"schema": "m2.transcript-evidence.v1", "observation_state": "OBSERVED", "source_media_hash": media_hash, "language": "en", "lexical_word_count": 12, "aligned_word_count": 12, "word_timing": "OBSERVED", "segments": [{"segment_id": "T1"}]})
            fr_hash = _write_json(root, "frames/A/receipt.json", {"schema": "m2.visual-preview.v2", "source_media_hash": media_hash, "frame_observation_state": "OBSERVED", "frame_budget": {"observed_frames": 6, "requested_frames": 6, "max_frames": 24, "truncated": False}, "cut_observation_state": "OBSERVED", "cut_candidates_ms": [], "cut_sampling_disclosure": {"truncated": False}})
            artifact = lambda path, digest: {path: digest}
            db = _make_db(root, [{
                "reel_id": "instagram:A", "code": "A", "identity_index": 0,
                "acquisition_state": "OBSERVED", "transcript_state": "OBSERVED", "frames_state": "OBSERVED", "scene_review_state": "REVIEW_PENDING",
                "acquisition_artifact": {"acquisition/A.media.json": acq_hash, "acquisition/A.mp4": media_hash}, "transcript_artifact": artifact("transcripts/A/transcription.json", tx_hash), "frames_artifact": artifact("frames/A/receipt.json", fr_hash),
                "attempts": {"acquisition": "OBSERVED", "transcript": "OBSERVED", "frames": "OBSERVED"},
            }])
            canonical = [
                {"reel_id": "instagram:A", "code": "A", "identity_index": 0, "research_quarantine_reasons": ["RESEARCH_QUARANTINE"]},
                {"reel_id": "instagram:B", "code": "B", "identity_index": 1},
            ]
            metadata = [
                {"reel_id": "instagram:A", "account_username": "acct-a", "views": 1000, "likes_per_1k_views": 4, "comments_per_1k_views": 2, "reshares_per_1k_views": 1, "saves_per_1k_views": 3, "numeric_valid": True, "eligibility_state": "PASS", "snapshot_date": "2026-09-01"},
                {"reel_id": "instagram:B", "account_username": "acct-b", "views": 0, "numeric_valid": False, "metric_missing_fields": ["saves"]},
            ]
            result = build_feature_dataset(canonical, db, artifact_root=root, metadata_rows=metadata)
            rows = {row["code"]: row for row in result["rows"]}
            self.assertEqual(result["summary"]["denominators"]["canonical_reels"], 2)
            self.assertEqual(len(result["rows"]), 2)
            self.assertTrue(rows["A"]["quarantined"])
            self.assertEqual(rows["A"]["transcript_word_count_lexical"], 12)
            self.assertEqual(rows["A"]["media_duration_seconds"], 12.0)
            self.assertAlmostEqual(rows["A"]["transcript_words_per_second"], 1.0)
            self.assertAlmostEqual(rows["A"]["transcript_aligned_words_per_second"], 1.0)
            self.assertEqual(rows["A"]["transcript_rate_comparability"], "LANGUAGE_CONDITIONED_TOKEN_RATE")
            self.assertEqual(rows["A"]["frame_sample_count"], 6)
            self.assertEqual(rows["A"]["cut_candidate_count"], 0)
            self.assertEqual(rows["A"]["comparability_gate"], "DESCRIPTIVE_ONLY_READY")
            self.assertEqual(rows["A"]["metric_eligibility_gate"], "BLOCKED_CANONICAL_QUARANTINE")
            self.assertIn("CORPUS_RECEIPT_MISSING", rows["B"]["missingness_reasons"])
            self.assertIn("MEDIA_STATE_NOT_ATTEMPTED", rows["B"]["missingness_reasons"])
            self.assertEqual(rows["B"]["model_gate"], "DISABLED_NO_FIT_REQUESTED")
            self.assertEqual(rows["B"]["metric_eligibility_gate"], "BLOCKED_METRIC_COMPARABILITY")

    def test_artifact_hash_mismatch_does_not_create_features(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_json(root, "acquisition/A.media.json", {"duration_ms": 12000, "has_audio": True})
            db = _make_db(root, [{
                "reel_id": "instagram:A", "code": "A", "identity_index": 0,
                "acquisition_state": "OBSERVED", "transcript_state": "NOT_ATTEMPTED", "frames_state": "NOT_ATTEMPTED", "scene_review_state": "NOT_ATTEMPTED",
                "acquisition_artifact": {"acquisition/A.media.json": "0" * 64}, "attempts": {"acquisition": "OBSERVED"},
            }])
            row = build_feature_dataset([{ "reel_id": "instagram:A", "code": "A", "identity_index": 0 }], db, artifact_root=root)["rows"][0]
            self.assertEqual(row["media_artifact_state"], "HASH_MISMATCH")
            self.assertIsNone(row["media_duration_ms"])
            self.assertIn("MEDIA_ARTIFACT_HASH_MISMATCH", row["missingness_reasons"])

    def test_empty_and_suspicious_asr_states_remain_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            empty_hash = _write_json(root, "transcripts/A/transcription.json", {"schema": "m2.transcript-evidence.v1", "observation_state": "EMPTY_OUTPUT_UNVERIFIED", "language": "pa", "segments": []})
            suspicious_hash = _write_json(root, "transcripts/B/transcription.json", {"schema": "m2.transcript-evidence.v1", "observation_state": "SUSPICIOUS_TIMINGS", "language": "en", "segments": []})
            db = _make_db(root, [
                {"reel_id": "instagram:A", "code": "A", "identity_index": 0, "acquisition_state": "OBSERVED", "transcript_state": "EMPTY_OUTPUT_UNVERIFIED", "frames_state": "OBSERVED", "scene_review_state": "REVIEW_PENDING", "transcript_artifact": {"transcripts/A/transcription.json": empty_hash}},
                {"reel_id": "instagram:B", "code": "B", "identity_index": 1, "acquisition_state": "OBSERVED", "transcript_state": "SUSPICIOUS_TIMINGS", "frames_state": "OBSERVED", "scene_review_state": "REVIEW_PENDING", "transcript_artifact": {"transcripts/B/transcription.json": suspicious_hash}},
            ])
            result = build_feature_dataset([{ "reel_id": "instagram:A", "code": "A" }, { "reel_id": "instagram:B", "code": "B" }], db, artifact_root=root)
            rows = {row["code"]: row for row in result["rows"]}
            self.assertIn("TRANSCRIPT_EMPTY_UNVERIFIED", rows["A"]["missingness_reasons"])
            self.assertIn("SILENCE_NOT_PROVEN", rows["A"]["missingness_reasons"])
            self.assertIn("TRANSCRIPT_SUSPICIOUS_TIMINGS", rows["B"]["missingness_reasons"])
            self.assertNotIn("TRANSCRIPT_EMPTY_UNVERIFIED", rows["B"]["missingness_reasons"])

    def test_source_identity_mismatch_withholds_transcript_features(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            media_path = root / "acquisition/A.mp4"
            media_path.parent.mkdir(parents=True, exist_ok=True)
            media_path.write_bytes(b"media-a")
            media_hash = hashlib.sha256(media_path.read_bytes()).hexdigest()
            acq_hash = _write_json(root, "acquisition/A.media.json", {"duration_ms": 12000, "has_audio": True, "sha256": media_hash})
            tx_hash = _write_json(root, "transcripts/A/transcription.json", {"language": "en", "source_media_hash": "f" * 64, "lexical_word_count": 12, "aligned_word_count": 12, "segments": []})
            fr_hash = _write_json(root, "frames/A/receipt.json", {"source_media_hash": media_hash, "frame_budget": {"observed_frames": 2, "requested_frames": 2}, "cut_observation_state": "OBSERVED"})
            db = _make_db(root, [{
                "reel_id": "instagram:A", "code": "A", "identity_index": 0,
                "acquisition_state": "OBSERVED", "transcript_state": "OBSERVED", "frames_state": "OBSERVED", "scene_review_state": "REVIEW_PENDING",
                "acquisition_artifact": {"acquisition/A.media.json": acq_hash, "acquisition/A.mp4": media_hash},
                "transcript_artifact": {"transcripts/A/transcription.json": tx_hash}, "frames_artifact": {"frames/A/receipt.json": fr_hash},
            }])
            row = build_feature_dataset([{"reel_id": "instagram:A", "code": "A"}], db, artifact_root=root)["rows"][0]
            self.assertTrue(row["media_artifact_verified"])
            self.assertEqual(row["transcript_source_identity_state"], "SOURCE_HASH_MISMATCH")
            self.assertFalse(row["transcript_artifact_verified"])
            self.assertIsNone(row["transcript_word_count_lexical"])
            self.assertTrue(row["frames_artifact_verified"])
            self.assertIsNone(row["cut_candidate_count"])

    def test_numeric_and_unknown_language_gates_are_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = _make_db(root, [{
                "reel_id": "instagram:A", "code": "A", "identity_index": 0,
                "acquisition_state": "NOT_ATTEMPTED", "transcript_state": "NOT_ATTEMPTED", "frames_state": "NOT_ATTEMPTED", "scene_review_state": "NOT_ATTEMPTED",
            }])
            row = build_feature_dataset([{"reel_id": "instagram:A", "code": "A"}], db, metadata_rows=[{
                "reel_id": "instagram:A", "account_username": "acct-a", "views": -1,
                "likes_per_1k_views": float("nan"), "comments_per_1k_views": -2,
                "reshares_per_1k_views": 1, "saves_per_1k_views": 1, "numeric_valid": 1.0,
            }])["rows"][0]
            self.assertEqual(row["comparability_gate"], "BLOCKED_NUMERIC_INVALID")
            self.assertEqual(row["metric_eligibility_gate"], "BLOCKED_METRIC_COMPARABILITY")
            self.assertIsNone(row["views"])
            self.assertIn("likes_per_1k_views", row["metric_invalid_fields"])
            self.assertIn("comments_per_1k_views", row["metric_invalid_fields"])
            self.assertEqual(row["transcript_rate_comparability"], "UNKNOWN_RATE_UNAVAILABLE")

    def test_symlink_database_and_artifact_ancestor_are_rejected(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = _make_db(root, [])
            db_link = root / "corpus-link.sqlite"
            os.symlink(db, db_link)
            with self.assertRaises(FeatureJoinError):
                build_feature_dataset([{"reel_id": "instagram:A"}], db_link)

            outside = root / "outside"
            outside.mkdir()
            os.symlink(outside, root / "linked")
            artifact = outside / "A.media.json"
            artifact.write_text("{}", encoding="utf-8")
            linked_db_root = root / "linked-case"
            linked_db_root.mkdir()
            linked_db = _make_db(linked_db_root, [{
                "reel_id": "instagram:A", "code": "A", "identity_index": 0,
                "acquisition_state": "OBSERVED", "transcript_state": "NOT_ATTEMPTED", "frames_state": "NOT_ATTEMPTED", "scene_review_state": "NOT_ATTEMPTED",
                "acquisition_artifact": {"linked/A.media.json": "0" * 64},
            }])
            row = build_feature_dataset([{"reel_id": "instagram:A"}], linked_db, artifact_root=root)["rows"][0]
            self.assertEqual(row["media_artifact_state"], "MISSING_FILE")
            self.assertFalse(row["media_artifact_verified"])

    def test_structural_labels_only_from_explicit_independent_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = _make_db(root, [{"reel_id": "instagram:A", "code": "A", "identity_index": 0, "acquisition_state": "NOT_ATTEMPTED", "transcript_state": "NOT_ATTEMPTED", "frames_state": "NOT_ATTEMPTED", "scene_review_state": "REVIEW_PENDING"}])
            canonical = [{"reel_id": "instagram:A", "code": "A"}]
            rejected = {"instagram:A": [{"maker": "maker", "reviewer": "maker", "review_state": "APPROVED"}]}
            accepted = {"instagram:A": [{"maker": "maker", "reviewer": "reviewer", "review_state": "APPROVED"}, {"maker": "maker", "reviewer": "reviewer", "review_state": "PENDING"}]}
            row_rejected = build_feature_dataset(canonical, db, reviewed_scene_rows=rejected)["rows"][0]
            row_accepted = build_feature_dataset(canonical, db, reviewed_scene_rows=accepted)["rows"][0]
            self.assertEqual(row_rejected["structural_label_state"], "UNAVAILABLE_UNREVIEWED")
            self.assertEqual(row_accepted["structural_label_state"], "UNAVAILABLE_UNREVIEWED")
            self.assertEqual(row_accepted["reviewed_scene_state"], "DISABLED_MVP")
            self.assertEqual(row_accepted["reviewed_scene_count"], 0)

    def test_manifest_and_metadata_duplicates_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"entries": [{"reel_id": "instagram:A", "code": "A", "identity_index": 0}, {"reel_id": "instagram:A", "code": "A2", "identity_index": 1}]}), encoding="utf-8")
            with self.assertRaises(FeatureJoinError):
                load_canonical_manifest(manifest)
            db = _make_db(root, [], manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest())
            with self.assertRaises(FeatureJoinError):
                build_feature_dataset([{ "reel_id": "instagram:A" }], db, metadata_rows=[{"reel_id": "instagram:A"}, {"code": "A"}])

    def test_file_entrypoint_reports_manifest_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"schema": "m2.media-manifest.v1", "entries": [{"reel_id": "instagram:A", "code": "A", "identity_index": 0}]}), encoding="utf-8")
            db = _make_db(root, [], manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest())
            result = build_feature_dataset_from_files(manifest, db)
            self.assertEqual(result["provenance"]["manifest_entry_count"], 1)
            self.assertEqual(len(result["provenance"]["manifest_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
