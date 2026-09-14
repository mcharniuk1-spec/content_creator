from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from m2_studio.fal_provider import FalModelSpec, FalQueueTransport
from m2_studio.media import StudioError, object_hash
from m2_studio.providers import ProviderJobs


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def read(self, size=-1):
        raw = json.dumps(self.payload).encode("utf-8")
        return raw if size < 0 else raw[:size]


class FakeOpener:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def open(self, request, timeout):
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("unexpected request")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FalProviderTests(unittest.TestCase):
    def request(self):
        return {
            "run_id": "run-1", "card_id": "card-1", "shot_id": "shot-1",
            "provider": "fal", "model": "fal-ai/example-video", "capability": "text_to_video",
            "prompt": "A synthetic blue object moves slowly", "duration_seconds": 4,
            "aspect_ratio": "9:16", "reference_hashes": [], "rights_receipt_id": "rights-1",
            "approval_id": "approval-1", "max_cost_microusd": 100,
            "capability_receipt_id": "cap-1",
        }

    def make_transport(self, request=None, *, responses=(), enabled=True, mapping=None, secret="test-secret"):
        request = request or self.request()
        mapping = mapping or {"text_to_video": {request["model"]: FalModelSpec(
            "https://queue.fal.run/fal-ai/example-video",
            lambda value: {"prompt": value["prompt"], "duration": value["duration_seconds"]},
        )}}
        return FalQueueTransport(mapping, approved_request_hashes=[object_hash(request)],
                                 enabled=enabled, secret=secret, opener=FakeOpener(responses))

    def test_disabled_by_default_makes_no_request(self):
        transport = self.make_transport(enabled=False)
        with self.assertRaisesRegex(StudioError, "PROVIDER_TRANSPORT_DISABLED"):
            transport.submit(self.request())
        self.assertEqual(transport._opener.requests, [])

    def test_unapproved_origin_and_model_fail_before_request(self):
        request = self.request()
        with self.assertRaisesRegex(StudioError, "UNAPPROVED_PROVIDER_ORIGIN"):
            FalQueueTransport({"text_to_video": {request["model"]: FalModelSpec(
                "https://evil.example/fal-ai/example-video", lambda value: {},
            )}})
        transport = self.make_transport(responses=())
        changed = dict(request); changed["model"] = "fal-ai/unapproved"
        with self.assertRaisesRegex(StudioError, "MODEL_NOT_ADMITTED"):
            transport.submit(changed)
        self.assertEqual(transport._opener.requests, [])

    def test_exact_request_hash_is_required_and_payload_is_model_specific(self):
        request = self.request()
        transport = self.make_transport(responses=[FakeResponse({
            "request_id": "req-1",
            "status_url": "https://queue.fal.run/fal-ai/example-video/requests/req-1/status",
            "response_url": "https://queue.fal.run/fal-ai/example-video/requests/req-1",
        })])
        changed = dict(request); changed["prompt"] = "unapproved"
        with self.assertRaisesRegex(StudioError, "FAL_REQUEST_NOT_APPROVED"):
            transport.submit(changed)
        self.assertEqual(transport._opener.requests, [])
        handle = transport.submit(request)
        payload = json.loads(transport._opener.requests[0].data.decode("utf-8"))
        self.assertEqual(payload, {"duration": 4, "prompt": request["prompt"]})
        self.assertEqual(json.loads(handle)["request_id"], "req-1")

    def test_no_secret_in_exception_and_completion_fetches_result_for_media_qa(self):
        request = self.request()
        opener = FakeOpener([
            FakeResponse({"request_id": "req-1", "status_url": "https://queue.fal.run/status/req-1", "response_url": "https://queue.fal.run/result/req-1"}),
            FakeResponse({"status": "COMPLETED"}),
            FakeResponse({"video": {"url": "https://storage.example/video.mp4"}}),
        ])
        transport = FalQueueTransport({"text_to_video": {request["model"]: FalModelSpec(
            "https://queue.fal.run/fal-ai/example-video", lambda value: {"prompt": value["prompt"]},
        )}}, approved_request_hashes=[object_hash(request)], enabled=True, secret="fixture-key", opener=opener)
        handle = transport.submit(request)
        result = transport.poll(handle)
        self.assertEqual(result["state"], "SUCCEEDED")
        self.assertEqual(result["media_qa_state"], "PENDING")
        self.assertIn("video", result["result"])
        self.assertEqual(len(opener.requests), 3)
        self.assertNotIn("fixture-key", repr(result))

    def test_completed_error_is_failed_without_fetching_result(self):
        request = self.request()
        opener = FakeOpener([
            FakeResponse({"request_id": "req-1", "status_url": "https://queue.fal.run/status/req-1", "response_url": "https://queue.fal.run/result/req-1"}),
            FakeResponse({"status": "COMPLETED", "error": "provider detail", "error_type": "MODEL_ERROR"}),
        ])
        transport = self.make_transport(responses=opener.responses)
        transport._opener = opener
        result = transport.poll(transport.submit(request))
        self.assertEqual(result["state"], "FAILED")
        self.assertEqual(result["error_code"], "FAL_COMPLETED_WITH_ERROR")
        self.assertEqual(len(opener.requests), 2)

    def test_status_error_and_redirect_are_sanitized(self):
        request = self.request()
        transport = self.make_transport(responses=[FakeResponse({"request_id": "req-1", "status_url": "https://evil.example/status", "response_url": "https://queue.fal.run/result"})])
        with self.assertRaisesRegex(StudioError, "UNAPPROVED_PROVIDER_ORIGIN"):
            transport.submit(request)
        opener = FakeOpener([RuntimeError("provider leaked fixture-key")])
        transport = self.make_transport(responses=())
        transport._opener = opener
        with self.assertRaisesRegex(StudioError, "FAL_REQUEST_FAILED") as caught:
            transport.submit(request)
        self.assertNotIn("fixture-key", str(caught.exception))

    def test_provider_jobs_activation_and_budget_seam(self):
        request = self.request()
        opener = FakeOpener([FakeResponse({
            "request_id": "req-seam",
            "status_url": "https://queue.fal.run/status/req-seam",
            "response_url": "https://queue.fal.run/result/req-seam",
        })])
        transport = self.make_transport(responses=opener.responses)
        activation = {
            "enabled": True,
            "expires_at_epoch": 4_102_444_800,
            "provider": "fal",
            "models": [request["model"]],
            "capabilities": [request["capability"]],
            "approval_id": request["approval_id"],
            "capability_receipt_id": request["capability_receipt_id"],
            "max_job_cost_microusd": request["max_cost_microusd"],
            "approved_request_hashes": [object_hash(request)],
        }
        with tempfile.TemporaryDirectory() as tmp:
            transport._opener = opener
            jobs = ProviderJobs(Path(tmp) / "jobs.sqlite", budget_microusd=100, transport=transport, activation=activation)
            planned = jobs.plan(request)
            submitted = jobs.submit(planned["id"])
            self.assertEqual(submitted["state"], "SUBMITTED")
            self.assertEqual(json.loads(submitted["provider_job"])["request_id"], "req-seam")
            self.assertEqual(len(opener.requests), 1)
            jobs.close()


if __name__ == "__main__":
    unittest.main()
