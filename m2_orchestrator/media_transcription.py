"""Bounded local Faster-Whisper transcription for an observed media record.

The public callable starts one isolated child process.  The child validates the
same frozen model bundle, decodes audio with bounded FFmpeg, and runs only a
local Faster-Whisper model.  No package install, model download, network call,
or provider client is available on this path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .process_budget import ProcessBudgetError, bounded_process


SCHEMA = "m2.transcript-evidence.v1"
MODEL_MANIFEST_NAMES = (
    "model-hash-manifest.json",
    "model_hash_manifest.json",
    "hash-manifest.json",
)
MAX_PROCESS_SECONDS = 900
MAX_STDOUT_BYTES = 64 * 1024
MAX_STDERR_BYTES = 64 * 1024
MAX_RAW_JSON_BYTES = 8 * 1024 * 1024
MAX_AUDIO_BYTES = 64 * 1024 * 1024
RSS_WATCHDOG_BYTES = int(1.5 * 1024 * 1024 * 1024)
FFMPEG_RSS_WATCHDOG_BYTES = 512 * 1024 * 1024
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class TranscriptionError(ValueError):
    """Stable, public-safe worker error code."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def object_hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def digest(path: str | Path) -> str:
    hasher = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    payload = _canonical(value) + b"\n"
    if len(payload) > MAX_RAW_JSON_BYTES:
        raise TranscriptionError("OUTPUT_JSON_LIMIT")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    if temporary.exists():
        raise TranscriptionError("OUTPUT_PARTIAL_EXISTS")
    temporary.write_bytes(payload)
    temporary.replace(path)


