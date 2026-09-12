import os
from typing import List

import httpx
import pytest
from pass_mcp.client import WalletKitPassClient

BASE_URL = os.getenv("WALLETKIT_API_URL", "http://localhost:3000")

@pytest.fixture
def pass_client():
    return WalletKitPassClient(base_url=BASE_URL, api_key="wk_test_key_123")


class RecordingTransport(httpx.MockTransport):
    """An httpx MockTransport that records every request it handles, so tests
    can assert on outbound headers/paths without hitting a real network."""

    def __init__(self, handler):
        self.requests: List[httpx.Request] = []

        def _wrapped(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return handler(request)

        super().__init__(_wrapped)


def default_mock_handler(request: httpx.Request) -> httpx.Response:
    """Returns a minimal, shape-correct payload for whichever wallet-pass-api
    endpoint was hit, so client/server code under test can proceed normally."""
    path = request.url.path
    if path.endswith("/mandates/issue"):
        return httpx.Response(201, json={
            "token": "fake.jwt.token",
            "mandate": {"jti": "mnd_fake123", "status": "ACTIVE"},
        })
    if path.endswith("/mandates/enforce"):
        return httpx.Response(200, json={
            "decision": "ALLOW",
            "reason": "ok",
            "pass": {"externalUserId": "usr_1", "urls": {}},
        })
    if path.endswith("/mandates/status"):
        return httpx.Response(200, json={"status": "ACTIVE"})
    if "/escalations/" in path and path.endswith("/respond"):
        return httpx.Response(200, json={"status": "APPROVED"})
    if "/escalations/" in path:
        return httpx.Response(200, json={"status": "PENDING"})
    if path.endswith("/mandates/revoke"):
        return httpx.Response(200, json={"status": "REVOKED"})
    if path.endswith("/holder-passes"):
        return httpx.Response(200, json={"passes": []})
    if path.endswith("/pass-lookup"):
        return httpx.Response(200, json={"id": "pass_1"})
    return httpx.Response(404, json={"error": "unhandled path in test transport"})


@pytest.fixture
def recording_transport(monkeypatch) -> RecordingTransport:
    """Patches httpx.AsyncClient so every outbound call made during the test
    (whether via WalletKitPassClient, an MCP tool, or the FastAPI gateway) is
    routed through an in-memory transport instead of a real socket."""
    transport = RecordingTransport(default_mock_handler)
    real_async_client = httpx.AsyncClient

    def _patched(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _patched)
    return transport
