import hashlib
import json
from pathlib import Path

import pytest

import m2_orchestrator.scene_media as scene_media


def fixture_inputs(tmp_path: Path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"retained scene source")
    media = {
        "media_id": "fixture",
        "reel_id": "fixture-reel",
        "source_pointer": source.name,
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "duration_ms": 1000,
        "frame_pts_ms": list(range(0, 1000, 100)),
        "observation_state": "OBSERVED",
        "source_kind": "approved_research_copy",
        "rights": {"analysis_allowed": True, "receipt_id": "rights-fixture", "public_display_allowed": False},
    }
    transcript = {
        "schema": "m2.transcript-evidence.v1",
        "source_media_hash": media["sha256"],
        "observation_state": "OBSERVED",
        "segments": [
            {"segment_id": "T00001", "start_ms": 0, "end_ms": 500, "text": "first", "words": []},
            {"segment_id": "T00002", "start_ms": 500, "end_ms": 1000, "text": "second", "words": []},
        ],
    }
    annotations = [
        {"scene_id": "S01", "start_ms": 0, "end_ms": 500, "sample_count": 2, "maker": "maker", "information_job": "first job", "boundary_reasons": ["goal_change"], "transcript_segment_ids": ["T00001"]},
        {"scene_id": "S02", "start_ms": 500, "end_ms": 1000, "sample_count": 2, "maker": "maker", "information_job": "second job", "boundary_reasons": ["action_change"], "transcript_segment_ids": ["T00002"]},
    ]
    return source, media, transcript, annotations


def test_extract_scene_media_decodes_global_union_once_and_preserves_pts(monkeypatch, tmp_path):
    source, media, transcript, annotations = fixture_inputs(tmp_path)
    calls = []

    def fake_extract(source_path, output, frames, receipts):
        calls.append((source_path, list(frames)))
        for frame in frames:
            target = output / f"{frame['frame_id']}.jpg"
            target.write_bytes(frame["frame_id"].encode())
            frame.update({"observation_state": "OBSERVED", "failure_code": None, "source_pointer": target.name, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "width_px": 480})
        receipts.append({"stage": "frame_decode", "returncode": 0, "threads": 2})
        return frames

    def fake_collage(frames, output, filename):
        target = output / filename
        target.write_bytes(b"collage")
        return {"observation_state": "OBSERVED", "source_pointer": filename, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "sample_count": len(frames)}

    monkeypatch.setattr(scene_media, "_extract_indexed_frames", fake_extract)
    monkeypatch.setattr(scene_media, "build_collage", fake_collage)
    result = scene_media.extract_scene_media(tmp_path, media, transcript, annotations, tmp_path / "scene-output")

    assert len(calls) == 1
    assert [frame["frame_index"] for frame in calls[0][1]] == [0, 4, 5, 9]
    assert len({frame["frame_index"] for frame in calls[0][1]}) == 4
    assert result["planned_frame_count"] == 4
    assert result["observed_frame_count"] == 4
    assert result["frame_observation_state"] == "OBSERVED"
    assert [scene["observed_frame_count"] for scene in result["scene_units"]] == [2, 2]
    assert all(scene["observation_state"] == "OBSERVED" for scene in result["scene_units"])
    assert all(frame["timestamp_source"] == "decoded_frame_pts_ms" for frame in calls[0][1])
    assert json.loads((tmp_path / "scene-output" / "receipt.json").read_text())["manifest_sha256"] == result["manifest_sha256"]


def test_source_and_transcript_validation_happens_before_output_creation(tmp_path):
    source, media, transcript, annotations = fixture_inputs(tmp_path)
    transcript["source_media_hash"] = "b" * 64
    output = tmp_path / "scene-output"
    with pytest.raises(scene_media.SceneMediaError, match="TRANSCRIPT_SOURCE_MEDIA_MISMATCH"):
        scene_media.extract_scene_media(tmp_path, media, transcript, annotations, output)
    assert not output.exists()


def test_repeated_decoded_index_across_scenes_fails_closed(monkeypatch, tmp_path):
    source, media, transcript, annotations = fixture_inputs(tmp_path)

    def duplicate_sampling(scene, pts):
        return [{"frame_index": 0, "timestamp_ms": 0, "role": "start"}] * scene["sample_count"]

    monkeypatch.setattr(scene_media, "sampling_pts", duplicate_sampling)
    output = tmp_path / "scene-output"
    with pytest.raises(scene_media.SceneMediaError, match="DUPLICATE_DECODED_FRAME_INDEX"):
        scene_media.extract_scene_media(tmp_path, media, transcript, annotations, output)
    assert not output.exists()


def test_partial_frame_results_keep_planned_and_observed_counts(monkeypatch, tmp_path):
    source, media, transcript, annotations = fixture_inputs(tmp_path)

    def partial_extract(source_path, output, frames, receipts):
        for index, frame in enumerate(frames):
            if index == 1:
                frame.update({"observation_state": "UNAVAILABLE", "failure_code": "FRAME_OUTPUT_INVALID"})
                continue
            target = output / f"{frame['frame_id']}.jpg"
            target.write_bytes(b"frame")
            frame.update({"observation_state": "OBSERVED", "failure_code": None, "source_pointer": target.name, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
        return frames

    def fake_collage(frames, output, filename):
        (output / filename).write_bytes(b"collage")
        return {"observation_state": "OBSERVED", "source_pointer": filename, "sample_count": len(frames)}

    monkeypatch.setattr(scene_media, "_extract_indexed_frames", partial_extract)
    monkeypatch.setattr(scene_media, "build_collage", fake_collage)
    result = scene_media.extract_scene_media(tmp_path, media, transcript, annotations, tmp_path / "scene-output")

    assert result["planned_frame_count"] == 4
    assert result["observed_frame_count"] == 3
    assert result["frame_observation_state"] == "PARTIAL"
    assert result["observation_state"] == "PARTIAL"
    assert result["scene_units"][0]["planned_sample_count"] == 2
    assert result["scene_units"][0]["observed_frame_count"] == 1
    assert result["scene_units"][0]["observation_state"] == "PARTIAL"
    assert result["scene_units"][0]["frame_failures"][0]["failure_code"] == "FRAME_OUTPUT_INVALID"


def test_existing_output_and_rights_are_rejected(tmp_path):
    source, media, transcript, annotations = fixture_inputs(tmp_path)
    output = tmp_path / "scene-output"
    output.mkdir()
    with pytest.raises(scene_media.SceneMediaError, match="OUTPUT_ALREADY_EXISTS"):
        scene_media.extract_scene_media(tmp_path, media, transcript, annotations, output)
    output.rmdir()
    media["rights"] = {"analysis_allowed": False, "receipt_id": "rights-fixture"}
    with pytest.raises(scene_media.SceneMediaError, match="RIGHTS_BLOCKED"):
        scene_media.extract_scene_media(tmp_path, media, transcript, annotations, output)
    assert not output.exists()
