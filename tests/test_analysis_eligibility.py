from __future__ import annotations

import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

from m2_signal.analysis_eligibility import (
    EligibilityInputError,
    build_eligibility,
    classify_row,
    sha256_file,
)


def feature_row(index: int, **updates):
    row = {
        "reel_id": f"instagram:R{index}",
        "code": f"R{index}",
        "identity_index": index,
        "quarantine_reasons": [],
        "research_quarantine_reasons": [],
        "quarantined": False,
        "account_cluster_id": "account-a",
        "acquisition_state": "NOT_ATTEMPTED",
        "media_artifact_verified": False,
        "transcript_state": "NOT_ATTEMPTED",
        "transcript_artifact_verified": False,
        "transcript_source_identity_state": "UNVERIFIED",
        "frames_state": "NOT_ATTEMPTED",
        "frames_artifact_verified": False,
        "frames_source_identity_state": "UNVERIFIED",
        "scene_review_state": "NOT_ATTEMPTED",
        "reviewed_scene_state": "DISABLED_MVP",
        "structural_label_state": "UNAVAILABLE_UNREVIEWED",
        "transcript_rate_comparability": "UNKNOWN_RATE_UNAVAILABLE",
        "transcript_word_count_lexical": None,
        "transcript_aligned_word_count": None,
        "transcript_words_per_second": None,
        "transcript_word_timing_state": None,
        "snapshot_date": "2026-09-01",
        "views": 100,
        "likes_per_1k_views": 2.0,
        "comments_per_1k_views": 1.0,
        "reshares_per_1k_views": 0.0,
        "saves_per_1k_views": None,
        "metric_missing_fields": ["saves_per_1k_views"],
        "metric_invalid_fields": [],
        "metric_eligibility_gate": "BLOCKED_METRIC_COMPARABILITY",
    }
    row.update(updates)
    return row


