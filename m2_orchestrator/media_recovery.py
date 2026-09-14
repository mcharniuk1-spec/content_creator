"""Bounded recovery for public video-only media sources.

The normal public resolver deliberately accepts only muxed MP4 formats.  Some
metadata exports contain a usable video-only MP4 instead.  This module keeps
that exceptional route separate from the frozen acquisition worker: metadata
is identity- and hash-bound, split streams fail closed, and a recovered
video-only file never implies that the original Reel had no speech or audio.

This module does not resolve URLs or merge DASH streams.  Callers provide
already captured metadata evidence and may inject download/probe functions in
tests.  The default functions are the existing bounded helpers.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping

from .media_acquisition import AcquisitionError, bounded_probe, digest, download, stable_hash, validate_url


_CODE_RE = re.compile(r"[A-Za-z0-9_-]{1,96}\Z")
_DEFAULT_ALLOWED_HOSTS = ("cdninstagram.com", "fbcdn.net")
MAX_METADATA_BYTES = 32 * 1024 * 1024
_SYSTEM_ALIASES = {Path("/tmp"), Path("/private/tmp"), Path("/var"), Path("/private/var")}
_PROBE_FIELDS = frozenset(
    {
        "duration_ms",
        "width",
        "height",
        "fps",
        "has_audio",
        "frame_pts_ms",
        "timebase_provenance",
        "probe_budget",
    }
)


def _metadata_bytes(metadata: Mapping[str, Any]) -> bytes:
    """Return deterministic UTF-8 bytes for an in-memory metadata object."""

    try:
        return json.dumps(metadata, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AcquisitionError("INVALID_METADATA") from exc


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _codec_present(value: Any) -> bool:
    """Treat yt-dlp's null/``none`` codec markers as absent."""

    return value is not None and str(value).strip().lower() not in {"", "none", "null"}


def _safe_probe_fields(value: Mapping[str, Any]) -> dict[str, Any]:
    """Keep only technical probe fields; provenance is recovery-owned."""

    if not isinstance(value, Mapping):
        raise AcquisitionError("PROBE_INVALID")
    return {key: value[key] for key in _PROBE_FIELDS if key in value}


def _candidate(item: Mapping[str, Any], code: str, route: str) -> dict[str, Any]:
    """Build a source candidate without trusting extractor-provided IDs."""

    url = item.get("url")
    # The parser validates the URL before this helper is called.  Keep the URL
    # in the private candidate so the recovery function can pass it to the
    # bounded downloader; public reports should use url_sha256 instead.
    return {
        "route": route,
        "url": url,
        "url_sha256": hashlib.sha256(url.encode("utf-8")).hexdigest(),
        "format_id": str(item.get("format_id")) if item.get("format_id") is not None else None,
        "source_code": code,
        "ext": item.get("ext"),
        "vcodec": item.get("vcodec"),
        "acodec": item.get("acodec"),
        "width": item.get("width"),
        "height": item.get("height"),
        "fps": item.get("fps"),
    }


