"""Create original deterministic codec/composition fixtures, never source media."""
from __future__ import annotations

import argparse
from pathlib import Path

from .media import digest, run_tool, write_json
from .timeline import build_card_edl, validate_edl


def build_fixture(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    fixtures = [("a-roll-test.mp4", "testsrc2=s=320x568:r=30:d=4"), ("demo-test.mp4", "color=c=teal:s=568x320:r=30:d=4")]
    bindings = {}
    for filename, source in fixtures:
        target = output / filename
        run_tool(["ffmpeg", "-v", "error", "-nostdin", "-n", "-f", "lavfi", "-i", source, "-c:v", "libx264", "-pix_fmt", "yuv420p", str(target)])
        aid = "owner-plate" if filename.startswith("a-roll") else "demo-plate"
        bindings[aid] = {"kind": "video", "path": filename, "sha256": digest(target), "rights_approved": True, "rights_receipt_id": "synthetic-fixture-owned", "duration_frames": 120}
    audio = output / "tone.wav"
    run_tool(["ffmpeg", "-v", "error", "-nostdin", "-n", "-f", "lavfi", "-i", "sine=frequency=440:duration=4:sample_rate=48000", str(audio)])
    card = {"card_id": "synthetic-av-fixture", "title": "A-roll and split-screen renderer test", "duration_seconds": 4, "fps": 30,
            "shots": [{"shot_id": "aroll", "start_ms": 0, "end_ms": 2000, "mode": "a_roll", "visual": "Synthetic source plate", "on_screen_text": "Synthetic A-roll layer", "asset_ids": ["owner-plate"]},
                      {"shot_id": "split", "start_ms": 2000, "end_ms": 4000, "mode": "split_screen", "visual": "Two independent synthetic plates", "on_screen_text": "Separate source + demo panels", "asset_ids": ["owner-plate", "demo-plate"]}],
            "segments": [{"start_ms": 0, "end_ms": 2000, "spoken_text": "Synthetic caption. Audio is a test tone."},
                         {"start_ms": 2000, "end_ms": 4000, "spoken_text": "Both panels use hash-verified local videos."}]}
    edl = build_card_edl(card, bindings)
    edl["assets"].append({"asset_id": "test-tone", "kind": "audio", "path": "tone.wav", "sha256": digest(audio), "rights_approved": True, "rights_receipt_id": "synthetic-fixture-owned", "duration_frames": 120})
    edl["audio_stems"] = [{"asset_id": "test-tone", "role": "sfx", "from_frame": 0, "duration_frames": 120, "volume": .1}]
    validate_edl(edl, asset_root=output)
    write_json(output / "edl.json", edl)
    write_json(output / "fixture-receipt.json", {"schema": "m2.synthetic-av-fixture.v1", "original_synthetic_media": True, "provider_execution": False,
                                               "assets": edl["assets"], "purpose": "codec, A-roll, split-screen, caption and audio-stem rendering only"})
    return edl


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    build_fixture(parser.parse_args().output)
