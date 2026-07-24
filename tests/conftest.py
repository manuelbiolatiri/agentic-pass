import os
import pytest
from pass_mcp.client import WalletKitPassClient

BASE_URL = os.getenv("WALLETKIT_API_URL", "http://localhost:3000")

@pytest.fixture
def pass_client():
    return WalletKitPassClient(base_url=BASE_URL, api_key="wk_test_key_123")
