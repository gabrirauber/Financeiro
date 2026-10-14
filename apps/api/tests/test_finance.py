import os
from datetime import date
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import Settings
from app.finance.card_models import (
    CardInstallment,
    CardPurchase,
    CreditCard,
    FinancingInstallment,
    Invoice,
    InvoiceAdvance,
    InvoiceFinancing,
)
from app.finance.models import Account, Expense, Movement
from app.identity.models import (
    Invite,
    LoginSession,
    Membership,
    PasswordReset,
    RateLimit,
    User,
    Workspace,
)
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
        for model in (
            InvoiceAdvance,
            FinancingInstallment,
            InvoiceFinancing,
            CardInstallment,
            CardPurchase,
            Invoice,
            CreditCard,
            Expense,
            Movement,
            Account,
            Invite,
            PasswordReset,
            Membership,
            Workspace,
            LoginSession,
            User,
            RateLimit,
        ):
            db.execute(delete(model))
        db.commit()
    with TestClient(app) as test_client:
        try:
            yield test_client
        finally:
            with Session(app.state.engine) as db:
                for model in (
                    InvoiceAdvance,
                    FinancingInstallment,
                    InvoiceFinancing,
                    CardInstallment,
                    CardPurchase,
                    Invoice,
                    CreditCard,
                    Expense,
                    Movement,
                    Account,
                ):
                    db.execute(delete(model))
                db.commit()


def setup(client, email="owner@example.com", name="Casa"):
    result = client.post("/auth/register", json={"email": email, "password": "Senha-segura-123"})
    assert result.status_code == 201, result.text
    headers = {"Authorization": "Bearer " + result.json()["token"]}
    space = client.post("/workspaces", headers=headers, json={"name": name})
    assert space.status_code == 201, space.text
    return headers, space.json()["id"]


def account(client, headers, space, name, balance):
    result = client.post(
        f"/workspaces/{space}/accounts",
        headers=headers,
        json={"name": name, "kind": "bank", "opening_balance_cents": balance},
    )
    assert result.status_code == 201, result.text
    return result.json()["id"]


def today():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()


