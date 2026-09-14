from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from m2_studio.cli import process_media_map
from m2_studio.media import StudioError, align_scenes, cut_candidates, digest, digital_silence, extract_scenes, inventory, normalize_whisper, object_hash, sampling_pts, validate_transcript
from m2_studio.providers import ProviderJobs, RunwayImageTransport
from m2_studio.timeline import alignment_plan_hash, build_card_edl, validate_edl


class MediaTests(unittest.TestCase):
    def test_digital_silence_detector_preserves_quiet_audio(self):
        import wave
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "audio.wav"
            for pcm, expected in [(b"\0\0" * 160, True), (b"\x01\0" + b"\0\0" * 159, False)]:
                with wave.open(str(source), "wb") as stream:
                    stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(16000); stream.writeframes(pcm)
                self.assertEqual(digital_silence(source), expected)

    def test_half_open_sampling_never_enters_next_scene(self):
        pts = list(range(0, 2000, 40))
        scene = {"start_ms": 0, "end_ms": 1000, "sample_count": 6}
        samples = sampling_pts(scene, pts)
        self.assertEqual(len(samples), 6)
        self.assertEqual(samples[0]["timestamp_ms"], 0)
        self.assertEqual(samples[-1]["timestamp_ms"], 960)
        self.assertEqual(samples, sampling_pts(scene, pts))

    def test_alignment_requires_semantic_reason_and_exact_segment_binding(self):
        transcript = {"source_media_hash": "a" * 64, "segments": [{"segment_id": "t1", "start_ms": 0, "end_ms": 2000, "text": "Evidence"}]}
        a = {"scene_id": "s1", "start_ms": 0, "end_ms": 2000, "sample_count": 2, "maker": "maker", "information_job": "show proof", "boundary_reasons": ["proof"], "transcript_segment_ids": ["t1"]}
        scenes = align_scenes([a], transcript, 2000, source_media_hash="a" * 64)
        self.assertEqual(scenes[0]["review_state"], "REVIEW_PENDING")
        a["boundary_reasons"] = ["cut_candidate"]
        with self.assertRaisesRegex(StudioError, "SEMANTIC_REASON"):
            align_scenes([a], transcript, 2000, source_media_hash="a" * 64)
        a["boundary_reasons"] = ["proof"]; a["transcript_segment_ids"] = []
        with self.assertRaisesRegex(StudioError, "BINDING_MISMATCH"):
            align_scenes([a], transcript, 2000, source_media_hash="a" * 64)

    def test_cross_media_transcript_and_changed_transcript_fail_before_extraction(self):
        transcript = {"source_media_hash": "a" * 64, "segments": [{"segment_id": "t1", "start_ms": 0, "end_ms": 2000, "text": "Evidence"}]}
        annotation = {"scene_id": "s1", "start_ms": 0, "end_ms": 2000, "sample_count": 2, "maker": "maker", "information_job": "show proof", "boundary_reasons": ["proof"], "transcript_segment_ids": ["t1"]}
        with self.assertRaisesRegex(StudioError, "TRANSCRIPT_SOURCE_MEDIA_MISMATCH"):
            align_scenes([annotation], transcript, 2000, source_media_hash="b" * 64)
        scenes = align_scenes([annotation], transcript, 2000, source_media_hash="a" * 64)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); output = root / "frames"
            media = {"observation_state": "OBSERVED", "sha256": "b" * 64, "duration_ms": 2000}
            with self.assertRaisesRegex(StudioError, "TRANSCRIPT_SOURCE_MEDIA_MISMATCH"):
                extract_scenes(root, media, scenes, output, transcript=transcript)
            for name, data in (("media", media), ("transcript", transcript), ("annotations", [annotation])):
                (root / f"{name}.json").write_text(json.dumps(data))
            result = subprocess.run([sys.executable, "-m", "m2_studio", "scenes", "--root", str(root), "--media", str(root / "media.json"), "--transcript", str(root / "transcript.json"), "--annotations", str(root / "annotations.json"), "--output", str(output)], text=True, capture_output=True, cwd=Path(__file__).resolve().parents[1])
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["failure_code"], "TRANSCRIPT_SOURCE_MEDIA_MISMATCH")
            media["sha256"] = "a" * 64
            changed = copy.deepcopy(transcript); changed["segments"][0]["text"] = "Different evidence"
            with self.assertRaisesRegex(StudioError, "SCENE_TRANSCRIPT_DIGEST_MISMATCH"):
                extract_scenes(root, media, scenes, output, transcript=changed)
            self.assertFalse(output.exists())

    def test_empty_asr_and_invalid_timestamp_are_not_silence_proof(self):
        media = {"duration_ms": 1000, "sha256": "a" * 64, "timebase_provenance": {"audio_offset_ms": 0}}
        result = normalize_whisper({"segments": []}, media)
        self.assertEqual(result["observation_state"], "EMPTY_OUTPUT_UNVERIFIED")
        with self.assertRaisesRegex(StudioError, "TIME_OUTSIDE"):
            normalize_whisper({"segments": [{"text": "hello", "start": 0, "end": 2}]}, media)

    def test_rights_paths_hashes_and_missing_rows_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.mp4").write_bytes(b"invalid")
            entry = {"media_id": "m1", "path": "a.mp4", "source_kind": "approved_research_copy", "sha256": "0" * 64, "rights": {"analysis_allowed": False, "receipt_id": "r1"}}
            self.assertEqual(inventory(root, [entry])[0]["observation_state"], "RIGHTS_BLOCKED")
            entry["rights"]["analysis_allowed"] = True
            self.assertEqual(inventory(root, [entry])[0]["failure_code"], "MEDIA_HASH_MISMATCH")
            entry["path"] = "../a.mp4"
            self.assertEqual(inventory(root, [entry])[0]["failure_code"], "PATH_OUTSIDE_ALLOWLIST")
            result = process_media_map(root, {"run_id": "r", "expected_codes": ["one", "two"], "entries": []}, root / "out")
            self.assertEqual(len(result["rows"]), 2)
            self.assertEqual(result["local_media_observed"], 0)
            self.assertFalse(result["hikerapi_execution"])

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg unavailable")
    def test_decode_cut_candidates_and_twelve_hashed_frames(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "fixture.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=red:s=160x284:r=25:d=1", "-f", "lavfi", "-i", "color=c=blue:s=160x284:r=25:d=1", "-f", "lavfi", "-i", "testsrc2=s=160x284:r=25:d=1", "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]", "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source)], check=True, capture_output=True)
            entry = {"media_id": "fixture", "path": "fixture.mp4", "source_kind": "synthetic_fixture", "sha256": digest(source), "rights": {"analysis_allowed": True, "public_display_allowed": True, "receipt_id": "synthetic-test"}}
            media = inventory(root, [entry])[0]
            self.assertEqual(media["observation_state"], "OBSERVED")
            cuts = cut_candidates(root, media, threshold=.1)
            self.assertEqual(cuts["observation_state"], "OBSERVED")
            self.assertTrue(any(abs(c["timestamp_ms"] - 1000) < 50 for c in cuts["candidates"]))
            self.assertIsNone(cuts["confirmed_shots"])
            annotations = [{"scene_id": f"s{i}", "start_ms": i * 1000, "end_ms": (i + 1) * 1000, "sample_count": n, "maker": "fixture-maker", "information_job": "synthetic color change", "boundary_reasons": ["object_change"], "transcript_segment_ids": []} for i, n in enumerate((2, 4, 6))]
            transcript = {"segments": [], "observation_state": "NOT_APPLICABLE", "source_media_hash": media["sha256"]}
            scenes = align_scenes(annotations, transcript, 3000, source_media_hash=media["sha256"])
            evidence = extract_scenes(root, media, scenes, root / "frames", transcript=transcript)
            self.assertEqual(evidence["transcript_sha256"], object_hash(transcript))
            self.assertEqual(evidence["transcript_source_media_hash"], media["sha256"])
            self.assertEqual(evidence["sample_count"], 12)
            self.assertEqual(evidence["review_state"], "REVIEW_PENDING")
            for scene in evidence["scene_units"]:
                self.assertLess(scene["sampled_frames"][-1]["timestamp_ms"], scene["end_ms"])
                for frame in scene["sampled_frames"]:
                    self.assertEqual(digest(root / "frames" / frame["source_pointer"]), frame["sha256"])


class FakeProvider:
    def __init__(self, ambiguous=False): self.calls = 0; self.ambiguous = ambiguous
    def submit(self, request):
        self.calls += 1
        if self.ambiguous: raise TimeoutError()
        return "job-1"
    def poll(self, job): return {"state": "SUCCEEDED"}


class ProviderTests(unittest.TestCase):
    def request(self):
        return {"run_id": "r1", "card_id": "c1", "shot_id": "s1", "provider": "fixture", "model": "fixture-video", "capability": "first_last_frame", "prompt": "Synthetic object", "duration_seconds": 4, "aspect_ratio": "9:16", "reference_hashes": ["a" * 64, "b" * 64], "rights_receipt_id": "r1", "approval_id": "ap1", "capability_receipt_id": "cap1", "max_cost_microusd": 100}

    def activation(self):
        return {"enabled": True, "expires_at_epoch": time.time() + 600, "provider": "fixture", "models": ["fixture-video"], "capabilities": ["first_last_frame"], "approval_id": "ap1", "capability_receipt_id": "cap1", "max_job_cost_microusd": 100, "approved_request_hashes": [object_hash(self.request())]}

    def test_activation_binds_every_request_field_before_any_submit(self):
        mutations = {"prompt": "Unapproved prompt", "reference_hashes": ["c" * 64, "d" * 64],
                     "rights_receipt_id": "unapproved-rights", "run_id": "other-run", "card_id": "other-card",
                     "shot_id": "other-shot", "duration_seconds": 6, "aspect_ratio": "16:9",
                     "max_cost_microusd": 90, "seed": 42}
        with tempfile.TemporaryDirectory() as tmp:
            provider = FakeProvider()
            jobs = ProviderJobs(Path(tmp) / "jobs.sqlite", budget_microusd=2000, transport=provider, activation=self.activation())
            for key, value in mutations.items():
                with self.subTest(changed_field=key):
                    request = self.request(); request[key] = value
                    row = jobs.plan(request)
                    with self.assertRaisesRegex(StudioError, "REQUEST_NOT_APPROVED"):
                        jobs.submit(row["id"])
                    self.assertEqual(jobs.get(row["id"])["state"], "PLANNED")
                    self.assertEqual(provider.calls, 0)
            approved = jobs.plan(self.request())
            self.assertEqual(jobs.submit(approved["id"])["state"], "SUBMITTED")
            self.assertEqual(provider.calls, 1)
            jobs.close()

    def test_activation_snapshot_and_stored_request_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = FakeProvider(); activation = self.activation()
            jobs = ProviderJobs(Path(tmp) / "jobs.sqlite", budget_microusd=300, transport=provider, activation=activation)
            changed = self.request(); changed["prompt"] = "Changed after approval"
            activation["approved_request_hashes"].append(object_hash(changed))
            row = jobs.plan(changed)
            with self.assertRaisesRegex(StudioError, "REQUEST_NOT_APPROVED"): jobs.submit(row["id"])
            approved = jobs.plan(self.request())
            jobs.db.execute("UPDATE jobs SET request=? WHERE id=?", (json.dumps(changed), approved["id"]))
            with self.assertRaisesRegex(StudioError, "JOB_REQUEST_HASH_MISMATCH"): jobs.submit(approved["id"])
            self.assertEqual(provider.calls, 0)
            jobs.close()

    def test_missing_wildcard_or_nonlist_approval_digests_fail_closed(self):
        for value in (None, [], ["*"], object_hash(self.request())):
            with self.subTest(digest_value=value), tempfile.TemporaryDirectory() as tmp:
                activation = self.activation()
                if value is None: activation.pop("approved_request_hashes")
                else: activation["approved_request_hashes"] = value
                provider = FakeProvider()
                jobs = ProviderJobs(Path(tmp) / "jobs.sqlite", budget_microusd=100, transport=provider, activation=activation)
                row = jobs.plan(self.request())
                with self.assertRaisesRegex(StudioError, "REQUEST_NOT_APPROVED"): jobs.submit(row["id"])
                self.assertEqual(provider.calls, 0)
                jobs.close()

    def test_default_disabled_and_same_request_one_reservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            jobs = ProviderJobs(Path(tmp) / "jobs.sqlite", budget_microusd=100)
            one = jobs.plan(self.request()); two = jobs.plan(self.request())
            self.assertEqual(one["id"], two["id"])
            with self.assertRaisesRegex(StudioError, "DISABLED"): jobs.submit(one["id"])
            request = self.request(); request["shot_id"] = "s2"
            with self.assertRaisesRegex(StudioError, "BUDGET"): jobs.plan(request)
            jobs.close()

    def test_ambiguous_submit_cannot_retry_and_holds_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = FakeProvider(ambiguous=True)
            jobs = ProviderJobs(Path(tmp) / "jobs.sqlite", budget_microusd=100, transport=provider, activation=self.activation())
            row = jobs.plan(self.request()); result = jobs.submit(row["id"])
            self.assertEqual(result["state"], "SUBMIT_UNKNOWN")
            with self.assertRaisesRegex(StudioError, "RECONCILIATION"): jobs.submit(row["id"])
            self.assertEqual(provider.calls, 1)
            jobs.reconcile(row["id"], provider_job_id="job-found", actual_microusd=90, outcome="SUCCEEDED", receipt_id="billing-receipt")
            with self.assertRaisesRegex(StudioError, "CONFLICT"):
                jobs.reconcile(row["id"], provider_job_id="job-found", actual_microusd=0, outcome="FAILED", receipt_id="conflict")
            jobs.close()

    def test_submit_poll_budget_reconciliation_and_expiry(self):
        with tempfile.TemporaryDirectory() as tmp:
            jobs = ProviderJobs(Path(tmp) / "jobs.sqlite", budget_microusd=200, transport=FakeProvider(), activation=self.activation())
            row = jobs.plan(self.request()); row = jobs.submit(row["id"])
            with self.assertRaisesRegex(StudioError, "POLL_TOO_EARLY"): jobs.poll(row["id"], now=row["next_poll"] - 1)
            row = jobs.poll(row["id"], now=row["next_poll"])
            self.assertEqual(row["state"], "SUCCEEDED")
            self.assertIsNone(row["actual"])
            row = jobs.reconcile(row["id"], provider_job_id="job-1", actual_microusd=110, outcome="SUCCEEDED", receipt_id="bill")
            self.assertEqual(row["failure"], "BUDGET_OVERRUN")
            jobs.close()

    def test_direct_adapter_compiles_keyframes_without_network_or_retry(self):
        import hashlib
        from types import SimpleNamespace
        class Client:
            base_url = "https://api.dev.runwayml.com"
            def with_options(self, **options):
                self.options = options
                return self
        client = Client()
        data = b"synthetic-test-bytes"
        checksum = hashlib.sha256(data).hexdigest()
        adapter = RunwayImageTransport(client, lambda h: (data, "image/png"))
        request = self.request(); request.update(provider="runway", model="seedance2_5", reference_hashes=[checksum, checksum])
        payload = adapter.compile(request)
        self.assertEqual([p["position"] for p in payload["prompt_image"]], ["first", "last"])
        self.assertEqual(payload["ratio"], "720:1280")
        self.assertFalse(payload["audio"])
        self.assertEqual(client.options["max_retries"], 0)
        with self.assertRaisesRegex(StudioError, "DISABLED"): adapter.submit(request)
        request["model"] = "gen4.5"
        with self.assertRaisesRegex(StudioError, "LAST_FRAME"): adapter.compile(request)


class TimelineTests(unittest.TestCase):
    def production_fixture(self):
        return {"schema": "m2.remotion-edl.v1", "fps": 30, "width": 1080, "height": 1920,
                "duration_frames": 60, "render_mode": "PRODUCTION", "review_state": "APPROVED", "source_card_hash": "c" * 64,
                "assets": [], "audio_stems": [], "captions": [], "pending_audio_assets": [], "speech_policy": "NO_SPEECH",
                "scenes": [{"scene_id": "s1", "from_frame": 0, "duration_frames": 60, "layout": "motion_graphic", "layers": [{"kind": "text", "text": "Approved editable title"}]}]}

    def test_production_blocks_pending_narration_and_unbuilt_graphics(self):
        edl = self.production_fixture(); validate_edl(edl, production=True)
        edl["pending_audio_assets"] = ["voice-not-recorded"]
        with self.assertRaisesRegex(StudioError, "AUDIO_RECORDING_OR_PLACEMENT_PENDING"): validate_edl(edl, production=True)
        edl["pending_audio_assets"] = []; edl["scenes"][0]["layers"] = [{"kind": "graphic", "text": "A diagram to build later"}]
        with self.assertRaisesRegex(StudioError, "UNBUILT_GRAPHIC_PLAN"): validate_edl(edl, production=True)

    def test_required_speech_needs_stem_and_content_bound_alignment(self):
        edl = self.production_fixture(); edl["speech_policy"] = "REQUIRED_RECORDED_SPEECH"
        with self.assertRaisesRegex(StudioError, "RECORDED_SPEECH_STEM_REQUIRED"): validate_edl(edl, production=True)
        edl["assets"] = [{"asset_id": "voice", "kind": "audio", "path": "voice.wav", "sha256": "a" * 64, "rights_approved": True, "rights_receipt_id": "rights", "duration_frames": 60}]
        edl["audio_stems"] = [{"asset_id": "voice", "role": "speech", "from_frame": 0, "duration_frames": 60, "volume": 1}]
        with self.assertRaisesRegex(StudioError, "ALIGNMENT_REQUIRED"): validate_edl(edl, production=True)
        edl["speech_alignment"] = {"review_state": "APPROVED", "receipt_id": "alignment", "source_card_hash": edl["source_card_hash"], "audio_asset_hashes": {"voice": "a" * 64}}
        edl["speech_alignment"]["alignment_plan_sha256"] = alignment_plan_hash(edl)
        validate_edl(edl, production=True)
        edl["assets"][0]["sha256"] = "b" * 64
        with self.assertRaisesRegex(StudioError, "ALIGNMENT_REQUIRED"): validate_edl(edl, production=True)

    def test_alignment_approval_rejects_changed_placement_trim_gain_or_caption(self):
        edl = self.production_fixture(); edl["speech_policy"] = "REQUIRED_RECORDED_SPEECH"
        edl["assets"] = [{"asset_id": "voice", "kind": "audio", "path": "voice.wav", "sha256": "a" * 64, "rights_approved": True, "rights_receipt_id": "rights", "duration_frames": 120}]
        edl["audio_stems"] = [{"asset_id": "voice", "role": "speech", "from_frame": 0, "duration_frames": 30, "trim_before_frames": 0, "volume": .8}]
        edl["captions"] = [{"from_frame": 0, "duration_frames": 30, "text": "Proof — Пример 🔬"}]
        edl["speech_alignment"] = {"review_state": "APPROVED", "receipt_id": "alignment", "source_card_hash": edl["source_card_hash"], "audio_asset_hashes": {"voice": "a" * 64}, "alignment_plan_sha256": alignment_plan_hash(edl)}
        validate_edl(edl, production=True)
        if shutil.which("node"):
            js = "import {alignmentPlanHash,validateEDL} from './studio/remotion/contract.mjs'; import fs from 'node:fs'; const e=JSON.parse(fs.readFileSync(0,'utf8')); validateEDL(e,{production:true}); console.log(alignmentPlanHash(e));"
            for volume in (.8, 1.0):
                shared = copy.deepcopy(edl); shared["audio_stems"][0]["volume"] = volume
                shared["speech_alignment"]["alignment_plan_sha256"] = alignment_plan_hash(shared)
                result = subprocess.run(["node", "--input-type=module", "-e", js], input=json.dumps(shared), capture_output=True, text=True, check=True, cwd=Path(__file__).resolve().parents[1])
                self.assertEqual(result.stdout.strip(), alignment_plan_hash(shared))
        for section, key, value in [("audio_stems", "from_frame", 1), ("audio_stems", "duration_frames", 29), ("audio_stems", "trim_before_frames", 1), ("audio_stems", "volume", .7), ("captions", "from_frame", 1), ("captions", "duration_frames", 29), ("captions", "text", "Changed caption")]:
            changed = copy.deepcopy(edl); changed[section][0][key] = value
            with self.subTest(section=section, key=key), self.assertRaisesRegex(StudioError, "ALIGNMENT_REQUIRED"):
                validate_edl(changed, production=True)

    def test_audio_binding_requires_explicit_stem_placement(self):
        card = self.fixture(); card["assets"] = [{"asset_id": "voice", "kind": "audio"}]
        bindings = {"voice": {"kind": "audio", "path": "voice.wav", "sha256": "a" * 64, "rights_approved": True, "rights_receipt_id": "rights", "duration_frames": 60}}
        edl = build_card_edl(card, bindings)
        self.assertEqual(edl["audio_stems"], []); self.assertEqual(edl["pending_audio_assets"], ["voice"])
        bindings["voice"]["stem"] = {"role": "speech", "from_frame": 0, "duration_frames": 60, "trim_before_frames": 0, "volume": .8}
        edl = build_card_edl(card, bindings)
        self.assertEqual(edl["pending_audio_assets"], []); self.assertEqual(edl["audio_stems"][0]["asset_id"], "voice")
        self.assertNotIn("stem", edl["assets"][0]); self.assertEqual(edl["speech_policy"], "REQUIRED_RECORDED_SPEECH")

    def fixture(self):
        return {"card_id": "c1", "title": "Demo", "duration_seconds": 2, "fps": 30, "shots": [{"shot_id": "s1", "start_ms": 0, "end_ms": 2000, "mode": "split_screen", "visual": "Proof", "on_screen_text": "Visible evidence", "asset_ids": ["owner", "demo"]}], "segments": [{"start_ms": 0, "end_ms": 2000, "spoken_text": "Show the proof"}]}

    def test_pending_assets_remain_previs_and_final_render_blocked(self):
        edl = build_card_edl(self.fixture())
        self.assertEqual(edl["scenes"][0]["layout"], "split_screen")
        self.assertEqual(edl["scenes"][0]["layers"][0]["kind"], "placeholder")
        with self.assertRaisesRegex(StudioError, "APPROVED"): validate_edl(edl, production=True)
        edl["review_state"] = "APPROVED"
        edl["render_mode"] = "PRODUCTION"
        with self.assertRaisesRegex(StudioError, "PENDING"): validate_edl(edl, production=True)

    def test_asset_hash_and_timeline_bounds_checked(self):
        edl = build_card_edl(self.fixture())
        edl["scenes"][0]["from_frame"] = 1
        with self.assertRaisesRegex(StudioError, "PARTITION"): validate_edl(edl)

    def test_audio_ids_never_become_visual_placeholders(self):
        card = self.fixture()
        card["assets"] = [{"asset_id": "voice", "kind": "audio"}, {"asset_id": "owner", "kind": "video", "production_route": "owner_recording"}, {"asset_id": "demo", "kind": "graphic"}]
        card["shots"][0]["asset_ids"].insert(0, "voice")
        edl = build_card_edl(card)
        self.assertEqual(edl["pending_audio_assets"], ["voice"])
        self.assertFalse(any("voice" in layer.get("text", "") for layer in edl["scenes"][0]["layers"]))
        self.assertEqual(edl["scenes"][0]["layers"][0]["panel"], "bottom")
        self.assertEqual(edl["scenes"][0]["layers"][1]["panel"], "top")


if __name__ == "__main__":
    unittest.main()
