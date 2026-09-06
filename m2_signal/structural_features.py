"""Hash-bound structural feature export for reviewed transcript annotations."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "m2.structural-features.v1"
ANNOTATION_SCHEMA = "m2.transcript-structure-annotation.v2"
ACCEPTED_VERDICTS = {
    "ACCEPT_WITH_LIMITATIONS_FOR_BOUNDED_STRUCTURAL_ANALYSIS",
    "ACCEPTED_FOR_BOUNDED_STRUCTURAL_ANALYSIS",
}
LABELS = ("hook", "body", "mechanism", "proof", "implication", "CTA", "unclear")
HEX64 = set("0123456789abcdef")


class StructuralFeatureError(ValueError):
    """Stable fail-closed error for structural feature admission."""


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise StructuralFeatureError("JSON_VALUE_INVALID") from exc


def object_hash(value: Any) -> str:
    return sha256_bytes(_canonical(value))


def _clean_hash(value: Any, code: str = "HASH_INVALID") -> str:
    if not isinstance(value, str):
        raise StructuralFeatureError(code)
    value = value.removeprefix("sha256:")
    if len(value) != 64 or not set(value) <= HEX64:
        raise StructuralFeatureError(code)
    return value


def _reject_symlink_ancestors(path: Path) -> None:
    absolute = path.absolute()
    for ancestor in (absolute, *absolute.parents):
        if ancestor.is_symlink():
            raise StructuralFeatureError("SYMLINK_PATH_REJECTED")


def _safe_existing_file(path: Any, code: str) -> tuple[Path, bytes, str]:
    if not isinstance(path, (str, Path)) or not str(path):
        raise StructuralFeatureError(code)
    raw_path = Path(path)
    _reject_symlink_ancestors(raw_path)
    if raw_path.is_symlink() or not raw_path.is_file():
        raise StructuralFeatureError(code)
    try:
        raw = raw_path.read_bytes()
    except (OSError, UnicodeError) as exc:
        raise StructuralFeatureError(code) from exc
    return raw_path.absolute(), raw, sha256_bytes(raw)


def _safe_root(path: Any) -> Path:
    if not isinstance(path, (str, Path)) or not str(path):
        raise StructuralFeatureError("CORPUS_ROOT_INVALID")
    root = Path(path).absolute()
    _reject_symlink_ancestors(root)
    if root.is_symlink() or not root.is_dir():
        raise StructuralFeatureError("CORPUS_ROOT_INVALID")
    return root


def _safe_relative_file(root: Path, relative: Any, code: str = "ARTIFACT_PATH_INVALID", *, read_content: bool = True) -> tuple[Path, bytes, str]:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise StructuralFeatureError(code)
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts or ":" in relative:
        raise StructuralFeatureError(code)
    # Existing annotations record transcript paths relative to the repository,
    # whereas acquisition maps are relative to the approved corpus root.
    # Strip only that exact configured prefix; no basename or suffix matching.
    repository = Path(__file__).resolve().parents[1]
    try:
        prefix = root.absolute().relative_to(repository).as_posix()
    except ValueError:
        prefix = None
    if prefix and relative.startswith(prefix + "/"):
        candidate = Path(relative[len(prefix) + 1:])
    lexical = root / candidate
    _reject_symlink_ancestors(lexical)
    if lexical.is_symlink():
        raise StructuralFeatureError(code)
    try:
        resolved = lexical.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (OSError, ValueError):
        raise StructuralFeatureError(code) from None
    if not resolved.is_file():
        raise StructuralFeatureError(code)
    if read_content:
        raw = resolved.read_bytes()
    else:
        digest = hashlib.sha256()
        with resolved.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return resolved, b"", digest.hexdigest()
    return resolved, raw, sha256_bytes(raw)


def _json_bytes(raw: bytes, code: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise StructuralFeatureError(code) from exc


def _identity_key(value: Mapping[str, Any]) -> tuple[str, str, int]:
    reel_id, code, index = value.get("reel_id"), value.get("code"), value.get("identity_index")
    if not isinstance(reel_id, str) or not reel_id or not isinstance(code, str) or not code:
        raise StructuralFeatureError("CANONICAL_IDENTITY_INVALID")
    if type(index) is not int or index < 0:
        raise StructuralFeatureError("CANONICAL_IDENTITY_INDEX_INVALID")
    return reel_id, code, index


def load_canonical_manifest(path: str | Path) -> tuple[list[dict[str, Any]], str]:
    _, raw, digest = _safe_existing_file(path, "CANONICAL_MANIFEST_UNAVAILABLE")
    value = _json_bytes(raw, "CANONICAL_MANIFEST_INVALID")
    entries = value.get("entries") if isinstance(value, dict) else value
    if not isinstance(entries, list) or not entries:
        raise StructuralFeatureError("CANONICAL_ENTRIES_REQUIRED")
    result, seen_indexes, seen_codes, seen_reels = [], set(), set(), set()
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            raise StructuralFeatureError("CANONICAL_ENTRY_INVALID")
        reel_id, code, index = _identity_key(raw_entry)
        if index in seen_indexes or code in seen_codes or reel_id in seen_reels:
            raise StructuralFeatureError("CANONICAL_IDENTITY_DUPLICATE")
        seen_indexes.add(index); seen_codes.add(code); seen_reels.add(reel_id)
        source_hash = raw_entry.get("source_media_hash")
        if source_hash is None and isinstance(raw_entry.get("sources"), list):
            for source in raw_entry["sources"]:
                if isinstance(source, dict) and source.get("sha256"):
                    source_hash = source["sha256"]
                    break
        reasons = list(raw_entry.get("quarantine_reasons") or [])
        research_reasons = list(raw_entry.get("research_quarantine_reasons") or [])
        quarantined = raw_entry.get("quarantined", raw_entry.get("is_quarantined", False))
        if not isinstance(quarantined, bool):
            raise StructuralFeatureError("CANONICAL_QUARANTINE_INVALID")
        result.append({"reel_id": reel_id, "code": code, "identity_index": index,
                       "quarantine_reasons": reasons, "research_quarantine_reasons": research_reasons,
                       "quarantined": quarantined or bool(reasons) or bool(research_reasons),
                       "source_media_hash": source_hash,
                       "transcript_sha256": raw_entry.get("transcript_sha256")})
    return result, digest


def _read_jsonl(raw: bytes) -> list[dict[str, Any]]:
    rows = []
    for line in raw.splitlines():
        if line.strip():
            value = _json_bytes(line, "ANNOTATION_JSONL_INVALID")
            if not isinstance(value, dict):
                raise StructuralFeatureError("ANNOTATION_JSONL_INVALID")
            rows.append(value)
    return rows


def _annotation_hash_from_review(review: Mapping[str, Any]) -> str | None:
    candidates = [review.get("annotation_sha256")]
    for container_name in ("inputs", "maker_artifacts", "artifacts", "source_hashes"):
        container = review.get(container_name)
        if isinstance(container, Mapping):
            for name, value in container.items():
                if "annotation" in str(name) or "structural" in str(name):
                    candidates.append(value)
    for value in candidates:
        if isinstance(value, str):
            try:
                return _clean_hash(value)
            except StructuralFeatureError:
                continue
    return None


def _review_scope(review: Mapping[str, Any]) -> set[int]:
    scope = review.get("scope")
    if not isinstance(scope, Mapping):
        raise StructuralFeatureError("REVIEW_SCOPE_REQUIRED")
    values = scope.get("identity_indexes", scope.get("included_indexes"))
    if values is None:
        raise StructuralFeatureError("REVIEW_SCOPE_REQUIRED")
    if not isinstance(values, list) or any(type(value) is not int or value < 0 for value in values):
        raise StructuralFeatureError("REVIEW_SCOPE_INVALID")
    return set(values)


def _validate_review(review: Mapping[str, Any], annotation_hash: str, review_hash: str, spec: Mapping[str, Any]) -> dict[str, Any]:
    if review.get("verdict") not in ACCEPTED_VERDICTS:
        raise StructuralFeatureError("REVIEW_VERDICT_NOT_ACCEPTED")
    maker, reviewer = review.get("maker") or review.get("maker_actor"), review.get("reviewer") or review.get("reviewer_actor")
    if not isinstance(maker, str) or not maker or not isinstance(reviewer, str) or not reviewer or maker == reviewer:
        raise StructuralFeatureError("REVIEW_ACTORS_NOT_DISTINCT")
    receipt_id = review.get("review_id") or review.get("receipt_id") or review.get("lane")
    if not isinstance(receipt_id, str) or not receipt_id:
        raise StructuralFeatureError("REVIEW_ID_REQUIRED")
    if _annotation_hash_from_review(review) != annotation_hash:
        raise StructuralFeatureError("REVIEW_ANNOTATION_HASH_MISMATCH")
    if _clean_hash(spec.get("review_sha256"), "REVIEW_HASH_INVALID") != review_hash:
        raise StructuralFeatureError("REVIEW_HASH_MISMATCH")
    return {"receipt_id": receipt_id, "maker": maker, "reviewer": reviewer, "scope": _review_scope(review), "review_sha256": review_hash}


def _finite(value: Any) -> bool:
    if type(value) not in {int, float} or isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError):
        return False


def _segment_shape(segment: Mapping[str, Any], error: str) -> tuple[str, float, float, str]:
    sid, start, end, text = segment.get("segment_id"), segment.get("start_ms"), segment.get("end_ms"), segment.get("text")
    if not isinstance(sid, str) or not sid or not _finite(start) or not _finite(end) or float(end) <= float(start) or not isinstance(text, str):
        raise StructuralFeatureError(error)
    return sid, float(start), float(end), text


def _word_counts(segment: Mapping[str, Any], bounds: tuple[float, float]) -> tuple[int, int, int]:
    words = segment.get("words", []) or []
    if not isinstance(words, list):
        raise StructuralFeatureError("TRANSCRIPT_WORDS_INVALID")
    valid = unaligned = lexical = 0
    lo, hi = bounds
    for word in words:
        if not isinstance(word, Mapping):
            raise StructuralFeatureError("TRANSCRIPT_WORD_INVALID")
        start, end, text = word.get("start_ms"), word.get("end_ms"), word.get("word", word.get("text"))
        if isinstance(text, str) and text.strip():
            lexical += 1
        if _finite(start) and _finite(end) and float(end) > float(start) and isinstance(text, str) and text.strip():
            if float(start) < lo or float(end) > hi:
                raise StructuralFeatureError("TRANSCRIPT_WORD_OUT_OF_SEGMENT")
            valid += 1
        else:
            unaligned += 1
    return valid, unaligned, lexical


def _safe_artifact_map(root: Path, mapping: Any) -> dict[str, str]:
    if mapping is None:
        return {}
    if not isinstance(mapping, Mapping):
        raise StructuralFeatureError("ARTIFACT_MAP_INVALID")
    result = {}
    for relative, claimed in mapping.items():
        ext = Path(str(relative)).suffix.lower()
        _, _, actual = _safe_relative_file(root, relative, "ARTIFACT_PATH_INVALID", read_content=ext not in {".mp4", ".mov", ".m4a", ".webm", ".mkv"})
        if actual != _clean_hash(claimed, "ARTIFACT_HASH_INVALID"):
            raise StructuralFeatureError("ARTIFACT_HASH_MISMATCH")
        result[str(relative)] = actual
    return result


def _verify_artifacts(root: Path, annotation: Mapping[str, Any], tx_ref: Mapping[str, Any], tx_hash: str, expected_source: str) -> None:
    source_input = annotation.get("input") if isinstance(annotation.get("input"), Mapping) else {}
    acquisition = _safe_artifact_map(root, source_input.get("acquisition_artifacts"))
    transcript_artifacts = _safe_artifact_map(root, source_input.get("transcript_artifacts"))
    if not acquisition:
        raise StructuralFeatureError("ACQUISITION_ARTIFACT_MAP_REQUIRED")
    if not transcript_artifacts:
        raise StructuralFeatureError("TRANSCRIPT_ARTIFACT_MAP_REQUIRED")
    if transcript_artifacts:
        tx_path = str(tx_ref["path"])
        matching = transcript_artifacts.get(tx_path)
        if matching != tx_hash:
            raise StructuralFeatureError("TRANSCRIPT_ARTIFACT_HASH_MISMATCH")
    if acquisition:
        media_files = [(name, digest) for name, digest in acquisition.items() if Path(name).suffix.lower() in {".mp4", ".mov", ".m4a", ".webm", ".mkv"}]
        records = [(name, digest) for name, digest in acquisition.items() if name.endswith(".media.json")]
        if len(media_files) != 1:
            raise StructuralFeatureError("ACQUISITION_MEDIA_ARTIFACT_REQUIRED")
        if len(records) != 1:
            raise StructuralFeatureError("ACQUISITION_RECORD_REQUIRED")
        if media_files:
            media_name, media_hash = media_files[0]
            if media_hash != expected_source:
                raise StructuralFeatureError("ACQUISITION_MEDIA_HASH_MISMATCH")
            record_path, record_raw, _ = _safe_relative_file(root, records[0][0], "ACQUISITION_RECORD_INVALID")
            record = _json_bytes(record_raw, "ACQUISITION_RECORD_INVALID")
            if not isinstance(record, Mapping) or record.get("reel_id") != annotation.get("reel_id") or record.get("media_id") not in {annotation.get("code"), None}:
                raise StructuralFeatureError("ACQUISITION_RECORD_IDENTITY_MISMATCH")
            if record.get("sha256") != media_hash:
                raise StructuralFeatureError("ACQUISITION_RECORD_HASH_MISMATCH")
            pointer = record.get("source_pointer") or record.get("artifact")
            if not isinstance(pointer, str) or not pointer or Path(pointer).is_absolute() or ".." in Path(pointer).parts:
                raise StructuralFeatureError("ACQUISITION_RECORD_POINTER_MISMATCH")
            try:
                pointer_rel = (record_path.parent / pointer).resolve(strict=True).relative_to(root.resolve(strict=True)).as_posix()
            except (OSError, ValueError):
                raise StructuralFeatureError("ACQUISITION_RECORD_POINTER_MISMATCH") from None
            if pointer_rel != media_name:
                raise StructuralFeatureError("ACQUISITION_RECORD_POINTER_MISMATCH")


def _annotation_only(texts: Sequence[str]) -> bool:
    nonempty = [text.strip() for text in texts if isinstance(text, str) and text.strip()]
    return bool(nonempty) and all(re.fullmatch(r"(?:\[[^\]\n]*\]\s*)+", text) for text in nonempty)


def _validated_input_counts(annotation: Mapping[str, Any], source_input: Mapping[str, Any], transcript: Mapping[str, Any], derived: Mapping[str, int]) -> tuple[dict[str, Any], list[str]]:
    """Validate declared counts against the transcript-derived counts without treating missing as zero."""
    containers = [container for container in (annotation, source_input, transcript) if isinstance(container, Mapping)]
    values: dict[str, list[Any]] = {name: [] for name in ("lexical_word_count", "aligned_word_count", "unaligned_word_count")}
    for container in containers:
        nested = container.get("counts") if isinstance(container.get("counts"), Mapping) else container
        for name in values:
            if name in nested:
                value = nested[name]
                if type(value) is not int or value < 0 or not _finite(value):
                    raise StructuralFeatureError("TRANSCRIPT_COUNT_INVALID")
                values[name].append(value)
    expected = {"lexical_word_count": derived["lexical"], "aligned_word_count": derived["valid"], "unaligned_word_count": derived["unaligned"]}
    segments = transcript["segments"]
    if all(isinstance(segment.get("raw_words"), list) and isinstance(segment.get("unaligned_words"), list) for segment in segments):
        expected = {
            "lexical_word_count": sum(len(segment["raw_words"]) for segment in segments),
            "aligned_word_count": sum(len(segment["words"]) for segment in segments),
            "unaligned_word_count": sum(len(segment["unaligned_words"]) for segment in segments),
        }
        if expected["lexical_word_count"] != expected["aligned_word_count"] + expected["unaligned_word_count"]:
            raise StructuralFeatureError("TRANSCRIPT_RAW_WORD_PARTITION_INVALID")
    for container in containers:
        for nested in (container, container.get("counts", {})):
            if isinstance(nested, Mapping) and "valid_timed_word_count" in nested:
                value = nested["valid_timed_word_count"]
                if type(value) is not int or value != derived["valid"]:
                    raise StructuralFeatureError("VALID_TIMED_WORD_COUNT_MISMATCH")
    for name, declared in values.items():
        if any(value != declared[0] for value in declared[1:]) or (declared and declared[0] != expected[name]):
            raise StructuralFeatureError("TRANSCRIPT_COUNT_MISMATCH")
    result = {name: (values[name][0] if values[name] else expected[name]) for name in values}
    timing = next((container.get("word_timing") for container in containers if isinstance(container.get("word_timing"), str)), "UNKNOWN")
    uncertainties = annotation.get("uncertainties") or source_input.get("uncertainties") or transcript.get("uncertainties") or []
    if not isinstance(uncertainties, list): uncertainties = [str(uncertainties)]
    result["word_timing"] = timing
    return result, uncertainties


def _load_transcript(root: Path, annotation: Mapping[str, Any], expected_source: Any) -> tuple[dict[str, Any], str, dict[str, Any]]:
    source_input = annotation.get("input") if isinstance(annotation.get("input"), Mapping) else {}
    relative = source_input.get("transcript_path") or annotation.get("transcript_path")
    transcript_path, raw, transcript_hash = _safe_relative_file(root, relative, "TRANSCRIPT_PATH_INVALID")
    expected_tx = source_input.get("transcript_sha256") or annotation.get("transcript_sha256")
    if expected_tx is None:
        raise StructuralFeatureError("TRANSCRIPT_HASH_REQUIRED")
    if _clean_hash(expected_tx, "TRANSCRIPT_HASH_INVALID") != transcript_hash:
        raise StructuralFeatureError("TRANSCRIPT_HASH_MISMATCH")
    transcript = _json_bytes(raw, "TRANSCRIPT_JSON_INVALID")
    if not isinstance(transcript, dict) or transcript.get("schema") != "m2.transcript-evidence.v1":
        raise StructuralFeatureError("TRANSCRIPT_SCHEMA_INVALID")
    actual_source = transcript.get("source_media_hash")
    actual_source = _clean_hash(actual_source, "SOURCE_HASH_INVALID")
    if expected_source is not None and _clean_hash(expected_source, "SOURCE_HASH_INVALID") != actual_source:
        raise StructuralFeatureError("TRANSCRIPT_SOURCE_HASH_MISMATCH")
    claimed_source = annotation.get("source_media_hash") or source_input.get("source_media_hash")
    if claimed_source is not None and _clean_hash(claimed_source, "SOURCE_HASH_INVALID") != actual_source:
        raise StructuralFeatureError("ANNOTATION_SOURCE_HASH_MISMATCH")
    return transcript, transcript_hash, {"path": transcript_path.relative_to(root).as_posix(), "sha256": transcript_hash, "source_media_hash": actual_source}


def _validate_record(annotation: Mapping[str, Any], canonical: Mapping[str, Any], review: Mapping[str, Any], root: Path, annotation_hash: str) -> dict[str, Any]:
    if annotation.get("schema") != ANNOTATION_SCHEMA:
        raise StructuralFeatureError("ANNOTATION_SCHEMA_INVALID")
    if _identity_key(annotation) != (canonical["reel_id"], canonical["code"], canonical["identity_index"]):
        raise StructuralFeatureError("ANNOTATION_CANONICAL_IDENTITY_MISMATCH")
    source_input = annotation.get("input") if isinstance(annotation.get("input"), Mapping) else {}
    claimed_source = annotation.get("source_media_hash") or source_input.get("source_media_hash")
    expected_source = canonical.get("source_media_hash")
    if expected_source is not None and claimed_source is not None and _clean_hash(expected_source, "SOURCE_HASH_INVALID") != _clean_hash(claimed_source, "SOURCE_HASH_INVALID"):
        raise StructuralFeatureError("CANONICAL_SOURCE_HASH_MISMATCH")
    transcript, tx_hash, tx_ref = _load_transcript(root, annotation, expected_source or claimed_source)
    source_segments, asr_segments, primary, secondary = transcript.get("segments"), annotation.get("asr_segments"), annotation.get("primary_partition"), annotation.get("rhetorical_sections")
    observation_state = transcript.get("observation_state", "UNKNOWN")
    if observation_state not in {"OBSERVED", "SUSPICIOUS_TIMINGS"} or source_segments == []:
        _verify_artifacts(root, annotation, tx_ref, tx_hash, tx_ref["source_media_hash"])
        empty = observation_state == "EMPTY_OUTPUT_UNVERIFIED" or source_segments == []
        return {"identity_index": canonical["identity_index"], "reel_id": canonical["reel_id"], "code": canonical["code"],
                "disposition": "NOT_ANALYZABLE_EMPTY_OUTPUT_UNVERIFIED" if empty else "NOT_ANALYZABLE_UNVERIFIED_TRANSCRIPT_STATE",
                "annotation_sha256": annotation_hash, "source_media_hash": tx_ref["source_media_hash"], "transcript_sha256": tx_hash,
                "review": {key: review[key] for key in ("receipt_id", "maker", "reviewer", "review_sha256")},
                "transcript_observation_state": observation_state, "transcript_failure_code": transcript.get("failure_code"),
                "coverage": {"source_segment_count": len(source_segments) if isinstance(source_segments, list) else None,
                             "primary_segment_count": 0, "spoken_word_count": None, "speech_eligibility": "UNKNOWN"},
                "quality_issues": ["EMPTY_OUTPUT_NOT_PROOF_OF_SILENCE"] if empty else ["TRANSCRIPT_STATE_NOT_ADMITTED"],
                "source": tx_ref, "caveats": ["No structural promotion. Missing or empty machine output does not establish silence, speech or meaning."]}
    if not all(isinstance(value, list) for value in (source_segments, asr_segments, primary, secondary)):
        raise StructuralFeatureError("ANNOTATION_SEGMENTS_INVALID")
    source_map = {}
    previous_end = None
    for segment in source_segments:
        if not isinstance(segment, Mapping):
            raise StructuralFeatureError("TRANSCRIPT_SEGMENT_INVALID")
        sid, start, end, text = _segment_shape(segment, "TRANSCRIPT_SEGMENT_INVALID")
        if sid in source_map:
            raise StructuralFeatureError("TRANSCRIPT_SEGMENT_DUPLICATE")
        if previous_end is not None and start < previous_end:
            raise StructuralFeatureError("TRANSCRIPT_SEGMENT_OVERLAP")
        previous_end = end
        valid, unaligned, lexical = _word_counts(segment, (start, end))
        source_map[sid] = (start, end, text, valid, unaligned, lexical)
    if len(asr_segments) != len(source_segments):
        raise StructuralFeatureError("ASR_SEGMENT_COUNT_MISMATCH")
    asr_seen = set()
    expected_ids = [segment["segment_id"] for segment in source_segments]
    for asr_order, segment in enumerate(asr_segments):
        if not isinstance(segment, Mapping):
            raise StructuralFeatureError("ANNOTATION_ASR_SEGMENT_INVALID")
        sid, start, end, text = _segment_shape(segment, "ANNOTATION_ASR_SEGMENT_INVALID")
        if sid in asr_seen:
            raise StructuralFeatureError("ANNOTATION_ASR_SEGMENT_DUPLICATE")
        if sid != expected_ids[asr_order]:
            raise StructuralFeatureError("ANNOTATION_ASR_SEGMENT_ORDER_INVALID")
        asr_seen.add(sid)
        src = source_map.get(sid)
        if src is None or (start, end, text, segment.get("valid_timed_word_count")) != (src[0], src[1], src[2], src[3]):
            raise StructuralFeatureError("ANNOTATION_ASR_SOURCE_MISMATCH")
    if asr_seen != set(source_map):
        raise StructuralFeatureError("ANNOTATION_ASR_SEGMENT_COVERAGE_INVALID")
    if len(primary) != len(source_segments):
        raise StructuralFeatureError("PRIMARY_PARTITION_NOT_EXCLUSIVE")
    primary_seen, spans = set(), []
    primary_by_label = {label: {"segment_count": 0, "valid_timed_word_count": 0, "duration_ms": 0} for label in LABELS}
    for order, part in enumerate(primary, 1):
        if not isinstance(part, Mapping) or part.get("partition_order") != order:
            raise StructuralFeatureError("PRIMARY_PARTITION_ORDER_INVALID")
        sid, label = part.get("source_segment_id"), part.get("label")
        if sid in primary_seen or sid not in source_map or label not in LABELS:
            raise StructuralFeatureError("PRIMARY_PARTITION_NOT_EXCLUSIVE")
        if sid != expected_ids[order - 1]:
            raise StructuralFeatureError("PRIMARY_PARTITION_SOURCE_ORDER_INVALID")
        primary_seen.add(sid); start, end, _, count, _, _ = source_map[sid]
        if part.get("start_ms") != start or part.get("end_ms") != end or part.get("valid_timed_word_count") != count:
            raise StructuralFeatureError("PRIMARY_PARTITION_SOURCE_MISMATCH")
        stats = primary_by_label[label]; stats["segment_count"] += 1; stats["valid_timed_word_count"] += count; stats["duration_ms"] += end - start; spans.append((start, end))
    if primary_seen != set(source_map):
        raise StructuralFeatureError("PRIMARY_PARTITION_INCOMPLETE")
    secondary_by_label = {label: {"section_count": 0, "valid_timed_word_count": 0, "segment_ids": []} for label in LABELS}
    secondary_rows = []
    secondary_ids = set()
    for section_order, section in enumerate(secondary, 1):
        if not isinstance(section, Mapping) or section.get("layer") != "secondary_non_additive" or section.get("non_additive") is not True:
            raise StructuralFeatureError("SECONDARY_NON_ADDITIVE_REQUIRED")
        section_id = section.get("section_id")
        if not isinstance(section_id, str) or not section_id or section_id in secondary_ids:
            raise StructuralFeatureError("SECONDARY_SECTION_ID_INVALID")
        secondary_ids.add(section_id)
        label, ids = section.get("label"), section.get("asr_segment_ids")
        if label not in LABELS or not isinstance(ids, list) or not ids or len(set(ids)) != len(ids) or any(sid not in source_map for sid in ids):
            raise StructuralFeatureError("SECONDARY_SECTION_INVALID")
        section_count = sum(source_map[sid][3] for sid in ids)
        if "valid_timed_word_count" in section and (type(section["valid_timed_word_count"]) is not int or section["valid_timed_word_count"] != section_count):
            raise StructuralFeatureError("SECONDARY_SECTION_COUNT_MISMATCH")
        section_start = min(source_map[sid][0] for sid in ids); section_end = max(source_map[sid][1] for sid in ids)
        if "start_ms" in section and section.get("start_ms") != section_start:
            raise StructuralFeatureError("SECONDARY_SECTION_BOUNDS_INVALID")
        if "end_ms" in section and section.get("end_ms") != section_end:
            raise StructuralFeatureError("SECONDARY_SECTION_BOUNDS_INVALID")
        stats = secondary_by_label[label]; stats["section_count"] += 1; stats["valid_timed_word_count"] += section_count; stats["segment_ids"].append(list(ids))
        secondary_rows.append({"section_id": section_id, "declared_count_state": "OBSERVED_VALIDATED" if "valid_timed_word_count" in section else "ABSENT", "section_order": section_order, "label": label, "segment_ids": list(ids), "start_ms": section_start, "end_ms": section_end, "valid_timed_word_count": section_count, "non_additive": True})
    union_ms = 0.0; cursor = None
    for start, end in sorted(spans):
        if cursor is None: cursor = [start, end]
        elif start <= cursor[1]: cursor[1] = max(cursor[1], end)
        else: union_ms += cursor[1] - cursor[0]; cursor = [start, end]
    if cursor is not None: union_ms += cursor[1] - cursor[0]
    timeline = max(end for _, end in spans) - min(start for start, _ in spans) if spans else 0
    primary_rows = []
    secondary_by_id = {section["section_id"]: section for section in secondary_rows}
    for order, part in enumerate(primary, 1):
        sid = part["source_segment_id"]
        primary_id = part.get("primary_section_id")
        if not isinstance(primary_id, str) or primary_id not in secondary_by_id:
            raise StructuralFeatureError("PRIMARY_SECTION_ID_INVALID")
        section = secondary_by_id[primary_id]
        if sid not in section["segment_ids"] or part["label"] != section["label"]:
            raise StructuralFeatureError("PRIMARY_SECTION_LINK_MISMATCH")
        start, end, _, count, _, _ = source_map[sid]
        primary_rows.append({"primary_section_id": primary_id, "partition_order": order, "source_segment_id": sid, "label": part["label"], "start_ms": start, "end_ms": end, "valid_timed_word_count": count})
    _verify_artifacts(root, annotation, tx_ref, tx_hash, tx_ref["source_media_hash"])
    language = transcript.get("language") if isinstance(transcript.get("language"), str) else None
    annotation_only = _annotation_only([value[2] for value in source_map.values()])
    source_input = annotation.get("input") if isinstance(annotation.get("input"), Mapping) else {}
    raw_counts, uncertainties = _validated_input_counts(annotation, source_input, transcript, {"lexical":sum(value[5] for value in source_map.values()), "valid":sum(value[3] for value in source_map.values()), "unaligned":sum(value[4] for value in source_map.values())})
    valid_total = sum(value[3] for value in source_map.values())
    caveats = ["Acoustic accuracy is not established.", "Primary words are valid timed source counts; secondary section counts are descriptive and non-additive.", "No scene promotion, causal claim, or language-pooled rate is produced."]
    if annotation_only:
        caveats.append("ASR_ANNOTATION_ONLY_SPEECH_UNVERIFIED: bracket-only machine annotations are not counted as spoken words and do not prove silence.")
    if annotation_only:
        caveats.append("Spoken-word eligibility is UNKNOWN; annotation-only text must not be interpreted as speech or silence.")
    return {"identity_index": canonical["identity_index"], "reel_id": canonical["reel_id"], "code": canonical["code"], "disposition": "STRUCTURAL_ACCEPTED_WITH_LIMITATIONS", "annotation_sha256": annotation_hash, "source_media_hash": tx_ref["source_media_hash"], "transcript_sha256": tx_hash, "review": {key: review[key] for key in ("receipt_id", "maker", "reviewer", "review_sha256")}, "coverage": {"source_segment_count": len(source_map), "primary_segment_count": len(primary_seen), "primary_valid_timed_word_count": valid_total, "lexical_word_count": raw_counts["lexical_word_count"], "aligned_word_count": raw_counts["aligned_word_count"], "unaligned_word_count": raw_counts["unaligned_word_count"], "valid_timed_word_count": valid_total, "spoken_word_count": None, "speech_eligibility": "UNKNOWN_UNVERIFIED_ANNOTATION_ONLY" if annotation_only else "NOT_ESTABLISHED", "word_timing": "UNVERIFIED_ANNOTATION_ONLY" if annotation_only else raw_counts["word_timing"], "input_uncertainties": uncertainties, "secondary_counts_non_additive": True}, "primary": {"by_label": primary_by_label, "segments": primary_rows, "timeline_span_ms": timeline, "asr_segment_coverage_ms": union_ms, "speaking_duration_ms": None, "speaking_duration_state": "UNKNOWN_NO_VAD"}, "secondary": {"by_label": secondary_by_label, "sections": secondary_rows, "non_additive": True}, "language": {"value": language, "rate_state": "NOT_COMPUTED", "pooling": "DISABLED_LANGUAGE_CONDITIONED_ONLY"}, "quality_issues": ["ASR_ANNOTATION_ONLY_SPEECH_UNVERIFIED"] if annotation_only else [], "caveats": caveats, "source": tx_ref}


def _new_output(path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise StructuralFeatureError("OUTPUT_MUST_BE_NEW")
    _reject_symlink_ancestors(path)
    if not path.parent.is_dir():
        raise StructuralFeatureError("OUTPUT_PARENT_UNAVAILABLE")


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical(value) + b"\n")


def _field_dictionary() -> dict[str, Any]:
    fields = {
        "identity_index":"Canonical population position.", "reel_id":"Canonical Reel identity.", "code":"Canonical short code.", "disposition":"Admission state preserving missing, quarantined, and invalid identities.", "quarantine_reasons":"Canonical quarantine reasons.", "research_quarantine_reasons":"Research quarantine reasons.", "quarantined":"Canonical boolean quarantine state.", "annotation_sha256":"Exact annotation JSONL SHA-256.", "source_media_hash":"Verified source-media SHA-256.", "transcript_sha256":"Exact transcript JSON SHA-256.", "review.receipt_id":"Accepted independent review receipt.", "review.maker":"Annotation maker.", "review.reviewer":"Independent reviewer.", "review.review_sha256":"Exact independent review receipt SHA-256.", "coverage.lexical_word_count":"Reported lexical count; not an accuracy claim.", "coverage.aligned_word_count":"Valid timed word count after validation.", "coverage.unaligned_word_count":"Words without valid bounded timing.", "coverage.spoken_word_count":"Unknown: no independent acoustic validation is established.", "coverage.speech_eligibility":"Speech eligibility evidence state.", "coverage.word_timing":"Observed or explicitly unverified timing state.", "coverage.input_uncertainties":"Input caveats retained as labels.", "primary.by_label.<label>.segment_count":"Exclusive segment count by label.", "primary.by_label.<label>.valid_timed_word_count":"Exclusive valid timed source words by label; not speech proof.", "primary.by_label.<label>.duration_ms":"Primary duration sum by label.", "primary.segments[]":"Exclusive segment rows with exact source bounds and counts.", "primary.segments[].primary_section_id":"Exact source rhetorical section ID used by this exclusive assignment.", "secondary.sections[].section_id":"Exact source rhetorical section ID, unique per Reel.", "secondary.sections[].declared_count_state":"Whether the input secondary word count was present and independently validated.", "primary.timeline_span_ms":"Outer transcript wall-clock span.", "primary.asr_segment_coverage_ms":"Union of ASR segment intervals; not speaking duration.", "primary.speaking_duration_ms":"Unknown without VAD/acoustic evidence.", "primary.speaking_duration_state":"Explicit speaking-duration evidence state.", "secondary.sections[]":"Per-section non-additive IDs, bounds, and counts.", "secondary.by_label.<label>.section_count":"Descriptive secondary section count.", "secondary.by_label.<label>.valid_timed_word_count":"Descriptive non-additive word count.", "secondary.by_label.<label>.segment_ids":"Secondary memberships, non-additive.", "secondary.non_additive":"Secondary sums are prohibited.", "quality_issues":"Typed quality limitations.", "language.value":"Source-reported language.", "language.rate_state":"Language-conditioned rate state.", "language.pooling":"Language pooling policy.", "caveats":"Evidence limitations.", "source.path":"Approved-root-relative transcript path.", "source.sha256":"Verified transcript artifact hash."}
    fields.update({
        "transcript_observation_state": "Source machine transcript state retained when structural admission is unavailable.",
        "transcript_failure_code": "Exact source failure code retained when structural admission is unavailable.",
        "coverage.source_segment_count": "Number of exact normalized source ASR segments.",
        "coverage.primary_segment_count": "Number of source segments assigned once to the primary partition.",
        "coverage.primary_valid_timed_word_count": "Sum of valid bounded machine word records across the exclusive primary partition.",
        "coverage.valid_timed_word_count": "Valid bounded machine word records; acoustic accuracy is unverified.",
        "coverage.secondary_counts_non_additive": "True: overlapping secondary memberships prohibit summing their word counts.",
        "source.source_media_hash": "SHA-256 of the retained source bytes verified through the acquisition artifact chain.",
    })
    common = {"identity_index": "Foreign key to the canonical population identity; never a sampled-row number."}
    tables = {
        "identities": {"identity_index": fields["identity_index"], "reel_id": fields["reel_id"], "code": fields["code"], "source_media_hash": fields["source_media_hash"], "transcript_sha256": fields["transcript_sha256"], "disposition": fields["disposition"], "quarantine_reasons_json": "JSON array of canonical identity quarantine reasons.", "research_quarantine_reasons_json": "JSON array of research eligibility quarantine reasons.", "quarantined": "Boolean stored as 0/1; canonical or research quarantine blocks promotion."},
        "dispositions": {**common, "disposition": fields["disposition"], "caveats_json": "JSON array explaining unavailable evidence, limitations or validation failure."},
        "reviews": {**common, "receipt_id": fields["review.receipt_id"], "maker": fields["review.maker"], "reviewer": fields["review.reviewer"], "review_sha256": fields["review.review_sha256"], "annotation_sha256": fields["annotation_sha256"]},
        "primary_segments": {**common, "partition_order": "One-based source chronological order; each source segment appears once.", "source_segment_id": "Exact ID in the bound normalized transcript.", "primary_section_id": "Exact referenced rhetorical section ID; multiple primary segments may reference one section.", "label": "Reviewed primary rhetorical role; exclusive within this source partition.", "start_ms": "Source segment start on the retained media timeline, in milliseconds.", "end_ms": "Source segment end on the retained media timeline, in milliseconds.", "valid_timed_word_count": "Valid bounded machine word records assigned once to this source segment; not verified speech."},
        "secondary_sections": {**common, "section_order": "One-based order in the bound annotation file.", "section_id": "Exact source rhetorical section identifier, unique per Reel.", "label": "Reviewed rhetorical role; memberships may overlap other sections.", "segment_ids_json": "JSON object containing exact segment_ids and derived minimum start_ms / maximum end_ms; outer bounds can include gaps.", "valid_timed_word_count": "Derived count for this section alone; do not sum across overlapping sections.", "non_additive": "Always 1: secondary counts are descriptive and non-additive."},
    }
    return {"schema":"m2.structural-features-field-dictionary.v1", "fields":fields, "sqlite_tables": tables}


def _write_sqlite(destination: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    path = destination / "structural-features.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript("""
        CREATE TABLE identities(identity_index INTEGER PRIMARY KEY, reel_id TEXT UNIQUE NOT NULL, code TEXT UNIQUE NOT NULL, source_media_hash TEXT, transcript_sha256 TEXT, disposition TEXT NOT NULL, quarantine_reasons_json TEXT NOT NULL, research_quarantine_reasons_json TEXT NOT NULL, quarantined INTEGER NOT NULL);
        CREATE TABLE dispositions(identity_index INTEGER PRIMARY KEY REFERENCES identities(identity_index), disposition TEXT NOT NULL, caveats_json TEXT NOT NULL);
        CREATE TABLE reviews(identity_index INTEGER PRIMARY KEY REFERENCES identities(identity_index), receipt_id TEXT NOT NULL, maker TEXT NOT NULL, reviewer TEXT NOT NULL, review_sha256 TEXT NOT NULL, annotation_sha256 TEXT NOT NULL);
        CREATE TABLE primary_segments(identity_index INTEGER NOT NULL REFERENCES identities(identity_index), partition_order INTEGER NOT NULL, source_segment_id TEXT NOT NULL, primary_section_id TEXT NOT NULL, label TEXT NOT NULL, start_ms REAL NOT NULL, end_ms REAL NOT NULL, valid_timed_word_count INTEGER NOT NULL, PRIMARY KEY(identity_index, partition_order), UNIQUE(identity_index, source_segment_id), FOREIGN KEY(identity_index, primary_section_id) REFERENCES secondary_sections(identity_index, section_id) DEFERRABLE INITIALLY DEFERRED);
        CREATE TABLE secondary_sections(identity_index INTEGER NOT NULL REFERENCES identities(identity_index), section_order INTEGER NOT NULL, section_id TEXT NOT NULL, label TEXT NOT NULL, segment_ids_json TEXT NOT NULL, valid_timed_word_count INTEGER NOT NULL, non_additive INTEGER NOT NULL, PRIMARY KEY(identity_index, section_order), UNIQUE(identity_index, section_id));
        """)
        for row in rows:
            db.execute("INSERT INTO identities VALUES(?,?,?,?,?,?,?,?,?)", (row["identity_index"], row["reel_id"], row["code"], row.get("source_media_hash"), row.get("transcript_sha256"), row["disposition"], json.dumps(row.get("quarantine_reasons", []), sort_keys=True), json.dumps(row.get("research_quarantine_reasons", []), sort_keys=True), int(bool(row.get("quarantined", False)))))
            db.execute("INSERT INTO dispositions VALUES(?,?,?)", (row["identity_index"], row["disposition"], json.dumps(row.get("caveats", []), sort_keys=True)))
            if row.get("review"):
                review = row["review"]
                db.execute("INSERT INTO reviews VALUES(?,?,?,?,?,?)", (row["identity_index"], review["receipt_id"], review["maker"], review["reviewer"], review["review_sha256"], row["annotation_sha256"]))
            for seg in row.get("primary", {}).get("segments", []):
                db.execute("INSERT INTO primary_segments VALUES(?,?,?,?,?,?,?,?)", (row["identity_index"], seg["partition_order"], seg["source_segment_id"], seg["primary_section_id"], seg["label"], seg["start_ms"], seg["end_ms"], seg["valid_timed_word_count"]))
            for section in row.get("secondary", {}).get("sections", []):
                db.execute("INSERT INTO secondary_sections VALUES(?,?,?,?,?,?,?)", (row["identity_index"], section["section_order"], section["section_id"], section["label"], json.dumps({"segment_ids": section["segment_ids"], "start_ms": section["start_ms"], "end_ms": section["end_ms"]}, sort_keys=True), section["valid_timed_word_count"], 1))
        db.commit()
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise StructuralFeatureError("SQLITE_INTEGRITY_FAILED")
        identity_count = db.execute("SELECT COUNT(*) FROM identities").fetchone()[0]
    return {"path": path.name, "sha256": sha256_file(path), "identity_rows": identity_count, "integrity": "PASS"}


def build_structural_features(canonical_manifest: str | Path, annotation_batches: Sequence[Mapping[str, Any]], corpus_root: str | Path, output_dir: str | Path, *, selected_revisions: Mapping[str | int, str] | None = None, expected_population: int | None = 2352) -> dict[str, Any]:
    """Write a fresh full-population structural feature export."""
    if not isinstance(annotation_batches, Sequence) or isinstance(annotation_batches, (str, bytes)):
        raise StructuralFeatureError("ANNOTATION_ALLOWLIST_REQUIRED")
    root = _safe_root(corpus_root); canonical, canonical_hash = load_canonical_manifest(canonical_manifest)
    if expected_population is not None and len(canonical) != expected_population:
        raise StructuralFeatureError("CANONICAL_POPULATION_MISMATCH")
    selected = {str(key): _clean_hash(value, "SELECTED_REVISION_HASH_INVALID") for key, value in (selected_revisions or {}).items()}
    prepared = []
    for spec in annotation_batches:
        if not isinstance(spec, Mapping): raise StructuralFeatureError("ANNOTATION_SPEC_INVALID")
        annotation_path, annotation_raw, annotation_hash = _safe_existing_file(spec.get("annotations_path"), "ANNOTATION_FILE_UNAVAILABLE")
        if _clean_hash(spec.get("annotations_sha256"), "ANNOTATION_HASH_INVALID") != annotation_hash: raise StructuralFeatureError("ANNOTATION_HASH_MISMATCH")
        review_path, review_raw, review_hash = _safe_existing_file(spec.get("review_path"), "REVIEW_FILE_UNAVAILABLE")
        review = _json_bytes(review_raw, "REVIEW_JSON_INVALID")
        if not isinstance(review, dict): raise StructuralFeatureError("REVIEW_JSON_INVALID")
        review_meta = _validate_review(review, annotation_hash, review_hash, spec)
        prepared.append((_read_jsonl(annotation_raw), review_meta, annotation_hash, str(annotation_path), review_hash))
    by_index = {entry["identity_index"]: entry for entry in canonical}; accepted = {}
    for rows, review_meta, annotation_hash, annotation_path, _ in prepared:
        for row in rows:
            _, code, index = _identity_key(row)
            if index not in by_index: raise StructuralFeatureError("ANNOTATION_IDENTITY_NOT_CANONICAL")
            if review_meta["scope"] is not None and index not in review_meta["scope"]: raise StructuralFeatureError("ANNOTATION_OUTSIDE_REVIEW_SCOPE")
            chosen = selected.get(str(index)) or selected.get(code)
            if chosen is not None and chosen != annotation_hash: continue
            prior = accepted.get(index)
            if prior is not None and (prior[2] != annotation_hash or object_hash(prior[0]) != object_hash(row)):
                raise StructuralFeatureError("CONFLICTING_ANNOTATION_REVISIONS")
            accepted[index] = (row, review_meta, annotation_hash, annotation_path)
    destination = Path(output_dir).absolute(); _new_output(destination); destination.mkdir(parents=False)
    output_rows, accepted_count, blocked_count, not_analyzable_count = [], 0, 0, 0
    for entry in sorted(canonical, key=lambda item: item["identity_index"]):
        candidate = accepted.get(entry["identity_index"])
        common = {"identity_index":entry["identity_index"], "reel_id":entry["reel_id"], "code":entry["code"], "quarantine_reasons":entry["quarantine_reasons"], "research_quarantine_reasons":entry["research_quarantine_reasons"], "quarantined":entry["quarantined"], "source_media_hash":entry.get("source_media_hash"), "transcript_sha256":entry.get("transcript_sha256")}
        if entry["quarantined"]:
            output_rows.append({**common, "disposition":"BLOCKED_CANONICAL_QUARANTINE", "caveats":["Canonical or research quarantine prevents structural promotion."]}); blocked_count += 1; continue
        if candidate is None:
            output_rows.append({**common, "disposition":"NOT_ANALYZABLE_NO_ACCEPTED_STRUCTURAL_REVIEW", "caveats":["No accepted hash-bound structural annotation was supplied."]}); continue
        try: feature = _validate_record(candidate[0], entry, candidate[1], root, candidate[2])
        except StructuralFeatureError as exc:
            blocked_count += 1; feature = {**common, "disposition":"BLOCKED_INVALID_STRUCTURAL_BINDING", "quarantine_reasons":[str(exc)], "caveats":["Structural evidence failed closed validation."]}
        else:
            if feature["disposition"] == "STRUCTURAL_ACCEPTED_WITH_LIMITATIONS":
                accepted_count += 1
            else:
                not_analyzable_count += 1
            feature.update({"quarantine_reasons":entry["quarantine_reasons"], "research_quarantine_reasons":entry["research_quarantine_reasons"], "quarantined":entry["quarantined"]})
        output_rows.append(feature)
    features_path = destination / "structural-features.jsonl"
    with features_path.open("x", encoding="utf-8") as stream:
        for row in output_rows: stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
    _write_json(destination / "field-dictionary.json", _field_dictionary())
    sqlite_meta = _write_sqlite(destination, output_rows)
    run = {"schema":SCHEMA, "status":"STRUCTURAL_FEATURES_COMPLETE_WITH_LIMITATIONS", "input":{"canonical_manifest_sha256":canonical_hash, "canonical_population":len(canonical), "annotation_batches":[{"annotations_path":path, "annotations_sha256":digest, "review_sha256":review_hash} for _, _, digest, path, review_hash in prepared]}, "approved_corpus_root":root.name, "population":{"input_rows":len(canonical), "output_rows":len(output_rows), "rows_dropped":0, "accepted_rows":accepted_count, "blocked_rows":blocked_count, "not_analyzable_rows":not_analyzable_count, "missing_review_rows":len(canonical)-accepted_count-blocked_count-not_analyzable_count}, "scope":{"exclusive_primary_partition":True, "secondary_non_additive":True, "speaking_duration":"UNKNOWN_NO_VAD", "language_pooling":False, "scene_promotion":False, "causal_fitting":False, "network":False, "media_decode":False}, "runtime":{"implementation":platform.python_implementation(), "version":platform.python_version(), "module_sha256":sha256_file(Path(__file__))}, "artifacts":{"features":features_path.name, "field_dictionary":"field-dictionary.json", "sqlite":sqlite_meta, "run_manifest":"run-manifest.json"}}
    _write_json(destination / "run-manifest.json", run)
    _write_json(destination / "artifact-manifest.json", {"schema":"m2.structural-features-artifacts.v1", "files":{name:sha256_file(destination/name) for name in ("field-dictionary.json", "run-manifest.json", "structural-features.jsonl", "structural-features.sqlite")}})
    return {"schema":SCHEMA, "status":run["status"], "output_dir":str(destination), "population":run["population"], "sqlite":sqlite_meta}


def _cli(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--canonical-manifest", required=True, type=Path); parser.add_argument("--batch", action="append", required=True); parser.add_argument("--corpus-root", required=True, type=Path); parser.add_argument("--output", required=True, type=Path); parser.add_argument("--expected-population", type=int, default=2352); args = parser.parse_args(argv)
    specs = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.batch]
    print(json.dumps(build_structural_features(args.canonical_manifest, specs, args.corpus_root, args.output, expected_population=args.expected_population), sort_keys=True)); return 0


if __name__ == "__main__": raise SystemExit(_cli())
