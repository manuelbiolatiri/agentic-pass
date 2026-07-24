from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ApprovalThresholdSchema(BaseModel):
    quantity: Optional[int] = None
    spend: Optional[float] = None

class AuthorizationDetailSchema(BaseModel):
    type: str
    pass_class: str
    resource: Optional[str] = None
    max_quantity: Optional[int] = None
    max_spend: Optional[float] = None
    currency: Optional[str] = None
    purpose: Optional[str] = None
    approval_threshold: Optional[ApprovalThresholdSchema] = None

class IssueMandateRequest(BaseModel):
    principal_id: str = Field(..., alias="principalId")
    agent_id: str = Field(..., alias="agentId")
    agent_jkt: Optional[str] = Field(None, alias="agentJkt")
    authorization_details: List[AuthorizationDetailSchema] = Field(..., alias="authorizationDetails")
    ttl_seconds: Optional[int] = Field(3600, alias="ttlSeconds")

    class Config:
        populate_by_name = True

class EnforcePassRequest(BaseModel):
    mandate_token: str = Field(..., alias="mandateToken")
    pass_class_id: str = Field(..., alias="passClassId")
    resource: Optional[str] = None
    quantity: Optional[int] = 1
    spend: Optional[float] = 0
    purpose: Optional[str] = None
    dpop_proof: Optional[str] = Field(None, alias="dpopProof")

    class Config:
        populate_by_name = True

class RevokeMandateRequest(BaseModel):
    jti: str
    reason: Optional[str] = None

class EnforcementResult(BaseModel):
    decision: str  # ALLOW | DENY | ESCALATE | ERROR
    reason: str
    mandate_jti: Optional[str] = Field(None, alias="mandateJti")
    principal_id: Optional[str] = Field(None, alias="principalId")
    agent_id: Optional[str] = Field(None, alias="agentId")
    auth_req_id: Optional[str] = Field(None, alias="authReqId")
    pass_data: Optional[Dict[str, Any]] = Field(None, alias="pass")
    audit_hash: Optional[str] = Field(None, alias="auditHash")
    is_replay: Optional[bool] = Field(False, alias="isReplay")

    class Config:
        populate_by_name = True
