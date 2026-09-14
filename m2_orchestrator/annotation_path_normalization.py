"""Strict, derived-only normalization for legacy transcript annotation paths."""

from __future__ import annotations

from copy import deepcopy
from pathlib import PurePosixPath
from typing import Any


EXPECTED_OLD_PREFIX = "runs/20260906-media-acquisition-v1/corpus-local-r1/"
EXPECTED_RELATIVE_PREFIX = "transcripts/"


class AnnotationPathError(ValueError):
    """Raised when an annotation path is not the exact approved legacy form."""


def normalize_transcript_path(value: Any) -> str:
    """Strip only the exact old repository prefix and return corpus-relative path.

    The function is lexical by design. It does not resolve, read, or hash the
    referenced file and rejects ambiguous path forms before any filesystem use.
    """
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise AnnotationPathError("TRANSCRIPT_PATH_INVALID")
    if value.startswith("/") or PurePosixPath(value).is_absolute():
        raise AnnotationPathError("TRANSCRIPT_PATH_INVALID")
    if not value.startswith(EXPECTED_OLD_PREFIX):
        raise AnnotationPathError("TRANSCRIPT_PATH_PREFIX_MISMATCH")
    suffix = value[len(EXPECTED_OLD_PREFIX) :]
    if not suffix.startswith(EXPECTED_RELATIVE_PREFIX):
        raise AnnotationPathError("TRANSCRIPT_PATH_ROOT_RELATIVE_REQUIRED")
    parts = suffix.split("/")
    if len(parts) < 3 or any(part in {"", ".", ".."} for part in parts):
        raise AnnotationPathError("TRANSCRIPT_PATH_INVALID")
    if PurePosixPath(suffix).is_absolute() or ".." in PurePosixPath(suffix).parts:
        raise AnnotationPathError("TRANSCRIPT_PATH_INVALID")
    return suffix


def normalize_annotation(row: Any) -> dict[str, Any]:
    """Copy an annotation row, changing only ``input.transcript_path``."""
    if not isinstance(row, dict):
        raise AnnotationPathError("ANNOTATION_ROW_INVALID")
    source_input = row.get("input")
    if not isinstance(source_input, dict) or "transcript_path" not in source_input:
        raise AnnotationPathError("TRANSCRIPT_PATH_MISSING")
    normalized = deepcopy(row)
    normalized["input"]["transcript_path"] = normalize_transcript_path(source_input["transcript_path"])
    return normalized
