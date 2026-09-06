from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from m2_orchestrator.media_manifest import build_manifest


def _write(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _entry(manifest: dict, code: str) -> dict:
    return next(item for item in manifest["entries"] if item["code"] == code)


def test_cache_dialects_preserve_all_urls_and_latest_cache_first(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    old = _write(
        cache / "old-clips.json",
        {"items": [{"code": "ABCde1", "video_versions": [{"url": "https://cdn.example/old"}, {"url": "https://cdn.example/old-2"}]}]},
    )
    new = _write(
        cache / "new-clips.json",
        {"response": {"items": [{"code": "ABCde1", "video_versions": [{"url": "https://cdn.example/new"}, {"url": "https://cdn.example/new-2"}]}]}},
    )
    os.utime(old, (100, 100))
    os.utime(new, (200, 200))

    manifest = build_manifest([{"reel_id": "r-1", "code": "ABCde1"}], [cache], [], None)
    sources = _entry(manifest, "ABCde1")["sources"]
    assert [source["url"] for source in sources] == [
        "https://cdn.example/new",
        "https://cdn.example/new-2",
        "https://cdn.example/old",
        "https://cdn.example/old-2",
    ]
    assert all(source["route"] == "cached_hiker_url" for source in sources)
    assert sources[0]["cache_relative_path"] == "new-clips.json"
    assert len(manifest["source_hash_provenance"]["cache_files"]) == 2


def test_existing_media_is_hashed_and_explicit_urls_are_appended(tmp_path: Path) -> None:
    media = tmp_path / "media"
    media_file = media / "ABCde1.mp4"
    media_file.parent.mkdir()
    media_file.write_bytes(b"video fixture")
    manifest = build_manifest(
        [{"reel_id": "r-1", "code": "ABCde1"}],
        [],
        [media],
        {"ABCde1": ["https://cdn.example/one", "https://cdn.example/two"]},
    )
    sources = _entry(manifest, "ABCde1")["sources"]
    assert sources[0]["route"] == "existing_media"
    assert sources[0]["path"] == str(media_file.absolute())
    assert len(sources[0]["sha256"]) == 64
    assert [source["route"] for source in sources[1:]] == ["explicit_url", "explicit_url"]
    assert manifest["counts"]["existing_media"] == 1


def test_duplicate_and_invalid_identities_are_quarantined_without_drop(tmp_path: Path) -> None:
    reels = [
        {"reel_id": "same", "code": "ABCde1"},
        {"reel_id": "same", "code": "ABCde1"},
        {"reel_id": "unsafe", "code": "bad/code"},
        {"reel_id": None, "code": "short"},
    ]
    manifest = build_manifest(reels, [], [], None)
    assert len(manifest["entries"]) == len(reels)
    assert all(entry["quarantine_reasons"] for entry in manifest["entries"])
    assert manifest["counts"]["quarantined_identities"] == 4
    assert any(issue["type"] == "duplicate_code" for issue in manifest["issues"])
    assert any(issue["type"] == "unsafe_code" for issue in manifest["issues"])


def test_absent_entries_are_retained_with_empty_sources(tmp_path: Path) -> None:
    manifest = build_manifest([{"reel_id": "r-1", "code": "ABCde1"}, {"reel_id": "r-2", "code": "ABCde2"}], [], [], None)
    assert len(manifest["entries"]) == 2
    assert all(entry["sources"] == [] for entry in manifest["entries"])
    assert manifest["counts"]["entries_without_sources"] == 2


def test_malformed_and_unsafe_urls_are_structured_and_masked(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    _write(
        cache / "bad-clips.json",
        {
            "items": [
                {"code": "ABCde1", "video_versions": [{"url": "file:///private/secret"}, {"url": "https://cdn.example/good"}]},
                "not-an-item",
            ]
        },
    )
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "broken-clips.json").write_bytes(b"not-json")
    manifest = build_manifest([{"reel_id": "r-1", "code": "ABCde1"}], [cache], [], None)
    assert [source["url"] for source in _entry(manifest, "ABCde1")["sources"]] == ["https://cdn.example/good"]
    issue_text = json.dumps(manifest["issues"], ensure_ascii=False)
    assert "file:///private/secret" not in issue_text
    assert any(issue["type"] == "invalid_media_url" for issue in manifest["issues"])
    assert any(issue["type"] == "malformed_cache_json" for issue in manifest["issues"])
    assert any(issue["type"] == "malformed_cache_item" for issue in manifest["issues"])


def test_cache_size_limit_is_enforced_before_json_parse(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    path = cache / "large-clips.json"
    path.parent.mkdir()
    with path.open("wb") as stream:
        stream.write(b"{" + b" " * (32 * 1024 * 1024) + b"}")
    manifest = build_manifest([{"reel_id": "r-1", "code": "ABCde1"}], [cache], [], None)
    assert any(issue["type"] == "cache_file_too_large" for issue in manifest["issues"])


def test_symlink_escape_is_rejected_for_cache_and_media(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_cache = _write(outside / "escape-clips.json", {"items": []})
    outside_media = outside / "ABCde1.mp4"
    outside_media.write_bytes(b"outside")
    cache = tmp_path / "cache"
    media = tmp_path / "media"
    cache.mkdir()
    media.mkdir()
    os.symlink(outside_cache, cache / "escape-clips.json")
    os.symlink(outside_media, media / "ABCde1.mp4")

    manifest = build_manifest([{"reel_id": "r-1", "code": "ABCde1"}], [cache], [media], None)
    assert _entry(manifest, "ABCde1")["sources"] == []
    assert sum(issue["type"] == "symlink_escape" for issue in manifest["issues"]) == 2


def test_explicit_map_accepts_string_or_list_and_rejects_arbitrary_schemes(tmp_path: Path) -> None:
    manifest = build_manifest(
        [{"reel_id": "r-1", "code": "ABCde1"}, {"reel_id": "r-2", "code": "ABCde2"}],
        [],
        [],
        {
            "ABCde1": "https://cdn.example/one",
            "ABCde2": ["http://cdn.example/no", "data:text/plain,secret", "https://cdn.example/two"],
        },
    )
    assert [source["url"] for source in _entry(manifest, "ABCde1")["sources"]] == ["https://cdn.example/one"]
    assert [source["url"] for source in _entry(manifest, "ABCde2")["sources"]] == ["https://cdn.example/two"]
    assert manifest["counts"]["explicit_urls"] == 2
    assert sum(issue["type"] == "invalid_media_url" for issue in manifest["issues"]) == 2


def test_non_list_reels_is_programmer_error() -> None:
    with pytest.raises(TypeError):
        build_manifest({"reel_id": "r-1", "code": "ABCde1"}, [], [], None)  # type: ignore[arg-type]
