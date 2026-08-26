#!/usr/bin/env python3
"""Fail-closed, provider-disabled transition controller for the Phase 1 batch."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


EXPECTED_RUN_ID = "20260811-phase1-content-batch"
EXPECTED_CASE_ID = "CASE-20260811-PHASE1-BATCH"
EXPECTED_FROM_STATE = "context_bound"
EXPECTED_STATE_SEQUENCE = (
    "sources.allowlisted",
    "research.capabilities_checked",
    "research.collecting",
)
EXPECTED_TO_STATE = "research.collecting"
EXPECTED_ROUTES = ("yt-dlp", "feedparser", "Jina Reader", "targeted lexical read")
EXPECTED_REPAIR_COUNT = 3
EXPECTED_POLICY_PATH = f"runs/{EXPECTED_RUN_ID}/state-policy.json"
EXPECTED_REVIEW_PATH = (
    f"runs/{EXPECTED_RUN_ID}/lanes/atlas/pre-research-governance-rereview-3.json"
)
EXPECTED_REVIEW_ID = "GOV-20260811-PHASE1-PRE-RESEARCH-REREVIEW-03"
EXPECTED_REVIEWER_ROLE = "governance_orchestrator"
EXPECTED_REVIEWER_ACTOR_ID = "atlas_governance"
EXPECTED_OWNER_AUTHORITY_PATH = "HANDOFF_PROMPT.md"
EXPECTED_OWNER_AUTHORITY_SCOPE = (
    "bounded read-only public research through proved routes and local "
    "provider-disabled artifact writes"
)
EXPECTED_DISCOVERY_PATH = f"runs/{EXPECTED_RUN_ID}/discovery-manifest.json"
EXPECTED_OUTPUT_ROOT = f"runs/{EXPECTED_RUN_ID}/lanes/scout/"
EXPECTED_NOT_BEFORE = "2026-08-11T12:00:00+03:00"
CLOCK_SKEW_ALLOWANCE = timedelta(seconds=30)
EXPECTED_PROHIBITED_ACTIONS = (
    "dependency installation or clone",
    "authentication or cookie/session reuse",
    "private or logged-in source access",
    "full third-party video retention",
    "provider/model media API execution",
    "private media or real-person voice/likeness work",
    "Figma mutation",
    "publication or social engagement",
    "deployment or Git remote write",
    "external writeback",
)
REQUIRED_INPUT_PATHS = (
    f"runs/{EXPECTED_RUN_ID}/admission-request.json",
    f"runs/{EXPECTED_RUN_ID}/admission-receipt.json",
    f"runs/{EXPECTED_RUN_ID}/capability-receipt.json",
    f"runs/{EXPECTED_RUN_ID}/research-brief.md",
    f"runs/{EXPECTED_RUN_ID}/source-allowlist.json",
    f"runs/{EXPECTED_RUN_ID}/source-rights-register.md",
    f"runs/{EXPECTED_RUN_ID}/output-contract.md",
    f"runs/{EXPECTED_RUN_ID}/responsibility-register.md",
    f"runs/{EXPECTED_RUN_ID}/task-contracts.md",
    EXPECTED_DISCOVERY_PATH,
    f"runs/{EXPECTED_RUN_ID}/content-case.json",
    "schemas/source-record.schema.json",
    "schemas/local-context-record.schema.json",
    "schemas/source-rights-decision.schema.json",
    "schemas/state-transition-receipt.schema.json",
    "schemas/independent-transition-review.schema.json",
    "templates/video-link-ledger.csv",
    "templates/material-link-ledger.csv",
    "scripts/content_case_state.py",
    "tests/test_content_case_state.py",
)


class TransitionError(ValueError):
    """The transition packet is incomplete, inconsistent, or unauthorized."""


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TransitionError(f"expected an object: {path}")
    return value


def repo_path(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or value.startswith(("/", "\\")):
        raise TransitionError(f"unsafe project-relative path: {value}")
    relative = Path(value)
    if ".." in relative.parts:
        raise TransitionError(f"unsafe project-relative path: {value}")
    resolved = (root / relative).resolve()
    resolved_root = root.resolve()
    if resolved_root not in (resolved, *resolved.parents):
        raise TransitionError(f"path escapes project root: {value}")
    return resolved


def require_exact(label: str, observed: Any, expected: Any) -> None:
    if observed != expected:
        raise TransitionError(f"{label} does not match the authorized value")


def parse_timestamp(label: str, value: Any) -> datetime:
    if not isinstance(value, str):
        raise TransitionError(f"{label} is not a date-time string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise TransitionError(f"{label} is not a valid ISO 8601 date-time") from exc
    if parsed.tzinfo is None:
        raise TransitionError(f"{label} must include an offset")
    return parsed.astimezone(timezone.utc)


def validate_policy(policy: dict[str, Any]) -> None:
    required = {
        "schema",
        "run_id",
        "case_id",
        "from_state",
        "state_sequence",
        "to_state",
        "not_before",
        "review_path",
        "expected_review_id",
        "expected_reviewer_role",
        "expected_reviewer_actor_id",
        "owner_authority_path",
        "owner_authority_scope",
        "allowed_routes",
        "exclusive_output_root",
        "discovery_manifest",
        "input_paths",
        "repair_count",
        "prohibited_actions",
    }
    missing = sorted(required - set(policy))
    extras = sorted(set(policy) - required)
    if missing:
        raise TransitionError(f"policy missing fields: {missing}")
    if extras:
        raise TransitionError(f"policy has unsupported fields: {extras}")

    require_exact("policy schema", policy["schema"], "content-engine.state-policy.v3")
    require_exact("run_id", policy["run_id"], EXPECTED_RUN_ID)
    require_exact("case_id", policy["case_id"], EXPECTED_CASE_ID)
    require_exact("from_state", policy["from_state"], EXPECTED_FROM_STATE)
    require_exact("state_sequence", policy["state_sequence"], list(EXPECTED_STATE_SEQUENCE))
    require_exact("to_state", policy["to_state"], EXPECTED_TO_STATE)
    require_exact("not_before", policy["not_before"], EXPECTED_NOT_BEFORE)
    parse_timestamp("not_before", policy["not_before"])
    require_exact("review_path", policy["review_path"], EXPECTED_REVIEW_PATH)
    require_exact("expected_review_id", policy["expected_review_id"], EXPECTED_REVIEW_ID)
    require_exact(
        "expected_reviewer_role", policy["expected_reviewer_role"], EXPECTED_REVIEWER_ROLE
    )
    require_exact(
        "expected_reviewer_actor_id",
        policy["expected_reviewer_actor_id"],
        EXPECTED_REVIEWER_ACTOR_ID,
    )
    require_exact(
        "owner_authority_path", policy["owner_authority_path"], EXPECTED_OWNER_AUTHORITY_PATH
    )
    require_exact(
        "owner_authority_scope",
        policy["owner_authority_scope"],
        EXPECTED_OWNER_AUTHORITY_SCOPE,
    )
    require_exact("allowed_routes", policy["allowed_routes"], list(EXPECTED_ROUTES))
    require_exact("exclusive_output_root", policy["exclusive_output_root"], EXPECTED_OUTPUT_ROOT)
    require_exact("discovery_manifest", policy["discovery_manifest"], EXPECTED_DISCOVERY_PATH)
    require_exact("input_paths", policy["input_paths"], list(REQUIRED_INPUT_PATHS))
    require_exact("repair_count", policy["repair_count"], EXPECTED_REPAIR_COUNT)
    require_exact(
        "prohibited_actions", policy["prohibited_actions"], list(EXPECTED_PROHIBITED_ACTIONS)
    )


def validate_canonical_state(root: Path, policy: dict[str, Any]) -> dict[str, Any]:
    content_case = load_json(repo_path(root, f"runs/{EXPECTED_RUN_ID}/content-case.json"))
    require_exact("ContentCase case_id", content_case.get("case_id"), EXPECTED_CASE_ID)
    require_exact("ContentCase repair_count", content_case.get("repair_count"), EXPECTED_REPAIR_COUNT)
    require_exact("ContentCase provider_execution", content_case.get("provider_execution"), False)
    require_exact("ContentCase publication_state", content_case.get("publication_state"), "BLOCKED")
    require_exact("ContentCase owner_state", content_case.get("owner_state"), "OWNER_REVIEW_PENDING")
    if "RESP-HAVEN-RIGHTS" not in content_case.get("responsibility_ids", []):
        raise TransitionError("ContentCase is missing the independent rights responsibility")

    request = load_json(repo_path(root, f"runs/{EXPECTED_RUN_ID}/admission-request.json"))
    require_exact("admission request run_id", request.get("run_id"), EXPECTED_RUN_ID)
    require_exact("admission request profile", request.get("profile"), "research")
    require_exact("admission request provider_mode", request.get("provider_mode"), "disabled")
    require_exact("admission request task_invocation", request.get("task_invocation"), False)
    require_exact("admission request provider_execution", request.get("provider_execution"), False)

    receipt = load_json(repo_path(root, f"runs/{EXPECTED_RUN_ID}/admission-receipt.json"))
    require_exact("admission receipt run_id", receipt.get("run_id"), EXPECTED_RUN_ID)
    require_exact("admission receipt profile", receipt.get("profile"), "research")
    require_exact("admission receipt provider_mode", receipt.get("provider_mode"), "disabled")
    require_exact("admission status", receipt.get("admission"), "accepted_planning_only")
    require_exact(
        "admission receipt status",
        receipt.get("admission_receipt", {}).get("status"),
        "valid_for_planning_only",
    )
    require_exact(
        "admission workflow state",
        receipt.get("state_record", {}).get("current_workflow_state"),
        EXPECTED_FROM_STATE,
    )
    require_exact("admission provider execution", receipt.get("approval", {}).get("execution_authorized"), False)
    dispatch = receipt.get("dispatch", {})
    for field in ("external_actions", "task_invoked", "writes"):
        require_exact(f"admission dispatch {field}", dispatch.get(field), False)

    capability = load_json(repo_path(root, f"runs/{EXPECTED_RUN_ID}/capability-receipt.json"))
    require_exact(
        "ContentCase capability receipt",
        content_case.get("capability_receipt_id"),
        capability.get("receipt_id"),
    )
    channels = capability.get("channels", {})
    require_exact("YouTube active backend", channels.get("youtube", {}).get("active_backend"), "yt-dlp")
    require_exact("RSS active backend", channels.get("rss", {}).get("active_backend"), "feedparser")
    require_exact("web active backend", channels.get("web", {}).get("active_backend"), "Jina Reader")
    for channel in ("youtube", "rss", "web"):
        require_exact(f"{channel} capability state", channels.get(channel, {}).get("state"), "READY")
    return content_case


def validate_discovery_and_output(root: Path, policy: dict[str, Any]) -> dict[str, Any]:
    discovery_path = repo_path(root, policy["discovery_manifest"])
    discovery = load_json(discovery_path)
    require_exact("discovery status", discovery.get("status"), "frozen_before_collection")
    require_exact("transport/authority boundary", discovery.get("transport_is_not_authority"), True)
    require_exact("YouTube discovery backend", discovery.get("youtube", {}).get("backend"), "yt-dlp")
    require_exact("RSS discovery backend", discovery.get("rss", {}).get("backend"), "feedparser")
    require_exact("web discovery backend", discovery.get("web", {}).get("backend"), "Jina Reader")
    require_exact("allowed routes", policy["allowed_routes"], list(EXPECTED_ROUTES))

    expected_output = repo_path(root, EXPECTED_OUTPUT_ROOT)
    observed_output = repo_path(root, policy["exclusive_output_root"])
    if observed_output != expected_output or not observed_output.is_dir():
        raise TransitionError("Scout output root is not the exact existing exclusive lane")
    return discovery


def validate_review(
    root: Path,
    policy: dict[str, Any],
    policy_path: Path,
    input_hashes: dict[str, str],
) -> tuple[dict[str, Any], str]:
    review_path = repo_path(root, policy["review_path"])
    if not review_path.is_file():
        raise TransitionError("independent approval review is missing")
    review = load_json(review_path)
    expected_review_fields = {
        "schema",
        "review_id",
        "run_id",
        "case_id",
        "repair_count",
        "reviewer_role",
        "reviewer_actor_id",
        "maker_separation",
        "verdict",
        "reviewed_at",
        "authorized_transition_at",
        "decision",
        "reviewed_hashes",
    }
    missing = sorted(expected_review_fields - set(review))
    extras = sorted(set(review) - expected_review_fields)
    if missing:
        raise TransitionError(f"review missing fields: {missing}")
    if extras:
        raise TransitionError(f"review has unsupported fields: {extras}")
    require_exact("review schema", review.get("schema"), "content-engine.independent-transition-review.v1")
    require_exact("review ID", review.get("review_id"), policy["expected_review_id"])
    require_exact("review run ID", review.get("run_id"), policy["run_id"])
    require_exact("review case ID", review.get("case_id"), policy["case_id"])
    require_exact("review repair count", review.get("repair_count"), policy["repair_count"])
    require_exact("reviewer role", review.get("reviewer_role"), policy["expected_reviewer_role"])
    require_exact(
        "reviewer actor ID", review.get("reviewer_actor_id"), policy["expected_reviewer_actor_id"]
    )
    require_exact("review verdict", review.get("verdict"), "APPROVE")
    if not isinstance(review.get("decision"), str) or not review["decision"].strip():
        raise TransitionError("review decision is empty")
    separation = review.get("maker_separation", {})
    if set(separation) != {"maker_actor_id", "independent_from_maker", "edited_maker_artifacts"}:
        raise TransitionError("review maker_separation fields are not exact")
    require_exact("reviewer independence", separation.get("independent_from_maker"), True)
    require_exact("reviewer maker edits", separation.get("edited_maker_artifacts"), False)
    require_exact("review maker actor", separation.get("maker_actor_id"), "codex_root")

    now = datetime.now(timezone.utc)
    not_before = parse_timestamp("not_before", policy["not_before"])
    reviewed_at = parse_timestamp("reviewed_at", review["reviewed_at"])
    authorized_at = parse_timestamp(
        "authorized_transition_at", review["authorized_transition_at"]
    )
    if now < not_before:
        raise TransitionError("transition issuance is earlier than not_before")
    if reviewed_at > authorized_at:
        raise TransitionError("reviewed_at is after authorized_transition_at")
    if authorized_at < not_before:
        raise TransitionError("authorized_transition_at is earlier than not_before")
    if reviewed_at > now + CLOCK_SKEW_ALLOWANCE:
        raise TransitionError("reviewed_at is future-dated")
    if authorized_at > now + CLOCK_SKEW_ALLOWANCE:
        raise TransitionError("authorized_transition_at is future-dated")

    policy_relative = policy_path.resolve().relative_to(root.resolve()).as_posix()
    expected_reviewed_hashes = dict(input_hashes)
    expected_reviewed_hashes[policy_relative] = sha256_path(policy_path)
    require_exact("reviewed packet hashes", review.get("reviewed_hashes"), expected_reviewed_hashes)
    return review, sha256_path(review_path)


def create_receipt(root: Path, policy_path: Path) -> dict[str, Any]:
    root = root.resolve()
    expected_policy_path = repo_path(root, EXPECTED_POLICY_PATH)
    if policy_path.resolve() != expected_policy_path:
        raise TransitionError("policy must be the canonical run policy")
    policy = load_json(policy_path)
    validate_policy(policy)
    validate_canonical_state(root, policy)
    validate_discovery_and_output(root, policy)

    owner_path = repo_path(root, policy["owner_authority_path"])
    if not owner_path.is_file():
        raise TransitionError("owner authority source is missing")

    input_hashes: dict[str, str] = {}
    for item in policy["input_paths"]:
        path = repo_path(root, item)
        if not path.is_file():
            raise TransitionError(f"required input is missing: {item}")
        input_hashes[item] = sha256_path(path)

    review, review_hash = validate_review(root, policy, policy_path, input_hashes)
    policy_hash = sha256_path(policy_path)
    record: dict[str, Any] = {
        "schema": "content-engine.state-transition.v1",
        "run_id": policy["run_id"],
        "case_id": policy["case_id"],
        "controller": "deterministic_local_state_controller",
        "from_state": policy["from_state"],
        "state_sequence": policy["state_sequence"],
        "to_state": policy["to_state"],
        "transition_at": review["authorized_transition_at"],
        "policy": {"path": EXPECTED_POLICY_PATH, "sha256": policy_hash},
        "review": {
            "path": policy["review_path"],
            "review_id": review["review_id"],
            "reviewer_role": review["reviewer_role"],
            "reviewer_actor_id": review["reviewer_actor_id"],
            "reviewed_at": review["reviewed_at"],
            "authorized_transition_at": review["authorized_transition_at"],
            "verdict": "APPROVE",
            "sha256": review_hash,
        },
        "owner_authority": {
            "path": policy["owner_authority_path"],
            "sha256": sha256_path(owner_path),
            "scope": policy["owner_authority_scope"],
        },
        "allowed_routes": policy["allowed_routes"],
        "exclusive_output_root": policy["exclusive_output_root"],
        "discovery_manifest": policy["discovery_manifest"],
        "input_hashes": input_hashes,
        "repair_count": policy["repair_count"],
        "prohibited_actions": policy["prohibited_actions"],
        "provider_execution": False,
        "external_actions": False,
    }
    material = json.dumps(record, separators=(",", ":"), sort_keys=True).encode("utf-8")
    record["transition_receipt"] = {
        "id": f"sha256:{hashlib.sha256(material).hexdigest()}",
        "status": "valid_for_bounded_local_collection",
    }
    return record


def verify_receipt(root: Path, policy_path: Path, receipt_path: Path) -> None:
    expected = create_receipt(root, policy_path)
    observed = load_json(receipt_path)
    if expected != observed:
        raise TransitionError("receipt does not match current policy, review, authority, or input hashes")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        policy_path = args.policy if args.policy.is_absolute() else root / args.policy
        if args.verify:
            receipt_path = args.verify if args.verify.is_absolute() else root / args.verify
            verify_receipt(root, policy_path, receipt_path)
            print(json.dumps({"verification": "PASS"}, sort_keys=True))
        else:
            print(json.dumps(create_receipt(root, policy_path), indent=2, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, TransitionError, ValueError) as exc:
        print(json.dumps({"transition": "rejected", "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
