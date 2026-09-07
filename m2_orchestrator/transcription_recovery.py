"""Memory-bounded recovery helpers for oversized local ASR attempts.

This route keeps the existing full-corpus transcription worker untouched.  It
plans adjacent core intervals of at most 30 seconds, adds at most one second
of context on each side, and accepts an injected one-chunk runner.  The runner
is deliberately required for execution: this module does not launch FFmpeg,
Whisper, the parent worker, or a network client by itself.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from .process_budget import ProcessBudgetError


CORE_MAX_MS = 30_000
PADDING_MAX_MS = 1_000
CPU_THREADS = 2
NUM_WORKERS = 1
COMPUTE_TYPE = "int8"
DEVICE = "cpu"
RSS_WATCHDOG_BYTES = int(1.5 * 1024 * 1024 * 1024)
DEFAULT_BEAM_SIZE = 5
MIN_BEAM_SIZE = 1
MAX_BEAM_SIZE = 5
HEX64 = set("0123456789abcdef")
CHUNK_ID_RE = re.compile(r"^C[0-9]{4}$")
ALLOWED_ALIAS_PATHS = {"/tmp", "/private/tmp", "/var", "/private/var"}


class TranscriptionRecoveryError(ValueError):
    """Stable, public-safe recovery error code."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise TranscriptionRecoveryError("JSON_VALUE_INVALID") from exc


def object_hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _beam_size(value: Any, code: str = "BEAM_SIZE_INVALID") -> int:
    if type(value) is not int or not MIN_BEAM_SIZE <= value <= MAX_BEAM_SIZE:
        raise TranscriptionRecoveryError(code)
    return value


def build_recovery_config(*, source_media_hash: str, duration_ms: int, model_bundle_sha256: str, core_ms: int = CORE_MAX_MS, padding_ms: int = PADDING_MAX_MS, beam_size: int = DEFAULT_BEAM_SIZE) -> dict[str, Any]:
    """Return the immutable config hashed into every production chunk request."""

    beam_size = _beam_size(beam_size)
    return {
        "schema": "m2.transcription-recovery-config.v1",
        "source_media_hash": _hash64(source_media_hash, "SOURCE_MEDIA_HASH_INVALID"),
        "duration_ms": duration_ms,
        "model_bundle_sha256": _hash64(model_bundle_sha256, "MODEL_HASH_INVALID"),
        "beam_size": beam_size,
        "core_window_max_ms": core_ms,
        "context_padding_max_ms": padding_ms,
        "device": DEVICE,
        "compute_type": COMPUTE_TYPE,
        "cpu_threads": CPU_THREADS,
        "num_workers": NUM_WORKERS,
        "rss_watchdog_bytes": RSS_WATCHDOG_BYTES,
        "ffmpeg_threads": CPU_THREADS,
        "audio_sample_rate": 16_000,
        "audio_channels": 1,
        "max_audio_window_ms": CORE_MAX_MS + (2 * PADDING_MAX_MS),
        "offline_only": True,
    }


