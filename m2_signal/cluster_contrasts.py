"""Hash-bound account-cluster descriptive contrasts with explicit outcome units."""
from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from statistics import median
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "m2.cluster-contrasts.v3"
RATE_ACTIONS = (
    "likes_per_1k_views",
    "comments_per_1k_views",
    "reshares_per_1k_views",
    "saves_per_1k_views",
    "total_actions_per_1k_views",
)
RAW_ACTIONS = ("likes", "comments", "reshares", "saves", "total_actions")
DEFAULT_ACTIONS = RATE_ACTIONS
MIN_POINT_ROWS, MIN_POINT_ACCOUNTS = 10, 5
MIN_PRIMARY_ACCOUNTS, MIN_PRIMARY_GROUP_ACCOUNTS = 30, 10
MIN_USABLE_REPLICATES = 100


class ClusterContrastError(ValueError):
    pass


def _finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def _outcome_spec(action: str, outcome_mode: str) -> dict[str, Any]:
    if not isinstance(action, str) or not action:
        raise ClusterContrastError("ACTION_INVALID")
    if outcome_mode not in {"rate_per_1k_views", "raw_count_sensitivity"}:
        raise ClusterContrastError("OUTCOME_MODE_INVALID")
    if action in RATE_ACTIONS:
        if outcome_mode != "rate_per_1k_views":
            raise ClusterContrastError("RATE_MODE_MISMATCH")
        base = action.removesuffix("_per_1k_views")
        return {
            "name": action,
            "mode": outcome_mode,
            "field": action,
            "base_action": base,
            "unit": "events_per_1000_views",
            "scale": "raw_rate",
            "log_scale": "not_applied",
            "formula": f"1000 * {base} / views",
            "requires_positive_views": True,
            "exposure_field": "views",
            "estimate_role": "COMPLETE_FOUR_ACTION_COMPOSITE" if action == "total_actions_per_1k_views" else "PRIMARY_CONTRACT_OUTCOME",
        }
    if action in RAW_ACTIONS:
        if outcome_mode != "raw_count_sensitivity":
            raise ClusterContrastError("ACTION_RATE_REQUIRED")
        return {
            "name": action,
            "mode": outcome_mode,
            "field": action,
            "base_action": action,
            "unit": "events_count",
            "scale": "raw_count",
            "log_scale": "not_applied",
            "formula": action,
            "requires_positive_views": False,
            "exposure_field": None,
            "estimate_role": "SENSITIVITY_ONLY",
        }
    raise ClusterContrastError("ACTION_INVALID")


def _action_value(record: Mapping[str, Any], spec: Mapping[str, Any]) -> Any:
    outcomes = record.get("outcomes")
    field = spec["field"]
    if isinstance(outcomes, Mapping) and field in outcomes:
        return outcomes[field]
    return record.get(field)


def _action_eligible(record: Mapping[str, Any], spec: Mapping[str, Any]) -> Any:
    eligibility = record.get("eligible_actions", record.get("eligibility"))
    field = spec["field"]
    return eligibility[field] if isinstance(eligibility, Mapping) and field in eligibility else None


def _quarantined(record: Mapping[str, Any]) -> bool:
    return (
        record.get("quarantined") is True
        or record.get("is_quarantined") is True
        or bool(record.get("quarantine_reasons"))
        or bool(record.get("research_quarantine_reasons"))
    )


