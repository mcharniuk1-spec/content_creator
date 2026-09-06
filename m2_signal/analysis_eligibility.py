"""Read-only population and missingness gates for M2 statistical analysis.

This module consumes one frozen ``m2.corpus-features.v1`` JSONL checkpoint.
It preserves every input row, classifies each action outcome independently,
and reports evidence intersections without fitting a model or changing the
feature/source artifacts.
"""
from __future__ import annotations

import argparse
import datetime as _datetime
import hashlib
import json
import math
import platform
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA = "m2.analysis-eligibility.v1"
FEATURE_SCHEMA = "m2.corpus-features.v1"
ACTIONS = (
    "likes_per_1k_views",
    "comments_per_1k_views",
    "reshares_per_1k_views",
    "saves_per_1k_views",
)
KNOWN_SCENE_REVIEW_STATES = {"APPROVED", "ACCEPTED", "REVIEWED"}
KNOWN_STRUCTURE_STATE = "ACCEPTED_REVIEWED"


class EligibilityInputError(ValueError):
    """Raised when a frozen input or its declared contract cannot be trusted."""


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_load_bytes(raw: bytes) -> Any:
    def reject_constant(value: str) -> None:
        raise EligibilityInputError(f"nonfinite_json_constant:{value.lower()}")

    try:
        return json.loads(raw.decode("utf-8"), parse_constant=reject_constant)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EligibilityInputError("input_json_invalid") from exc


def _read_hashed_json(path: str | Path, label: str) -> tuple[Any, str]:
    try:
        raw = Path(path).read_bytes()
    except (OSError, PermissionError) as exc:
        raise EligibilityInputError(f"{label}_unreadable") from exc
    digest = hashlib.sha256(raw).hexdigest()
    return _json_load_bytes(raw), digest


def _expected_hash(observed: str, expected: str | None, label: str) -> None:
    if expected is not None and expected.removeprefix("sha256:") != observed:
        raise EligibilityInputError(f"{label}_hash_mismatch")


def load_feature_rows(path: str | Path, *, expected_sha256: str | None = None, expected_rows: int | None = 2352) -> tuple[list[dict[str, Any]], str]:
    """Load a frozen feature JSONL and fail closed on identity or JSON errors."""
    source = Path(path)
    try:
        raw = source.read_bytes()
    except (OSError, PermissionError) as exc:
        raise EligibilityInputError("feature_dataset_unreadable") from exc
    observed_hash = hashlib.sha256(raw).hexdigest()
    _expected_hash(observed_hash, expected_sha256, "feature_dataset")
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_codes: set[str] = set()
    seen_indexes: set[int] = set()
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise EligibilityInputError("feature_dataset_unreadable") from exc
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line, parse_constant=lambda token: (_ for _ in ()).throw(EligibilityInputError("nonfinite_json_constant")))
        except json.JSONDecodeError as exc:
            raise EligibilityInputError(f"feature_row_invalid_json:{line_number}") from exc
        if not isinstance(value, dict):
            raise EligibilityInputError(f"feature_row_not_object:{line_number}")
        reel_id, code, identity_index = value.get("reel_id"), value.get("code"), value.get("identity_index")
        if not isinstance(reel_id, str) or not reel_id or not isinstance(code, str) or not code or type(identity_index) is not int:
            raise EligibilityInputError(f"feature_identity_invalid:{line_number}")
        if reel_id in seen_ids or code in seen_codes or identity_index in seen_indexes:
            raise EligibilityInputError("feature_identity_not_unique")
        seen_ids.add(reel_id)
        seen_codes.add(code)
        seen_indexes.add(identity_index)
        rows.append(value)
    if expected_rows is not None and len(rows) != expected_rows:
        raise EligibilityInputError(f"feature_row_count_mismatch:{len(rows)}")
    return rows, observed_hash


def _number_state(value: Any, *, nonnegative: bool = True, positive: bool = False) -> str:
    if value is None:
        return "MISSING"
    if type(value) not in {int, float} or isinstance(value, bool):
        return "INVALID_TYPE"
    try:
        numeric = float(value)
    except (OverflowError, ValueError):
        return "INVALID_OVERFLOW"
    if not math.isfinite(numeric):
        return "INVALID_NONFINITE"
    if nonnegative and numeric < 0:
        return "INVALID_NEGATIVE"
    if positive and numeric <= 0:
        return "OBSERVED_ZERO"
    if numeric == 0:
        return "OBSERVED_ZERO"
    return "OBSERVED_POSITIVE"


