from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from edit_pipeline.core import (
    PipelineError,
    analyze_video,
    build_fixture_case,
    export_otio,
    render_edl,
    validate_case,
    validate_edl,
    write_json,
)


class HybridEditingPipelineTests(unittest.TestCase):
    def test_fixture_renders_cuts_audio_color_and_embedded_captions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="archflow_edit_fixture_") as directory:
            result = build_fixture_case(directory)
            output = Path(directory) / "render.mp4"
            manifest = render_edl(result["edl"], output, case=result["case"])
            self.assertEqual(manifest["status"], "PASS")
            self.assertAlmostEqual(manifest["duration_seconds"], 3.2, delta=0.15)
            self.assertEqual(manifest["caption_mode"], "embedded_text_track")
            probe = subprocess.run(
                [
                    shutil.which("ffprobe") or "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "stream=codec_type,codec_name",
                    "-of",
                    "json",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            streams = json.loads(probe.stdout)["streams"]
            self.assertEqual(
                [(stream["codec_type"], stream["codec_name"]) for stream in streams],
                [("video", "h264"), ("audio", "aac"), ("subtitle", "mov_text")],
            )

    def test_analysis_is_explicitly_baseline_and_provider_disabled(self) -> None:
        with tempfile.TemporaryDirectory(prefix="archflow_edit_analysis_") as directory:
            result = build_fixture_case(directory)
            analysis = analyze_video(result["source"], segment_seconds=1.0)
            self.assertEqual(analysis["analysis_mode"], "deterministic_baseline_for_codex_review")
            self.assertEqual(analysis["semantic_status"], "PENDING_CODEX_REVIEW")
            self.assertFalse(analysis["provider_execution"])
            self.assertEqual(len(analysis["candidates"]), 4)

    def test_invalid_rights_and_provider_policy_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="archflow_edit_policy_") as directory:
            result = build_fixture_case(directory)
            bad_case = json.loads(json.dumps(result["case"]))
            bad_case["rights"]["status"] = "unclear"
            with self.assertRaisesRegex(PipelineError, "RIGHTS_NOT_APPROVED"):
                validate_case(bad_case, source_path=result["source"])
            bad_case = json.loads(json.dumps(result["case"]))
            bad_case["policy"]["provider_execution"] = True
            with self.assertRaisesRegex(PipelineError, "PROVIDER_EXECUTION_MUST_BE_DISABLED"):
                validate_case(bad_case, source_path=result["source"])
            bad_case = json.loads(json.dumps(result["case"]))
            bad_case["rights"] = {"status": "owner_owned_approved", "consent": "missing"}
            with self.assertRaisesRegex(PipelineError, "CONSENT_MISSING"):
                validate_case(bad_case, source_path=result["source"])

    def test_invalid_timeline_and_unapproved_repair_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="archflow_edit_edl_") as directory:
            result = build_fixture_case(directory)
            bad_edl = json.loads(json.dumps(result["edl"]))
            bad_edl["segments"][1]["timeline_start"] = 0.1
            with self.assertRaisesRegex(PipelineError, "EDL_TIMELINE_NOT_CONTIGUOUS"):
                validate_edl(bad_edl)
            bad_edl = json.loads(json.dumps(result["edl"]))
            bad_edl["segments"][0]["repair"] = {"provider_execution": True, "approval": "pending"}
            with self.assertRaisesRegex(PipelineError, "GENERATIVE_REPAIR_NOT_APPROVED"):
                validate_edl(bad_edl)

    def test_otio_is_optional_and_truthful(self) -> None:
        with tempfile.TemporaryDirectory(prefix="archflow_edit_otio_") as directory:
            result = build_fixture_case(directory)
            receipt = export_otio(result["edl"], Path(directory) / "timeline.otio")
            self.assertIn(receipt["status"], {"PASS", "NOT_AVAILABLE"})
            self.assertFalse(receipt["provider_execution"])

    def test_cli_plan_exposes_codex_selection_to_the_edl(self) -> None:
        with tempfile.TemporaryDirectory(prefix="archflow_edit_cli_") as directory:
            result = build_fixture_case(directory)
            root = Path(directory)
            write_json(root / "case.json", result["case"])
            write_json(root / "analysis.json", result["analysis"])
            write_json(root / "captions.json", [{"start": 0, "end": 1, "text": "CLI caption"}])
            output = root / "planned-edl.json"
            subprocess.run(
                [
                    "python3",
                    "-m",
                    "edit_pipeline.cli",
                    "plan",
                    "--case",
                    str(root / "case.json"),
                    "--analysis",
                    str(root / "analysis.json"),
                    "--select",
                    "shot-001,shot-003",
                    "--captions",
                    str(root / "captions.json"),
                    "--output",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            planned = json.loads(output.read_text(encoding="utf-8"))
            validate_edl(planned)
            self.assertEqual([x["id"] for x in planned["segments"]], ["shot-001", "shot-003"])


if __name__ == "__main__":
    unittest.main()
