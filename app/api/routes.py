"""
FastAPI routes for MedOrch.

Endpoints:
  POST /chat            -- main orchestrated chat request
  POST /session          -- establish/update a user's role for the session
  GET  /audit/{request_id} -- fetch a single audit record
  GET  /health           -- liveness/readiness check

The API never exposes internal chain-of-thought; it returns structured
execution metadata only (agents considered, authorized, executed, and
citations).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.audit.logger import get_audit_service
from app.auth.models import Role
from app.graph.workflow import run_request

router = APIRouter()

# --- simple in-memory session store (POC-scope only) -----------------------
_sessions: dict[str, str] = {}  # user_id -> role


class ChatRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    role: str | None = Field(default=None, description="CLINICIAN | OPERATIONS | ADMIN | RESTRICTED")
    message: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    request_id: str
    status: str
    final_response: str
    agents_considered: list[str]
    authorized_agents: list[str]
    denied_agents: list[str]
    executed_agents: list[str]
    citations: list[dict]


class SessionRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    role: str = Field(..., description="CLINICIAN | OPERATIONS | ADMIN | RESTRICTED")


class SessionResponse(BaseModel):
    user_id: str
    role: str


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    role = req.role or _sessions.get(req.user_id)
    if role:
        role = role.upper()
        if role not in Role.values():
            raise HTTPException(status_code=422, detail=f"Unknown role '{role}'. Valid roles: {Role.values()}")

    request_id = f"req-{uuid.uuid4().hex[:12]}"
    result = run_request(user_id=req.user_id, role=role, message=req.message, request_id=request_id)

    # Persist the role on the session once provided, so subsequent requests
    # don't need to re-specify it (mirrors the Streamlit UI's role selector).
    if role:
        _sessions[req.user_id] = role

    return ChatResponse(
        request_id=result["request_id"],
        status=result.get("status", "ERROR"),
        final_response=result.get("final_answer", ""),
        agents_considered=result.get("detected_agents", []),
        authorized_agents=result.get("authorized_agents", []),
        denied_agents=result.get("denied_agents", []),
        executed_agents=result.get("executed_agents", []),
        citations=result.get("citations", []),
    )


@router.post("/session", response_model=SessionResponse)
def create_session(req: SessionRequest) -> SessionResponse:
    role = req.role.upper()
    if role not in Role.values():
        raise HTTPException(status_code=422, detail=f"Unknown role '{role}'. Valid roles: {Role.values()}")
    _sessions[req.user_id] = role
    return SessionResponse(user_id=req.user_id, role=role)


@router.get("/audit/{request_id}")
def get_audit(request_id: str) -> dict:
    record = get_audit_service().get(request_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Audit record not found")
    return record.to_dict()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "medorch"}
