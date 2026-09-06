"""Coverage-aware, incremental feature joins for the M2 media corpus.

This module is intentionally a join and audit layer.  It keeps one row for
each canonical Reel, preserves corpus receipts and quarantines, and exposes
typed missingness for each evidence modality.  It does not infer scenes,
labels, silence, or performance and it does not fit statistical models.
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = "m2.corpus-features.v1"
STAGE_NAMES = ("acquisition", "transcript", "frames")
ACCEPTED_SCENE_REVIEW_STATES = {"APPROVED", "ACCEPTED", "REVIEWED"}
RATE_FIELDS = (
    "likes_per_1k_views",
    "comments_per_1k_views",
    "reshares_per_1k_views",
    "saves_per_1k_views",
)


class FeatureJoinError(ValueError):
    """Stable input/contract error for the bounded feature join."""


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_object(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _as_int(value: Any) -> int | None:
    return value if type(value) is int else None


def _as_number(value: Any) -> int | float | None:
    if type(value) not in {int, float} or isinstance(value, bool):
        return None
    return value if math.isfinite(float(value)) and value >= 0 else None


def _canonical_key(value: Mapping[str, Any]) -> str:
    reel_id = value.get("reel_id")
    code = value.get("code")
    if isinstance(reel_id, str) and reel_id:
        return reel_id
    if isinstance(code, str) and code:
        return f"instagram:{code}"
    raise FeatureJoinError("canonical_entry_requires_reel_id_or_code")


def load_canonical_manifest(path: str | Path) -> tuple[list[dict[str, Any]], str]:
    """Load and validate the stable canonical identity manifest."""
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    entries = payload.get("entries") if isinstance(payload, dict) else payload
    if not isinstance(entries, list) or not entries:
        raise FeatureJoinError("canonical_manifest_entries_required")
    out: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_codes: set[str] = set()
    seen_indexes: set[int] = set()
    for position, raw in enumerate(entries):
        if not isinstance(raw, dict):
            raise FeatureJoinError("canonical_entry_must_be_object")
        reel_id = _canonical_key(raw)
        code = raw.get("code")
        if not isinstance(code, str) or not code:
            code = reel_id.split(":", 1)[-1]
        identity_index = raw.get("identity_index", position)
        if type(identity_index) is not int or identity_index < 0:
            raise FeatureJoinError("canonical_identity_index_invalid")
        if reel_id in seen_ids or code in seen_codes or identity_index in seen_indexes:
            raise FeatureJoinError("canonical_identity_not_unique")
        seen_ids.add(reel_id)
        seen_codes.add(code)
        seen_indexes.add(identity_index)
        out.append(
            {
                "reel_id": reel_id,
                "code": code,
                "identity_index": identity_index,
                "quarantine_reasons": list(raw.get("quarantine_reasons") or []),
                "research_quarantine_reasons": list(raw.get("research_quarantine_reasons") or []),
            }
        )
    return out, sha256_file(source)


def load_metadata_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Load optional metric/account metadata without changing its semantics."""
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise FeatureJoinError("metadata_row_must_be_object")
            rows.append(value)
    return rows


