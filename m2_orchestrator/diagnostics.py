"""Export a read-only, provenance checked controller snapshot.

The export is deliberately separate from the controller database. It never
calls ``Controller`` (a diagnostics change can alter an existing run's runtime
fingerprint), never writes to a source database, and never copies run config.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
from pathlib import Path
from typing import Any

from .policy import BY_ID
from .state import digest


class DiagnosticsError(ValueError):
    """A controller or diagnostics input cannot be safely exported."""


EXPORT_SCHEMA_VERSION = "m2.diagnostic-v2"
SUCCESS_STATES = {"PASS", "PASS_WITH_LIMITATIONS"}


def _file_hash(path: Path) -> str:
    if not path.is_file():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_relative_path(root: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise DiagnosticsError("ARTIFACT_PATH_OUTSIDE_ROOT")
    resolved_root = root.resolve()
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise DiagnosticsError("ARTIFACT_PATH_OUTSIDE_ROOT") from exc
    return resolved


def _parse_json(value: str, label: str) -> dict[str, Any]:
    try:
        result = json.loads(value)
    except (TypeError, ValueError) as exc:
        raise DiagnosticsError(f"JSON_INVALID:{label}") from exc
    if not isinstance(result, dict):
        raise DiagnosticsError(f"JSON_OBJECT_REQUIRED:{label}")
    return result


def _finite(value: Any) -> bool:
    return value is None or (isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value))


def _expected_unit(metric_name: str) -> str | None:
    if metric_name.endswith("_per_1k_views"):
        return "events_per_1000_views"
    if metric_name in {"views", "likes", "comments", "reshares", "saves", "followers", "source_observations"}:
        return "count"
    if metric_name == "duration_seconds":
        return "seconds"
    if metric_name == "creator_view_index":
        return "index"
    if metric_name == "diagnostic_equal_weight_z" or metric_name.endswith("_robust_z"):
        return "robust_z"
    if metric_name.endswith("_coverage") or metric_name.endswith("_rate"):
        return "fraction"
    return None


def _metric_issues(metric_name: str, unit: str | None, value: Any, denominator: Any, observed_n: Any) -> list[str]:
    issues: list[str] = []
    expected = _expected_unit(metric_name)
    if expected and unit and expected != unit:
        issues.append(f"UNIT_MISMATCH:{unit}->{expected}")
    if not _finite(value):
        issues.append("NON_FINITE_VALUE")
    if not _finite(denominator):
        issues.append("NON_FINITE_DENOMINATOR")
    if denominator is not None and isinstance(denominator, (int, float)) and not isinstance(denominator, bool) and denominator < 0:
        issues.append("NEGATIVE_DENOMINATOR")
    if value is not None and _finite(value):
        if unit == "events_per_1000_views":
            if value < 0:
                issues.append("NEGATIVE_RATE")
            if denominator is None or not _finite(denominator) or denominator <= 0:
                issues.append("DENOMINATOR_MUST_BE_POSITIVE")
        elif unit == "fraction" and (value < 0 or value > 1):
            issues.append("FRACTION_OUT_OF_BOUNDS")
        elif unit in {"count", "seconds", "index"} and value < 0:
            issues.append("NEGATIVE_VALUE")
        elif unit == "robust_z" and not -5 <= value <= 5:
            issues.append("ROBUST_Z_OUT_OF_BOUNDS")
    if observed_n is not None and (not isinstance(observed_n, int) or isinstance(observed_n, bool) or observed_n < 0):
        issues.append("INVALID_OBSERVED_N")
    return issues


def _issue(run_id: str, stage_id: str, kind: str, ordinal: int, *, severity: str = "MED", status: str = "OPEN",
           opened: int | None = None, resolved: int | None = None, error_code: str, error_message: str | None = None,
           evidence_hash: str | None = None, solution: str | None = None, learning_evidence: str | None = None) -> dict[str, Any]:
    return {"run_id": run_id, "issue_id": f"{run_id}:{stage_id}:{kind}:{ordinal}", "stage_id": stage_id,
            "kind": kind, "severity": severity, "status": status, "opened_event_seq": opened,
            "resolved_event_seq": resolved, "error_code": error_code, "error_message": error_message,
            "evidence_hash": evidence_hash, "solution": solution, "learning_evidence": learning_evidence}


_SENSITIVE_EVENT_KEYS = {"token", "api_key", "apikey", "password", "cookie", "authorization", "secret"}


def _masked_event_payload(value: Any) -> Any:
    """Keep the trace useful while excluding credentials and worker tokens."""
    if isinstance(value, dict):
        return {key: "[REDACTED]" if str(key).lower() in _SENSITIVE_EVENT_KEYS else _masked_event_payload(item)
                for key, item in value.items()}
    if isinstance(value, list):
        return [_masked_event_payload(item) for item in value]
    return value


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA foreign_keys=ON;
        CREATE TABLE IF NOT EXISTS diagnostic_exports(
            run_id TEXT NOT NULL, schema_version TEXT NOT NULL, state_db_path TEXT NOT NULL,
            signal_db_path TEXT, run_config_hash TEXT NOT NULL, policy_hash TEXT NOT NULL,
            controller_db_hash TEXT NOT NULL, signal_db_hash TEXT, source_signature TEXT NOT NULL,
            state_events_ok INTEGER NOT NULL, total_stages INTEGER NOT NULL,
            PRIMARY KEY(run_id, schema_version)
        );
        CREATE TABLE IF NOT EXISTS diagnostic_events(
            run_id TEXT NOT NULL, seq INTEGER NOT NULL, stage TEXT, kind TEXT NOT NULL, at REAL,
            previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL, payload TEXT NOT NULL, chain_valid INTEGER NOT NULL,
            PRIMARY KEY(run_id, seq)
        );
        CREATE TABLE IF NOT EXISTS diagnostic_stages(
            run_id TEXT NOT NULL, stage_id TEXT NOT NULL, stage_index INTEGER NOT NULL, goal TEXT NOT NULL,
            actor TEXT, state TEXT NOT NULL, attempt INTEGER NOT NULL, limitations_count INTEGER NOT NULL,
            completion_hash TEXT, receipt_artifact_hash TEXT, input_signature TEXT, provenance_ok INTEGER NOT NULL,
            PRIMARY KEY(run_id, stage_id)
        );
        CREATE TABLE IF NOT EXISTS diagnostic_stage_artifacts(
            run_id TEXT NOT NULL, stage_id TEXT NOT NULL, path TEXT NOT NULL, expected_sha256 TEXT,
            observed_sha256 TEXT, size_bytes INTEGER, validation TEXT NOT NULL,
            PRIMARY KEY(run_id, stage_id, path)
        );
        CREATE TABLE IF NOT EXISTS diagnostic_metrics(
            run_id TEXT NOT NULL, release_id TEXT NOT NULL, scope TEXT NOT NULL CHECK(scope IN ('reel','account')),
            entity_id TEXT NOT NULL, metric_name TEXT NOT NULL, unit TEXT NOT NULL, value REAL,
            denominator REAL, observed_n INTEGER, formula_version TEXT, is_missing INTEGER NOT NULL,
            validation_state TEXT NOT NULL, validation_issues TEXT,
            PRIMARY KEY(run_id, release_id, scope, entity_id, metric_name)
        );
        CREATE TABLE IF NOT EXISTS diagnostic_issues(
            run_id TEXT NOT NULL, issue_id TEXT NOT NULL, stage_id TEXT NOT NULL, kind TEXT NOT NULL,
            severity TEXT NOT NULL, status TEXT NOT NULL, opened_event_seq INTEGER, resolved_event_seq INTEGER,
            error_code TEXT NOT NULL, error_message TEXT, evidence_hash TEXT, solution TEXT, learning_evidence TEXT,
            PRIMARY KEY(run_id, issue_id)
        );
        """
    )


