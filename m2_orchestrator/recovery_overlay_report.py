"""Build a hash-bound full-population overlay for bounded recovery attempts.

The overlay is a new reporting snapshot. It never updates the primary media
ledger and never turns a recovery word-bearing result into a reviewed primary
transcript. Primary attempt history, recovery attempts, and video-only audio
uncertainty remain separate fields.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "m2.recovery-overlay-report.v1"
MAX_JSON_BYTES = 64 * 1024 * 1024
_HASH_FIELDS = ("source_media_hash", "media_hash", "sha256")


class RecoveryOverlayError(ValueError):
    """Stable fail-closed report-builder error."""


def _hash64(value: Any, error: str = "HASH_INVALID") -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdefABCDEF" for c in value):
        raise RecoveryOverlayError(error)
    return value.lower()


def _finite(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def _json_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _read_json(path: Path) -> Any:
    if _has_symlink_ancestor(path, include_self=True) or not path.is_file():
        raise RecoveryOverlayError("INPUT_FILE_INVALID")
    if path.stat().st_size > MAX_JSON_BYTES:
        raise RecoveryOverlayError("INPUT_FILE_TOO_LARGE")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RecoveryOverlayError("INPUT_JSON_INVALID") from exc


def _has_symlink_ancestor(path: Path, *, include_self: bool = False) -> bool:
    current = path if include_self else path.parent
    while True:
        if current.exists() and current.is_symlink():
            return True
        parent = current.parent
        if parent == current:
            return False
        current = parent


def _safe_local_candidate(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value or value.startswith(("http://", "https://")):
        return None
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise RecoveryOverlayError("ARTIFACT_PATH_INVALID")
    candidate = root / relative
    if _has_symlink_ancestor(candidate, include_self=True):
        raise RecoveryOverlayError("ARTIFACT_PATH_SYMLINK")
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise RecoveryOverlayError("ARTIFACT_PATH_OUTSIDE_ROOT") from exc
    return candidate


def _records_from_file(path: Path) -> list[Mapping[str, Any]]:
    value = _read_json(path)
    if isinstance(value, Mapping):
        for key in ("entries", "records", "identities", "rows"):
            if isinstance(value.get(key), list):
                value = value[key]
                break
        else:
            value = [value]
    if not isinstance(value, list) or any(not isinstance(row, Mapping) for row in value):
        raise RecoveryOverlayError("RECORD_LIST_INVALID")
    return list(value)


def load_canonical_records(
    path: str | Path,
    *,
    expected_snapshot_hash: str | None = None,
    expected_population: int | None = 2352,
) -> list[dict[str, Any]]:
    """Load canonical identities, adapting the actual full-manifest shape.

    The full media manifest binds the population to its file-byte SHA-256 but
    does not repeat that global binding on every entry.  When the caller
    supplies the expected hash, add that same global value to entries lacking
    ``source_snapshot_hash``.  Declared per-entry bindings remain strict and
    conflicting values fail closed; no per-media hash is inferred from source
    fields.
    """
    path = Path(path)
    if _has_symlink_ancestor(path, include_self=True) or not path.is_file() or path.stat().st_size > MAX_JSON_BYTES:
        raise RecoveryOverlayError("CANONICAL_FILE_INVALID")
    expected = None
    if expected_snapshot_hash is not None:
        expected = _hash64(expected_snapshot_hash, "SOURCE_SNAPSHOT_HASH_INVALID")
        if _stream_hash(path) != expected:
            raise RecoveryOverlayError("CANONICAL_SNAPSHOT_FILE_MISMATCH")
    if path.suffix.lower() == ".jsonl":
        if _has_symlink_ancestor(path, include_self=True) or not path.is_file() or path.stat().st_size > MAX_JSON_BYTES:
            raise RecoveryOverlayError("CANONICAL_FILE_INVALID")
        rows = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    value = json.loads(line)
                    if not isinstance(value, Mapping):
                        raise RecoveryOverlayError("CANONICAL_RECORD_INVALID")
                    rows.append(dict(value))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RecoveryOverlayError("CANONICAL_FILE_INVALID") from exc
    else:
        rows = [dict(row) for row in _records_from_file(path)]
    bound_rows = []
    for row in rows:
        candidate = dict(row)
        declared = candidate.get("source_snapshot_hash")
        if declared is None:
            if expected is not None:
                candidate["source_snapshot_hash"] = expected
        elif expected is not None:
            declared_hash = _hash64(declared, "CANONICAL_SOURCE_HASH_INVALID")
            if declared_hash != expected:
                raise RecoveryOverlayError("CANONICAL_SNAPSHOT_MISMATCH")
            candidate["source_snapshot_hash"] = declared_hash
        bound_rows.append(candidate)
    return normalize_canonical_records(bound_rows, expected_population=expected_population)


def normalize_canonical_records(records: Sequence[Mapping[str, Any]], *, expected_population: int | None = 2352) -> list[dict[str, Any]]:
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        raise RecoveryOverlayError("CANONICAL_RECORDS_REQUIRED")
    seen_ids, seen_codes, seen_indexes = set(), set(), set()
    normalized = []
    for record in records:
        if not isinstance(record, Mapping):
            raise RecoveryOverlayError("CANONICAL_RECORD_INVALID")
        reel_id, code, index = record.get("reel_id"), record.get("code"), record.get("identity_index")
        if not isinstance(reel_id, str) or not reel_id.strip() or not isinstance(code, str) or not code.strip() or type(index) is not int or index < 0:
            raise RecoveryOverlayError("CANONICAL_IDENTITY_INVALID")
        if reel_id in seen_ids:
            raise RecoveryOverlayError("DUPLICATE_CANONICAL_REEL_ID")
        if code in seen_codes:
            raise RecoveryOverlayError("DUPLICATE_CANONICAL_CODE")
        if index in seen_indexes:
            raise RecoveryOverlayError("DUPLICATE_CANONICAL_INDEX")
        seen_ids.add(reel_id)
        seen_codes.add(code)
        seen_indexes.add(index)
        source_snapshot_hash = record.get("source_snapshot_hash")
        if source_snapshot_hash is None:
            raise RecoveryOverlayError("CANONICAL_SNAPSHOT_BINDING_MISSING")
        source_snapshot_hash = _hash64(source_snapshot_hash, "CANONICAL_SOURCE_HASH_INVALID")
        source_media_hash = record.get("source_media_hash")
        if source_media_hash is not None:
            source_media_hash = _hash64(source_media_hash, "CANONICAL_MEDIA_HASH_INVALID")
        normalized.append({"reel_id": reel_id, "code": code, "identity_index": index, "source_snapshot_hash": source_snapshot_hash, "source_media_hash": source_media_hash})
    if expected_population is not None and len(normalized) != expected_population:
        raise RecoveryOverlayError("CANONICAL_POPULATION_MISMATCH")
    return sorted(normalized, key=lambda row: row["identity_index"])


def _resolve_identity(record: Mapping[str, Any], by_code: Mapping[str, Mapping[str, Any]], by_reel: Mapping[str, Mapping[str, Any]]) -> Mapping[str, Any]:
    code = record.get("code")
    reel_id = record.get("reel_id")
    by_code_row = by_code.get(code) if isinstance(code, str) else None
    by_reel_row = by_reel.get(reel_id) if isinstance(reel_id, str) else None
    if by_code_row is not None and by_reel_row is not None and by_code_row["reel_id"] != by_reel_row["reel_id"]:
        raise RecoveryOverlayError("SOURCE_CODE_REEL_COLLISION")
    identity = by_code_row or by_reel_row
    if identity is None:
        raise RecoveryOverlayError("SOURCE_IDENTITY_NOT_CANONICAL")
    if isinstance(code, str) and code and code != identity["code"]:
        raise RecoveryOverlayError("SOURCE_CODE_MISMATCH")
    if isinstance(reel_id, str) and reel_id and reel_id != identity["reel_id"]:
        raise RecoveryOverlayError("SOURCE_REEL_ID_MISMATCH")
    return identity


def _hash_from_record(record: Mapping[str, Any], *, error: str, include_generic_sha256: bool = True) -> str | None:
    values = []
    fields = _HASH_FIELDS if include_generic_sha256 else _HASH_FIELDS[:2]
    for key in fields:
        if key in record and record[key] is not None:
            values.append(_hash64(record[key], error))
    if len(set(values)) > 1:
        raise RecoveryOverlayError("SOURCE_HASH_CONFLICT")
    return values[0] if values else None


def _primary_artifacts(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise RecoveryOverlayError("PRIMARY_ARTIFACTS_INVALID") from exc
    if not isinstance(value, Mapping):
        raise RecoveryOverlayError("PRIMARY_ARTIFACTS_INVALID")
    result = {}
    for path, digest in value.items():
        if not isinstance(path, str) or not isinstance(digest, str):
            raise RecoveryOverlayError("PRIMARY_ARTIFACTS_INVALID")
        result[path] = _hash64(digest, "PRIMARY_ARTIFACT_HASH_INVALID")
    return result


def load_primary_ledger(
    path: str | Path,
    *,
    expected_snapshot_hash: str,
    expected_ledger_snapshot_hash: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Read a transactionally consistent primary-ledger snapshot.

    The source database remains read-only.  ``BEGIN`` pins one SQLite view,
    including committed WAL rows, while reels, attempt history, binding, and
    event provenance are read.  The returned logical hash is over those rows;
    it is deliberately not a hash of the live SQLite file bytes.
    """
    expected_snapshot_hash = _hash64(expected_snapshot_hash, "SOURCE_SNAPSHOT_HASH_INVALID")
    if expected_ledger_snapshot_hash is not None:
        expected_ledger_snapshot_hash = _hash64(expected_ledger_snapshot_hash, "LEDGER_SNAPSHOT_HASH_INVALID")
    path = Path(path)
    if _has_symlink_ancestor(path, include_self=True) or not path.is_file():
        raise RecoveryOverlayError("PRIMARY_LEDGER_INVALID")
    db: sqlite3.Connection | None = None
    try:
        db = sqlite3.connect(f"file:{path.absolute()}?mode=ro", uri=True)
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        tables = {row[0] for row in db.execute("select name from sqlite_master where type='table'")}
        if "reels" not in tables or "attempts" not in tables:
            raise RecoveryOverlayError("PRIMARY_LEDGER_SCHEMA_INVALID")
        binding = {key: value for key, value in db.execute("select key,value from binding")} if "binding" in tables else {}
        snapshot_keys = ("manifest_sha256", "source_snapshot_hash")
        present_snapshot_keys = [key for key in snapshot_keys if key in binding]
        if not present_snapshot_keys:
            raise RecoveryOverlayError("PRIMARY_SNAPSHOT_BINDING_MISSING")
        for key in present_snapshot_keys:
            if not isinstance(binding[key], str) or len(binding[key]) != 64:
                raise RecoveryOverlayError("PRIMARY_SNAPSHOT_BINDING_INVALID")
            if binding[key].lower() != expected_snapshot_hash:
                raise RecoveryOverlayError("PRIMARY_SNAPSHOT_MISMATCH")
        attempts = defaultdict(list)
        attempt_rows = []
        for row in db.execute("select reel_id,stage,attempt,state,error,started,finished,artifacts_json,resources_json from attempts order by reel_id,stage,attempt"):
            reel_id, stage, attempt, state, error, started, finished, artifacts, resources = row
            normalized = {"stage": stage, "attempt": attempt, "state": state, "error": error, "started": started, "finished": finished, "artifacts": _primary_artifacts(artifacts), "resources": _json_load_or_none(resources, "PRIMARY_RESOURCES_INVALID")}
            attempts[reel_id].append(normalized)
            attempt_rows.append({"reel_id": reel_id, **normalized})
        records = []
        reel_rows = []
        for row in db.execute("select reel_id,code,identity_index,acquisition_state,transcript_state,frames_state,scene_review_state,acquisition_artifact,transcript_artifact,frames_artifact from reels order by identity_index,reel_id"):
            reel_id, code, index, acquisition_state, transcript_state, frames_state, scene_review_state, acquisition_artifact, transcript_artifact, frames_artifact = row
            reel_rows.append({"reel_id": reel_id, "code": code, "identity_index": index, "acquisition_state": acquisition_state, "transcript_state": transcript_state, "frames_state": frames_state, "scene_review_state": scene_review_state, "acquisition_artifact": acquisition_artifact, "transcript_artifact": transcript_artifact, "frames_artifact": frames_artifact})
            records.append({
                "reel_id": reel_id,
                "code": code,
                "identity_index": index,
                "primary_states": {"acquisition": acquisition_state, "transcript": transcript_state, "frames": frames_state, "scene_review": scene_review_state},
                "primary_artifacts": {"acquisition": _primary_artifacts(acquisition_artifact), "transcript": _primary_artifacts(transcript_artifact), "frames": _primary_artifacts(frames_artifact)},
                "primary_attempt_history": attempts.get(reel_id, []),
            })
        event_rows = []
        if "events" in tables:
            for row in db.execute("select id,event,stage,reel_id,observed_at,payload_json from events order by id"):
                event_id, event, stage, reel_id, observed_at, payload_json = row
                event_rows.append({"id": event_id, "event": event, "stage": stage, "reel_id": reel_id, "observed_at": observed_at, "payload_json": payload_json})
        logical_snapshot_hash = _json_hash({"binding": binding, "reels": reel_rows, "attempts": attempt_rows, "events": event_rows})
        if expected_ledger_snapshot_hash is not None and logical_snapshot_hash != expected_ledger_snapshot_hash:
            raise RecoveryOverlayError("PRIMARY_LEDGER_SNAPSHOT_MISMATCH")
        binding = dict(binding)
        binding.update({
            "ledger_snapshot_hash": logical_snapshot_hash,
            "ledger_snapshot_event_count": len(event_rows),
            "ledger_snapshot_last_event_id": event_rows[-1]["id"] if event_rows else None,
        })
        db.close()
    except RecoveryOverlayError:
        if db is not None:
            db.close()
        raise
    except sqlite3.Error as exc:
        if db is not None:
            db.close()
        raise RecoveryOverlayError("PRIMARY_LEDGER_READ_FAILED") from exc
    return records, binding


