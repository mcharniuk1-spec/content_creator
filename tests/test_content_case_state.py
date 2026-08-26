#!/usr/bin/env python3
"""Negative fixtures for the Phase 1 state-transition controller."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "content_case_state.py"
SPEC = importlib.util.spec_from_file_location("content_case_state", MODULE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import guard
    raise RuntimeError("could not load content_case_state")
controller = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(controller)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class PacketFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.policy_path = root / controller.EXPECTED_POLICY_PATH
        self.review_path = root / controller.EXPECTED_REVIEW_PATH
        (root / controller.EXPECTED_OUTPUT_ROOT).mkdir(parents=True, exist_ok=True)
        (root / "HANDOFF_PROMPT.md").write_text("owner-authorized bounded test\n", encoding="utf-8")

        for relative in controller.REQUIRED_INPUT_PATHS:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix == ".json":
                write_json(path, {})
            else:
                path.write_text(f"fixture for {relative}\n", encoding="utf-8")

        run = controller.EXPECTED_RUN_ID
        write_json(
            root / f"runs/{run}/admission-request.json",
            {
                "run_id": run,
                "profile": "research",
                "provider_mode": "disabled",
                "task_invocation": False,
                "provider_execution": False,
            },
        )
        write_json(
            root / f"runs/{run}/admission-receipt.json",
            {
                "run_id": run,
                "profile": "research",
                "provider_mode": "disabled",
                "admission": "accepted_planning_only",
                "admission_receipt": {"status": "valid_for_planning_only"},
                "approval": {"execution_authorized": False},
                "state_record": {"current_workflow_state": "context_bound"},
                "dispatch": {"external_actions": False, "task_invoked": False, "writes": False},
            },
        )
        write_json(
            root / f"runs/{run}/capability-receipt.json",
            {
                "receipt_id": "agent-reach-20260811-phase1-content-batch",
                "channels": {
                    "youtube": {"state": "READY", "active_backend": "yt-dlp"},
                    "rss": {"state": "READY", "active_backend": "feedparser"},
                    "web": {"state": "READY", "active_backend": "Jina Reader"},
                },
            },
        )
        write_json(
            root / controller.EXPECTED_DISCOVERY_PATH,
            {
                "status": "frozen_before_collection",
                "transport_is_not_authority": True,
                "youtube": {"backend": "yt-dlp"},
                "rss": {"backend": "feedparser"},
                "web": {"backend": "Jina Reader"},
            },
        )
        write_json(
            root / f"runs/{run}/content-case.json",
            {
                "case_id": controller.EXPECTED_CASE_ID,
                "capability_receipt_id": "agent-reach-20260811-phase1-content-batch",
                "repair_count": controller.EXPECTED_REPAIR_COUNT,
                "provider_execution": False,
                "publication_state": "BLOCKED",
                "owner_state": "OWNER_REVIEW_PENDING",
                "responsibility_ids": ["RESP-HAVEN-RIGHTS"],
            },
        )
        self.policy = {
            "schema": "content-engine.state-policy.v3",
            "run_id": run,
            "case_id": controller.EXPECTED_CASE_ID,
            "from_state": controller.EXPECTED_FROM_STATE,
            "state_sequence": list(controller.EXPECTED_STATE_SEQUENCE),
            "to_state": controller.EXPECTED_TO_STATE,
            "not_before": controller.EXPECTED_NOT_BEFORE,
            "review_path": controller.EXPECTED_REVIEW_PATH,
            "expected_review_id": controller.EXPECTED_REVIEW_ID,
            "expected_reviewer_role": controller.EXPECTED_REVIEWER_ROLE,
            "expected_reviewer_actor_id": controller.EXPECTED_REVIEWER_ACTOR_ID,
            "owner_authority_path": controller.EXPECTED_OWNER_AUTHORITY_PATH,
            "owner_authority_scope": controller.EXPECTED_OWNER_AUTHORITY_SCOPE,
            "allowed_routes": list(controller.EXPECTED_ROUTES),
            "exclusive_output_root": controller.EXPECTED_OUTPUT_ROOT,
            "discovery_manifest": controller.EXPECTED_DISCOVERY_PATH,
            "input_paths": list(controller.REQUIRED_INPUT_PATHS),
            "repair_count": controller.EXPECTED_REPAIR_COUNT,
            "prohibited_actions": list(controller.EXPECTED_PROHIBITED_ACTIONS),
        }
        self.write_policy_and_approval()

    def write_policy_and_approval(self, verdict: str = "APPROVE") -> None:
        write_json(self.policy_path, self.policy)
        reviewed_hashes = {
            relative: controller.sha256_path(self.root / relative)
            for relative in controller.REQUIRED_INPUT_PATHS
        }
        reviewed_hashes[controller.EXPECTED_POLICY_PATH] = controller.sha256_path(self.policy_path)
        reviewed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        write_json(
            self.review_path,
            {
                "schema": "content-engine.independent-transition-review.v1",
                "review_id": controller.EXPECTED_REVIEW_ID,
                "run_id": controller.EXPECTED_RUN_ID,
                "case_id": controller.EXPECTED_CASE_ID,
                "repair_count": controller.EXPECTED_REPAIR_COUNT,
                "reviewer_role": controller.EXPECTED_REVIEWER_ROLE,
                "reviewer_actor_id": controller.EXPECTED_REVIEWER_ACTOR_ID,
                "maker_separation": {
                    "maker_actor_id": "codex_root",
                    "independent_from_maker": True,
                    "edited_maker_artifacts": False,
                },
                "verdict": verdict,
                "reviewed_at": reviewed_at,
                "authorized_transition_at": reviewed_at,
                "decision": "fixture decision",
                "reviewed_hashes": reviewed_hashes,
            },
        )


class StateControllerTests(unittest.TestCase):
    def with_fixture(self, callback: Callable[[PacketFixture], None]) -> None:
        with tempfile.TemporaryDirectory() as directory:
            callback(PacketFixture(Path(directory)))

    def test_valid_packet_creates_and_verifies_receipt(self) -> None:
        def check(fixture: PacketFixture) -> None:
            receipt = controller.create_receipt(fixture.root, fixture.policy_path)
            self.assertEqual(receipt["to_state"], "research.collecting")
            receipt_path = fixture.root / "receipt.json"
            write_json(receipt_path, receipt)
            controller.verify_receipt(fixture.root, fixture.policy_path, receipt_path)

        self.with_fixture(check)

    def test_semantically_malformed_policies_fail_closed(self) -> None:
        mutations: dict[str, Callable[[PacketFixture], None]] = {
            "wrong_from_state": lambda f: f.policy.__setitem__("from_state", "complete"),
            "wrong_sequence": lambda f: f.policy.__setitem__(
                "state_sequence",
                ["sources.allowlisted", "publication.approval_interrupt", "research.collecting"],
            ),
            "provider_route": lambda f: f.policy.__setitem__("allowed_routes", ["provider-paid-route"]),
            "escaping_output": lambda f: f.policy.__setitem__("exclusive_output_root", "../outside-scout"),
            "other_output": lambda f: f.policy.__setitem__(
                "exclusive_output_root", f"runs/{controller.EXPECTED_RUN_ID}/lanes/other/"
            ),
            "wrong_run": lambda f: f.policy.__setitem__("run_id", "wrong-run"),
            "wrong_case": lambda f: f.policy.__setitem__("case_id", "CASE-WRONG"),
            "wrong_repair": lambda f: f.policy.__setitem__("repair_count", 1),
            "future_not_before": lambda f: f.policy.__setitem__(
                "not_before", (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                fixture = PacketFixture(Path(directory))
                mutate(fixture)
                fixture.write_policy_and_approval()
                with self.assertRaises(controller.TransitionError):
                    controller.create_receipt(fixture.root, fixture.policy_path)

    def test_canonical_artifact_mismatches_fail_closed(self) -> None:
        def check(fixture: PacketFixture) -> None:
            case_path = fixture.root / f"runs/{controller.EXPECTED_RUN_ID}/content-case.json"
            case = controller.load_json(case_path)
            case["repair_count"] = 1
            write_json(case_path, case)
            fixture.write_policy_and_approval()
            with self.assertRaises(controller.TransitionError):
                controller.create_receipt(fixture.root, fixture.policy_path)

        self.with_fixture(check)

    def test_inactive_or_undeclared_backends_fail_closed(self) -> None:
        def check(fixture: PacketFixture) -> None:
            capability_path = (
                fixture.root / f"runs/{controller.EXPECTED_RUN_ID}/capability-receipt.json"
            )
            capability = controller.load_json(capability_path)
            capability["channels"]["youtube"]["active_backend"] = "provider-paid-route"
            write_json(capability_path, capability)
            fixture.write_policy_and_approval()
            with self.assertRaises(controller.TransitionError):
                controller.create_receipt(fixture.root, fixture.policy_path)

        self.with_fixture(check)

    def test_review_identity_and_verdict_fail_closed(self) -> None:
        def check(fixture: PacketFixture) -> None:
            review = controller.load_json(fixture.review_path)
            review["reviewer_actor_id"] = "maker"
            write_json(fixture.review_path, review)
            with self.assertRaises(controller.TransitionError):
                controller.create_receipt(fixture.root, fixture.policy_path)
            fixture.write_policy_and_approval(verdict="REVISE")
            with self.assertRaises(controller.TransitionError):
                controller.create_receipt(fixture.root, fixture.policy_path)

        self.with_fixture(check)

    def test_reviewed_hash_mismatch_fails_closed(self) -> None:
        def check(fixture: PacketFixture) -> None:
            target = fixture.root / f"runs/{controller.EXPECTED_RUN_ID}/research-brief.md"
            target.write_text("tampered after review\n", encoding="utf-8")
            with self.assertRaises(controller.TransitionError):
                controller.create_receipt(fixture.root, fixture.policy_path)

        self.with_fixture(check)

    def test_future_authorization_and_review_after_transition_fail_closed(self) -> None:
        def check(fixture: PacketFixture) -> None:
            review = controller.load_json(fixture.review_path)
            future = datetime.now(timezone.utc) + timedelta(hours=1)
            review["reviewed_at"] = future.isoformat(timespec="seconds")
            review["authorized_transition_at"] = future.isoformat(timespec="seconds")
            write_json(fixture.review_path, review)
            with self.assertRaises(controller.TransitionError):
                controller.create_receipt(fixture.root, fixture.policy_path)

            fixture.write_policy_and_approval()
            review = controller.load_json(fixture.review_path)
            reviewed = datetime.now(timezone.utc)
            review["reviewed_at"] = reviewed.isoformat(timespec="seconds")
            review["authorized_transition_at"] = (reviewed - timedelta(seconds=1)).isoformat(
                timespec="seconds"
            )
            write_json(fixture.review_path, review)
            with self.assertRaises(controller.TransitionError):
                controller.create_receipt(fixture.root, fixture.policy_path)

        self.with_fixture(check)

    def test_tampered_receipt_fails_verification(self) -> None:
        def check(fixture: PacketFixture) -> None:
            receipt = controller.create_receipt(fixture.root, fixture.policy_path)
            receipt["transition_receipt"]["id"] = "sha256:" + ("0" * 64)
            receipt_path = fixture.root / "tampered-receipt.json"
            write_json(receipt_path, receipt)
            with self.assertRaises(controller.TransitionError):
                controller.verify_receipt(fixture.root, fixture.policy_path, receipt_path)

        self.with_fixture(check)


if __name__ == "__main__":
    unittest.main()
