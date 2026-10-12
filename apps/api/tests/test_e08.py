import os
from datetime import date, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import Settings
from app.finance.recurrence_models import (
    IncomeOccurrence,
    IncomePlan,
    IncomeReceipt,
    RecurringOccurrence,
    RecurringRule,
)
from app.finance.run_recurring import main as run_recurring
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
    with TestClient(app) as test_client:
        yield test_client
    with Session(app.state.engine) as db:
        for model in (
            IncomeReceipt,
            IncomeOccurrence,
            IncomePlan,
            RecurringOccurrence,
            RecurringRule,
        ):
            db.execute(delete(model))
        db.commit()


def setup(client):
    email = f"e08-{uuid4().hex}@example.com"
    registered = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "Senha-segura-123",
            "workspace_name": "Casa",
        },
    )
    assert registered.status_code == 201, registered.text
    headers = {"Authorization": "Bearer " + registered.json()["token"]}
    workspace = client.get("/workspaces", headers=headers).json()[0]["id"]
    root = f"/workspaces/{workspace}"
    user_id = client.get("/auth/me", headers=headers).json()["id"]
    account = client.post(
        f"{root}/accounts",
        headers=headers,
        json={
            "name": "Banco",
            "kind": "bank",
            "opening_balance_cents": 100_000,
        },
    ).json()["id"]
    cat = client.get(f"{root}/categories", headers=headers).json()[0]
    return headers, root, user_id, account, cat["id"], cat["subcategories"][0]["id"]


def current():
    return datetime.now(ZoneInfo("America/Sao_Paulo")).date()


