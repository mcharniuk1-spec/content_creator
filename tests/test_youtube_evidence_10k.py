from pathlib import Path

import pytest

from scripts.youtube_evidence_10k import DiskReserveError, ensure_disk_reserve, pick_indexes


def test_pick_indexes_is_bounded_and_keeps_endpoints():
    indexes = pick_indexes(100, 6)
    assert len(indexes) == 6
    assert indexes[0] == 0
    assert indexes[-1] == 99
    assert indexes == sorted(set(indexes))


def test_pick_indexes_keeps_small_storyboard():
    assert pick_indexes(3, 6) == [0, 1, 2]
    assert pick_indexes(0, 6) == []


def test_disk_reserve_stops_before_write(tmp_path: Path):
    with pytest.raises(DiskReserveError):
        ensure_disk_reserve(tmp_path, minimum_free_bytes=100, free_override=99)
    ensure_disk_reserve(tmp_path, minimum_free_bytes=100, free_override=100)