def _metadata_index(rows: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for raw in rows:
        key = _canonical_key(raw)
        if key in index:
            raise FeatureJoinError("metadata_reel_ids_not_unique")
        index[key] = dict(raw)
    return index


def _safe_artifact_path(root: Path | None, relative: str) -> Path | None:
    if root is None or not isinstance(relative, str) or not relative:
        return None
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts or "\\" in relative or ":" in relative:
        return None
    resolved_root = root.resolve()
    current = resolved_root
    for part in candidate.parts:
        current = current / part
        if current.is_symlink():
            return None
    resolved = current.resolve()
    return resolved if resolved.is_relative_to(resolved_root) and resolved.is_file() else None


def _artifact_map(value: Any) -> dict[str, str]:
    if not isinstance(value, str) or not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _load_verified_artifact(root: Path | None, artifact_map: Mapping[str, Any], suffix: str) -> dict[str, Any]:
    matches = sorted((str(path), str(expected)) for path, expected in artifact_map.items() if str(path).endswith(suffix))
    if not matches:
        return {"state": "MISSING_POINTER", "path": None, "data": None, "hash_state": "NOT_AVAILABLE"}
    relative, expected = matches[-1]
    path = _safe_artifact_path(root, relative)
    if path is None:
        return {"state": "MISSING_FILE", "path": relative, "data": None, "hash_state": "UNAVAILABLE"}
    observed = sha256_file(path)
    expected_clean = expected.removeprefix("sha256:")
    if observed != expected_clean:
        return {"state": "HASH_MISMATCH", "path": relative, "data": None, "hash_state": "FAIL", "observed_sha256": observed, "expected_sha256": expected_clean}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {"state": "INVALID_JSON", "path": relative, "data": None, "hash_state": "PASS"}
    return {"state": "OBSERVED", "path": relative, "data": data, "hash_state": "PASS", "sha256": observed, "expected_sha256": expected_clean}


def _load_verified_file(root: Path | None, artifact_map: Mapping[str, Any], suffix: str) -> dict[str, Any]:
    """Verify a non-JSON artifact referenced by a receipt."""
    matches = sorted((str(path), str(expected)) for path, expected in artifact_map.items() if str(path).endswith(suffix))
    if not matches:
        return {"state": "MISSING_POINTER", "path": None, "hash_state": "NOT_AVAILABLE", "sha256": None, "expected_sha256": None}
    relative, expected = matches[-1]
    path = _safe_artifact_path(root, relative)
    if path is None:
        return {"state": "MISSING_FILE", "path": relative, "hash_state": "UNAVAILABLE", "sha256": None, "expected_sha256": expected.removeprefix("sha256:")}
    expected_clean = expected.removeprefix("sha256:")
    observed = sha256_file(path)
    return {
        "state": "OBSERVED" if observed == expected_clean else "HASH_MISMATCH",
        "path": relative,
        "hash_state": "PASS" if observed == expected_clean else "FAIL",
        "sha256": observed,
        "expected_sha256": expected_clean,
    }


def _source_media_identity(data: Mapping[str, Any], trusted_media_hash: str | None) -> str:
    source_hash = data.get("source_media_hash")
    if trusted_media_hash is None:
        return "UNVERIFIED_MEDIA_HASH"
    if not isinstance(source_hash, str) or not source_hash:
        return "SOURCE_HASH_MISSING"
    return "VERIFIED" if source_hash.removeprefix("sha256:") == trusted_media_hash else "SOURCE_HASH_MISMATCH"


def _read_corpus(corpus_db: str | Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, dict[str, Any]]], dict[str, Any]]:
    raw_path = Path(corpus_db)
    if raw_path.is_symlink():
        raise FeatureJoinError("corpus_database_symlink_rejected")
    path = raw_path.resolve()
    if not path.is_file():
        raise FeatureJoinError("corpus_database_missing")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        reel_rows = [dict(row) for row in connection.execute("SELECT * FROM reels ORDER BY identity_index, code")]
        attempts: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        for row in connection.execute("SELECT * FROM attempts ORDER BY id"):
            value = dict(row)
            attempts[value["reel_id"]][value["stage"]] = value
        bindings = {row["key"]: row["value"] for row in connection.execute("SELECT key,value FROM binding")}
        connection.rollback()
    finally:
        connection.close()
    by_id: dict[str, dict[str, Any]] = {}
    for row in reel_rows:
        key = row["reel_id"]
        if key in by_id:
            raise FeatureJoinError("corpus_reel_ids_not_unique")
        by_id[key] = row
    return by_id, dict(attempts), bindings


def _reviewed_scene_state(reel_id: str, reviewed_scene_rows: Mapping[str, Sequence[Mapping[str, Any]]] | None) -> tuple[str, int]:
    # MVP deliberately has no promotion path. Exact media/annotation/review
    # receipt proofs are not represented in the input contract yet.
    return "DISABLED_MVP", 0


