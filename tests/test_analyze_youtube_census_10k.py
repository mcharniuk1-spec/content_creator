import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_youtube_census_10k import classify_video, select_top_references, validate_evidence_identity  # noqa: E402


def cohort_row(video_id: str = "video-1", creator_id: str = "creator-1") -> dict:
    return {
        "native_video_id": video_id,
        "native_channel_id": creator_id,
        "canonical_url": f"https://www.youtube.com/watch?v={video_id}",
        "title": "How to build a safe AI agent workflow",
        "description": "A business workflow tutorial with approval gates and rollback.",
        "duration_seconds": 45,
        "format_state": "DURATION_CANDIDATE",
        "native_short_proved": False,
        "analysis_eligible": True,
        "selection_state": "broad_screen",
        "view_count": 1000,
        "like_count": 50,
        "comment_count": 10,
        "relevance_signals": {"agent_hits": 3, "business_hits": 2, "proof_hits": 1},
    }


def test_classification_preserves_evidence_denominators() -> None:
    transcript = {
        "availability": "observed",
        "language": "en",
        "segments": [{"start_ms": 0, "end_ms": 5000, "text": "How do you stop an AI agent from breaking a business workflow?"}],
        "speech_text": "How do you stop an AI agent from breaking a business workflow? Add approval and rollback.",
        "segment_count": 1,
        "speech_segment_count": 1,
    }
    frames = {"status": "observed", "frames": [{"frame_index": 0}], "media": {"collection_method": "youtube_storyboard"}}
    result = classify_video(cohort_row(), transcript, frames, 500)
    assert result["analysis_eligible"] is True
    assert result["transcript_availability"] == "observed"
    assert result["hook_evidence_basis"] == "transcript_segments_ending_by_10s"
    assert result["frame_count"] == 1
    assert result["frame_state"] == "observed"


def test_title_proxy_is_explicit_when_transcript_missing() -> None:
    result = classify_video(cohort_row(), {}, {}, 1000)
    assert result["hook_evidence_basis"] == "title_proxy"
    assert result["transcript_availability"] == "gap"
    assert result["frame_state"] == "not_attempted"


def test_top_reference_selection_enforces_one_video_per_creator() -> None:
    rows = []
    for creator_index in range(120):
        for video_index in range(2):
            row = classify_video(
                cohort_row(f"v-{creator_index}-{video_index}", f"c-{creator_index}"),
                {"availability": "observed", "segments": [], "speech_text": "workflow agent business", "segment_count": 0},
                {"status": "observed", "frames": []},
                1000,
            )
            row["reference_score"] += video_index
            rows.append(row)
    selected = select_top_references(rows, 100)
    assert len(selected) == 100
    assert len({row["native_channel_id"] for row in selected}) == 100
    assert [row["reference_rank"] for row in selected] == list(range(1, 101))


def test_terminal_evidence_gate_requires_exact_cohort_identity() -> None:
    cohort_ids = {"video-1", "video-2"}
    validate_evidence_identity(
        cohort_ids,
        {"video-1": {}, "video-2": {}},
        {"video-1": {}, "video-2": {}},
        allow_partial=False,
    )
    try:
        validate_evidence_identity(
            cohort_ids,
            {"video-1": {}, "foreign": {}},
            {"video-1": {}, "video-2": {}},
            allow_partial=False,
        )
    except ValueError as error:
        assert "foreign evidence" in str(error)
    else:
        raise AssertionError("foreign transcript identity passed the terminal gate")
