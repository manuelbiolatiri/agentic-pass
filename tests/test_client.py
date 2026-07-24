import pytest
from pass_mcp.client import WalletKitPassClient
from pass_mcp.rate_limiter import check_and_increment_rate_limit

def test_client_instantiation():
    client = WalletKitPassClient(base_url="http://localhost:3000")
    assert client is not None
    assert client.base_url == "http://localhost:3000"
    assert hasattr(client, "issue_mandate")
    assert hasattr(client, "enforce_request")
    assert hasattr(client, "check_mandate_status")

def test_rate_limiter_local():
    allowed, msg = check_and_increment_rate_limit(has_api_key=False)
    assert allowed is True
    assert "Free daily pass" in msg

def test_rate_limiter_api_key_bypass():
    allowed, msg = check_and_increment_rate_limit(has_api_key=True)
    assert allowed is True
    assert "Unlimited" in msg