def _metric_fields(metadata: Mapping[str, Any]) -> dict[str, Any]:
    raw_views = metadata.get("views")
    views = _as_number(raw_views)
    rates = {name: _as_number(metadata.get(name)) for name in RATE_FIELDS}
    invalid_fields = [name for name in RATE_FIELDS if metadata.get(name) is not None and rates[name] is None]
    if raw_views is not None and views is None:
        invalid_fields.append("views")
    observed_rates = [value for value in rates.values() if value is not None]
    total = sum(float(value) for value in observed_rates) if len(observed_rates) == len(RATE_FIELDS) else None
    missing = list(metadata.get("metric_missing_fields") or [])
    for name, value in rates.items():
        if value is None and name not in missing:
            missing.append(name)
    numeric_valid = type(metadata.get("numeric_valid")) is bool and metadata.get("numeric_valid") is True
    positive_views = views is not None and float(views) > 0
    account = metadata.get("account_username") or metadata.get("account") or metadata.get("account_cluster_id")
    if not isinstance(account, str) or not account:
        account = None
    if account is None:
        comparability = "BLOCKED_ACCOUNT_CLUSTER_MISSING"
    elif not numeric_valid:
        comparability = "BLOCKED_NUMERIC_INVALID"
    elif not positive_views:
        comparability = "BLOCKED_NONPOSITIVE_VIEWS"
    elif len(observed_rates) != len(RATE_FIELDS):
        comparability = "DESCRIPTIVE_ONLY_MISSING_ACTION_RATE"
    elif not isinstance(metadata.get("snapshot_date"), str) or not metadata.get("snapshot_date"):
        comparability = "DESCRIPTIVE_ONLY_SNAPSHOT_DATE_MISSING"
    else:
        comparability = "DESCRIPTIVE_ONLY_READY"
    return {
        "account_cluster_id": account,
        "views": views,
        **rates,
        "total_actions_per_1k_views": total,
        "metric_missing_fields": sorted(set(str(item) for item in missing)),
        "metric_invalid_fields": sorted(set(invalid_fields)),
        "numeric_valid": numeric_valid,
        "positive_views": positive_views,
        "eligibility_state": metadata.get("eligibility_state"),
        "capture_time_state": metadata.get("capture_time_state"),
        "snapshot_date": metadata.get("snapshot_date"),
        "published_epoch_seconds": metadata.get("published_epoch_seconds"),
        "duration_seconds_source": metadata.get("duration_seconds"),
        "account_baseline_n": metadata.get("author_baseline_n"),
        "account_median_views": metadata.get("author_median_views"),
        "comparability_gate": comparability,
        "model_gate": "DISABLED_NO_FIT_REQUESTED",
    }


