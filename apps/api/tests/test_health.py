from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.config import Settings
from app.main import create_app


def settings(**kwargs):
    return Settings(
        _env_file=None,
        database_url="postgresql://example:secret@127.0.0.1:1/unreachable",
        **kwargs,
    )


def test_liveness_does_not_require_database():
    with TestClient(create_app(settings())) as client:
        assert client.get("/health/live").json() == {"status": "ok", "stage": "E04"}


def test_readiness_reports_failure_without_secrets():
    app = create_app(settings())
    with patch("app.main.database_ready", side_effect=OperationalError("secret", {}, Exception())):
        with TestClient(app) as client:
            response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unavailable", "stage": "E04"}
    assert "secret" not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_readiness_requires_migrated_schema():
    with patch("app.main.database_ready", return_value=False):
        with TestClient(create_app(settings())) as client:
            assert client.get("/health/ready").status_code == 503


def test_cors_allows_only_configured_browser_origin():
    with TestClient(create_app(settings(cors_origins=["http://localhost:8081"]))) as client:
        allowed = client.get("/health/live", headers={"Origin": "http://localhost:8081"})
        denied = client.get("/health/live", headers={"Origin": "https://untrusted.example"})
        assert allowed.headers["access-control-allow-origin"] == "http://localhost:8081"
        assert "access-control-allow-origin" not in denied.headers


def test_production_hides_docs():
    with TestClient(create_app(settings(app_env="production"))) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_railway_url_uses_psycopg_and_preserves_password():
    configured = Settings(_env_file=None, database_url="postgres://u:p%25ss@host/db")
    assert configured.sqlalchemy_url.drivername == "postgresql+psycopg"
    assert configured.sqlalchemy_url.password == "p%ss"
