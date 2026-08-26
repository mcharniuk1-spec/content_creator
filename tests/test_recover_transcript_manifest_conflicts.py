from pathlib import Path

from scripts.recover_transcript_manifest_conflicts import conflict_video_id


def test_numbered_conflict_name_maps_to_canonical_video_identity():
    assert conflict_video_id(Path("abc_DEF-123 2.json")) == "abc_DEF-123"
    assert conflict_video_id(Path("abc_DEF-123 19.json")) == "abc_DEF-123"
    assert conflict_video_id(Path("abc_DEF-123.json")) is None