def _readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.execute("PRAGMA query_only=ON")
    connection.execute("BEGIN")
    return connection


def _logical_hash(connection: sqlite3.Connection) -> str:
    # Hash the transaction snapshot, including committed WAL rows. This is a
    # logical SQL digest, not a digest of the database file's physical bytes.
    h = hashlib.sha256()
    for statement in connection.iterdump():
        h.update(statement.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _same_file(left: Path, right: Path | None) -> bool:
    return right is not None and (left == right or
        (left.exists() and right.exists() and left.samefile(right)))


def _read_controller_state(state_path: Path):
    if not state_path.is_file():
        raise DiagnosticsError("STATE_DB_MISSING")
    connection = _readonly(state_path)
    connection.row_factory = sqlite3.Row
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"run", "stages", "events", "approvals"}.issubset(tables):
            raise DiagnosticsError("CONTROLLER_SCHEMA_INVALID")
        run = connection.execute("SELECT * FROM run LIMIT 1").fetchone()
        if run is None:
            raise DiagnosticsError("CONTROLLER_RUN_MISSING")
        config = _parse_json(run["config"], "run.config")
        stages = [dict(row) for row in connection.execute("SELECT * FROM stages ORDER BY rowid")]
        events = [dict(row) for row in connection.execute("SELECT * FROM events ORDER BY seq")]
        return connection, run, config, stages, events
    except Exception:
        connection.close()
        raise


