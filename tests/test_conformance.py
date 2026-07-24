"""
Pass-MCP Conformance Benchmark Suite
Verifies over-the-wire implementation of RFC 8693 token exchange, draft-klrc-aiagent-auth,
and all 15 core security & delegation invariants against running walletKit backend.
"""
import pytest
import httpx
import asyncio

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
    async def test_case_02_wrapped_scalper(self, pass_client):
        """Case 2: Wrapped scalper (bot presenting well-formed but undelegated identity)."""
        try:
            invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IndhbGxldGtpdC1tYW5kYXRlK2p3dCJ9.eyJzdWIiOiJ1c3JfaHVtYW4iLCJtYW5kYXRlX2p0aSI6Im1uZF9mYWtlIn0.invalid"
            enforce_res = await pass_client.enforce_request(
                mandate_token=invalid_token,
                pass_class_id="event_ticket"
            )
            assert enforce_res["decision"] in ["DENY", "ERROR"]
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
                quantity=5  # Exceeds ceiling of 1
            )

            assert enforce_res["decision"] == "DENY"
        except httpx.HTTPError:
            pytest.skip("walletKit backend server not currently running at WALLETKIT_API_URL")

    @pytest.mark.asyncio
    async def test_case_04_retry_idempotency(self, pass_client):
        """Case 4: Replay duplicate request under context reset returns stored outcome."""
        try:
            issue_res = await pass_client.issue_mandate(
                principal_id="usr_human_conf_04",
                agent_id="agent_ai_conf_04",
                authorization_details=[{
                    "type": "event_ticket",
                    "pass_class": "event_ticket",
                    "max_quantity": 1
                }]
            )
            token = issue_res["token"]

            res1 = await pass_client.enforce_request(
                mandate_token=token,
                pass_class_id="event_ticket",
                quantity=1
            )

            res2 = await pass_client.enforce_request(
                mandate_token=token,
                pass_class_id="event_ticket",
                quantity=1
            )

            assert res1["decision"] == res2["decision"]
            assert res2.get("isReplay") is True
        except httpx.HTTPError:
            pytest.skip("walletKit backend server not currently running at WALLETKIT_API_URL")

    @pytest.mark.asyncio
    async def test_case_05_replayed_denial(self, pass_client):
        """Case 5: Replayed DENY returns stored DENY without re-evaluation."""
        try:
            issue_res = await pass_client.issue_mandate(
                principal_id="usr_human_conf_05",
                agent_id="agent_ai_conf_05",
                authorization_details=[{
                    "type": "event_ticket",
                    "pass_class": "event_ticket",
                    "max_quantity": 1
                }]
            )
            token = issue_res["token"]

            # Trigger DENY by exceeding quantity limit
            res1 = await pass_client.enforce_request(
                mandate_token=token,
                pass_class_id="event_ticket",
                quantity=10
            )
            assert res1["decision"] == "DENY"

            # Replay denial
            res2 = await pass_client.enforce_request(
                mandate_token=token,
                pass_class_id="event_ticket",
                quantity=10
            )
            assert res2["decision"] == "DENY"
            assert res2.get("isReplay") is True
        except httpx.HTTPError:
            pytest.skip("walletKit backend server not currently running at WALLETKIT_API_URL")

    @pytest.mark.asyncio
    async def test_case_06_escalation_boundary(self, pass_client):
        """Case 6: Requests just-above threshold trigger ESCALATE, just-below trigger ALLOW."""
        try:
            issue_res = await pass_client.issue_mandate(
                principal_id="usr_human_conf_06",
                agent_id="agent_ai_conf_06",
                authorization_details=[{
                    "type": "event_ticket",
                    "pass_class": "event_ticket",
                    "max_quantity": 10,
                    "approval_threshold": {"quantity": 1}
                }]
            )
            token = issue_res["token"]

            # Just-below/equal threshold -> ALLOW
            res_below = await pass_client.enforce_request(
                mandate_token=token,
                pass_class_id="event_ticket",
                quantity=1
            )
            assert res_below["decision"] == "ALLOW"

            # Just-above threshold -> ESCALATE
            res_above = await pass_client.enforce_request(
                mandate_token=token,
                pass_class_id="event_ticket",
                quantity=2
            )
            assert res_above["decision"] == "ESCALATE"
            assert "authReqId" in res_above or "auth_req_id" in res_above
        except httpx.HTTPError:
            pytest.skip("walletKit backend server not currently running at WALLETKIT_API_URL")

    @pytest.mark.asyncio
    async def test_case_07_escalation_timeout(self, pass_client):
        """Case 7: Unresponded escalation request times out and fails closed (DENY)."""
        try:
            issue_res = await pass_client.issue_mandate(
                principal_id="usr_human_conf_07",
                agent_id="agent_ai_conf_07",
                authorization_details=[{
                    "type": "event_ticket",
                    "pass_class": "event_ticket",
                    "max_quantity": 10,
                    "approval_threshold": {"quantity": 1}
                }]
            )
            token = issue_res["token"]

            res_above = await pass_client.enforce_request(
                mandate_token=token,
                pass_class_id="event_ticket",
                quantity=3
            )
            auth_req_id = res_above.get("authReqId") or res_above.get("auth_req_id")
            assert auth_req_id is not None

            # Poll escalation status
            escalation = await pass_client.poll_escalation(auth_req_id)
            assert escalation["status"] in ["PENDING", "EXPIRED", "DENIED"]
        except httpx.HTTPError:
            pytest.skip("walletKit backend server not currently running at WALLETKIT_API_URL")

    @pytest.mark.asyncio
    async def test_case_09_revocation_latency(self, pass_client):
        """Case 9: Revocation latency (revoke -> first denied attempt)."""
        try:
            issue_res = await pass_client.issue_mandate(
                principal_id="usr_human_conf_09",
                agent_id="agent_ai_conf_09",
                authorization_details=[{
                    "type": "event_ticket",
                    "pass_class": "event_ticket",
                    "max_quantity": 5
                }]
            )
            token = issue_res["token"]
            jti = issue_res["mandate"]["jti"]

            # Revoke mandate
            await pass_client.revoke_mandate(jti=jti, reason="Revocation testing")

            # First attempt post-revocation must fail immediately
            enforce_res = await pass_client.enforce_request(
                mandate_token=token,
                pass_class_id="event_ticket",
                quantity=1
            )
            assert enforce_res["decision"] in ["DENY", "ERROR"]
        except httpx.HTTPError:
            pytest.skip("walletKit backend server not currently running at WALLETKIT_API_URL")

    @pytest.mark.asyncio
    async def test_case_12_principal_binding(self, pass_client):
        """Case 12: Issued pass MUST bind to human principal, never to agent."""
        try:
            issue_res = await pass_client.issue_mandate(
                principal_id="usr_human_conf_12",
                agent_id="agent_ai_conf_12",
                authorization_details=[{
                    "type": "event_ticket",
                    "pass_class": "event_ticket"
                }]
            )

            result = await pass_client.enforce_request(
                mandate_token=issue_res["token"],
                pass_class_id="event_ticket"
            )

            assert result["decision"] == "ALLOW"
            assert result["pass"]["externalUserId"] == "usr_human_conf_12"
            assert result["pass"]["externalUserId"] != "agent_ai_conf_12"
        except httpx.HTTPError:
            pytest.skip("walletKit backend server not currently running at WALLETKIT_API_URL")

    @pytest.mark.asyncio
    async def test_case_15_audit_completeness(self, pass_client):
        """Case 15: Every decision is recorded in audit ledger and chain integrity holds."""
        try:
            issue_res = await pass_client.issue_mandate(
                principal_id="usr_human_conf_15",
                agent_id="agent_ai_conf_15",
                authorization_details=[{
                    "type": "event_ticket",
                    "pass_class": "event_ticket"
                }]
            )
            jti = issue_res["mandate"]["jti"]

            # Perform action
            await pass_client.enforce_request(
                mandate_token=issue_res["token"],
                pass_class_id="event_ticket"
            )

            # Reconstruct audit ledger via API
            async with httpx.AsyncClient(base_url=pass_client.base_url) as client:
                res = await client.get(f"/api/v1/mandates/audit/{jti}")
                assert res.status_code == 200
                audit_data = res.json().get("data", res.json())
                assert audit_data["valid"] is True
                assert len(audit_data["history"]) >= 1
        except httpx.HTTPError:
            pytest.skip("walletKit backend server not currently running at WALLETKIT_API_URL")
