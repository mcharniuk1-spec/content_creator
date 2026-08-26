#!/usr/bin/env python3
"""Structural validator for the photorealistic storyboard reference library."""

import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "studio/story-framework-library/v3-realistic"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((LIB / "manifest.json").read_text())
    errors = []
    if manifest["story_count"] != 50 or manifest["frame_count"] != 300:
        errors.append("expected 50 stories and 300 frames")
    seen = set()
    for story in manifest["stories"]:
        folder = LIB / story["path"]
        gen = json.loads((folder / "generation.json").read_text())
        if gen["reference_evidence_state"] != "NO_SOURCE_FRAMES_AVAILABLE":
            errors.append(f"{story['story_id']}: evidence boundary")
        if gen["rights_state"] != "original_fictional_clean_room_previsualization":
            errors.append(f"{story['story_id']}: rights boundary")
        if len(story["frames"]) != 6:
            errors.append(f"{story['story_id']}: frame count")
        if digest(folder / "contact-sheet-generated.png") != story["source_sheet_sha256"]:
            errors.append(f"{story['story_id']}: sheet hash")
        for row in story["frames"]:
            path = folder / row["file"]
            if not path.exists() or Image.open(path).size != (540, 960):
                errors.append(f"{row['frame_id']}: missing/dimensions")
            elif digest(path) != row["sha256"]:
                errors.append(f"{row['frame_id']}: hash")
            if row["frame_id"] in seen:
                errors.append(f"{row['frame_id']}: duplicate id")
            seen.add(row["frame_id"])
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "stories": len(manifest["stories"]), "frames": len(seen), "blank_risk_count": manifest["blank_risk_count"], "errors": errors}, indent=2))
    raise SystemExit(bool(errors))


if __name__ == "__main__":
    main()
