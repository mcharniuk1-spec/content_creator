from pathlib import Path

from scripts.analyze_youtube_calibration import hook_text
from scripts.youtube_evidence_300 import de_roll_caption_segments, parse_vtt_segments


def test_parse_vtt_segments_deduplicates_consecutive_caption_lines(tmp_path: Path):
    path = tmp_path / "x.vtt"
    path.write_text(
        "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nHello <b>world</b>\n\n00:00:01.000 --> 00:00:02.000\nHello world\n\n00:00:02.000 --> 00:00:03.000\nNext &amp; final\n",
        encoding="utf-8",
    )
    assert parse_vtt_segments(path) == [
        {"start_ms": 0, "end_ms": 1000, "text": "Hello world"},
        {"start_ms": 2000, "end_ms": 3000, "text": "Next & final"},
    ]


def test_de_roll_caption_segments_preserves_only_new_speech_tokens():
    segments = [
        {"start_ms": 0, "end_ms": 1000, "text": "This is a rolling"},
        {"start_ms": 500, "end_ms": 1500, "text": "This is a rolling caption"},
        {"start_ms": 1000, "end_ms": 2000, "text": "a rolling caption example."},
    ]
    speech = de_roll_caption_segments(segments)
    assert " ".join(item["text"] for item in speech) == "This is a rolling caption example."
    assert [item["source_overlap_tokens"] for item in speech] == [0, 4, 3]


def test_de_roll_caption_segments_keeps_non_overlapping_cues():
    segments = [
        {"start_ms": 0, "end_ms": 1000, "text": "First sentence."},
        {"start_ms": 1000, "end_ms": 2000, "text": "Second sentence."},
    ]
    assert [item["text"] for item in de_roll_caption_segments(segments)] == [
        "First sentence.",
        "Second sentence.",
    ]


def test_de_roll_caption_segments_matches_case_and_edge_punctuation():
    segments = [
        {"start_ms": 0, "end_ms": 1000, "text": "Build the Agent"},
        {"start_ms": 500, "end_ms": 1500, "text": "build the agent, safely."},
    ]
    assert " ".join(item["text"] for item in de_roll_caption_segments(segments)) == "Build the Agent safely."


def test_de_roll_caption_segments_ignores_punctuation_only_increment():
    segments = [
        {"start_ms": 0, "end_ms": 1000, "text": "Useful text"},
        {"start_ms": 500, "end_ms": 1500, "text": "Useful text ..."},
    ]
    assert " ".join(item["text"] for item in de_roll_caption_segments(segments)) == "Useful text"


def test_hook_text_rejects_segment_that_crosses_ten_second_boundary():
    transcript = {
        "speech_segments": [
            {"start_ms": 0, "end_ms": 12000, "text": "This cue crosses the strict boundary."}
        ]
    }
    assert hook_text(transcript, "Safe title proxy") == ("Safe title proxy", "title_proxy")