def _build_row(
    canonical: Mapping[str, Any],
    corpus: Mapping[str, Any] | None,
    attempt_rows: Mapping[str, Any],
    metadata: Mapping[str, Any],
    artifact_root: Path | None,
    reviewed_scene_rows: Mapping[str, Sequence[Mapping[str, Any]]] | None,
) -> dict[str, Any]:
    reel_id = canonical["reel_id"]
    missing: list[str] = []
    if corpus is None:
        missing.append("CORPUS_RECEIPT_MISSING")
        corpus = {
            "reel_id": reel_id,
            "code": canonical["code"],
            "identity_index": canonical["identity_index"],
            "acquisition_state": "NOT_ATTEMPTED",
            "transcript_state": "NOT_ATTEMPTED",
            "frames_state": "NOT_ATTEMPTED",
            "scene_review_state": "NOT_ATTEMPTED",
            "acquisition_artifact": None,
            "transcript_artifact": None,
            "frames_artifact": None,
        }
    acquisition_state = corpus.get("acquisition_state", "UNKNOWN")
    transcript_state = corpus.get("transcript_state", "UNKNOWN")
    frames_state = corpus.get("frames_state", "UNKNOWN")
    scene_state = corpus.get("scene_review_state", "UNKNOWN")
    if acquisition_state != "OBSERVED":
        missing.append(f"MEDIA_STATE_{acquisition_state}")
    if transcript_state == "NOT_ATTEMPTED":
        missing.append("TRANSCRIPT_NOT_ATTEMPTED")
    elif transcript_state == "EMPTY_OUTPUT_UNVERIFIED":
        missing.append("TRANSCRIPT_EMPTY_UNVERIFIED")
    elif transcript_state == "SUSPICIOUS_TIMINGS":
        missing.append("TRANSCRIPT_SUSPICIOUS_TIMINGS")
    elif transcript_state != "OBSERVED":
        missing.append(f"TRANSCRIPT_STATE_{transcript_state}")
    if frames_state != "OBSERVED":
        missing.append(f"FRAMES_STATE_{frames_state}")
    if scene_state == "NOT_ATTEMPTED":
        missing.append("SCENE_REVIEW_NOT_ATTEMPTED")
    elif scene_state != "REVIEW_PENDING":
        missing.append(f"SCENE_REVIEW_STATE_{scene_state}")

    acquisition_map = _artifact_map(corpus.get("acquisition_artifact"))
    transcript_map = _artifact_map(corpus.get("transcript_artifact"))
    frames_map = _artifact_map(corpus.get("frames_artifact"))
    acquisition_artifact = _load_verified_artifact(artifact_root, acquisition_map, ".media.json")
    media_file = _load_verified_file(artifact_root, acquisition_map, ".mp4")
    transcript_artifact = _load_verified_artifact(artifact_root, transcript_map, "transcription.json")
    frames_artifact = _load_verified_artifact(artifact_root, frames_map, "receipt.json")
    if acquisition_artifact["state"] != "OBSERVED" and acquisition_state == "OBSERVED":
        missing.append(f"MEDIA_ARTIFACT_{acquisition_artifact['state']}")
    if transcript_artifact["state"] != "OBSERVED" and transcript_state == "OBSERVED":
        missing.append(f"TRANSCRIPT_ARTIFACT_{transcript_artifact['state']}")
    if frames_artifact["state"] != "OBSERVED" and frames_state == "OBSERVED":
        missing.append(f"FRAMES_ARTIFACT_{frames_artifact['state']}")

    media_raw = acquisition_artifact.get("data") if isinstance(acquisition_artifact.get("data"), dict) else {}
    corpus_media_hash = media_file.get("expected_sha256")
    observed_media_hash = media_file.get("sha256")
    media_identity_state = "UNVERIFIED"
    if acquisition_artifact["state"] == "OBSERVED" and media_file["state"] == "OBSERVED":
        declared_media_hash = media_raw.get("sha256")
        if not isinstance(declared_media_hash, str) or not declared_media_hash:
            media_identity_state = "MEDIA_JSON_HASH_MISSING"
        elif corpus_media_hash != observed_media_hash or declared_media_hash.removeprefix("sha256:") != observed_media_hash:
            media_identity_state = "MEDIA_HASH_MISMATCH"
        else:
            media_identity_state = "VERIFIED"
    media_verified = acquisition_state == "OBSERVED" and acquisition_artifact["state"] == "OBSERVED" and media_identity_state == "VERIFIED"
    media = media_raw if media_verified else {}
    transcript_raw = transcript_artifact.get("data") if isinstance(transcript_artifact.get("data"), dict) else {}
    frames_raw = frames_artifact.get("data") if isinstance(frames_artifact.get("data"), dict) else {}
    transcript_identity_state = _source_media_identity(transcript_raw, observed_media_hash if media_verified else None)
    frames_identity_state = _source_media_identity(frames_raw, observed_media_hash if media_verified else None)
    transcript_verified = transcript_state == "OBSERVED" and transcript_artifact["state"] == "OBSERVED" and transcript_identity_state == "VERIFIED"
    frames_verified = frames_state == "OBSERVED" and frames_artifact["state"] == "OBSERVED" and frames_identity_state == "VERIFIED"
    transcript = transcript_raw if transcript_verified else {}
    frames = frames_raw if frames_verified else {}
    if acquisition_state == "OBSERVED" and not media_verified:
        missing.append(f"MEDIA_SOURCE_IDENTITY_{media_identity_state}")
    if transcript_state == "OBSERVED" and not transcript_verified:
        missing.append(f"TRANSCRIPT_SOURCE_IDENTITY_{transcript_identity_state}")
    if frames_state == "OBSERVED" and not frames_verified:
        missing.append(f"FRAMES_SOURCE_IDENTITY_{frames_identity_state}")
    tx_segments = transcript.get("segments") if isinstance(transcript.get("segments"), list) else []
    tx_words = transcript.get("words")
    if _as_number(tx_words) is None:
        tx_words = transcript.get("lexical_word_count")
    if transcript_state == "OBSERVED" and transcript_verified and tx_words is None:
        tx_words = transcript.get("raw_word_count")
    if tx_words is not None and _as_number(tx_words) is None:
        tx_words = None
        missing.append("TRANSCRIPT_WORD_COUNT_INVALID")
    if transcript_state == "OBSERVED" and transcript_verified and tx_words is None:
        missing.append("TRANSCRIPT_WORD_COUNT_MISSING")
    duration_ms = media.get("duration_ms")
    duration_seconds = float(duration_ms) / 1000.0 if _as_number(duration_ms) is not None and float(duration_ms) > 0 else None
    words_per_second = float(tx_words) / duration_seconds if duration_seconds and _as_number(tx_words) is not None else None
    aligned_words = transcript.get("aligned_word_count") if transcript_verified else None
    if aligned_words is not None and _as_number(aligned_words) is None:
        aligned_words = None
        missing.append("TRANSCRIPT_ALIGNED_WORD_COUNT_INVALID")
    aligned_words_per_second = float(aligned_words) / duration_seconds if duration_seconds and _as_number(aligned_words) is not None else None
    language = transcript.get("language")
    language_known = isinstance(language, str) and language.strip().lower() not in {"", "unknown", "undetermined", "und"}
    if words_per_second is None:
        rate_comparability = "UNKNOWN_RATE_UNAVAILABLE"
    elif not language_known:
        rate_comparability = "UNKNOWN_LANGUAGE_TOKEN_RATE"
    else:
        rate_comparability = "LANGUAGE_CONDITIONED_TOKEN_RATE"
    frame_budget = frames.get("frame_budget") if isinstance(frames.get("frame_budget"), dict) else {}
    cut_candidates = frames.get("cut_candidates_ms")
    if cut_candidates is None:
        cut_candidates = frames.get("cut_candidates")
    reviewed_state, reviewed_count = _reviewed_scene_state(reel_id, reviewed_scene_rows)
    if reviewed_state != "ACCEPTED":
        missing.append("STRUCTURAL_LABELS_NOT_INDEPENDENTLY_ACCEPTED")

    metrics = _metric_fields(metadata)
    if metrics["account_cluster_id"] is None:
        missing.append("ACCOUNT_CLUSTER_MISSING")
    missing.extend(f"METRIC_MISSING_{field}" for field in metrics["metric_missing_fields"])
    missing.extend(f"METRIC_INVALID_{field}" for field in metrics["metric_invalid_fields"])
    if media.get("has_audio") is not True and acquisition_state == "OBSERVED":
        missing.append("AUDIO_STATE_UNVERIFIED")
    if transcript_state == "EMPTY_OUTPUT_UNVERIFIED":
        missing.append("SILENCE_NOT_PROVEN")
    if canonical["quarantine_reasons"] or canonical["research_quarantine_reasons"]:
        metric_eligibility = "BLOCKED_CANONICAL_QUARANTINE"
    elif metrics["comparability_gate"] != "DESCRIPTIVE_ONLY_READY":
        metric_eligibility = "BLOCKED_METRIC_COMPARABILITY"
    else:
        metric_eligibility = "DESCRIPTIVE_ONLY_ELIGIBLE"

    latest_attempt = {stage: attempt_rows.get(stage) for stage in STAGE_NAMES}
    return {
        "reel_id": reel_id,
        "code": canonical["code"],
        "identity_index": canonical["identity_index"],
        "quarantine_reasons": canonical["quarantine_reasons"],
        "research_quarantine_reasons": canonical["research_quarantine_reasons"],
        "quarantined": bool(canonical["quarantine_reasons"] or canonical["research_quarantine_reasons"]),
        "account_cluster_id": metrics["account_cluster_id"],
        "acquisition_state": acquisition_state,
        "acquisition_attempt_state": (latest_attempt["acquisition"] or {}).get("state"),
        "acquisition_attempt_id": (latest_attempt["acquisition"] or {}).get("id"),
        "media_artifact_state": acquisition_artifact["state"],
        "media_artifact_hash_state": acquisition_artifact["hash_state"],
        "media_file_hash_state": media_file["hash_state"],
        "media_source_identity_state": media_identity_state,
        "media_artifact_verified": media_verified,
        "media_corpus_expected_sha256": corpus_media_hash,
        "media_observed_sha256": observed_media_hash,
        "media_sha256": media.get("sha256") if media_verified else None,
        "media_duration_ms": duration_ms,
        "media_duration_seconds": duration_seconds,
        "media_has_audio": media.get("has_audio"),
        "transcript_state": transcript_state,
        "transcript_attempt_state": (latest_attempt["transcript"] or {}).get("state"),
        "transcript_attempt_id": (latest_attempt["transcript"] or {}).get("id"),
        "transcript_artifact_state": transcript_artifact["state"],
        "transcript_artifact_hash_state": transcript_artifact["hash_state"],
        "transcript_source_identity_state": transcript_identity_state,
        "transcript_artifact_verified": transcript_verified,
        "asr_language": transcript.get("language") if transcript_verified else None,
        "asr_language_probability": transcript.get("language_probability") if transcript_verified else None,
        "transcript_segment_count": len(tx_segments) if transcript_verified else None,
        "transcript_word_count_lexical": tx_words if transcript_verified else None,
        "transcript_aligned_word_count": aligned_words,
        "transcript_words_per_second": words_per_second,
        "transcript_aligned_words_per_second": aligned_words_per_second,
        "transcript_rate_comparability": rate_comparability,
        "transcript_word_timing_state": transcript.get("word_timing") if transcript_verified else None,
        "frames_state": frames_state,
        "frames_attempt_state": (latest_attempt["frames"] or {}).get("state"),
        "frames_attempt_id": (latest_attempt["frames"] or {}).get("id"),
        "frames_artifact_state": frames_artifact["state"],
        "frames_artifact_hash_state": frames_artifact["hash_state"],
        "frames_source_identity_state": frames_identity_state,
        "frames_artifact_verified": frames_verified,
        "frame_observation_state": frames.get("frame_observation_state") if frames_verified else None,
        "frame_sample_count": frame_budget.get("observed_frames") if frames_verified and frame_budget else (frames.get("sample_count") if frames_verified else None),
        "frame_requested_count": frame_budget.get("requested_frames") if frames_verified and frame_budget else None,
        "frame_budget_max": frame_budget.get("max_frames") if frames_verified and frame_budget else None,
        "frame_sampling_truncated": frame_budget.get("truncated") if frames_verified and frame_budget else None,
        "cut_observation_state": frames.get("cut_observation_state") if frames_verified else None,
        "cut_candidate_count": len(cut_candidates) if frames_verified and frames.get("cut_observation_state") == "OBSERVED" and isinstance(cut_candidates, list) else None,
        "cut_sampling_truncated": (frames.get("cut_sampling_disclosure") or {}).get("truncated") if frames_verified else None,
        "scene_review_state": scene_state,
        "reviewed_scene_state": reviewed_state,
        "reviewed_scene_count": reviewed_count,
        "structural_label_state": "ACCEPTED_REVIEWED" if reviewed_state == "ACCEPTED" else "UNAVAILABLE_UNREVIEWED",
        "metric_eligibility_gate": metric_eligibility,
        **metrics,
        "missingness_reasons": sorted(set(missing)),
    }


