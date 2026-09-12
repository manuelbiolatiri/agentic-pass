import pytest
from pass_mcp.client import WalletKitPassClient
from pass_mcp import rate_limiter
from pass_mcp.rate_limiter import check_and_increment_rate_limit

def test_client_instantiation():
    client = WalletKitPassClient(base_url="http://localhost:3000")
    assert client is not None
    assert client.base_url == "http://localhost:3000"
    assert hasattr(client, "issue_mandate")
    assert hasattr(client, "enforce_request")
    assert hasattr(client, "check_mandate_status")


# ---------------------------------------------------------------------------
# Rate limiting: 100 passes/day, tracked per business (not a truthy bypass)
#
# `isolated_usage_store` points the limiter at a throwaway directory so these
# tests never read/write the real developer's ~/.pass_mcp/usage.json.
# ---------------------------------------------------------------------------

@pytest.fixture
def isolated_usage_store(tmp_path, monkeypatch):
    config_dir = tmp_path / ".pass_mcp"
    monkeypatch.setattr(rate_limiter, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(rate_limiter, "DEVICE_ID_FILE", config_dir / "device_id")
    monkeypatch.setattr(rate_limiter, "USAGE_FILE", config_dir / "usage.json")
    return config_dir

def test_rate_limiter_local_device_quota(isolated_usage_store):
    allowed, msg = check_and_increment_rate_limit(api_key=None)
    assert allowed is True
    assert "1/100" in msg
    assert "device" in msg

def test_rate_limiter_business_key_quota(isolated_usage_store):
    allowed, msg = check_and_increment_rate_limit(api_key="wk_live_realbusiness")
    assert allowed is True
    assert "1/100" in msg
    assert "business" in msg

def test_rate_limiter_garbage_key_is_still_capped(isolated_usage_store):
    """Regression test: passing any non-empty string used to skip the local
    quota entirely and report 'Unlimited quota'. A key that isn't real can
    no longer buy unlimited local usage - it gets its own 100/day bucket
    like any other identity, same as a garbage key would before it fails
    auth upstream."""
    for _ in range(rate_limiter.DAILY_PASS_LIMIT):
        allowed, _ = check_and_increment_rate_limit(api_key="garbage-not-a-real-key")
        assert allowed is True

    allowed, msg = check_and_increment_rate_limit(api_key="garbage-not-a-real-key")
    assert allowed is False
    assert "Daily limit reached" in msg

def test_rate_limiter_different_keys_get_independent_buckets(isolated_usage_store):
    """Business A exhausting its quota must not affect business B."""
    for _ in range(rate_limiter.DAILY_PASS_LIMIT):
        allowed, _ = check_and_increment_rate_limit(api_key="wk_business_A")
        assert allowed is True
    exhausted, _ = check_and_increment_rate_limit(api_key="wk_business_A")
    assert exhausted is False

    still_fresh, msg = check_and_increment_rate_limit(api_key="wk_business_B")
    assert still_fresh is True
    assert "1/100" in msg

def test_rate_limiter_api_key_is_never_stored_in_plaintext(isolated_usage_store):
    check_and_increment_rate_limit(api_key="wk_super_secret_key")
    raw = isolated_usage_store.joinpath("usage.json").read_text()
    assert "wk_super_secret_key" not in raw

@pytest.mark.asyncio
async def test_issue_mandate_does_not_consume_pass_quota(recording_transport, isolated_usage_store):
    """Issuing a mandate token doesn't create a pass, so it must not eat into
    the 100-passes-per-day allowance - only enforce_request (which actually
    issues a pass) should."""
    client = WalletKitPassClient(base_url="http://test", api_key="wk_live_realbusiness")

    for _ in range(rate_limiter.DAILY_PASS_LIMIT + 5):
        await client.issue_mandate(
            principal_id="usr_1",
            agent_id="agent_1",
            authorization_details=[{"type": "loyalty", "pass_class": "loyalty"}],
        )

    # Quota must still be fully available for an actual pass request.
    allowed, msg = check_and_increment_rate_limit(api_key="wk_live_realbusiness")
    assert allowed is True
    assert "1/100" in msg


# ---------------------------------------------------------------------------
# Auth/access: per-call credential scoping
#
# These pin down the "one hardcoded key" bug class: a client with no key
# configured must send no header, a configured default must be used as a
# fallback only, and a per-call override must always win and never leak into
# a different call.
# ---------------------------------------------------------------------------

def test_no_key_configured_sends_no_api_key_header():
    client = WalletKitPassClient(base_url="http://test", api_key=None)
    headers = client._get_headers()
    assert "X-Api-Key" not in headers

def test_server_default_key_is_sent_when_no_override_given():
    client = WalletKitPassClient(base_url="http://test", api_key="wk_server_default")
    headers = client._get_headers()
    assert headers["X-Api-Key"] == "wk_server_default"

def test_per_call_override_takes_precedence_over_server_default():
    client = WalletKitPassClient(base_url="http://test", api_key="wk_server_default")
    headers = client._get_headers(api_key_override="wk_caller_business")
    assert headers["X-Api-Key"] == "wk_caller_business"

def test_device_id_header_always_present_regardless_of_auth():
    client = WalletKitPassClient(base_url="http://test", api_key=None)
    assert "X-Pass-MCP-Device-Id" in client._get_headers()
    assert "X-Pass-MCP-Device-Id" in client._get_headers(api_key_override="anything")

@pytest.mark.asyncio
async def test_successive_calls_with_different_keys_never_leak_into_each_other(
    recording_transport,
):
    """A single running pass-mcp instance must be able to act for different
    businesses call-by-call, with zero cross-contamination between calls."""
    client = WalletKitPassClient(base_url="http://test", api_key=None)

    await client.lookup_pass("pass_a", api_key="wk_business_A")
    await client.lookup_pass("pass_b", api_key="wk_business_B")
    await client.lookup_pass("pass_c")  # no key at all

    sent_keys = [r.headers.get("x-api-key") for r in recording_transport.requests]
    assert sent_keys == ["wk_business_A", "wk_business_B", None]

@pytest.mark.asyncio
async def test_fastapi_gateway_forwards_x_api_key_header(recording_transport):
    """The FastAPI gateway (pass_mcp/api.py) must forward a caller's
    X-Api-Key header through to wallet-pass-api rather than only ever using
    the process-wide default key."""
    from fastapi.testclient import TestClient
    from pass_mcp.api import app

    with TestClient(app) as test_client:
        resp = test_client.get(
            "/api/v1/mandates/status",
            params={"token": "tok"},
            headers={"x-api-key": "wk_gateway_caller"},
        )
    assert resp.status_code == 200
    assert recording_transport.requests[-1].headers["x-api-key"] == "wk_gateway_caller"

@pytest.mark.asyncio
async def test_fastapi_gateway_omits_header_when_caller_sends_none(recording_transport):
    from fastapi.testclient import TestClient
    from pass_mcp.api import app

    with TestClient(app) as test_client:
        resp = test_client.get("/api/v1/mandates/status", params={"token": "tok"})
    assert resp.status_code == 200
    assert "x-api-key" not in recording_transport.requests[-1].headers
