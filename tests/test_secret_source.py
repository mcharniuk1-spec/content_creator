from pathlib import Path

import pytest

from m2_engine.secret_source import SecretSourceError, inventory, load_secret


def test_inventory_never_returns_values(tmp_path: Path) -> None:
    key = "AIza" + "a" * 35
    secret_file = tmp_path / "keys.md"
    secret_file.write_text(f"YouTube API key: {key}\n", encoding="utf-8")
    result = inventory(secret_file)
    assert result["services"]["youtube"] == {"present": True, "candidate_count": 1}
    assert key not in repr(result)


def test_load_secret_accepts_standalone_google_key(tmp_path: Path) -> None:
    key = "AIza" + "b" * 35
    secret_file = tmp_path / "keys.md"
    secret_file.write_text(key, encoding="utf-8")
    assert load_secret("youtube", secret_file=secret_file) == key


def test_load_secret_fails_closed_on_multiple_candidates(tmp_path: Path) -> None:
    secret_file = tmp_path / "keys.md"
    secret_file.write_text("\n".join(["AIza" + "c" * 35, "AIza" + "d" * 35]), encoding="utf-8")
    with pytest.raises(SecretSourceError, match="multiple"):
        load_secret("youtube", secret_file=secret_file)


def test_environment_precedes_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    environment_key = "AIza" + "e" * 35
    monkeypatch.setenv("YOUTUBE_API_KEY", environment_key)
    secret_file = tmp_path / "keys.md"
    secret_file.write_text("AIza" + "f" * 35, encoding="utf-8")
    assert load_secret("youtube", secret_file=secret_file) == environment_key


def test_labelled_secret_ignores_trailing_comment(tmp_path: Path) -> None:
    key = "AIza" + "g" * 35
    secret_file = tmp_path / "keys.md"
    secret_file.write_text(f"YouTube API key: `{key}` # local only", encoding="utf-8")
    assert load_secret("youtube", secret_file=secret_file) == key
