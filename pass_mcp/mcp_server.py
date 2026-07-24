import asyncio
import json
import sys
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP
from pass_mcp.client import WalletKitPassClient

mcp = FastMCP("pass-mcp")
client = WalletKitPassClient()

@mcp.tool()
async def request_pass(
    mandate_token: str,
    pass_class: str,
    resource: Optional[str] = None,
    quantity: int = 1,
    spend: float = 0,
    purpose: Optional[str] = None,
) -> str:
    """
    Request a digital wallet pass (Apple Wallet .pkpass / Google Wallet pass) under a signed agent delegation token.
    Enforces a default free limit of 10 passes per day per installer.
    """
    try:
        result = await client.enforce_request(
            mandate_token=mandate_token,
            pass_class_id=pass_class,
            resource=resource,
            quantity=quantity,
            spend=spend,
            purpose=purpose,
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

@mcp.tool()
async def check_mandate_status(mandate_token: str) -> str:
    """Check live status and remaining lifetime of a delegation token."""
    try:
        result = await client.check_mandate_status(mandate_token=mandate_token)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

@mcp.tool()
async def poll_escalation(auth_req_id: str) -> str:
    """Poll status of a pending CIBA human-in-the-loop escalation request."""
    try:
        result = await client.poll_escalation(auth_req_id=auth_req_id)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

@mcp.tool()
async def issue_mandate(
    principal_id: str,
    agent_id: str,
    authorization_details: List[Dict[str, Any]],
    ttl_seconds: int = 3600,
) -> str:
    """
    Issue a signed RFC 8693 delegation mandate token for an AI agent (Principal / Admin tool).
    authorization_details array format: [{'type': 'event_ticket', 'pass_class': 'event_ticket', 'max_quantity': 2}]
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
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

def main():
    """Main entrypoint running Pass-MCP server over Stdio transport."""
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
