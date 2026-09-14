"""Build a bounded, provider-disabled manifest for cached Reel media.

The manifest is deliberately a read-only index.  It never contacts HikerAPI,
downloads a URL, imports a Hiker client, or removes a file.  URL values are
private downstream inputs and are therefore kept only in the returned private
manifest; malformed-input issues never echo them.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse


SCHEMA = "m2.media-manifest.v1"
MAX_CACHE_BYTES = 32 * 1024 * 1024
SAFE_CODE = re.compile(r"[A-Za-z0-9_-]{5,30}\Z")
MEDIA_SUFFIXES = frozenset(
    {
        ".3gp",
        ".avi",
        ".m4a",
        ".m4v",
        ".mkv",
        ".mov",
        ".mp3",
        ".mp4",
        ".mpeg",
        ".mpg",
        ".wav",
        ".webm",
    }
)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha256_stream(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                return digest.hexdigest()
            digest.update(chunk)


def _safe_private_url(value: Any) -> bool:
    """Only allow downloader-compatible HTTPS URLs.

    This check is intentionally shared by cache and explicit-map routes.  DNS,
    redirect and response validation belong to the downloader integration.
    """

    if not isinstance(value, str) or not value or len(value) > 8192:
        return False
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return bool(
        parsed.scheme.lower() == "https"
        and parsed.netloc
        and not parsed.username
        and not parsed.password
        and "\x00" not in value
    )


def _issue(
    issues: list[dict[str, Any]],
    kind: str,
    *,
    path: str | None = None,
    identity_index: int | None = None,
    code: str | None = None,
    detail: str | None = None,
) -> None:
    # Do not add exception strings here: JSON parsers and URL libraries can
    # include source bodies or signed URLs in their messages.
    item: dict[str, Any] = {"type": kind, "severity": "error"}
    if path is not None:
        item["path"] = path
    if identity_index is not None:
        item["identity_index"] = identity_index
    if code is not None:
        item["code"] = code
    if detail is not None:
        item["detail"] = detail
    issues.append(item)


def _path_info(path: Path, root: Path) -> tuple[Path, str] | None:
    """Return resolved path and lexical root-relative path if safely confined."""

    try:
        resolved_root = root.resolve(strict=True)
        resolved_path = path.resolve(strict=True)
        if not resolved_path.is_relative_to(resolved_root):
            return None
        relative = path.relative_to(root)
    except (OSError, ValueError):
        return None
    return resolved_path, relative.as_posix()


def _root_entries(roots: Iterable[Path]) -> list[Path]:
    result: list[Path] = []
    for root in roots:
        path = Path(root)
        if path not in result:
            result.append(path)
    return result


def _identity_value(value: Any) -> Any:
    """Make malformed identity values hashable/canonical without leaking data."""

    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return repr(type(value).__name__)


def _extract_cache_items(payload: Any) -> list[Any] | None:
    if not isinstance(payload, Mapping):
        return None
    if "items" in payload:
        return payload["items"] if isinstance(payload["items"], list) else None
    response = payload.get("response")
    if isinstance(response, Mapping) and "items" in response:
        return response["items"] if isinstance(response["items"], list) else None
    return None


def build_manifest(
    reels: list[dict],
    cache_roots: list[Path],
    media_roots: list[Path],
    explicit_map: dict | None = None,
) -> dict:
    """Index every requested identity and all locally observable media routes.

    ``cache_roots`` and ``media_roots`` are explicit roots.  Cache JSON files
    are limited to 32 MiB before parsing.  Cache URLs are ordered by descending
    observed cache mtime, then by file path and item/version order.  A later
    observation of the same URL supersedes its older provenance entry.
    """

    if not isinstance(reels, list):
        raise TypeError("reels must be a list")
    cache_roots = _root_entries(cache_roots)
    media_roots = _root_entries(media_roots)
    issues: list[dict[str, Any]] = []

    entries: list[dict[str, Any]] = []
    for index, reel in enumerate(reels):
        if isinstance(reel, Mapping):
            reel_id = reel.get("reel_id")
            code = reel.get("code")
        else:
            reel_id = None
            code = None
        reasons: list[str] = []
        if not isinstance(reel_id, str) or not reel_id.strip():
            reasons.append("invalid_reel_id")
            _issue(issues, "invalid_identity", identity_index=index, detail="reel_id")
        if not isinstance(code, str) or not SAFE_CODE.fullmatch(code):
            reasons.append("unsafe_code")
            _issue(issues, "unsafe_code", identity_index=index, code=code if isinstance(code, str) else None)
        entries.append(
            {
                "identity_index": index,
                "reel_id": reel_id if isinstance(reel_id, str) else None,
                "code": code if isinstance(code, str) else None,
                "quarantine_reasons": reasons,
                "sources": [],
            }
        )

    by_reel_id: dict[str, list[int]] = {}
    by_code: dict[str, list[int]] = {}
    for index, entry in enumerate(entries):
        if isinstance(entry["reel_id"], str) and entry["reel_id"].strip():
            by_reel_id.setdefault(entry["reel_id"], []).append(index)
        if isinstance(entry["code"], str) and SAFE_CODE.fullmatch(entry["code"]):
            by_code.setdefault(entry["code"], []).append(index)
    for value_map, reason, issue_type, key_name in (
        (by_reel_id, "duplicate_reel_id", "duplicate_reel_id", "reel_id"),
        (by_code, "duplicate_code", "duplicate_code", "code"),
    ):
        for value, indexes in value_map.items():
            if len(indexes) > 1:
                for index in indexes:
                    if reason not in entries[index]["quarantine_reasons"]:
                        entries[index]["quarantine_reasons"].append(reason)
                    _issue(issues, issue_type, identity_index=index, code=value if key_name == "code" else None)

    valid_codes = {
        entry["code"]
        for entry in entries
        if isinstance(entry["code"], str)
        and SAFE_CODE.fullmatch(entry["code"])
        and not entry["quarantine_reasons"]
    }

    identity_hash_input = [
        {
            "identity_index": index,
            "reel_id": _identity_value(entry["reel_id"]),
            "code": _identity_value(entry["code"]),
        }
        for index, entry in enumerate(entries)
    ]
    input_identity_hash = _digest(identity_hash_input)

    cache_records: list[dict[str, Any]] = []
    seen_cache_files: set[Path] = set()
    for root_index, root in enumerate(cache_roots):
        if not root.is_dir():
            _issue(issues, "cache_root_unavailable", path=f"cache_root[{root_index}]")
            continue
        try:
            paths = sorted(root.rglob("*clips*.json"), key=lambda path: path.as_posix())
        except OSError:
            _issue(issues, "cache_root_unavailable", path=f"cache_root[{root_index}]")
            continue
        for path in paths:
            info = _path_info(path, root)
            if info is None:
                _issue(issues, "symlink_escape", path=f"cache_root[{root_index}]/{path.name}")
                continue
            resolved, relative = info
            if resolved in seen_cache_files:
                continue
            seen_cache_files.add(resolved)
            try:
                stat_result = resolved.stat()
                size = stat_result.st_size
                mtime = stat_result.st_mtime
            except OSError:
                _issue(issues, "cache_file_unreadable", path=relative)
                continue
            record: dict[str, Any] = {
                "root_index": root_index,
                "root": root,
                "path": path,
                "resolved": resolved,
                "relative": relative,
                "size_bytes": size,
                "observed_mtime": mtime,
                "sha256": None,
                "payload": None,
            }
            try:
                record["sha256"] = _sha256_stream(resolved)
            except OSError:
                _issue(issues, "cache_file_unreadable", path=relative)
                continue
            if size > MAX_CACHE_BYTES:
                _issue(issues, "cache_file_too_large", path=relative, detail="32MiB_limit")
                cache_records.append(record)
                continue
            try:
                payload = json.loads(resolved.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
                _issue(issues, "malformed_cache_json", path=relative)
                cache_records.append(record)
                continue
            items = _extract_cache_items(payload)
            if items is None:
                _issue(issues, "malformed_cache_payload", path=relative, detail="items_missing_or_not_list")
            else:
                record["payload"] = items
            cache_records.append(record)

    cache_records.sort(key=lambda record: (record["observed_mtime"], record["relative"]), reverse=True)
    cache_urls: dict[str, list[dict[str, Any]]] = {code: [] for code in valid_codes}
    seen_urls: dict[str, set[str]] = {code: set() for code in valid_codes}
    for record in cache_records:
        items = record["payload"]
        if not isinstance(items, list):
            continue
        for item_index, original_item in enumerate(items):
            item = original_item
            if isinstance(item, Mapping) and isinstance(item.get("media"), Mapping):
                item = item["media"]
            if not isinstance(item, Mapping):
                _issue(issues, "malformed_cache_item", path=record["relative"], detail=f"item_{item_index}")
                continue
            code = item.get("code")
            if not isinstance(code, str):
                _issue(issues, "malformed_cache_item", path=record["relative"], detail=f"item_{item_index}_code")
                continue
            if code not in valid_codes:
                continue
            versions = item.get("video_versions")
            if versions is None:
                _issue(issues, "missing_video_versions", path=record["relative"], code=code)
                continue
            if not isinstance(versions, list):
                _issue(issues, "malformed_video_versions", path=record["relative"], code=code)
                continue
            for version_index, version in enumerate(versions):
                if not isinstance(version, Mapping):
                    _issue(issues, "malformed_video_version", path=record["relative"], code=code, detail=f"version_{version_index}")
                    continue
                url = version.get("url")
                if not _safe_private_url(url):
                    if url is not None:
                        _issue(issues, "invalid_media_url", path=record["relative"], code=code, detail="https_required")
                    else:
                        _issue(issues, "missing_media_url", path=record["relative"], code=code, detail=f"version_{version_index}")
                    continue
                if url in seen_urls[code]:
                    continue
                seen_urls[code].add(url)
                cache_urls[code].append(
                    {
                        "route": "cached_hiker_url",
                        "url": url,
                        "cache_relative_path": record["relative"],
                        "cache_sha256": record["sha256"],
                        "observed_mtime": record["observed_mtime"],
                    }
                )

    explicit_values: dict[str, list[Any]] = {}
    if explicit_map is not None:
        if not isinstance(explicit_map, Mapping):
            _issue(issues, "malformed_explicit_map", detail="mapping_required")
        else:
            for raw_code, raw_value in explicit_map.items():
                code = raw_code if isinstance(raw_code, str) else None
                if code not in valid_codes:
                    _issue(issues, "unknown_explicit_code", code=code)
                    continue
                values = raw_value if isinstance(raw_value, list) else [raw_value]
                if not values:
                    _issue(issues, "empty_explicit_urls", code=code)
                    continue
                explicit_values[code] = values

    explicit_urls: dict[str, list[dict[str, Any]]] = {code: [] for code in valid_codes}
    for code, values in explicit_values.items():
        for url in values:
            if not _safe_private_url(url):
                _issue(issues, "invalid_media_url", code=code, detail="https_required")
                continue
            if url in seen_urls[code]:
                continue
            seen_urls[code].add(url)
            explicit_urls[code].append({"route": "explicit_url", "url": url})

    media_records: list[dict[str, Any]] = []
    seen_media_files: set[Path] = set()
    for root_index, root in enumerate(media_roots):
        if not root.is_dir():
            _issue(issues, "media_root_unavailable", path=f"media_root[{root_index}]")
            continue
        try:
            paths = sorted(root.rglob("*"), key=lambda path: path.as_posix())
        except OSError:
            _issue(issues, "media_root_unavailable", path=f"media_root[{root_index}]")
            continue
        for path in paths:
            if path.suffix.lower() not in MEDIA_SUFFIXES or path.stem not in valid_codes:
                continue
            info = _path_info(path, root)
            if info is None:
                _issue(issues, "symlink_escape", path=f"media_root[{root_index}]/{path.name}", code=path.stem)
                continue
            resolved, relative = info
            if resolved in seen_media_files:
                continue
            seen_media_files.add(resolved)
            try:
                if not resolved.is_file():
                    continue
                sha256 = _sha256_stream(resolved)
                stat_result = resolved.stat()
            except OSError:
                _issue(issues, "media_file_unreadable", path=relative, code=path.stem)
                continue
            media_records.append(
                {
                    "code": path.stem,
                    "route": "existing_media",
                    "path": str(path.absolute()),
                    "sha256": sha256,
                    "size_bytes": stat_result.st_size,
                    "observed_mtime": stat_result.st_mtime,
                    "root_relative_path": relative,
                    "root_index": root_index,
                }
            )

    media_by_code: dict[str, list[dict[str, Any]]] = {code: [] for code in valid_codes}
    for record in media_records:
        media_by_code[record["code"]].append(record)
    for entry in entries:
        code = entry["code"]
        if code not in valid_codes:
            continue
        # Existing local media lets the downloader short-circuit.  Remote
        # candidates retain latest-cache-first ordering inside the URL routes.
        entry["sources"].extend(media_by_code[code])
        entry["sources"].extend(cache_urls[code])
        entry["sources"].extend(explicit_urls[code])

    cache_provenance = [
        {
            "root_index": record["root_index"],
            "relative_path": record["relative"],
            "sha256": record["sha256"],
            "size_bytes": record["size_bytes"],
            "observed_mtime": record["observed_mtime"],
        }
        for record in cache_records
    ]
    media_provenance = [
        {
            "root_index": record["root_index"],
            "relative_path": record["root_relative_path"],
            "sha256": record["sha256"],
            "size_bytes": record["size_bytes"],
            "observed_mtime": record["observed_mtime"],
        }
        for record in media_records
    ]
    try:
        explicit_map_sha256 = _digest(explicit_map) if isinstance(explicit_map, Mapping) else None
    except (TypeError, ValueError):
        explicit_map_sha256 = None
        _issue(issues, "malformed_explicit_map", detail="values_not_json")
    explicit_provenance = {
        "provided": explicit_map is not None,
        "sha256": explicit_map_sha256,
    }
    provenance = {
        "cache_files": cache_provenance,
        "media_files": media_provenance,
        "explicit_map": explicit_provenance,
    }

    route_counts = {"cached_hiker_url": 0, "explicit_url": 0, "existing_media": 0}
    for entry in entries:
        for source in entry["sources"]:
            route = source.get("route")
            if route in route_counts:
                route_counts[route] += 1
    quarantined = sum(bool(entry["quarantine_reasons"]) for entry in entries)
    with_sources = sum(bool(entry["sources"]) for entry in entries)
    absent = len(entries) - with_sources
    counts = {
        "input_identities": len(entries),
        "valid_identities": len(entries) - quarantined,
        "quarantined_identities": quarantined,
        "entries_with_sources": with_sources,
        "entries_without_sources": absent,
        "cache_files_scanned": len(cache_records),
        "media_files_scanned": len(media_records),
        "issues": len(issues),
        "sources": sum(route_counts.values()),
        "cached_hiker_urls": route_counts["cached_hiker_url"],
        "explicit_urls": route_counts["explicit_url"],
        "existing_media": route_counts["existing_media"],
    }
    return {
        "schema": SCHEMA,
        "entries": entries,
        "issues": issues,
        "counts": counts,
        "input_identity_hash": input_identity_hash,
        "source_hash_provenance": provenance,
        "source_hash_provenance_hash": _digest(provenance),
    }


__all__ = ["build_manifest"]
