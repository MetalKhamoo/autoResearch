"""
api/routers/health.py
─────────────────────
Health-check endpoints.  No DB or external dependencies — always fast.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from config.settings import get_settings

router = APIRouter(tags=["health"])

_START_TIME = time.time()
settings = get_settings()


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    timestamp: str
    config: dict


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health() -> HealthResponse:
    """
    Returns service status, version, uptime, and a subset of active config.
    No authentication required — used by load balancers and CI smoke tests.
    """
    return HealthResponse(
        status="ok",
        version="0.1.0",
        uptime_seconds=round(time.time() - _START_TIME, 2),
        timestamp=datetime.now(timezone.utc).isoformat(),
        config={
            "llm_provider": settings.llm_provider.value,
            "llm_model": settings.llm_model,
            "search_provider": settings.search_provider.value,
            "log_level": settings.log_level.value,
        },
    )
