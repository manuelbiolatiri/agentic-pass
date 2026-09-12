import os
import httpx
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from pass_mcp.rate_limiter import check_and_increment_rate_limit, get_or_create_device_id

load_dotenv()

class WalletKitPassClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or os.getenv("WALLETKIT_API_URL", "http://localhost:3000")
        self.api_key = api_key or os.getenv("WALLETKIT_API_KEY")
        self.device_id = get_or_create_device_id()

    def _get_headers(self, api_key_override: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "X-Pass-MCP-Device-Id": self.device_id,
            "Content-Type": "application/json",
        }
        effective_key = api_key_override or self.api_key
        if effective_key:
            headers["X-Api-Key"] = effective_key
        return headers

    def _unwrap(self, response: httpx.Response) -> Dict[str, Any]:
        data = response.json()
        if isinstance(data, dict) and "data" in data and "success" in data:
            return data["data"]
        return data

    async def issue_mandate(
        self,
        principal_id: str,
        agent_id: str,
        authorization_details: list,
        agent_jkt: Optional[str] = None,
        ttl_seconds: int = 3600,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        # No quota check here: issuing a mandate token doesn't create a pass,
        # so it shouldn't consume the per-day pass-issuance allowance.
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            payload = {
                "principalId": principal_id,
                "agentId": agent_id,
                "authorizationDetails": authorization_details,
                "ttlSeconds": ttl_seconds,
            }
            if agent_jkt:
                payload["agentJkt"] = agent_jkt

            response = await client.post("/api/v1/mandates/issue", json=payload, headers=self._get_headers(api_key))
            response.raise_for_status()
            return self._unwrap(response)

    async def enforce_request(
        self,
        mandate_token: str,
        pass_class_id: str,
        resource: Optional[str] = None,
        quantity: int = 1,
        spend: float = 0,
        purpose: Optional[str] = None,
        dpop_proof: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        allowed, msg = check_and_increment_rate_limit(api_key=api_key or self.api_key)
        if not allowed:
            return {
                "decision": "DENY",
                "reason": msg,
                "rate_limit_exceeded": True,
            }

        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            payload = {
                "mandateToken": mandate_token,
                "passClassId": pass_class_id,
                "quantity": quantity,
                "spend": spend,
            }
            if resource:
                payload["resource"] = resource
            if purpose:
                payload["purpose"] = purpose
            if dpop_proof:
                payload["dpopProof"] = dpop_proof

            response = await client.post("/api/v1/mandates/enforce", json=payload, headers=self._get_headers(api_key))
            response.raise_for_status()
            return self._unwrap(response)

    async def check_mandate_status(self, mandate_token: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            response = await client.get("/api/v1/mandates/status", params={"token": mandate_token}, headers=self._get_headers(api_key))
            response.raise_for_status()
            return self._unwrap(response)

    async def poll_escalation(self, auth_req_id: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            response = await client.get(f"/api/v1/mandates/escalations/{auth_req_id}", headers=self._get_headers(api_key))
            response.raise_for_status()
            return self._unwrap(response)

    async def respond_to_escalation(
        self,
        auth_req_id: str,
        approved: bool,
        reason: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            payload: Dict[str, Any] = {"approved": approved}
            if reason:
                payload["reason"] = reason
            response = await client.post(
                f"/api/v1/mandates/escalations/{auth_req_id}/respond",
                json=payload,
                headers=self._get_headers(api_key),
            )
            response.raise_for_status()
            return self._unwrap(response)

    async def revoke_mandate(self, jti: str, reason: Optional[str] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            payload = {"jti": jti}
            if reason:
                payload["reason"] = reason
            response = await client.post("/api/v1/mandates/revoke", json=payload, headers=self._get_headers(api_key))
            response.raise_for_status()
            return self._unwrap(response)

    async def get_holder_passes(
        self,
        external_user_id: Optional[str] = None,
        mandate_token: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            params = {}
            if external_user_id:
                params["externalUserId"] = external_user_id
            if mandate_token:
                params["token"] = mandate_token
            response = await client.get("/api/v1/mandates/holder-passes", params=params, headers=self._get_headers(api_key))
            response.raise_for_status()
            return self._unwrap(response)

    async def lookup_pass(self, pass_id: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10.0) as client:
            response = await client.get("/api/v1/mandates/pass-lookup", params={"passId": pass_id}, headers=self._get_headers(api_key))
            response.raise_for_status()
            return self._unwrap(response)
