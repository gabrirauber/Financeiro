import os
from datetime import datetime
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import Settings
from app.finance.models import Expense, Movement
from app.main import create_app


@pytest.fixture
def client(monkeypatch):
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Defina TEST_DATABASE_URL para banco descartável")
    assert (make_url(url).database or "").endswith("_test")
    monkeypatch.setenv("DATABASE_URL", url)
    command.upgrade(Config("alembic.ini"), "head")
    with TestClient(create_app(Settings(app_env="test"))) as test_client:
        yield test_client


def setup(client, suffix="a"):
    response = client.post(
        "/auth/register",
        json={"email": f"e05-{suffix}-{uuid4().hex}@example.com", "password": "Senha-segura-123"},
    )
    assert response.status_code == 201, response.text
    headers = {"Authorization": "Bearer " + response.json()["token"]}
    wid = client.post("/workspaces", headers=headers, json={"name": "Casa"}).json()["id"]
    root = f"/workspaces/{wid}"
    bank = client.post(
        f"{root}/accounts",
        headers=headers,
        json={"name": "Banco", "kind": "bank", "opening_balance_cents": 100000},
    ).json()["id"]
    cats = client.get(f"{root}/categories", headers=headers).json()
    casa = next(item for item in cats if item["name"] == "Casa")
    return headers, root, bank, casa["id"], casa["subcategories"][0]["id"]


def payload(bank, category, sub, cents=8000):
    return {
        "account_id": bank,
        "category_id": category,
        "subcategory_id": sub,
        "amount_cents": cents,
        "occurred_on": datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat(),
        "payment_method": "pix",
        "note": "Teste",
    }


def test_paid_expense_reduces_balance_once_and_edits_and_deletes(client):
    h, root, bank, category, sub = setup(client)
    expense = client.post(f"{root}/expenses", headers=h, json=payload(bank, category, sub))
    assert expense.status_code == 201, expense.text
    expense_id = expense.json()["id"]
    month = payload(bank, category, sub)["occurred_on"][:7]
    assert len(client.get(f"{root}/expenses?month={month}", headers=h).json()) == 1
    assert client.get(f"{root}/accounts", headers=h).json()[0]["balance_cents"] == 92000
    assert client.get(f"{root}/accounts/{bank}/statement", headers=h).json()[0]["kind"] == "expense"
    corrected = client.patch(
        f"{root}/expenses/{expense_id}", headers=h, json=payload(bank, category, sub, 9000)
    )
    assert corrected.status_code == 200, corrected.text
    assert client.get(f"{root}/accounts", headers=h).json()[0]["balance_cents"] == 91000
    assert client.delete(f"{root}/expenses/{expense_id}", headers=h).status_code == 204
    assert client.get(f"{root}/accounts", headers=h).json()[0]["balance_cents"] == 100000
    assert client.get(f"{root}/expenses?month={month}", headers=h).json() == []


def test_categories_are_shared_only_inside_workspace_and_preserve_history(client):
    h, root, bank, category, sub = setup(client)
    outsider, other_root, _, _, _ = setup(client, "b")
    assert client.get(f"{root}/categories", headers=outsider).status_code == 404
    assert (
        client.post(
            f"{other_root}/expenses", headers=outsider, json=payload(bank, category, sub)
        ).status_code
        == 404
    )
    custom = client.post(f"{root}/categories", headers=h, json={"name": "Saúde"})
    assert custom.status_code == 201, custom.text
    assert client.post(f"{root}/categories", headers=h, json={"name": "saúde"}).status_code == 409
    custom_id = custom.json()["id"]
    new_sub = client.post(
        f"{root}/categories/{custom_id}/subcategories", headers=h, json={"name": "Consulta"}
    )
    assert new_sub.status_code == 201
    expense = client.post(f"{root}/expenses", headers=h, json=payload(bank, category, sub))
    assert expense.status_code == 201
    assert (
        client.delete(f"{root}/categories/{category}/subcategories/{sub}", headers=h).status_code
        == 204
    )
    assert client.delete(f"{root}/categories/{category}", headers=h).status_code == 204
    month = payload(bank, category, sub)["occurred_on"][:7]
    assert (
        client.get(f"{root}/expenses?month={month}", headers=h).json()[0]["category_id"] == category
    )
    assert (
        client.post(f"{root}/expenses", headers=h, json=payload(bank, category, sub)).status_code
        == 422
    )
    assert (
        client.patch(
            f"{root}/expenses/{expense.json()['id']}",
            headers=h,
            json=payload(bank, category, sub, 9000),
        ).status_code
        == 200
    )
    restored = client.post(f"{root}/categories", headers=h, json={"name": "Casa"})
    assert restored.status_code == 201 and restored.json()["id"] == category
    restored_sub = client.post(
        f"{root}/categories/{category}/subcategories", headers=h, json={"name": "Aluguel"}
    )
    assert restored_sub.status_code == 201 and restored_sub.json()["id"] == sub
    assert (
        client.post(f"{root}/expenses", headers=h, json=payload(bank, category, sub)).status_code
        == 201
    )
    assert all(
        x["name"] != "Saúde"
        for x in client.get(f"{other_root}/categories", headers=outsider).json()
    )


def test_wrong_account_type_and_previous_month_rejected(client):
    h, root, bank, category, sub = setup(client)
    cash = client.post(
        f"{root}/accounts",
        headers=h,
        json={"name": "Carteira", "kind": "cash", "opening_balance_cents": 0},
    ).json()["id"]
    wrong = payload(cash, category, sub)
    assert client.post(f"{root}/expenses", headers=h, json=wrong).status_code == 422
    valid = {**wrong, "payment_method": "cash"}
    assert client.post(f"{root}/expenses", headers=h, json=valid).status_code == 201
    old = payload(bank, category, sub)
    old["occurred_on"] = "2020-01-01"
    assert client.post(f"{root}/expenses", headers=h, json=old).status_code == 422
    id_ = client.post(f"{root}/expenses", headers=h, json=payload(bank, category, sub)).json()["id"]
    assert client.patch(f"{root}/expenses/{id_}", headers=h, json=old).status_code == 422


def test_member_sees_shared_expense_and_old_month_cannot_be_deleted(client):
    owner, root, bank, category, sub = setup(client)
    registered = client.post(
        "/auth/register",
        json={"email": f"member-{uuid4().hex}@example.com", "password": "Senha-segura-123"},
    )
    member = {"Authorization": "Bearer " + registered.json()["token"]}
    code = client.post(f"{root}/invites", headers=owner).json()["code"]
    assert client.post("/invites/accept", headers=member, json={"code": code}).status_code == 200
    created = client.post(
        f"{root}/expenses", headers=owner, json=payload(bank, category, sub)
    ).json()
    month = created["occurred_on"][:7]
    assert (
        client.get(f"{root}/expenses?month={month}", headers=member).json()[0]["id"]
        == created["id"]
    )
    with Session(client.app.state.engine) as db:
        expense = db.get(Expense, UUID(created["id"]))
        db.get(Movement, expense.movement_id).occurred_on = datetime(2020, 1, 1).date()
        db.commit()
    assert client.delete(f"{root}/expenses/{created['id']}", headers=owner).status_code == 422
    assert (
        client.get(f"{root}/expenses?month=2020-01", headers=member).json()[0]["id"]
        == created["id"]
    )
