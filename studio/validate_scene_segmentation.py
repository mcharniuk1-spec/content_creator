#!/usr/bin/env python3
"""Lightweight invariant checker for scene-first manifests."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(path: str) -> None:
    data = json.loads(Path(path).read_text())
    errors = []
    scenes = data.get("scene_units", [])
    previous_end = 0
    for i, scene in enumerate(scenes):
        sid = scene.get("scene_id", f"scene-{i}")
        if scene["end_ms"] <= scene["start_ms"]:
            errors.append(f"{sid}: non-positive interval")
        if scene["start_ms"] != previous_end:
            errors.append(f"{sid}: scene gap/overlap at {previous_end}")
        previous_end = scene["end_ms"]
        samples = scene.get("sampled_frames", [])
        if len(samples) not in (2, 4, 6):
            errors.append(f"{sid}: sample count")
        expected = {"two_start_end": 2, "four_progression": 4, "six_long_hold_or_effect": 6}.get(scene.get("sample_policy"))
        if expected is not None and len(samples) != expected:
            errors.append(f"{sid}: sample policy/count mismatch")
        if samples and samples[0]["role"] != "start":
            errors.append(f"{sid}: first sample is not start")
        if samples and samples[-1]["role"] != "end":
            errors.append(f"{sid}: last sample is not end")
        if scene.get("start_frame", {}).get("role") != "start" or scene.get("end_frame", {}).get("role") != "end":
            errors.append(f"{sid}: start/end frame roles")
        if samples and samples[0]["timestamp_ms"] != scene["start_ms"]:
            errors.append(f"{sid}: first sample does not equal scene start")
        if samples and samples[-1]["timestamp_ms"] != scene["end_ms"]:
            errors.append(f"{sid}: last sample does not equal scene end")
        if scene.get("collage", {}).get("sample_count") != len(samples):
            errors.append(f"{sid}: collage/sample count mismatch")
        for sample in samples:
            if not scene["start_ms"] <= sample["timestamp_ms"] <= scene["end_ms"]:
                errors.append(f"{sid}: sample outside scene")
    if previous_end != data.get("duration_ms"):
        errors.append("scene intervals do not cover duration")
    result = {"status": "PASS" if not errors else "FAIL", "scene_count": len(scenes), "errors": errors}
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(errors))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate_scene_segmentation.py MANIFEST.json")
    main(sys.argv[1])
