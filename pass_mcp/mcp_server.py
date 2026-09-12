import asyncio
import json
import sys
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP
from pass_mcp.client import WalletKitPassClient

mcp = FastMCP("pass-mcp")
client = WalletKitPassClient()

def format_pass_result(result: Any) -> str:
    """Formats pass responses into clean JSON with visual pass card preview image markdown."""
    try:
        json_str = json.dumps(result, indent=2)
        if isinstance(result, dict):
            pass_obj = result.get("pass") or (result if "urls" in result else None)
            if isinstance(pass_obj, dict):
                card_url = pass_obj.get("urls", {}).get("previewCardUrl")
                if card_url:
                    return f"![Pass Visual Card]({card_url})\n\n" + json_str
        return json_str
    except Exception:
        return json.dumps(result, indent=2)

@mcp.tool()
async def request_pass(
    mandate_token: str,
    pass_class: str,
    resource: Optional[str] = None,
    quantity: int = 1,
    spend: float = 0,
    purpose: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    """
    Request a digital wallet pass (Apple Wallet .pkpass / Google Wallet pass) under a signed agent delegation token.
    Enforces a limit of 100 pass issuances per day, tracked per business (api_key)
    when one is supplied, or per installer device otherwise.

    api_key: optional merchant API key to act on behalf of that business for this call.
    Falls back to the server's configured WALLETKIT_API_KEY when omitted, letting one
    running pass-mcp instance serve multiple businesses per-call.
    """
    try:
        result = await client.enforce_request(
            mandate_token=mandate_token,
            pass_class_id=pass_class,
            resource=resource,
            quantity=quantity,
            spend=spend,
            purpose=purpose,
            api_key=api_key,
        )
        return format_pass_result(result)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

@mcp.tool()
async def check_mandate_status(mandate_token: str, api_key: Optional[str] = None) -> str:
    """Check live status and remaining lifetime of a delegation token."""
    try:
        result = await client.check_mandate_status(mandate_token=mandate_token, api_key=api_key)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

@mcp.tool()
async def poll_escalation(auth_req_id: str, api_key: Optional[str] = None) -> str:
    """Poll status of a pending CIBA human-in-the-loop escalation request."""
    try:
        result = await client.poll_escalation(auth_req_id=auth_req_id, api_key=api_key)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

@mcp.tool()
async def respond_to_escalation(
    auth_req_id: str,
    approved: bool,
    reason: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    """Approve or deny a pending CIBA human-in-the-loop escalation request (Human Principal action)."""
    try:
        result = await client.respond_to_escalation(
            auth_req_id=auth_req_id,
            approved=approved,
            reason=reason,
            api_key=api_key,
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

@mcp.tool()
async def revoke_mandate(jti: str, reason: Optional[str] = None, api_key: Optional[str] = None) -> str:
    """Revoke a mandate immediately by JTI, blocking any further enforcement under it."""
    try:
        result = await client.revoke_mandate(jti=jti, reason=reason, api_key=api_key)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

@mcp.tool()
async def issue_mandate(
    principal_id: str,
    agent_id: str,
    authorization_details: List[Dict[str, Any]],
    ttl_seconds: int = 3600,
    api_key: Optional[str] = None,
) -> str:
    """
    Issue a signed RFC 8693 delegation mandate token for an AI agent (Principal / Admin tool).
    authorization_details array format: [{'type': 'event_ticket', 'pass_class': 'event_ticket', 'max_quantity': 2}]

    api_key: optional merchant API key to issue this mandate under that business.
    """
    try:
        normalized_details = []
        sys.stderr.write(f"[pass-mcp] authorization_details ==> {authorization_details}\n")
        for detail in authorization_details:
            if isinstance(detail, dict):
                d = dict(detail)
                if "pass_class" not in d and "type" in d:
                    d["pass_class"] = d["type"]
                if "max_quantity" not in d and "quantity" in d:
                    d["max_quantity"] = d["quantity"]
                normalized_details.append(d)
            else:
                normalized_details.append(detail)

        result = await client.issue_mandate(
            principal_id=principal_id,
            agent_id=agent_id,
            authorization_details=normalized_details,
            ttl_seconds=ttl_seconds,
            api_key=api_key,
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

@mcp.tool()
async def get_holder_passes(
    external_user_id: Optional[str] = None,
    mandate_token: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    """Get all active Apple & Google Wallet passes held by a human principal / user."""
    try:
        result = await client.get_holder_passes(
            external_user_id=external_user_id,
            mandate_token=mandate_token,
            api_key=api_key,
        )
        return format_pass_result(result)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

@mcp.tool()
async def lookup_pass(pass_id: str, api_key: Optional[str] = None) -> str:
    """Lookup full details of a specific pass by passId or serialNumber."""
    try:
        result = await client.lookup_pass(pass_id=pass_id, api_key=api_key)
        return format_pass_result(result)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

def main():
    """Main entrypoint running Pass-MCP server over Stdio transport."""
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
