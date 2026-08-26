"""Bounded retry and quarantine policy for mechanical collection and QA jobs.

This module is deliberately provider-neutral. It does not perform network calls,
sleep, login, or retry work itself; it returns a deterministic decision that a
caller can record in collection_job and failure receipts.
"""

from dataclasses import dataclass
from typing import Dict, FrozenSet


RETRYABLE: FrozenSet[str] = frozenset({
    "timeout", "rate_limit", "transient_network", "provider_5xx", "temporary_file_lock"
})
NON_RETRYABLE: FrozenSet[str] = frozenset({
    "auth", "rights", "terms", "robots", "not_found", "schema_invalid",
    "credential_missing", "policy_block"
})
BACKOFF_SECONDS = (2, 5, 15, 45, 120)
MAX_STRIKES = 5


@dataclass(frozen=True)
class StrikeDecision:
    failure_key: str
    failure_code: str
    strike: int
    action: str
    backoff_seconds: int
    reason: str


class FiveStrikeLedger:
    """Track strikes by record/stage/failure class without blind batch retries."""

    def __init__(self) -> None:
        self._strikes: Dict[str, int] = {}

    def decide(self, failure_key: str, failure_code: str) -> StrikeDecision:
        prior = self._strikes.get(failure_key, 0)
        strike = min(prior + 1, MAX_STRIKES)
        self._strikes[failure_key] = strike

        if failure_code in NON_RETRYABLE:
            return StrikeDecision(
                failure_key, failure_code, strike, "block", 0,
                "non-retryable policy, rights, identity, schema, or credential failure"
            )
        if failure_code not in RETRYABLE:
            return StrikeDecision(
                failure_key, failure_code, strike, "quarantine", 0,
                "unknown failure class requires review before retry"
            )
        if strike >= MAX_STRIKES:
            return StrikeDecision(
                failure_key, failure_code, strike, "quarantine", BACKOFF_SECONDS[-1],
                "fifth strike reached; quarantine the record and require review"
            )
        return StrikeDecision(
            failure_key, failure_code, strike, "retry_record_only", BACKOFF_SECONDS[strike - 1],
            "retry only this record after bounded backoff"
        )

    def strike_count(self, failure_key: str) -> int:
        return self._strikes.get(failure_key, 0)

    def snapshot(self) -> Dict[str, int]:
        return dict(self._strikes)