def _account(record: Mapping[str, Any]) -> str | None:
    values = []
    for key in ("account_cluster", "account_cluster_id"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
    if len(set(values)) > 1:
        raise ClusterContrastError("ACCOUNT_CLUSTER_CONFLICT")
    return values[0] if values else None


def _is_category(value: Any, category: Any) -> bool:
    if isinstance(value, (list, tuple, set, frozenset)):
        return category in value
    return value == category


def _jsonable(value: Any) -> Any:
    if isinstance(value, (set, frozenset)):
        return sorted((_jsonable(x) for x in value), key=repr)
    if isinstance(value, (list, tuple)):
        return [_jsonable(x) for x in value]
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
    return value


def identity_binding_sha256(records: Sequence[Mapping[str, Any]], *, group_field: str) -> str:
    """Digest canonical Reel identity plus fixed group/account assignment."""
    entries = []
    for record in records:
        if not isinstance(record, Mapping) or not isinstance(record.get("reel_id"), str) or not record["reel_id"].strip():
            raise ClusterContrastError("RECORD_IDENTITY_INVALID")
        if type(record.get("identity_index")) is not int or record["identity_index"] < 0:
            raise ClusterContrastError("RECORD_IDENTITY_INVALID")
        entries.append(
            {
                "reel_id": record["reel_id"],
                "identity_index": record["identity_index"],
                "group": _jsonable(record.get(group_field)),
                "account_cluster": _account(record),
            }
        )
    payload = json.dumps(
        sorted(entries, key=lambda x: (x["identity_index"], x["reel_id"])),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _validate_binding(
    records: Sequence[Mapping[str, Any]],
    *,
    group_field: str,
    source_snapshot_hash: str,
    identity_binding_hash: str,
) -> str:
    if not isinstance(source_snapshot_hash, str) or len(source_snapshot_hash) != 64 or any(c not in "0123456789abcdefABCDEF" for c in source_snapshot_hash):
        raise ClusterContrastError("SOURCE_SNAPSHOT_HASH_INVALID")
    if not isinstance(identity_binding_hash, str) or len(identity_binding_hash) != 64 or any(c not in "0123456789abcdefABCDEF" for c in identity_binding_hash):
        raise ClusterContrastError("IDENTITY_BINDING_HASH_INVALID")
    seen_ids, seen_codes, seen_indexes = set(), set(), set()
    for record in records:
        if not isinstance(record, Mapping):
            raise ClusterContrastError("RECORD_IDENTITY_INVALID")
        rid, idx = record.get("reel_id"), record.get("identity_index")
        if not isinstance(rid, str) or not rid.strip() or type(idx) is not int or idx < 0:
            raise ClusterContrastError("RECORD_IDENTITY_INVALID")
        if rid in seen_ids:
            raise ClusterContrastError("DUPLICATE_REEL_ID")
        code = record.get("code")
        if isinstance(code, str) and code:
            if code in seen_codes:
                raise ClusterContrastError("DUPLICATE_REEL_CODE")
            seen_codes.add(code)
        if idx in seen_indexes:
            raise ClusterContrastError("DUPLICATE_IDENTITY_INDEX")
        seen_ids.add(rid)
        seen_indexes.add(idx)
        if record.get("source_snapshot_hash") != source_snapshot_hash:
            raise ClusterContrastError("SOURCE_SNAPSHOT_MISMATCH")
        _account(record)
    actual = identity_binding_sha256(records, group_field=group_field)
    if actual.lower() != identity_binding_hash.lower():
        raise ClusterContrastError("IDENTITY_BINDING_MISMATCH")
    return actual


def _positive_exposure(record: Mapping[str, Any], *, required: bool) -> bool:
    if not required:
        return True
    views = record.get("views")
    if not _finite_number(views) or float(views) <= 0:
        return False
    if "exposure_eligible" in record and record.get("exposure_eligible") is not True:
        return False
    if "views_state" in record and record.get("views_state") != "OBSERVED_POSITIVE":
        return False
    if "exposure_state" in record and record.get("exposure_state") != "OBSERVED_POSITIVE":
        return False
    return True


def _median_delta(rows: Sequence[tuple[Any, float]], category: Any) -> float:
    left = [v for g, v in rows if g == category]
    right = [v for g, v in rows if g != category]
    return float(median(left) - median(right))


def _equal_account_delta(rows: Sequence[tuple[Any, float, str]], category: Any) -> float:
    grouped: dict[tuple[str, Any], list[float]] = defaultdict(list)
    for group, value, cluster in rows:
        grouped[(cluster, group)].append(value)
    left = [sum(v) / len(v) for (cluster, group), v in grouped.items() if group == category]
    right = [sum(v) / len(v) for (cluster, group), v in grouped.items() if group != category]
    if not left or not right:
        raise ClusterContrastError("BOOTSTRAP_GROUP_MISSING")
    return float(median(left) - median(right))


def _influence(rows: Sequence[tuple[Any, float, str]], category: Any) -> dict[str, Any]:
    accounts = sorted({a for _, _, a in rows})
    estimates = []
    for account in accounts:
        kept = [r for r in rows if r[2] != account]
        groups = {r[0] for r in kept}
        if category in groups and len(groups) >= 2:
            estimates.append((account, _median_delta([(g, v) for g, v, _ in kept], category)))
    point = _median_delta([(g, v) for g, v, _ in rows], category)
    values = [v for _, v in estimates]
    return {
        "accounts_evaluated": len(estimates),
        "leave_one_account_out_range": [min(values), max(values)] if values else None,
        "largest_absolute_change": max((abs(v - point) for v in values), default=None),
    }


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    pos = (len(values) - 1) * q
    low, high = math.floor(pos), math.ceil(pos)
    return values[low] if low == high else values[low] + (values[high] - values[low]) * (pos - low)


def cluster_contrast(
    records: Sequence[Mapping[str, Any]],
    *,
    action: str,
    group_field: str,
    category: Any,
    source_snapshot_hash: str,
    identity_binding_hash: str,
    outcome_mode: str = "rate_per_1k_views",
    seed: int = 20260906,
    bootstrap_replicates: int = 2000,
    min_rows: int = 10,
    min_accounts: int = 5,
    reliability_accounts: int = 30,
    min_group_accounts: int = 10,
) -> dict[str, Any]:
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        raise ClusterContrastError("RECORDS_REQUIRED")
    if not isinstance(group_field, str) or not group_field:
        raise ClusterContrastError("GROUP_FIELD_INVALID")
    if type(seed) is not int or seed < 0:
        raise ClusterContrastError("SEED_INVALID")
    if type(bootstrap_replicates) is not int or not 1 <= bootstrap_replicates <= 100_000:
        raise ClusterContrastError("BOOTSTRAP_REPLICATES_INVALID")
    policy = {
        "min_rows": min_rows,
        "min_accounts": min_accounts,
        "reliability_accounts": reliability_accounts,
        "min_group_accounts": min_group_accounts,
    }
    if any(type(v) is not int or v < 1 for v in policy.values()):
        raise ClusterContrastError("SUPPORT_POLICY_INVALID")
    if min_rows < MIN_POINT_ROWS or min_accounts < MIN_POINT_ACCOUNTS or reliability_accounts < MIN_PRIMARY_ACCOUNTS or min_group_accounts < MIN_PRIMARY_GROUP_ACCOUNTS:
        raise ClusterContrastError("SUPPORT_POLICY_BELOW_CONTRACT_FLOOR")
    spec = _outcome_spec(action, outcome_mode)
    bound_hash = _validate_binding(records, group_field=group_field, source_snapshot_hash=source_snapshot_hash, identity_binding_hash=identity_binding_hash)

    missing = Counter()
    eligible = []
    declared = sum(_action_eligible(r, spec) is True for r in records)
    quarantined_total = sum(_quarantined(r) for r in records)
    invalid_total = invalid_quarantined = invalid_exposure = validated = missing_group = missing_account = 0
    for record in records:
        allowed = _action_eligible(record, spec)
        value = _action_value(record, spec)
        quarantined = _quarantined(record)
        valid = _finite_number(value) and float(value) >= 0
        exposure_ok = _positive_exposure(record, required=spec["requires_positive_views"])
        if allowed is True and not valid:
            invalid_total += 1
            if quarantined:
                invalid_quarantined += 1
        if allowed is True and not exposure_ok:
            invalid_exposure += 1
        if quarantined:
            missing["QUARANTINED"] += 1
            continue
        if allowed is not True:
            missing["ELIGIBILITY_MISSING" if allowed is None else "OUTCOME_NOT_ELIGIBLE"] += 1
            continue
        if not valid:
            missing["OUTCOME_INVALID_OR_MISSING"] += 1
            continue
        if not exposure_ok:
            missing["EXPOSURE_INVALID_OR_MISSING"] += 1
            continue
        validated += 1
        group = record.get(group_field)
        if group is None or (isinstance(group, str) and not group.strip()) or (isinstance(group, (list, tuple, set, frozenset)) and not group):
            missing_group += 1
            missing["GROUP_MISSING"] += 1
            continue
        account = _account(record)
        if account is None:
            missing_account += 1
            missing["ACCOUNT_CLUSTER_MISSING"] += 1
            continue
        eligible.append((_is_category(group, category), float(value), account))

    grouped = {"category": [r for r in eligible if r[0] is True], "noncategory": [r for r in eligible if r[0] is False]}
    group_rows = {k: len(v) for k, v in grouped.items()}
    group_accounts = {k: len({a for _, _, a in v}) for k, v in grouped.items()}
    accounts = sorted({a for _, _, a in eligible})
    support_ok = all(group_rows[k] >= min_rows and group_accounts[k] >= min_accounts for k in grouped)
    support_state = "SUPPORTED" if support_ok else "INSUFFICIENT_SUPPORT"
    point = {"row_median_delta": None, "equal_account_delta": None}
    influence = None
    interval_state = "NO_INTERVAL_SUPPORT"
    intervals = None
    used = 0
    if support_ok:
        point = {
            "row_median_delta": _median_delta([(g, v) for g, v, _ in eligible], True),
            "equal_account_delta": _equal_account_delta(eligible, True),
        }
        influence = _influence(eligible, True)
        primary_group_floor = max(MIN_PRIMARY_GROUP_ACCOUNTS, min_group_accounts)
        primary_account_floor = max(MIN_PRIMARY_ACCOUNTS, reliability_accounts)
        if min(group_accounts.values()) < primary_group_floor:
            interval_state = "NO_INTERVAL_BELOW_GROUP_ACCOUNT_FLOOR"
        elif len(accounts) < primary_account_floor:
            interval_state = "EXPLORATORY_UNSTABLE_NO_SIGNIFICANCE"
        else:
            interval_state = "PRIMARY_95CI"
        if interval_state in {"EXPLORATORY_UNSTABLE_NO_SIGNIFICANCE", "PRIMARY_95CI"}:
            by_account = defaultdict(list)
            for row in eligible:
                by_account[row[2]].append(row)
            rng = random.Random(seed)
            row_deltas, equal_deltas = [], []
            for _ in range(bootstrap_replicates):
                sampled = [accounts[rng.randrange(len(accounts))] for _ in accounts]
                replicate, equal_replicate = [], []
                for ordinal, account in enumerate(sampled):
                    cluster_id = f"{account}#draw-{ordinal}"
                    replicate.extend(by_account[account])
                    equal_replicate.extend((g, v, cluster_id) for g, v, _ in by_account[account])
                if True not in {r[0] for r in replicate} or False not in {r[0] for r in replicate}:
                    continue
                row_deltas.append(_median_delta([(g, v) for g, v, _ in replicate], True))
                equal_deltas.append(_equal_account_delta(equal_replicate, True))
            used = len(row_deltas)
            if used < MIN_USABLE_REPLICATES:
                interval_state = "NO_INTERVAL_INSUFFICIENT_REPLICATES"
            else:
                intervals = {
                    "row_median_delta": [_percentile(row_deltas, 0.025), _percentile(row_deltas, 0.975)],
                    "equal_account_delta": [_percentile(equal_deltas, 0.025), _percentile(equal_deltas, 0.975)],
                    "replicates_requested": bootstrap_replicates,
                    "replicates_used": used,
                }

    staged = {
        "canonical_rows": len(records),
        "declared_action_eligible_rows": declared,
        "quarantined_rows": quarantined_total,
        "quarantined_declared_action_eligible_rows": sum(_action_eligible(r, spec) is True and _quarantined(r) for r in records),
        "invalid_outcome_rows": invalid_total,
        "invalid_outcome_quarantined_rows": invalid_quarantined,
        "invalid_exposure_rows": invalid_exposure,
        "validated_action_eligible_rows": validated,
        "missing_group_rows": missing_group,
        "missing_account_cluster_rows": missing_account,
        "grouped_rows": len(eligible),
        "account_clusters": len(accounts),
        "group_rows": group_rows,
        "group_accounts": group_accounts,
        "missingness": dict(sorted(missing.items())),
    }
    return {
        "schema": SCHEMA,
        "status": "DESCRIPTIVE_CLUSTER_CONTRAST_COMPLETE",
        "action": action,
        "outcome": spec,
        "group_field": group_field,
        "category": category,
        "source_binding": {
            "source_snapshot_hash": source_snapshot_hash,
            "identity_binding_sha256": bound_hash,
            "record_count": len(records),
            "reel_identity_field": "reel_id",
            "group_assignment_bound": True,
            "account_cluster_field": "account_cluster_or_account_cluster_id",
        },
        "estimands": {
            "row_median_delta": "primary row median: median(eligible Reel raw outcome | category) - median(eligible Reel raw outcome | noncategory)",
            "equal_account_median_delta": "median_across_accounts(mean(category outcome within-account)) - median_across_accounts(mean(ncategory outcome within-account)); recomputed per bootstrap draw for intervals; sensitivity estimand distinct from the primary row median",
        },
        "units": {
            "outcome_unit": spec["unit"],
            "outcome_scale": spec["scale"],
            "outcome_log_scale": spec["log_scale"],
            "row_estimand_unit": "eligible_reel_row",
            "equal_account_estimand_unit": "replicate_account_cluster",
            "sampling_unit": "account_cluster",
            "exposure_unit": "views" if spec["requires_positive_views"] else None,
        },
        "eligible": staged,
        "support_policy": {
            **policy,
            "contract_floors": {
                "point_rows": MIN_POINT_ROWS,
                "point_accounts": MIN_POINT_ACCOUNTS,
                "primary_overall_accounts": MIN_PRIMARY_ACCOUNTS,
                "primary_group_accounts": MIN_PRIMARY_GROUP_ACCOUNTS,
                "minimum_usable_replicates": MIN_USABLE_REPLICATES,
            },
            "effective_interval_floors": {
                "overall_accounts": max(MIN_PRIMARY_ACCOUNTS, reliability_accounts),
                "group_accounts": max(MIN_PRIMARY_GROUP_ACCOUNTS, min_group_accounts),
            },
        },
        "support_state": support_state,
        "point_estimate": point,
        "interval_state": interval_state,
        "intervals": intervals,
        "leave_one_account_out": influence,
        "bootstrap": {
            "resample_unit": "account_cluster",
            "seed": seed,
            "carries_all_rows_in_sampled_account": True,
            "replicate_cluster_identity": "source_account#draw-ordinal",
            "replicates_requested": bootstrap_replicates,
            "replicates_used": used,
        },
        "inference": {
            "p_values": "UNAVAILABLE_CLUSTER_TEST_NOT_IMPLEMENTED",
            "q_values": "UNAVAILABLE_CLUSTER_TEST_NOT_IMPLEMENTED",
            "causal_interpretation": "NOT_APPLICABLE",
        },
        "limitations": [
            "Descriptive corpus contrast only; no significance, q-value, causal, power, or beyond-corpus generalization claim.",
            "Primary outcomes are precomputed per-1,000-view rates and require positive finite views plus explicit rate eligibility; raw counts require the explicit raw_count_sensitivity mode.",
            "Confidence intervals summarize account-cluster resampling variability; exploratory intervals are explicitly unstable and not significance claims.",
            "Missing, quarantined, invalid, unknown-group, unknown-account, and invalid-exposure rows remain in staged denominator counts and are excluded from grouped estimation.",
        ],
    }


def build_cluster_contrasts(
    records: Sequence[Mapping[str, Any]],
    *,
    actions: Iterable[str] = DEFAULT_ACTIONS,
    group_field: str,
    category: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    names = tuple(actions)
    if not names or any(not isinstance(a, str) or not a for a in names):
        raise ClusterContrastError("ACTIONS_INVALID")
    return {
        "schema": SCHEMA,
        "status": "DESCRIPTIVE_CLUSTER_CONTRASTS_COMPLETE",
        "actions": {
            a: cluster_contrast(records, action=a, group_field=group_field, category=category, **kwargs)
            for a in names
        },
        "no_cross_action_denominator": True,
    }
