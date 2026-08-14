from fastapi.testclient import TestClient

from app.main import app


def test_healthz():
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "ok"


def test_profile_requires_auth():
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/health/v1/profile")
    assert resp.status_code == 401
    assert resp.json()["code"] == 2001


def test_core_routes_registered():
    paths = set(app.openapi()["paths"])
    for path in (
        "/api/health/v1/recommend",
        "/api/health/v1/recommend/{rec_id}/swap",
        "/api/health/v1/avoid-list",
        "/api/health/v1/weight",
        "/api/health/v1/exercise",
        "/api/health/v1/report/weekly",
        "/api/health/v1/export",
        "/api/health/v1/sync",
        "/api/health/v1/sync/batch",
        "/api/health/v1/parse/text",
        "/api/health/v1/parse/image",
        "/api/health/v1/foods/contribute",
        "/api/health/v1/dashboard",
    ):
        assert path in paths, path
