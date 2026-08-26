import copy

import pytest

from scripts.youtube_video_census_10k import (
    approved_creator_cap,
    build_cohort,
    creator_cap_config_sha256,
    validate_pinned_creator_cap,
)


def row(channel: int, video: int, short: bool = True, relevant: bool = True):
    return {
        "native_channel_id": f"c{channel:04d}",
        "native_video_id": f"v{channel:04d}-{video:02d}",
        "canonical_url": f"https://www.youtube.com/watch?v=v{channel:04d}-{video:02d}",
        "format_state": "DURATION_CANDIDATE" if short else "NON_SHORT",
        "native_short_proved": False,
        "analysis_eligible": relevant,
        "english_evidenced": True,
        "published_at": f"2026-08-{video + 1:02d}T00:00:00Z",
        "view_count": video,
        "raw_uri": f"raw/{channel}.json",
        "raw_sha256": f"{channel:064x}"[-64:],
        "relevance_signals": {"relevant": relevant, "agent_hits": int(relevant), "business_hits": int(relevant), "proof_hits": 0},
    }


def test_builds_exact_deterministic_cohort_with_creator_bounds_and_baseline():
    source = [row(channel, video, short=video < 8) for channel in range(120) for video in range(10)]
    baseline = [item for item in source if int(item["native_channel_id"][1:]) < 2 and int(item["native_video_id"].split("-")[1]) < 3]
    first, summary = build_cohort(source, baseline, target=1000, minimum_per_creator=3, maximum_per_creator=10)
    second, _ = build_cohort(copy.deepcopy(source), copy.deepcopy(baseline), target=1000, minimum_per_creator=3, maximum_per_creator=10)
    assert [item["native_video_id"] for item in first] == [item["native_video_id"] for item in second]
    assert len(first) == 1000
    assert summary["maximum_selected_per_creator"] == 10
    assert summary["maximum_creator_fraction"] == 0.01
    assert {item["native_video_id"] for item in baseline} <= {item["native_video_id"] for item in first}
    assert all(item["format_claim"] != "native_short_proved" for item in first)


def test_rejects_duplicate_source_video():
    source = [row(channel, video) for channel in range(2) for video in range(3)]
    with pytest.raises(ValueError, match="duplicate source video"):
        build_cohort(source + [copy.deepcopy(source[0])], [], target=3, maximum_per_creator=3)


def test_reports_insufficient_capacity():
    source = [row(channel, video) for channel in range(2) for video in range(3)]
    with pytest.raises(ValueError, match="insufficient eligible capacity"):
        build_cohort(source, [], target=7, maximum_per_creator=3)


def test_enforces_one_percent_creator_cap():
    source = [row(channel, video) for channel in range(4) for video in range(10)]
    with pytest.raises(ValueError, match="exceeds the approved"):
        build_cohort(source, [], target=30, maximum_per_creator=10)


def test_approved_creator_cap_is_loaded_from_config(tmp_path):
    config = tmp_path / "youtube.json"
    config.write_text('{"maximum_creator_contribution_fraction": 0.0075}', encoding="utf-8")
    assert approved_creator_cap(config) == 0.0075
    assert len(creator_cap_config_sha256(config)) == 64


def test_run_creator_cap_pin_detects_config_drift(tmp_path):
    config = tmp_path / "youtube.json"
    config.write_text('{"maximum_creator_contribution_fraction": 0.01}', encoding="utf-8")
    run = tmp_path / "run"
    (run / "derived").mkdir(parents=True)
    (run / "derived" / "cohort-summary.json").write_text(
        '{"approved_maximum_creator_fraction":0.01,"creator_cap_config_sha256":"'
        + creator_cap_config_sha256(config) + '"}',
        encoding="utf-8",
    )
    assert validate_pinned_creator_cap(run, config) == 0.01
    config.write_text('{"maximum_creator_contribution_fraction": 0.02}', encoding="utf-8")
    with pytest.raises(ValueError, match="drifted"):
        validate_pinned_creator_cap(run, config)


def test_custom_creator_cap_requires_matching_policy_hash():
    source = [row(channel, video) for channel in range(10) for video in range(3)]
    with pytest.raises(ValueError, match="policy hash"):
        build_cohort(source, [], target=30, maximum_per_creator=3, maximum_contribution_fraction=0.1)
