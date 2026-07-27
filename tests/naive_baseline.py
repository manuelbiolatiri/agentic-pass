"""
Naive Reference Implementation for Conformance Testing

Simulates the standard/naive pattern common in 93% of current AI agent integrations:
- Reads scope and quantity directly from the request body payload.
- Does not verify RFC 8693 token signatures or claims server-side.
- Lacks SHA-256 idempotency caching.
- Binds credentials to whatever identity string is provided in the request body.
- Does not check revocation blacklists or DPoP sender-constrained proofs.
"""
from typing import Dict, Any, Optional
import time
import uuid

class NaiveAgentServer:
    def __init__(self):
        self.issued_passes = []

    def enforce_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        mandate_token = payload.get("mandateToken") or payload.get("mandate_token")
        pass_class = payload.get("passClass") or payload.get("pass_class_id") or "event_ticket"
        quantity = payload.get("quantity", 1)
        user_id = payload.get("externalUserId") or payload.get("agent_id") or "agent_unknown"

        # Naive Flaw 1: Accepts invalid/fake tokens if string is non-empty
        if not mandate_token:
            return {"decision": "DENY", "reason": "Missing token"}

        # Naive Flaw 2: Trusts request body quantity & scope without checking token ceiling
        # Naive Flaw 3: Does not check idempotency (creates duplicate pass every call)
        # Naive Flaw 4: Binds pass to request identity (often the purchasing agent instead of human)
        pass_obj = {
            "id": f"pass_naive_{uuid.uuid4().hex[:12]}",
            "passType": pass_class,
            "externalUserId": user_id,
            "quantity": quantity,
            "createdAt": time.time(),
        }
        self.issued_passes.append(pass_obj)

        return {
            "decision": "ALLOW",
            "reason": "Naive auto-approval",
            "pass": pass_obj,
            "isReplay": False,
        }