class AnalysisEligibilityTests(unittest.TestCase):
    def test_action_outcomes_are_independent_of_saves(self):
        result = classify_row(feature_row(0))
        self.assertTrue(result["outcomes"]["likes_per_1k_views"]["eligible"])
        self.assertTrue(result["outcomes"]["comments_per_1k_views"]["eligible"])
        self.assertTrue(result["outcomes"]["reshares_per_1k_views"]["eligible"])
        self.assertFalse(result["outcomes"]["saves_per_1k_views"]["eligible"])
        self.assertEqual(result["outcomes"]["saves_per_1k_views"]["metric_states"]["saves_per_1k_views"], "MISSING_DECLARED")
        self.assertFalse(result["outcomes"]["saves_per_1k_views"]["requires_other_action_rates"])
        self.assertTrue(result["outcomes"]["saves_per_1k_views"]["requires_saves"])
        self.assertFalse(result["outcomes"]["total_actions_per_1k_views"]["eligible"])
        self.assertTrue(result["outcomes"]["total_actions_per_1k_views"]["requires_other_action_rates"])

    def test_nonfinite_and_negative_values_are_invalid(self):
        result = classify_row(feature_row(0, views=float("nan"), likes_per_1k_views=-1.0))
        self.assertEqual(result["metrics"]["views_state"], "INVALID_NONFINITE")
        self.assertEqual(result["outcomes"]["likes_per_1k_views"]["metric_states"]["likes_per_1k_views"], "INVALID_NEGATIVE")
        self.assertEqual(result["outcomes"]["likes_per_1k_views"]["state"], "INELIGIBLE_INVALID")

    def test_missing_is_distinct_from_observed_zero(self):
        result = classify_row(feature_row(0))
        self.assertEqual(result["metrics"]["reshares_per_1k_views"], 0.0)
        self.assertEqual(result["outcomes"]["reshares_per_1k_views"]["metric_states"]["reshares_per_1k_views"], "OBSERVED_ZERO")
        self.assertEqual(result["outcomes"]["saves_per_1k_views"]["metric_states"]["saves_per_1k_views"], "MISSING_DECLARED")
        self.assertIn("saves_per_1k_views:saves_per_1k_views_MISSING_DECLARED", result["missingness"])

    def test_unknown_account_and_invalid_snapshot_are_separate_gates(self):
        unknown = classify_row(feature_row(0, account_cluster_id=None))
        self.assertEqual(unknown["metrics"]["account_state"], "UNKNOWN_ACCOUNT_CLUSTER")
        self.assertTrue(unknown["outcomes"]["likes_per_1k_views"]["eligible"])
        self.assertFalse(unknown["outcomes"]["likes_per_1k_views"]["grouped_eligible"])
        invalid_snapshot = classify_row(feature_row(0, snapshot_date="not-a-date"))
        self.assertEqual(invalid_snapshot["metrics"]["snapshot_state"], "INVALID_SNAPSHOT")
        self.assertFalse(invalid_snapshot["outcomes"]["likes_per_1k_views"]["eligible"])
        self.assertIn("INVALID_SNAPSHOT", invalid_snapshot["outcomes"]["likes_per_1k_views"]["reasons"])

    def test_state_only_review_and_word_rate_without_timing_are_blocked(self):
        row = feature_row(0, structural_label_state="ACCEPTED_REVIEWED", reviewed_scene_state="ACCEPTED", frames_artifact_verified=True, frames_source_identity_state="VERIFIED", transcript_state="OBSERVED", transcript_artifact_verified=True, transcript_source_identity_state="VERIFIED", asr_language="en", transcript_rate_comparability="LANGUAGE_CONDITIONED_TOKEN_RATE", transcript_word_count_lexical=10, transcript_aligned_word_count=10, transcript_words_per_second=2.0)
        result = classify_row(row)
        self.assertEqual(result["modalities"]["structural_labels"]["state"], "UNVERIFIED_STATE_ONLY")
        self.assertEqual(result["modalities"]["scenes"]["state"], "UNVERIFIED_STATE_ONLY")
        self.assertEqual(result["modalities"]["language_conditioned_word_rate"]["state"], "NOT_ELIGIBLE")

    def test_numeric_overflow_and_quarantine_boolean_are_preserved(self):
        row = feature_row(0, views=10**400, quarantined=True, quarantine_reasons=[])
        result = classify_row(row)
        self.assertEqual(result["metrics"]["views_state"], "INVALID_OVERFLOW")
        self.assertIn("CANONICAL_QUARANTINE", result["missingness"])

    def test_rowcount_preservation_and_hash_bound_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            features = root / "features.jsonl"
            features.write_text("\n".join(json.dumps(feature_row(i), sort_keys=True) for i in range(2)) + "\n", encoding="utf-8")
            contract = root / "contract.json"
            contract.write_text(json.dumps({"schema": "m2.full-evidence-analysis-contract.v1", "status": "DESIGN_COMPLETE_FIT_PENDING_REVIEWED_EVIDENCE"}), encoding="utf-8")
            dictionary = root / "dictionary.json"
            dictionary.write_text(json.dumps({"schema": "m2.corpus-features-field-dictionary.v1", "fields": {"views": {"meaning": "views"}}}), encoding="utf-8")
            output = root / "output"
            result = build_eligibility(features, output, contract_path=contract, field_dictionary_path=dictionary, expected_features_sha256=sha256_file(features), expected_rows=2)
            self.assertEqual(result["summary"]["denominators"]["input_rows"], 2)
            self.assertEqual(result["summary"]["denominators"]["output_rows"], 2)
            self.assertEqual(len((output / "coverage-and-eligibility.jsonl").read_text().splitlines()), 2)
            dictionary = json.loads((output / "field-dictionary.json").read_text())
            self.assertEqual(dictionary["schema"], "m2.analysis-eligibility-field-dictionary.v1")
            self.assertIn("outcomes.*.state", dictionary["derived_fields"])
            self.assertIn("outcomes.*.reasons", dictionary["derived_fields"])
            analysis_run = json.loads((output / "analysis-run.json").read_text())
            self.assertEqual(analysis_run["runtime"]["module_sha256"], sha256_file(Path(__file__).parents[1] / "m2_signal" / "analysis_eligibility.py"))
            self.assertTrue((output / "artifact-manifest.json").is_file())

    def test_changed_feature_hash_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            features = root / "features.jsonl"
            features.write_text(json.dumps(feature_row(0)) + "\n", encoding="utf-8")
            expected = hashlib.sha256(b"different") .hexdigest()
            contract = root / "contract.json"
            contract.write_text(json.dumps({"schema": "m2.full-evidence-analysis-contract.v1"}), encoding="utf-8")
            dictionary = root / "dictionary.json"
            dictionary.write_text(json.dumps({"fields": {"views": {}}}), encoding="utf-8")
            with self.assertRaisesRegex(EligibilityInputError, "feature_dataset_hash_mismatch"):
                build_eligibility(features, root / "output", contract_path=contract, field_dictionary_path=dictionary, expected_features_sha256=expected, expected_rows=1)

    def test_existing_file_or_symlink_output_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            features = root / "features.jsonl"
            features.write_text(json.dumps(feature_row(0)) + "\n", encoding="utf-8")
            contract = root / "contract.json"
            contract.write_text(json.dumps({"schema": "m2.full-evidence-analysis-contract.v1"}), encoding="utf-8")
            dictionary = root / "dictionary.json"
            dictionary.write_text(json.dumps({"fields": {"views": {}}}), encoding="utf-8")
            existing = root / "existing"
            existing.mkdir()
            with self.assertRaisesRegex(EligibilityInputError, "output_directory_must_be_new"):
                build_eligibility(features, existing, contract_path=contract, field_dictionary_path=dictionary, expected_rows=1)
            target = root / "target"
            target.mkdir()
            link = root / "link"
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(EligibilityInputError, "output_directory_must_be_new"):
                build_eligibility(features, link, contract_path=contract, field_dictionary_path=dictionary, expected_rows=1)
            ancestor = root / "ancestor-target"
            ancestor.mkdir()
            ancestor_link = root / "ancestor-link"
            ancestor_link.symlink_to(ancestor, target_is_directory=True)
            with self.assertRaisesRegex(EligibilityInputError, "output_ancestor_symlink_rejected"):
                build_eligibility(features, ancestor_link / "child", contract_path=contract, field_dictionary_path=dictionary, expected_rows=1)
            nested_target = root / "nested-target"
            (nested_target / "nested").mkdir(parents=True)
            nested_link = root / "nested-link"
            nested_link.symlink_to(nested_target, target_is_directory=True)
            with self.assertRaisesRegex(EligibilityInputError, "output_ancestor_symlink_rejected"):
                build_eligibility(features, nested_link / "nested" / "child", contract_path=contract, field_dictionary_path=dictionary, expected_rows=1)


if __name__ == "__main__":
    unittest.main()
