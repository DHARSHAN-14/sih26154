from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.templates.registry import load_all

# Load templates so root endpoint returns available_formats
load_all()

client = TestClient(app, raise_server_exceptions=False)


class TestRoot:
    def test_root_200(self):
        r = client.get("/")
        assert r.status_code == 200

    def test_root_service_name(self):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["service"] == "sutra"

    def test_root_has_formats(self):
        r = client.get("/")
        data = r.json()
        assert "available_formats" in data
        assert "advisory" in data["available_formats"]


class TestLiveness:
    def test_health_200(self):
        assert client.get("/api/health").status_code == 200

    def test_health_structure(self):
        data = client.get("/api/health").json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    def test_request_id_header(self):
        r = client.get("/api/health")
        assert "x-request-id" in r.headers


class TestReadiness:
    def test_ready_valid_status(self):
        r = client.get("/api/health/ready")
        assert r.status_code in (200, 503)

    def test_ready_structure(self):
        data = client.get("/api/health/ready").json()
        assert data["status"] in ("ready", "degraded")
        assert "checks" in data
        assert "database" in data["checks"]

    def test_ready_degraded_without_db(self):
        r = client.get("/api/health/ready")
        if r.status_code == 503:
            assert r.json()["status"] == "degraded"
        else:
            assert r.json()["status"] == "ready"
