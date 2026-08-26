"""Secret-safe, quota-aware YouTube Data API v3 public-read adapter."""

from __future__ import annotations

import hashlib
import json
import random
import threading
import time
import fcntl
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from m2_engine.engine import canonical_hash, canonical_json


API_BASE = "https://www.googleapis.com/youtube/v3"
ADAPTER_VERSION = "youtube-data-api-v3-public@1.0.0"
MAX_STRIKES = 5
_LOCKS_GUARD = threading.Lock()
_PROCESS_LOCKS: dict[str, threading.Lock] = {}


class YouTubeAPIError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool, global_stop: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.global_stop = global_stop


@dataclass(frozen=True)
class APIResult:
    operation: str
    fingerprint: str
    payload: dict[str, Any]
    raw_sha256: str
    raw_uri: str
    captured_at: str
    refresh_or_delete_by: str
    resumed: bool


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_line(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def _append_jsonl(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(_json_line(value))
        stream.flush()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    records.append(value)
    return records


def _process_lock(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _LOCKS_GUARD:
        return _PROCESS_LOCKS.setdefault(key, threading.Lock())


@contextmanager
def exclusive_file_lock(path: Path):
    """Serialize a critical section across threads and processes."""

    path.parent.mkdir(parents=True, exist_ok=True)
    thread_lock = _process_lock(path)
    with thread_lock:
        with path.open("a+", encoding="utf-8") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def request_fingerprint(operation: str, params: Mapping[str, Any]) -> str:
    safe_params = {key: value for key, value in params.items() if key.lower() not in {"key", "access_token"}}
    return canonical_hash({"operation": operation, "params": safe_params})


def classify_http_error(status: int, reasons: set[str]) -> tuple[str, bool, bool]:
    if status in {401} or reasons & {"authError", "keyInvalid", "ipRefererBlocked"}:
        return "AUTH_ERROR", False, True
    if status == 403 and reasons & {"quotaExceeded", "dailyLimitExceeded"}:
        return "QUOTA_EXHAUSTED", False, True
    if reasons & {"rateLimitExceeded", "userRateLimitExceeded"}:
        return "RATE_LIMITED", True, False
    if status == 403:
        return "FORBIDDEN", False, False
    if status == 429:
        return "RATE_LIMITED", True, False
    if status >= 500:
        return "UPSTREAM_SERVER_ERROR", True, False
    if status == 404:
        return "NOT_FOUND", False, False
    if status == 400:
        return "INVALID_REQUEST", False, False
    return "HTTP_ERROR", False, False


class QuotaLedger:
    """Durable attempt ledger; an attempted request counts even when it fails."""

    def __init__(self, path: Path, *, daily_unit_budget: int, daily_search_call_budget: int) -> None:
        self.path = path
        self.daily_unit_budget = daily_unit_budget
        self.daily_search_call_budget = daily_search_call_budget

    def usage(self, day: str | None = None) -> dict[str, int]:
        target_day = day or _utc_now().date().isoformat()
        attempts = [row for row in _read_jsonl(self.path) if row.get("event") == "request_attempt" and row.get("utc_day") == target_day]
        return {
            "units": sum(int(row.get("estimated_units", 0)) for row in attempts),
            "search_calls": sum(1 for row in attempts if row.get("operation") == "search.list"),
            "requests": len(attempts),
        }

    def reserve(self, *, operation: str, fingerprint: str, estimated_units: int) -> dict[str, int]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            stream.seek(0)
            rows = [json.loads(line) for line in stream if line.strip()]
            day = _utc_now().date().isoformat()
            attempts = [row for row in rows if row.get("event") == "request_attempt" and row.get("utc_day") == day]
            usage = {
                "units": sum(int(row.get("estimated_units", 0)) for row in attempts),
                "search_calls": sum(1 for row in attempts if row.get("operation") == "search.list"),
                "requests": len(attempts),
            }
            if usage["units"] + estimated_units > self.daily_unit_budget:
                raise YouTubeAPIError("LOCAL_QUOTA_BUDGET", "local daily API unit budget reached", retryable=False, global_stop=True)
            if operation == "search.list" and usage["search_calls"] + 1 > self.daily_search_call_budget:
                raise YouTubeAPIError("LOCAL_SEARCH_BUDGET", "local daily search-call budget reached", retryable=False, global_stop=True)
            stream.seek(0, 2)
            stream.write(_json_line({
                "schema": "youtube.quota-event.v1",
                "event": "request_attempt",
                "utc_day": day,
                "attempted_at": _utc_now().isoformat(),
                "operation": operation,
                "request_fingerprint": fingerprint,
                "estimated_units": estimated_units,
            }))
            stream.flush()
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        return self.usage()


class PersistentStrikeLedger:
    """Append-only five-strike state keyed by request fingerprint."""

    def __init__(self, path: Path, maximum: int = MAX_STRIKES) -> None:
        self.path = path
        self.maximum = maximum

    def terminal_action(self, failure_key: str) -> str | None:
        actions = [str(row.get("action")) for row in _read_jsonl(self.path) if row.get("failure_key") == failure_key]
        return actions[-1] if actions and actions[-1] in {"block", "quarantine", "global_stop"} else None

    def record(self, *, failure_key: str, error_code: str, retryable: bool, global_stop: bool) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            stream.seek(0)
            prior_rows = [json.loads(line) for line in stream if line.strip()]
            prior = max([int(row.get("strike", 0)) for row in prior_rows if row.get("failure_key") == failure_key] or [0])
            strike = min(self.maximum, prior + 1)
            action = "global_stop" if global_stop else "block" if not retryable else "quarantine" if strike >= self.maximum else "retry_record_only"
            event = {
                "schema": "youtube.five-strike-event.v1",
                "failure_key": failure_key,
                "error_code": error_code,
                "strike": strike,
                "action": action,
                "observed_at": _utc_now().isoformat(),
            }
            stream.seek(0, 2)
            stream.write(_json_line(event))
            stream.flush()
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        return event


class YouTubeDataAPIClient:
    def __init__(
        self,
        *,
        api_key: str,
        run_dir: Path,
        quota: QuotaLedger,
        timeout_seconds: float = 30.0,
        max_attempts: int = 5,
        min_interval_seconds: float = 0.25,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self._api_key = api_key
        self.run_dir = run_dir
        self.quota = quota
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.min_interval_seconds = min_interval_seconds
        self.sleeper = sleeper
        self._last_request_at = 0.0
        self.request_ledger = run_dir / "ledgers" / "youtube-api-requests.jsonl"
        self.failure_ledger = run_dir / "ledgers" / "youtube-api-failures.jsonl"
        self.collector_lock = run_dir / "ledgers" / "youtube-collector.lock"
        if max_attempts != MAX_STRIKES:
            raise ValueError("YouTube API client requires exactly five attempts")
        self.strike_ledger = PersistentStrikeLedger(run_dir / "ledgers" / "youtube-api-strikes.jsonl")

    def _successful_receipt(self, fingerprint: str) -> dict[str, Any] | None:
        for row in reversed(_read_jsonl(self.request_ledger)):
            if row.get("request_fingerprint") == fingerprint and row.get("status") == "success":
                raw_uri = row.get("raw_uri")
                if isinstance(raw_uri, str) and (self.run_dir / raw_uri).exists():
                    return row
        return None

    def _resume(self, operation: str, fingerprint: str, receipt: Mapping[str, Any]) -> APIResult:
        raw_uri = str(receipt["raw_uri"])
        raw_bytes = (self.run_dir / raw_uri).read_bytes()
        actual_hash = _sha256_bytes(raw_bytes)
        if actual_hash != str(receipt["raw_sha256"]):
            raise YouTubeAPIError("RAW_HASH_MISMATCH", "resumed raw artifact hash does not match receipt", retryable=False, global_stop=True)
        payload = json.loads(raw_bytes)
        return APIResult(
            operation=operation,
            fingerprint=fingerprint,
            payload=payload,
            raw_sha256=str(receipt["raw_sha256"]),
            raw_uri=raw_uri,
            captured_at=str(receipt["captured_at"]),
            refresh_or_delete_by=str(receipt["refresh_or_delete_by"]),
            resumed=True,
        )

    def get(self, resource: str, operation: str, params: Mapping[str, Any], *, estimated_units: int = 1) -> APIResult:
        safe_params = {key: value for key, value in params.items() if key.lower() not in {"key", "access_token"}}
        fingerprint = request_fingerprint(operation, safe_params)
        with exclusive_file_lock(self.collector_lock):
            prior = self._successful_receipt(fingerprint)
            if prior:
                return self._resume(operation, fingerprint, prior)
            terminal_action = self.strike_ledger.terminal_action(fingerprint)
            if terminal_action:
                raise YouTubeAPIError("TARGET_BLOCKED", f"request fingerprint is terminal: {terminal_action}", retryable=False)

            last_error: YouTubeAPIError | None = None
            for attempt in range(1, self.max_attempts + 1):
                elapsed = time.monotonic() - self._last_request_at
                if elapsed < self.min_interval_seconds:
                    self.sleeper(self.min_interval_seconds - elapsed)
                self.quota.reserve(operation=operation, fingerprint=fingerprint, estimated_units=estimated_units)
                query = urlencode({**safe_params, "key": self._api_key})
                request = Request(f"{API_BASE}/{resource}?{query}", headers={"Accept": "application/json", "User-Agent": "ArchFlow-North-Hux/1.0"})
                self._last_request_at = time.monotonic()
                try:
                    with urlopen(request, timeout=self.timeout_seconds) as response:
                        raw_bytes = response.read()
                    payload = json.loads(raw_bytes)
                    if not isinstance(payload, dict):
                        raise YouTubeAPIError("MALFORMED_API_JSON", "API response is not an object", retryable=False)
                    captured = _utc_now()
                    raw_sha = _sha256_bytes(raw_bytes)
                    raw_uri = Path("raw") / "youtube-data-api" / operation.replace(".", "_") / f"{raw_sha}.json"
                    raw_path = self.run_dir / raw_uri
                    raw_path.parent.mkdir(parents=True, exist_ok=True)
                    if raw_path.exists() and raw_path.read_bytes() != raw_bytes:
                        raise YouTubeAPIError("RAW_HASH_CONFLICT", "existing raw artifact conflicts with response hash", retryable=False, global_stop=True)
                    if not raw_path.exists():
                        raw_path.write_bytes(raw_bytes)
                    result = APIResult(
                        operation=operation,
                        fingerprint=fingerprint,
                        payload=payload,
                        raw_sha256=raw_sha,
                        raw_uri=raw_uri.as_posix(),
                        captured_at=captured.isoformat(),
                        refresh_or_delete_by=(captured + timedelta(days=30)).isoformat(),
                        resumed=False,
                    )
                    _append_jsonl(self.request_ledger, {
                        "schema": "youtube.api-request-receipt.v1",
                        "adapter_version": ADAPTER_VERSION,
                        "operation": operation,
                        "request_fingerprint": fingerprint,
                        "safe_params": safe_params,
                        "status": "success",
                        "attempt": attempt,
                        "captured_at": result.captured_at,
                        "refresh_or_delete_by": result.refresh_or_delete_by,
                        "raw_sha256": raw_sha,
                        "raw_uri": result.raw_uri,
                    })
                    return result
                except HTTPError as exc:
                    reasons: set[str] = set()
                    http_status: int | None = exc.code
                    try:
                        error_payload = json.loads(exc.read())
                        for item in error_payload.get("error", {}).get("errors", []):
                            if isinstance(item, dict) and isinstance(item.get("reason"), str):
                                reasons.add(item["reason"])
                    except (json.JSONDecodeError, UnicodeError, AttributeError):
                        reasons = set()
                    code, retryable, global_stop = classify_http_error(exc.code, reasons)
                    last_error = YouTubeAPIError(code, f"YouTube API request failed with HTTP {exc.code}", retryable=retryable, global_stop=global_stop)
                    retry_after = exc.headers.get("Retry-After") if exc.headers else None
                except (URLError, TimeoutError) as exc:
                    last_error = YouTubeAPIError("NETWORK_ERROR", f"YouTube API request failed: {type(exc).__name__}", retryable=True)
                    retry_after = None
                    http_status = None
                    reasons = set()
                except (json.JSONDecodeError, UnicodeError) as exc:
                    last_error = YouTubeAPIError("MALFORMED_API_JSON", f"YouTube API response parsing failed: {type(exc).__name__}", retryable=False)
                    retry_after = None
                    http_status = None
                    reasons = set()
                except YouTubeAPIError as exc:
                    last_error = exc
                    retry_after = None
                    http_status = None
                    reasons = set()

                assert last_error is not None
                strike_event = self.strike_ledger.record(
                    failure_key=fingerprint,
                    error_code=last_error.code,
                    retryable=last_error.retryable,
                    global_stop=last_error.global_stop,
                )
                _append_jsonl(self.failure_ledger, {
                    "schema": "youtube.api-failure.v1",
                    "operation": operation,
                    "request_fingerprint": fingerprint,
                    "attempt": attempt,
                    "error_code": last_error.code,
                    "retryable": last_error.retryable,
                    "global_stop": last_error.global_stop,
                    "http_status": http_status,
                    "api_reasons": sorted(reasons),
                    "strike": strike_event["strike"],
                    "action": strike_event["action"],
                    "observed_at": _utc_now().isoformat(),
                })
                if strike_event["action"] != "retry_record_only":
                    raise last_error
                try:
                    if retry_after:
                        try:
                            wait_seconds = max(0.0, float(retry_after))
                        except ValueError:
                            retry_time = parsedate_to_datetime(retry_after)
                            wait_seconds = max(0.0, (retry_time - _utc_now()).total_seconds())
                    else:
                        wait_seconds = min(60.0, (2 ** (attempt - 1)) + random.random())
                except (ValueError, TypeError, OverflowError):
                    wait_seconds = min(60.0, (2 ** (attempt - 1)) + random.random())
                self.sleeper(wait_seconds)
            raise last_error or YouTubeAPIError("UNKNOWN", "request failed", retryable=False)
