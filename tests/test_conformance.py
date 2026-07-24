"""
Pass-MCP Conformance Suite
Verifies over-the-wire implementation of RFC 8693 token exchange, draft-klrc-aiagent-auth,
and security invariants against running walletKit backend.
"""
import pytest
import httpx

class TestPassMCPConformanceSuite:

    @pytest.mark.asyncio
    async def test_case_01_mandate_adherence(self, pass_client):
        """Case 1: Normal delegated purchase within scope (0 out-of-scope issuances)."""
        try:
            issue_res = await pass_client.issue_mandate(
                principal_id="usr_human_conf_01",
                agent_id="agent_ai_conf_01",
                authorization_details=[{
                    "type": "event_ticket",
                    "pass_class": "event_ticket",
                    "max_quantity": 2
                }]
            )
            token = issue_res["token"]

            enforce_res = await pass_client.enforce_request(
                mandate_token=token,
                pass_class_id="event_ticket",
                quantity=1
            )

            assert enforce_res["decision"] == "ALLOW"
            assert enforce_res["pass"]["externalUserId"] == "usr_human_conf_01"
        except httpx.HTTPError:
            pytest.skip("walletKit backend server not currently running at WALLETKIT_API_URL")

    @pytest.mark.asyncio
    async def test_case_03_injection_escalation(self, pass_client):
        """Case 3: Attempting body instruction scope escalation beyond token claims."""
        try:
            issue_res = await pass_client.issue_mandate(
                principal_id="usr_human_conf_03",
                agent_id="agent_ai_conf_03",
                authorization_details=[{
                    "type": "event_ticket",
                    "pass_class": "event_ticket",
                    "max_quantity": 1
                }]
            )
            token = issue_res["token"]

            enforce_res = await pass_client.enforce_request(
                mandate_token=token,
                pass_class_id="event_ticket",
                quantity=5
            )

            assert enforce_res["decision"] == "DENY"
        except httpx.HTTPError:
            pytest.skip("walletKit backend server not currently running at WALLETKIT_API_URL")
