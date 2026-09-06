import json
from pathlib import Path

import pytest

import m2_orchestrator.media_visual as visual


def media_record() -> dict:
    return {
        "media_id": "fixture",
        "reel_id": "reel-fixture",
        "sha256": "a" * 64,
        "duration_ms": 1000,
        "frame_pts_ms": [0, 100, 200, 300, 400, 500, 600, 700, 800, 900],
        "rights": {"analysis_allowed": True, "receipt_id": "fixture", "public_display_allowed": False},
        "observation_state": "OBSERVED",
        "source_pointer": "fixture.mp4",
    }


def test_cut_candidates_are_mapped_to_real_adjacent_decoded_frames():
    assert visual._cut_times(b"pts_time:0.300\npts_time:0.301\npts_time:0.900\n", 1000) == [300, 900]
    assert visual._frame_for_cut(media_record()["frame_pts_ms"], 350) == (3, 4)
    assert visual._frame_for_cut(media_record()["frame_pts_ms"], 0) == (None, 0)


def test_extract_preview_uses_one_indexed_decode_and_emits_change_types(monkeypatch, tmp_path: Path):
    source = tmp_path / "fixture.mp4"
    source.write_bytes(b"retained-video")
    output = tmp_path / "visual"
    media = media_record()

    monkeypatch.setattr(visual, "observed_source", lambda root, record: source)
    monkeypatch.setattr(visual, "build_collage", lambda frames, root, filename: {
        "observation_state": "OBSERVED", "source_pointer": filename, "sample_count": len(frames)
    })
    calls = []

    def fake_bounded(args, **kwargs):
        calls.append((args, kwargs))
        if "showinfo" in " ".join(args):
            return {"returncode": 0, "stdout": b"", "stderr": b"pts_time:0.500\n", "elapsed_seconds": .01,
                    "sampled_peak_rss_bytes": 1234, "rss_poll_seconds": .2}
        pattern = Path(args[-1])
        for n in range(1, 7):
            (pattern.parent / f"decoded-{n:03d}.jpg").write_bytes(f"frame-{n}".encode())
        return {"returncode": 0, "stdout": b"", "stderr": b"", "elapsed_seconds": .02,
                "sampled_peak_rss_bytes": 2345, "rss_poll_seconds": .2}

    monkeypatch.setattr(visual, "bounded_process", fake_bounded)
    result = visual.extract_preview(tmp_path, media, output, count=4, threshold=.2)

    assert len(calls) == 2
    assert calls[0][1]["timeout"] == 120
    assert calls[0][1]["rss_limit_bytes"] == 512 * 1024 * 1024
    assert all(calls[1][0][i] != "-i" or calls[1][0][i + 1] == str(source) for i in range(len(calls[1][0]) - 1))
    assert len(result["sampled_frames"]) == 6
    assert {frame["sample_type"] for frame in result["sampled_frames"]} == {"regular", "cut_before", "cut_after"}
    assert len({frame["frame_index"] for frame in result["sampled_frames"]}) == len(result["sampled_frames"])
    assert all(frame["timestamp_source"] == "decoded_frame_pts_ms" for frame in result["sampled_frames"])
    assert result["frame_observation_state"] == "OBSERVED"
    assert result["semantic_scene_state"] == "NOT_REVIEWED"
    assert result["public_display_allowed"] is False
    assert result["retention"]["source_video"] == "RETAINED"
    assert json.loads((output / "receipt.json").read_text())["manifest_sha256"] == result["manifest_sha256"]


def test_frame_decode_failure_is_retained_as_partial_typed_attempt(monkeypatch, tmp_path: Path):
    source = tmp_path / "fixture.mp4"
    source.write_bytes(b"retained-video")
    media = media_record()
    monkeypatch.setattr(visual, "observed_source", lambda root, record: source)
    monkeypatch.setattr(visual, "build_collage", lambda frames, root, filename: {"sample_count": len(frames)})

    def fake_bounded(args, **kwargs):
        if "showinfo" in " ".join(args):
            return {"returncode": 0, "stdout": b"", "stderr": b"", "elapsed_seconds": .01,
                    "sampled_peak_rss_bytes": 1, "rss_poll_seconds": .2}
        return {"returncode": 1, "stdout": b"", "stderr": b"private ffmpeg detail", "elapsed_seconds": .01,
                "sampled_peak_rss_bytes": 1, "rss_poll_seconds": .2}

    monkeypatch.setattr(visual, "bounded_process", fake_bounded)
    result = visual.extract_preview(tmp_path, media, tmp_path / "visual", count=2)

    assert result["frame_observation_state"] == "DECODE_FAILED"
    assert len(result["frame_failures"]) == 2
    assert all(item["failure_code"] == "VISUAL_DECODE_FAILED" for item in result["frame_failures"])
    assert result["sampled_frames"] == []
    assert "frame_failures" in result["limitations"][-1]


def test_output_symlink_and_budget_are_rejected(tmp_path: Path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(visual.VisualExtractionError, match="OUTPUT_SYMLINK_UNSAFE"):
        visual._safe_output_dir(link)
    with pytest.raises(visual.VisualExtractionError, match="INVALID_FRAME_BUDGET"):
        visual.extract_preview(tmp_path, media_record(), tmp_path / "budget", count=2, max_frames=1)


def test_missing_middle_output_never_shifts_frame_identity(tmp_path, monkeypatch):
    frames=[{'frame_id':f'F{i:03}', 'frame_index':i*10} for i in range(1,4)]
    def fake(*args, **kwargs):
        (tmp_path/'decoded-001.jpg').write_bytes(b'first')
        (tmp_path/'decoded-003.jpg').write_bytes(b'third')
        return {'returncode':0}
    monkeypatch.setattr(visual,'_run_ffmpeg',fake)
    result=visual._extract_indexed_frames(tmp_path/'source.mp4',tmp_path,frames,[])
    assert all(x['observation_state']=='UNAVAILABLE' for x in result)
    assert all(x['failure_code']=='DECODED_SEQUENCE_MISMATCH' for x in result)
    assert not list(tmp_path.glob('F*.jpg'))
