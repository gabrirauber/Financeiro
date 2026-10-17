import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

from app.config import Settings
from app.database import Base, build_engine
from app.main import create_app


def test_postgres_migration_roundtrip(monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Defina TEST_DATABASE_URL para PostgreSQL descartável terminado em _test")
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("Teste de migração exige banco exclusivo com nome terminado em _test")
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("alembic.ini")
    engine = build_engine(Settings())
    try:
        # Nunca destruir um banco contendo tabelas desconhecidas.
        assert set(inspect(engine).get_table_names()) <= set(Base.metadata.tables) | {
            "alembic_version"
        }
        command.downgrade(config, "base")
        command.upgrade(config, "e08_income")
        with engine.begin() as connection:
            for email in ("gabrirauber@gmail.com", "antigo@example.com"):
                connection.execute(text(
                    "INSERT INTO users (id, email, password_hash) "
                    "VALUES (:id, :email, 'teste')"
                ), {"id": uuid4(), "email": email})
        command.upgrade(config, "head")
        with engine.connect() as connection:
            rows = connection.execute(text(
                "SELECT email, access_status, is_access_admin FROM users ORDER BY email"
            )).all()
        assert rows == [
            ("antigo@example.com", "approved", False),
            ("gabrirauber@gmail.com", "approved", True),
        ]
        command.upgrade(config, "head")
        command.check(config)
        assert "app_metadata" in inspect(engine).get_table_names()
        with TestClient(create_app(Settings())) as client:
            response = client.get("/health/ready")
            assert response.status_code == 200
            assert response.json()["database"] == "ready"
        protected_settings = Settings(app_env="test", access_approval_enabled=True)
        with TestClient(create_app(protected_settings)) as client:
            assert client.get("/health/ready").status_code == 200
        with engine.begin() as connection:
            connection.execute(text(
                "UPDATE users SET is_access_admin = false WHERE email = 'gabrirauber@gmail.com'"
            ))
        with TestClient(create_app(protected_settings)) as client:
            assert client.get("/health/ready").status_code == 503
        command.downgrade(config, "base")
        assert "app_metadata" not in inspect(engine).get_table_names()
        with TestClient(create_app(Settings())) as client:
            assert client.get("/health/ready").status_code == 503
        command.upgrade(config, "head")
    finally:
        engine.dispose()