def _json_load_or_none(value: Any, error: str) -> Any:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return dict(value)
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise RecoveryOverlayError(error) from exc
    return parsed


def normalize_primary_records(records: Sequence[Mapping[str, Any]], canonical: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    by_code = {row["code"]: row for row in canonical}
    by_reel = {row["reel_id"]: row for row in canonical}
    result = {}
    for record in records:
        identity = _resolve_identity(record, by_code, by_reel)
        if type(record.get("identity_index")) is not int or record["identity_index"] != identity["identity_index"]:
            raise RecoveryOverlayError("PRIMARY_IDENTITY_INDEX_MISMATCH")
        if identity["reel_id"] in result:
            raise RecoveryOverlayError("DUPLICATE_PRIMARY_IDENTITY")
        states = record.get("primary_states")
        if not isinstance(states, Mapping):
            raise RecoveryOverlayError("PRIMARY_STATES_INVALID")
        result[identity["reel_id"]] = {
            "primary_states": {str(k): v for k, v in states.items()},
            "primary_artifacts": record.get("primary_artifacts", {}),
            "primary_attempt_history": record.get("primary_attempt_history", []),
        }
    missing = [row["reel_id"] for row in canonical if row["reel_id"] not in result]
    if missing:
        raise RecoveryOverlayError("PRIMARY_IDENTITY_MISSING")
    return result


def load_acquisition_records(root: str | Path) -> list[dict[str, Any]]:
    root = Path(root)
    if _has_symlink_ancestor(root, include_self=True) or not root.is_dir():
        raise RecoveryOverlayError("ACQUISITION_ROOT_INVALID")
    records = []
    for path in sorted(root.rglob("*.media.json")):
        if _has_symlink_ancestor(path, include_self=True):
            raise RecoveryOverlayError("ACQUISITION_ARTIFACT_SYMLINK")
        value = _read_json(path)
        if not isinstance(value, Mapping):
            raise RecoveryOverlayError("ACQUISITION_RECORD_INVALID")
        record = dict(value)
        record["artifact_path"] = str(path.relative_to(root))
        record["record_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        source_hash = _hash_from_record(record, error="ACQUISITION_SOURCE_HASH_INVALID")
        media_path = None
        for candidate_root in (root, root.parent):
            try:
                media_path = _safe_local_candidate(candidate_root, record.get("source_pointer") or record.get("media_path") or record.get("retained_media_path"))
            except RecoveryOverlayError:
                raise
            if media_path is not None and media_path.is_file():
                break
        if record.get("observation_state") == "OBSERVED":
            if media_path is None or not media_path.is_file() or _has_symlink_ancestor(media_path, include_self=True):
                raise RecoveryOverlayError("ACQUISITION_MEDIA_BYTES_UNVERIFIED")
            observed_media_hash = _stream_hash(media_path)
            if source_hash != observed_media_hash:
                raise RecoveryOverlayError("ACQUISITION_MEDIA_HASH_MISMATCH")
            record["media_path"] = str(media_path.relative_to(root.parent if media_path.is_relative_to(root.parent) else root))
            record["media_sha256_verified"] = True
        else:
            record["media_sha256_verified"] = None
        records.append(record)
    return records


def normalize_acquisition_records(records: Sequence[Mapping[str, Any]], canonical: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    by_code = {row["code"]: row for row in canonical}
    by_reel = {row["reel_id"]: row for row in canonical}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        identity = _resolve_identity(record, by_code, by_reel)
        if "identity_index" in record and (type(record["identity_index"]) is not int or record["identity_index"] != identity["identity_index"]):
            raise RecoveryOverlayError("ACQUISITION_IDENTITY_INDEX_MISMATCH")
        source_hash = _hash_from_record(record, error="ACQUISITION_SOURCE_HASH_INVALID")
        if source_hash is None:
            raise RecoveryOverlayError("ACQUISITION_SOURCE_HASH_MISSING")
        if record.get("record_sha256") is None:
            raise RecoveryOverlayError("ACQUISITION_RECORD_HASH_MISSING")
        grouped[identity["reel_id"]].append({
            "source_media_hash": source_hash,
            "artifact_path": record.get("artifact_path"),
            "record_sha256": _hash64(record.get("record_sha256"), "ACQUISITION_RECORD_HASH_MISSING") if record.get("record_sha256") is not None else None,
            "media_path": record.get("media_path"),
            "media_sha256_verified": record.get("media_sha256_verified"),
            "source_pointer": record.get("source_pointer"),
            "observation_state": record.get("observation_state"),
            "has_audio": record.get("has_audio"),
            "original_audio_unknown": record.get("original_audio_unknown"),
            "original_audio_status": record.get("original_audio_status"),
            "speech_state": record.get("speech_state"),
        })
    result = {}
    for reel_id, items in grouped.items():
        hashes = {item["source_media_hash"] for item in items}
        if len(hashes) != 1:
            raise RecoveryOverlayError("ACQUISITION_SOURCE_HASH_CONFLICT")
        result[reel_id] = {"source_media_hash": next(iter(hashes)), "attempts": items,
                           "original_audio_unknown": any(item.get("original_audio_unknown") is True for item in items),
                           "original_audio_status": "UNKNOWN" if any(item.get("original_audio_unknown") is True or item.get("original_audio_status") == "UNKNOWN" for item in items) else items[-1].get("original_audio_status"),
                           "speech_state": "UNKNOWN" if any(item.get("original_audio_unknown") is True or item.get("speech_state") == "UNKNOWN" for item in items) else items[-1].get("speech_state")}
    return result


def _unwrap_recovery(value: Mapping[str, Any]) -> tuple[dict[str, Any], Mapping[str, Any]]:
    if isinstance(value.get("result"), Mapping):
        return dict(value["result"]), value
    return dict(value), value


def _recovery_hashes(result: Mapping[str, Any], wrapper: Mapping[str, Any]) -> set[str]:
    hashes = set()
    for candidate in (result, wrapper, result.get("run_manifest"), wrapper.get("run_manifest"), result.get("request"), wrapper.get("request"), result.get("aggregate_metrics"), wrapper.get("aggregate_metrics")):
        if isinstance(candidate, Mapping):
            value = _hash_from_record(candidate, error="RECOVERY_SOURCE_HASH_INVALID", include_generic_sha256=False)
            if value:
                hashes.add(value)
    for key in ("chunks", "chunk_receipts", "results"):
        values = result.get(key)
        if isinstance(values, list):
            for item in values:
                if isinstance(item, Mapping):
                    value = _hash_from_record(item, error="RECOVERY_SOURCE_HASH_INVALID", include_generic_sha256=False)
                    if value:
                        hashes.add(value)
                    for nested_key in ("request", "run_manifest"):
                        nested = item.get(nested_key)
                        if isinstance(nested, Mapping):
                            value = _hash_from_record(nested, error="RECOVERY_SOURCE_HASH_INVALID", include_generic_sha256=False)
                            if value:
                                hashes.add(value)
    return hashes


def _recovery_identity(record: Mapping[str, Any], code_hint: str, canonical_by_code: Mapping[str, Mapping[str, Any]], canonical_by_reel: Mapping[str, Mapping[str, Any]]) -> Mapping[str, Any]:
    value = dict(record)
    if not value.get("code"):
        value["code"] = code_hint
    return _resolve_identity(value, canonical_by_code, canonical_by_reel)


def _bound_source_pointer_code(outer: Mapping[str, Any], result: Mapping[str, Any]) -> str | None:
    """Derive a bare-run identity only from its bound ``media/<code>.mp4`` pointer."""
    candidates: set[str] = set()
    for part in (outer, result):
        manifest = part.get("run_manifest")
        if not isinstance(manifest, Mapping):
            continue
        pointer = manifest.get("source_pointer")
        if not isinstance(pointer, str):
            continue
        pieces = PurePosixPath(pointer).parts
        if len(pieces) != 2 or pieces[0] != "media" or not pieces[1].endswith(".mp4"):
            continue
        code = pieces[1][:-4]
        if code:
            candidates.add(code)
    if len(candidates) > 1:
        raise RecoveryOverlayError("RECOVERY_IDENTITY_CONFLICT")
    return next(iter(candidates), None)


def _resolve_recovery_identity_parts(
    outer: Mapping[str, Any],
    result: Mapping[str, Any],
    code_hint: str,
    canonical_by_code: Mapping[str, Mapping[str, Any]],
    canonical_by_reel: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Reject wrapper/result identity disagreement before flattening fields."""
    identities = []
    for part in (outer, result):
        if part.get("code") or part.get("reel_id"):
            identities.append(_recovery_identity(part, code_hint, canonical_by_code, canonical_by_reel))
    if identities and any(item["reel_id"] != identities[0]["reel_id"] for item in identities[1:]):
        raise RecoveryOverlayError("RECOVERY_IDENTITY_CONFLICT")
    identity = identities[0] if identities else _recovery_identity({}, code_hint, canonical_by_code, canonical_by_reel)
    for part in (outer, result):
        if "identity_index" in part and (type(part["identity_index"]) is not int or part["identity_index"] != identity["identity_index"]):
            raise RecoveryOverlayError("RECOVERY_IDENTITY_INDEX_MISMATCH")
    return identity


def load_recovery_records(roots: Iterable[str | Path], canonical: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    canonical_by_code = {row["code"]: row for row in canonical}
    canonical_by_reel = {row["reel_id"]: row for row in canonical}
    records = []
    for root_value in roots:
        root = Path(root_value)
        if _has_symlink_ancestor(root, include_self=True) or not root.is_dir():
            raise RecoveryOverlayError("RECOVERY_ROOT_INVALID")
        for path in sorted(root.rglob("transcription-recovery.json")):
            if _has_symlink_ancestor(path, include_self=True):
                raise RecoveryOverlayError("RECOVERY_ARTIFACT_SYMLINK")
            wrapper = _read_json(path)
            if not isinstance(wrapper, Mapping):
                raise RecoveryOverlayError("RECOVERY_RECORD_INVALID")
            result, outer = _unwrap_recovery(wrapper)
            path_hint = path.parent.name
            pointer_hint = _bound_source_pointer_code(outer, result)
            if pointer_hint is not None and path_hint in canonical_by_code and path_hint != pointer_hint:
                raise RecoveryOverlayError("RECOVERY_IDENTITY_CONFLICT")
            code_hint = pointer_hint or path_hint
            identity = _resolve_recovery_identity_parts(outer, result, code_hint, canonical_by_code, canonical_by_reel)
            if pointer_hint is not None and identity["code"] != pointer_hint:
                raise RecoveryOverlayError("RECOVERY_IDENTITY_CONFLICT")
            hashes = _recovery_hashes(result, outer)
            source_hash = _hash_from_record(result, error="RECOVERY_SOURCE_HASH_INVALID", include_generic_sha256=False) or _hash_from_record(outer, error="RECOVERY_SOURCE_HASH_INVALID", include_generic_sha256=False)
            if hashes and (source_hash is None or hashes != {source_hash}):
                raise RecoveryOverlayError("RECOVERY_SOURCE_HASH_CONFLICT")
            records.append({"reel_id": identity["reel_id"], "code": identity["code"], "identity_index": identity["identity_index"], "source_media_hash": source_hash, "artifact_path": str(path.relative_to(root)), "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "result": result, "wrapper": outer})
    return records


def _validated_review_receipt(result: Mapping[str, Any], source_hash: str | None) -> tuple[bool, str | None]:
    """Record a declared receipt, never grant quality authority in a report.

    An embedded object and matching claimed hashes do not authenticate an
    independent acoustic review of actual output bytes. Quality promotion
    belongs to a separate reviewed adapter; this overlay stays report-only.
    """
    receipt = result.get("review_receipt")
    return False, _json_hash(dict(receipt)) if isinstance(receipt, Mapping) else None


def _stream_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _attempt_summary(record: Mapping[str, Any], expected_source_hash: str | None) -> dict[str, Any]:
    result = record["result"]
    source_hash = record.get("source_media_hash")
    if expected_source_hash is not None and source_hash != expected_source_hash:
        raise RecoveryOverlayError("RECOVERY_ACQUISITION_SOURCE_MISMATCH")
    artifact_hash = record.get("artifact_sha256")
    if artifact_hash is None:
        raise RecoveryOverlayError("RECOVERY_ARTIFACT_HASH_MISSING")
    artifact_hash = _hash64(artifact_hash, "RECOVERY_ARTIFACT_HASH_INVALID")
    state = result.get("observation_state", record["wrapper"].get("state"))
    if not isinstance(state, str) or not state:
        state = "UNKNOWN"
    aggregate = result.get("aggregate_metrics") if isinstance(result.get("aggregate_metrics"), Mapping) else {}
    count = result.get("owned_aligned_word_count", aggregate.get("owned_aligned_word_count"))
    if count is not None and (type(count) is not int or count < 0):
        raise RecoveryOverlayError("RECOVERY_WORD_COUNT_INVALID")
    chunk_count = result.get("chunk_count")
    completed = result.get("completed_chunk_count")
    if chunk_count is not None and (type(chunk_count) is not int or chunk_count < 0):
        raise RecoveryOverlayError("RECOVERY_CHUNK_COUNT_INVALID")
    if completed is not None and (type(completed) is not int or completed < 0 or (chunk_count is not None and completed > chunk_count)):
        raise RecoveryOverlayError("RECOVERY_COMPLETED_CHUNK_COUNT_INVALID")
    reported_review_state = result.get("review_state", "REVIEW_REQUIRED")
    review_state = reported_review_state
    if not isinstance(review_state, str) or not review_state:
        review_state = "REVIEW_REQUIRED"
    metric_names = ("lexical_word_count", "aligned_word_count", "unaligned_word_count", "raw_word_count")
    word_metrics = {}
    for name in metric_names:
        value = result.get(name, aggregate.get(name))
        if value is not None and (type(value) is not int or value < 0):
            raise RecoveryOverlayError("RECOVERY_WORD_METRIC_INVALID")
        word_metrics[name] = value
    raw_result = result.get("raw") if isinstance(result.get("raw"), Mapping) else {}
    language = result.get("language", aggregate.get("language", raw_result.get("language")))
    language_probability = result.get("language_probability", aggregate.get("language_probability", raw_result.get("language_probability")))
    if language_probability is not None and (not _finite(language_probability) or not 0 <= float(language_probability) <= 1):
        raise RecoveryOverlayError("RECOVERY_LANGUAGE_PROBABILITY_INVALID")
    reported_analysis_approved = result.get("analysis_approved") is True
    reported_analysis_ready = result.get("analysis_ready") is True
    receipt_valid, review_receipt_hash = _validated_review_receipt(result, source_hash)
    effective_review = receipt_valid
    if not effective_review:
        review_state = "REVIEW_REQUIRED"
    acoustic_review_state = result.get("acoustic_review_state", "NOT_REVIEWED")
    if not isinstance(acoustic_review_state, str) or not acoustic_review_state:
        acoustic_review_state = "NOT_REVIEWED"
    return {
        "artifact_path": record["artifact_path"],
        "artifact_sha256": artifact_hash,
        "attempt_number": result.get("attempt", record["wrapper"].get("attempt")) if type(result.get("attempt", record["wrapper"].get("attempt"))) is int else None,
        "source_media_hash": source_hash,
        "observation_state": state,
        "machine_observed": result.get("machine_observed") is True,
        "owned_aligned_words": {"count": count, "state": "OBSERVED_COUNT_ONLY" if count is not None else "UNAVAILABLE"},
        "word_metrics": word_metrics,
        "language": language,
        "language_probability": language_probability,
        "timing_state": aggregate.get("word_timing", result.get("word_timing")),
        "chunk_coverage": {"chunk_count": chunk_count, "completed_chunk_count": completed, "incomplete_chunks": result.get("incomplete_chunks"), "state": "COMPLETE" if chunk_count is not None and completed == chunk_count else "PARTIAL_OR_UNKNOWN"},
        "review_state": review_state,
        "reported_review_state": reported_review_state,
        "review_receipt_state": "DECLARED_UNVERIFIED" if review_receipt_hash else "MISSING_OR_INVALID",
        "review_receipt_sha256": review_receipt_hash,
        "reported_acoustic_review_state": acoustic_review_state,
        "acoustic_review_state": "NOT_REVIEWED",
        "reported_analysis_approved": reported_analysis_approved,
        "reported_analysis_ready": reported_analysis_ready,
        "analysis_approved": reported_analysis_approved and effective_review,
        "analysis_ready": reported_analysis_ready and effective_review,
        "original_audio_status": "UNKNOWN" if result.get("original_audio_unknown") is True or result.get("original_audio_status") == "UNKNOWN" else result.get("original_audio_status"),
        "original_audio_unknown": result.get("original_audio_unknown") is True,
        "speech_state": "UNKNOWN" if result.get("original_audio_unknown") is True or result.get("speech_state") == "UNKNOWN" else result.get("speech_state"),
        "boundary_issues": list(result.get("boundary_issues", [])) if isinstance(result.get("boundary_issues", []), list) else None,
    }


def _merge_recovery_attempts(
    attempts: Sequence[Mapping[str, Any]],
    source_hash: str | None,
    *,
    original_audio_unknown: bool = False,
    original_audio_status: str | None = None,
    speech_state: str | None = None,
) -> dict[str, Any]:
    if not attempts:
        unknown = original_audio_unknown or source_hash is None
        return {"state": "NOT_ATTEMPTED", "attempt_count": 0, "attempts": [], "source_media_hash": source_hash, "machine_observed": False, "owned_aligned_words": {"count": None, "state": "UNAVAILABLE"}, "word_metrics": {name: None for name in ("lexical_word_count", "aligned_word_count", "unaligned_word_count", "raw_word_count")}, "language": None, "language_probability": None, "timing_state": None, "complete_chunk_coverage": {"chunk_count": None, "completed_chunk_count": None, "incomplete_chunks": None, "state": "NOT_ATTEMPTED"}, "review_state": "NOT_ATTEMPTED", "acoustic_review_state": "NOT_REVIEWED", "reported_analysis_approved": False, "reported_analysis_ready": False, "analysis_approved": False, "analysis_ready": False, "original_audio_status": "UNKNOWN" if unknown else (original_audio_status or "NOT_EVALUATED"), "original_audio_unknown": unknown, "speech_state": "UNKNOWN" if unknown else (speech_state or "NOT_EVALUATED")}
    indexed = [(a.get("attempt_number"), position, a) for position, a in enumerate(attempts)]
    numbered = [number for number, _position, _attempt in indexed if number is not None]
    if len(numbered) != len(set(numbered)):
        raise RecoveryOverlayError("RECOVERY_ATTEMPT_DUPLICATE")
    latest_number = max((number for number, _position, _attempt in indexed if number is not None), default=None)
    latest = next((a for number, _position, a in reversed(indexed) if latest_number is None or number == latest_number), attempts[-1])
    if original_audio_unknown or any(a["original_audio_unknown"] for a in attempts):
        original_audio_status, speech_state, original_unknown = "UNKNOWN", "UNKNOWN", True
    else:
        original_audio_status = latest["original_audio_status"] if latest["original_audio_status"] is not None else original_audio_status
        speech_state = latest["speech_state"] if latest["speech_state"] is not None else speech_state
        original_unknown = False
    return {
        "state": latest["observation_state"],
        "attempt_count": len(attempts),
        "attempts": list(attempts),
        "machine_observed": latest["machine_observed"],
        "selected_attempt_artifact_path": latest["artifact_path"],
        "selected_attempt_artifact_sha256": latest["artifact_sha256"],
        "selected_attempt_number": latest.get("attempt_number"),
        "prior_attempt_machine_observed": any(a["machine_observed"] for a in attempts if a is not latest),
        "source_media_hash": source_hash,
        "owned_aligned_words": dict(latest["owned_aligned_words"]),
        "word_metrics": dict(latest["word_metrics"]),
        "language": latest["language"],
        "language_probability": latest["language_probability"],
        "timing_state": latest["timing_state"],
        "complete_chunk_coverage": latest["chunk_coverage"],
        "review_state": latest["review_state"],
        "reported_review_state": latest["reported_review_state"],
        "review_receipt_state": latest["review_receipt_state"],
        "review_receipt_sha256": latest["review_receipt_sha256"],
        "acoustic_review_state": latest["acoustic_review_state"],
        "reported_analysis_approved": latest["reported_analysis_approved"],
        "reported_analysis_ready": latest["reported_analysis_ready"],
        "analysis_approved": latest["analysis_approved"],
        "analysis_ready": latest["analysis_ready"],
        "original_audio_status": original_audio_status,
        "original_audio_unknown": original_unknown,
        "speech_state": speech_state,
    }


def _fresh_output(path: Path) -> None:
    if _has_symlink_ancestor(path, include_self=True) or path.exists() or path.is_symlink():
        raise RecoveryOverlayError("OUTPUT_DIRECTORY_MUST_BE_NEW")
    if path.parent.is_symlink():
        raise RecoveryOverlayError("OUTPUT_PARENT_SYMLINK")
    path.mkdir(parents=False)


def build_recovery_overlay(
    canonical_records: Sequence[Mapping[str, Any]],
    primary_records: Sequence[Mapping[str, Any]],
    acquisition_records: Sequence[Mapping[str, Any]],
    recovery_records: Sequence[Mapping[str, Any]],
    *,
    source_snapshot_hash: str,
    primary_binding: Mapping[str, Any] | None = None,
    expected_ledger_snapshot_hash: str | None = None,
    output_dir: str | Path | None = None,
    expected_population: int | None = 2352,
) -> dict[str, Any]:
    source_snapshot_hash = _hash64(source_snapshot_hash, "SOURCE_SNAPSHOT_HASH_INVALID")
    if primary_binding is not None and not isinstance(primary_binding, Mapping):
        raise RecoveryOverlayError("PRIMARY_BINDING_INVALID")
    if primary_binding is not None:
        for key in ("manifest_sha256", "source_snapshot_hash"):
            value = primary_binding.get(key)
            if value is not None and (not isinstance(value, str) or value.lower() != source_snapshot_hash):
                raise RecoveryOverlayError("PRIMARY_SNAPSHOT_MISMATCH")
    ledger_snapshot_hash = None
    if primary_binding is not None and primary_binding.get("ledger_snapshot_hash") is not None:
        ledger_snapshot_hash = _hash64(primary_binding["ledger_snapshot_hash"], "LEDGER_SNAPSHOT_HASH_INVALID")
    if expected_ledger_snapshot_hash is not None:
        expected_ledger_snapshot_hash = _hash64(expected_ledger_snapshot_hash, "LEDGER_SNAPSHOT_HASH_INVALID")
        if ledger_snapshot_hash != expected_ledger_snapshot_hash:
            raise RecoveryOverlayError("PRIMARY_LEDGER_SNAPSHOT_MISMATCH")
    canonical = normalize_canonical_records(canonical_records, expected_population=expected_population)
    for row in canonical:
        if row["source_snapshot_hash"] is not None and row["source_snapshot_hash"] != source_snapshot_hash:
            raise RecoveryOverlayError("CANONICAL_SNAPSHOT_MISMATCH")
    by_code = {row["code"]: row for row in canonical}
    by_reel = {row["reel_id"]: row for row in canonical}
    primary = normalize_primary_records(primary_records, canonical)
    acquisition = normalize_acquisition_records(acquisition_records, canonical)
    recovery_by_reel: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in recovery_records:
        identity = _resolve_identity(record, by_code, by_reel)
        if type(record.get("identity_index")) is not int or record["identity_index"] != identity["identity_index"]:
            raise RecoveryOverlayError("RECOVERY_IDENTITY_INDEX_MISMATCH")
        source_hash = _hash64(record["source_media_hash"], "RECOVERY_SOURCE_HASH_MISSING") if record.get("source_media_hash") is not None else None
        if source_hash is None:
            raise RecoveryOverlayError("RECOVERY_SOURCE_HASH_MISSING")
        nested_hashes = _recovery_hashes(record.get("result", {}), record.get("wrapper", {}))
        if nested_hashes and nested_hashes != {source_hash}:
            raise RecoveryOverlayError("RECOVERY_SOURCE_HASH_CONFLICT")
        expected_hash = acquisition.get(identity["reel_id"], {}).get("source_media_hash")
        recovery_by_reel[identity["reel_id"]].append(_attempt_summary({**record, "source_media_hash": source_hash}, expected_hash))
    rows = []
    for identity in canonical:
        reel_id = identity["reel_id"]
        acq = acquisition.get(reel_id)
        recovery_hashes = {attempt["source_media_hash"] for attempt in recovery_by_reel.get(reel_id, []) if attempt.get("source_media_hash") is not None}
        if len(recovery_hashes) > 1:
            raise RecoveryOverlayError("RECOVERY_SOURCE_HASH_CONFLICT")
        acquisition_hash = acq["source_media_hash"] if acq else None
        recovery_hash = next(iter(recovery_hashes), None)
        if acquisition_hash is not None and recovery_hash is not None and acquisition_hash != recovery_hash:
            raise RecoveryOverlayError("RECOVERY_ACQUISITION_SOURCE_MISMATCH")
        source_hash = acquisition_hash or recovery_hash
        primary_row = primary[reel_id]
        observed_primary = primary_row["primary_states"].get("acquisition") == "OBSERVED"
        if observed_primary and acq is None:
            raise RecoveryOverlayError("PRIMARY_OBSERVED_ACQUISITION_MISSING")
        if observed_primary:
            primary_hashes = set()
            for digest in primary_row["primary_artifacts"].get("acquisition", {}).values():
                primary_hashes.add(digest)
            if source_hash is not None and primary_hashes and source_hash not in primary_hashes:
                raise RecoveryOverlayError("PRIMARY_ACQUISITION_SOURCE_HASH_MISMATCH")
        recovery = _merge_recovery_attempts(
            recovery_by_reel.get(reel_id, []), source_hash,
            original_audio_unknown=bool(acq and acq.get("original_audio_unknown")),
            original_audio_status=acq.get("original_audio_status") if acq else None,
            speech_state=acq.get("speech_state") if acq else None,
        )
        rows.append({
            "identity_index": identity["identity_index"],
            "reel_id": reel_id,
            "code": identity["code"],
            "source_snapshot_hash": source_snapshot_hash,
            "canonical_source_media_hash": identity.get("source_media_hash"),
            "source_media_hash": source_hash,
            "primary": primary_row,
            "acquisition": acq or {"source_media_hash": None, "attempts": []},
            "recovery": recovery,
            "overlay_disposition": "RECOVERY_OVERLAY_REVIEW_REQUIRED" if recovery["attempt_count"] else "PRIMARY_ONLY_NO_RECOVERY_ATTEMPT",
        })
    report = {
        "schema": SCHEMA,
        "status": "RECOVERY_OVERLAY_COMPLETE_WITH_REVIEW_REQUIRED",
        "source_binding": {"source_snapshot_hash": source_snapshot_hash, "canonical_population": len(canonical), "primary_ledger_unchanged": True, "recovery_is_overlay": True,
                            "primary_ledger_snapshot_hash": ledger_snapshot_hash,
                            "primary_ledger_event_count": primary_binding.get("ledger_snapshot_event_count") if primary_binding else None,
                            "primary_ledger_last_event_id": primary_binding.get("ledger_snapshot_last_event_id") if primary_binding else None},
        "population": {"canonical_rows": len(rows), "primary_rows": len(primary), "recovery_attempt_rows": sum(len(v) for v in recovery_by_reel.values()), "reels_with_recovery_attempt": sum(bool(v) for v in recovery_by_reel.values()), "reels_machine_observed_recovery": sum(r["recovery"].get("machine_observed") is True for r in rows)},
        "denominators": {"primary_transcript_states": _counts(r["primary"]["primary_states"].get("transcript") for r in rows), "recovery_states": _counts(r["recovery"]["state"] for r in rows), "recovery_review_states": _counts(r["recovery"]["review_state"] for r in rows)},
        "limitations": ["Primary ledger states and attempt history are preserved and never overwritten by this overlay.", "Machine-observed recovery words are not acoustic-reviewed transcript evidence; analysis approval remains separate.", "Video-only retained sources preserve original audio and speech as UNKNOWN even when a downstream ASR state is NOT_APPLICABLE.", "Null fields mean unavailable or unverified; no missing count, duration, or word total is converted to zero."],
        "rows": rows,
    }
    if output_dir is not None:
        destination = Path(output_dir).absolute()
        _fresh_output(destination)
        jsonl = destination / "recovery-overlay.jsonl"
        csv_path = destination / "recovery-overlay.csv"
        with jsonl.open("x", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
        columns = [
            "identity_index", "reel_id", "code", "source_snapshot_hash", "canonical_source_media_hash", "source_media_hash", "overlay_disposition",
            "primary_acquisition_state", "primary_transcript_state", "primary_frames_state", "primary_scene_review_state", "primary_attempt_count", "primary_artifact_count",
            "acquisition_observation_state", "acquisition_source_pointer", "acquisition_record_count", "acquisition_media_sha256_verified", "acquisition_original_audio_unknown", "acquisition_speech_state",
            "recovery_state", "recovery_attempt_count", "recovery_selected_attempt_number", "recovery_selected_attempt_artifact_sha256", "recovery_source_media_hash", "recovery_owned_aligned_word_count", "recovery_owned_aligned_word_state",
            "recovery_lexical_word_count", "recovery_aligned_word_count", "recovery_unaligned_word_count", "recovery_raw_word_count", "recovery_language", "recovery_language_probability", "recovery_timing_state",
            "recovery_chunk_count", "recovery_completed_chunk_count", "recovery_chunk_coverage_state", "recovery_review_state", "recovery_reported_review_state", "recovery_review_receipt_state", "recovery_acoustic_review_state",
            "recovery_reported_analysis_approved", "recovery_reported_analysis_ready", "recovery_analysis_approved", "recovery_analysis_ready", "recovery_original_audio_status", "recovery_original_audio_unknown", "recovery_speech_state",
        ]
        with csv_path.open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            for row in rows:
                primary_row = row["primary"]
                primary_states = primary_row["primary_states"]
                acq = row["acquisition"]
                acq_attempts = acq.get("attempts", [])
                acq_latest = acq_attempts[-1] if acq_attempts else {}
                recovery = row["recovery"]
                coverage = recovery.get("complete_chunk_coverage") or {}
                values = {
                    "identity_index": row["identity_index"], "reel_id": row["reel_id"], "code": row["code"], "source_snapshot_hash": row["source_snapshot_hash"], "canonical_source_media_hash": row["canonical_source_media_hash"], "source_media_hash": row["source_media_hash"], "overlay_disposition": row["overlay_disposition"],
                    "primary_acquisition_state": primary_states.get("acquisition"), "primary_transcript_state": primary_states.get("transcript"), "primary_frames_state": primary_states.get("frames"), "primary_scene_review_state": primary_states.get("scene_review"), "primary_attempt_count": len(primary_row.get("primary_attempt_history", [])), "primary_artifact_count": sum(len(v) for v in primary_row.get("primary_artifacts", {}).values() if isinstance(v, Mapping)),
                    "acquisition_observation_state": acq_latest.get("observation_state"), "acquisition_source_pointer": acq_latest.get("source_pointer"), "acquisition_record_count": len(acq_attempts), "acquisition_media_sha256_verified": acq_latest.get("media_sha256_verified"), "acquisition_original_audio_unknown": acq.get("original_audio_unknown"), "acquisition_speech_state": acq.get("speech_state"),
                    "recovery_state": recovery.get("state"), "recovery_attempt_count": recovery.get("attempt_count"), "recovery_selected_attempt_number": recovery.get("selected_attempt_number"), "recovery_selected_attempt_artifact_sha256": recovery.get("selected_attempt_artifact_sha256"), "recovery_source_media_hash": recovery.get("source_media_hash"), "recovery_owned_aligned_word_count": recovery.get("owned_aligned_words", {}).get("count"), "recovery_owned_aligned_word_state": recovery.get("owned_aligned_words", {}).get("state"),
                    "recovery_lexical_word_count": recovery.get("word_metrics", {}).get("lexical_word_count"), "recovery_aligned_word_count": recovery.get("word_metrics", {}).get("aligned_word_count"), "recovery_unaligned_word_count": recovery.get("word_metrics", {}).get("unaligned_word_count"), "recovery_raw_word_count": recovery.get("word_metrics", {}).get("raw_word_count"), "recovery_language": recovery.get("language"), "recovery_language_probability": recovery.get("language_probability"), "recovery_timing_state": recovery.get("timing_state"),
                    "recovery_chunk_count": coverage.get("chunk_count"), "recovery_completed_chunk_count": coverage.get("completed_chunk_count"), "recovery_chunk_coverage_state": coverage.get("state"), "recovery_review_state": recovery.get("review_state"), "recovery_reported_review_state": recovery.get("reported_review_state"), "recovery_review_receipt_state": recovery.get("review_receipt_state"), "recovery_acoustic_review_state": recovery.get("acoustic_review_state"),
                    "recovery_reported_analysis_approved": recovery.get("reported_analysis_approved"), "recovery_reported_analysis_ready": recovery.get("reported_analysis_ready"), "recovery_analysis_approved": recovery.get("analysis_approved"), "recovery_analysis_ready": recovery.get("analysis_ready"), "recovery_original_audio_status": recovery.get("original_audio_status"), "recovery_original_audio_unknown": recovery.get("original_audio_unknown"), "recovery_speech_state": recovery.get("speech_state"),
                }
                writer.writerow(values)
        fields = {}
        for column in columns:
            fields[column] = {"source": "overlay row", "null_meaning": "unavailable or unverified; never zero", "unit": "state/count/hash/text as named", "description": "Flat row-level export field; detailed primary/recovery attempt arrays remain in JSONL."}
        fields.update({
            "primary.primary_states": {"source": "JSONL primary.primary_states", "null_meaning": "explicit stage state required", "unit": "categorical state", "description": "Acquisition, transcript, frames, and scene-review states from the primary ledger."},
            "primary.primary_artifacts": {"source": "JSONL primary.primary_artifacts", "null_meaning": "empty map means no committed artifacts", "unit": "relative path to SHA-256", "description": "Primary committed artifact bindings."},
            "primary.primary_attempt_history": {"source": "JSONL primary.primary_attempt_history", "null_meaning": "empty array means no recorded primary attempt", "unit": "attempt records", "description": "Complete primary history, including failures; never overwritten by recovery."},
            "acquisition.attempts": {"source": "JSONL acquisition.attempts", "null_meaning": "empty array means no retained-source receipt", "unit": "attempt records", "description": "Retained source mapping and record/media byte-binding evidence."},
            "acquisition.source_media_hash": {"source": "retained acquisition receipt", "null_meaning": "no retained source hash", "unit": "SHA-256", "description": "Per-media hash; distinct from the global source snapshot hash."},
            "source_snapshot_hash": {"source": "canonical manifest binding", "null_meaning": "never omitted after validation", "unit": "SHA-256", "description": "Global canonical source snapshot hash."},
            "canonical_source_media_hash": {"source": "optional canonical manifest field", "null_meaning": "not supplied by canonical manifest", "unit": "SHA-256", "description": "Optional per-media hash from canonical input; never used as the global snapshot hash."},
            "source_media_hash": {"source": "acquisition/recovery source binding", "null_meaning": "no retained or recovery source hash", "unit": "SHA-256", "description": "Per-media source hash used to join recovery evidence."},
            "primary_attempt_history": {"source": "JSONL primary.primary_attempt_history", "null_meaning": "empty array means no recorded attempt", "unit": "attempt records", "description": "Complete primary attempt history, preserved without recovery promotion."},
            "recovery.attempts": {"source": "JSONL recovery.attempts", "null_meaning": "empty array means no recovery attempt", "unit": "attempt records", "description": "All source/hash-bound recovery attempts; selected attempt alone supplies flat summary metrics."},
            "recovery.word_metrics": {"source": "selected recovery attempt", "null_meaning": "unavailable or unverified", "unit": "word counts", "description": "Lexical/aligned/unaligned/raw counts; padding and cross-attempt values are not silently added."},
            "recovery.acoustic_review_state": {"source": "selected recovery attempt", "null_meaning": "NOT_REVIEWED", "unit": "review state", "description": "Independent acoustic review status, separate from machine observation."},
            "recovery.original_audio_unknown": {"source": "retained acquisition/recovery evidence", "null_meaning": "unknown when absent", "unit": "boolean", "description": "Preserves unknown original audio/speech for video-only fallback; never means no speech."},
            "recovery.reported_analysis_ready": {"source": "machine result, audit only", "null_meaning": "false when absent", "unit": "boolean", "description": "Reported flag retained separately; effective analysis readiness requires a validated hash-bound scoped review receipt."},
            "denominators": {"source": "report.denominators", "null_meaning": "not applicable", "unit": "counts by explicit state", "description": "Primary and recovery state counts use disjoint status fields; missing rows remain in the 2,352 identity denominator."},
        })
        (destination / "field-dictionary.json").write_text(json.dumps(fields, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        report["artifacts"] = {"jsonl": jsonl.name, "csv": csv_path.name, "field_dictionary": "field-dictionary.json", "jsonl_sha256": hashlib.sha256(jsonl.read_bytes()).hexdigest(), "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest()}
        (destination / "report-manifest.json").write_text(json.dumps({"schema": "m2.recovery-overlay-artifacts.v1", "report": report, "files": report["artifacts"]}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report


def _counts(values: Iterable[Any]) -> dict[str, int]:
    counts = Counter(str(value) if value is not None else "UNKNOWN" for value in values)
    return dict(sorted(counts.items()))


def _cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-manifest", required=True, type=Path)
    parser.add_argument("--primary-ledger", required=True, type=Path)
    parser.add_argument("--acquisition-root", required=True, type=Path)
    parser.add_argument("--video-only-root", action="append", default=[], type=Path,
                        help="Additional bounded acquisition roots containing retained video-only records")
    parser.add_argument("--recovery-root", required=True, action="append", type=Path)
    parser.add_argument("--source-snapshot-hash", required=True)
    parser.add_argument("--ledger-snapshot-hash", required=True, help="Expected logical hash of one transactionally captured primary-ledger snapshot")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--expected-population", type=int, default=2352)
    args = parser.parse_args(argv)
    canonical = load_canonical_records(args.canonical_manifest, expected_snapshot_hash=args.source_snapshot_hash, expected_population=args.expected_population)
    primary, primary_binding = load_primary_ledger(args.primary_ledger, expected_snapshot_hash=args.source_snapshot_hash, expected_ledger_snapshot_hash=args.ledger_snapshot_hash)
    acquisition: list[dict[str, Any]] = []
    for acquisition_root in (args.acquisition_root, *args.video_only_root):
        acquisition.extend(load_acquisition_records(acquisition_root))
    recovery = load_recovery_records(args.recovery_root, canonical)
    report = build_recovery_overlay(canonical, primary, acquisition, recovery, source_snapshot_hash=args.source_snapshot_hash, primary_binding=primary_binding, expected_ledger_snapshot_hash=args.ledger_snapshot_hash, output_dir=args.output_dir, expected_population=args.expected_population)
    print(json.dumps({key: report[key] for key in ("schema", "status", "source_binding", "population", "denominators", "artifacts") if key in report}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
