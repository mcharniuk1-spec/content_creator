#!/usr/bin/env python3
"""Convert frozen Forge beat sheets into exact FrameSequence packets."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "20260811-phase1-content-batch"
FORGE = RUN / "lanes" / "forge" / "prejury"
OUTPUTS = ROOT / "outputs" / "video-plans"
CANDIDATE_HASH = "sha256:7519764ef9d7d296e25613d1ce9a8e79fa5d8aa109636769ac9f732eafe22be4"
SELECTED = ["V01", "V02", "V03", "V05", "V07", "V08", "V09", "V10", "V11", "V12", "V13", "V15"]
COMPOSITIONS = [
    "generated_scene",
    "motion_graphic",
    "motion_graphic",
    "screen_capture",
    "screen_capture",
    "motion_graphic",
    "motion_graphic",
    "screen_capture",
    "motion_graphic",
    "generated_scene",
]


def transition_edge(video_id: str, edge_index: int) -> str:
    """Return one exact, duration-bound edge with explicit endpoints and motion."""
    if edge_index == 0:
        return f"START -> {video_id}-F01 | duration 200 ms | fade up from the approved local base plate."
    if edge_index == 10:
        return f"{video_id}-F10 -> END | duration 800 ms | hold the owner-review end card for 600 ms, then fade to the dark brand field over 200 ms."
    return (
        f"{video_id}-F{edge_index:02d} -> {video_id}-F{edge_index + 1:02d} | duration 250 ms | "
        "clean cross-state morph with shared object positions and caption safe zones held stable."
    )


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build(video_id: str) -> dict:
    candidate = load(FORGE / video_id / "candidate.json")
    plan = load(OUTPUTS / video_id / "content-plan.json")
    if candidate["candidate_set_hash"] != CANDIDATE_HASH or plan["candidate_set_hash"] != CANDIDATE_HASH:
        raise ValueError(f"candidate-set mismatch: {video_id}")
    expected_sequence_id = f"SEQ-{video_id}-PHASE1"
    if plan["frame_sequence_id"] != expected_sequence_id:
        raise ValueError(f"content-plan sequence link mismatch: {video_id}")
    production = candidate["production_spec"]
    beats = production["beats"]
    if len(beats) != 10:
        raise ValueError(f"expected ten beats: {video_id}")
    palette_id = "palette-onboarding-v1" if plan["campaign_domain"] == "archflow_onboarding" else "palette-hotel-v1"
    frames = []
    for index, beat in enumerate(beats):
        frame_id = f"{video_id}-F{index + 1:02d}"
        transition_in = transition_edge(video_id, index)
        transition_out = transition_edge(video_id, index + 1)
        base_prompt = (
            f"Use outputs/storyboard-base-plates/{video_id}.png as the original source-free atmosphere plate. "
            f"Recompose it as an editable clean-room scene for this beat: {beat['base_visual']} "
            "Do not bake text, logos, real UI, or source imagery into the base."
        )
        overlays = [
            beat["editable_overlay"],
            f"Editable on-screen label: {beat['on_screen_text']}",
            "Editable status/source/truth footer with owner-review and NOT RUN states.",
        ]
        frame = {
            "frame_id": frame_id,
            "sequence_number": index + 1,
            "start_ms": beat["start_ms"],
            "end_ms": beat["end_ms"],
            "story_function": beat["story_function"],
            "composition_type": COMPOSITIONS[index],
            "base_plate_prompt": base_prompt,
            "overlay_asset_prompts": overlays,
            "combined_composite_description": f"Original base plate plus the {beat['story_function']} state, deterministic label '{beat['on_screen_text']}', status footer, and caption-safe narration cue. All text remains editable and separate.",
            "camera_and_motion": beat["motion_intent"],
            "narration": beat["narration"],
            "on_screen_text": beat["on_screen_text"],
            "transition_in": transition_in,
            "transition_out": transition_out,
            "music_cue": production["audio_plan"]["music"],
            "sfx_cue": beat["audio_cue"],
            "continuity_ids": [
                f"base-plate-{video_id.lower()}-v1",
                palette_id,
                "type-system-archflow-previs-v1",
                "truth-footer-phase1-v1",
                "candidate-set-7519764e",
            ],
            "negative_constraints": production["negative_constraints"],
            "fallback": production["fallbacks"][index % len(production["fallbacks"])],
            "acceptance_checks": [
                beat["acceptance"],
                "Frame duration is exactly 3000 ms and the interval is contiguous with adjacent frames.",
                "Base, UI/illustration, text overlay, caption, status/footer, and audio cues remain separately specified.",
                "No external provider, final video, voice, music, Figma mutation, publication, or deployment is represented as executed.",
            ],
        }
        frames.append(frame)
    return {
        "sequence_id": f"SEQ-{video_id}-PHASE1",
        "video_id": video_id,
        "target_duration_ms": plan["target_duration_ms"],
        "aspect_ratio": "9:16",
        "frames": frames,
        "contact_sheet_path": f"outputs/video-plans/{video_id}/{video_id}-sequence-board.png",
        "individual_frame_paths": [f"outputs/video-plans/{video_id}/individual-frames/{video_id}-F{index:02d}.png" for index in range(1, 11)],
        "storyboard_asset_state": "MIXED_LOCAL_READY",
        "external_provider_generation_state": "NOT_RUN",
        "owner_state": "OWNER_REVIEW_PENDING",
        "review": {
            "maker": "Canvas",
            "reviewer": "Sight",
            "verdict": "PENDING",
            "notes": "Exact frozen Forge beats plus original local Codex base plate and deterministic editable overlays; independent previsualization review pending."
        },
    }


def validate(sequence: dict) -> None:
    frames = sequence["frames"]
    assert len(frames) == 10
    assert frames[0]["start_ms"] == 0
    assert frames[-1]["end_ms"] == sequence["target_duration_ms"]
    for index, frame in enumerate(frames):
        assert frame["sequence_number"] == index + 1
        assert frame["frame_id"] == f"{sequence['video_id']}-F{index + 1:02d}"
        assert frame["end_ms"] - frame["start_ms"] == 3000
        if index:
            assert frames[index - 1]["end_ms"] == frame["start_ms"]
        assert len(frame["negative_constraints"]) >= 1
        assert len(frame["acceptance_checks"]) >= 1
        assert frame["composition_type"] not in {"talking_head", "hybrid"}


def main() -> None:
    for video_id in SELECTED:
        sequence = build(video_id)
        validate(sequence)
        dump(OUTPUTS / video_id / "frame-sequence.json", sequence)
    print(json.dumps({"sequences": len(SELECTED), "frames": len(SELECTED) * 10, "candidate_set_hash": CANDIDATE_HASH}, indent=2))


if __name__ == "__main__":
    main()
