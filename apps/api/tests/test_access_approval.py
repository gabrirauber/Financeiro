"""Novos cadastros só entram após liberação do administrador de acesso."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.identity.models import User
from app.main import create_app

pytest_plugins = ["test_identity"]


def test_new_registration_cannot_claim_access_administration(client):
    app = create_app(Settings(app_env="test", access_approval_enabled=True))
    with TestClient(app) as protected:
        result = protected.post("/auth/register", json={
            "email": "gabrirauber@gmail.com", "password": "Senha-segura-123",
            "workspace_name": "Casa",
        })
        assert result.status_code == 201
        assert result.json() == {"status": "pending"}
        with Session(protected.app.state.engine) as db:
            user = db.scalar(select(User).where(User.email == "gabrirauber@gmail.com"))
            assert user.access_status == "pending"
            assert user.is_access_admin is False
        assert protected.get("/health/ready").status_code == 503


def test_pending_approval_revocation_and_admin_permissions(client):
    owner = client.post("/auth/register", json={
        "email": "gabrirauber@gmail.com", "password": "Senha-segura-123",
        "workspace_name": "Casa",
    })
    assert owner.status_code == 201, owner.text
    with Session(client.app.state.engine) as db:
        admin = db.scalar(select(User).where(User.email == "gabrirauber@gmail.com"))
        admin.is_access_admin = True
        db.commit()

    app = create_app(Settings(app_env="test", access_approval_enabled=True))
    with TestClient(app) as protected:
        registration = protected.post("/auth/register", json={
            "email": "nova@example.com", "password": "Senha-segura-123",
            "workspace_name": "Pessoal",
        })
        assert registration.status_code == 201, registration.text
        assert registration.json() == {"status": "pending"}
        credentials = {"email": "nova@example.com", "password": "Senha-segura-123"}
        assert protected.post("/auth/login", json=credentials).status_code == 403
        wrong = protected.post("/auth/login", json={
            **credentials, "password": "Senha-errada-123",
        })
        assert wrong.status_code == 401

        owner_login = protected.post("/auth/login", json={
            "email": "gabrirauber@gmail.com", "password": "Senha-segura-123",
        })
        assert owner_login.status_code == 200, owner_login.text
        owner_headers = {"Authorization": "Bearer " + owner_login.json()["token"]}
        assert protected.get("/auth/me", headers=owner_headers).json()["access_admin"] is True
        users = protected.get("/admin/users", headers=owner_headers)
        assert users.status_code == 200, users.text
        applicant = next(item for item in users.json() if item["email"] == "nova@example.com")
        assert applicant["status"] == "pending"
        assert protected.get("/admin/users").status_code == 401
        assert protected.patch(f"/admin/users/{applicant['id']}/access", headers=owner_headers,
                               json={"status": "approved"}).status_code == 200

        login = protected.post("/auth/login", json=credentials)
        assert login.status_code == 200, login.text
        user_headers = {"Authorization": "Bearer " + login.json()["token"]}
        assert protected.get("/auth/me", headers=user_headers).json()["onboarding_step"] == 0
        assert protected.patch("/auth/onboarding", headers=user_headers,
                               json={"step": 1}).json() == {"step": 1}
        assert protected.patch("/auth/onboarding", headers=user_headers,
                               json={"step": 0}).json() == {"step": 1}
        assert protected.post("/auth/login", json=credentials).status_code == 200
        assert protected.get("/auth/me", headers=user_headers).json()["onboarding_step"] == 1
        assert protected.patch("/auth/onboarding", headers=user_headers,
                               json={"step": 4}).json() == {"step": 4}
        assert protected.get("/admin/users", headers=user_headers).status_code == 403
        assert protected.patch(f"/admin/users/{applicant['id']}/access", headers=user_headers,
                               json={"status": "revoked"}).status_code == 403
        assert protected.patch(f"/admin/users/{applicant['id']}/access", headers=owner_headers,
                               json={"status": "revoked"}).status_code == 200
        assert protected.get("/auth/me", headers=user_headers).status_code == 401
        assert protected.post("/auth/login", json=credentials).status_code == 403
        assert protected.patch(f"/admin/users/{applicant['id']}/access", headers=owner_headers,
                               json={"status": "approved"}).status_code == 200
        assert protected.post("/auth/login", json=credentials).status_code == 200
        admin_id = protected.get("/auth/me", headers=owner_headers).json()["id"]
        assert protected.patch(f"/admin/users/{admin_id}/access", headers=owner_headers,
                               json={"status": "revoked"}).status_code == 409


def test_rejected_invited_registration_keeps_workspace_isolated(client):
    owner = client.post("/auth/register", json={
        "email": "gabrirauber@gmail.com", "password": "Senha-segura-123",
        "workspace_name": "Casa",
    })
    owner_headers = {"Authorization": "Bearer " + owner.json()["token"]}
    space = client.get("/workspaces", headers=owner_headers).json()[0]["id"]
    code = client.post(f"/workspaces/{space}/invites", headers=owner_headers).json()["code"]
    with Session(client.app.state.engine) as db:
        admin = db.scalar(select(User).where(User.email == "gabrirauber@gmail.com"))
        admin.is_access_admin = True
        db.commit()

    app = create_app(Settings(app_env="test", access_approval_enabled=True))
    with TestClient(app) as protected:
        registration = protected.post("/auth/register", json={
            "email": "convidada@example.com", "password": "Senha-segura-123",
            "invite_code": code,
        })
        assert registration.json() == {"status": "pending"}
        assert protected.post("/auth/login", json={
            "email": "convidada@example.com", "password": "Senha-segura-123",
        }).status_code == 403
        users = protected.get("/admin/users", headers=owner_headers).json()
        applicant = next(item for item in users if item["email"] == "convidada@example.com")
        rejected = protected.patch(f"/admin/users/{applicant['id']}/access",
                                   headers=owner_headers, json={"status": "rejected"})
        assert rejected.status_code == 200, rejected.text
        assert protected.post("/auth/login", json={
            "email": "convidada@example.com", "password": "Senha-segura-123",
        }).status_code == 403
        members = protected.get(f"/workspaces/{space}/members", headers=owner_headers)
        assert members.status_code == 200
