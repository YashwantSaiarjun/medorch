"""
MedOrch FastAPI application entrypoint.

Run with:
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.rag.kb_loader import load_all_kbs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("medorch")

app = FastAPI(
    title="MedOrch -- Secure Multi-Agent Healthcare Orchestration Platform",
    description=(
        "Technical proof-of-concept demonstrating role-based, policy-enforced multi-agent "
        "orchestration. Uses ONLY synthetic data. NOT intended for clinical decision-making."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def on_startup() -> None:
    settings = get_settings()
    logger.info("MedOrch starting up (env=%s, llm_configured=%s)", settings.app_env, bool(settings.llm_api_key))
    load_all_kbs()
    logger.info("Synthetic knowledge bases loaded (clinical_kb, operations_kb).")


@app.get("/")
def root() -> dict:
    return {
        "service": "MedOrch",
        "disclaimer": "Proof-of-concept using synthetic data only. Not for clinical decision-making.",
        "docs": "/docs",
    }
