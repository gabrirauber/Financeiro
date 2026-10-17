import os
from datetime import timedelta

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import Settings
from app.identity.models import (
    Invite,
    LoginSession,
    Membership,
    PasswordReset,
    RateLimit,
    User,
    Workspace,
)
from app.identity.security import digest, now
from app.main import create_app


@pytest.fixture
def client(monkeypatch):
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Defina TEST_DATABASE_URL para banco descartável")
    assert (make_url(url).database or "").endswith("_test")
    monkeypatch.setenv("DATABASE_URL", url)
    command.upgrade(Config("alembic.ini"), "head")
    app = create_app(Settings(app_env="test"))
    with Session(app.state.engine) as db:
        for model in (Invite, PasswordReset, Membership, Workspace, LoginSession, User, RateLimit):
            db.execute(delete(model))
        db.commit()
    with TestClient(app) as test_client:
        yield test_client


def register(client, email):
    response = client.post("/auth/register", json={"email": email, "password": "Senha-segura-123"})
    assert response.status_code == 201, response.text
    return {"Authorization": "Bearer " + response.json()["token"]}


def test_registration_login_logout_and_session_expiry(client):
    headers = register(client, "Pessoa@example.com")
    response = client.get("/auth/me", headers=headers)
    assert response.json()["email"] == "pessoa@example.com"
    assert response.json()["onboarding_step"] == 0
    with Session(client.app.state.engine) as db:
        user = db.scalar(select(User))
        assert user.password_hash.startswith("$argon2")
        assert user.password_hash != "Senha-segura-123"
        session = db.scalar(select(LoginSession))
        assert session.token_hash != headers["Authorization"][7:]
    assert (
        client.post(
            "/auth/login", json={"email": "pessoa@example.com", "password": "senha-incorreta"}
        ).status_code
        == 401
    )
    login = client.post(
        "/auth/login", json={"email": "PESSOA@example.com", "password": "Senha-segura-123"}
    )
    assert login.status_code == 200
    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401
    token = login.json()["token"]
    with Session(client.app.state.engine) as db:
        db.get(LoginSession, digest(token)).expires_at = now() - timedelta(seconds=1)
        db.commit()
    assert client.get("/auth/me", headers={"Authorization": "Bearer " + token}).status_code == 401


def test_registration_selects_exactly_one_space(client):
    owner = client.post(
        "/auth/register",
        json={
            "email": "owner@example.com",
            "password": "Senha-segura-123",
            "workspace_name": "Minha casa",
        },
    )
    assert owner.status_code == 201, owner.text
    owner_headers = {"Authorization": "Bearer " + owner.json()["token"]}
    own_space = client.get("/workspaces", headers=owner_headers).json()
    assert len(own_space) == 1
    assert own_space[0]["name"] == "Minha casa"
    assert own_space[0]["role"] == "admin"
    assert (
        client.post("/workspaces", headers=owner_headers, json={"name": "Outro"}).status_code
        == 409
    )

    code = invite(client, owner_headers, own_space[0]["id"])["code"]
    invited = client.post(
        "/auth/register",
        json={
            "email": "guest@example.com",
            "password": "Senha-segura-123",
            "invite_code": code.lower(),
        },
    )
    assert invited.status_code == 201, invited.text
    guest_headers = {"Authorization": "Bearer " + invited.json()["token"]}
    assert client.get("/workspaces", headers=guest_headers).json() == [
        {"id": own_space[0]["id"], "name": "Minha casa", "role": "member"}
    ]
    assert (
        client.post("/workspaces", headers=guest_headers, json={"name": "Outro"}).status_code
        == 409
    )
    another_code = invite(client, owner_headers, own_space[0]["id"])["code"]
    assert (
        client.post(
            "/invites/accept", headers=guest_headers, json={"code": another_code}
        ).status_code
        == 409
    )

    invalid = client.post(
        "/auth/register",
        json={
            "email": "retry@example.com",
            "password": "Senha-segura-123",
            "invite_code": "INVALIDO",
        },
    )
    assert invalid.status_code == 400
    retry = client.post(
        "/auth/register",
        json={
            "email": "retry@example.com",
            "password": "Senha-segura-123",
            "workspace_name": "Pessoal",
        },
    )
    assert retry.status_code == 201, retry.text
    retry_headers = {"Authorization": "Bearer " + retry.json()["token"]}
    assert len(client.get("/workspaces", headers=retry_headers).json()) == 1


def test_workspace_isolation_and_member_permissions(client):
    a = register(client, "a@example.com")
    b = register(client, "b@example.com")
    c = register(client, "c@example.com")
    aid = client.get("/auth/me", headers=a).json()["id"]
    bid = client.get("/auth/me", headers=b).json()["id"]
    wid = client.post("/workspaces", headers=a, json={"name": "Casa"}).json()["id"]
    assert client.get("/workspaces", headers=b).json() == []
    assert client.get(f"/workspaces/{wid}/members", headers=c).status_code == 404
    from uuid import UUID

    with Session(client.app.state.engine) as db:
        db.add(Membership(workspace_id=UUID(wid), user_id=UUID(bid), role="member"))
        db.commit()
    assert len(client.get(f"/workspaces/{wid}/members", headers=b).json()) == 2
    assert client.delete(f"/workspaces/{wid}/members/{aid}", headers=b).status_code == 403
    assert client.delete(f"/workspaces/{wid}/members/{aid}", headers=a).status_code == 409
    assert client.delete(f"/workspaces/{wid}/members/{bid}", headers=a).status_code == 204
    assert client.get(f"/workspaces/{wid}/members", headers=b).status_code == 404


