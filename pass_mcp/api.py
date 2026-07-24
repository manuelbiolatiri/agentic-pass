import os
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pass_mcp.schemas import (
    IssueMandateRequest,
    EnforcePassRequest,
)
from pass_mcp.client import WalletKitPassClient

app = FastAPI(
    title="Pass-MCP Python Gateway",
    description="Python Gateway & MCP Server for Apple & Google Wallet Pass Agent Delegation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = WalletKitPassClient()

@app.get("/")
async def root():
    return {"status": "ok", "service": "pass-mcp-gateway"}

@app.post("/api/v1/mandates/issue")
async def issue_mandate(req: IssueMandateRequest):
    try:
        return await client.issue_mandate(
            principal_id=req.principal_id,
            agent_id=req.agent_id,
            authorization_details=[d.model_dump(by_alias=True, exclude_none=True) for d in req.authorization_details],
            agent_jkt=req.agent_jkt,
            ttl_seconds=req.ttl_seconds or 3600,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/mandates/enforce")
async def enforce_request(req: EnforcePassRequest):
    try:
        return await client.enforce_request(
            mandate_token=req.mandate_token,
            pass_class_id=req.pass_class_id,
            resource=req.resource,
            quantity=req.quantity or 1,
            spend=req.spend or 0,
            purpose=req.purpose,
            dpop_proof=req.dpop_proof,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/mandates/status")
async def check_status(token: str = Query(...)):
    try:
        return await client.check_mandate_status(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

def main():
    port = int(os.getenv("PORT", 9000))
    uvicorn.run("pass_mcp.api:app", host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    main()