def _validate_events(run_id: str, events: list[dict[str, Any]], known_stages: set[str], issues: list[dict[str, Any]]):
    rows: list[tuple] = []
    previous = "0" * 64
    valid = True
    failures: dict[str, dict[str, Any]] = {}
    ordinal = 0
    expected_seq = 1
    for row in events:
        seq = row["seq"]
        try:
            payload = _parse_json(row["payload"], f"events:{seq}")
        except DiagnosticsError as exc:
            ordinal += 1
            issues.append(_issue(run_id, "_unknown", "event", ordinal, severity="HIGH", opened=seq,
                                 error_code=str(exc), error_message=f"event {seq} payload is invalid",
                                 evidence_hash=row.get("hash"), solution="Recover from immutable event source",
                                 learning_evidence="Event payload must be canonical JSON"))
            valid = False
            payload = {"kind": "INVALID"}
        expected_hash = digest({"previous": previous, "payload": payload})
        chain_valid = row.get("previous") == previous and row.get("hash") == expected_hash and seq == expected_seq
        if not chain_valid:
            ordinal += 1
            code = "EVENT_SEQUENCE_GAP" if seq != expected_seq else "EVENT_CHAIN_MISMATCH"
            issues.append(_issue(run_id, str(payload.get("stage") or "_unknown"), "event", ordinal, severity="HIGH", opened=seq,
                                 error_code=code, error_message=f"event {seq} failed direct chain validation",
                                 evidence_hash=row.get("hash"), solution="Recover controller from immutable event source",
                                 learning_evidence="Event hashes attest order and payload integrity"))
            valid = False
        stage = payload.get("stage")
        if payload.get("kind") == "STAGE_STARTED" and stage not in known_stages:
            ordinal += 1
            issues.append(_issue(run_id, str(stage or "_unknown"), "event", ordinal, severity="HIGH", opened=seq,
                                 error_code="UNKNOWN_STAGE", error_message="stage is absent from local policy",
                                 evidence_hash=row.get("hash"), solution="Bind the run to its matching policy bundle",
                                 learning_evidence="A stage event cannot be interpreted without its policy"))
        if stage and payload.get("kind") == "STAGE_FAILED":
            failures[stage] = {"seq": seq, "hash": row.get("hash"), "error": payload.get("error")}
        elif stage and payload.get("kind") == "STAGE_COMPLETED" and stage in failures:
            failed = failures.pop(stage)
            ordinal += 1
            issues.append(_issue(run_id, stage, "stage-failure", ordinal, severity="LOW", status="RESOLVED",
                                 opened=failed["seq"], resolved=seq, error_code="RESOLVED_BY_COMPLETION",
                                 error_message=str(failed.get("error") or "stage later completed"), evidence_hash=row.get("hash"),
                                 solution="Stage was rerun and completed with a receipt",
                                 learning_evidence="Resolution is evidenced by a later completion event"))
        rows.append((run_id, seq, stage, payload.get("kind", "UNKNOWN"), payload.get("at"), row.get("previous", ""),
                     row.get("hash", ""), json.dumps(_masked_event_payload(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")), int(chain_valid)))
        previous = row.get("hash", previous)
        expected_seq = seq + 1
    for stage, failed in failures.items():
        ordinal += 1
        issues.append(_issue(run_id, stage, "stage-failure", ordinal, severity="HIGH",
                             opened=failed["seq"], error_code="STAGE_FAILURE_UNRESOLVED",
                             error_message="No later completion event resolves this failure",
                             evidence_hash=failed["hash"], solution="Review and recover the failed stage"))
    return rows, valid


def _stage_outputs(run_root: Path, run_id: str, stage: dict[str, Any], stage_index: int, issues: list[dict[str, Any]], artifact_rows: list[tuple]):
    stage_id = str(stage.get("id"))
    state = str(stage.get("state") or "UNKNOWN")
    receipt_text = stage.get("receipt")
    attempt = stage.get("attempt", 0)
    limitations = []
    receipt: dict[str, Any] | None = None
    completion_hash = None
    receipt_artifact_hash = None
    input_signature = None
    provenance_ok = True
    ordinal = 0
    if receipt_text is not None:
        try:
            receipt = _parse_json(receipt_text, f"receipt:{stage_id}")
            completion_hash = hashlib.sha256(str(receipt_text).encode()).hexdigest()
            artifacts = receipt.get("artifacts") if isinstance(receipt.get("artifacts"), list) else []
            receipt_artifact_hash = digest(artifacts)
            input_signature = json.dumps(receipt.get("parents", []), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            limitations = receipt.get("limitations", [])
            seen: set[str] = set()
            for item in artifacts:
                ordinal += 1
                if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                    issues.append(_issue(run_id, stage_id, "artifact", ordinal, severity="MED", error_code="ARTIFACT_ENTRY_INVALID",
                                         error_message="receipt artifact must contain a relative path", solution="Emit a valid stage receipt",
                                         learning_evidence="Artifact paths are the evidence boundary"))
                    provenance_ok = False
                    continue
                rel = item["path"]
                expected = item.get("sha256")
                if rel in seen:
                    issues.append(_issue(run_id, stage_id, "artifact", ordinal, severity="MED", error_code="ARTIFACT_DUPLICATE",
                                         error_message=f"duplicate artifact path: {rel}", solution="Deduplicate the receipt artifact list",
                                         learning_evidence="One primary key row is retained per stage/path"))
                    provenance_ok = False
                    continue
                seen.add(rel)
                observed = None
                size = None
                validation = "MISSING"
                try:
                    absolute = _safe_relative_path(run_root, rel)
                except DiagnosticsError:
                    validation = "OUTSIDE_ROOT"
                    issues.append(_issue(run_id, stage_id, "artifact", ordinal, severity="HIGH", error_code="ARTIFACT_PATH_OUTSIDE_ROOT",
                                         error_message=f"artifact path escapes run root: {rel}", solution="Use a relative path inside the run",
                                         learning_evidence="Source artifacts cannot be read outside the controller run"))
                    provenance_ok = False
                else:
                    if not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
                        validation = "INVALID_EXPECTED_HASH"
                        issues.append(_issue(run_id, stage_id, "artifact", ordinal, severity="HIGH", error_code="ARTIFACT_HASH_INVALID",
                                             error_message=f"invalid expected SHA-256 for {rel}", solution="Emit a lowercase SHA-256 digest",
                                             learning_evidence="Artifact identity requires a concrete digest"))
                        provenance_ok = False
                    elif absolute.is_file():
                        observed = _file_hash(absolute)
                        size = absolute.stat().st_size
                        validation = "OK" if observed == expected else "HASH_MISMATCH"
                        if validation != "OK":
                            issues.append(_issue(run_id, stage_id, "artifact", ordinal, severity="HIGH", error_code="ARTIFACT_HASH_MISMATCH",
                                                 error_message=f"artifact hash mismatch: {rel}", solution="Reproduce or restore the receipt-bound artifact",
                                                 learning_evidence="Artifact bytes are validated directly during export"))
                            provenance_ok = False
                    else:
                        issues.append(_issue(run_id, stage_id, "artifact", ordinal, severity="MED", error_code="ARTIFACT_MISSING",
                                             error_message=f"artifact missing: {rel}", solution="Restore the receipt-bound artifact",
                                             learning_evidence="A completion receipt without its artifact is not reproducible"))
                        provenance_ok = False
                artifact_rows.append((run_id, stage_id, rel, expected, observed, size, validation))
            if state in SUCCESS_STATES and not artifacts:
                issues.append(_issue(run_id, stage_id, "artifact", 0, severity="HIGH", error_code="PASS_WITHOUT_ARTIFACTS",
                                     error_message=f"{state} stage has no receipt artifacts", solution="Re-run with at least one bound artifact",
                                     learning_evidence="Completed stages must expose evidence"))
                provenance_ok = False
        except DiagnosticsError as exc:
            issues.append(_issue(run_id, stage_id, "receipt", 0, severity="HIGH", error_code=str(exc),
                                 error_message="stage receipt is not a JSON object", solution="Emit a valid stage receipt",
                                 learning_evidence="Receipt JSON is required for completed stages"))
            provenance_ok = False
    elif state in SUCCESS_STATES:
        issues.append(_issue(run_id, stage_id, "receipt", 0, severity="HIGH", error_code="PASS_WITHOUT_RECEIPT",
                             error_message=f"{state} stage has no receipt", solution="Re-run stage to generate a receipt",
                             learning_evidence="State alone does not prove stage output"))
        provenance_ok = False
    if not isinstance(limitations, list):
        limitations = []
    goal = BY_ID[stage_id].output if stage_id in BY_ID else "UNKNOWN"
    return (run_id, stage_id, stage_index, goal, stage.get("actor"), state, int(attempt or 0), len(limitations),
            completion_hash, receipt_artifact_hash, input_signature, int(provenance_ok))


def _append_metric(run_id: str, scope: str, row: dict[str, Any], metric_rows: list[tuple], issues: list[dict[str, Any]], seen: set[tuple], ordinal: list[int]) -> None:
    release_id, entity_id, metric_name, unit = row.get("release_id"), row.get("entity_id"), row.get("metric_name"), row.get("unit")
    if not all(isinstance(value, str) and value for value in (release_id, entity_id, metric_name, unit)):
        ordinal[0] += 1
        issues.append(_issue(run_id, "signal", "metric", ordinal[0], severity="MED", error_code="METRIC_ROW_INVALID",
                             error_message="metric row lacks release, entity, name, or unit", solution="Repair metric schema before import",
                             learning_evidence="Optional metrics remain excluded when identity is incomplete"))
        return
    key = (release_id, scope, entity_id, metric_name)
    if key in seen:
        ordinal[0] += 1
        issues.append(_issue(run_id, "signal", "metric", ordinal[0], severity="MED", error_code="METRIC_DUPLICATE",
                             error_message=f"duplicate metric: {metric_name}", solution="Deduplicate source metric rows",
                             learning_evidence="Diagnostic metric keys are release/scope/entity/name"))
        return
    seen.add(key)
    value, denominator, observed_n = row.get("value"), row.get("denominator"), row.get("observed_n")
    problems = _metric_issues(metric_name, unit, value, denominator, observed_n)
    metric_rows.append((run_id, release_id, scope, entity_id, metric_name, unit, value, denominator, observed_n,
                        row.get("formula_version"), int(value is None), "PASS" if not problems else "INVALID",
                        json.dumps(problems, sort_keys=True) if problems else None))
    if problems:
        ordinal[0] += 1
        issues.append(_issue(run_id, "signal", "metric", ordinal[0], severity="MED", error_code=problems[0],
                             error_message=f"metric {metric_name} failed validation", solution="Review the source metric denominator and unit",
                             learning_evidence="Null values remain null; invalid non-null values remain visible as INVALID"))


def _import_signal_metrics(signal_path: Path, run_id: str, metric_rows: list[tuple], issues: list[dict[str, Any]]) -> str | None:
    if not signal_path.is_file():
        issues.append(_issue(run_id, "signal", "schema", 0, severity="HIGH", error_code="SIGNAL_DB_MISSING",
                             error_message="optional signal database path does not exist", solution="Supply a readable signal export",
                             learning_evidence="Diagnostics never invent metrics when optional evidence is absent"))
        return
    connection = _readonly(signal_path)
    connection.row_factory = sqlite3.Row
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"releases", "reel_metric_values"}.issubset(tables):
            issues.append(_issue(run_id, "signal", "schema", 0, severity="HIGH", error_code="SIGNAL_SCHEMA_MISSING",
                                 error_message="releases and reel_metric_values are required for metric import",
                                 solution="Use a compatible signal SQLite export", learning_evidence="Signal evidence has a versioned schema"))
            return
        releases = {row["release_id"] for row in connection.execute("SELECT release_id FROM releases")}
        seen: set[tuple] = set()
        ordinal = [0]
        for raw in connection.execute("SELECT release_id,reel_id,metric_name,value,observed_n,denominator,unit,formula_version FROM reel_metric_values"):
            row = dict(raw)
            row["entity_id"] = row.pop("reel_id")
            if row.get("release_id") not in releases:
                ordinal[0] += 1
                issues.append(_issue(run_id, "signal", "metric", ordinal[0], severity="HIGH", error_code="METRIC_RELEASE_UNKNOWN",
                                     error_message=f"metric references unknown release: {row.get('release_id')}", solution="Bind metrics to a release row",
                                     learning_evidence="Release identity is part of metric provenance"))
                continue
            _append_metric(run_id, "reel", row, metric_rows, issues, seen, ordinal)
        if "account_metric_values" in tables:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(account_metric_values)")}
            required_columns = {"release_id", "account_username", "metric_name", "value", "unit"}
            if required_columns.issubset(columns):
                optional = {name: name if name in columns else f"NULL AS {name}"
                            for name in ("observed_n", "denominator", "formula_version")}
                select = ("release_id,account_username,metric_name,value,{observed_n},{denominator},unit,{formula_version}"
                          .format(**optional))
                for raw in connection.execute(f"SELECT {select} FROM account_metric_values"):
                    row = dict(raw)
                    row["entity_id"] = row.pop("account_username")
                    _append_metric(run_id, "account", row, metric_rows, issues, seen, ordinal)
        return _logical_hash(connection)
    finally:
        connection.close()


def export_diagnostics(state_db: str | Path, output_db: str | Path, signal_db: str | Path | None = None, force: bool = False) -> dict[str, Any]:
    state_path = Path(state_db).resolve()
    output_path = Path(output_db).resolve()
    signal_path = Path(signal_db).resolve() if signal_db else None
    if _same_file(output_path, state_path) or _same_file(output_path, signal_path):
        raise DiagnosticsError("OUTPUT_MUST_BE_SEPARATE_FROM_SOURCE_DATABASES")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    connection, run, config, stages, events = _read_controller_state(state_path)
    try:
        run_id, config_hash, policy_hash = str(run["id"]), str(run["hash"]), str(run["policy_hash"])
        controller_hash = _logical_hash(connection)
        signal_hash = None
        issues: list[dict[str, Any]] = []
        if digest(config) != config_hash:
            issues.append(_issue(run_id, "_run", "config", 0, severity="HIGH", error_code="CONFIG_HASH_MISMATCH",
                                 error_message="run config hash does not match its stored digest", solution="Recover the immutable run bundle",
                                 learning_evidence="Configuration is bound by hash and is not copied into diagnostics"))
        event_rows, events_ok = _validate_events(run_id, events, set(BY_ID), issues)
        stage_order = {stage_id: index for index, stage_id in enumerate(BY_ID)}
        stage_rows, artifact_rows = [], []
        for stage in stages:
            stage_id = str(stage.get("id"))
            if stage_id not in stage_order:
                issues.append(_issue(run_id, stage_id, "policy", 0, severity="HIGH", error_code="UNKNOWN_STAGE",
                                     error_message="controller stage is absent from local policy", solution="Use the policy bundle that created the run",
                                     learning_evidence="Unknown stages are preserved without inventing a goal"))
                index = -1
            else:
                index = stage_order[stage_id]
            stage_rows.append(_stage_outputs(state_path.parent, run_id, stage, index, issues, artifact_rows))
        metric_rows: list[tuple] = []
        if signal_path is not None:
            signal_hash = _import_signal_metrics(signal_path, run_id, metric_rows, issues)

        source_signature = digest({"controller_logical_sql": controller_hash,
                                   "signal_logical_sql": signal_hash,
                                   "artifacts": artifact_rows,
                                   "schema": EXPORT_SCHEMA_VERSION})
        idempotent = False
        if output_path.is_file() and not force:
            try:
                existing = _readonly(output_path)
                try:
                    previous = existing.execute("SELECT source_signature FROM diagnostic_exports WHERE run_id=? AND schema_version=?",
                                                (run_id, EXPORT_SCHEMA_VERSION)).fetchone()
                    idempotent = bool(previous and previous[0] == source_signature)
                finally:
                    existing.close()
            except sqlite3.Error:
                pass
        # Always regenerate after checking sources and artifacts. A cached
        # signature must never bypass artifact validation or hide output damage.
        output = sqlite3.connect(output_path)
        try:
            _ensure_schema(output)
            with output:
                for table in ("diagnostic_exports", "diagnostic_events", "diagnostic_stages", "diagnostic_stage_artifacts", "diagnostic_metrics", "diagnostic_issues"):
                    output.execute(f"DELETE FROM {table} WHERE run_id=?", (run_id,))
                output.execute("INSERT INTO diagnostic_exports VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                               (run_id, EXPORT_SCHEMA_VERSION, str(state_path), str(signal_path) if signal_path else None,
                                config_hash, policy_hash, controller_hash, signal_hash,
                                source_signature, int(events_ok), len(stages)))
                output.executemany("INSERT INTO diagnostic_events VALUES(?,?,?,?,?,?,?,?,?)", event_rows)
                output.executemany("INSERT INTO diagnostic_stages VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", stage_rows)
                output.executemany("INSERT INTO diagnostic_stage_artifacts VALUES(?,?,?,?,?,?,?)", artifact_rows)
                output.executemany("INSERT INTO diagnostic_metrics VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", metric_rows)
                issue_columns = ("run_id", "issue_id", "stage_id", "kind", "severity", "status", "opened_event_seq", "resolved_event_seq", "error_code", "error_message", "evidence_hash", "solution", "learning_evidence")
                output.executemany("INSERT INTO diagnostic_issues VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", [tuple(item[key] for key in issue_columns) for item in issues])
        finally:
            output.close()
        return {"run_id": run_id, "export_schema": EXPORT_SCHEMA_VERSION, "idempotent": idempotent, "output_db": str(output_path),
                "stages": len(stages), "stage_artifacts": len(artifact_rows), "metrics": len(metric_rows), "issues": len(issues),
                "state_events_ok": events_ok, "source_signature": source_signature}
    finally:
        connection.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export controller diagnostics into a separate SQLite")
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--signal", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(export_diagnostics(args.state, args.output, args.signal, args.force), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