def test_invalid_inputs_do_not_echo_password(client):
    response = client.post("/auth/register", json={"email": "bad", "password": "secret"})
    assert response.status_code == 422
    assert "secret" not in response.text
    assert client.get("/workspaces").status_code == 401
    a = register(client, "a@example.com")
    assert (
        client.post(
            "/auth/register", json={"email": "A@example.com", "password": "Senha-segura-123"}
        ).status_code
        == 409
    )
    assert client.post("/workspaces", headers=a, json={"name": "   "}).status_code == 422


def test_login_rate_limit_persists_failed_attempts(client):
    data = {"email": "unknown@example.com", "password": "senha-incorreta"}
    for _ in range(15):
        assert client.post("/auth/login", json=data).status_code == 401
    assert client.post("/auth/login", json=data).status_code == 429


def invite(client, owner, wid):
    response = client.post(f"/workspaces/{wid}/invites", headers=owner)
    assert response.status_code == 201, response.text
    return response.json()


def test_invites_single_use_revocation_expiry_and_permissions(client):
    from uuid import UUID

    a, b, c = [register(client, f"{name}@example.com") for name in ("a", "b", "c")]
    wid = client.post("/workspaces", headers=a, json={"name": "Família"}).json()["id"]
    code = invite(client, a, wid)
    assert client.post(f"/workspaces/{wid}/invites", headers=c).status_code == 404
    assert client.post("/invites/accept", headers=b, json={"code": code["code"]}).status_code == 200
    assert client.post("/invites/accept", headers=c, json={"code": code["code"]}).status_code == 400
    assert client.post(f"/workspaces/{wid}/invites", headers=b).status_code == 403
    assert client.get("/workspaces", headers=b).json()[0]["id"] == wid
    cancelled = invite(client, a, wid)
    assert (
        client.delete(f"/workspaces/{wid}/invites/{cancelled['id']}", headers=a).status_code == 204
    )
    assert (
        client.post("/invites/accept", headers=c, json={"code": cancelled["code"]}).status_code
        == 400
    )
    expired = invite(client, a, wid)
    with Session(client.app.state.engine) as db:
        db.get(Invite, UUID(expired["id"])).expires_at = now() - timedelta(seconds=1)
        db.commit()
    assert (
        client.post("/invites/accept", headers=c, json={"code": expired["code"]}).status_code == 400
    )
    assert (
        client.post("/invites/accept", headers=c, json={"code": "inexistente"}).status_code == 400
    )


def test_transfer_admin_and_leave(client):
    a, b = [register(client, f"{name}@example.com") for name in ("a", "b")]
    aid = client.get("/auth/me", headers=a).json()["id"]
    bid = client.get("/auth/me", headers=b).json()["id"]
    wid = client.post("/workspaces", headers=a, json={"name": "Casa"}).json()["id"]
    assert client.post(f"/workspaces/{wid}/leave", headers=a).status_code == 409
    code = invite(client, a, wid)["code"]
    client.post("/invites/accept", headers=b, json={"code": code})
    assert client.post(f"/workspaces/{wid}/transfer-admin/{aid}", headers=b).status_code == 403
    assert client.post(f"/workspaces/{wid}/transfer-admin/{bid}", headers=a).status_code == 204
    assert client.post(f"/workspaces/{wid}/invites", headers=a).status_code == 403
    assert client.post(f"/workspaces/{wid}/leave", headers=a).status_code == 204
    assert client.get(f"/workspaces/{wid}/members", headers=a).status_code == 404
    assert client.post(f"/workspaces/{wid}/leave", headers=b).status_code == 409


def test_simultaneous_invite_acceptance(client):
    from concurrent.futures import ThreadPoolExecutor

    a, b, c = [register(client, f"{name}@example.com") for name in ("a", "b", "c")]
    wid = client.post("/workspaces", headers=a, json={"name": "Casa"}).json()["id"]
    code = invite(client, a, wid)["code"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda headers: client.post(
                    "/invites/accept", headers=headers, json={"code": code}
                ),
                (b, c),
            )
        )
    assert sorted(response.status_code for response in results) == [200, 400]
    assert len(client.get(f"/workspaces/{wid}/members", headers=a).json()) == 2


def test_recovery_neutral_response_single_use_and_revoked_sessions(client):
    a = register(client, "a@example.com")
    messages = []
    client.app.state.reset_sender = lambda email, link: messages.append((email, link))
    known = client.post("/auth/password-reset/request", json={"email": "a@example.com"})
    unknown = client.post("/auth/password-reset/request", json={"email": "unknown@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert len(messages) == 1
    token = messages[0][1].split("#reset=")[1]
    assert token not in known.text
    payload = {"token": token, "password": "Nova-senha-segura"}
    assert client.post("/auth/password-reset/confirm", json=payload).status_code == 204
    assert client.post("/auth/password-reset/confirm", json=payload).status_code == 400
    assert client.get("/auth/me", headers=a).status_code == 401
    assert (
        client.post(
            "/auth/login", json={"email": "a@example.com", "password": "Senha-segura-123"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/auth/login", json={"email": "a@example.com", "password": "Nova-senha-segura"}
        ).status_code
        == 200
    )


def test_recovery_expiry_and_missing_provider(client):
    register(client, "a@example.com")
    assert (
        client.post("/auth/password-reset/request", json={"email": "a@example.com"}).status_code
        == 503
    )
    messages = []
    client.app.state.reset_sender = lambda email, link: messages.append(link)
    client.post("/auth/password-reset/request", json={"email": "a@example.com"})
    token = messages[0].split("#reset=")[1]
    with Session(client.app.state.engine) as db:
        db.get(PasswordReset, digest(token)).expires_at = now() - timedelta(seconds=1)
        db.commit()
    assert (
        client.post(
            "/auth/password-reset/confirm", json={"token": token, "password": "Nova-senha-segura"}
        ).status_code
        == 400
    )