def classify_metadata(
    code: str,
    data: Mapping[str, Any],
    *,
    allowed_hosts: tuple[str, ...] = _DEFAULT_ALLOWED_HOSTS,
) -> dict[str, Any]:
    """Classify safe MP4 sources from one identity-bound metadata object.

    The result has three source classes: ``muxed`` (video and audio are both
    advertised), ``video_only`` (video is advertised and audio is explicitly
    absent), and ``split_streams`` (a video-only and audio-only pair exists and
    would require a merge).  Audio-only formats are retained only as evidence
    for split detection and are never returned as video candidates.
    """

    if not isinstance(code, str) or not _CODE_RE.fullmatch(code):
        raise AcquisitionError("INVALID_CODE")
    if not isinstance(data, Mapping):
        raise AcquisitionError("INVALID_METADATA")
    identity_fields = [data[key] for key in ("id", "display_id") if key in data and data[key] is not None]
    if len(identity_fields) == 2 and identity_fields[0] != identity_fields[1]:
        raise AcquisitionError("EXTRACTOR_IDENTITY_MISMATCH")
    if not any(value == code for value in identity_fields):
        raise AcquisitionError("EXTRACTOR_IDENTITY_MISMATCH")
    formats = data.get("formats", [])
    if not isinstance(formats, list):
        raise AcquisitionError("INVALID_EXTRACTOR_FORMATS")

    metadata_sha256 = _sha256_bytes(_metadata_bytes(data))
    muxed: list[dict[str, Any]] = []
    video_only: list[dict[str, Any]] = []
    audio_only: list[dict[str, Any]] = []
    seen_by_class: dict[str, set[str]] = {"muxed": set(), "video_only": set(), "audio_only": set()}

    for raw in formats:
        if not isinstance(raw, Mapping):
            continue
        url = raw.get("url")
        if not isinstance(url, str):
            continue
        try:
            validate_url(url, allowed_hosts)
        except AcquisitionError:
            continue
        has_video = _codec_present(raw.get("vcodec"))
        has_audio = _codec_present(raw.get("acodec"))
        ext = str(raw.get("ext") or "").lower()
        # Recovery itself retains MP4 video only.  Audio-only m4a/webm/etc.
        # still count as split-stream evidence and must not be discarded.
        if has_video and has_audio and ext == "mp4":
            if url not in seen_by_class["muxed"]:
                muxed.append(_candidate(raw, code, "muxed"))
                seen_by_class["muxed"].add(url)
        elif has_video and not has_audio and ext == "mp4":
            if url not in seen_by_class["video_only"]:
                video_only.append(_candidate(raw, code, "video_only_no_advertised_audio"))
                seen_by_class["video_only"].add(url)
        elif not has_video and has_audio:
            # This is evidence that a separate audio stream exists, never a
            # video source.  It is included only for the merge decision.
            if url not in seen_by_class["audio_only"]:
                audio_only.append(_candidate(raw, code, "audio_only"))
                seen_by_class["audio_only"].add(url)

    if muxed:
        selected = muxed[0]
        classification = "muxed"
    elif video_only and audio_only:
        selected = None
        classification = "split_streams_needing_merge"
    elif video_only:
        selected = video_only[0]
        classification = "video_only_with_no_advertised_audio"
    else:
        selected = None
        classification = "no_supported_video"

    return {
        "schema": "m2.media-recovery-format-classification.v1",
        "code": code,
        "metadata_sha256": metadata_sha256,
        "classification": classification,
        "selected": selected,
        "muxed": muxed,
        "video_only": video_only,
        "audio_only": audio_only,
        "audio_source_status": (
            "ADVERTISED" if classification == "muxed" else
            "NOT_ADVERTISED_UNKNOWN" if classification == "video_only_with_no_advertised_audio" else
            "SEPARATE_STREAM_REQUIRES_MERGE" if classification == "split_streams_needing_merge" else
            "UNKNOWN"
        ),
        "original_audio_unknown": classification == "video_only_with_no_advertised_audio",
        "source_completeness_flag": (
            "VIDEO_RETAINED_AUDIO_ORIGINAL_UNKNOWN"
            if classification == "video_only_with_no_advertised_audio"
            else "VIDEO_AUDIO_ADVERTISEMENT_PRESENT"
            if classification == "muxed"
            else "INCOMPLETE_OR_MERGE_REQUIRED"
        ),
    }


# Short aliases make the pure parser easy to discover for callers and tests.
parse_metadata = classify_metadata
classify_formats = classify_metadata


def _read_metadata(
    metadata: Mapping[str, Any] | str | os.PathLike[str],
) -> tuple[dict[str, Any], bytes, str, str | None]:
    """Load metadata and return object, bytes, hash, and source evidence path."""

    if isinstance(metadata, Mapping):
        data = dict(metadata)
        raw = _metadata_bytes(data)
        return data, raw, _sha256_bytes(raw), None
    try:
        path = Path(metadata)
        if path.is_symlink() or any(parent.is_symlink() for parent in path.absolute().parents) or not path.is_file():
            raise AcquisitionError("METADATA_EVIDENCE_INVALID")
        if path.stat().st_size > MAX_METADATA_BYTES:
            raise AcquisitionError("METADATA_SIZE_LIMIT")
        with path.open("rb") as handle:
            raw = handle.read(MAX_METADATA_BYTES + 1)
        if len(raw) > MAX_METADATA_BYTES:
            raise AcquisitionError("METADATA_SIZE_LIMIT")
        data = json.loads(raw.decode("utf-8"))
    except AcquisitionError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise AcquisitionError("METADATA_EVIDENCE_INVALID") from exc
    if not isinstance(data, Mapping):
        raise AcquisitionError("INVALID_METADATA")
    return dict(data), raw, _sha256_bytes(raw), str(path)


