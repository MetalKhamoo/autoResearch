"""
main.py
───────
Entry-point for running the AutoResearch API server.

Usage:
    python main.py                   # development (auto-reload)
    uvicorn main:app --host 0.0.0.0  # production
"""

import uvicorn

from api.app import app  # noqa: F401 — re-exported so `uvicorn main:app` works
from config.settings import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.value.lower(),
    )
