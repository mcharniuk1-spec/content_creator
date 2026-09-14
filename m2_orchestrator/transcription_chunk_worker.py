"""Concrete offline worker for one bounded transcription recovery chunk.

The parent recovery route starts this module as one child at a time through
``bounded_process``.  The child validates source/model/config hashes, extracts
one local PCM window, runs only the frozen local Faster-Whisper configuration,
and writes raw/normalized receipts into its private chunk directory.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path
from typing import Any, Mapping

from .media_transcription import (
    MAX_AUDIO_BYTES,
    MAX_RAW_JSON_BYTES,
    TranscriptionError,
    _normalize_raw,
    _safe_relative,
    digest,
    object_hash,
    validate_model_bundle,
)
from .process_budget import ProcessBudgetError, bounded_process
from m2_studio.media import digital_silence


SCHEMA = "m2.transcription-recovery-chunk-result.v1"
CHUNK_TIMEOUT_SECONDS = 900
DEFAULT_BEAM_SIZE = 5
MIN_BEAM_SIZE = 1
MAX_BEAM_SIZE = 5
FFMPEG_RSS_WATCHDOG_BYTES = 512 * 1024 * 1024
HEX64 = set("0123456789abcdef")
CHUNK_ID_RE = re.compile(r"^C[0-9]{4}$")
ALLOWED_ALIAS_PATHS = {"/tmp", "/private/tmp", "/var", "/private/var"}


def _hash64(value: Any, code: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(char not in HEX64 for char in value):
        raise TranscriptionError(code)
    return value


def _beam_size(value: Any, code: str = "BEAM_SIZE_INVALID") -> int:
    if type(value) is not int or not MIN_BEAM_SIZE <= value <= MAX_BEAM_SIZE:
        raise TranscriptionError(code)
    return value


def _json_write(path: Path, value: Mapping[str, Any], *, overwrite: bool = False) -> None:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
    if len(payload) > MAX_RAW_JSON_BYTES:
        raise TranscriptionError("OUTPUT_JSON_LIMIT")
    if path.exists() or path.is_symlink():
        if not overwrite:
            raise TranscriptionError("OUTPUT_ALREADY_EXISTS")
    temporary = path.with_name(path.name + ".partial")
    if temporary.exists() or temporary.is_symlink():
        raise TranscriptionError("OUTPUT_PARTIAL_EXISTS")
    temporary.write_bytes(payload)
    temporary.replace(path)


def _reject_symlink_ancestors(path: Path) -> None:
    """Reject output ancestry symlinks, retaining the system tmp/var aliases."""

    absolute = path.absolute()
    for ancestor in (absolute, *absolute.parents):
        if ancestor.is_symlink() and str(ancestor) not in ALLOWED_ALIAS_PATHS:
            raise TranscriptionError("OUTPUT_SYMLINK_ANCESTOR")


def _contained_path(root: Path, relative: str, code: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise TranscriptionError(code)
    candidate_raw = root / relative
    _reject_symlink_ancestors(candidate_raw)
    if candidate_raw.is_symlink():
        raise TranscriptionError(code)
    candidate = candidate_raw.resolve(strict=False)
    try:
        candidate.relative_to(root.resolve(strict=False))
    except ValueError:
        raise TranscriptionError(code) from None
    return candidate


def _write_result_digest(path: Path) -> None:
    digest_path = path.with_name("chunk-result.sha256")
    if digest_path.exists() or digest_path.is_symlink():
        raise TranscriptionError("OUTPUT_ALREADY_EXISTS")
    digest_path.write_text(digest(path) + "\n", encoding="ascii")


def _resource_receipt(process: Mapping[str, Any] | None, *, phase: str, elapsed_seconds: float | None = None, failure_code: str | None = None) -> dict[str, Any]:
    """Normalize bounded_process resource evidence, including explicit gaps."""

    receipt = {
        "schema": "m2.transcription-recovery-resource-receipt.v1",
        "phase": phase,
        "returncode": process.get("returncode") if isinstance(process, Mapping) else None,
        "elapsed_seconds": process.get("elapsed_seconds", elapsed_seconds) if isinstance(process, Mapping) else elapsed_seconds,
        "sampled_peak_rss_bytes": process.get("sampled_peak_rss_bytes") if isinstance(process, Mapping) else None,
        "rss_watchdog_limit_bytes": process.get("rss_watchdog_limit_bytes") if isinstance(process, Mapping) else int(1.5 * 1024 * 1024 * 1024),
        "rss_poll_seconds": process.get("rss_poll_seconds") if isinstance(process, Mapping) else None,
        "measurement_state": "OBSERVED" if isinstance(process, Mapping) else "UNAVAILABLE_ON_EXCEPTION",
    }
    if failure_code is not None:
        receipt["failure_code"] = failure_code
    return receipt


def _persist_parent_resource_receipt(output: Path, receipt: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    """Persist parent wait/limit evidence separately so child hashes stay stable."""

    path = output / "parent-resource-receipt.json"
    request_path = output / "chunk-request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    result_path = output / "chunk-result.json"
    bound = dict(receipt) | {"binding": {
        **{k: request[k] for k in ("chunk_id", "source_media_hash", "model_bundle_sha256", "config_sha256", "request_sha256")},
        "request_file_sha256": digest(request_path),
        "child_result_sha256": digest(result_path) if result_path.is_file() and not result_path.is_symlink() else None,
    }}
    _json_write(path, bound)
    return bound, digest(path)


def _attach_parent_resource_receipt(result: Mapping[str, Any], receipt: Mapping[str, Any], receipt_sha256: str) -> dict[str, Any]:
    enriched = dict(result)
    enriched["parent_resource_receipt"] = dict(receipt)
    enriched["parent_resource_receipt_sha256"] = receipt_sha256
    return enriched


def _load_parent_resource_receipt(output: Path) -> tuple[dict[str, Any] | None, str | None]:
    path = output / "parent-resource-receipt.json"
    if path.is_symlink() or not path.is_file():
        return None, None
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise TranscriptionError("RESOURCE_RECEIPT_INVALID") from None
    if not isinstance(receipt, Mapping) or receipt.get("schema") != "m2.transcription-recovery-resource-receipt.v1":
        raise TranscriptionError("RESOURCE_RECEIPT_INVALID")
    request_path, result_path = output / "chunk-request.json", output / "chunk-result.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    expected = {**{k: request[k] for k in ("chunk_id", "source_media_hash", "model_bundle_sha256", "config_sha256", "request_sha256")},
                "request_file_sha256": digest(request_path), "child_result_sha256": digest(result_path)}
    if receipt.get("binding") != expected:
        raise TranscriptionError("RESOURCE_RECEIPT_BINDING_MISMATCH")
    return dict(receipt), digest(path)


def _finalize_completed_result(result: Mapping[str, Any], request: Mapping[str, Any], request_path: Path, output: Path) -> dict[str, Any]:
    """Bind all persisted artifact hashes after the result JSON is complete."""

    if result.get("observation_state") not in {"OBSERVED", "SUSPICIOUS_TIMINGS"}:
        return dict(result)
    audio = output / "chunk-audio.wav"
    raw = output / "chunk-raw.json"
    for path in (audio, raw, request_path):
        if path.is_symlink() or not path.is_file():
            raise TranscriptionError("CHUNK_ARTIFACT_MISSING")
    finalized = dict(result)
    finalized["request_sha256"] = request["request_sha256"]
    finalized["artifacts"] = {"audio": audio.name, "raw": raw.name, "request": request_path.name}
    finalized["artifact_hashes"] = {"audio": digest(audio), "raw": digest(raw), "request": digest(request_path)}
    finalized["source_audio_sha256"] = finalized["artifact_hashes"]["audio"]
    finalized["raw_transcript_sha256"] = finalized["artifact_hashes"]["raw"]
    result_path = output / "chunk-result.json"
    _json_write(result_path, finalized, overwrite=True)
    _write_result_digest(result_path)
    return finalized


def _failure(request: Mapping[str, Any], code: str, *, source_audio_sha256: str | None = None, asr_execution: bool | None = None, resource_receipt: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "modality": "transcript",
        "chunk_id": request.get("chunk_id"),
        "observation_state": "PARTIAL",
        "failure_code": code,
        "source_media_hash": request.get("source_media_hash"),
        "source_audio_sha256": source_audio_sha256,
        "model_bundle_sha256": request.get("model_bundle_sha256"),
        "config_sha256": request.get("config_sha256"),
        "beam_size": request.get("beam_size"),
        "global_offset_ms": request.get("global_offset_ms"),
        "core_interval_ms": request.get("core_interval_ms"),
        "window_interval_ms": request.get("window_interval_ms"),
        "raw": None,
        "segments": [],
        "asr_execution": asr_execution,
        "no_speech_confirmed": False,
        "original_audio_status": "UNKNOWN" if request.get("original_audio_unknown") is True else "NOT_EVALUATED",
        "original_audio_unknown": request.get("original_audio_unknown") is True,
        "speech_state": "UNKNOWN",
        "review_state": "REVIEW_REQUIRED",
        "resource_receipt": dict(resource_receipt or {}),
    }


def _validate_request(request: Mapping[str, Any]) -> tuple[Path, Path, Path, dict[str, Any], tuple[int, int], tuple[int, int]]:
    if request.get("schema") != "m2.transcription-recovery-chunk-request.v1":
        raise TranscriptionError("CHUNK_REQUEST_INVALID")
    source_hash = _hash64(request.get("source_media_hash"), "SOURCE_MEDIA_HASH_INVALID")
    model_hash = _hash64(request.get("model_bundle_sha256"), "MODEL_HASH_INVALID")
    config_hash = _hash64(request.get("config_sha256"), "CONFIG_HASH_INVALID")
    request_hash = request.get("request_sha256")
    unsigned_request = {key: value for key, value in request.items() if key != "request_sha256"}
    if request_hash != object_hash(unsigned_request):
        raise TranscriptionError("CHUNK_REQUEST_HASH_MISMATCH")
    if not isinstance(request.get("chunk_id"), str) or not CHUNK_ID_RE.fullmatch(request["chunk_id"]):
        raise TranscriptionError("CHUNK_ID_INVALID")
    core = request.get("core_interval_ms")
    window = request.get("window_interval_ms")
    if not isinstance(core, list) or len(core) != 2 or any(type(value) is not int for value in core):
        raise TranscriptionError("CORE_INTERVAL_INVALID")
    if not isinstance(window, list) or len(window) != 2 or any(type(value) is not int for value in window):
        raise TranscriptionError("WINDOW_INTERVAL_INVALID")
    core_interval, window_interval = (core[0], core[1]), (window[0], window[1])
    if core_interval[0] < 0 or core_interval[1] <= core_interval[0] or window_interval[0] < 0 or window_interval[1] <= window_interval[0] or not window_interval[0] <= core_interval[0] <= core_interval[1] <= window_interval[1]:
        raise TranscriptionError("CHUNK_INTERVAL_INVALID")
    if window_interval[1] - window_interval[0] > 32_000:
        raise TranscriptionError("CHUNK_WINDOW_LIMIT")
    if request.get("global_offset_ms") != window_interval[0]:
        raise TranscriptionError("CHUNK_OFFSET_INVALID")
    config = request.get("config")
    if not isinstance(config, Mapping) or object_hash(config) != config_hash:
        raise TranscriptionError("CONFIG_HASH_MISMATCH")
    beam_size = _beam_size(request.get("beam_size"), "BEAM_SIZE_MISSING")
    config_beam_size = _beam_size(config.get("beam_size"), "BEAM_SIZE_MISSING")
    if config_beam_size != beam_size:
        raise TranscriptionError("BEAM_SIZE_MISMATCH")
    if config.get("source_media_hash") != source_hash or config.get("model_bundle_sha256") != model_hash or config.get("device") != "cpu" or config.get("compute_type") != "int8" or config.get("cpu_threads") != 2 or config.get("num_workers") != 1 or config.get("rss_watchdog_bytes") != int(1.5 * 1024 * 1024 * 1024):
        raise TranscriptionError("CONFIG_VALUES_INVALID")
    try:
        source_root_arg = Path(request["source_root"])
        output_arg = Path(request["output"])
        model_dir_arg = Path(request["model_dir"])
        source_pointer = request.get("source_pointer")
        if not isinstance(source_pointer, str) or not source_pointer or Path(source_pointer).is_absolute() or "\\" in source_pointer:
            raise TranscriptionError("INVALID_MEDIA_POINTER")
        # Inspect lexical paths before resolve() so a symlinked root or source
        # pointer cannot lose its provenance and become an apparently safe
        # resolved path.
        _reject_symlink_ancestors(source_root_arg)
        _reject_symlink_ancestors(model_dir_arg)
        _reject_symlink_ancestors(source_root_arg / source_pointer)
        _reject_symlink_ancestors(output_arg)
        source_root = source_root_arg.resolve(strict=True)
        output = output_arg.resolve()
        model_dir = model_dir_arg.resolve(strict=True)
    except TranscriptionError:
        raise
    except (KeyError, OSError, TypeError, ValueError):
        raise TranscriptionError("WORKER_PATH_INVALID") from None
    source = _safe_relative(source_root, source_pointer)
    if digest(source) != source_hash:
        raise TranscriptionError("MEDIA_HASH_MISMATCH")
    receipt = validate_model_bundle(model_dir)
    if receipt["bundle_sha256"] != model_hash:
        raise TranscriptionError("MODEL_HASH_MISMATCH")
    if output.exists() and output.is_symlink():
        raise TranscriptionError("OUTPUT_SYMLINK")
    output.mkdir(parents=True, exist_ok=True)
    if output.is_symlink():
        raise TranscriptionError("OUTPUT_SYMLINK")
    return source, output, model_dir, dict(config), core_interval, window_interval


def _validate_result(result: Mapping[str, Any], request: Mapping[str, Any]) -> None:
    """Reject child output that is not bound to the exact chunk request."""

    if result.get("schema") != SCHEMA or result.get("chunk_id") != request.get("chunk_id"):
        raise TranscriptionError("CHUNK_RESULT_SCHEMA_INVALID")
    for key in ("source_media_hash", "model_bundle_sha256", "config_sha256", "global_offset_ms", "core_interval_ms", "window_interval_ms"):
        if result.get(key) != request.get(key):
            raise TranscriptionError("CHUNK_RESULT_BINDING_MISMATCH")
    if _beam_size(result.get("beam_size"), "BEAM_SIZE_MISSING") != _beam_size(request.get("beam_size"), "BEAM_SIZE_MISSING"):
        raise TranscriptionError("BEAM_SIZE_MISMATCH")
    state = result.get("observation_state")
    if state in {"OBSERVED", "SUSPICIOUS_TIMINGS"}:
        _hash64(result.get("source_audio_sha256"), "CHUNK_AUDIO_HASH_MISSING")
        if not isinstance(result.get("raw"), Mapping) or not isinstance(result.get("segments"), list):
            raise TranscriptionError("CHUNK_RESULT_SCHEMA_INVALID")
    elif state != "PARTIAL":
        raise TranscriptionError("CHUNK_RESULT_STATE_INVALID")


def _validate_cached_result(result: Mapping[str, Any], request: Mapping[str, Any], result_path: Path) -> None:
    """Validate a completed cache, including every persisted evidence file."""

    _validate_result(result, request)
    if result.get("observation_state") not in {"OBSERVED", "SUSPICIOUS_TIMINGS"}:
        return
    chunk_dir = result_path.parent
    artifacts = result.get("artifacts")
    hashes = result.get("artifact_hashes")
    if not isinstance(artifacts, Mapping) or not isinstance(hashes, Mapping):
        raise TranscriptionError("CHUNK_ARTIFACT_BINDING_MISSING")
    if result.get("request_sha256") is None:
        raise TranscriptionError("CHUNK_REQUEST_HASH_MISSING")
    for key in ("audio", "raw", "request"):
        if key not in artifacts or key not in hashes:
            raise TranscriptionError("CHUNK_ARTIFACT_BINDING_MISSING")
        path = _contained_path(chunk_dir, artifacts[key], "CHUNK_ARTIFACT_PATH_INVALID")
        if path.is_symlink() or not path.is_file():
            raise TranscriptionError("CHUNK_ARTIFACT_MISSING")
        if digest(path) != hashes[key]:
            raise TranscriptionError("CHUNK_ARTIFACT_HASH_MISMATCH")
    audio_path = _contained_path(chunk_dir, artifacts["audio"], "CHUNK_ARTIFACT_PATH_INVALID")
    raw_path = _contained_path(chunk_dir, artifacts["raw"], "CHUNK_ARTIFACT_PATH_INVALID")
    request_path = _contained_path(chunk_dir, artifacts["request"], "CHUNK_ARTIFACT_PATH_INVALID")
    if result.get("source_audio_sha256") != digest(audio_path) or result.get("raw_transcript_sha256") != digest(raw_path):
        raise TranscriptionError("CHUNK_ARTIFACT_HASH_MISMATCH")
    try:
        persisted_raw = json.loads(raw_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise TranscriptionError("CHUNK_RAW_ARTIFACT_INVALID") from None
    if persisted_raw != result.get("raw"):
        raise TranscriptionError("CHUNK_RAW_RESULT_MISMATCH")
    digest_sidecar = result_path.with_name("chunk-result.sha256")
    if digest_sidecar.is_symlink() or not digest_sidecar.is_file() or digest_sidecar.read_text(encoding="ascii").strip() != digest(result_path):
        raise TranscriptionError("CHUNK_RESULT_HASH_MISMATCH")
    try:
        persisted_request = json.loads(request_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise TranscriptionError("CHUNK_REQUEST_ARTIFACT_INVALID") from None
    if not isinstance(persisted_request, Mapping) or persisted_request.get("request_sha256") != result.get("request_sha256"):
        raise TranscriptionError("CHUNK_REQUEST_HASH_MISMATCH")
    if object_hash({key: value for key, value in persisted_request.items() if key != "request_sha256"}) != persisted_request.get("request_sha256"):
        raise TranscriptionError("CHUNK_REQUEST_HASH_MISMATCH")
    for key in ("chunk_id", "source_media_hash", "model_bundle_sha256", "config_sha256", "beam_size", "global_offset_ms", "core_interval_ms", "window_interval_ms"):
        if persisted_request.get(key) != request.get(key):
            raise TranscriptionError("CHUNK_REQUEST_BINDING_MISMATCH")


def _run(request: Mapping[str, Any]) -> dict[str, Any]:
    source, output, model_dir, config, core, window = _validate_request(request)
    source_hash = request["source_media_hash"]
    if request.get("original_audio_unknown") is True:
        return _failure(request, "ORIGINAL_AUDIO_UNKNOWN_REQUIRES_AUDIO_SOURCE_PROOF", asr_execution=False)
    audio_partial = output / "chunk-audio.wav.partial"
    audio = output / "chunk-audio.wav"
    raw_path = output / "chunk-raw.json"
    result_path = output / "chunk-result.json"
    if any(path.exists() or path.is_symlink() for path in (audio, raw_path, result_path)):
        raise TranscriptionError("OUTPUT_ALREADY_EXISTS")
    ffmpeg_args = [
        "ffmpeg", "-v", "error", "-nostdin", "-n", "-threads", "2", "-filter_threads", "2", "-filter_complex_threads", "2",
        "-protocol_whitelist", "file,pipe", "-ss", f"{window[0] / 1000:.3f}", "-i", str(source), "-map", "0:a:0",
        "-t", f"{(window[1] - window[0]) / 1000:.3f}", "-af", "asetpts=PTS-STARTPTS", "-ac", "1", "-ar", "16000",
        "-c:a", "pcm_s16le", "-f", "wav", "-fs", str(MAX_AUDIO_BYTES), str(audio_partial),
    ]
    try:
        ffmpeg = bounded_process(ffmpeg_args, timeout=CHUNK_TIMEOUT_SECONDS, stdout_limit=64 * 1024, stderr_limit=64 * 1024, rss_limit_bytes=FFMPEG_RSS_WATCHDOG_BYTES)
    except (ProcessBudgetError, TimeoutError) as exc:
        return _failure(request, str(exc), asr_execution=False, resource_receipt={"phase": "audio_decode", "rss_watchdog_bytes": FFMPEG_RSS_WATCHDOG_BYTES, "measurement_state": "UNAVAILABLE_ON_EXCEPTION"})
    if ffmpeg.get("returncode") != 0 or not audio_partial.is_file():
        return _failure(request, "AUDIO_DECODE_FAILED", asr_execution=False, resource_receipt={"phase": "audio_decode", "returncode": ffmpeg.get("returncode"), "elapsed_seconds": ffmpeg.get("elapsed_seconds"), "sampled_peak_rss_bytes": ffmpeg.get("sampled_peak_rss_bytes"), "rss_watchdog_limit_bytes": ffmpeg.get("rss_watchdog_limit_bytes"), "rss_poll_seconds": ffmpeg.get("rss_poll_seconds"), "measurement_state": "OBSERVED"})
    audio_bytes = audio_partial.stat().st_size
    if audio_bytes <= 44 or audio_bytes > MAX_AUDIO_BYTES:
        return _failure(request, "AUDIO_WINDOW_EMPTY_UNVERIFIED", asr_execution=False, resource_receipt={"phase": "audio_decode", "bytes": audio_bytes, "elapsed_seconds": ffmpeg.get("elapsed_seconds"), "sampled_peak_rss_bytes": ffmpeg.get("sampled_peak_rss_bytes"), "rss_watchdog_limit_bytes": ffmpeg.get("rss_watchdog_limit_bytes"), "measurement_state": "OBSERVED"})
    audio_partial.replace(audio)
    audio_hash = digest(audio)
    if digital_silence(audio):
        return _failure(request, "DIGITAL_SILENCE_REVIEW_REQUIRED", source_audio_sha256=audio_hash, asr_execution=False, resource_receipt={"phase": "silence_preflight", "bytes": audio_bytes, "elapsed_seconds": ffmpeg.get("elapsed_seconds"), "sampled_peak_rss_bytes": ffmpeg.get("sampled_peak_rss_bytes"), "rss_watchdog_limit_bytes": ffmpeg.get("rss_watchdog_limit_bytes"), "measurement_state": "OBSERVED"})
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(str(model_dir), device="cpu", compute_type="int8", cpu_threads=2, num_workers=1, local_files_only=True)
        segments, info = model.transcribe(str(audio), language=None, word_timestamps=True, beam_size=config["beam_size"])
        raw_segments = []
        for segment in segments:
            words = []
            for word in segment.words or []:
                words.append({"start": float(word.start), "end": float(word.end), "word": str(word.word), "probability": word.probability})
            raw_segments.append({"start": float(segment.start), "end": float(segment.end), "text": str(segment.text), "words": words})
        raw = {"language": getattr(info, "language", None), "language_probability": getattr(info, "language_probability", None), "segments": raw_segments, "parameters": {"language": "auto", "beam_size": config["beam_size"], "word_timestamps": True, "device": "cpu", "compute_type": "int8", "cpu_threads": 2, "num_workers": 1}}
    except (ImportError, AttributeError, TypeError, ValueError, OSError, RuntimeError):
        return _failure(request, "ASR_EXECUTION_FAILED", source_audio_sha256=audio_hash, asr_execution=True, resource_receipt={"phase": "asr", "audio_decode_elapsed_seconds": ffmpeg.get("elapsed_seconds"), "audio_decode_sampled_peak_rss_bytes": ffmpeg.get("sampled_peak_rss_bytes"), "audio_decode_rss_watchdog_limit_bytes": ffmpeg.get("rss_watchdog_limit_bytes"), "measurement_state": "OBSERVED"})
    _json_write(raw_path, raw)
    chunk_record = {"duration_ms": window[1] - window[0], "sha256": source_hash, "timebase_provenance": {"audio_offset_ms": 0}}
    normalized = _normalize_raw(raw, chunk_record)
    result = dict(normalized)
    result.update({"schema": SCHEMA, "chunk_id": request["chunk_id"], "source_media_hash": source_hash, "source_audio_sha256": audio_hash, "model_bundle_sha256": request["model_bundle_sha256"], "config_sha256": request["config_sha256"], "beam_size": config["beam_size"], "global_offset_ms": request["global_offset_ms"], "core_interval_ms": request["core_interval_ms"], "window_interval_ms": request["window_interval_ms"], "raw": raw, "raw_transcript_sha256": digest(raw_path), "artifacts": {"audio": audio.name, "raw": raw_path.name}, "resource_receipt": {"phase": "asr", "ffmpeg_threads": 2, "rss_watchdog_bytes": int(1.5 * 1024 * 1024 * 1024), "audio_decode_elapsed_seconds": ffmpeg.get("elapsed_seconds"), "audio_decode_sampled_peak_rss_bytes": ffmpeg.get("sampled_peak_rss_bytes"), "audio_decode_rss_watchdog_limit_bytes": ffmpeg.get("rss_watchdog_limit_bytes"), "measurement_state": "OBSERVED"}})
    _validate_result(result, request)
    _json_write(result_path, result)
    return result


def worker(request_path: str | Path) -> dict[str, Any]:
    request_path = Path(request_path)
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
        if not isinstance(request, Mapping):
            raise TranscriptionError("CHUNK_REQUEST_INVALID")
        result = _run(request)
        output = Path(request["output"])
        if not (output / "chunk-result.json").is_file():
            _json_write(output / "chunk-result.json", result)
        if result.get("observation_state") in {"OBSERVED", "SUSPICIOUS_TIMINGS"}:
            result = _finalize_completed_result(result, request, request_path, output)
    except (TranscriptionError, ProcessBudgetError, TimeoutError) as exc:
        request = request if "request" in locals() and isinstance(request, Mapping) else {}
        result = _failure(request, str(exc), asr_execution=False)
        try:
            output = Path(request["output"])
            output.mkdir(parents=True, exist_ok=True)
            _json_write(output / "chunk-result.json", result)
        except (KeyError, OSError, TranscriptionError, TypeError):
            pass
    return result


def production_chunk_runner(
    request: Mapping[str, Any],
    *,
    output_root: str | Path,
    source_root: str | Path,
    model_dir: str | Path,
    python_executable: str | Path = sys.executable,
) -> dict[str, Any]:
    """Start one concrete offline worker, or resume its hash-bound result."""

    from .transcription_recovery import object_hash

    root = Path(output_root).absolute()
    _reject_symlink_ancestors(root)
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise TranscriptionError("OUTPUT_DIRECTORY_INVALID")
    root.mkdir(parents=True, exist_ok=True)
    chunk_id = request["chunk_id"]
    if not isinstance(chunk_id, str) or not CHUNK_ID_RE.fullmatch(chunk_id):
        raise TranscriptionError("CHUNK_ID_INVALID")
    chunk_parent = root / chunk_id
    if chunk_parent.is_symlink() or (chunk_parent.exists() and not chunk_parent.is_dir()):
        raise TranscriptionError("CHUNK_OUTPUT_INVALID")
    if chunk_parent.exists():
        if any(item.is_symlink() for item in chunk_parent.iterdir()):
            raise TranscriptionError("CHUNK_OUTPUT_INVALID")
        candidates = [chunk_parent]
        candidates.extend(sorted((item for item in chunk_parent.iterdir() if item.is_dir() and re.fullmatch(r"attempt-[0-9]{4}", item.name)), key=lambda item: item.name, reverse=True))
        for candidate in candidates:
            result_path = candidate / "chunk-result.json"
            if result_path.is_file() and not result_path.is_symlink():
                try:
                    result = json.loads(result_path.read_text(encoding="utf-8"))
                    if isinstance(result, Mapping):
                        _validate_cached_result(result, request, result_path)
                        receipt, receipt_sha256 = _load_parent_resource_receipt(candidate)
                        if receipt is not None and receipt_sha256 is not None:
                            return _attach_parent_resource_receipt(result, receipt, receipt_sha256)
                        cached = dict(result)
                        cached["parent_resource_receipt_state"] = "NOT_AVAILABLE_PRE_R6"
                        return cached
                except (OSError, UnicodeError, json.JSONDecodeError, TranscriptionError):
                    continue
        attempt_numbers = [int(item.name[8:]) for item in chunk_parent.iterdir() if item.is_dir() and re.fullmatch(r"attempt-[0-9]{4}", item.name)]
        attempt = max(attempt_numbers, default=1) + 1
        chunk_dir = chunk_parent / f"attempt-{attempt:04d}"
        chunk_dir.mkdir()
    else:
        chunk_parent.mkdir()
        chunk_dir = chunk_parent
    _reject_symlink_ancestors(chunk_dir)
    result_path = chunk_dir / "chunk-result.json"
    full_request = dict(request)
    full_request.update({"source_root": str(Path(source_root).absolute()), "source_pointer": request.get("source_pointer"), "model_dir": str(Path(model_dir).absolute()), "output": str(chunk_dir.absolute())})
    full_request["request_sha256"] = object_hash({key: value for key, value in full_request.items() if key != "request_sha256"})
    request_path = chunk_dir / "chunk-request.json"
    _json_write(request_path, full_request)
    started = time.monotonic()
    try:
        process = bounded_process([str(python_executable), "-m", "m2_orchestrator.transcription_chunk_worker", "--worker", str(request_path)], timeout=CHUNK_TIMEOUT_SECONDS, stdout_limit=64 * 1024, stderr_limit=64 * 1024, env={"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1"}, rss_limit_bytes=int(1.5 * 1024 * 1024 * 1024))
    except (ProcessBudgetError, TimeoutError) as exc:
        receipt = _resource_receipt(None, phase="child", elapsed_seconds=time.monotonic() - started, failure_code=str(exc))
        receipt, receipt_sha256 = _persist_parent_resource_receipt(chunk_dir, receipt)
        result = _failure(full_request, str(exc), asr_execution=None, resource_receipt=receipt)
        _json_write(result_path, result)
        return _attach_parent_resource_receipt(result, receipt, receipt_sha256)
    receipt = _resource_receipt(process, phase="child")
    receipt, receipt_sha256 = _persist_parent_resource_receipt(chunk_dir, receipt)
    if not result_path.is_file() or result_path.is_symlink():
        result = _failure(full_request, "WORKER_OUTPUT_MISSING", asr_execution=False, resource_receipt=receipt)
        _json_write(result_path, result)
        return _attach_parent_resource_receipt(result, receipt, receipt_sha256)
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        result = _failure(full_request, "WORKER_OUTPUT_INVALID", asr_execution=False, resource_receipt=receipt)
        _json_write(result_path, result, overwrite=True)
        return _attach_parent_resource_receipt(result, receipt, receipt_sha256)
    if not isinstance(result, Mapping):
        result = _failure(full_request, "WORKER_OUTPUT_INVALID", asr_execution=False, resource_receipt=receipt)
    elif process.get("returncode") != 0 and result.get("observation_state") in {"OBSERVED", "SUSPICIOUS_TIMINGS"}:
        result = _failure(full_request, "WORKER_NONZERO_EXIT", source_audio_sha256=result.get("source_audio_sha256"), asr_execution=False, resource_receipt=receipt)
    else:
        try:
            _validate_cached_result(result, full_request, result_path)
        except TranscriptionError as exc:
            result = _failure(full_request, str(exc), asr_execution=False, resource_receipt=receipt)
            _json_write(result_path, result, overwrite=True)
    return _attach_parent_resource_receipt(result, receipt, receipt_sha256)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("request")
    args = parser.parse_args(argv)
    if not args.worker:
        return 2
    result = worker(args.request)
    print(json.dumps({"schema": SCHEMA, "chunk_id": result.get("chunk_id"), "observation_state": result.get("observation_state"), "failure_code": result.get("failure_code")}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())


__all__ = ["production_chunk_runner", "worker"]
