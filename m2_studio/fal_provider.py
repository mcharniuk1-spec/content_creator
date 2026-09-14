"""Provider-disabled Fal queue transport.

This module only supplies a narrow ``Transport`` implementation for the
existing :class:`m2_studio.providers.ProviderJobs` escrow.  Model payloads are
provided by an explicit, immutable capability map because Fal models do not
share one universal request schema.  There are no retries, credential-file
reads, redirects, or live calls on import.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .media import StudioError, object_hash
from .providers import Transport, validate_request


FAL_ORIGIN = "queue.fal.run"
FAL_DOCS_URL = "https://fal.ai/docs/documentation/model-apis/inference/queue"
_SECRET_KEY_PARTS = ("api_key", "password", "token", "cookie", "authorization")
_MAX_HANDLE_BYTES = 16_384


@dataclass(frozen=True)
class FalModelSpec:
    """One explicitly admitted model route and its model-specific payload builder."""

    queue_url: str
    payload_builder: Callable[[Mapping[str, Any]], Mapping[str, Any]]


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):  # pragma: no cover - urllib path
        raise StudioError("REDIRECT_REFUSED")


class FalQueueTransport(Transport):
    """Bounded Fal queue API adapter.

    ``capability_mapping`` must be shaped as ``{capability: {model:
    FalModelSpec}}``.  Builders own the exact schema for their model; this
    adapter never invents generic Fal fields.  ``approved_request_hashes`` is
    frozen at construction and must contain the full canonical request digest
    accepted by the ProviderJobs activation envelope.
    """

    def __init__(
        self,
        capability_mapping: Mapping[str, Mapping[str, FalModelSpec]],
        *,
        approved_request_hashes: list[str] | tuple[str, ...] | None = None,
        secret: str | None = None,
        enabled: bool = False,
        opener=None,
        timeout_seconds: int = 60,
    ):
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 300:
            raise StudioError("INVALID_PROVIDER_TIMEOUT")
        self.enabled = enabled is True
        self.timeout_seconds = timeout_seconds
        self._secret = secret
        self._opener = opener or build_opener(_NoRedirect())
        self.capability_mapping = self._freeze_mapping(capability_mapping)
        self.approved_request_hashes = self._freeze_hashes(approved_request_hashes)
        for models in self.capability_mapping.values():
            for model, spec in models.items():
                self._validate_model_route(model, spec)

    @staticmethod
    def _freeze_hashes(values):
        if values is None:
            return ()
        if isinstance(values, (str, bytes)):
            raise StudioError("FAL_APPROVED_HASHES_INVALID")
        frozen = tuple(values)
        if not frozen or any(
            not isinstance(value, str)
            or len(value) != 64
            or any(char not in "0123456789abcdef" for char in value)
            for value in frozen
        ):
            raise StudioError("FAL_APPROVED_HASHES_INVALID")
        return frozen

    @staticmethod
    def _freeze_mapping(mapping):
        if not isinstance(mapping, Mapping) or not mapping:
            raise StudioError("FAL_CAPABILITY_MAP_REQUIRED")
        frozen = {}
        for capability, models in mapping.items():
            if not isinstance(capability, str) or not capability or not isinstance(models, Mapping) or not models:
                raise StudioError("FAL_CAPABILITY_MAP_INVALID")
            frozen_models = {}
            for model, spec in models.items():
                if not isinstance(model, str) or not model or not isinstance(spec, FalModelSpec):
                    raise StudioError("FAL_CAPABILITY_MAP_INVALID")
                frozen_models[model] = spec
            frozen[capability] = MappingProxyType(frozen_models)
        return MappingProxyType(frozen)

    @staticmethod
    def _validate_model_route(model: str, spec: FalModelSpec) -> None:
        parsed = urlparse(spec.queue_url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != FAL_ORIGIN
            or parsed.port not in {None, 443}
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path != "/" + model
        ):
            raise StudioError("UNAPPROVED_PROVIDER_ORIGIN")
        if not callable(spec.payload_builder):
            raise StudioError("FAL_PAYLOAD_BUILDER_REQUIRED")

    @staticmethod
    def _validate_return_url(value: Any, *, required: bool = True) -> str | None:
        if value is None and not required:
            return None
        if not isinstance(value, str) or not value:
            raise StudioError("FAL_QUEUE_HANDLE_INVALID")
        parsed = urlparse(value)
        if (
            parsed.scheme != "https"
            or parsed.hostname != FAL_ORIGIN
            or parsed.port not in {None, 443}
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise StudioError("UNAPPROVED_PROVIDER_ORIGIN")
        return value

    def _read_secret(self) -> str:
        secret = self._secret if self._secret is not None else os.environ.get("FAL_KEY")
        if not isinstance(secret, str) or not secret:
            raise StudioError("FAL_KEY_MISSING")
        return secret

    @staticmethod
    def _contains_secret_key(value: Any) -> bool:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if any(part in str(key).lower() for part in _SECRET_KEY_PARTS):
                    return True
                if FalQueueTransport._contains_secret_key(child):
                    return True
        elif isinstance(value, (list, tuple)):
            return any(FalQueueTransport._contains_secret_key(child) for child in value)
        return False

    def _compile_payload(self, request: Mapping[str, Any]) -> tuple[str, dict]:
        validate_request(dict(request))
        if request.get("provider") != "fal":
            raise StudioError("MODEL_NOT_ADMITTED")
        models = self.capability_mapping.get(request.get("capability"), {})
        spec = models.get(request.get("model"))
        if spec is None:
            raise StudioError("MODEL_NOT_ADMITTED")
        digest = object_hash(dict(request))
        if digest not in self.approved_request_hashes:
            raise StudioError("FAL_REQUEST_NOT_APPROVED")
        try:
            payload = spec.payload_builder(dict(request))
        except StudioError:
            raise
        except Exception:
            raise StudioError("FAL_PAYLOAD_BUILD_FAILED")
        if not isinstance(payload, Mapping) or self._contains_secret_key(payload):
            raise StudioError("FAL_PAYLOAD_INVALID")
        try:
            payload = json.loads(json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), allow_nan=False))
        except (TypeError, ValueError, OverflowError):
            raise StudioError("FAL_PAYLOAD_INVALID")
        return spec.queue_url, payload

    def _request_json(self, url: str, *, method: str, payload: Mapping[str, Any] | None = None) -> dict:
        secret = self._read_secret()
        data = None if payload is None else json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        headers = {"Authorization": "Key " + secret, "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = Request(url, data=data, headers=headers, method=method)
        try:
            response = self._opener.open(request, timeout=self.timeout_seconds)
            status = getattr(response, "status", None)
            if isinstance(status, int) and 300 <= status < 400:
                raise StudioError("REDIRECT_REFUSED")
            try:
                raw = response.read(4_194_305)
                if len(raw) > 4_194_304:
                    raise StudioError("FAL_RESPONSE_TOO_LARGE")
            finally:
                if hasattr(response, 'close'):
                    response.close()
        except StudioError:
            raise
        except HTTPError as exc:
            if 300 <= exc.code < 400:
                raise StudioError("REDIRECT_REFUSED")
            raise StudioError("FAL_HTTP_" + ("4XX" if 400 <= exc.code < 500 else "5XX" if exc.code >= 500 else "ERROR"))
        except (TimeoutError, OSError):
            raise StudioError("FAL_NETWORK_ERROR")
        except URLError:
            raise StudioError("FAL_NETWORK_ERROR")
        except Exception:
            # Do not surface provider/client exception text: it may contain a
            # secret, request payload, or an untrusted response body.
            raise StudioError("FAL_REQUEST_FAILED")
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (AttributeError, UnicodeDecodeError, json.JSONDecodeError):
            raise StudioError("FAL_INVALID_JSON")
        if not isinstance(decoded, dict):
            raise StudioError("FAL_RESPONSE_INVALID")
        return decoded

    @staticmethod
    def _decode_handle(provider_job_id: str) -> dict:
        if not isinstance(provider_job_id, str) or len(provider_job_id.encode("utf-8")) > _MAX_HANDLE_BYTES:
            raise StudioError("FAL_QUEUE_HANDLE_INVALID")
        try:
            handle = json.loads(provider_job_id)
        except (TypeError, json.JSONDecodeError):
            raise StudioError("FAL_QUEUE_HANDLE_INVALID")
        if not isinstance(handle, dict) or not isinstance(handle.get("model"), str):
            raise StudioError("FAL_QUEUE_HANDLE_INVALID")
        FalQueueTransport._validate_return_url(handle.get("status_url"))
        FalQueueTransport._validate_return_url(handle.get("response_url"))
        FalQueueTransport._validate_return_url(handle.get("cancel_url"), required=False)
        return handle

    def submit(self, request: dict) -> str:
        if not self.enabled:
            raise StudioError("PROVIDER_TRANSPORT_DISABLED")
        queue_url, payload = self._compile_payload(request)
        result = self._request_json(queue_url, method="POST", payload=payload)
        request_id = result.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            raise StudioError("FAL_QUEUE_HANDLE_INVALID")
        status_url = self._validate_return_url(result.get("status_url"))
        response_url = self._validate_return_url(result.get("response_url"))
        cancel_url = self._validate_return_url(result.get("cancel_url"), required=False)
        handle = {
            "model": request["model"],
            "request_id": request_id,
            "status_url": status_url,
            "response_url": response_url,
            "cancel_url": cancel_url,
        }
        encoded = json.dumps(handle, sort_keys=True, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > _MAX_HANDLE_BYTES:
            raise StudioError("FAL_QUEUE_HANDLE_INVALID")
        return encoded

    def poll(self, provider_job_id: str) -> dict:
        if not self.enabled:
            raise StudioError("PROVIDER_TRANSPORT_DISABLED")
        handle = self._decode_handle(provider_job_id)
        status_result = self._request_json(handle["status_url"], method="GET")
        status = status_result.get("status")
        if status in {"IN_QUEUE", "IN_PROGRESS"}:
            return {"state": "RUNNING", "provider_status": status}
        if status in {"FAILED", "CANCELLED"}:
            return {"state": status, "provider_status": status}
        if status != "COMPLETED":
            raise StudioError("UNKNOWN_PROVIDER_STATE")
        if status_result.get("error") is not None or status_result.get("error_type") is not None:
            return {"state": "FAILED", "provider_status": "COMPLETED", "error_code": "FAL_COMPLETED_WITH_ERROR"}
        result = self._request_json(handle["response_url"], method="GET")
        if result.get('error') is not None or result.get('error_type') is not None:
            return {'state': 'FAILED', 'provider_status': 'COMPLETED', 'error_code': 'FAL_RESULT_ERROR'}
        return {
            "state": "SUCCEEDED",
            "provider_status": "COMPLETED",
            "result": result,
            "media_qa_state": "PENDING",
        }

    def cancel(self, provider_job_id: str) -> dict:
        """Request cancellation; a request to cancel is not a final job state."""
        if not self.enabled:
            raise StudioError("PROVIDER_TRANSPORT_DISABLED")
        handle = self._decode_handle(provider_job_id)
        if not handle.get("cancel_url"):
            raise StudioError("FAL_CANCEL_URL_MISSING")
        result = self._request_json(handle["cancel_url"], method="PUT")
        return {"state": "CANCEL_REQUESTED", "provider_status": result.get("status")}