def test_correct_opening_balance_updates_cash_without_creating_income(client):
    headers, space = setup(client)
    account_id = account(client, headers, space, "Banco", 10_000)
    root = f"/workspaces/{space}"
    income = client.post(
        f"{root}/incomes", headers=headers,
        json={"account_id": account_id, "amount_cents": 2_000, "occurred_on": today()},
    )
    assert income.status_code == 201, income.text

    changed = client.patch(
        f"{root}/accounts/{account_id}/opening-balance", headers=headers,
        json={"opening_balance_cents": 15_000},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["opening_balance_cents"] == 15_000
    assert changed.json()["balance_cents"] == 17_000
    assert len(client.get(f"{root}/accounts/{account_id}/statement", headers=headers).json()) == 1

    invalid = client.patch(
        f"{root}/accounts/{account_id}/opening-balance", headers=headers,
        json={"opening_balance_cents": -1},
    )
    assert invalid.status_code == 422
    assert client.get(f"{root}/accounts", headers=headers).json()[0]["balance_cents"] == 17_000


def test_balances_statement_and_atomic_transfer(client):
    headers, space = setup(client)
    a = account(client, headers, space, "A", 100_000)
    b = account(client, headers, space, "B", 0)
    income = client.post(
        f"/workspaces/{space}/incomes",
        headers=headers,
        json={"account_id": a, "amount_cents": 50_000, "occurred_on": today(), "note": "Salário"},
    )
    assert income.status_code == 201, income.text
    transfer = client.post(
        f"/workspaces/{space}/transfers",
        headers=headers,
        json={
            "from_account_id": a,
            "to_account_id": b,
            "amount_cents": 20_000,
            "occurred_on": today(),
        },
    )
    assert transfer.status_code == 201, transfer.text
    root = f"/workspaces/{space}"
    rows = client.get(f"{root}/accounts", headers=headers).json()
    assert {item["name"]: item["balance_cents"] for item in rows} == {"A": 130_000, "B": 20_000}
    assert sum(item["balance_cents"] for item in rows) == 150_000
    statement = client.get(f"{root}/accounts/{a}/statement", headers=headers).json()
    assert {item["kind"] for item in statement} == {"income", "transfer_out"}
    assert all(item["kind"] != "opening" for item in statement)
    detail = client.get(f"{root}/transfers/{transfer.json()['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["to_account_id"] == b
    changed = client.patch(
        f"{root}/transfers/{transfer.json()['id']}",
        headers=headers,
        json={
            "from_account_id": a,
            "to_account_id": b,
            "amount_cents": 10_000,
            "occurred_on": today(),
            "note": "Ajuste",
        },
    )
    assert changed.status_code == 200, changed.text
    assert {
        item["name"]: item["balance_cents"]
        for item in client.get(f"{root}/accounts", headers=headers).json()
    } == {"A": 140_000, "B": 10_000}

    invalid = client.post(
        f"{root}/transfers",
        headers=headers,
        json={
            "from_account_id": a,
            "to_account_id": str(UUID(int=1)),
            "amount_cents": 999,
            "occurred_on": today(),
        },
    )
    assert invalid.status_code == 404
    assert len(client.get(f"{root}/accounts/{a}/statement", headers=headers).json()) == 2
    assert (
        client.delete(f"{root}/transfers/{transfer.json()['id']}", headers=headers).status_code
        == 204
    )
    rows = client.get(f"{root}/accounts", headers=headers).json()
    assert {item["name"]: item["balance_cents"] for item in rows} == {"A": 150_000, "B": 0}


def test_income_correction_and_previous_month_rejected(client):
    headers, space = setup(client)
    a = account(client, headers, space, "A", 100_000)
    b = account(client, headers, space, "B", 0)
    root = f"/workspaces/{space}"
    path = f"{root}/incomes"
    income = client.post(
        path, headers=headers, json={"account_id": a, "amount_cents": 5000, "occurred_on": today()}
    ).json()
    changed = client.patch(
        f"{path}/{income['id']}",
        headers=headers,
        json={"account_id": b, "amount_cents": 7000, "occurred_on": today(), "note": "Correção"},
    )
    assert changed.status_code == 200, changed.text
    assert [x["balance_cents"] for x in client.get(f"{root}/accounts", headers=headers).json()] == [
        100000,
        7000,
    ]
    this_month = date.fromisoformat(today())
    old = date(this_month.year - (this_month.month == 1), (this_month.month - 2) % 12 + 1, 1)
    payload = {"account_id": a, "amount_cents": 1, "occurred_on": old.isoformat()}
    assert client.post(path, headers=headers, json=payload).status_code == 422
    assert client.patch(f"{path}/{income['id']}", headers=headers, json=payload).status_code == 422
    with Session(client.app.state.engine) as db:
        row = db.get(Movement, UUID(income["id"]))
        row.occurred_on = old
        db.commit()
    assert client.delete(f"{path}/{income['id']}", headers=headers).status_code == 422
    assert client.get(f"{root}/accounts", headers=headers).json()[1]["balance_cents"] == 7000


def test_workspace_isolation_and_members_share_balance(client):
    owner, space = setup(client)
    outsider, other_space = setup(client, "other@example.com", "Outro")
    a = account(client, owner, space, "A", 10000)
    root = f"/workspaces/{space}"
    assert client.get(f"{root}/accounts", headers=outsider).status_code == 404
    assert client.get(f"{root}/accounts/{a}/statement", headers=outsider).status_code == 404
    assert (
        client.post(
            f"{root}/incomes",
            headers=outsider,
            json={"account_id": a, "amount_cents": 100, "occurred_on": today()},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/workspaces/{other_space}/incomes",
            headers=outsider,
            json={"account_id": a, "amount_cents": 100, "occurred_on": today()},
        ).status_code
        == 404
    )
    invite = client.post(f"{root}/invites", headers=owner).json()["code"]
    assert (
        client.post("/invites/accept", headers=outsider, json={"code": invite}).status_code
        == 409
    )
    registered = client.post(
        "/auth/register",
        json={"email": "guest@example.com", "password": "Senha-segura-123"},
    )
    guest = {"Authorization": "Bearer " + registered.json()["token"]}
    assert (
        client.post("/invites/accept", headers=guest, json={"code": invite}).status_code == 200
    )
    assert client.get(f"{root}/accounts", headers=guest).json()[0]["balance_cents"] == 10000


def test_invalid_amount_and_account_input(client):
    headers, space = setup(client)
    root = f"/workspaces/{space}"
    assert (
        client.post(
            f"{root}/accounts",
            headers=headers,
            json={"name": "  ", "kind": "bank", "opening_balance_cents": 0},
        ).status_code
        == 422
    )
    a = account(client, headers, space, "A", 0)
    assert (
        client.post(
            f"{root}/incomes",
            headers=headers,
            json={"account_id": a, "amount_cents": 0, "occurred_on": today()},
        ).status_code
        == 422
    )