def _hash64(value: Any, code: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(char not in HEX64 for char in value):
        raise TranscriptionRecoveryError(code)
    return value


def _interval(value: Any, code: str) -> tuple[int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 2 or any(type(item) is not int for item in value):
        raise TranscriptionRecoveryError(code)
    start, end = value
    if start < 0 or end <= start:
        raise TranscriptionRecoveryError(code)
    return start, end


def plan_windows(
    duration_ms: int,
    *,
    core_ms: int = CORE_MAX_MS,
    padding_ms: int = PADDING_MAX_MS,
) -> list[dict[str, Any]]:
    """Plan adjacent half-open core windows covering ``[0,duration_ms)``."""

    if type(duration_ms) is not int or duration_ms <= 0:
        raise TranscriptionRecoveryError("MEDIA_DURATION_INVALID")
    if type(core_ms) is not int or not 0 < core_ms <= CORE_MAX_MS:
        raise TranscriptionRecoveryError("CORE_WINDOW_LIMIT")
    if type(padding_ms) is not int or not 0 <= padding_ms <= PADDING_MAX_MS:
        raise TranscriptionRecoveryError("PADDING_WINDOW_LIMIT")
    plans: list[dict[str, Any]] = []
    start = 0
    ordinal = 1
    while start < duration_ms:
        end = min(duration_ms, start + core_ms)
        window_start = max(0, start - padding_ms)
        window_end = min(duration_ms, end + padding_ms)
        plans.append(
            {
                "schema": "m2.transcription-recovery-chunk-request.v1",
                "chunk_id": f"C{ordinal:04d}",
                "core_interval_ms": [start, end],
                "window_interval_ms": [window_start, window_end],
                "global_offset_ms": window_start,
                "left_padding_ms": start - window_start,
                "right_padding_ms": window_end - end,
                "core_duration_ms": end - start,
                "window_duration_ms": window_end - window_start,
                "ownership_rule": "global_word_midpoint_in_half_open_core_interval",
            }
        )
        start = end
        ordinal += 1
    return plans


def build_chunk_request(
    plan: Mapping[str, Any],
    *,
    source_media_hash: str,
    model_bundle_sha256: str,
    config_sha256: str,
    source_pointer: str | None = None,
    config: Mapping[str, Any] | None = None,
    original_audio_unknown: bool = False,
    beam_size: int | None = None,
) -> dict[str, Any]:
    """Bind one planned window to source, model, and config hashes."""

    source_media_hash = _hash64(source_media_hash, "SOURCE_MEDIA_HASH_INVALID")
    model_bundle_sha256 = _hash64(model_bundle_sha256, "MODEL_HASH_INVALID")
    config_sha256 = _hash64(config_sha256, "CONFIG_HASH_INVALID")
    if beam_size is not None:
        beam_size = _beam_size(beam_size)
    elif isinstance(config, Mapping):
        beam_size = _beam_size(config.get("beam_size"))
    else:
        beam_size = DEFAULT_BEAM_SIZE
    chunk_id = plan.get("chunk_id")
    if not isinstance(chunk_id, str) or not chunk_id:
        raise TranscriptionRecoveryError("CHUNK_ID_INVALID")
    core = _interval(plan.get("core_interval_ms"), "CORE_INTERVAL_INVALID")
    window = _interval(plan.get("window_interval_ms"), "WINDOW_INTERVAL_INVALID")
    offset = plan.get("global_offset_ms")
    if type(offset) is not int or offset != window[0] or not window[0] <= core[0] <= core[1] <= window[1]:
        raise TranscriptionRecoveryError("CHUNK_OFFSET_INVALID")
    request: dict[str, Any] = {
        "schema": "m2.transcription-recovery-chunk-request.v1",
        "chunk_id": chunk_id,
        "source_media_hash": source_media_hash,
        "source_pointer": source_pointer,
        "global_offset_ms": offset,
        "core_interval_ms": list(core),
        "window_interval_ms": list(window),
        "audio_window_duration_ms": window[1] - window[0],
        "model_bundle_sha256": model_bundle_sha256,
        "config_sha256": config_sha256,
        "device": DEVICE,
        "compute_type": COMPUTE_TYPE,
        "cpu_threads": CPU_THREADS,
        "num_workers": NUM_WORKERS,
        "rss_watchdog_bytes": RSS_WATCHDOG_BYTES,
        "source_frame_probe_reused": True,
        "original_audio_unknown": bool(original_audio_unknown),
    }
    if config is not None:
        if not isinstance(config, Mapping) or object_hash(config) != config_sha256:
            raise TranscriptionRecoveryError("CONFIG_HASH_MISMATCH")
        if _beam_size(config.get("beam_size")) != beam_size:
            raise TranscriptionRecoveryError("BEAM_SIZE_MISMATCH")
        request["config"] = dict(config)
    request["beam_size"] = beam_size
    request["request_sha256"] = object_hash(request)
    return request


def _local_word(raw: Mapping[str, Any], offset: int) -> dict[str, Any]:
    """Normalize a runner word into global milliseconds without inventing data."""

    if "start_ms" in raw or "end_ms" in raw:
        if type(raw.get("start_ms")) is not int or type(raw.get("end_ms")) is not int:
            raise TranscriptionRecoveryError("CHUNK_WORD_TIMING_INVALID")
        start_ms, end_ms = raw["start_ms"], raw["end_ms"]
    else:
        try:
            start_ms, end_ms = round(float(raw["start"]) * 1000), round(float(raw["end"]) * 1000)
        except (KeyError, TypeError, ValueError, OverflowError):
            raise TranscriptionRecoveryError("CHUNK_WORD_TIMING_INVALID") from None
        if not math.isfinite(start_ms) or not math.isfinite(end_ms):
            raise TranscriptionRecoveryError("CHUNK_WORD_TIMING_INVALID")
    if start_ms < 0 or end_ms <= start_ms:
        raise TranscriptionRecoveryError("CHUNK_WORD_TIMING_INVALID")
    text = raw.get("text", raw.get("word"))
    if not isinstance(text, str) or not text.strip():
        raise TranscriptionRecoveryError("CHUNK_WORD_TEXT_INVALID")
    return {
        "text": text,
        "local_start_ms": start_ms,
        "local_end_ms": end_ms,
        "global_start_ms": start_ms + offset,
        "global_end_ms": end_ms + offset,
        "raw": dict(raw),
    }


def _words_and_text(
    result: Mapping[str, Any],
    offset: int,
    chunk_id: str,
    *,
    window_duration_ms: int,
    source_duration_ms: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    segments = result.get("segments")
    if not isinstance(segments, list):
        raise TranscriptionRecoveryError("CHUNK_RESULT_INVALID")
    words: list[dict[str, Any]] = []
    raw_text: list[dict[str, Any]] = []
    for index, segment in enumerate(segments):
        if not isinstance(segment, Mapping):
            raise TranscriptionRecoveryError("CHUNK_SEGMENT_INVALID")
        try:
            start = segment.get("start_ms")
            end = segment.get("end_ms")
            if type(start) is int and type(end) is int:
                local_start, local_end = start, end
            else:
                local_start = round(float(segment["start"]) * 1000)
                local_end = round(float(segment["end"]) * 1000)
            if not math.isfinite(local_start) or not math.isfinite(local_end) or local_start < 0 or local_end <= local_start or local_end > window_duration_ms:
                raise ValueError
            start, end = offset + local_start, offset + local_end
            if end > source_duration_ms:
                raise ValueError
        except (KeyError, TypeError, ValueError, OverflowError):
            raise TranscriptionRecoveryError("CHUNK_SEGMENT_TIMING_INVALID") from None
        text = segment.get("text")
        if not isinstance(text, str):
            raise TranscriptionRecoveryError("CHUNK_SEGMENT_TEXT_INVALID")
        raw_text.append({"chunk_id": chunk_id, "segment_index": index, "global_start_ms": start, "global_end_ms": end, "text": text, "source": "raw_segment_text"})
        raw_words = segment.get("words", []) or []
        if not isinstance(raw_words, list):
            raise TranscriptionRecoveryError("CHUNK_WORDS_INVALID")
        for raw in raw_words:
            if not isinstance(raw, Mapping):
                raise TranscriptionRecoveryError("CHUNK_WORD_INVALID")
            word = _local_word(raw, offset)
            word.update({"chunk_id": chunk_id, "segment_index": index})
            words.append(word)
    return words, raw_text


def _same_word(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return " ".join(str(left.get("text", "")).split()).casefold() == " ".join(str(right.get("text", "")).split()).casefold()


def _validate_binding(value: Mapping[str, Any], source_hash: str, model_hash: str, config_hash: str, *, beam_size: int = DEFAULT_BEAM_SIZE) -> None:
    beam_size = _beam_size(beam_size)
    if value.get("source_media_hash") != source_hash:
        raise TranscriptionRecoveryError("SOURCE_MEDIA_HASH_MISMATCH")
    if value.get("model_bundle_sha256") != model_hash:
        raise TranscriptionRecoveryError("MODEL_HASH_MISMATCH")
    if value.get("config_sha256") != config_hash:
        raise TranscriptionRecoveryError("CONFIG_HASH_MISMATCH")
    if "beam_size" in value:
        if _beam_size(value.get("beam_size")) != beam_size:
            raise TranscriptionRecoveryError("BEAM_SIZE_MISMATCH")
    elif beam_size != DEFAULT_BEAM_SIZE:
        raise TranscriptionRecoveryError("BEAM_SIZE_MISSING")


def _validate_cached_plan_binding(
    result: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    source_hash: str,
    model_hash: str,
    config_hash: str,
    beam_size: int = DEFAULT_BEAM_SIZE,
) -> None:
    """Require cached timing identity to match the current immutable plan."""

    for key in ("global_offset_ms", "core_interval_ms", "window_interval_ms"):
        if result.get(key) != plan.get(key):
            raise TranscriptionRecoveryError("CHUNK_PLAN_BINDING_MISMATCH")
    request = result.get("request")
    if request is not None:
        if not isinstance(request, Mapping):
            raise TranscriptionRecoveryError("CHUNK_REQUEST_INVALID")
        _validate_binding(request, source_hash, model_hash, config_hash, beam_size=beam_size)
        for key in ("chunk_id", "global_offset_ms", "core_interval_ms", "window_interval_ms"):
            if request.get(key) != plan.get(key):
                raise TranscriptionRecoveryError("CHUNK_PLAN_BINDING_MISMATCH")
        if "request_sha256" in request and request.get("request_sha256") != object_hash({key: value for key, value in request.items() if key != "request_sha256"}):
            raise TranscriptionRecoveryError("CHUNK_REQUEST_HASH_MISMATCH")
    _validate_binding(result, source_hash, model_hash, config_hash, beam_size=beam_size)


def _validate_audio_source_proof(source_hash: str, proof: Mapping[str, Any] | None) -> None:
    if not isinstance(proof, Mapping) or proof.get("source_media_hash") != source_hash or proof.get("has_audio") is not True or not isinstance(proof.get("proof_id"), str) or not proof["proof_id"]:
        raise TranscriptionRecoveryError("ORIGINAL_AUDIO_UNKNOWN_REQUIRES_AUDIO_SOURCE_PROOF")


def _chunk_metrics(result: Mapping[str, Any]) -> dict[str, Any]:
    """Keep the child's counters and language evidence without re-counting padding."""

    raw = result.get("raw") if isinstance(result.get("raw"), Mapping) else {}
    values = {
        "lexical_word_count": result.get("lexical_word_count", result.get("raw_word_count")),
        "aligned_word_count": result.get("aligned_word_count"),
        "unaligned_word_count": result.get("unaligned_word_count"),
        "language": result.get("language", raw.get("language")),
        "language_probability": result.get("language_probability", raw.get("language_probability")),
        "word_timing": result.get("word_timing"),
    }
    for key in ("lexical_word_count", "aligned_word_count", "unaligned_word_count"):
        if values[key] is not None and (type(values[key]) is not int or values[key] < 0):
            raise TranscriptionRecoveryError("CHUNK_METRICS_INVALID")
    if values["language"] is not None and not isinstance(values["language"], str):
        raise TranscriptionRecoveryError("CHUNK_METRICS_INVALID")
    probability = values["language_probability"]
    if probability is not None and (type(probability) not in {int, float} or not math.isfinite(probability) or not 0 <= probability <= 1):
        raise TranscriptionRecoveryError("CHUNK_METRICS_INVALID")
    counts = [values[k] for k in ("lexical_word_count", "aligned_word_count", "unaligned_word_count")]
    if all(x is not None for x in counts) and counts[0] != counts[1] + counts[2]:
        raise TranscriptionRecoveryError("CHUNK_METRICS_INVALID")
    return values


def merge_chunk_results(
    plans: Iterable[Mapping[str, Any]],
    results: Iterable[Mapping[str, Any]],
    *,
    source_media_hash: str,
    model_bundle_sha256: str,
    config_sha256: str,
    padding_ms: int = PADDING_MAX_MS,
    rights: Mapping[str, Any] | None = None,
    review_receipt: Mapping[str, Any] | None = None,
    original_audio_unknown: bool = False,
    audio_source_proof: Mapping[str, Any] | None = None,
    beam_size: int = DEFAULT_BEAM_SIZE,
) -> dict[str, Any]:
    """Merge completed chunks by global midpoint ownership.

    Raw segment text and padding words remain separate from owned words.  Any
    incomplete chunk or multi-window boundary receives a non-OBSERVED result;
    this function never claims a perfect semantic or phonetic merge.
    """

    source_media_hash = _hash64(source_media_hash, "SOURCE_MEDIA_HASH_INVALID")
    model_bundle_sha256 = _hash64(model_bundle_sha256, "MODEL_HASH_INVALID")
    config_sha256 = _hash64(config_sha256, "CONFIG_HASH_INVALID")
    beam_size = _beam_size(beam_size)
    if original_audio_unknown:
        _validate_audio_source_proof(source_media_hash, audio_source_proof)
    if type(padding_ms) is not int or not 0 <= padding_ms <= PADDING_MAX_MS:
        raise TranscriptionRecoveryError("PADDING_WINDOW_LIMIT")
    plan_list = list(plans)
    plan_by_id: dict[str, Mapping[str, Any]] = {}
    for plan in plan_list:
        chunk_id = plan.get("chunk_id")
        if not isinstance(chunk_id, str) or chunk_id in plan_by_id:
            raise TranscriptionRecoveryError("CHUNK_ID_INVALID")
        plan_by_id[chunk_id] = plan
    result_by_id: dict[str, Mapping[str, Any]] = {}
    for result in results:
        if not isinstance(result, Mapping):
            raise TranscriptionRecoveryError("CHUNK_RESULT_INVALID")
        chunk_id = result.get("chunk_id")
        if not isinstance(chunk_id, str) or chunk_id in result_by_id or chunk_id not in plan_by_id:
            raise TranscriptionRecoveryError("CHUNK_RESULT_ID_INVALID")
        _validate_binding(result, source_media_hash, model_bundle_sha256, config_sha256, beam_size=beam_size)
        result_by_id[chunk_id] = result

    all_words: list[dict[str, Any]] = []
    raw_segment_text: list[dict[str, Any]] = []
    padding_words: list[dict[str, Any]] = []
    owned_words: list[dict[str, Any]] = []
    chunk_receipts: list[dict[str, Any]] = []
    chunk_metrics: list[dict[str, Any]] = []
    resource_receipts: list[dict[str, Any]] = []
    incomplete: list[str] = []
    audio_hashes: list[dict[str, Any]] = []
    boundary_issues: list[str] = []
    for chunk_id, plan in plan_by_id.items():
        core_start, core_end = _interval(plan.get("core_interval_ms"), "CORE_INTERVAL_INVALID")
        window_start, window_end = _interval(plan.get("window_interval_ms"), "WINDOW_INTERVAL_INVALID")
        offset = plan.get("global_offset_ms")
        if type(offset) is not int or offset != window_start:
            raise TranscriptionRecoveryError("CHUNK_OFFSET_INVALID")
        result = result_by_id.get(chunk_id)
        if result is None:
            incomplete.append(chunk_id)
            chunk_receipts.append({"chunk_id": chunk_id, "observation_state": "PARTIAL", "failure_code": "CHUNK_RESULT_MISSING", "core_interval_ms": [core_start, core_end]})
            continue
        state = result.get("observation_state")
        if isinstance(result.get("parent_resource_receipt"), Mapping):
            resource_receipts.append({"chunk_id": chunk_id, **dict(result["parent_resource_receipt"])})
        audio_hash = result.get("source_audio_sha256", result.get("audio_sha256"))
        if audio_hash is not None:
            audio_hash = _hash64(audio_hash, "CHUNK_AUDIO_HASH_INVALID")
            audio_hashes.append({"chunk_id": chunk_id, "sha256": audio_hash, "core_interval_ms": [core_start, core_end]})
        request = result.get("request")
        if request is not None:
            if not isinstance(request, Mapping):
                raise TranscriptionRecoveryError("CHUNK_REQUEST_INVALID")
            _validate_binding(request, source_media_hash, model_bundle_sha256, config_sha256, beam_size=beam_size)
        if state not in {"OBSERVED", "SUSPICIOUS_TIMINGS"}:
            incomplete.append(chunk_id)
            chunk_receipts.append({"chunk_id": chunk_id, "observation_state": "PARTIAL", "failure_code": result.get("failure_code", "CHUNK_FAILED"), "core_interval_ms": [core_start, core_end], "result": dict(result)})
            continue
        if audio_hash is None:
            incomplete.append(chunk_id)
            chunk_receipts.append({"chunk_id": chunk_id, "observation_state": "PARTIAL", "failure_code": "CHUNK_AUDIO_HASH_MISSING", "core_interval_ms": [core_start, core_end]})
            continue
        try:
            words, text_rows = _words_and_text(
                result,
                offset,
                chunk_id,
                window_duration_ms=window_end - window_start,
                source_duration_ms=max(item["core_interval_ms"][1] for item in plan_list),
            )
        except TranscriptionRecoveryError:
            incomplete.append(chunk_id)
            chunk_receipts.append({"chunk_id": chunk_id, "observation_state": "PARTIAL", "failure_code": "CHUNK_RESULT_INVALID", "core_interval_ms": [core_start, core_end]})
            continue
        raw_segment_text.extend(text_rows)
        metrics = _chunk_metrics(result)
        metrics.update({"chunk_id": chunk_id, "core_interval_ms": [core_start, core_end], "window_interval_ms": [window_start, window_end], "padding_overlap_possible": window_start < core_start or core_end < window_end})
        chunk_metrics.append(metrics)
        for word in words:
            midpoint_numerator = word["global_start_ms"] + word["global_end_ms"]
            owner = 2 * core_start <= midpoint_numerator < 2 * core_end
            inside_window = window_start <= word["global_start_ms"] and word["global_end_ms"] <= window_end
            if not inside_window:
                boundary_issues.append("CHUNK_WORD_OUTSIDE_WINDOW_REVIEW_REQUIRED")
            word["ownership"] = "core" if owner else "padding"
            word["midpoint_ms"] = midpoint_numerator / 2
            all_words.append(word)
            if owner:
                owned_words.append(word)
            else:
                padding_words.append(word)
        chunk_receipts.append({"chunk_id": chunk_id, "observation_state": state, "failure_code": result.get("failure_code"), "core_interval_ms": [core_start, core_end], "window_interval_ms": [window_start, window_end], "raw_transcript": result.get("raw", result.get("segments")), "source_audio_sha256": audio_hash, "metrics": metrics, "parent_resource_receipt": result.get("parent_resource_receipt")})

    # Compare overlapping context from different chunks.  Equal text is a
    # duplicate context observation and is counted once by ownership.  A
    # disagreement is retained as review evidence, never silently selected.
    for index, left in enumerate(all_words):
        for right in all_words[index + 1 :]:
            if left["chunk_id"] == right["chunk_id"]:
                continue
            overlap = max(left["global_start_ms"], right["global_start_ms"]) < min(left["global_end_ms"], right["global_end_ms"])
            near = abs(left["midpoint_ms"] - right["midpoint_ms"]) <= 2 * padding_ms
            if (overlap or near) and not _same_word(left, right):
                if "CHUNK_BOUNDARY_SEMANTIC_PHONETIC_REVIEW_REQUIRED" not in boundary_issues:
                    boundary_issues.append("CHUNK_BOUNDARY_SEMANTIC_PHONETIC_REVIEW_REQUIRED")
    if len(plan_list) > 1:
        boundary_issues.append("WINDOW_BOUNDARY_TIMING_REVIEW_REQUIRED")
    boundary_issues = list(dict.fromkeys(boundary_issues))

    rights_approved = isinstance(rights, Mapping) and rights.get("analysis_allowed") is True and bool(rights.get("receipt_id"))
    evidence_sha256 = object_hash({"plans": plan_list, "results": result_by_id, "source_media_hash": source_media_hash,
                                  "model_bundle_sha256": model_bundle_sha256, "config_sha256": config_sha256, "rights": rights})
    analysis_approved = (isinstance(review_receipt, Mapping)
        and review_receipt.get("schema") == "m2.transcription-quality-review.v1"
        and review_receipt.get("verdict") == "ACCEPTED"
        and all(isinstance(review_receipt.get(k), str) and review_receipt[k].strip() for k in ("review_id", "maker_actor", "reviewer_actor"))
        and review_receipt["maker_actor"] != review_receipt["reviewer_actor"]
        and isinstance(review_receipt.get("scope"), list)
        and all(isinstance(item, str) for item in review_receipt["scope"])
        and {"transcript_quality", "word_timing"}.issubset(review_receipt["scope"])
        and review_receipt.get("evidence_sha256") == evidence_sha256
        and review_receipt.get("source_media_hash") == source_media_hash
        and review_receipt.get("model_bundle_sha256") == model_bundle_sha256
        and review_receipt.get("config_sha256") == config_sha256)
    full_alignment = bool(all_words) and all(item["word_timing"] == "OBSERVED" and item["unaligned_word_count"] == 0 for item in chunk_metrics)
    if incomplete:
        observation_state = "PARTIAL"
        failure_code = "CHUNK_FAILURE_REVIEW_REQUIRED"
    elif boundary_issues:
        observation_state = "SUSPICIOUS_TIMINGS"
        failure_code = "WINDOW_BOUNDARY_REVIEW_REQUIRED"
    else:
        observation_state = "OBSERVED"
        failure_code = None
    return {
        "schema": "m2.transcription-recovery.v1",
        "modality": "transcript",
        "observation_state": observation_state,
        "failure_code": failure_code,
        "machine_observed": observation_state in {"OBSERVED", "SUSPICIOUS_TIMINGS"} and not incomplete,
        "full_transcript_observed": observation_state == "OBSERVED" and analysis_approved and full_alignment,
        "review_evidence_sha256": evidence_sha256,
        "analysis_approved": analysis_approved,
        "review_state": "APPROVED_WITH_SCOPE" if analysis_approved and observation_state == "OBSERVED" else "REVIEW_REQUIRED",
        "source_media_hash": source_media_hash,
        "model_bundle_sha256": model_bundle_sha256,
        "config_sha256": config_sha256,
        "beam_size": beam_size,
        "audio_hashes": audio_hashes,
        "chunks": chunk_receipts,
        "chunk_metrics": chunk_metrics,
        "resource_receipts": resource_receipts,
        "raw_segment_text": raw_segment_text,
        "padding_words": padding_words,
        "words": owned_words,
        "raw_word_count": len(all_words),
        "word_count": len(owned_words),
        "padding_word_count": len(padding_words),
        "chunk_count": len(plan_list),
        "completed_chunk_count": len(plan_list) - len(incomplete),
        "incomplete_chunks": incomplete,
        "boundary_issues": boundary_issues,
        "rights_state": "APPROVED" if rights_approved else "REQUIRED",
        "analysis_ready": rights_approved and analysis_approved and observation_state == "OBSERVED" and full_alignment,
        "rights_required_for_frames_and_asr": True,
        "asr_execution": True if all_words or any(chunk.get("observation_state") in {"OBSERVED", "SUSPICIOUS_TIMINGS"} for chunk in chunk_receipts) else None,
        "no_speech_confirmed": False,
        "original_audio_status": "UNKNOWN" if original_audio_unknown else "NOT_EVALUATED",
        "original_audio_unknown": bool(original_audio_unknown),
        "speech_state": "UNKNOWN" if original_audio_unknown else "NOT_EVALUATED",
        "aggregate_metrics": {
            "lexical_word_count": chunk_metrics[0]["lexical_word_count"] if len(chunk_metrics) == 1 else None,
            "aligned_word_count": chunk_metrics[0]["aligned_word_count"] if len(chunk_metrics) == 1 else None,
            "unaligned_word_count": chunk_metrics[0]["unaligned_word_count"] if len(chunk_metrics) == 1 else None,
            "language": chunk_metrics[0]["language"] if len(chunk_metrics) == 1 else None,
            "language_probability": chunk_metrics[0]["language_probability"] if len(chunk_metrics) == 1 else None,
            "word_timing": chunk_metrics[0]["word_timing"] if len(chunk_metrics) == 1 else "PARTIAL",
            "chunk_metric_sums": {
                key: sum(item[key] for item in chunk_metrics if isinstance(item[key], int)) if chunk_metrics and all(isinstance(item[key], int) for item in chunk_metrics) else None
                for key in ("lexical_word_count", "aligned_word_count", "unaligned_word_count")
            },
            "chunk_metric_sums_additivity": "NON_ADDITIVE_FOR_PADDING_OVERLAP",
            "owned_aligned_word_count": len(owned_words),
            "beam_size": beam_size,
        },
    }


def completed_chunk_ids(
    plans: Iterable[Mapping[str, Any]],
    results: Iterable[Mapping[str, Any]],
    *,
    source_media_hash: str,
    model_bundle_sha256: str,
    config_sha256: str,
    artifact_roots: Mapping[str, str | Path] | None = None,
    beam_size: int = DEFAULT_BEAM_SIZE,
) -> set[str]:
    """Return only hash-bound completed chunks safe to resume."""

    source_media_hash = _hash64(source_media_hash, "SOURCE_MEDIA_HASH_INVALID")
    model_bundle_sha256 = _hash64(model_bundle_sha256, "MODEL_HASH_INVALID")
    config_sha256 = _hash64(config_sha256, "CONFIG_HASH_INVALID")
    beam_size = _beam_size(beam_size)
    plan_list = list(plans)
    plan_by_id: dict[str, Mapping[str, Any]] = {}
    for plan in plan_list:
        if not isinstance(plan, Mapping):
            raise TranscriptionRecoveryError("CHUNK_PLAN_INVALID")
        chunk_id = plan.get("chunk_id")
        if not isinstance(chunk_id, str) or not CHUNK_ID_RE.fullmatch(chunk_id) or chunk_id in plan_by_id:
            raise TranscriptionRecoveryError("CHUNK_PLAN_ID_INVALID")
        plan_by_id[chunk_id] = plan
    result_list = list(results)
    seen: set[str] = set()
    for result in result_list:
        if not isinstance(result, Mapping) or result.get("chunk_id") not in plan_by_id:
            raise TranscriptionRecoveryError("CHUNK_RESULT_ID_INVALID")
        chunk_id = result["chunk_id"]
        if chunk_id in seen:
            raise TranscriptionRecoveryError("CHUNK_RESULT_ID_DUPLICATE")
        seen.add(chunk_id)
    completed: set[str] = set()
    for result in result_list:
        chunk_id = result["chunk_id"]
        _validate_binding(result, source_media_hash, model_bundle_sha256, config_sha256, beam_size=beam_size)
        _validate_cached_plan_binding(
            result,
            plan_by_id[chunk_id],
            source_hash=source_media_hash,
            model_hash=model_bundle_sha256,
            config_hash=config_sha256,
            beam_size=beam_size,
        )
        if result.get("observation_state") in {"OBSERVED", "SUSPICIOUS_TIMINGS"}:
            if result.get("source_audio_sha256", result.get("audio_sha256")) is None:
                raise TranscriptionRecoveryError("CHUNK_AUDIO_HASH_MISSING")
            root = artifact_roots.get(chunk_id) if isinstance(artifact_roots, Mapping) else None
            if root is None:
                raise TranscriptionRecoveryError("CHUNK_ARTIFACT_ROOT_REQUIRED")
            validate_completed_chunk_artifacts(result, Path(root), source_media_hash, model_bundle_sha256, config_sha256)
            completed.add(result["chunk_id"])
    return completed


def validate_completed_chunk_artifacts(
    result: Mapping[str, Any],
    artifact_root: Path,
    source_media_hash: str,
    model_bundle_sha256: str,
    config_sha256: str,
) -> None:
    """Verify persisted request/raw/audio/result evidence before API resume."""

    source_media_hash = _hash64(source_media_hash, "SOURCE_MEDIA_HASH_INVALID")
    model_bundle_sha256 = _hash64(model_bundle_sha256, "MODEL_HASH_INVALID")
    config_sha256 = _hash64(config_sha256, "CONFIG_HASH_INVALID")
    if not isinstance(result.get("chunk_id"), str) or not CHUNK_ID_RE.fullmatch(result["chunk_id"]):
        raise TranscriptionRecoveryError("CHUNK_ID_INVALID")
    if any(result.get(key) != value for key, value in (("source_media_hash", source_media_hash), ("model_bundle_sha256", model_bundle_sha256), ("config_sha256", config_sha256))):
        raise TranscriptionRecoveryError("CHUNK_RESULT_BINDING_MISMATCH")
    root = artifact_root.absolute()
    for ancestor in (root, *root.parents):
        if ancestor.is_symlink() and str(ancestor) not in ALLOWED_ALIAS_PATHS:
            raise TranscriptionRecoveryError("OUTPUT_SYMLINK_ANCESTOR")
    if root.is_symlink() or not root.is_dir():
        raise TranscriptionRecoveryError("CHUNK_ARTIFACT_ROOT_INVALID")
    artifacts, hashes = result.get("artifacts"), result.get("artifact_hashes")
    if not isinstance(artifacts, Mapping) or not isinstance(hashes, Mapping):
        raise TranscriptionRecoveryError("CHUNK_ARTIFACT_BINDING_MISSING")
    def artifact_path(name: Any) -> Path:
        if not isinstance(name, str) or not name or Path(name).is_absolute() or Path(name).name != name:
            raise TranscriptionRecoveryError("CHUNK_ARTIFACT_PATH_INVALID")
        candidate = root / name
        if candidate.is_symlink() or not candidate.is_file():
            raise TranscriptionRecoveryError("CHUNK_ARTIFACT_MISSING")
        return candidate
    for key in ("audio", "raw", "request"):
        if key not in artifacts or key not in hashes:
            raise TranscriptionRecoveryError("CHUNK_ARTIFACT_BINDING_MISSING")
        path = artifact_path(artifacts[key])
        if hashlib.sha256(path.read_bytes()).hexdigest() != hashes[key]:
            raise TranscriptionRecoveryError("CHUNK_ARTIFACT_HASH_MISMATCH")
    audio_path, raw_path, request_path = (artifact_path(artifacts[key]) for key in ("audio", "raw", "request"))
    if result.get("source_audio_sha256") != hashlib.sha256(audio_path.read_bytes()).hexdigest() or result.get("raw_transcript_sha256") != hashlib.sha256(raw_path.read_bytes()).hexdigest():
        raise TranscriptionRecoveryError("CHUNK_ARTIFACT_HASH_MISMATCH")
    try:
        persisted_raw = json.loads(raw_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise TranscriptionRecoveryError("CHUNK_RAW_ARTIFACT_INVALID") from None
    if persisted_raw != result.get("raw"):
        raise TranscriptionRecoveryError("CHUNK_RAW_RESULT_MISMATCH")
    result_path, sidecar = root / "chunk-result.json", root / "chunk-result.sha256"
    if result_path.is_symlink() or not result_path.is_file() or sidecar.is_symlink() or not sidecar.is_file() or sidecar.read_text(encoding="ascii").strip() != hashlib.sha256(result_path.read_bytes()).hexdigest():
        raise TranscriptionRecoveryError("CHUNK_RESULT_HASH_MISMATCH")
    try:
        persisted = json.loads(request_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise TranscriptionRecoveryError("CHUNK_REQUEST_ARTIFACT_INVALID") from None
    if not isinstance(persisted, Mapping) or persisted.get("request_sha256") != result.get("request_sha256") or object_hash({key: value for key, value in persisted.items() if key != "request_sha256"}) != persisted.get("request_sha256"):
        raise TranscriptionRecoveryError("CHUNK_REQUEST_HASH_MISMATCH")
    for key in ("chunk_id", "source_media_hash", "model_bundle_sha256", "config_sha256", "beam_size", "global_offset_ms", "core_interval_ms", "window_interval_ms"):
        if persisted.get(key) != result.get(key):
            raise TranscriptionRecoveryError("CHUNK_REQUEST_BINDING_MISMATCH")


def recover_chunks(
    plans: Iterable[Mapping[str, Any]],
    *,
    source_media_hash: str,
    model_bundle_sha256: str,
    config_sha256: str,
    chunk_runner: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    completed_results: Iterable[Mapping[str, Any]] = (),
    source_pointer: str | None = None,
    rights: Mapping[str, Any] | None = None,
    config: Mapping[str, Any] | None = None,
    production: Mapping[str, Any] | None = None,
    original_audio_unknown: bool = False,
    audio_source_proof: Mapping[str, Any] | None = None,
    review_receipt: Mapping[str, Any] | None = None,
    completed_artifact_roots: Mapping[str, str | Path] | None = None,
    beam_size: int | None = None,
) -> dict[str, Any]:
    """Run a serial injected chunk route and merge its immutable receipts.

    ``chunk_runner`` is intentionally mandatory for any missing chunk.  A
    timeout or process-budget exception becomes an explicit partial result;
    no retry, model launch, or parent-worker launch occurs here.
    """

    plan_list = list(plans)
    if beam_size is None:
        beam_size = _beam_size(config.get("beam_size")) if isinstance(config, Mapping) else DEFAULT_BEAM_SIZE
    else:
        beam_size = _beam_size(beam_size)
        if isinstance(config, Mapping) and _beam_size(config.get("beam_size")) != beam_size:
            raise TranscriptionRecoveryError("BEAM_SIZE_MISMATCH")
    if isinstance(config, Mapping) and object_hash(config) != config_sha256:
        raise TranscriptionRecoveryError("CONFIG_HASH_MISMATCH")
    if original_audio_unknown:
        _validate_audio_source_proof(_hash64(source_media_hash, "SOURCE_MEDIA_HASH_INVALID"), audio_source_proof)
    if chunk_runner is None and production is not None:
        from .transcription_chunk_worker import production_chunk_runner
        production_args = dict(production)
        chunk_runner = lambda request: production_chunk_runner(request, **production_args)
    existing = list(completed_results)
    completed_chunk_ids(
        plan_list,
        existing,
        source_media_hash=source_media_hash,
        model_bundle_sha256=model_bundle_sha256,
        config_sha256=config_sha256,
        artifact_roots=completed_artifact_roots,
        beam_size=beam_size,
    )
    by_id = {item["chunk_id"]: item for item in existing}
    results: list[Mapping[str, Any]] = []
    for plan in plan_list:
        request = build_chunk_request(plan, source_media_hash=source_media_hash, model_bundle_sha256=model_bundle_sha256, config_sha256=config_sha256, source_pointer=source_pointer, config=config, original_audio_unknown=original_audio_unknown, beam_size=beam_size)
        chunk_id = request["chunk_id"]
        prior = by_id.get(chunk_id)
        if prior is not None and prior.get("observation_state") in {"OBSERVED", "SUSPICIOUS_TIMINGS"}:
            results.append(prior)
            continue
        if chunk_runner is None:
            results.append({**request, "chunk_id": chunk_id, "observation_state": "PARTIAL", "failure_code": "CHUNK_RUNNER_REQUIRED", "source_audio_sha256": None, "request": request})
            continue
        try:
            raw_result = chunk_runner(request)
            if not isinstance(raw_result, Mapping):
                raise TranscriptionRecoveryError("CHUNK_RESULT_INVALID")
            result = dict(raw_result)
            result.setdefault("chunk_id", chunk_id)
            result.setdefault("source_media_hash", source_media_hash)
            result.setdefault("model_bundle_sha256", model_bundle_sha256)
            result.setdefault("config_sha256", config_sha256)
            result["request"] = request
            results.append(result)
        except (ProcessBudgetError, TimeoutError) as exc:
            results.append({**request, "chunk_id": chunk_id, "observation_state": "PARTIAL", "failure_code": str(exc), "source_audio_sha256": None, "request": request})
        except (TranscriptionRecoveryError, ValueError, OSError, TypeError) as exc:
            results.append({**request, "chunk_id": chunk_id, "observation_state": "PARTIAL", "failure_code": str(exc), "source_audio_sha256": None, "request": request})
    return merge_chunk_results(
        plan_list,
        results,
        source_media_hash=source_media_hash,
        model_bundle_sha256=model_bundle_sha256,
        config_sha256=config_sha256,
        beam_size=beam_size,
        rights=rights,
        review_receipt=review_receipt,
        original_audio_unknown=original_audio_unknown,
        audio_source_proof=audio_source_proof,
    )


__all__ = [
    "CORE_MAX_MS",
    "PADDING_MAX_MS",
    "DEFAULT_BEAM_SIZE",
    "MIN_BEAM_SIZE",
    "MAX_BEAM_SIZE",
    "RSS_WATCHDOG_BYTES",
    "TranscriptionRecoveryError",
    "build_recovery_config",
    "build_chunk_request",
    "completed_chunk_ids",
    "merge_chunk_results",
    "object_hash",
    "plan_windows",
    "recover_chunks",
    "validate_completed_chunk_artifacts",
]
