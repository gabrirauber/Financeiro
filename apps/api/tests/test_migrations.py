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
        command.upgrade(config, "e11_access_approval")
        with engine.begin() as connection:
            owner_id = connection.scalar(text(
                "SELECT id FROM users WHERE email = 'gabrirauber@gmail.com'"
            ))
            workspace_id = uuid4()
            connection.execute(text(
                "INSERT INTO workspaces (id, name, timezone) "
                "VALUES (:id, 'Casa', 'America/Sao_Paulo')"
            ), {"id": workspace_id})
            connection.execute(text(
                "INSERT INTO memberships (workspace_id, user_id, role) "
                "VALUES (:workspace, :owner, 'admin')"
            ), {"workspace": workspace_id, "owner": owner_id})
        command.upgrade(config, "head")
        with engine.connect() as connection:
            rows = connection.execute(text(
                "SELECT email, access_status, is_access_admin, is_demo "
                "FROM users ORDER BY email"
            )).all()
            example = connection.execute(text(
                "SELECT count(*), sum(amount_cents) FROM movements "
                "WHERE account_id IN (SELECT id FROM accounts "
                "WHERE name = 'Conta de demonstração') AND kind = 'expense'"
            )).one()
        assert rows == [
            ("antigo@example.com", "approved", False, False),
            ("gabrirauber@gmail.com", "approved", True, False),
            ("teste@teste.com.br", "pending", False, True),
        ]
        assert example == (3, 50000)
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
            credentials = {"email": "teste@teste.com.br", "password": "12345678"}
            assert client.post("/auth/login", json=credentials).status_code == 403
            with engine.begin() as connection:
                connection.execute(text(
                    "UPDATE users SET access_status = 'approved' "
                    "WHERE email = 'teste@teste.com.br'"
                ))
            login = client.post("/auth/login", json=credentials)
            assert login.status_code == 200, login.text
            assert login.json()["demo"] is True
            headers = {"Authorization": f"Bearer {login.json()['token']}"}
            assert client.get("/auth/me", headers=headers).json()["demo"] is True
            assert len(client.get("/workspaces", headers=headers).json()) == 1
            blocked = client.post("/workspaces", headers=headers,
                                  json={"name": "Não permitido"})
            assert blocked.status_code == 403
            assert "somente consultas" in blocked.json()["detail"]
            assert client.post("/auth/logout", headers=headers).status_code == 204
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
