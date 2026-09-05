import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from m2_orchestrator.policy import BY_ID, STAGES, dependencies
from m2_orchestrator.state import Controller, StateError, digest, validate_config


def config():
    return {"schema": "m2.run-config.v1", "platforms": ["instagram_reels"], "mode": "replay",
            "hikerapi_execution": False, "provider_execution": False,
            "source_manifest": [{"source_id": "fixture", "sha256": "1" * 64}],
            "actors": {"maker": list({s.role for s in STAGES if not s.reviewer}),
                       "reviewer": [s.role for s in STAGES if s.reviewer], "owner": ["owner"]}}


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.c = Controller(self.root)
        self.config = config()
        self.c.init("fixture", self.config)
        (self.root / "artifact.json").write_text('{"fixture":true}')

    def complete(self, stage, actor="maker"):
        b = self.c.begin(stage, actor)
        artifact = self.review_artifact(stage, b) if BY_ID[stage].reviewer else "artifact.json"
        return self.c.finish(stage, b["token"], [artifact], "PASS")

    def review_artifact(self, stage, begun):
        name = stage + ".json"
        (self.root / name).write_text(json.dumps({"schema": "m2.independent-review.v1", "stage": stage,
            "run_id": "fixture", "config_hash": digest(self.config), "reviewer": "reviewer",
            "subjects": {p["stage"]: p["receipt_hash"] for p in begun["parents"]},
            "verdict": "APPROVED", "scope": "synthetic fixture only", "limitations": []}))
        return name

    def ready_to(self, target):
        for s in STAGES:
            if s.id == target:
                return
            if s.gate:
                continue
            self.complete(s.id, "reviewer" if s.reviewer else "maker")

    def test_frozen_config_idempotence_and_change_rejected(self):
        self.assertEqual(self.c.init("fixture", self.config), digest(self.config))
        changed = dict(self.config, mode="incremental")
        with self.assertRaisesRegex(StateError, "MISMATCH"):
            self.c.init("fixture", changed)

    def test_retired_platform_and_paid_collection_rejected(self):
        for field, value in [("platforms", ["youtube"]), ("hikerapi_execution", True), ("provider_execution", True)]:
            with self.subTest(field=field), self.assertRaises(StateError):
                validate_config(dict(self.config, **{field: value}))

    def test_dependency_gate_actor_and_duplicate_start(self):
        with self.assertRaisesRegex(StateError, "DEPENDENCY"):
            self.c.begin("inventory", "maker")
        with self.assertRaisesRegex(StateError, "ACTOR"):
            self.c.begin("admit", "reviewer")
        b = self.c.begin("admit", "maker")
        with self.assertRaisesRegex(StateError, "RUNNING"):
            self.c.begin("admit", "maker")
        with self.assertRaisesRegex(StateError, "STALE"):
            self.c.finish("admit", "wrong", ["artifact.json"], "PASS")
        self.c.finish("admit", b["token"], ["artifact.json"], "PASS")
        self.assertTrue(self.c.begin("admit", "maker")["cached"])

    def test_missing_mutated_and_outside_artifacts_fail(self):
        b = self.c.begin("admit", "maker")
        for path in ["missing.json", "../outside", str(self.root / "artifact.json")]:
            with self.assertRaises(StateError):
                self.c.finish("admit", b["token"], [path], "PASS")
        self.c.finish("admit", b["token"], ["artifact.json"], "PASS")
        (self.root / "artifact.json").write_text('{"fixture":false}')
        with self.assertRaisesRegex(StateError, "HASH_CHANGED"):
            self.c.begin("freeze_config", "maker")
        with self.assertRaises(StateError):
            self.c.verify()

    def test_expired_lease_recovery_fences_old_worker(self):
        b = self.c.begin("admit", "maker", lease_seconds=1)
        with self.assertRaisesRegex(StateError, "NOT_EXPIRED"):
            self.c.recover("admit")
        with patch("m2_orchestrator.state.time.time", return_value=time.time()+2):
            self.c.recover("admit")
        fresh = self.c.begin("admit", "maker")
        with self.assertRaisesRegex(StateError, "STALE"):
            self.c.finish("admit", b["token"], ["artifact.json"], "PASS")
        self.c.finish("admit", fresh["token"], ["artifact.json"], "PASS")

    def test_repeated_failure_stops_and_error_redaction(self):
        for _ in range(2):
            b = self.c.begin("admit", "maker")
            self.c.fail("admit", b["token"], "MISSING_EVIDENCE")
        with self.assertRaisesRegex(StateError, "REPEATED_FAILURE"):
            self.c.begin("admit", "maker")

    def test_event_chain_and_append_only_trigger(self):
        self.complete("admit")
        self.assertEqual(self.c.verify()["events"], 3)
        c = sqlite3.connect(self.c.db)
        with self.assertRaises(sqlite3.IntegrityError):
            c.execute("DELETE FROM events")
        c.close()

    def test_maker_reviewer_separation(self):
        self.ready_to("review_signal")
        with self.assertRaisesRegex(StateError, "ACTOR"):
            self.c.begin("review_signal", "maker")
        self.complete("review_signal", "reviewer")

    def test_exact_approval_expiry_and_revocation(self):
        self.ready_to("project_notion")
        with self.assertRaisesRegex(StateError, "APPROVAL"):
            self.c.begin("project_notion", "maker")
        self.c.approve("notion_write", "a" * 64, "owner", time.time()+60)
        with self.assertRaisesRegex(StateError, "APPROVAL"):
            self.c.begin("project_notion", "maker", "b" * 64)
        self.c.approve("notion_write", "a" * 64, "owner", time.time()+60, revoke=True)
        with self.assertRaisesRegex(StateError, "APPROVAL"):
            self.c.begin("project_notion", "maker", "a" * 64)

    def test_review_requires_exact_subject_and_verdict(self):
        self.ready_to("review_signal")
        b = self.c.begin("review_signal", "reviewer")
        with self.assertRaisesRegex(StateError, "STRUCTURED_REVIEW"):
            self.c.finish("review_signal", b["token"], ["artifact.json"], "PASS")
        path = self.review_artifact("review_signal", b)
        value = json.loads((self.root / path).read_text())
        value["subjects"] = {}
        (self.root / path).write_text(json.dumps(value))
        with self.assertRaisesRegex(StateError, "SUBJECT_MISMATCH"):
            self.c.finish("review_signal", b["token"], [path], "PASS")

    def test_approval_revoked_after_start_cannot_finish(self):
        self.ready_to("project_notion")
        self.c.approve("notion_write", "a" * 64, "owner", time.time()+60)
        b = self.c.begin("project_notion", "maker", "a" * 64)
        self.c.approve("notion_write", "a" * 64, "owner", time.time()+60, revoke=True)
        with self.assertRaisesRegex(StateError, "APPROVAL"):
            self.c.finish("project_notion", b["token"], ["artifact.json"], "PASS")

    def test_changed_parent_after_start_cannot_finish(self):
        self.complete("admit")
        b = self.c.begin("freeze_config", "maker")
        (self.root / "artifact.json").write_text('{"fixture":false}')
        with self.assertRaisesRegex(StateError, "HASH_CHANGED"):
            self.c.finish("freeze_config", b["token"], ["artifact.json"], "PASS")

    def test_review_limitations_cannot_be_dropped(self):
        self.ready_to("review_signal")
        b = self.c.begin("review_signal", "reviewer")
        path = self.review_artifact("review_signal", b)
        value = json.loads((self.root / path).read_text())
        value.update(verdict="APPROVED_WITH_LIMITATIONS", limitations=["Missing source media"])
        (self.root / path).write_text(json.dumps(value))
        with self.assertRaisesRegex(StateError, "LIMITATIONS_MUST_PROPAGATE"):
            self.c.finish("review_signal", b["token"], [path], "PASS_WITH_LIMITATIONS", ["Some limits"])
        self.c.finish("review_signal", b["token"], [path], "PASS_WITH_LIMITATIONS", value["limitations"])

    def test_implementation_upgrade_cannot_reuse_cache(self):
        self.complete("admit")
        with patch("m2_orchestrator.state.runtime_hash", return_value="changed"):
            with self.assertRaisesRegex(StateError, "IMPLEMENTATION_CHANGED"):
                self.c.begin("admit", "maker")

    def test_transitive_maker_cannot_review_through_other_actor(self):
        config2 = config()
        config2["actors"]["maker"].append("signal_reviewer")
        config2["actors"]["aggregator"] = ["quantitative_analyst"]
        other = Controller(self.root / "separate")
        other.init("fixture2", config2)
        (other.root / "artifact.json").write_text('{"fixture":true}')
        for stage in STAGES:
            if stage.id == "review_signal":
                break
            actor = "aggregator" if stage.id == "account_aggregate" else "maker"
            b = other.begin(stage.id, actor)
            other.finish(stage.id, b["token"], ["artifact.json"], "PASS")
        with self.assertRaisesRegex(StateError, "MAKER_CANNOT_REVIEW"):
            other.begin("review_signal", "maker")

    def test_transitive_artifact_change_blocks_cached_and_new_stage(self):
        self.complete("admit")
        (self.root / "config-output.json").write_text('{"config":true}')
        b = self.c.begin("freeze_config", "maker")
        self.c.finish("freeze_config", b["token"], ["config-output.json"], "PASS")
        b = self.c.begin("inventory", "maker")
        (self.root / "inventory-output.json").write_text('{"inventory":true}')
        self.c.finish("inventory", b["token"], ["inventory-output.json"], "PASS")
        (self.root / "artifact.json").write_text('{"fixture":false}')
        for stage in ["inventory", "collect_or_replay"]:
            with self.assertRaisesRegex(StateError, "HASH_CHANGED"):
                self.c.begin(stage, "maker")

    def test_optional_generation_requires_review_only_when_used(self):
        self.assertNotIn("review_assets", dependencies("render_remotion", self.config))
        self.assertIn("review_assets", dependencies("render_remotion", dict(self.config, production={"requires_generation": True})))

    def test_trace_contains_frozen_config_and_actor(self):
        self.complete("admit")
        trace = self.c.trace()
        self.assertEqual(trace[0]["config_hash"], digest(self.config))
        self.assertEqual(trace[-1]["receipt"]["actor"], "maker")


if __name__ == "__main__":
    unittest.main()