def test_fixed_forecast_replaced_by_actual_expense_and_no_duplicate(client):
    headers, root, _, account, cat, sub = setup(client)
    payload = {
        "kind": "expense",
        "description": "Internet",
        "amount_cents": 10_000,
        "day_of_month": current().day,
        "category_id": cat,
        "subcategory_id": sub,
        "payment_method": "pix",
    }
    rule = client.post(f"{root}/recurring-rules", headers=headers, json=payload)
    assert rule.status_code == 201, rule.text
    period = current().strftime("%Y-%m")
    first = client.get(f"{root}/recurring-occurrences?month={period}", headers=headers).json()
    run_recurring()
    second = client.get(f"{root}/recurring-occurrences?month={period}", headers=headers).json()
    assert len(first) == len(second) == 1
    assert first[0]["id"] == second[0]["id"]
    assert first[0]["paid_cents"] is None
    assert client.get(f"{root}/accounts", headers=headers).json()[0]["balance_cents"] == 100_000
    paid = client.post(
        f"{root}/recurring-occurrences/{first[0]['id']}/pay",
        headers=headers,
        json={
            "account_id": account,
            "amount_cents": 11_000,
            "occurred_on": current().isoformat(),
            "payment_method": "pix",
        },
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["amount_cents"] == 10_000
    assert paid.json()["paid_cents"] == 11_000
    assert (
        client.post(
            f"{root}/recurring-occurrences/{first[0]['id']}/pay",
            headers=headers,
            json={
                "account_id": account,
                "amount_cents": 11_000,
                "occurred_on": current().isoformat(),
                "payment_method": "pix",
            },
        ).status_code
        == 200
    )
    assert client.get(f"{root}/accounts", headers=headers).json()[0]["balance_cents"] == 89_000


def test_card_subscription_once_per_month(client):
    headers, root, _, _, cat, sub = setup(client)
    card = client.post(
        f"{root}/cards",
        headers=headers,
        json={
            "name": "Cartão",
            "closing_day": 28,
            "due_day": 5,
            "closing_day_next_bill": False,
        },
    ).json()["id"]
    result = client.post(
        f"{root}/recurring-rules",
        headers=headers,
        json={
            "kind": "card",
            "description": "Assinatura",
            "amount_cents": 5000,
            "day_of_month": current().day,
            "category_id": cat,
            "subcategory_id": sub,
            "card_id": card,
        },
    )
    assert result.status_code == 201, result.text
    period = current().strftime("%Y-%m")
    first = client.get(f"{root}/recurring-occurrences?month={period}", headers=headers).json()
    run_recurring()
    second = client.get(f"{root}/recurring-occurrences?month={period}", headers=headers).json()
    assert len(first) == len(second) == 1
    assert first[0]["purchase_id"] == second[0]["purchase_id"]
    assert first[0]["purchase_id"] is not None
    invoices = client.get(f"{root}/invoices?card_id={card}", headers=headers).json()
    assert sum(len(invoice["installments"]) for invoice in invoices) == 1


def test_income_partial_deferral_and_single_cash_entry(client):
    headers, root, user_id, account, _, _ = setup(client)
    plan = client.post(
        f"{root}/income-plans",
        headers=headers,
        json={
            "description": "Salário",
            "amount_cents": 300_000,
            "day_of_month": current().day,
            "responsible_user_id": user_id,
        },
    )
    assert plan.status_code == 201, plan.text
    period = current().strftime("%Y-%m")
    occurrence = client.get(f"{root}/income-occurrences?month={period}", headers=headers).json()[0]
    assert occurrence["remaining_cents"] == 300_000
    assert len(client.get(f"{root}/income-reminders", headers=headers).json()) == 1
    assert (
        client.post(
            f"{root}/income-occurrences/{occurrence['id']}/defer", headers=headers
        ).status_code
        == 200
    )
    assert client.get(f"{root}/income-reminders", headers=headers).json() == []
    receipt = {
        "account_id": account,
        "amount_cents": 280_000,
        "occurred_on": current().isoformat(),
        "complete": False,
        "request_id": uuid4().hex,
    }
    first = client.post(
        f"{root}/income-occurrences/{occurrence['id']}/receive", headers=headers, json=receipt
    )
    assert first.status_code == 200, first.text
    assert first.json()["remaining_cents"] == 20_000
    again = client.post(
        f"{root}/income-occurrences/{occurrence['id']}/receive", headers=headers, json=receipt
    )
    assert again.status_code == 200
    assert again.json()["received_cents"] == 280_000
    assert client.get(f"{root}/accounts", headers=headers).json()[0]["balance_cents"] == 380_000
    final = client.post(
        f"{root}/income-occurrences/{occurrence['id']}/receive",
        headers=headers,
        json={
            **receipt,
            "amount_cents": 10_000,
            "complete": True,
            "request_id": uuid4().hex,
        },
    )
    assert final.status_code == 200, final.text
    assert final.json()["remaining_cents"] == 0
    assert final.json()["received_cents"] == 290_000
    assert client.get(f"{root}/accounts", headers=headers).json()[0]["balance_cents"] == 390_000


def test_income_adjusts_only_current_occurrence(client):
    headers, root, user_id, _, _, _ = setup(client)
    plan = client.post(
        f"{root}/income-plans",
        headers=headers,
        json={
            "description": "Aluguel recebido",
            "amount_cents": 200_000,
            "day_of_month": 20,
            "responsible_user_id": user_id,
        },
    ).json()
    period = current().strftime("%Y-%m")
    current_occurrence = client.get(
        f"{root}/income-occurrences?month={period}", headers=headers
    ).json()[0]
    changed = client.patch(
        f"{root}/income-occurrences/{current_occurrence['id']}",
        headers=headers,
        json={
            "expected_cents": 180_000,
        },
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["expected_cents"] == 180_000
    assert client.get(f"{root}/income-plans", headers=headers).json()[0]["amount_cents"] == 200_000
    assert date.fromisoformat(plan["start_month"]).month == current().month


def test_income_above_forecast_records_actual_amount_once(client):
    headers, root, user_id, account, _, _ = setup(client)
    assert client.post(
        f"{root}/income-plans",
        headers=headers,
        json={
            "description": "Renda variável",
            "amount_cents": 100_000,
            "day_of_month": current().day,
            "responsible_user_id": user_id,
        },
    ).status_code == 201
    period = current().strftime("%Y-%m")
    occurrence = client.get(f"{root}/income-occurrences?month={period}", headers=headers).json()[0]
    payload = {
        "account_id": account,
        "amount_cents": 110_000,
        "occurred_on": current().isoformat(),
        "complete": False,
        "request_id": uuid4().hex,
    }
    received = client.post(
        f"{root}/income-occurrences/{occurrence['id']}/receive", headers=headers, json=payload
    )
    assert received.status_code == 200, received.text
    assert received.json()["received_cents"] == 110_000
    assert received.json()["completed"] is True
    assert client.get(f"{root}/accounts", headers=headers).json()[0]["balance_cents"] == 210_000