def _field_state(row: Mapping[str, Any], field: str, *, nonnegative: bool = True, positive: bool = False) -> str:
    value = row.get(field)
    state = _number_state(value, nonnegative=nonnegative, positive=positive)
    if state == "MISSING":
        invalid_fields = {str(item) for item in row.get("metric_invalid_fields", []) if item is not None}
        missing_fields = {str(item) for item in row.get("metric_missing_fields", []) if item is not None}
        if field in invalid_fields or field.removesuffix("_per_1k_views") in invalid_fields:
            return "INVALID_DECLARED"
        if field in missing_fields or field.removesuffix("_per_1k_views") in missing_fields:
            return "MISSING_DECLARED"
        return "MISSING_UNDECLARED"
    return state


def _snapshot_state(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return "MISSING_SNAPSHOT"
    try:
        _datetime.date.fromisoformat(value)
    except ValueError:
        return "INVALID_SNAPSHOT"
    return "VALID_SNAPSHOT"


def _account_state(value: Any) -> str:
    return "KNOWN_ACCOUNT_CLUSTER" if isinstance(value, str) and value.strip() else "UNKNOWN_ACCOUNT_CLUSTER"


def _stage_dispositions(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "acquisition": {"state": row.get("acquisition_state", "UNKNOWN"), "artifact_verified": row.get("media_artifact_verified") is True},
        "transcript": {"state": row.get("transcript_state", "UNKNOWN"), "artifact_verified": row.get("transcript_artifact_verified") is True, "source_identity": row.get("transcript_source_identity_state", "UNVERIFIED")},
        "frames": {"state": row.get("frames_state", "UNKNOWN"), "artifact_verified": row.get("frames_artifact_verified") is True, "source_identity": row.get("frames_source_identity_state", "UNVERIFIED")},
        "scene_review": {"state": row.get("scene_review_state", "UNKNOWN"), "reviewed_state": row.get("reviewed_scene_state", "UNKNOWN")},
    }


def _modality_gates(row: Mapping[str, Any]) -> dict[str, Any]:
    transcript_verified = row.get("transcript_state") == "OBSERVED" and row.get("transcript_artifact_verified") is True and row.get("transcript_source_identity_state") == "VERIFIED"
    transcript_words = _field_state(row, "transcript_word_count_lexical")
    language = row.get("asr_language")
    language_known = isinstance(language, str) and language.strip().lower() not in {"", "unknown", "undetermined", "und"}
    transcript_word_count_present = transcript_words in {"OBSERVED_POSITIVE", "OBSERVED_ZERO"}
    actual_rate = row.get("transcript_words_per_second")
    rate_state = _number_state(actual_rate, nonnegative=True)
    aligned_state = _field_state(row, "transcript_aligned_word_count")
    timing_state = row.get("transcript_word_timing_state")
    valid_timing_coverage = timing_state in {"OBSERVED", "PARTIAL"} and aligned_state in {"OBSERVED_POSITIVE", "OBSERVED_ZERO"}
    word_rate = transcript_verified and language_known and row.get("transcript_rate_comparability") == "LANGUAGE_CONDITIONED_TOKEN_RATE" and transcript_word_count_present and rate_state in {"OBSERVED_POSITIVE", "OBSERVED_ZERO"} and valid_timing_coverage
    structure_state = row.get("structural_label_state")
    structure_gate = "UNVERIFIED_STATE_ONLY" if structure_state == KNOWN_STRUCTURE_STATE else "NOT_REVIEWED"
    scene_state = row.get("reviewed_scene_state")
    scene_gate = "UNVERIFIED_STATE_ONLY" if scene_state in KNOWN_SCENE_REVIEW_STATES else "NOT_REVIEWED"
    return {
        "transcript_text": {"state": "ELIGIBLE" if transcript_verified and transcript_word_count_present else ("UNVERIFIED" if not transcript_verified else "EMPTY_OR_MISSING"), "source_identity": row.get("transcript_source_identity_state", "UNVERIFIED"), "word_count_state": transcript_words},
        "language_conditioned_word_rate": {"state": "ELIGIBLE" if word_rate else "NOT_ELIGIBLE", "language": language if language_known else None, "rate_state": rate_state, "timing_state": timing_state, "coverage_state": aligned_state, "reason": None if word_rate else "FINITE_RATE_LANGUAGE_VERIFIED_TRANSCRIPT_TIMING_COVERAGE_GATE"},
        "structural_labels": {"state": structure_gate, "source_state": structure_state or "UNKNOWN", "receipt_binding": "UNIMPLEMENTED"},
        "scenes": {"state": scene_gate, "scene_review_state": scene_state or "UNKNOWN", "frame_artifact_verified": row.get("frames_artifact_verified") is True, "receipt_binding": "UNIMPLEMENTED"},
    }


def _outcome(row: Mapping[str, Any], outcome: str, views_state: str, snapshot_state: str, account_state: str) -> dict[str, Any]:
    required = ACTIONS if outcome == "total_actions_per_1k_views" else (outcome,)
    metric_states = {action: _field_state(row, action) for action in required}
    reasons: list[str] = []
    if row.get("quarantined") is True or row.get("quarantine_reasons") or row.get("research_quarantine_reasons"):
        reasons.append("CANONICAL_QUARANTINE")
    if snapshot_state != "VALID_SNAPSHOT":
        reasons.append(snapshot_state)
    if views_state != "OBSERVED_POSITIVE":
        reasons.append("VIEWS_" + views_state)
    for action, metric_state in metric_states.items():
        if metric_state not in {"OBSERVED_POSITIVE", "OBSERVED_ZERO"}:
            reasons.append(action + "_" + metric_state)
    eligible = not reasons
    grouped = eligible and account_state == "KNOWN_ACCOUNT_CLUSTER"
    if eligible:
        state = "ELIGIBLE"
    elif "CANONICAL_QUARANTINE" in reasons:
        state = "BLOCKED_QUARANTINE"
    elif any("INVALID" in item or item.startswith("VIEWS_INVALID") or item == "INVALID_SNAPSHOT" for item in reasons):
        state = "INELIGIBLE_INVALID"
    else:
        state = "INELIGIBLE_MISSING_OR_NONPOSITIVE"
    return {"state": state, "eligible": eligible, "grouped_eligible": grouped, "required_action_rates": list(required), "requires_other_action_rates": len(required) > 1, "requires_saves": "saves_per_1k_views" in required, "metric_states": metric_states, "reasons": reasons}


def classify_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Create one auditable coverage row without changing source values."""
    views_state = _field_state(row, "views", positive=True)
    snapshot_state = _snapshot_state(row.get("snapshot_date"))
    account_state = _account_state(row.get("account_cluster_id"))
    outcomes = {action: _outcome(row, action, views_state, snapshot_state, account_state) for action in ACTIONS + ("total_actions_per_1k_views",)}
    modalities = _modality_gates(row)
    missingness: list[str] = []
    if row.get("quarantined") is True or row.get("quarantine_reasons") or row.get("research_quarantine_reasons"):
        missingness.append("CANONICAL_QUARANTINE")
    if account_state != "KNOWN_ACCOUNT_CLUSTER":
        missingness.append("UNKNOWN_ACCOUNT_CLUSTER")
    if snapshot_state != "VALID_SNAPSHOT":
        missingness.append(snapshot_state)
    if views_state not in {"OBSERVED_POSITIVE", "OBSERVED_ZERO"}:
        missingness.append("VIEWS_" + views_state)
    for action, value in outcomes.items():
        if not value["eligible"]:
            missingness.extend(f"{action}:{reason}" for reason in value["reasons"])
    for name, value in modalities.items():
        if value["state"] not in {"ELIGIBLE"}:
            missingness.append(f"{name}:{value['state']}")
    return {
        "reel_id": row["reel_id"],
        "code": row["code"],
        "identity_index": row["identity_index"],
        "quarantine_reasons": list(row.get("quarantine_reasons") or []),
        "research_quarantine_reasons": list(row.get("research_quarantine_reasons") or []),
        "stages": _stage_dispositions(row),
        "metrics": {"views_state": views_state, "snapshot_state": snapshot_state, "account_state": account_state, "account_cluster_id": row.get("account_cluster_id"), "views": row.get("views"), **{action: row.get(action) for action in ACTIONS}},
        "outcomes": outcomes,
        "modalities": modalities,
        "missingness": sorted(set(missingness)),
    }


def _count_language(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        language = row.get("asr_language")
        key = language.strip().lower() if isinstance(language, str) and language.strip() else "UNKNOWN_LANGUAGE"
        counts[key] += 1
    return dict(sorted(counts.items()))


def summarize(rows: Sequence[Mapping[str, Any]], classified: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    missing = Counter(reason for row in classified for reason in row["missingness"])
    output: dict[str, Any] = {
        "schema": SCHEMA,
        "denominators": {"input_rows": len(rows), "preserved_rows": len(classified), "output_rows": len(classified), "quarantined_rows": sum(bool(r.get("quarantine_reasons") or r.get("research_quarantine_reasons") or r.get("quarantined") is True) for r in rows)},
        "outcomes": {},
        "feature_gates": {},
        "intersections": {},
        "language_strata": _count_language(rows),
        "missingness_counts": dict(sorted(missing.items())),
        "fit_state": "FIT_REQUESTED_WAITING_FOR_EVIDENCE",
    }
    for action in ACTIONS + ("total_actions_per_1k_views",):
        eligible = [r for r in classified if r["outcomes"][action]["eligible"]]
        grouped = [r for r in classified if r["outcomes"][action]["grouped_eligible"]]
        output["outcomes"][action] = {
            "eligible_rows": len(eligible),
            "eligible_accounts": len({r["metrics"]["account_cluster_id"] for r in grouped}),
            "grouped_eligible_rows": len(grouped),
            "state_counts": dict(sorted(Counter(r["outcomes"][action]["state"] for r in classified).items())),
            "requires_other_action_rates": action == "total_actions_per_1k_views",
            "requires_saves": action in {"saves_per_1k_views", "total_actions_per_1k_views"},
        }
    for name in ("transcript_text", "language_conditioned_word_rate", "structural_labels", "scenes"):
        output["feature_gates"][name] = dict(sorted(Counter(r["modalities"][name]["state"] for r in classified).items()))
    for action in ACTIONS + ("total_actions_per_1k_views",):
        for feature in ("transcript_text", "language_conditioned_word_rate", "structural_labels", "scenes"):
            key = f"{action}__{feature}"
            output["intersections"][key] = sum(r["outcomes"][action]["eligible"] and r["modalities"][feature]["state"] == "ELIGIBLE" for r in classified)
        output["intersections"][f"{action}__known_account_cluster"] = sum(r["outcomes"][action]["eligible"] and r["metrics"]["account_state"] == "KNOWN_ACCOUNT_CLUSTER" for r in classified)
    return output


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _require_new_output_dir(destination: Path) -> None:
    if any(part == ".." for part in destination.parts):
        raise EligibilityInputError("output_path_lexical_parent_rejected")
    if destination.exists() or destination.is_symlink():
        raise EligibilityInputError("output_directory_must_be_new")
    for current in destination.parents:
        if not current.exists():
            continue
        if current.is_symlink():
            resolved = current.resolve()
            # macOS commonly exposes /private/tmp through /tmp.  This known
            # OS alias is safe; any user-created lexical ancestor symlink is
            # rejected, including one hidden below an ordinary directory.
            if current in {Path("/tmp"), Path("/var"), Path("/var/tmp")} and resolved in {Path("/private/tmp"), Path("/private/var"), Path("/private/var/tmp")}:
                continue
            raise EligibilityInputError("output_ancestor_symlink_rejected")
        if not current.is_dir():
            raise EligibilityInputError("output_ancestor_not_directory")


def _derived_field_dictionary(source: Mapping[str, Any]) -> dict[str, Any]:
    derived = {
        "reel_id": "Canonical Reel identity copied from the frozen feature row.",
        "code": "Canonical short code copied from the frozen feature row.",
        "identity_index": "Stable canonical population index.",
        "quarantine_reasons": "Canonical quarantine reason list; retained without diagnosis or filtering.",
        "research_quarantine_reasons": "Research quarantine reason list; retained without diagnosis or filtering.",
        "stages.acquisition.state": "Committed acquisition stage state.",
        "stages.acquisition.artifact_verified": "Acquisition artifact verification flag.",
        "stages.transcript.state": "Committed transcript stage state.",
        "stages.transcript.artifact_verified": "Transcript artifact verification flag.",
        "stages.transcript.source_identity": "Transcript-to-media source identity gate.",
        "stages.frames.state": "Committed frame stage state.",
        "stages.frames.artifact_verified": "Frame artifact verification flag.",
        "stages.frames.source_identity": "Frame-to-media source identity gate.",
        "stages.scene_review.state": "Committed scene-review workflow state.",
        "stages.scene_review.reviewed_state": "Scene review promotion state.",
        "metrics.views_state": "Views numeric state: missing, observed zero, positive, or typed invalid state.",
        "metrics.snapshot_state": "ISO snapshot validity gate.",
        "metrics.account_state": "Known versus unknown account-cluster gate.",
        "metrics.account_cluster_id": "Explicit account-cluster key when supplied; never imputed.",
        "metrics.views": "Source views value retained when valid; zero remains observed zero.",
        "metrics.likes_per_1k_views": "Source like rate retained when present and valid.",
        "metrics.comments_per_1k_views": "Source comment rate retained when present and valid.",
        "metrics.reshares_per_1k_views": "Source reshare rate retained when present and valid.",
        "metrics.saves_per_1k_views": "Source save rate retained when present and valid.",
        "outcomes.*.state": "Outcome gate state for one action or the complete-four composite.",
        "outcomes.*.eligible": "Row-level eligibility for the named outcome only.",
        "outcomes.*.grouped_eligible": "Outcome eligibility plus known account cluster for grouped analysis.",
        "outcomes.*.required_action_rates": "Action-rate fields required by the named outcome.",
        "outcomes.*.requires_other_action_rates": "Whether the outcome requires multiple action rates.",
        "outcomes.*.requires_saves": "Whether the named outcome owns/requires the save rate.",
        "outcomes.*.metric_states": "Per-required-rate numeric states.",
        "outcomes.*.reasons": "Stable blocking reason codes for the named outcome.",
        "modalities.transcript_text.state": "Verified transcript text availability gate.",
        "modalities.transcript_text.source_identity": "Transcript source identity state.",
        "modalities.transcript_text.word_count_state": "Transcript lexical count numeric state.",
        "modalities.language_conditioned_word_rate.state": "Verified known-language rate eligibility gate.",
        "modalities.language_conditioned_word_rate.language": "Known ASR language retained for stratification.",
        "modalities.language_conditioned_word_rate.rate_state": "Actual word-rate numeric state.",
        "modalities.language_conditioned_word_rate.timing_state": "Word timing state used by the rate gate.",
        "modalities.language_conditioned_word_rate.coverage_state": "Aligned-word coverage numeric state.",
        "modalities.language_conditioned_word_rate.reason": "Word-rate blocking reason when unavailable.",
        "modalities.structural_labels.state": "Structural label gate; state-only acceptance remains unverified.",
        "modalities.structural_labels.source_state": "Source structural-label state.",
        "modalities.structural_labels.receipt_binding": "Receipt/source binding adapter status.",
        "modalities.scenes.state": "Scene gate; state-only acceptance remains unverified.",
        "modalities.scenes.scene_review_state": "Scene review state supplied by source.",
        "modalities.scenes.frame_artifact_verified": "Frame artifact verification prerequisite.",
        "modalities.scenes.receipt_binding": "Scene receipt/source binding adapter status.",
        "missingness": "Stable list of evidence and eligibility gaps; missing is never zero.",
    }
    return {"schema": "m2.analysis-eligibility-field-dictionary.v1", "source_schema": source.get("schema"), "source_fields": source.get("fields", {}), "derived_fields": derived}


def build_eligibility(
    features_path: str | Path,
    output_dir: str | Path,
    *,
    contract_path: str | Path,
    field_dictionary_path: str | Path,
    expected_features_sha256: str | None = None,
    expected_contract_sha256: str | None = None,
    expected_field_dictionary_sha256: str | None = None,
    expected_rows: int | None = 2352,
) -> dict[str, Any]:
    """Build a new immutable eligibility output directory from frozen inputs."""
    rows, feature_hash = load_feature_rows(features_path, expected_sha256=expected_features_sha256, expected_rows=expected_rows)
    contract, contract_hash = _read_hashed_json(contract_path, "contract")
    field_dictionary, dictionary_hash = _read_hashed_json(field_dictionary_path, "field_dictionary")
    _expected_hash(contract_hash, expected_contract_sha256, "contract")
    _expected_hash(dictionary_hash, expected_field_dictionary_sha256, "field_dictionary")
    if not isinstance(contract, dict) or contract.get("schema") != "m2.full-evidence-analysis-contract.v1":
        raise EligibilityInputError("analysis_contract_schema_mismatch")
    if not isinstance(field_dictionary, dict) or not field_dictionary.get("fields"):
        raise EligibilityInputError("field_dictionary_invalid")
    if not all(row.get("metric_eligibility_gate") is not None for row in rows):
        raise EligibilityInputError("metric_eligibility_gate_missing")
    destination = Path(output_dir)
    _require_new_output_dir(destination)
    destination.mkdir(parents=True, exist_ok=True)
    classified = [classify_row(row) for row in rows]
    summary = summarize(rows, classified)
    run = {
        "schema": SCHEMA,
        "status": "ELIGIBILITY_COMPLETE_FIT_PENDING_REVIEWED_EVIDENCE",
        "input": {"feature_dataset": {"name": Path(features_path).name, "sha256": feature_hash, "row_count": len(rows), "schema": FEATURE_SCHEMA}, "contract": {"name": Path(contract_path).name, "sha256": contract_hash}, "field_dictionary": {"name": Path(field_dictionary_path).name, "sha256": dictionary_hash}},
        "contract_status": contract.get("status"),
        "population_preservation": {"input_rows": len(rows), "output_rows": len(classified), "rows_dropped": 0},
        "runtime": {"implementation": platform.python_implementation(), "version": platform.python_version(), "executable_basename": Path(sys.executable).name, "module_sha256": sha256_file(Path(__file__))},
        "scope": {"per_action_outcomes": True, "likes_and_comments_do_not_require_saves": True, "missing_is_not_zero": True, "quarantine_and_unknown_account_separate": True, "no_fitting": True, "no_network": True},
        "artifacts": {"coverage": "coverage-and-eligibility.jsonl", "missingness": "missingness.json", "field_dictionary": "field-dictionary.json"},
    }
    with (destination / "coverage-and-eligibility.jsonl").open("w", encoding="utf-8") as stream:
        for row in classified:
            stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
    _write_json(destination / "missingness.json", summary)
    _write_json(destination / "field-dictionary.json", _derived_field_dictionary(field_dictionary))
    _write_json(destination / "analysis-run.json", run)
    manifest = {}
    for path in sorted(destination.iterdir()):
        if path.name == "artifact-manifest.json":
            continue
        manifest[path.name] = sha256_file(path)
    _write_json(destination / "artifact-manifest.json", {"schema": "m2.analysis-eligibility-artifacts.v1", "files": manifest})
    return {"schema": SCHEMA, "status": run["status"], "summary": summary, "output_dir": str(destination), "input_sha256": feature_hash}


def _cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--field-dictionary", type=Path, required=True)
    parser.add_argument("--expected-features-sha256")
    parser.add_argument("--expected-contract-sha256")
    parser.add_argument("--expected-field-dictionary-sha256")
    parser.add_argument("--expected-rows", type=int, default=2352)
    args = parser.parse_args(argv)
    result = build_eligibility(args.features, args.output, contract_path=args.contract, field_dictionary_path=args.field_dictionary, expected_features_sha256=args.expected_features_sha256, expected_contract_sha256=args.expected_contract_sha256, expected_field_dictionary_sha256=args.expected_field_dictionary_sha256, expected_rows=args.expected_rows)
    print(json.dumps({"status": result["status"], "rows": result["summary"]["denominators"]["output_rows"], "output_dir": result["output_dir"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())


__all__ = ["ACTIONS", "EligibilityInputError", "build_eligibility", "classify_row", "load_feature_rows", "sha256_file", "summarize"]