def _safe_relative(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or "\\" in relative:
        raise TranscriptionError("INVALID_MEDIA_POINTER")
    base = root.resolve(strict=True)
    candidate = (base / relative).resolve(strict=True)
    if ".." in Path(relative).parts or not candidate.is_relative_to(base) or not candidate.is_file():
        raise TranscriptionError("MEDIA_OUTSIDE_ROOT")
    return candidate


def _model_manifest_path(model_dir: Path) -> Path:
    for name in MODEL_MANIFEST_NAMES:
        candidate = model_dir / name
        if candidate.is_file() and not candidate.is_symlink():
            return candidate
    raise TranscriptionError("MODEL_HASH_MANIFEST_UNAVAILABLE")


def _manifest_entries(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, Mapping):
        raise TranscriptionError("MODEL_HASH_MANIFEST_INVALID")
    values = payload.get("files", payload.get("entries"))
    if not isinstance(values, list) or not values:
        raise TranscriptionError("MODEL_HASH_MANIFEST_INVALID")
    return values


def validate_model_bundle(model_dir: str | Path) -> dict[str, Any]:
    """Validate a frozen local model directory and return its hash receipt."""

    root = Path(model_dir)
    try:
        root = root.resolve(strict=True)
    except OSError:
        raise TranscriptionError("MODEL_DIRECTORY_UNAVAILABLE") from None
    if not root.is_dir():
        raise TranscriptionError("MODEL_DIRECTORY_UNAVAILABLE")
    manifest_path = _model_manifest_path(root)
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        rows = _manifest_entries(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        raise TranscriptionError("MODEL_HASH_MANIFEST_INVALID") from None

    listed: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise TranscriptionError("MODEL_HASH_MANIFEST_INVALID")
        relative = row.get("path", row.get("relative_path"))
        checksum = row.get("sha256")
        if (
            not isinstance(relative, str)
            or not relative
            or Path(relative).is_absolute()
            or "\\" in relative
            or ".." in Path(relative).parts
            or not isinstance(checksum, str)
            or not HEX64.fullmatch(checksum)
        ):
            raise TranscriptionError("MODEL_HASH_MANIFEST_INVALID")
        if relative in listed:
            raise TranscriptionError("MODEL_HASH_MANIFEST_DUPLICATE")
        try:
            candidate = (root / relative).resolve(strict=True)
        except OSError:
            raise TranscriptionError("MODEL_FILE_UNAVAILABLE") from None
        if not candidate.is_file() or not candidate.is_relative_to(root):
            raise TranscriptionError("MODEL_FILE_OUTSIDE_ROOT")
        try:
            actual = digest(candidate)
        except OSError:
            raise TranscriptionError("MODEL_FILE_UNAVAILABLE") from None
        if actual != checksum:
            raise TranscriptionError("MODEL_FILE_HASH_MISMATCH")
        listed[relative] = checksum

    # A frozen manifest must cover every regular file in its explicit model
    # directory.  This catches accidental model replacement or untracked
    # tokenizer/config additions before inference starts.
    discovered: set[str] = set()
    try:
        paths = sorted(root.rglob("*"), key=lambda p: p.as_posix())
    except OSError:
        raise TranscriptionError("MODEL_DIRECTORY_UNAVAILABLE") from None
    for path in paths:
        if not path.is_file():
            continue
        try:
            resolved = path.resolve(strict=True)
            if not resolved.is_relative_to(root):
                raise TranscriptionError("MODEL_FILE_OUTSIDE_ROOT")
            relative = path.relative_to(root).as_posix()
        except (OSError, ValueError):
            raise TranscriptionError("MODEL_FILE_OUTSIDE_ROOT") from None
        if relative == manifest_path.relative_to(root).as_posix():
            continue
        discovered.add(relative)
    if discovered != set(listed):
        raise TranscriptionError("MODEL_HASH_MANIFEST_INCOMPLETE")
    try:
        manifest_sha256 = digest(manifest_path)
    except OSError:
        raise TranscriptionError("MODEL_HASH_MANIFEST_UNAVAILABLE") from None
    return {
        "model_dir": str(root),
        "manifest_path": manifest_path.name,
        "manifest_sha256": manifest_sha256,
        "files": [{"path": path, "sha256": listed[path]} for path in sorted(listed)],
        "bundle_sha256": object_hash({"manifest_sha256": manifest_sha256, "files": listed}),
    }


def _rights_and_source(root: Path, record: Mapping[str, Any]) -> Path:
    if record.get("observation_state") != "OBSERVED":
        raise TranscriptionError("MEDIA_NOT_OBSERVED")
    if record.get("source_kind") != "approved_research_copy":
        raise TranscriptionError("APPROVED_RESEARCH_COPY_REQUIRED")
    rights = record.get("rights")
    if not isinstance(rights, Mapping) or rights.get("analysis_allowed") is not True or not rights.get("receipt_id"):
        raise TranscriptionError("RIGHTS_BLOCKED")
    media_hash = record.get("sha256")
    if not isinstance(media_hash, str) or not HEX64.fullmatch(media_hash):
        raise TranscriptionError("MEDIA_HASH_MISSING")
    source = _safe_relative(root, record.get("source_pointer"))
    if digest(source) != media_hash:
        raise TranscriptionError("MEDIA_HASH_MISMATCH")
    return source


def _validate_duration(record: Mapping[str, Any]) -> int:
    duration_ms = record.get("duration_ms")
    if type(duration_ms) is not int or not 0 < duration_ms <= 600_000:
        raise TranscriptionError("MEDIA_DURATION_INVALID")
    return duration_ms


def _config(model_receipt: Mapping[str, Any], media_hash: str, duration_ms: int | None = None) -> dict[str, Any]:
    return {
        "schema": "m2.transcription-config.v1",
        "media_sha256": media_hash,
        "duration_ms": duration_ms,
        "model_bundle_sha256": model_receipt["bundle_sha256"],
        "language": "auto",
        "beam_size": 5,
        "word_timestamps": True,
        "cpu_threads": 2,
        "num_workers": 1,
        "compute_type": "int8",
        "device": "cpu",
        "ffmpeg_threads": 2,
        "max_timeout_seconds": MAX_PROCESS_SECONDS,
        "output_limits": {"stdout_bytes": MAX_STDOUT_BYTES, "stderr_bytes": MAX_STDERR_BYTES, "audio_bytes": MAX_AUDIO_BYTES},
        "rss_watchdog_bytes": RSS_WATCHDOG_BYTES,
    }


def _attempt(state: str, failure_code: str | None = None, **data: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "modality": "transcript",
        "observation_state": state,
        "failure_code": failure_code,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "review_state": "NOT_REVIEWED",
        "provider_execution": False,
        **data,
    }


def _serialize_segment(segment: Any) -> dict[str, Any]:
    try:
        words = []
        for word in segment.words or []:
            words.append({"start": float(word.start), "end": float(word.end), "word": str(word.word), "probability": word.probability})
        return {"start": float(segment.start), "end": float(segment.end), "text": str(segment.text), "words": words}
    except (AttributeError, TypeError, ValueError, OverflowError):
        raise TranscriptionError("ASR_OUTPUT_INVALID") from None


def _normalize_raw(raw: Mapping[str, Any], record: Mapping[str, Any]) -> dict[str, Any]:
    segments = raw.get("segments")
    if not isinstance(segments, list):
        raise TranscriptionError("ASR_OUTPUT_INVALID")
    if not segments:
        return _attempt(
            "EMPTY_OUTPUT_UNVERIFIED",
            "EMPTY_ASR_NOT_PROOF_OF_SILENCE",
            segments=[],
            words=0,
            language=raw.get("language"),
            word_timing="UNAVAILABLE",
            source_media_hash=record["sha256"],
            asr_execution=True,
            no_speech_confirmed=False,
        )
    duration_ms = record.get("duration_ms")
    try:
        if type(duration_ms) is not int or duration_ms <= 0:
            raise ValueError
        offset = (record.get("timebase_provenance") or {}).get("audio_offset_ms") or 0
        if type(offset) is not int:
            raise ValueError
        normalized: list[dict[str, Any]] = []
        previous_end = -1
        suspicious = False
        lexical_word_count = 0
        aligned_word_count = 0
        unaligned_word_count = 0
        timing_issues: list[str] = []
        for index, item in enumerate(segments):
            if not isinstance(item, Mapping):
                raise ValueError
            start = float(item["start"])
            end = float(item["end"])
            if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
                raise ValueError
            start_ms = round(start * 1000) + offset
            end_ms = round(end * 1000) + offset
            if not 0 <= start_ms < end_ms <= duration_ms:
                raise ValueError
            if start_ms < previous_end:
                suspicious = True
                if "OVERLAPPING_SEGMENTS_REVIEW_REQUIRED" not in timing_issues:
                    timing_issues.append("OVERLAPPING_SEGMENTS_REVIEW_REQUIRED")
            previous_end = end_ms
            text = item.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            words = []
            unaligned_words = []
            raw_word_records = []
            raw_words = item.get("words", []) or []
            if not isinstance(raw_words, list):
                raise ValueError
            for word_index, word in enumerate(raw_words):
                lexical_word_count += 1
                reason = None
                if not isinstance(word, Mapping):
                    reason = "UNALIGNED_WORD_MALFORMED"
                    raw_word = {"value": str(type(word).__name__)}
                else:
                    raw_word = dict(word)
                    try:
                        ws, we = float(word["start"]), float(word["end"])
                        if not math.isfinite(ws) or not math.isfinite(we):
                            reason = "UNALIGNED_WORD_INVALID_TIME"
                        elif ws == we:
                            reason = "ZERO_DURATION_WORD"
                        elif we < ws:
                            reason = "UNALIGNED_WORD_REVERSED"
                        else:
                            wsm, wem = round(ws * 1000) + offset, round(we * 1000) + offset
                            if not start_ms <= wsm < wem <= end_ms:
                                reason = "UNALIGNED_WORD_OUT_OF_BOUNDS"
                    except (KeyError, TypeError, ValueError, OverflowError):
                        reason = "UNALIGNED_WORD_INVALID_TIME"
                raw_word_records.append(raw_word)
                if reason is not None:
                    unaligned_word = {"word_index": word_index, "reason": reason, "raw": raw_word}
                    unaligned_words.append(unaligned_word)
                    unaligned_word_count += 1
                    if reason != "ZERO_DURATION_WORD":
                        suspicious = True
                        if reason not in timing_issues:
                            timing_issues.append(reason)
                    continue
                words.append({"start_ms": wsm, "end_ms": wem, "text": str(word.get("word", "")), "confidence": word.get("probability")})
                aligned_word_count += 1
            normalized.append({
                "segment_id": f"T{index + 1:05}",
                "start_ms": start_ms,
                "end_ms": end_ms,
                "text": text.strip(),
                "raw_start_seconds": start,
                "raw_end_seconds": end,
                "words": words,
                "raw_words": raw_word_records,
                "unaligned_words": unaligned_words,
            })
        if not normalized:
            return _attempt("EMPTY_OUTPUT_UNVERIFIED", "EMPTY_ASR_NOT_PROOF_OF_SILENCE", segments=[], words=0, source_media_hash=record["sha256"], asr_execution=True, no_speech_confirmed=False)
        result = _attempt(
            "SUSPICIOUS_TIMINGS" if suspicious else "OBSERVED",
            "TIMING_REVIEW_REQUIRED" if suspicious else None,
            segments=normalized,
            words=lexical_word_count,
            raw_word_count=lexical_word_count,
            lexical_word_count=lexical_word_count,
            aligned_word_count=aligned_word_count,
            unaligned_word_count=unaligned_word_count,
            timing_issues=timing_issues,
            language=raw.get("language"),
            word_timing="PARTIAL" if unaligned_word_count and aligned_word_count else "OBSERVED" if aligned_word_count else "UNAVAILABLE",
            source_media_hash=record["sha256"],
            asr_execution=True,
            no_speech_confirmed=False,
        )
        return result
    except (KeyError, TypeError, ValueError, OverflowError):
        raise TranscriptionError("ASR_TIMINGS_INVALID") from None


def _worker(request_path: Path) -> dict[str, Any]:
    asr_attempted = False
    media_hash: str | None = None
    model_receipt: dict[str, Any] | None = None
    config_sha256: str | None = None
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
        if not isinstance(request, Mapping):
            raise TranscriptionError("WORKER_REQUEST_INVALID")
        root = Path(request["root"]).resolve(strict=True)
        output = Path(request["output"]).resolve()
        record = request["record"]
        if not isinstance(record, Mapping):
            raise TranscriptionError("WORKER_REQUEST_INVALID")
        model_receipt = validate_model_bundle(request["model_dir"])
        source = _rights_and_source(root, record)
        duration_ms = _validate_duration(record)
        media_hash = record["sha256"]
        config = _config(model_receipt, media_hash, duration_ms)
        expected_config = request.get("config_sha256")
        config_sha256 = object_hash(config)
        if expected_config != config_sha256:
            raise TranscriptionError("TRANSCRIPTION_CONFIG_MISMATCH")
        output.mkdir(parents=True, exist_ok=True)
        audio_partial = output / "normalized-audio.wav.partial"
        audio = output / "normalized-audio.wav"
        raw_path = output / "raw-transcript.json"
        result_path = output / "transcription.json"
        if audio.exists() or raw_path.exists() or result_path.exists():
            raise TranscriptionError("OUTPUT_ALREADY_EXISTS")
        ffmpeg = bounded_process(
            [
                "ffmpeg",
                "-v",
                "error",
                "-nostdin",
                "-n",
                "-threads",
                "2",
                "-filter_threads",
                "2",
                "-filter_complex_threads",
                "2",
                "-protocol_whitelist",
                "file,pipe",
                "-i",
                str(source),
                "-map",
                "0:a:0",
                "-t",
                f"{duration_ms / 1000:.3f}",
                "-af",
                "asetpts=PTS-STARTPTS",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                "-f",
                "wav",
                "-fs",
                str(MAX_AUDIO_BYTES),
                str(audio_partial),
            ],
            timeout=MAX_PROCESS_SECONDS,
            stdout_limit=MAX_STDOUT_BYTES,
            stderr_limit=MAX_STDERR_BYTES,
            rss_limit_bytes=FFMPEG_RSS_WATCHDOG_BYTES,
        )
        if ffmpeg["returncode"] != 0 or not audio_partial.is_file():
            raise TranscriptionError("AUDIO_DECODE_FAILED")
        if audio_partial.stat().st_size <= 44 or audio_partial.stat().st_size > MAX_AUDIO_BYTES:
            raise TranscriptionError("NORMALIZED_AUDIO_LIMIT")
        audio_partial.replace(audio)
        audio_hash = digest(audio)
        from m2_studio.media import digital_silence

        if digital_silence(audio):
            result = _attempt(
                "EMPTY_OUTPUT_UNVERIFIED",
                "DIGITAL_SILENCE_REVIEW_REQUIRED",
                segments=[],
                words=0,
                source_media_hash=media_hash,
                source_audio_sha256=audio_hash,
                model_sha256=model_receipt["bundle_sha256"],
                model_hash_manifest_sha256=model_receipt["manifest_sha256"],
                config_sha256=config_sha256,
                asr_execution=False,
                no_speech_confirmed=False,
                method="pcm_exact_zero_preflight",
            )
            result["artifacts"] = {"audio": audio.name}
            _write_json(result_path, result)
            return result

        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise TranscriptionError("FASTER_WHISPER_UNAVAILABLE") from None
        asr_attempted = True
        try:
            model = WhisperModel(str(Path(request["model_dir"]).resolve()), device="cpu", compute_type="int8", cpu_threads=2, num_workers=1, local_files_only=True)
            segments, info = model.transcribe(str(audio), language=None, word_timestamps=True, beam_size=5)
            raw_segments = [_serialize_segment(segment) for segment in segments]
            raw = {
                "language": getattr(info, "language", None),
                "language_probability": getattr(info, "language_probability", None),
                "segments": raw_segments,
                "parameters": {"language": "auto", "beam_size": 5, "word_timestamps": True, "cpu_threads": 2, "num_workers": 1, "device": "cpu", "compute_type": "int8"},
            }
        except (TranscriptionError, TypeError, ValueError, OSError, RuntimeError):
            raise TranscriptionError("ASR_EXECUTION_FAILED") from None
        _write_json(raw_path, raw)
        if raw_path.stat().st_size > MAX_RAW_JSON_BYTES:
            raise TranscriptionError("OUTPUT_JSON_LIMIT")
        # The duration was checked before decoding; retaining this local value
        # makes the bound explicit for reviewers of the child command.
        assert duration_ms == record["duration_ms"]
        result = _normalize_raw(raw, record)
        result.update(
            {
                "method": "faster_whisper_local",
                "model_sha256": model_receipt["bundle_sha256"],
                "model_hash_manifest_sha256": model_receipt["manifest_sha256"],
                "source_audio_sha256": audio_hash,
                "raw_transcript_sha256": digest(raw_path),
                "config_sha256": config_sha256,
                "parameters": raw["parameters"],
                "artifacts": {"audio": audio.name, "raw_json": raw_path.name},
            }
        )
        _write_json(result_path, result)
        return result
    except (TranscriptionError, ProcessBudgetError) as exc:
        failure_data: dict[str, Any] = {"asr_execution": asr_attempted}
        if media_hash:
            failure_data["source_media_hash"] = media_hash
        if model_receipt:
            failure_data["model_sha256"] = model_receipt["bundle_sha256"]
            failure_data["model_hash_manifest_sha256"] = model_receipt["manifest_sha256"]
        if config_sha256:
            failure_data["config_sha256"] = config_sha256
        result = _attempt("ASR_FAILED", str(exc), **failure_data)
        try:
            output = Path(request.get("output", ".")).resolve() if isinstance(request, Mapping) else None
            if output:
                output.mkdir(parents=True, exist_ok=True)
                _write_json(output / "transcription.json", result)
        except (OSError, TranscriptionError, AttributeError):
            pass
        return result


def transcribe(
    record: dict,
    root: Path,
    output: Path,
    python_executable: str | Path,
    model_dir: Path,
) -> dict:
    """Run one bounded local transcription child and return its evidence record."""

    root = Path(root).resolve()
    output = Path(output).resolve()
    if not root.is_dir():
        return _attempt("ASR_FAILED", "MEDIA_ROOT_UNAVAILABLE", asr_execution=False)
    try:
        source = _rights_and_source(root, record)
        media_hash = record["sha256"]
        if record.get("has_audio") is False:
            return _attempt("NOT_APPLICABLE", "NO_AUDIO_STREAM", source_media_hash=media_hash,
                            asr_execution=False, segments=[], word_timing="NOT_APPLICABLE",
                            no_speech_confirmed=False)
        model_receipt = validate_model_bundle(model_dir)
        config = _config(model_receipt, media_hash, _validate_duration(record))
        config_sha256 = object_hash(config)
        output.mkdir(parents=True, exist_ok=True)
        request_path = output / "worker-request.json"
        if request_path.exists():
            raise TranscriptionError("OUTPUT_ALREADY_EXISTS")
        _write_json(request_path, {"root": str(root), "output": str(output), "record": record, "model_dir": str(Path(model_dir).resolve()), "config_sha256": config_sha256})
        args = [str(python_executable), "-m", "m2_orchestrator.media_transcription", "--worker", str(request_path)]
        try:
            process = bounded_process(
                args,
                timeout=MAX_PROCESS_SECONDS,
                stdout_limit=MAX_STDOUT_BYTES,
                stderr_limit=MAX_STDERR_BYTES,
                env={"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1"},
                rss_limit_bytes=RSS_WATCHDOG_BYTES,
            )
        except ProcessBudgetError as exc:
            return _attempt("ASR_FAILED", str(exc), source_media_hash=media_hash, config_sha256=config_sha256, model_sha256=model_receipt["bundle_sha256"], model_hash_manifest_sha256=model_receipt["manifest_sha256"], asr_execution=None, execution_state="INTERRUPTED_PHASE_UNCONFIRMED", resource_receipt={"sampled_peak_rss_bytes": None, "rss_watchdog_limit_bytes": RSS_WATCHDOG_BYTES, "rss_claim": "sampled_watchdog_only"})
        result_path = output / "transcription.json"
        if result_path.is_file():
            try:
                result = json.loads(result_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                result = _attempt("ASR_FAILED", "WORKER_OUTPUT_INVALID", source_media_hash=media_hash, config_sha256=config_sha256, asr_execution=False)
        else:
            result = _attempt("ASR_FAILED", "WORKER_OUTPUT_MISSING", source_media_hash=media_hash, config_sha256=config_sha256, asr_execution=False)
        result["resource_receipt"] = {
            "elapsed_seconds": process.get("elapsed_seconds"),
            "sampled_peak_rss_bytes": process.get("sampled_peak_rss_bytes"),
            "rss_watchdog_limit_bytes": RSS_WATCHDOG_BYTES,
            "rss_claim": "sampled_watchdog_only",
            "stdout_bytes": len(process.get("stdout", b"")),
            "stderr_bytes": len(process.get("stderr", b"")),
            "returncode": process.get("returncode"),
        }
        if process.get("returncode") != 0 and result.get("observation_state") not in {"ASR_FAILED", "SUSPICIOUS_TIMINGS"}:
            result["observation_state"] = "ASR_FAILED"
            result["failure_code"] = "WORKER_NONZERO_EXIT"
        _write_json(output / "resource-receipt.json", result["resource_receipt"])
        return result
    except TranscriptionError as exc:
        return _attempt("ASR_FAILED", str(exc), asr_execution=False)
    except (OSError, TypeError, ValueError):
        return _attempt("ASR_FAILED", "WORKER_INPUT_INVALID", asr_execution=False)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("request")
    args = parser.parse_args(argv)
    if not args.worker:
        return 2
    result = _worker(Path(args.request))
    print(json.dumps({"schema": SCHEMA, "observation_state": result.get("observation_state"), "failure_code": result.get("failure_code")}, separators=(",", ":")))
    return 0 if result.get("observation_state") in {"OBSERVED", "EMPTY_OUTPUT_UNVERIFIED", "SUSPICIOUS_TIMINGS"} else 2


if __name__ == "__main__":
    raise SystemExit(_main())


__all__ = ["TranscriptionError", "digest", "object_hash", "transcribe", "validate_model_bundle"]