def _safe_dir(path: Path) -> Path:
    """Create a fresh private output directory while rejecting symlink traversal."""

    absolute = path.absolute()
    if absolute.is_symlink():
        raise AcquisitionError("OUTPUT_SYMLINK")
    for parent in absolute.parents:
        if parent.is_symlink() and parent not in _SYSTEM_ALIASES:
            raise AcquisitionError("OUTPUT_SYMLINK")
    if absolute.exists():
        raise AcquisitionError("OUTPUT_ALREADY_EXISTS")
    if not absolute.parent.is_dir():
        raise AcquisitionError("OUTPUT_PARENT_UNAVAILABLE")
    try:
        absolute.mkdir()
    except FileExistsError as exc:
        raise AcquisitionError("OUTPUT_ALREADY_EXISTS") from exc
    except OSError as exc:
        raise AcquisitionError("OUTPUT_DIRECTORY_INVALID") from exc
    if absolute.is_symlink() or not absolute.is_dir():
        raise AcquisitionError("OUTPUT_DIRECTORY_INVALID")
    return absolute


def recover_video(
    code: str,
    metadata: Mapping[str, Any] | str | os.PathLike[str],
    output_dir: str | os.PathLike[str],
    *,
    expected_metadata_sha256: str | None = None,
    allowed_hosts: tuple[str, ...] = _DEFAULT_ALLOWED_HOSTS,
    max_bytes: int = 128 * 1024 * 1024,
    timeout: float = 90,
    reserve_bytes: int = 5 * 1024**3,
    cache_bytes: int = 8 * 1024**3,
    rights: Mapping[str, Any] | None = None,
    download_fn: Callable[..., Mapping[str, Any]] | None = None,
    probe_fn: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Recover one video source into a new private directory.

    The function performs no metadata resolution and never merges streams.
    It downloads only a selected allowlisted URL through the existing bounded
    downloader, probes the retained file, and writes an immutable media record
    containing both media and metadata evidence hashes.
    """

    data, raw_metadata, metadata_sha256, evidence_path = _read_metadata(metadata)
    if expected_metadata_sha256 and metadata_sha256 != expected_metadata_sha256:
        raise AcquisitionError("METADATA_HASH_MISMATCH")
    classification = classify_metadata(code, data, allowed_hosts=allowed_hosts)
    if classification["classification"] == "split_streams_needing_merge":
        raise AcquisitionError("MERGE_REQUIRED_UNSUPPORTED")
    selected = classification.get("selected")
    if not selected:
        raise AcquisitionError("NO_SUPPORTED_VIDEO_FORMAT")
    if type(max_bytes) is not int or max_bytes <= 0 or type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise AcquisitionError("INVALID_LIMITS")
    if type(reserve_bytes) is not int or reserve_bytes < 0 or type(cache_bytes) is not int or cache_bytes <= 0:
        raise AcquisitionError("INVALID_LIMITS")

    output = _safe_dir(Path(output_dir))
    media_path = output / f"{code}.mp4"
    record_path = output / f"{code}.media.json"
    record_partial_path = output / f"{code}.media.json.partial"
    metadata_path = output / f"{code}.metadata.private.json"
    failure_path = output / f"{code}.failure.json"
    for target in (media_path, record_path, record_partial_path, metadata_path, failure_path):
        if target.exists() or target.is_symlink():
            raise AcquisitionError("OUTPUT_COLLISION" if not target.is_symlink() else "OUTPUT_SYMLINK")

    usage = shutil.disk_usage(output)
    if usage.free < reserve_bytes + max_bytes:
        raise AcquisitionError("STORAGE_BUDGET_STOP")
    if max_bytes > cache_bytes:
        raise AcquisitionError("STORAGE_BUDGET_STOP")
    rights_approved = (
        isinstance(rights, Mapping)
        and rights.get("analysis_allowed") is True
        and isinstance(rights.get("receipt_id"), str)
        and bool(rights.get("receipt_id"))
        and isinstance(rights.get("source_kind"), str)
        and rights.get("source_kind") == "approved_research_copy"
    )
    if rights is not None and not rights_approved:
        raise AcquisitionError("RIGHTS_BLOCKED")
    rights_receipt = dict(rights) if rights_approved else None
    rights_receipt_sha256 = stable_hash(rights_receipt) if rights_receipt is not None else None
    # Resolve defaults at call time so a bounded test harness or an explicit
    # recovery caller can replace either helper without touching this module's
    # frozen acquisition implementation.
    download_fn = download if download_fn is None else download_fn
    probe_fn = bounded_probe if probe_fn is None else probe_fn

    # Preserve the metadata evidence before acquiring media.  xb prevents an
    # accidental overwrite if a caller races another recovery invocation.
    try:
        with metadata_path.open("xb") as handle:
            handle.write(raw_metadata)
    except FileExistsError as exc:
        raise AcquisitionError("OUTPUT_COLLISION") from exc
    except OSError as exc:
        raise AcquisitionError("OUTPUT_WRITE_FAILED") from exc

    staging: Path | None = None
    staged_bytes: int | None = None
    source_sha256: str | None = None
    download_result: Mapping[str, Any] | None = None
    try:
        fd, temporary = tempfile.mkstemp(prefix=f"{code}-", suffix=".partial", dir=output)
        os.close(fd)
        staging = Path(temporary)
        staging.unlink()
        raw_download_result = download_fn(
            selected["url"],
            staging,
            allowed_hosts=allowed_hosts,
            max_bytes=max_bytes,
            timeout=timeout,
        )
        download_result = raw_download_result if isinstance(raw_download_result, Mapping) else None
        if not staging.is_file() or staging.is_symlink():
            raise AcquisitionError("DOWNLOAD_OUTPUT_INVALID")
        staged_bytes = staging.stat().st_size
        if staged_bytes <= 0:
            raise AcquisitionError("TRUNCATED_DOWNLOAD")
        if staged_bytes > max_bytes:
            raise AcquisitionError("DOWNLOAD_SIZE_LIMIT")
        if len(raw_metadata) + staged_bytes > cache_bytes:
            raise AcquisitionError("STORAGE_BUDGET_STOP")
        source_sha256 = digest(staging)
        probe = _safe_probe_fields(probe_fn(staging))
        if digest(staging) != source_sha256:
            raise AcquisitionError("SOURCE_CHANGED_DURING_PROBE")
        if media_path.exists() or media_path.is_symlink():
            raise AcquisitionError("OUTPUT_COLLISION" if not media_path.is_symlink() else "OUTPUT_SYMLINK")
        staging.replace(media_path)
        if classification["classification"] == "video_only_with_no_advertised_audio":
            audio_source_status = "NOT_ADVERTISED_UNKNOWN"
            original_audio_status = "UNKNOWN"
            speech_state = "UNKNOWN"
            audio_reason = "source_advertises_video_only; original_audio_and_speech_are_unverified"
            probe["retained_media_has_audio"] = probe.get("has_audio")
            probe["has_audio"] = None
            transcription_eligibility = "UNKNOWN_ORIGINAL_AUDIO"
        else:
            audio_source_status = "ADVERTISED_AND_PROBED"
            original_audio_status = "PRESENT_IN_RETAINED_MEDIA" if probe.get("has_audio") else "ABSENT_IN_RETAINED_MEDIA"
            speech_state = "UNKNOWN"
            audio_reason = "speech_content_requires_separate_audio_or_transcript_evidence"
            transcription_eligibility = "RETAINED_MEDIA_AUDIO_PROBED"
        record = {
            "schema": "m2.recovered-media.v1",
            "media_id": code,
            "reel_id": f"instagram:{code}",
            "observation_state": "OBSERVED",
            "source_pointer": media_path.name,
            "sha256": source_sha256,
            "source_hash": source_sha256,
            "route": "public_video_only_recovery" if classification["classification"] == "video_only_with_no_advertised_audio" else "public_muxed_recovery",
            "source_route_hash": stable_hash({"route": selected["route"], "url_sha256": selected["url_sha256"]}),
            "review_state": "NOT_REVIEWED",
            "speech_state": speech_state,
            "transcription_eligibility": transcription_eligibility,
            "rights_state": "APPROVED" if rights_approved else "REQUIRED",
            "analysis_ready": rights_approved,
            "rights_required_for_frames_and_asr": True,
            "source_kind": rights.get("source_kind") if rights_approved else None,
            "rights_receipt": rights_receipt,
            "rights_receipt_sha256": rights_receipt_sha256,
            "audio_source_status": audio_source_status,
            "original_audio_status": original_audio_status,
            "original_audio_unknown": original_audio_status == "UNKNOWN",
            "source_completeness_flag": (
                "VIDEO_RETAINED_AUDIO_ORIGINAL_UNKNOWN"
                if original_audio_status == "UNKNOWN" else "VIDEO_AUDIO_ADVERTISEMENT_PRESENT"
            ),
            "audio_status_reason": audio_reason,
            "format_classification": classification["classification"],
            "source_format": {k: v for k, v in selected.items() if k != "url"},
            "source_completeness": {
                "video": "RETAINED_AND_PROBED",
                "audio": "UNKNOWN" if classification["classification"] == "video_only_with_no_advertised_audio" else ("RETAINED_AND_PROBED" if probe.get("has_audio") else "ABSENT_IN_RETAINED_MEDIA"),
                "original_audio": original_audio_status,
                "original_audio_unknown": original_audio_status == "UNKNOWN",
            },
            "acquisition_provenance": {
                "source_sha256": source_sha256,
                "source_url_sha256": selected["url_sha256"],
                "metadata_evidence": {
                    "path": metadata_path.name,
                    "sha256": _sha256_bytes(raw_metadata),
                    "input_path": evidence_path,
                },
                "metadata_sha256": metadata_sha256,
                "metadata_evidence_sha256": metadata_sha256,
                "download": dict(download_result) if download_result is not None else {},
            },
            **probe,
        }
        # Probe output is technical evidence only.  Reassert the recovery
        # contract after merging it so a malformed/injected probe cannot turn
        # unknown original audio into a speech or silence claim.
        record.update({
            "source_pointer": media_path.name,
            "sha256": source_sha256,
            "source_hash": source_sha256,
            "source_kind": rights.get("source_kind") if rights_approved else None,
            "rights_receipt": rights_receipt,
            "rights_receipt_sha256": rights_receipt_sha256,
            "acquisition_provenance": {
                "source_sha256": source_sha256,
                "source_url_sha256": selected["url_sha256"],
                "metadata_evidence": {
                    "path": metadata_path.name,
                    "sha256": _sha256_bytes(raw_metadata),
                    "input_path": evidence_path,
                },
                "metadata_sha256": metadata_sha256,
                "metadata_evidence_sha256": metadata_sha256,
                "download": dict(download_result) if download_result is not None else {},
            },
            "speech_state": speech_state,
            "audio_source_status": audio_source_status,
            "original_audio_status": original_audio_status,
            "original_audio_unknown": original_audio_status == "UNKNOWN",
            "source_completeness_flag": (
                "VIDEO_RETAINED_AUDIO_ORIGINAL_UNKNOWN"
                if original_audio_status == "UNKNOWN" else "VIDEO_AUDIO_ADVERTISEMENT_PRESENT"
            ),
            "transcription_eligibility": transcription_eligibility,
            "rights_state": "APPROVED" if rights_approved else "REQUIRED",
            "analysis_ready": rights_approved,
            "rights_required_for_frames_and_asr": True,
            "no_speech_confirmed": False,
            "source_completeness": {
                "video": "RETAINED_AND_PROBED",
                "audio": "UNKNOWN" if original_audio_status == "UNKNOWN" else ("RETAINED_AND_PROBED" if probe.get("has_audio") else "ABSENT_IN_RETAINED_MEDIA"),
                "original_audio": original_audio_status,
                "original_audio_unknown": original_audio_status == "UNKNOWN",
            },
        })
        try:
            # Serialize to a sibling and promote atomically.  A serializer or
            # filesystem failure must not leave a misleading empty record.
            with record_partial_path.open("x", encoding="utf-8") as handle:
                json.dump(record, handle, sort_keys=True, separators=(",", ":"), allow_nan=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            record_partial_path.replace(record_path)
        except FileExistsError as exc:
            raise AcquisitionError("OUTPUT_COLLISION") from exc
        return {
            "state": "OBSERVED",
            "code": code,
            "classification": classification["classification"],
            "media_path": str(media_path),
            "record_path": str(record_path),
            "metadata_path": str(metadata_path),
            "source_sha256": source_sha256,
            "source_hash": source_sha256,
            "metadata_sha256": metadata_sha256,
            "metadata_evidence_sha256": metadata_sha256,
            "audio_source_status": audio_source_status,
            "original_audio_status": original_audio_status,
            "original_audio_unknown": original_audio_status == "UNKNOWN",
            "source_completeness_flag": (
                "VIDEO_RETAINED_AUDIO_ORIGINAL_UNKNOWN"
                if original_audio_status == "UNKNOWN" else "VIDEO_AUDIO_ADVERTISEMENT_PRESENT"
            ),
            "speech_state": speech_state,
            "transcription_eligibility": transcription_eligibility,
            "rights_state": "APPROVED" if rights_approved else "REQUIRED",
            "analysis_ready": rights_approved,
            "source_kind": rights.get("source_kind") if rights_approved else None,
            "rights_receipt_sha256": rights_receipt_sha256,
        }
    except BaseException:
        retained_hash = None
        retained_path: Path | None = None
        # Promotion happens before record serialization.  Inspect the promoted
        # path first so a record-write failure cannot report valid media as lost.
        if media_path.is_file() and not media_path.is_symlink():
            retained_path = media_path
        elif staging and staging.is_file() and not staging.is_symlink():
            retained_path = staging
        if retained_path is not None:
            try:
                staged_bytes = retained_path.stat().st_size
                if 0 < staged_bytes <= max_bytes:
                    retained_hash = digest(retained_path)
                    if retained_path == staging and not media_path.exists() and not media_path.is_symlink():
                        staging.replace(media_path)
                        retained_path = media_path
            except OSError:
                retained_hash = None
        if staging and staging.exists():
            staging.unlink(missing_ok=True)
        if record_partial_path.exists() and not record_partial_path.is_symlink():
            record_partial_path.unlink(missing_ok=True)
        failure = {
            "schema": "m2.recovered-media-failure.v1",
            "media_id": code,
            "observation_state": "PARTIAL",
            "failure_code": str(sys.exc_info()[1]) if sys.exc_info()[1] else "RECOVERY_FAILED",
            "format_classification": classification.get("classification"),
            "metadata_sha256": metadata_sha256,
            "source_sha256": retained_hash,
            "source_hash": retained_hash,
            "source_bytes": staged_bytes,
            "retained_media": bool(retained_hash),
            "retained_media_path": media_path.name if retained_hash else None,
            "metadata_evidence": metadata_path.name if metadata_path.is_file() else None,
            "metadata_evidence_sha256": _sha256_bytes(raw_metadata) if metadata_path.is_file() else None,
            "rights_state": "APPROVED" if rights_approved else "REQUIRED",
            "source_kind": rights.get("source_kind") if rights_approved else None,
            "rights_receipt": rights_receipt,
            "rights_receipt_sha256": rights_receipt_sha256,
            "analysis_ready": False,
            "review_state": "REVIEW_REQUIRED",
        }
        try:
            with failure_path.open("x", encoding="utf-8") as handle:
                json.dump(failure, handle, sort_keys=True, separators=(",", ":"), allow_nan=False)
                handle.write("\n")
        except (OSError, ValueError, TypeError):
            pass
        raise


recover = recover_video
recover_video_only = recover_video


__all__ = [
    "classify_metadata",
    "classify_formats",
    "parse_metadata",
    "recover",
    "recover_video",
    "recover_video_only",
]
