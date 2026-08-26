from scripts.youtube_frames_100 import select_timestamps


def test_select_timestamps_preserves_hook_and_limits_output():
    values = select_timestamps(30.0, [index * 0.7 for index in range(1, 40)], limit=12)
    assert len(values) <= 12
    assert 0.4 in values
    assert 1.2 in values
    assert 2.4 in values
    assert values == sorted(values)


def test_select_timestamps_handles_zero_duration():
    assert select_timestamps(0, [1.0]) == []
