"""Phase 1 smoke test — /health endpoint"""

import pytest
from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_health_has_required_fields():
    response = client.get("/health")
    data = response.json()
    for field in ["status", "version", "uptime_seconds", "timestamp", "config"]:
        assert field in data, f"Missing field: {field}"


def test_health_config_snapshot():
    response = client.get("/health")
    config = response.json()["config"]
    assert "llm_provider" in config
    assert "search_provider" in config


def test_unknown_route_returns_404():
    response = client.get("/nonexistent")
    assert response.status_code == 404
