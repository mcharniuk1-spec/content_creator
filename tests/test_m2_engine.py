#!/usr/bin/env python3
"""Focused failure and reproducibility tests for the M2 vertical slice."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from m2_engine import engine
from m2_engine import (
    DisabledProviderAdapter,
    M2Error,
    build_studio_package,
    canonical_hash,
    import_golden_cohort,
    import_registered_sources,
    normalize_metric_snapshots,
    robust_score_records,
    run_vertical_slice,
    validate_daily_route_collection,
)

RUN_INPUT = PROJECT_ROOT / "runs" / "20260824-m2-bootstrap-v1"


def load_cohort() -> dict:
    return json.loads((RUN_INPUT / "golden-reference-cohort.json").read_text(encoding="utf-8"))


def metric_snapshot(index: int, views: int | None, **changes: object) -> dict:
    value = {
        "snapshot_id": f"MS-{index:03d}",
        "post_id": f"POST-{index:03d}",
        "creator_id": "CREATOR-001",
        "platform": "youtube",
        "format": "short",
        "duration_bucket": "16-30s",
        "collected_at": f"2026-08-{index + 1:02d}T10:00:00+03:00",
        "provider": "fixture",
        "metric_semantics_version": "fixture.v1",
        "metrics": {"views": views, "likes": None, "comments": None, "shares": None, "reposts": None, "saves": None},
        "raw_payload": {"fixture": index, "views": views},
    }
    value.update(changes)
    return value


class SeedImportTests(unittest.TestCase):
    def test_full_creator_post_cohort_aliases_and_unresolved_parents_round_trip(self) -> None:
        result = import_golden_cohort(load_cohort())
        self.assertEqual(len(result["creator_records"]), 12)
        self.assertEqual(len(result["post_records"]), 14)
        self.assertEqual(len(result["alias_ledger"]), 4)
        self.assertEqual(result["quarantine"], [])
        self.assertEqual(
            [item["reference_id"] for item in result["post_records"] if item["parent_state"] == "GAP_UNRESOLVED"],
            ["PR-013", "PR-014"],
        )
        source = load_cohort()
        source_aliases = {item["reference_id"]: item["aliases"] for item in source["post_references"]}
        roundtrip_aliases = {
            item["reference_id"]: [alias["exact_url"] for alias in item["aliases"]]
            for item in result["post_records"]
        }
        self.assertEqual(roundtrip_aliases, source_aliases)
        self.assertTrue(all(value is None for item in result["post_records"] for value in item["metrics"].values()))

    def test_duplicate_id_and_url_quarantine_without_silent_merge(self) -> None:
        cohort = load_cohort()
        duplicate = copy.deepcopy(cohort["post_references"][0])
        duplicate["reference_id"] = "PR-099"
        cohort["post_references"].append(duplicate)
        duplicate_id = copy.deepcopy(cohort["post_references"][1])
        duplicate_id["exact_url"] = "https://www.instagram.com/reel/unique99/"
        cohort["post_references"].append(duplicate_id)
        result = import_golden_cohort(cohort)
        self.assertEqual(len(result["post_records"]), 14)
        self.assertEqual([item["code"] for item in result["quarantine"]], ["DUPLICATE_SEED", "DUPLICATE_SEED"])

    def test_invalid_seed_is_recoverably_quarantined(self) -> None:
        cohort = load_cohort()
        cohort["creator_references"][0]["exact_url"] = "http://not-allowed.example/"
        result = import_golden_cohort(cohort)
        self.assertEqual(len(result["creator_records"]), 11)
        self.assertEqual(result["quarantine"][0]["code"], "INVALID_URL")
        self.assertTrue(result["quarantine"][0]["recoverable"])

    def test_schema_drift_is_typed(self) -> None:
        cohort = load_cohort()
        cohort["schema"] = "unknown.v9"
        with self.assertRaisesRegex(M2Error, "unsupported golden cohort schema") as caught:
            import_golden_cohort(cohort)
        self.assertEqual(caught.exception.code, "SCHEMA_DRIFT")


class SnapshotAndScoringTests(unittest.TestCase):
    def test_snapshot_hashes_raw_payload_and_preserves_null(self) -> None:
        result = normalize_metric_snapshots([metric_snapshot(0, None)])
        self.assertEqual(result["quarantine"], [])
        snapshot = result["snapshots"][0]
        self.assertIsNone(snapshot["metrics"]["views"])
        self.assertRegex(snapshot["raw_hash"], r"^sha256:[0-9a-f]{64}$")
        self.assertRegex(snapshot["immutable_hash"], r"^sha256:[0-9a-f]{64}$")

    def test_duplicate_and_conflicting_snapshot_identity_are_quarantined(self) -> None:
        original = metric_snapshot(0, 10)
        identical = copy.deepcopy(original)
        conflict = copy.deepcopy(original)
        conflict["metrics"]["views"] = 11
        conflict["raw_payload"]["views"] = 11
        result = normalize_metric_snapshots([original, identical, conflict])
        self.assertEqual(len(result["snapshots"]), 1)
        self.assertEqual([item["code"] for item in result["quarantine"]], ["DUPLICATE_SNAPSHOT", "SNAPSHOT_IMMUTABILITY_CONFLICT"])

    def test_bad_timestamp_and_impossible_metric_quarantine(self) -> None:
        bad_time = metric_snapshot(0, 10, collected_at="yesterday")
        bad_metric = metric_snapshot(1, -1)
        result = normalize_metric_snapshots([bad_time, bad_metric])
        self.assertEqual([item["code"] for item in result["quarantine"]], ["INVALID_TIMESTAMP", "IMPOSSIBLE_METRIC"])

    def test_robust_z_log_formula_is_versioned_reproducible_and_outlier_resistant(self) -> None:
        raw = [metric_snapshot(index, views) for index, views in enumerate([10, 11, 12, 13, 1_000_000])]
        snapshots = normalize_metric_snapshots(raw)["snapshots"]
        first = robust_score_records(snapshots)
        second = robust_score_records(copy.deepcopy(snapshots))
        self.assertEqual(first, second)
        self.assertTrue(all(item["formula_id"] == "m2.robust-z.v1" for item in first))
        self.assertTrue(all(item["status"] == "SCORED" for item in first))
        self.assertGreater(first[-1]["robust_z_views"], 10)
        self.assertAlmostEqual(first[2]["baseline_median"], engine.math.log1p(12))

    def test_insufficient_creator_baseline_and_missing_views_are_explicit_gaps(self) -> None:
        snapshots = normalize_metric_snapshots([metric_snapshot(0, 10), metric_snapshot(1, None)])["snapshots"]
        scores = robust_score_records(snapshots)
        self.assertEqual(scores[0]["gap_reason"], "INSUFFICIENT_BASELINE")
        self.assertEqual(scores[1]["gap_reason"], "MISSING_VIEWS")
        self.assertIsNone(scores[0]["score"])
        self.assertIsNone(scores[1]["score"])


class RegisteredSourceIntegrationTests(unittest.TestCase):
    def test_frozen_twelve_record_registration_preserves_raw_pointer_and_nulls(self) -> None:
        registration = RUN_INPUT / "collection" / "source-registration.jsonl"
        result = import_registered_sources(registration, project_root=PROJECT_ROOT)
        self.assertEqual(len(result["records"]), 12)
        self.assertEqual(len(result["snapshot_inputs"]), 12)
        self.assertEqual(result["quarantine"], [])
        first = result["records"][0]
        self.assertEqual(first["raw_payload_path"], "runs/20260824-m2-bootstrap-v1/collection/YT-M2-01.raw.jsonl")
        self.assertEqual(first["raw_payload_sha256"], "f0efbfed342192243a86c52077e6cb9a47049a6aaf829ccc15bf1a5bc8ceacae")
        self.assertEqual(first["raw_record_line"], 1)
        self.assertEqual(first["registration_line"], 1)
        self.assertEqual(first["metrics"]["views"], 20238)
        self.assertIsNone(first["metrics"]["likes"])
        snapshots = normalize_metric_snapshots(result["snapshot_inputs"])
        self.assertEqual(snapshots["quarantine"], [])
        self.assertEqual(snapshots["snapshots"][0]["raw_payload_path"], first["raw_payload_path"])
        self.assertEqual(snapshots["snapshots"][0]["raw_hash"], first["raw_hash"])
        self.assertIsNone(snapshots["snapshots"][0]["metrics"]["likes"])
        scores = robust_score_records(snapshots["snapshots"])
        self.assertTrue(all(item["status"] == "GAP" for item in scores))
        self.assertTrue(all(item["gap_reason"] == "INSUFFICIENT_BASELINE" for item in scores))
        self.assertTrue(all(item["baseline_count"] < 5 for item in scores))

    def test_registered_raw_hash_mismatch_is_quarantined(self) -> None:
        first_line = (RUN_INPUT / "collection" / "source-registration.jsonl").read_text(encoding="utf-8").splitlines()[0]
        item = json.loads(first_line)
        item["raw_payload_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            registration = Path(directory) / "source-registration.jsonl"
            registration.write_text(json.dumps(item) + "\n", encoding="utf-8")
            result = import_registered_sources(registration, project_root=PROJECT_ROOT)
        self.assertEqual(result["records"], [])
        self.assertEqual(result["quarantine"][0]["code"], "RAW_HASH_MISMATCH")


class FailureBoundaryTests(unittest.TestCase):
    def test_disabled_and_unavailable_provider_is_recoverable(self) -> None:
        result = DisabledProviderAdapter("instagram", "no active backend").fetch()
        self.assertEqual(result.status, "DISABLED")
        self.assertEqual(result.records, ())
        self.assertEqual(result.failure["code"], "CAPABILITY_UNAVAILABLE")
        self.assertTrue(result.failure["recoverable"])

    def test_provider_outage_remains_typed_partial_state(self) -> None:
        result = DisabledProviderAdapter("youtube", "simulated provider outage").fetch()
        self.assertIn("simulated provider outage", result.failure["message"])
        self.assertEqual(result.failure["code"], "CAPABILITY_UNAVAILABLE")

    def test_malformed_and_missing_transcript(self) -> None:
        self.assertEqual(engine.validate_transcript_payload(None)["code"], "TRANSCRIPT_UNAVAILABLE")
        self.assertEqual(engine.validate_transcript_payload({"segments": [{}]})["code"], "MALFORMED_TRANSCRIPT")
        self.assertIsNone(engine.validate_transcript_payload({"segments": [{"text": "bounded fixture"}]}))

    def test_invalid_media_path_and_unsupported_resolve_operation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(engine.validate_media_path("../escape.mov", allowed_root=root)["code"], "INVALID_MEDIA_PATH")
            self.assertEqual(engine.validate_media_path("missing.mov", allowed_root=root)["code"], "INVALID_MEDIA_PATH")
        self.assertEqual(engine.validate_resolve_operation("render_final_video")["code"], "UNSUPPORTED_RESOLVE_OPERATION")
        self.assertIsNone(engine.validate_resolve_operation("plan_timeline"))


class RouteAndStudioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evidence = [
            {"source_id": "SRC-M2-ADMISSION", "evidence_id": "EVID-M2-ADMISSION"},
            {"source_id": "SRC-M2-CAPABILITY", "evidence_id": "EVID-M2-CAPABILITY"},
            {"source_id": "SRC-M2-OUTPUT-CONTRACT", "evidence_id": "EVID-M2-OUTPUT-CONTRACT"},
            {"source_id": "SRC-M2-NORMALIZED-COHORT", "evidence_id": "EVID-M2-NORMALIZED-COHORT"},
            {"source_id": "SRC-M2-COVERAGE", "evidence_id": "EVID-M2-COVERAGE"},
            {"source_id": "SRC-M2-FAILURE-REPORT", "evidence_id": "EVID-M2-FAILURE-REPORT"},
        ]
        self.artifact_hashes = {}
        for index, item in enumerate(self.evidence):
            item.update({"path_root": "output_dir", "path": f"fixture-{index}.json", "sha256": canonical_hash({"fixture": index}), "label": "FACT", "scope": "first_party_run_evidence"})
            self.artifact_hashes[f"output_dir:fixture-{index}.json"] = item["sha256"]
        self.registry = {"schema": "m2.first-party-evidence-registry.v1", "registry_id": "FIXTURE-EVIDENCE", "path_roots": {"run_input": ".", "output_dir": "burn-in/"}, "records": self.evidence}
        self.routes = engine._default_route_collection(self.evidence)

    def test_complete_daily_routes_validate_and_build_provider_neutral_package(self) -> None:
        self.assertEqual(validate_daily_route_collection(self.routes, self.registry, self.artifact_hashes), [])
        package = build_studio_package(self.routes, self.registry, self.artifact_hashes)
        self.assertEqual(set(package), {
            "script-package.json", "shot-manifest.json", "asset-manifest.json", "founder-shoot-manifest.json",
            "edit-manifest.json", "platform-package.json", "qc-report.json", "transformation-statement.md",
        })
        shots = package["shot-manifest.json"]["shots"]
        self.assertEqual(len(shots), 12)
        self.assertEqual(shots[0]["start_ms"], 0)
        self.assertEqual(shots[-1]["end_ms"], package["shot-manifest.json"]["duration_ms"])
        self.assertTrue(all(left["end_ms"] == right["start_ms"] for left, right in zip(shots, shots[1:])))
        self.assertTrue(all(item["end_ms"] - item["start_ms"] == 2000 for item in shots))
        required_shot_fields = {
            "narrative_function", "spoken_line", "visual_objective", "framing", "motion",
            "screen_or_diagram_content", "on_screen_text", "transition", "audio_cue",
            "asset_ids", "evidence_ids", "source_state", "generation_state", "fallback", "qc",
        }
        self.assertTrue(all(required_shot_fields.issubset(item) for item in shots))
        for left, right in zip(shots[::2], shots[1::2]):
            self.assertEqual(left["spoken_line"], right["spoken_line"])
            self.assertNotEqual(left["visual_objective"], right["visual_objective"])
        self.assertTrue(all(item["generation_state"] == "NOT_RUN" for item in shots))
        script = package["script-package.json"]
        self.assertEqual(len(script["segments"]), 6)
        self.assertTrue(script["full_script"])
        self.assertGreater(script["reading_speed_wpm"], 0)
        self.assertTrue(all(script[field] for field in ("cta", "title", "cover_text", "caption", "pinned_comment_strategy")))
        claim_evidence = [tuple(item["evidence_ids"]) for item in script["claim_map"]]
        self.assertGreater(len(set(claim_evidence)), 1)
        self.assertEqual(script["claim_map"][0]["evidence_ids"], ["EVID-M2-CAPABILITY"])
        self.assertEqual(script["claim_map"][3]["evidence_ids"], ["EVID-M2-FAILURE-REPORT"])
        self.assertEqual(package["edit-manifest.json"]["resolve_mutation_state"], "BLOCKED_APPROVAL")
        self.assertEqual(package["platform-package.json"]["publication_state"], "BLOCKED_APPROVAL")
        self.assertEqual(set(package["platform-package.json"]["packages"]), {"instagram_reels", "tiktok", "youtube_shorts"})
        self.assertIn("tiktok", self.routes["routes"][0]["platforms"])
        self.assertEqual(package["qc-report.json"]["reviewer"], None)

    def test_missing_evidence_prohibited_copy_and_m2_proof_are_rejected(self) -> None:
        for field in ("source_ids", "evidence_ids", "claim_evidence_map", "audience", "job", "pain", "why_now", "market_context", "prohibited_copy", "m2_contribution", "m2_proof", "strategic_placement", "production_complexity"):
            routes = copy.deepcopy(self.routes)
            routes["routes"][0][field] = [] if field in {"source_ids", "evidence_ids", "prohibited_copy"} else None
            failures = validate_daily_route_collection(routes, self.registry, self.artifact_hashes)
            self.assertTrue(any(item["code"] == "ROUTE_FIELD_MISSING" and field in item["message"] for item in failures), field)

    def test_invalid_route_blocks_studio(self) -> None:
        routes = copy.deepcopy(self.routes)
        routes["routes"][2]["m2_proof"] = ""
        with self.assertRaises(M2Error) as caught:
            build_studio_package(routes, self.registry, self.artifact_hashes)
        self.assertEqual(caught.exception.code, "DAILY_ROUTE_INVALID")

    def test_evidence_registry_unknown_pair_path_and_hash_fail_closed(self) -> None:
        no_registry = validate_daily_route_collection(self.routes)
        self.assertTrue(any(item["code"] == "EVIDENCE_REGISTRY_MISSING" for item in no_registry))

        unknown = copy.deepcopy(self.routes)
        unknown["routes"][0]["source_ids"][0] = "SRC-UNKNOWN"
        failures = validate_daily_route_collection(unknown, self.registry, self.artifact_hashes)
        self.assertTrue(any(item["code"] == "SOURCE_ID_UNRESOLVED" for item in failures))

        mismatched = copy.deepcopy(self.routes)
        mismatched["routes"][0]["evidence_ids"].remove("EVID-M2-CAPABILITY")
        failures = validate_daily_route_collection(mismatched, self.registry, self.artifact_hashes)
        self.assertTrue(any(item["code"] == "SOURCE_EVIDENCE_PAIR_MISMATCH" for item in failures))

        bad_path = copy.deepcopy(self.registry)
        bad_path["records"][0]["path"] = "missing.json"
        failures = validate_daily_route_collection(self.routes, bad_path, self.artifact_hashes)
        self.assertTrue(any(item["code"] == "EVIDENCE_PATH_UNRESOLVED" for item in failures))

        bad_hash = copy.deepcopy(self.registry)
        bad_hash["records"][0]["sha256"] = "sha256:" + "0" * 64
        failures = validate_daily_route_collection(self.routes, bad_hash, self.artifact_hashes)
        self.assertTrue(any(item["code"] == "EVIDENCE_HASH_MISMATCH" for item in failures))

        package = build_studio_package(self.routes, self.registry, self.artifact_hashes)
        broken_package = copy.deepcopy(package)
        broken_package["shot-manifest.json"]["shots"][0]["evidence_ids"] = ["EVID-UNKNOWN"]
        failures = engine.validate_studio_evidence_links(broken_package, self.registry, self.artifact_hashes)
        self.assertTrue(any(item["code"] == "STUDIO_EVIDENCE_UNRESOLVED" for item in failures))


class DurableSnapshotPersistenceTests(unittest.TestCase):
    def test_same_identity_metric_change_is_rejected_and_prior_bytes_remain(self) -> None:
        original = normalize_metric_snapshots([metric_snapshot(0, 10)])["snapshots"]
        changed = normalize_metric_snapshots([metric_snapshot(0, 11)])["snapshots"]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "metric-snapshots.jsonl"
            created = engine.persist_metric_snapshots(target, original)
            prior = target.read_bytes()
            self.assertEqual(created["status"], "CREATED")
            unchanged = engine.persist_metric_snapshots(target, original)
            self.assertEqual(unchanged["status"], "UNCHANGED")
            self.assertEqual(target.read_bytes(), prior)
            with self.assertRaises(M2Error) as caught:
                engine.persist_metric_snapshots(target, changed)
            self.assertEqual(caught.exception.code, "SNAPSHOT_PERSISTENCE_CONFLICT")
            self.assertEqual(target.read_bytes(), prior)


class VerticalSliceTests(unittest.TestCase):
    def test_deterministic_rerun_and_required_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = run_vertical_slice(RUN_INPUT, Path(first_dir))
            second = run_vertical_slice(RUN_INPUT, Path(second_dir))
            self.assertEqual(first, second)
            self.assertEqual(first["content_hash"], second["content_hash"])
            required = {
                "golden-reference-cohort.normalized.json", "source-records.jsonl", "metric-snapshots.jsonl",
                "quarantine.jsonl", "score-decompositions.jsonl", "dataset-manifest.json", "coverage-report.json",
                "failure-test-report.json", "trace.jsonl", "daily-route-collection.json", "manifest.json",
                "first-party-evidence-registry.json",
                "studio-package/script-package.json", "studio-package/shot-manifest.json", "studio-package/asset-manifest.json",
                "studio-package/founder-shoot-manifest.json", "studio-package/edit-manifest.json",
                "studio-package/platform-package.json", "studio-package/transformation-statement.md", "studio-package/qc-report.json",
            }
            self.assertTrue(all((Path(first_dir) / name).is_file() for name in required))
            registry = json.loads((Path(first_dir) / "first-party-evidence-registry.json").read_text(encoding="utf-8"))
            self.assertEqual(len(registry["records"]), 6)
            for record in registry["records"]:
                root = RUN_INPUT if record["path_root"] == "run_input" else Path(first_dir)
                self.assertEqual(engine.file_hash(root / record["path"]), record["sha256"])
            self.assertTrue(any(item["path"] == "first-party-evidence-registry.json" for item in first["artifacts"]))
            coverage = json.loads((Path(first_dir) / "coverage-report.json").read_text(encoding="utf-8"))
            self.assertEqual(coverage["observed"]["total_seeds"], 26)
            self.assertEqual(coverage["observed"]["collected_source_records"], 12)
            self.assertEqual(coverage["observed"]["total_source_records"], 38)
            self.assertEqual(coverage["observed"]["collected_metric_snapshots"], 12)
            self.assertEqual(coverage["observed"]["aliases"], 4)
            self.assertEqual(coverage["observed"]["unresolved_parent_links"], 2)
            self.assertEqual(coverage["provider_mode"], "disabled")
            self.assertEqual(coverage["cost_usd"], 0)
            dataset = json.loads((Path(first_dir) / "dataset-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(dataset["record_counts"]["total_seeds"], 26)
            self.assertEqual(dataset["record_counts"]["collected_source_records"], 12)
            self.assertEqual(dataset["registered_source_input"]["path"], "collection/source-registration.jsonl")
            score_rows = [json.loads(line) for line in (Path(first_dir) / "score-decompositions.jsonl").read_text(encoding="utf-8").splitlines()]
            collected_scores = [item for item in score_rows if str(item["snapshot_id"]).startswith("MS-SRC-YT-M2")]
            self.assertEqual(len(collected_scores), 12)
            self.assertTrue(all(item["status"] == "GAP" and item["baseline_count"] < 5 for item in collected_scores))
            routes = json.loads((Path(first_dir) / "daily-route-collection.json").read_text(encoding="utf-8"))
            self.assertTrue(all(source_id.startswith("SRC-M2-") for route in routes["routes"] for source_id in route["source_ids"]))
            failures = json.loads((Path(first_dir) / "failure-test-report.json").read_text(encoding="utf-8"))
            codes = {item["code"] for item in failures["failures"]}
            self.assertTrue({"MALFORMED_PAYLOAD", "MALFORMED_TRANSCRIPT", "INVALID_MEDIA_PATH", "UNSUPPORTED_RESOLVE_OPERATION", "CAPABILITY_UNAVAILABLE"}.issubset(codes))

    def test_cli_requires_explicit_output_and_writes_only_there(self) -> None:
        script = PROJECT_ROOT / "scripts" / "m2_bootstrap.py"
        missing = subprocess.run([sys.executable, str(script), "--input-dir", str(RUN_INPUT)], capture_output=True, text=True, check=False)
        self.assertNotEqual(missing.returncode, 0)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "explicit-output"
            completed = subprocess.run([sys.executable, str(script), "--input-dir", str(RUN_INPUT), "--output-dir", str(target)], capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((target / "manifest.json").is_file())
            self.assertEqual(json.loads(completed.stdout)["status"], "COMPLETE_WITH_EXPLICIT_GAPS")

    def test_canonical_hash_is_order_independent_for_objects(self) -> None:
        self.assertEqual(canonical_hash({"a": 1, "b": 2}), canonical_hash({"b": 2, "a": 1}))


if __name__ == "__main__":
    unittest.main()
