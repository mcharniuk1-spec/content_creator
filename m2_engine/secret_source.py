"""Runtime-only secret loading with zero-value logging.

This module deliberately returns only a requested value to the in-process
caller.  Its inventory surface reports service presence and counts, never
secret text, prefixes, lengths, hashes, or source lines.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


class SecretSourceError(RuntimeError):
    """Raised when a required runtime secret cannot be resolved safely."""


@dataclass(frozen=True)
class SecretCandidate:
    service: str
    value: str
    source_kind: str


_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "youtube": (
        re.compile(r"(?<![A-Za-z0-9_-])(AIza[0-9A-Za-z_-]{30,50})(?![A-Za-z0-9_-])"),
    ),
    "notion": (
        re.compile(r"(?<![A-Za-z0-9_-])((?:secret_|ntn_)[0-9A-Za-z_-]{20,})(?![A-Za-z0-9_-])"),
    ),
}

_LABEL_ALIASES: dict[str, tuple[str, ...]] = {
    "youtube": ("youtube_api_key", "youtube data api", "youtube key", "google_api_key", "google api key"),
    "notion": ("notion_token", "notion secret", "notion api key", "notion integration token"),
}


def _clean_candidate(value: str) -> str:
    return value.strip().strip("`\"'[](){}<>,;")


def _labelled_candidates(text: str, service: str) -> list[SecretCandidate]:
    aliases = _LABEL_ALIASES.get(service, ())
    found: list[SecretCandidate] = []
    for raw_line in text.splitlines():
        lower = raw_line.lower()
        if not any(alias in lower for alias in aliases):
            continue
        for separator in ("=", ":"):
            if separator not in raw_line:
                continue
            suffix = raw_line.split(separator, 1)[1]
            matched = False
            for pattern in _PATTERNS.get(service, ()):
                for match in pattern.finditer(suffix):
                    found.append(SecretCandidate(service, match.group(1), "label"))
                    matched = True
            if matched:
                break
    return found


def _pattern_candidates(text: str, service: str) -> list[SecretCandidate]:
    found: list[SecretCandidate] = []
    for pattern in _PATTERNS.get(service, ()):
        found.extend(SecretCandidate(service, match.group(1), "pattern") for match in pattern.finditer(text))
    return found


def _deduplicate(candidates: list[SecretCandidate]) -> list[SecretCandidate]:
    unique: dict[str, SecretCandidate] = {}
    for candidate in candidates:
        unique.setdefault(candidate.value, candidate)
    return list(unique.values())


def inventory(secret_file: Path) -> dict[str, object]:
    """Return a non-sensitive service inventory for operator checks."""

    text = secret_file.read_text(encoding="utf-8", errors="strict")
    services: dict[str, dict[str, object]] = {}
    for service in sorted(_PATTERNS):
        candidates = _deduplicate(_labelled_candidates(text, service) + _pattern_candidates(text, service))
        services[service] = {"present": bool(candidates), "candidate_count": len(candidates)}
    return {"source_readable": True, "services": services}


def load_secret(service: str, *, secret_file: Path | None = None) -> str:
    """Resolve one service secret from environment first, then a local file."""

    normalized = service.lower().strip()
    env_names = {
        "youtube": ("YOUTUBE_API_KEY", "GOOGLE_API_KEY"),
        "notion": ("NOTION_TOKEN", "NOTION_API_KEY"),
    }.get(normalized)
    if not env_names:
        raise SecretSourceError(f"unsupported secret service: {normalized}")
    env_values = _deduplicate(
        [SecretCandidate(normalized, os.environ[name], "environment") for name in env_names if os.environ.get(name)]
    )
    if len(env_values) == 1:
        return env_values[0].value
    if len(env_values) > 1:
        raise SecretSourceError(f"multiple environment candidates found for {normalized}")
    if secret_file is None:
        raise SecretSourceError(f"no runtime secret source supplied for {normalized}")
    text = secret_file.read_text(encoding="utf-8", errors="strict")
    candidates = _deduplicate(_labelled_candidates(text, normalized) + _pattern_candidates(text, normalized))
    if not candidates:
        raise SecretSourceError(f"no recognizable {normalized} credential is present")
    if len(candidates) > 1:
        raise SecretSourceError(f"multiple {normalized} credential candidates are present")
    return candidates[0].value