def _count_states(rows: Sequence[Mapping[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(field)) for row in rows).items()))


def summarize_rows(rows: Sequence[Mapping[str, Any]], *, canonical_count: int, corpus_count: int, bindings: Mapping[str, Any] | None = None) -> dict[str, Any]:
    missingness = Counter(reason for row in rows for reason in row.get("missingness_reasons", []))
    return {
        "schema": SCHEMA,
        "denominators": {
            "canonical_reels": canonical_count,
            "corpus_receipt_reels": corpus_count,
            "output_rows": len(rows),
            "media_observed": sum(row.get("acquisition_state") == "OBSERVED" for row in rows),
            "media_artifact_verified": sum(row.get("media_artifact_verified") is True for row in rows),
            "audio_observed": sum(row.get("media_has_audio") is True for row in rows),
            "transcript_observed": sum(row.get("transcript_state") == "OBSERVED" for row in rows),
            "transcript_artifact_verified": sum(row.get("transcript_artifact_verified") is True for row in rows),
            "transcript_word_bearing": sum((row.get("transcript_word_count_lexical") or 0) > 0 for row in rows if row.get("transcript_state") == "OBSERVED"),
            "frames_observed": sum(row.get("frames_state") == "OBSERVED" for row in rows),
            "frames_artifact_verified": sum(row.get("frames_artifact_verified") is True for row in rows),
            "scene_review_pending_or_attempted": sum(row.get("scene_review_state") in {"REVIEW_PENDING", "REVIEWED", "APPROVED", "ACCEPTED"} for row in rows),
            "independently_accepted_scene_labels": sum(row.get("structural_label_state") == "ACCEPTED_REVIEWED" for row in rows),
            "quarantined": sum(bool(row.get("quarantined")) for row in rows),
        },
        "state_counts": {field: _count_states(rows, field) for field in ("acquisition_state", "transcript_state", "frames_state", "scene_review_state", "comparability_gate", "metric_eligibility_gate", "transcript_rate_comparability")},
        "missingness_counts": dict(sorted(missingness.items())),
        "bindings": dict(bindings or {}),
        "gates": {
            "account_cluster_ready": "per-row account_cluster_id is explicit; missing accounts remain null",
            "descriptive_comparability": "per-row comparability_gate only; no cross-row model fitting",
            "word_rate_comparability": "language-conditioned token rates only; no pooled cross-language interpretation",
            "structural_labels": "only separately supplied accepted maker/reviewer records can set ACCEPTED_REVIEWED",
            "causal_or_predictive_claims": "BLOCKED_NOT_ESTIMATED",
            "p_values_or_regression": "NOT_RUN_BY_CONTRACT",
        },
    }


