"""
tests/test_api.py — Integration tests for the FastAPI endpoints.
Uses TestClient (no network/model calls for unit tests).
"""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from dashboard.api import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_has_status_ok(self):
        resp = client.get("/health")
        assert resp.json()["status"] == "ok"

    def test_health_has_version(self):
        resp = client.get("/health")
        assert "version" in resp.json()


class TestAPIStructure:
    def test_docs_accessible(self):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_openapi_schema(self):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "paths" in schema
        # Key endpoints must exist in schema
        for path in ["/health", "/quotes", "/signals"]:
            assert path in schema["paths"], f"Missing API path: {path}"
