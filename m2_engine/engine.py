"""Deterministic, standard-library-only M2 Signal and Studio contracts.

This module intentionally has no network or provider implementation.  It turns
frozen local records into reviewable artifacts and typed partial/failure states.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit


SCHEMA_VERSION = "m2.vertical-slice.v1"
FORMULA_REGISTRY: dict[str, Any] = {
    "formula_id": "m2.robust-z.v1",
    "transform": "x = ln(1 + views)",
    "robust_z": "z = 0.6745 * (x - median(x)) / MAD(x)",
    "mad_definition": "median(abs(x - median(x)))",
    "epsilon": 1e-9,
    "minimum_baseline": 5,
    "group_dimensions": ["creator_id", "platform", "format", "duration_bucket"],
    "component_weights": {
        "views": 0.30,
        "engagement": 0.20,
        "shares_or_reposts": 0.20,
        "comments": 0.10,
        "early_velocity": 0.20,
    },
    "missing_component_policy": "visible omission and renormalization; never null-to-zero",
}

REQUIRED_ROUTE_FIELDS = (
    "route_id",
    "topic",
    "source_ids",
    "evidence_ids",
    "claim_evidence_map",
    "audience",
    "job",
    "pain",
    "why_now",
    "market_context",
    "angle",
    "mechanisms",
    "prohibited_copy",
    "m2_contribution",
    "m2_proof",
    "strategic_placement",
    "production_complexity",
)
ALLOWED_RESOLVE_OPERATIONS = {
    "plan_bins",
    "plan_timeline",
    "plan_markers",
    "plan_captions",
    "plan_export_metadata",
}


class M2Error(ValueError):
    """Typed unrecoverable local contract error."""

    def __init__(self, code: str, message: str, *, recoverable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.recoverable = recoverable

    def as_failure(self, stage: str, record_id: str | None = None) -> dict[str, Any]:
        return failure(self.code, str(self), stage=stage, record_id=record_id, recoverable=self.recoverable)


@dataclass(frozen=True)
class AdapterResult:
    status: str
    records: tuple[dict[str, Any], ...]
    failure: dict[str, Any] | None


class DisabledProviderAdapter:
    """Explicitly disabled provider boundary; never performs I/O."""

    def __init__(self, provider: str, reason: str = "provider mode is disabled") -> None:
        self.provider = provider
        self.reason = reason

    def fetch(self, _request: Mapping[str, Any] | None = None) -> AdapterResult:
        return AdapterResult(
            status="DISABLED",
            records=(),
            failure=failure(
                "CAPABILITY_UNAVAILABLE",
                f"{self.provider}: {self.reason}",
                stage="adapter",
                recoverable=True,
                next_action="retain seed-only state or obtain a separately approved capability",
            ),
        )


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def json_artifact_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def json_artifact_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json_artifact_bytes(value)).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def failure(
    code: str,
    message: str,
    *,
    stage: str,
    recoverable: bool,
    record_id: str | None = None,
    next_action: str = "correct the local input and rerun the bounded stage",
) -> dict[str, Any]:
    return {
        "failure_id": canonical_hash([stage, code, record_id, message]),
        "code": code,
        "stage": stage,
        "record_id": record_id,
        "message": message,
        "recoverable": recoverable,
        "next_action": next_action,
    }


def _required_string(record: Mapping[str, Any], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise M2Error("MALFORMED_PAYLOAD", f"{field} must be a non-empty string", recoverable=True)
    return value


def canonicalize_url(value: str) -> str:
    try:
        parts = urlsplit(value)
    except ValueError as exc:
        raise M2Error("INVALID_URL", f"invalid URL: {value}", recoverable=True) from exc
    if parts.scheme.lower() != "https" or not parts.netloc:
        raise M2Error("INVALID_URL", f"only absolute HTTPS URLs are admitted: {value}", recoverable=True)
    host = parts.hostname.lower() if parts.hostname else ""
    if host.startswith("www."):
        host = host[4:]
    port = f":{parts.port}" if parts.port else ""
    path = "/" + "/".join(segment for segment in parts.path.split("/") if segment)
    if path != "/":
        path += "/"
    return urlunsplit(("https", host + port, path, "", ""))


def _seed_record(
    seed: Mapping[str, Any], *, entity_type: str, platform: str, cohort_id: str, provenance: Mapping[str, Any]
) -> dict[str, Any]:
    reference_id = _required_string(seed, "reference_id")
    prefix = "CR-" if entity_type == "creator_reference" else "PR-"
    if not reference_id.startswith(prefix):
        raise M2Error("INVALID_REFERENCE_ID", f"{reference_id} is not a {entity_type} ID", recoverable=True)
    exact_url = _required_string(seed, "exact_url")
    canonical_url = canonicalize_url(exact_url)
    aliases = seed.get("aliases", [])
    if not isinstance(aliases, list) or any(not isinstance(value, str) for value in aliases):
        raise M2Error("MALFORMED_PAYLOAD", f"{reference_id} aliases must be strings", recoverable=True)
    alias_entries = [
        {"exact_url": value, "canonical_url": canonicalize_url(value)} for value in aliases
    ]
    parent = seed.get("parent_creator_reference_id") if entity_type == "post_reference" else None
    metrics = seed.get("metrics") if entity_type == "post_reference" else None
    if metrics is not None:
        if not isinstance(metrics, dict):
            raise M2Error("MALFORMED_PAYLOAD", f"{reference_id} metrics must be an object", recoverable=True)
        for name, value in metrics.items():
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0):
                raise M2Error("IMPOSSIBLE_METRIC", f"{reference_id}.{name} must be null or non-negative", recoverable=True)
    raw = dict(seed)
    return {
        "schema": "m2.seed-record.v1",
        "reference_id": reference_id,
        "entity_type": entity_type,
        "platform": platform,
        "label": seed.get("label"),
        "exact_url": exact_url,
        "canonical_url": canonical_url,
        "aliases": alias_entries,
        "parent_creator_reference_id": parent,
        "parent_state": (
            "NOT_APPLICABLE"
            if entity_type == "creator_reference"
            else "RESOLVED"
            if isinstance(parent, str) and parent
            else "GAP_UNRESOLVED"
        ),
        "evidence_status": seed.get("evidence_status", "seed_only"),
        "metrics": metrics,
        "role_vector": seed.get("role_vector") if entity_type == "creator_reference" else None,
        "role_vector_state": seed.get("role_vector_state") if entity_type == "creator_reference" else None,
        "cohort_id": cohort_id,
        "source_state": provenance.get("live_collection_state", "NOT_RUN"),
        "claim_label": "GAP",
        "rights_state": "REFERENCE_ONLY_SEED_ONLY",
        "raw_hash": canonical_hash(raw),
    }


def import_golden_cohort(cohort: Mapping[str, Any]) -> dict[str, Any]:
    if cohort.get("schema") != "m2.golden-reference-cohort.v1":
        raise M2Error("SCHEMA_DRIFT", "unsupported golden cohort schema", recoverable=True)
    cohort_id = _required_string(cohort, "cohort_id")
    platform = _required_string(cohort, "platform")
    provenance = cohort.get("provenance")
    if not isinstance(provenance, dict):
        raise M2Error("MALFORMED_PAYLOAD", "cohort provenance must be an object", recoverable=True)
    creators = cohort.get("creator_references")
    posts = cohort.get("post_references")
    if not isinstance(creators, list) or not isinstance(posts, list):
        raise M2Error("MALFORMED_PAYLOAD", "creator_references and post_references must be arrays", recoverable=True)

    admitted: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    seen_ids: dict[str, str] = {}
    seen_exact_urls: dict[str, str] = {}
    seen_canonical_urls: dict[str, str] = {}
    creator_ids = {
        item.get("reference_id") for item in creators if isinstance(item, dict) and isinstance(item.get("reference_id"), str)
    }
    for entity_type, seeds in (("creator_reference", creators), ("post_reference", posts)):
        for index, seed in enumerate(seeds):
            if not isinstance(seed, dict):
                quarantined.append(failure("MALFORMED_PAYLOAD", "seed must be an object", stage="seed_import", record_id=f"index:{index}", recoverable=True))
                continue
            record_id = seed.get("reference_id") if isinstance(seed.get("reference_id"), str) else f"index:{index}"
            try:
                record = _seed_record(seed, entity_type=entity_type, platform=platform, cohort_id=cohort_id, provenance=provenance)
                collisions: list[str] = []
                if record["reference_id"] in seen_ids:
                    collisions.append(f"duplicate reference_id with {seen_ids[record['reference_id']]}")
                if record["exact_url"] in seen_exact_urls:
                    collisions.append(f"duplicate exact_url with {seen_exact_urls[record['exact_url']]}")
                if record["canonical_url"] in seen_canonical_urls:
                    collisions.append(f"duplicate canonical_url with {seen_canonical_urls[record['canonical_url']]}")
                if collisions:
                    quarantined.append(failure("DUPLICATE_SEED", "; ".join(collisions), stage="seed_import", record_id=record_id, recoverable=True))
                    continue
                if entity_type == "post_reference" and record["parent_creator_reference_id"] not in (None, *creator_ids):
                    quarantined.append(failure("UNRESOLVED_PARENT", "parent_creator_reference_id does not resolve", stage="seed_import", record_id=record_id, recoverable=True))
                    continue
                seen_ids[record["reference_id"]] = record["reference_id"]
                seen_exact_urls[record["exact_url"]] = record["reference_id"]
                seen_canonical_urls[record["canonical_url"]] = record["reference_id"]
                admitted.append(record)
            except M2Error as exc:
                quarantined.append(exc.as_failure("seed_import", record_id))

    alias_ledger = [
        {
            "reference_id": record["reference_id"],
            "canonical_seed_url": record["exact_url"],
            "alias_exact_url": alias["exact_url"],
            "alias_canonical_url": alias["canonical_url"],
            "resolution_state": "PRESERVED_UNRESOLVED_VARIANT",
        }
        for record in admitted
        for alias in record["aliases"]
    ]
    return {
        "schema": "m2.normalized-cohort.v1",
        "cohort_id": cohort_id,
        "creator_records": [r for r in admitted if r["entity_type"] == "creator_reference"],
        "post_records": [r for r in admitted if r["entity_type"] == "post_reference"],
        "alias_ledger": alias_ledger,
        "quarantine": quarantined,
        "limitations": list(cohort.get("limitations", [])),
        "content_hash": canonical_hash(admitted),
    }


def _duration_bucket(duration_seconds: int | float | None) -> str | None:
    if duration_seconds is None:
        return None
    if duration_seconds <= 30:
        return "0-30s"
    if duration_seconds <= 60:
        return "31-60s"
    if duration_seconds <= 180:
        return "61-180s"
    if duration_seconds <= 600:
        return "181-600s"
    return "601s+"


def _resolve_registered_raw_file(project_root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise M2Error("INVALID_RAW_PAYLOAD_PATH", "raw_payload_path must be safe and project-relative", recoverable=True)
    resolved = (project_root / path).resolve()
    root = project_root.resolve()
    if root not in (resolved, *resolved.parents) or not resolved.is_file():
        raise M2Error("INVALID_RAW_PAYLOAD_PATH", "registered raw payload is missing or outside the project", recoverable=True)
    return resolved


def import_registered_sources(registration_path: Path, *, project_root: Path) -> dict[str, Any]:
    """Validate registered public metadata without collecting or embedding raw payloads."""
    records: list[dict[str, Any]] = []
    snapshot_inputs: list[dict[str, Any]] = []
    quarantine: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    try:
        lines = registration_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise M2Error("INPUT_IO_ERROR", f"could not read source registration: {exc}") from exc
    for registration_line, text in enumerate(lines, 1):
        record_id = f"registration-line:{registration_line}"
        try:
            try:
                item = json.loads(text)
            except json.JSONDecodeError as exc:
                raise M2Error("MALFORMED_PAYLOAD", "registration line is not valid JSON", recoverable=True) from exc
            if not isinstance(item, dict):
                raise M2Error("MALFORMED_PAYLOAD", "registration record must be an object", recoverable=True)
            source_id = _required_string(item, "source_id")
            record_id = source_id
            platform = _required_string(item, "platform")
            canonical_url = _required_string(item, "canonical_url")
            parts = urlsplit(canonical_url)
            if parts.scheme != "https" or not parts.netloc:
                raise M2Error("INVALID_URL", "collected canonical_url must be absolute HTTPS", recoverable=True)
            native_id = _required_string(item, "public_native_id")
            creator_id = _required_string(item, "creator_id")
            collected_at = _required_string(item, "collected_at")
            if not _timestamp_is_valid(collected_at):
                raise M2Error("INVALID_TIMESTAMP", "collected_at must be an offset ISO date-time", recoverable=True)
            provider = _required_string(item, "provider")
            provider_version = _required_string(item, "provider_version")
            raw_payload_path = _required_string(item, "raw_payload_path")
            raw_payload_sha256 = _required_string(item, "raw_payload_sha256")
            if len(raw_payload_sha256) != 64 or any(char not in "0123456789abcdef" for char in raw_payload_sha256):
                raise M2Error("INVALID_RAW_HASH", "raw_payload_sha256 must be 64 lowercase hex characters", recoverable=True)
            raw_record_line = item.get("raw_record_line")
            if isinstance(raw_record_line, bool) or not isinstance(raw_record_line, int) or raw_record_line < 1:
                raise M2Error("INVALID_RAW_RECORD_LINE", "raw_record_line must be a positive integer", recoverable=True)
            raw_file = _resolve_registered_raw_file(project_root, raw_payload_path)
            if file_hash(raw_file) != "sha256:" + raw_payload_sha256:
                raise M2Error("RAW_HASH_MISMATCH", "registered raw payload hash does not match the local file", recoverable=True)
            raw_lines = raw_file.read_text(encoding="utf-8").splitlines()
            if raw_record_line > len(raw_lines):
                raise M2Error("INVALID_RAW_RECORD_LINE", "raw_record_line exceeds the raw payload", recoverable=True)
            try:
                raw_pointer_record = json.loads(raw_lines[raw_record_line - 1])
            except json.JSONDecodeError as exc:
                raise M2Error("MALFORMED_RAW_PAYLOAD", "registered raw record is not valid JSON", recoverable=True) from exc
            if not isinstance(raw_pointer_record, dict) or raw_pointer_record.get("id") != native_id:
                raise M2Error("RAW_RECORD_MISMATCH", "registered native ID does not match the raw record line", recoverable=True)
            metrics = item.get("metric_snapshot")
            if not isinstance(metrics, dict):
                raise M2Error("MALFORMED_PAYLOAD", "metric_snapshot must be an object", recoverable=True)
            duration = item.get("duration_seconds")
            if duration is not None and (isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration < 0):
                raise M2Error("IMPOSSIBLE_DURATION", "duration_seconds must be null or non-negative", recoverable=True)
            if source_id in seen_ids:
                raise M2Error("DUPLICATE_SOURCE_ID", "collected source_id is duplicated", recoverable=True)
            if canonical_url in seen_urls:
                raise M2Error("DUPLICATE_SOURCE_URL", "collected canonical_url is duplicated", recoverable=True)
            seen_ids.add(source_id)
            seen_urls.add(canonical_url)
            normalized = {
                "schema": "m2.collected-source-record.v1",
                "source_id": source_id,
                "entity_type": "collected_post_metadata",
                "query_id": item.get("query_id"),
                "platform": platform,
                "canonical_url": canonical_url,
                "public_native_id": native_id,
                "creator_id": creator_id,
                "creator_name": item.get("creator_name"),
                "title": item.get("title"),
                "published_at": item.get("published_at"),
                "collected_at": collected_at,
                "duration_seconds": duration,
                "provider": provider,
                "provider_version": provider_version,
                "raw_payload_path": raw_payload_path,
                "raw_payload_sha256": raw_payload_sha256,
                "raw_record_line": raw_record_line,
                "raw_hash": "sha256:" + raw_payload_sha256,
                "registration_line": registration_line,
                "registration_hash": canonical_hash(item),
                "metrics": {name: metrics.get(name) for name in ("views", "likes", "comments", "shares", "reposts", "saves")},
                "access_state": item.get("access_state"),
                "rights_state": item.get("rights_state"),
                "analysis_status": item.get("analysis_status"),
                "claim_label": "FACT",
                "limitations": list(item.get("limitations", [])),
            }
            records.append(normalized)
            snapshot_inputs.append(
                {
                    "snapshot_id": f"MS-{source_id}",
                    "post_id": source_id,
                    "creator_id": creator_id,
                    "platform": platform,
                    "format": "video",
                    "duration_bucket": _duration_bucket(duration),
                    "collected_at": collected_at,
                    "provider": provider,
                    "metric_semantics_version": f"{provider}.public-search-metadata.{provider_version}",
                    "metrics": normalized["metrics"],
                    "raw_payload": {"path": raw_payload_path, "line": raw_record_line, "native_id": native_id},
                    "raw_payload_path": raw_payload_path,
                    "raw_payload_sha256": raw_payload_sha256,
                    "raw_record_line": raw_record_line,
                    "registration_line": registration_line,
                }
            )
        except M2Error as exc:
            quarantine.append(exc.as_failure("registered_source_import", record_id))
    return {"records": records, "snapshot_inputs": snapshot_inputs, "quarantine": quarantine}


def _timestamp_is_valid(value: Any) -> bool:
    if not isinstance(value, str) or "T" not in value:
        return False
    try:
        from datetime import datetime

        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def normalize_metric_snapshots(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    snapshots: list[dict[str, Any]] = []
    quarantine: list[dict[str, Any]] = []
    identities: dict[tuple[str, str, str], str] = {}
    for index, record in enumerate(records):
        record_id = record.get("snapshot_id") if isinstance(record.get("snapshot_id"), str) else f"index:{index}"
        try:
            post_id = _required_string(record, "post_id")
            collected_at = _required_string(record, "collected_at")
            semantics_version = _required_string(record, "metric_semantics_version")
            provider = _required_string(record, "provider")
            raw_payload = record.get("raw_payload")
            if not isinstance(raw_payload, dict):
                raise M2Error("MALFORMED_PAYLOAD", "raw_payload must be an object", recoverable=True)
            if not _timestamp_is_valid(collected_at):
                raise M2Error("INVALID_TIMESTAMP", "collected_at must be an offset ISO date-time", recoverable=True)
            metrics = record.get("metrics")
            if not isinstance(metrics, dict):
                raise M2Error("MALFORMED_PAYLOAD", "metrics must be an object", recoverable=True)
            normalized_metrics: dict[str, int | float | None] = {}
            for name in ("views", "likes", "comments", "shares", "reposts", "saves"):
                value = metrics.get(name)
                if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
                    raise M2Error("IMPOSSIBLE_METRIC", f"{name} must be null or a finite non-negative number", recoverable=True)
                normalized_metrics[name] = value
            identity = (post_id, collected_at, semantics_version)
            provided_raw_hash = record.get("raw_payload_sha256")
            if provided_raw_hash is not None:
                if not isinstance(provided_raw_hash, str) or len(provided_raw_hash) != 64 or any(char not in "0123456789abcdef" for char in provided_raw_hash):
                    raise M2Error("INVALID_RAW_HASH", "raw_payload_sha256 must be 64 lowercase hex characters", recoverable=True)
                raw_hash = "sha256:" + provided_raw_hash
            else:
                raw_hash = canonical_hash(raw_payload)
            immutable_hash = canonical_hash({"identity": identity, "provider": provider, "metrics": normalized_metrics, "raw_hash": raw_hash})
            if identity in identities:
                code = "DUPLICATE_SNAPSHOT" if identities[identity] == immutable_hash else "SNAPSHOT_IMMUTABILITY_CONFLICT"
                raise M2Error(code, "metric snapshot identity is append-only and already exists", recoverable=True)
            identities[identity] = immutable_hash
            snapshots.append(
                {
                    "schema": "m2.metric-snapshot.v1",
                    "snapshot_id": record.get("snapshot_id") or "MS-" + immutable_hash.split(":", 1)[1][:20].upper(),
                    "post_id": post_id,
                    "creator_id": record.get("creator_id"),
                    "platform": record.get("platform"),
                    "format": record.get("format"),
                    "duration_bucket": record.get("duration_bucket"),
                    "collected_at": collected_at,
                    "provider": provider,
                    "metric_semantics_version": semantics_version,
                    "raw_hash": raw_hash,
                    "raw_payload_path": record.get("raw_payload_path"),
                    "raw_record_line": record.get("raw_record_line"),
                    "registration_line": record.get("registration_line"),
                    "metrics": normalized_metrics,
                    "immutable_hash": immutable_hash,
                }
            )
        except M2Error as exc:
            quarantine.append(exc.as_failure("metric_snapshot", record_id))
    return {"snapshots": snapshots, "quarantine": quarantine}


def robust_score_records(snapshots: Sequence[Mapping[str, Any]], minimum_baseline: int | None = None) -> list[dict[str, Any]]:
    minimum = minimum_baseline or int(FORMULA_REGISTRY["minimum_baseline"])
    grouped: dict[tuple[Any, ...], list[Mapping[str, Any]]] = {}
    for snapshot in snapshots:
        key = tuple(snapshot.get(name) for name in FORMULA_REGISTRY["group_dimensions"])
        grouped.setdefault(key, []).append(snapshot)
    output: list[dict[str, Any]] = []
    for key in sorted(grouped, key=lambda item: canonical_json(item)):
        group = grouped[key]
        valid = [item for item in group if item.get("metrics", {}).get("views") is not None]
        transformed = [math.log1p(float(item["metrics"]["views"])) for item in valid]
        median = statistics.median(transformed) if transformed else None
        mad = statistics.median(abs(value - median) for value in transformed) if transformed else None
        baseline_reason = None
        if any(value is None for value in key):
            baseline_reason = "GROUP_IDENTITY_MISSING"
        elif len(valid) < minimum:
            baseline_reason = "INSUFFICIENT_BASELINE"
        elif mad is None or mad <= float(FORMULA_REGISTRY["epsilon"]):
            baseline_reason = "ZERO_OR_NEAR_ZERO_MAD"
        for item in group:
            views = item.get("metrics", {}).get("views")
            reason = "MISSING_VIEWS" if views is None else baseline_reason
            z_value = None
            x_value = math.log1p(float(views)) if views is not None else None
            if reason is None and x_value is not None and median is not None and mad is not None:
                z_value = 0.6745 * (x_value - median) / mad
            output.append(
                {
                    "schema": "m2.score-decomposition.v1",
                    "snapshot_id": item.get("snapshot_id"),
                    "formula_id": FORMULA_REGISTRY["formula_id"],
                    "group": dict(zip(FORMULA_REGISTRY["group_dimensions"], key)),
                    "baseline_count": len(valid),
                    "minimum_baseline": minimum,
                    "transformed_views": x_value,
                    "baseline_median": median,
                    "baseline_mad": mad,
                    "robust_z_views": z_value,
                    "component_weights": dict(FORMULA_REGISTRY["component_weights"]),
                    "available_components": ["views"] if z_value is not None else [],
                    "renormalized_weights": {"views": 1.0} if z_value is not None else {},
                    "score": z_value,
                    "status": "SCORED" if z_value is not None else "GAP",
                    "gap_reason": reason,
                }
            )
    return sorted(output, key=lambda item: str(item.get("snapshot_id")))


def validate_transcript_payload(payload: Any) -> dict[str, Any] | None:
    if payload is None:
        return failure("TRANSCRIPT_UNAVAILABLE", "transcript is absent", stage="transcript", recoverable=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("segments"), list):
        return failure("MALFORMED_TRANSCRIPT", "transcript payload must contain a segments array", stage="transcript", recoverable=True)
    for segment in payload["segments"]:
        if not isinstance(segment, dict) or not isinstance(segment.get("text"), str) or not segment["text"].strip():
            return failure("MALFORMED_TRANSCRIPT", "every transcript segment needs text", stage="transcript", recoverable=True)
    return None


def validate_media_path(value: str, *, allowed_root: Path) -> dict[str, Any] | None:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return failure("INVALID_MEDIA_PATH", "media path must be project-relative and non-escaping", stage="media", recoverable=True)
    resolved = (allowed_root / path).resolve()
    if allowed_root.resolve() not in (resolved, *resolved.parents) or not resolved.is_file():
        return failure("INVALID_MEDIA_PATH", "media path is missing or outside the allowed root", stage="media", recoverable=True)
    return None


def validate_resolve_operation(operation: str) -> dict[str, Any] | None:
    if operation not in ALLOWED_RESOLVE_OPERATIONS:
        return failure(
            "UNSUPPORTED_RESOLVE_OPERATION",
            f"Resolve operation is not supported in provider-disabled planning: {operation}",
            stage="edit",
            recoverable=True,
            next_action="retain the provider-neutral edit instruction as BLOCKED_APPROVAL",
        )
    return None


def validate_evidence_registry(
    registry: Mapping[str, Any] | None, artifact_hashes: Mapping[str, str] | None
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    if not isinstance(registry, Mapping):
        return [failure("EVIDENCE_REGISTRY_MISSING", "a persisted evidence registry is required", stage="evidence_validation", recoverable=True)]
    if registry.get("schema") != "m2.first-party-evidence-registry.v1":
        failures.append(failure("SCHEMA_DRIFT", "unsupported evidence registry schema", stage="evidence_validation", recoverable=True))
    records = registry.get("records")
    if not isinstance(records, list) or not records:
        failures.append(failure("EVIDENCE_REGISTRY_EMPTY", "evidence registry requires records", stage="evidence_validation", recoverable=True))
        return failures
    hashes = artifact_hashes or {}
    seen_sources: set[str] = set()
    seen_evidence: set[str] = set()
    for index, record in enumerate(records):
        record_id = f"registry:{index}"
        if not isinstance(record, Mapping):
            failures.append(failure("EVIDENCE_RECORD_INVALID", "registry record must be an object", stage="evidence_validation", record_id=record_id, recoverable=True))
            continue
        try:
            source_id = _required_string(record, "source_id")
            evidence_id = _required_string(record, "evidence_id")
            path_root = _required_string(record, "path_root")
            relative_path = _required_string(record, "path")
            declared_hash = _required_string(record, "sha256")
        except M2Error as exc:
            failures.append(exc.as_failure("evidence_validation", record_id))
            continue
        if path_root not in {"run_input", "output_dir"}:
            failures.append(failure("EVIDENCE_PATH_INVALID", "path_root must be run_input or output_dir", stage="evidence_validation", record_id=evidence_id, recoverable=True))
        relative = Path(relative_path)
        if relative.is_absolute() or ".." in relative.parts:
            failures.append(failure("EVIDENCE_PATH_INVALID", "evidence path must be safe and relative", stage="evidence_validation", record_id=evidence_id, recoverable=True))
        if source_id in seen_sources or evidence_id in seen_evidence:
            failures.append(failure("EVIDENCE_ID_DUPLICATE", "source_id and evidence_id must be unique", stage="evidence_validation", record_id=evidence_id, recoverable=True))
        seen_sources.add(source_id)
        seen_evidence.add(evidence_id)
        key = f"{path_root}:{relative_path}"
        observed_hash = hashes.get(key)
        if observed_hash is None:
            failures.append(failure("EVIDENCE_PATH_UNRESOLVED", f"evidence path is not resolvable: {key}", stage="evidence_validation", record_id=evidence_id, recoverable=True))
        elif observed_hash != declared_hash:
            failures.append(failure("EVIDENCE_HASH_MISMATCH", f"evidence hash mismatch: {key}", stage="evidence_validation", record_id=evidence_id, recoverable=True))
    return failures


def validate_daily_route_collection(
    collection: Mapping[str, Any],
    evidence_registry: Mapping[str, Any] | None = None,
    artifact_hashes: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    failures.extend(validate_evidence_registry(evidence_registry, artifact_hashes))
    registry_records = evidence_registry.get("records", []) if isinstance(evidence_registry, Mapping) else []
    by_source = {item.get("source_id"): item for item in registry_records if isinstance(item, Mapping)}
    by_evidence = {item.get("evidence_id"): item for item in registry_records if isinstance(item, Mapping)}
    routes = collection.get("routes")
    if collection.get("schema") != "m2.daily-route-collection.v1":
        failures.append(failure("SCHEMA_DRIFT", "unsupported DailyRouteCollection schema", stage="route_validation", recoverable=True))
    if not isinstance(routes, list) or not routes:
        failures.append(failure("ROUTES_MISSING", "DailyRouteCollection requires routes", stage="route_validation", recoverable=True))
        return failures
    seen_ids: set[str] = set()
    for index, route in enumerate(routes):
        record_id = route.get("route_id") if isinstance(route, dict) else f"index:{index}"
        if not isinstance(route, dict):
            failures.append(failure("MALFORMED_ROUTE", "route must be an object", stage="route_validation", record_id=record_id, recoverable=True))
            continue
        for field in REQUIRED_ROUTE_FIELDS:
            value = route.get(field)
            if value is None or value == "" or value == [] or value == {}:
                failures.append(failure("ROUTE_FIELD_MISSING", f"required route field is missing: {field}", stage="route_validation", record_id=record_id, recoverable=True))
        if record_id in seen_ids:
            failures.append(failure("DUPLICATE_ROUTE_ID", "route_id must be unique", stage="route_validation", record_id=record_id, recoverable=True))
        if isinstance(record_id, str):
            seen_ids.add(record_id)
        for field in ("source_ids", "evidence_ids", "mechanisms", "prohibited_copy"):
            value = route.get(field)
            if value is not None and (not isinstance(value, list) or not value or any(not isinstance(item, str) or not item.strip() for item in value)):
                failures.append(failure("ROUTE_FIELD_INVALID", f"{field} must be a non-empty string array", stage="route_validation", record_id=record_id, recoverable=True))
        source_ids = route.get("source_ids") if isinstance(route.get("source_ids"), list) else []
        evidence_ids = route.get("evidence_ids") if isinstance(route.get("evidence_ids"), list) else []
        for source_id in source_ids:
            registered = by_source.get(source_id)
            if registered is None:
                failures.append(failure("SOURCE_ID_UNRESOLVED", f"source_id is absent from evidence registry: {source_id}", stage="route_validation", record_id=record_id, recoverable=True))
            elif registered.get("evidence_id") not in evidence_ids:
                failures.append(failure("SOURCE_EVIDENCE_PAIR_MISMATCH", f"source_id is not paired with its registered evidence_id: {source_id}", stage="route_validation", record_id=record_id, recoverable=True))
        for evidence_id in evidence_ids:
            registered = by_evidence.get(evidence_id)
            if registered is None:
                failures.append(failure("EVIDENCE_ID_UNRESOLVED", f"evidence_id is absent from evidence registry: {evidence_id}", stage="route_validation", record_id=record_id, recoverable=True))
            elif registered.get("source_id") not in source_ids:
                failures.append(failure("SOURCE_EVIDENCE_PAIR_MISMATCH", f"evidence_id is not paired with its registered source_id: {evidence_id}", stage="route_validation", record_id=record_id, recoverable=True))
        claim_map = route.get("claim_evidence_map")
        if not isinstance(claim_map, dict) or not claim_map:
            failures.append(failure("CLAIM_EVIDENCE_MAP_INVALID", "claim_evidence_map must be a non-empty object", stage="route_validation", record_id=record_id, recoverable=True))
        else:
            for claim, claim_ids in claim_map.items():
                if not isinstance(claim, str) or not claim or not isinstance(claim_ids, list) or not claim_ids:
                    failures.append(failure("CLAIM_EVIDENCE_MAP_INVALID", "every claim-map entry needs evidence IDs", stage="route_validation", record_id=record_id, recoverable=True))
                    continue
                for evidence_id in claim_ids:
                    registered = by_evidence.get(evidence_id)
                    if registered is None or evidence_id not in evidence_ids:
                        failures.append(failure("CLAIM_EVIDENCE_UNRESOLVED", f"claim-map evidence does not resolve within the route: {evidence_id}", stage="route_validation", record_id=record_id, recoverable=True))
                    elif registered.get("source_id") not in source_ids:
                        failures.append(failure("CLAIM_SOURCE_UNRESOLVED", f"claim-map source does not resolve within the route: {claim}", stage="route_validation", record_id=record_id, recoverable=True))
        placement = route.get("strategic_placement")
        if isinstance(placement, dict) and set(placement) != {"90_day", "30_day", "7_day"}:
            failures.append(failure("ROUTE_FIELD_INVALID", "strategic_placement must define 90_day, 30_day, and 7_day", stage="route_validation", record_id=record_id, recoverable=True))
    selected = collection.get("selected_route_id")
    if not isinstance(selected, str) or selected not in seen_ids:
        failures.append(failure("SELECTED_ROUTE_INVALID", "selected_route_id must resolve to one route", stage="route_validation", recoverable=True))
    return failures


def validate_studio_evidence_links(
    package: Mapping[str, Any],
    evidence_registry: Mapping[str, Any] | None,
    artifact_hashes: Mapping[str, str] | None,
) -> list[dict[str, Any]]:
    failures = validate_evidence_registry(evidence_registry, artifact_hashes)
    records = evidence_registry.get("records", []) if isinstance(evidence_registry, Mapping) else []
    by_evidence = {item.get("evidence_id"): item for item in records if isinstance(item, Mapping)}

    def check_links(item: Mapping[str, Any], label: str, require_sources: bool = False) -> None:
        evidence_ids = item.get("evidence_ids")
        if not isinstance(evidence_ids, list) or not evidence_ids:
            failures.append(failure("STUDIO_EVIDENCE_MISSING", f"{label} has no evidence IDs", stage="studio_validation", record_id=label, recoverable=True))
            return
        sources = item.get("source_ids") if require_sources else None
        if require_sources and (not isinstance(sources, list) or not sources):
            failures.append(failure("STUDIO_SOURCE_MISSING", f"{label} has no source IDs", stage="studio_validation", record_id=label, recoverable=True))
            sources = []
        for evidence_id in evidence_ids:
            registered = by_evidence.get(evidence_id)
            if registered is None:
                failures.append(failure("STUDIO_EVIDENCE_UNRESOLVED", f"{label} evidence is absent from registry: {evidence_id}", stage="studio_validation", record_id=label, recoverable=True))
            elif require_sources and registered.get("source_id") not in sources:
                failures.append(failure("STUDIO_SOURCE_EVIDENCE_MISMATCH", f"{label} source/evidence pair does not match registry", stage="studio_validation", record_id=label, recoverable=True))

    script = package.get("script-package.json")
    if not isinstance(script, Mapping):
        failures.append(failure("STUDIO_SCRIPT_MISSING", "script package is missing", stage="studio_validation", recoverable=True))
    else:
        for index, segment in enumerate(script.get("segments", [])):
            if isinstance(segment, Mapping):
                check_links(segment, f"script.segment.{index}")
        for index, claim in enumerate(script.get("claim_map", [])):
            if isinstance(claim, Mapping):
                check_links(claim, f"script.claim.{index}")
    shots = package.get("shot-manifest.json", {}).get("shots", []) if isinstance(package.get("shot-manifest.json"), Mapping) else []
    for index, shot in enumerate(shots):
        if isinstance(shot, Mapping):
            check_links(shot, f"shot.{index}", require_sources=True)
    edit = package.get("edit-manifest.json")
    if isinstance(edit, Mapping):
        for index, marker in enumerate(edit.get("marker_plan", [])):
            if isinstance(marker, Mapping):
                check_links(marker, f"edit.marker.{index}")
    return failures


def _default_route_collection(evidence: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    source_ids = [str(item["source_id"]) for item in evidence]
    evidence_ids = [str(item["evidence_id"]) for item in evidence]
    available_evidence = set(evidence_ids)
    claim_evidence_map = {
        "capability": ["EVID-M2-CAPABILITY"],
        "missingness": ["EVID-M2-CAPABILITY", "EVID-M2-NORMALIZED-COHORT", "EVID-M2-COVERAGE"],
        "lineage": ["EVID-M2-NORMALIZED-COHORT"],
        "failure_behavior": ["EVID-M2-FAILURE-REPORT"],
        "scope_boundary": ["EVID-M2-ADMISSION", "EVID-M2-OUTPUT-CONTRACT", "EVID-M2-COVERAGE"],
        "production_gate": ["EVID-M2-ADMISSION", "EVID-M2-OUTPUT-CONTRACT"],
    }
    claim_evidence_map = {
        claim: [evidence_id for evidence_id in ids if evidence_id in available_evidence]
        for claim, ids in claim_evidence_map.items()
    }
    shared = {
        "topic": "What a provider-disabled content-engine burn-in actually proves",
        "source_ids": source_ids,
        "evidence_ids": evidence_ids,
        "claim_evidence_map": claim_evidence_map,
        "audience": "technical founders and content-system operators",
        "job": "evaluate an AI content workflow without confusing setup evidence with production readiness",
        "pain": "polished automation demos often hide missing data, unsupported connectors, and skipped approval gates",
        "why_now": "the current run produced dated first-party admission, capability, cohort, and validation artifacts",
        "market_context": "first-party run evidence supports system-process claims only; live market coverage remains a GAP",
        "mechanisms": ["show the receipt chain", "show null and quarantine behavior", "show the explicit provider-disabled boundary"],
        "prohibited_copy": ["creator wording or structure", "performance claims from seed-only URLs", "fake UI, metrics, customer outcomes, or readiness claims"],
        "m2_contribution": "an original evidence-to-route-to-production-plan walkthrough authored from local run receipts",
        "m2_proof": "hashed local contracts, deterministic outputs, and focused failure tests",
        "strategic_placement": {"90_day": "credibility through inspectable systems", "30_day": "provider-disabled build-in-public series", "7_day": "current engineering proof slot"},
        "production_complexity": {"class": "LOW_LOCAL", "duration_seconds": 24, "providers_required": [], "external_actions": []},
        "platforms": ["linkedin", "instagram_reels", "tiktok", "youtube_shorts"],
        "success_metrics": ["owner review completion", "evidence-link validity", "zero unsupported claims"],
    }
    angles = [
        ("ROUTE-001", "Receipts before reach", "Open with the gap between a configured connector and a dated capability receipt."),
        ("ROUTE-002", "Null is a product feature", "Demonstrate why missing metrics must remain null and enter explicit partial states."),
        ("ROUTE-003", "The vertical slice that refuses to pretend", "Follow one seed-to-studio trace while every external provider stays disabled."),
    ]
    routes = []
    for route_id, title, angle in angles:
        route = dict(shared)
        route.update({"route_id": route_id, "title": title, "angle": angle, "claim_label": "FACT"})
        routes.append(route)
    return {
        "schema": "m2.daily-route-collection.v1",
        "collection_id": "DRC-20260824-M2-BOOTSTRAP-V1",
        "provider_mode": "disabled",
        "routes": routes,
        "selected_route_id": "ROUTE-003",
        "selection_state": "OWNER_REVIEW_PENDING",
    }


def build_studio_package(
    collection: Mapping[str, Any],
    evidence_registry: Mapping[str, Any] | None = None,
    artifact_hashes: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    route_failures = validate_daily_route_collection(collection, evidence_registry, artifact_hashes)
    if route_failures:
        raise M2Error("DAILY_ROUTE_INVALID", canonical_json(route_failures), recoverable=True)
    route = next(item for item in collection["routes"] if item["route_id"] == collection["selected_route_id"])
    route_id = route["route_id"]
    duration_ms = int(route["production_complexity"]["duration_seconds"]) * 1000
    lines = [
        (0, 4000, "hook", "A connector name is not evidence that a system can reach a source."),
        (4000, 8000, "tension", "In this run, unavailable platforms stay disabled and their metrics stay null."),
        (8000, 12000, "mechanism", "Each seed keeps its exact URL, aliases, parent state, and raw hash."),
        (12000, 16000, "proof", "Duplicates and malformed snapshots become typed recoverable failures."),
        (16000, 20000, "payoff", "Only first-party run receipts support this build-in-public route."),
        (20000, duration_ms, "cta", "Review the manifest, the gaps, and the next gated action before production."),
    ]
    route_claim_evidence = route.get("claim_evidence_map", {})
    registry_records = evidence_registry.get("records", []) if isinstance(evidence_registry, Mapping) else []
    evidence_to_source = {
        item.get("evidence_id"): item.get("source_id") for item in registry_records if isinstance(item, Mapping)
    }
    evidence_by_function = {
        "hook": route_claim_evidence.get("capability", []),
        "tension": route_claim_evidence.get("missingness", []),
        "mechanism": route_claim_evidence.get("lineage", []),
        "proof": route_claim_evidence.get("failure_behavior", []),
        "payoff": route_claim_evidence.get("scope_boundary", []),
        "cta": route_claim_evidence.get("production_gate", []),
    }
    if any(not evidence_by_function[function] for _, _, function, _ in lines):
        raise M2Error("CLAIM_EVIDENCE_MISSING", "every spoken claim must have direct first-party evidence", recoverable=True)
    full_script = " ".join(line for _, _, _, line in lines)
    reading_speed_wpm = round(len(full_script.split()) / (duration_ms / 60000), 1)
    platform_adaptations = {
        "instagram_reels": {
            "opening": "CONFIG ≠ CAPABILITY appears before the first spoken word.",
            "cover_text": "The automation that refuses to fake readiness",
            "title": "What a provider-disabled content engine actually proves",
            "caption": "A build-in-public receipt chain: honest gaps, immutable inputs, and no fabricated reach.",
            "cta": "Review the manifest before approving production.",
        },
        "tiktok": {
            "opening": "Start on the red DISABLED connector state, then snap to the dated receipt.",
            "cover_text": "Configured does not mean connected",
            "title": "This AI workflow refuses to invent missing data",
            "caption": "Null stays null. Blocked stays blocked. The proof is in the receipt chain.",
            "cta": "Open the manifest and challenge one gap.",
        },
        "youtube_shorts": {
            "opening": "Ask what the system can prove with every provider switched off.",
            "cover_text": "Proof before production",
            "title": "What an AI Content Engine Can Prove Offline",
            "caption": "A 24-second provider-disabled audit from source receipt to Studio plan.",
            "cta": "Inspect the evidence links before the next gate.",
        },
    }
    script = {
        "schema": "m2.script-package.v1",
        "script_id": f"SCRIPT-{route_id}",
        "route_id": route_id,
        "version": 1,
        "duration_ms": duration_ms,
        "hook_options": [lines[0][3], "What does an AI content engine prove when every provider is off?", "The useful output of a blocked connector is an honest gap."],
        "chosen_hook": lines[0][3],
        "segments": [{"start_ms": start, "end_ms": end, "function": function, "spoken_line": line, "evidence_ids": evidence_by_function[function], "claim_label": "FACT"} for start, end, function, line in lines],
        "full_script": full_script,
        "reading_speed_wpm": reading_speed_wpm,
        "cta": lines[-1][3],
        "title": "The vertical slice that refuses to pretend",
        "cover_text": "CONFIGURED ≠ READY",
        "caption": "A provider-disabled content-engine burn-in should prove its boundaries as clearly as its happy path.",
        "pinned_comment_strategy": {
            "prompt": "Which missing capability should remain a hard gate before production?",
            "reply_policy": "Answer only from linked first-party run evidence; label unresolved questions GAP.",
            "engagement_state": "PLAN_ONLY_PUBLICATION_BLOCKED",
        },
        "platform_adaptations": platform_adaptations,
        "claim_map": [{"claim": line, "evidence_ids": evidence_by_function[function], "label": "FACT"} for _, _, function, line in lines],
        "on_screen_text": ["CONFIG ≠ CAPABILITY", "NULL ≠ ZERO", "HASH → VALIDATE → QUARANTINE", "FIRST-PARTY RUN EVIDENCE"],
        "approval_state": "OWNER_REVIEW_PENDING",
    }
    shot_visuals = {
        "hook": [
            ("Contrast configuration with proof", "centered receipt card", "two-column slide-in", "connector label beside an empty capability cell", "CONFIG ≠ CAPABILITY"),
            ("Reveal the dated capability state", "tight crop on status row", "cursor-line wipe", "dated capability receipt with DISABLED badges", "ASK FOR THE RECEIPT"),
        ],
        "tension": [
            ("Show unavailable routes without concealment", "four-card status grid", "blocked cards settle downward", "disabled platform adapter cards", "DISABLED STAYS DISABLED"),
            ("Distinguish missing from zero", "split metric cell close-up", "null symbol pulses once", "NULL cell compared with a separate numeric zero", "NULL ≠ ZERO"),
        ],
        "mechanism": [
            ("Trace immutable seed identity", "left-to-right ledger strip", "URL tokens advance one step", "exact URL, canonical URL, and alias columns", "PRESERVE THE INPUT"),
            ("Expose unresolved lineage honestly", "parent-link graph detail", "two dotted edges stop at GAP nodes", "parent state and raw-hash nodes", "UNRESOLVED IS A STATE"),
        ],
        "proof": [
            ("Demonstrate duplicate quarantine", "stacked record comparison", "duplicate row moves into amber lane", "identity collision and quarantine receipt", "DUPLICATE → QUARANTINE"),
            ("Demonstrate recoverable malformed input", "failure receipt close-up", "error code types on deterministically", "typed code, recoverable flag, and next action", "FAIL TYPED, NOT SILENT"),
        ],
        "payoff": [
            ("Bind every claim to first-party evidence", "evidence graph overview", "three evidence edges illuminate", "admission, capability, and output-contract nodes", "FIRST-PARTY RUN EVIDENCE"),
            ("Separate local proof from market claims", "scope boundary card", "market claims fade behind GAP boundary", "local proof column versus deferred live-market column", "NO REACH CLAIMS"),
        ],
        "cta": [
            ("Present the reviewable artifact set", "manifest checklist", "checks appear top to bottom", "manifest, failures, route, and Studio package rows", "REVIEW THE MANIFEST"),
            ("End at the next explicit gate", "single centered approval gate", "camera eases to a stop", "owner review and independent review pending states", "APPROVE THE NEXT GATE—NOT THE MYTH"),
        ],
    }
    shots = []
    for beat_index, (start, _end, function, line) in enumerate(lines):
        for state_index, (objective, framing, motion, screen_content, on_screen_text) in enumerate(shot_visuals[function]):
            index = beat_index * 2 + state_index + 1
            shot_start = start + state_index * 2000
            shot_end = shot_start + 2000
            shots.append(
                {
                    "shot_id": f"SHOT-{index:02d}",
                    "start_ms": shot_start,
                    "end_ms": shot_end,
                    "narrative_function": function,
                    "spoken_line": line,
                    "visual_objective": objective,
                    "visual": objective,
                    "framing": framing,
                    "motion": motion,
                    "screen_or_diagram_content": screen_content,
                    "on_screen_text": on_screen_text,
                    "source_ids": [evidence_to_source[evidence_id] for evidence_id in evidence_by_function[function]],
                    "evidence_ids": evidence_by_function[function],
                    "asset_ids": [f"ASSET-{index:02d}"],
                    "source_state": "FIRST_PARTY_RUN_EVIDENCE",
                    "generation_state": "NOT_RUN",
                    "deterministic": True,
                    "transition": "hard cut on two-second visual state boundary",
                    "audio": "spoken-line timing placeholder; no generated or real-person voice",
                    "audio_cue": "subtle deterministic interface tick; source audio NOT_RUN",
                    "fallback": "static local diagram card retaining the same evidence IDs and text",
                    "qc": ["duration is exactly 2000 ms", "interval is contiguous", "text remains editable", "visual objective is distinct within its spoken beat", "no fake external proof"],
                }
            )
    assets = [
        {
            "asset_id": f"ASSET-{index:02d}",
            "asset_type": "DETERMINISTIC_GRAPHIC",
            "path": None,
            "rights_state": "M2_ORIGINAL_PLANNING",
            "provider_state": "NOT_RUN",
            "retention": "run-local plan only",
            "fallback": "editable text and shapes",
        }
        for index in range(1, len(shots) + 1)
    ]
    package = {
        "script-package.json": script,
        "shot-manifest.json": {"schema": "m2.shot-manifest.v1", "route_id": route_id, "duration_ms": duration_ms, "shots": shots, "provider_execution": "NOT_RUN"},
        "asset-manifest.json": {"schema": "m2.asset-manifest.v1", "route_id": route_id, "assets": assets, "private_media_state": "BLOCKED_APPROVAL", "generated_media_state": "NOT_RUN"},
        "founder-shoot-manifest.json": {"schema": "m2.founder-shoot-manifest.v1", "route_id": route_id, "state": "BLOCKED_APPROVAL", "takes": [], "reason": "no private media or real-person likeness/voice approval"},
        "edit-manifest.json": {
            "schema": "m2.edit-manifest.v1", "route_id": route_id, "timeline_state": "PLAN_ONLY", "duration_ms": duration_ms,
            "operations": sorted(ALLOWED_RESOLVE_OPERATIONS), "shots": [item["shot_id"] for item in shots],
            "timeline": [{"shot_id": item["shot_id"], "start_ms": item["start_ms"], "end_ms": item["end_ms"], "asset_ids": item["asset_ids"], "transition": item["transition"]} for item in shots],
            "track_plan": {"V1": "deterministic graphic cards", "V2": "editable text and diagrams", "A1": "spoken-line placeholder only", "A2": "optional deterministic interface cues"},
            "marker_plan": [{"at_ms": start, "label": function.upper(), "evidence_ids": evidence_by_function[function]} for start, _, function, _ in lines],
            "caption_plan": [{"start_ms": start, "end_ms": end, "text": line} for start, end, _, line in lines],
            "audio_plan": {"voice_state": "NOT_RUN", "music_state": "NOT_RUN", "sfx_state": "PLAN_ONLY", "target": "speech-first mobile intelligibility"},
            "export_plan": {"aspect_ratio": "9:16", "resolution": "1080x1920", "duration_ms": duration_ms, "state": "BLOCKED_APPROVAL"},
            "unsupported_operations": ["media import", "timeline mutation", "render queue mutation", "final render"],
            "resolve_mutation_state": "BLOCKED_APPROVAL", "final_video_state": "NOT_RUN"
        },
        "platform-package.json": {
            "schema": "m2.platform-package.v1", "route_id": route_id, "route_platforms": route["platforms"], "central_thesis": route["angle"],
            "packages": platform_adaptations, "shared_full_script": full_script, "pinned_comment_strategy": script["pinned_comment_strategy"],
            "linkedin_state": "ROUTE_LISTED_NO_SHORT_FORM_PACKAGE", "publication_state": "BLOCKED_APPROVAL", "feedback_ingestion_state": "NOT_RUN"
        },
        "qc-report.json": {"schema": "m2.qc-report.v1", "route_id": route_id, "maker": "RESP-M2-M1", "reviewer": None, "verdict": "PENDING_INDEPENDENT_REVIEW", "checks": {"route_valid": True, "shot_density_21_30s": "12_WITHIN_REQUIRED_10_16", "time_contiguous": True, "two_visual_states_per_spoken_beat": True, "three_short_form_platform_packages": True, "provider_execution": False, "publication": False, "maker_self_approval": False}},
        "transformation-statement.md": (
            "# Transformation statement\n\n"
            "First-party evidence: the frozen M2 run contracts, capability state, normalized cohort, and local validation receipts.\n\n"
            "General mechanisms: an evidence-first hook, visible missingness, and a receipt-chain walkthrough.\n\n"
            "Uniquely authored here: the script, sequence, diagrams, and provider-disabled demonstration structure.\n\n"
            "Prohibited: creator wording, footage, layout, identity, voice, performance claims, fake UI/results, or a near-identical timeline.\n"
        ),
    }
    studio_failures = validate_studio_evidence_links(package, evidence_registry, artifact_hashes)
    if studio_failures:
        raise M2Error("STUDIO_EVIDENCE_INVALID", canonical_json(studio_failures), recoverable=True)
    return package


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_artifact_bytes(value))


def _write_jsonl(path: Path, values: Iterable[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical_json(value) + "\n" for value in values), encoding="utf-8")


def persist_metric_snapshots(path: Path, snapshots: Sequence[Mapping[str, Any]]) -> dict[str, int | str]:
    """Persist snapshots idempotently and append-only across separate invocations."""
    path.parent.mkdir(parents=True, exist_ok=True)

    def identity(item: Mapping[str, Any]) -> tuple[Any, Any, Any]:
        return (item.get("post_id"), item.get("collected_at"), item.get("metric_semantics_version"))

    incoming: dict[tuple[Any, Any, Any], Mapping[str, Any]] = {}
    for item in snapshots:
        key = identity(item)
        if None in key or not isinstance(item.get("immutable_hash"), str):
            raise M2Error("SNAPSHOT_PERSISTENCE_INVALID", "snapshot identity and immutable_hash are required")
        if key in incoming:
            raise M2Error("SNAPSHOT_PERSISTENCE_CONFLICT", "incoming snapshot identity is duplicated")
        incoming[key] = item
    if not path.exists():
        _write_jsonl(path, snapshots)
        return {"status": "CREATED", "existing": 0, "appended": len(snapshots)}
    existing_bytes = path.read_bytes()
    existing: dict[tuple[Any, Any, Any], Mapping[str, Any]] = {}
    try:
        lines = existing_bytes.decode("utf-8").splitlines()
        for line in lines:
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError("snapshot line is not an object")
            key = identity(item)
            if None in key or key in existing or not isinstance(item.get("immutable_hash"), str):
                raise ValueError("existing snapshot identity is invalid or duplicated")
            existing[key] = item
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise M2Error("SNAPSHOT_STORE_CORRUPT", f"existing snapshot store is invalid: {exc}") from exc
    for key, old in existing.items():
        new = incoming.get(key)
        if new is None:
            raise M2Error("SNAPSHOT_PERSISTENCE_CONFLICT", "incoming run would remove a persisted snapshot")
        if old.get("immutable_hash") != new.get("immutable_hash"):
            raise M2Error("SNAPSHOT_PERSISTENCE_CONFLICT", "same snapshot identity has different immutable content")
    additions = [item for key, item in incoming.items() if key not in existing]
    if additions:
        with path.open("a", encoding="utf-8") as stream:
            for item in additions:
                stream.write(canonical_json(item) + "\n")
        return {"status": "APPENDED", "existing": len(existing), "appended": len(additions)}
    if path.read_bytes() != existing_bytes:  # pragma: no cover - defensive invariant
        raise M2Error("SNAPSHOT_PERSISTENCE_CONFLICT", "idempotent check unexpectedly changed snapshot bytes")
    return {"status": "UNCHANGED", "existing": len(existing), "appended": 0}


def _safe_output_dir(output_dir: Path) -> Path:
    if output_dir.exists() and not output_dir.is_dir():
        raise M2Error("OUTPUT_IO_ERROR", "output path exists and is not a directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir.resolve()


def run_vertical_slice(input_dir: Path, output_dir: Path) -> dict[str, Any]:
    input_dir = input_dir.resolve()
    project_root = input_dir.parents[1] if input_dir.parent.name == "runs" else input_dir
    cohort_path = input_dir / "golden-reference-cohort.json"
    if not cohort_path.is_file():
        raise M2Error("INPUT_NOT_FOUND", f"required frozen input missing: {cohort_path}")
    try:
        cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise M2Error("INPUT_IO_ERROR", f"could not read frozen cohort: {exc}") from exc
    if not isinstance(cohort, dict):
        raise M2Error("MALFORMED_PAYLOAD", "golden cohort must be an object")
    normalized = import_golden_cohort(cohort)
    output_root = _safe_output_dir(output_dir)

    registration_path = input_dir / "collection" / "source-registration.jsonl"
    collected = (
        import_registered_sources(registration_path, project_root=project_root)
        if registration_path.is_file()
        else {"records": [], "snapshot_inputs": [], "quarantine": []}
    )
    seed_source_records = normalized["creator_records"] + normalized["post_records"]
    source_records = seed_source_records + collected["records"]
    seed_snapshots = []
    for post in normalized["post_records"]:
        seed_snapshots.append(
            {
                "snapshot_id": f"MS-{post['reference_id']}-SEED",
                "post_id": post["reference_id"],
                "creator_id": post["parent_creator_reference_id"],
                "platform": post["platform"],
                "format": post["evidence_status"],
                "duration_bucket": None,
                "collected_at": cohort["provenance"]["registered_at"],
                "provider": "user_supplied_seed_registry",
                "metric_semantics_version": "seed-visible-metrics.v1",
                "metrics": dict(post["metrics"] or {}),
                "raw_payload": {"reference_id": post["reference_id"], "metrics": post["metrics"]},
            }
        )
    snapshot_result = normalize_metric_snapshots(seed_snapshots + collected["snapshot_inputs"])
    scores = robust_score_records(snapshot_result["snapshots"])

    disabled = [DisabledProviderAdapter(name).fetch().failure for name in ("instagram", "tiktok", "paid_media", "resolve", "figma", "publishing")]
    quarantine = normalized["quarantine"] + collected["quarantine"] + snapshot_result["quarantine"]
    failures = [item for item in disabled if item is not None]
    adversarial_failures = [
        failure(
            "MALFORMED_PAYLOAD",
            "synthetic fixture: provider payload is not an object",
            stage="normalization_fixture",
            recoverable=True,
        ),
        validate_transcript_payload({"segments": [{}]}),
        validate_media_path("../outside-approved-root.mov", allowed_root=input_dir),
        validate_resolve_operation("render_final_video"),
        DisabledProviderAdapter("youtube", "synthetic provider outage fixture").fetch().failure,
    ]
    failures.extend(item for item in adversarial_failures if item is not None)
    coverage = {
        "schema": "m2.coverage-report.v1",
        "targets": {"creator_seeds": 12, "post_seeds": 14, "total_seeds": 26},
        "observed": {"creator_seeds": len(normalized["creator_records"]), "post_seeds": len(normalized["post_records"]), "total_seeds": len(seed_source_records), "collected_source_records": len(collected["records"]), "total_source_records": len(source_records), "aliases": len(normalized["alias_ledger"]), "unresolved_parent_links": sum(item["parent_state"] == "GAP_UNRESOLVED" for item in normalized["post_records"]), "seed_metric_snapshots": len(seed_snapshots), "collected_metric_snapshots": len(collected["snapshot_inputs"]), "snapshots": len(snapshot_result["snapshots"]), "comments": 0, "transcripts": 0, "deep_analyses": 0},
        "denominators": {"seed_records": len(seed_source_records), "collected_records": len(collected["records"]), "all_source_records": len(source_records), "post_seed_records": len(normalized["post_records"]), "snapshot_records": len(snapshot_result["snapshots"])},
        "missingness": {name: {"missing": sum(item["metrics"].get(name) is None for item in snapshot_result["snapshots"]), "denominator": len(snapshot_result["snapshots"])} for name in ("views", "likes", "comments", "shares", "reposts", "saves")},
        "duplicates": {"count": sum(item["code"] in {"DUPLICATE_SEED", "DUPLICATE_SNAPSHOT", "DUPLICATE_SOURCE_ID", "DUPLICATE_SOURCE_URL"} for item in quarantine), "denominator": len(source_records) + len(seed_snapshots) + len(collected["snapshot_inputs"])},
        "source_mix": {"instagram_seed_only": len(seed_source_records), "registered_public_metadata": len(collected["records"]), "live_network_requests_by_engine": 0},
        "provider_mode": "disabled",
        "cost_usd": 0,
        "runtime_seconds": None,
        "live_market_acceptance": "GAP",
        "limitations": normalized["limitations"],
    }
    failure_report = {
        "schema": "m2.failure-test-report.v1",
        "status": "RECOVERABLE_PARTIAL_STATES_EMITTED",
        "fixture_only": True,
        "failures": failures,
        "provider_execution": False,
    }
    evidence = []
    artifact_hashes: dict[str, str] = {}
    for filename, evidence_id in (("admission-receipt.json", "EVID-M2-ADMISSION"), ("capability-receipt.json", "EVID-M2-CAPABILITY"), ("output-contract.md", "EVID-M2-OUTPUT-CONTRACT")):
        path = input_dir / filename
        if not path.is_file():
            raise M2Error("INPUT_NOT_FOUND", f"required frozen evidence input missing: {path}")
        observed_hash = file_hash(path)
        artifact_hashes[f"run_input:{filename}"] = observed_hash
        evidence.append({"source_id": f"SRC-M2-{filename.upper()}", "evidence_id": evidence_id, "path_root": "run_input", "path": filename, "sha256": observed_hash, "label": "FACT", "scope": "first_party_run_evidence"})
    generated_evidence = (
        ("SRC-M2-NORMALIZED-COHORT", "EVID-M2-NORMALIZED-COHORT", "golden-reference-cohort.normalized.json", normalized),
        ("SRC-M2-COVERAGE", "EVID-M2-COVERAGE", "coverage-report.json", coverage),
        ("SRC-M2-FAILURE-REPORT", "EVID-M2-FAILURE-REPORT", "failure-test-report.json", failure_report),
    )
    for source_id, evidence_id, relative_path, value in generated_evidence:
        observed_hash = json_artifact_hash(value)
        artifact_hashes[f"output_dir:{relative_path}"] = observed_hash
        evidence.append({"source_id": source_id, "evidence_id": evidence_id, "path_root": "output_dir", "path": relative_path, "sha256": observed_hash, "label": "FACT", "scope": "generated_first_party_run_evidence"})
    evidence_registry = {
        "schema": "m2.first-party-evidence-registry.v1",
        "registry_id": "EVIDENCE-REGISTRY-20260824-M2-BOOTSTRAP-V1",
        "path_roots": {"run_input": ".", "output_dir": "burn-in/"},
        "records": evidence,
    }
    registry_failures = validate_evidence_registry(evidence_registry, artifact_hashes)
    if registry_failures:
        raise M2Error("EVIDENCE_REGISTRY_INVALID", canonical_json(registry_failures), recoverable=True)
    routes = _default_route_collection(evidence)
    route_failures = validate_daily_route_collection(routes, evidence_registry, artifact_hashes)
    if route_failures:
        failure_report["failures"] = failures + route_failures
        raise M2Error("DAILY_ROUTE_INVALID", canonical_json(route_failures), recoverable=True)
    studio = build_studio_package(routes, evidence_registry, artifact_hashes)
    trace = [
        {"schema": "m2.trace.v1", "trace_id": "TRACE-SEED-IMPORT", "stage": "seed_and_registered_source_import", "status": "PARTIAL" if normalized["quarantine"] or collected["quarantine"] else "COMPLETE", "input_hashes": [file_hash(cohort_path)] + ([file_hash(registration_path)] if registration_path.is_file() else []), "output_ids": [str(item.get("reference_id") or item.get("source_id")) for item in source_records], "provider_mode": "disabled", "external_actions": False, "cost_usd": 0},
        {"schema": "m2.trace.v1", "trace_id": "TRACE-SCORING", "stage": "scoring", "status": "GAP" if any(item["status"] == "GAP" for item in scores) else "COMPLETE", "input_hashes": [item["immutable_hash"] for item in snapshot_result["snapshots"]], "output_ids": [str(item["snapshot_id"]) for item in scores], "provider_mode": "disabled", "external_actions": False, "cost_usd": 0},
        {"schema": "m2.trace.v1", "trace_id": "TRACE-STUDIO", "stage": "studio_package", "status": "COMPLETE" if not route_failures else "BLOCKED", "input_hashes": [canonical_hash(routes)], "output_ids": sorted(studio), "provider_mode": "disabled", "external_actions": False, "cost_usd": 0},
    ]

    persist_metric_snapshots(output_root / "metric-snapshots.jsonl", snapshot_result["snapshots"])
    _write_json(output_root / "golden-reference-cohort.normalized.json", normalized)
    _write_jsonl(output_root / "source-records.jsonl", source_records)
    _write_jsonl(output_root / "quarantine.jsonl", quarantine)
    _write_jsonl(output_root / "score-decompositions.jsonl", scores)
    _write_json(output_root / "coverage-report.json", coverage)
    _write_json(output_root / "failure-test-report.json", failure_report)
    _write_json(output_root / "first-party-evidence-registry.json", evidence_registry)
    _write_jsonl(output_root / "trace.jsonl", trace)
    _write_json(output_root / "daily-route-collection.json", routes)
    for name, value in studio.items():
        path = output_root / "studio-package" / name
        if name.endswith(".md"):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(value), encoding="utf-8")
        else:
            _write_json(path, value)

    artifact_paths = sorted(
        str(path.relative_to(output_root))
        for path in output_root.rglob("*")
        if path.is_file() and path.name not in {"dataset-manifest.json", "manifest.json"}
    )
    dataset_manifest = {
        "schema": "m2.dataset-manifest.v1",
        "source_input": {"path": "golden-reference-cohort.json", "sha256": file_hash(cohort_path)},
        "registered_source_input": (
            {"path": "collection/source-registration.jsonl", "sha256": file_hash(registration_path)}
            if registration_path.is_file()
            else None
        ),
        "record_counts": {"creator_seeds": len(normalized["creator_records"]), "post_seeds": len(normalized["post_records"]), "total_seeds": len(seed_source_records), "collected_source_records": len(collected["records"]), "seed_snapshots": len(seed_snapshots), "collected_snapshots": len(collected["snapshot_inputs"]), "total_snapshots": len(snapshot_result["snapshots"]), "quarantined": len(quarantine)},
        "snapshot_persistence": {"policy": "append_only_idempotent", "persisted_identities": len(snapshot_result["snapshots"])},
        "formula_registry": FORMULA_REGISTRY,
        "provider_mode": "disabled",
        "external_actions": False,
    }
    _write_json(output_root / "dataset-manifest.json", dataset_manifest)
    artifact_paths.append("dataset-manifest.json")
    manifest = {
        "schema": "m2.run-manifest.v1",
        "engine_schema": SCHEMA_VERSION,
        "provider_mode": "disabled",
        "external_actions": False,
        "artifacts": [
            {"path": relative, "sha256": file_hash(output_root / relative)} for relative in sorted(artifact_paths)
        ],
        "content_hash": canonical_hash({"coverage": coverage, "evidence_registry": evidence_registry, "routes": routes, "studio": studio, "dataset": dataset_manifest}),
        "review_state": "PENDING_INDEPENDENT_REVIEW",
    }
    _write_json(output_root / "manifest.json", manifest)
    return manifest