def build_feature_dataset(
    canonical_entries: Sequence[Mapping[str, Any]],
    corpus_db: str | Path,
    *,
    artifact_root: str | Path | None = None,
    metadata_rows: Iterable[Mapping[str, Any]] = (),
    reviewed_scene_rows: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Build one coverage-aware row per canonical Reel from read-only receipts."""
    canonical = [dict(entry) for entry in canonical_entries]
    if not canonical:
        raise FeatureJoinError("canonical_entries_required")
    canonical_ids = [_canonical_key(entry) for entry in canonical]
    if len(set(canonical_ids)) != len(canonical_ids):
        raise FeatureJoinError("canonical_entries_not_unique")
    normalized = []
    for entry in canonical:
        item = dict(entry)
        item["reel_id"] = _canonical_key(item)
        item.setdefault("code", item["reel_id"].split(":", 1)[-1])
        item.setdefault("identity_index", len(normalized))
        item.setdefault("quarantine_reasons", [])
        item.setdefault("research_quarantine_reasons", [])
        normalized.append(item)
    metadata = _metadata_index(metadata_rows)
    corpus_by_id, attempts, bindings = _read_corpus(corpus_db)
    if artifact_root is not None:
        raw_root = Path(artifact_root)
        if raw_root.is_symlink():
            raise FeatureJoinError("artifact_root_symlink_rejected")
        root = raw_root.resolve()
    else:
        root = None
    rows = [
        _build_row(entry, corpus_by_id.get(entry["reel_id"]), attempts.get(entry["reel_id"], {}), metadata.get(entry["reel_id"], {}), root, reviewed_scene_rows)
        for entry in normalized
    ]
    summary = summarize_rows(rows, canonical_count=len(normalized), corpus_count=len(corpus_by_id), bindings=bindings)
    return {"schema": SCHEMA, "rows": rows, "summary": summary}


def build_feature_dataset_from_files(
    manifest_path: str | Path,
    corpus_db: str | Path,
    *,
    artifact_root: str | Path | None = None,
    metadata_path: str | Path | None = None,
    reviewed_scene_rows: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    entries, manifest_sha256 = load_canonical_manifest(manifest_path)
    metadata = load_metadata_jsonl(metadata_path) if metadata_path is not None else []
    result = build_feature_dataset(entries, corpus_db, artifact_root=artifact_root, metadata_rows=metadata, reviewed_scene_rows=reviewed_scene_rows)
    binding_manifest_sha256 = result["summary"]["bindings"].get("manifest_sha256")
    if not isinstance(binding_manifest_sha256, str):
        raise FeatureJoinError("manifest_binding_missing")
    if binding_manifest_sha256 != manifest_sha256:
        raise FeatureJoinError("manifest_binding_mismatch")
    result["provenance"] = {
        "manifest_sha256": manifest_sha256,
        "manifest_entry_count": len(entries),
        "metadata_row_count": len(metadata),
        "metadata_sha256": sha256_file(metadata_path) if metadata_path is not None else None,
        "corpus_binding_manifest_sha256": binding_manifest_sha256,
        "feature_module_schema": SCHEMA,
        "feature_module_sha256": sha256_file(Path(__file__)),
    }
    return result


__all__ = [
    "FeatureJoinError",
    "SCHEMA",
    "build_feature_dataset",
    "build_feature_dataset_from_files",
    "load_canonical_manifest",
    "load_metadata_jsonl",
    "sha256_file",
    "summarize_rows",
]
