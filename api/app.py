"""
api/app.py
──────────
FastAPI application factory.
Only Phase 1 endpoints are wired here; later phases will add routers.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from importlib.metadata import version as pkg_version

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config.settings import get_settings

settings = get_settings()

# ── Startup / Shutdown ────────────────────────────────────────────────────────

_START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialise resources on startup, clean up on shutdown.
    Phases 2-8 will hook into this context manager.
    """
    # Phase 2+: initialise DB, vector store, scheduler here
    yield
    # Phase 2+: graceful shutdown of scheduler, DB pool here


# ── App factory ───────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    app = FastAPI(
        title="AutoResearch",
        description=(
            "Autonomous AI Research & Reporting Agent — "
            "LLM tool-use, RAG, multi-agent orchestration, scheduling."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS — wide open for local dev; tighten in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    from api.routers import health  # noqa: F401  (avoids circular at module level)

    app.include_router(health.router)

    # Phase 4+: uncomment as routers are built
    # from api.routers import research, reports
    # app.include_router(research.router, prefix="/research", tags=["research"])
    # app.include_router(reports.router, prefix="/reports", tags=["reports"])

    # Phase 6+: serve dashboard static files
    # app.mount("/", StaticFiles(directory="dashboard", html=True), name="dashboard")

    return app


app = create_app()
