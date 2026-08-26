from pathlib import Path

from scripts.recover_transcript_manifest_conflicts import conflict_video_id, quarantine


def test_numbered_conflict_name_maps_to_canonical_video_identity():
    assert conflict_video_id(Path("abc_DEF-123 2.json")) == "abc_DEF-123"
    assert conflict_video_id(Path("abc_DEF-123 19.json")) == "abc_DEF-123"
    assert conflict_video_id(Path("abc_DEF-123.json")) is None


def test_quarantine_preserves_copy_without_reading_its_bytes(tmp_path, monkeypatch):
    source = tmp_path / "abc_DEF-123 2.json"
    source.write_text('{"stale": true}', encoding="utf-8")
    target_dir = tmp_path / "quarantine"

    def fail_if_hydrated(*_args, **_kwargs):
        raise AssertionError("quarantine must not force byte hydration")

    monkeypatch.setattr(Path, "read_bytes", fail_if_hydrated)
    target_name = quarantine(source, target_dir)

    assert not source.exists()
    assert (target_dir / target_name).read_text(encoding="utf-8") == '{"stale": true}'
