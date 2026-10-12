import os
from datetime import date, datetime, timedelta
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
from app.finance.card_models import (
    CardInstallment,
    CardPurchase,
    CreditCard,
    FinancingInstallment,
    Invoice,
    InvoiceAdvance,
    InvoiceFinancing,
)
from app.finance.cycles import shift_month
from app.finance.models import Account, Expense, Movement
from app.finance.recurrence_models import (
    IncomeOccurrence,
    IncomePlan,
    IncomeReceipt,
    RecurringOccurrence,
    RecurringRule,
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
    with TestClient(app) as api:
        yield api
    with Session(app.state.engine) as db:
        for model in (
            IncomeReceipt, IncomeOccurrence, IncomePlan,
            RecurringOccurrence, RecurringRule,
            InvoiceAdvance, FinancingInstallment, InvoiceFinancing,
            CardInstallment, CardPurchase, Invoice, CreditCard,
            Expense, Movement, Account,
        ):
            db.execute(delete(model))
        db.commit()


def setup(client):
    response = client.post("/auth/register", json={
        "email": f"e09-{uuid4().hex}@example.com",
        "password": "Senha-segura-123",
        "workspace_name": "Casa",
    })
    assert response.status_code == 201, response.text
    headers = {"Authorization": "Bearer " + response.json()["token"]}
    workspace_id = client.get("/workspaces", headers=headers).json()[0]["id"]
    user_id = client.get("/auth/me", headers=headers).json()["id"]
    root = f"/workspaces/{workspace_id}"
    account = client.post(f"{root}/accounts", headers=headers, json={
        "name": "Banco", "kind": "bank", "opening_balance_cents": 0,
    }).json()["id"]
    category = client.get(f"{root}/categories", headers=headers).json()[0]
    return headers, root, user_id, account, category["id"], category["subcategories"][0]["id"]


def current():
    return datetime.now(ZoneInfo("America/Sao_Paulo")).date()


def test_month_result_and_cash_projection_do_not_deduct_paid_twice(client):
    headers, root, user_id, account, cat, sub = setup(client)
    month = current().replace(day=1).isoformat()
    period = month[:7]
    assert client.post(f"{root}/income-plans", headers=headers, json={
        "description": "Salário", "amount_cents": 300_000,
        "day_of_month": current().day, "responsible_user_id": user_id,
    }).status_code == 201
    income = client.get(f"{root}/income-occurrences?month={period}", headers=headers).json()[0]
    assert client.post(f"{root}/income-occurrences/{income['id']}/receive", headers=headers,
        json={"account_id": account, "amount_cents": 150_000,
              "occurred_on": current().isoformat(), "complete": False,
              "request_id": uuid4().hex}).status_code == 200
    assert client.post(f"{root}/expenses", headers=headers, json={
        "account_id": account, "category_id": cat, "subcategory_id": sub,
        "amount_cents": 40_000, "occurred_on": current().isoformat(),
        "payment_method": "pix", "note": "Mercado",
    }).status_code == 201
    assert client.post(f"{root}/recurring-rules", headers=headers, json={
        "kind": "expense", "description": "Aluguel", "amount_cents": 80_000,
        "day_of_month": current().day, "category_id": cat,
        "subcategory_id": sub, "payment_method": "pix",
    }).status_code == 201
    card = client.post(f"{root}/cards", headers=headers, json={
        "name": "Cartão", "closing_day": 10, "due_day": 20,
        "closing_day_next_bill": False,
    }).json()["id"]
    assert client.post(f"{root}/card-purchases", headers=headers, json={
        "card_id": card, "category_id": cat, "subcategory_id": sub,
        "purchased_on": current().isoformat(), "total_cents": 60_000,
        "installment_count": 1, "legacy": True,
        "first_bill_month": month,
    }).status_code == 201
    response = client.get(f"{root}/projection?month={period}", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["income_cents"] == 300_000
    assert body["received_income_cents"] == 150_000
    assert body["expected_income_cents"] == 150_000
    assert body["paid_expenses_cents"] == 40_000
    assert body["pending_fixed_cents"] == 80_000
    assert body["card_commitment_cents"] == 60_000
    assert body["result_cents"] == 120_000
    assert body["cash_balance_cents"] == 110_000
    assert body["projected_balance_cents"] == 120_000


def test_zero_income_deficit_and_historical_balance(client):
    headers, root, _, account, cat, sub = setup(client)
    period = current().strftime("%Y-%m")
    assert client.post(f"{root}/expenses", headers=headers, json={
        "account_id": account, "category_id": cat, "subcategory_id": sub,
        "amount_cents": 1000, "occurred_on": current().isoformat(),
        "payment_method": "pix", "note": "Teste",
    }).status_code == 201
    body = client.get(f"{root}/projection?month={period}", headers=headers).json()
    assert body["income_cents"] == 0
    assert body["result_cents"] == -1000
    assert body["commitment_percent"] is None
    assert body["projected_balance_cents"] == -1000
    previous = current().replace(day=1)
    previous = previous.fromordinal(previous.toordinal() - 1).strftime("%Y-%m")
    history = client.get(f"{root}/projection?month={previous}", headers=headers).json()
    assert history["kind"] == "historical"
    assert history["cash_balance_cents"] == 0
    assert history["projected_balance_cents"] == 0


def test_refinanced_principal_moves_to_future_month(client, monkeypatch):
    headers, root, _, account, cat, sub = setup(client)
    month = current().replace(day=1)
    card = client.post(f"{root}/cards", headers=headers, json={
        "name": "Cartão", "closing_day": max(1, current().day - 1), "due_day": 31,
        "closing_day_next_bill": False,
    }).json()["id"]
    created = client.post(f"{root}/card-purchases", headers=headers, json={
        "card_id": card, "category_id": cat, "subcategory_id": sub,
        "purchased_on": current().isoformat(), "total_cents": 100_000,
        "installment_count": 1, "legacy": True,
        "first_bill_month": month.isoformat(),
    })
    assert created.status_code == 201, created.text
    invoice_id = created.json()["installments"][0]["invoice_id"]
    import app.finance.financing as financing

    after_close = date.fromisoformat(
        client.get(f"{root}/invoices/{invoice_id}", headers=headers).json()["closes_on"]
    ) + timedelta(days=1)
    monkeypatch.setattr(financing, "today", lambda _workspace: after_close)
    paid = client.post(f"{root}/invoices/{invoice_id}/pay-partial", headers=headers, json={
        "account_id": account, "paid_cents": 60_000,
        "fee_cents": 4000, "installment_count": 2,
    })
    assert paid.status_code == 200, paid.text
    now = client.get(f"{root}/projection?month={month:%Y-%m}", headers=headers).json()
    assert now["card_commitment_cents"] == 60_000
    assert now["card_refinanced_cents"] == 40_000
    assert now["card_pending_cents"] == 0
    assert now["cash_balance_cents"] == -60_000
    assert now["projected_balance_cents"] == -60_000
    next_month = shift_month(month, 1)
    future = client.get(f"{root}/projection?month={next_month:%Y-%m}", headers=headers).json()
    assert future["card_commitment_cents"] == 22_000
    assert future["result_cents"] == -22_000
    assert future["projected_balance_cents"] == -82_000


def test_extra_income_and_partial_forecast_are_both_counted(client):
    headers, root, user_id, account, _, _ = setup(client)
    period = current().strftime("%Y-%m")
    assert client.post(f"{root}/income-plans", headers=headers, json={
        "description": "Salário", "amount_cents": 300_000,
        "day_of_month": current().day, "responsible_user_id": user_id,
    }).status_code == 201
    occurrence = client.get(f"{root}/income-occurrences?month={period}", headers=headers).json()[0]
    assert client.post(f"{root}/income-occurrences/{occurrence['id']}/receive", headers=headers,
        json={"account_id": account, "amount_cents": 280_000,
              "occurred_on": current().isoformat(), "complete": False,
              "request_id": uuid4().hex}).status_code == 200
    assert client.post(f"{root}/incomes", headers=headers, json={
        "account_id": account, "amount_cents": 20_000,
        "occurred_on": current().isoformat(), "note": "Extra",
    }).status_code == 201
    body = client.get(f"{root}/projection?month={period}", headers=headers).json()
    assert body["received_income_cents"] == 300_000
    assert body["expected_income_cents"] == 20_000
    assert body["income_cents"] == 320_000
    assert body["projected_balance_cents"] == 320_000


def test_old_pending_bill_is_separate_from_current_result(client, monkeypatch):
    headers, root, _, _, cat, sub = setup(client)
    month = current().replace(day=1)
    assert client.post(f"{root}/recurring-rules", headers=headers, json={
        "kind": "expense", "description": "Internet", "amount_cents": 10_000,
        "day_of_month": current().day, "category_id": cat,
        "subcategory_id": sub, "payment_method": "pix",
    }).status_code == 201
    import app.finance.projection as projection_module

    next_month = shift_month(month, 1)
    monkeypatch.setattr(projection_module, "today", lambda _workspace: next_month)
    body = client.get(f"{root}/projection?month={next_month:%Y-%m}", headers=headers).json()
    assert body["pending_fixed_cents"] == 10_000
    assert body["overdue_cents"] == 10_000
    assert body["result_cents"] == -10_000
    assert body["projected_balance_cents"] == -20_000


def test_future_card_subscription_is_projected_before_purchase_date(client):
    headers, root, _, _, cat, sub = setup(client)
    month = current().replace(day=1)
    card = client.post(f"{root}/cards", headers=headers, json={
        "name": "Assinaturas", "closing_day": max(1, current().day - 1),
        "due_day": 31, "closing_day_next_bill": True,
    }).json()["id"]
    assert client.post(f"{root}/recurring-rules", headers=headers, json={
        "kind": "card", "description": "Streaming", "amount_cents": 5000,
        "day_of_month": current().day, "category_id": cat,
        "subcategory_id": sub, "card_id": card,
    }).status_code == 201
    next_month = shift_month(month, 1)
    first = client.get(f"{root}/projection?month={next_month:%Y-%m}", headers=headers).json()
    assert first["card_commitment_cents"] == 5000
    second_month = shift_month(month, 2)
    second = client.get(f"{root}/projection?month={second_month:%Y-%m}", headers=headers).json()
    assert second["card_commitment_cents"] == 5000
    assert second["projected_balance_cents"] == -10_000


def test_deactivating_rule_removes_previously_generated_future_forecast(client):
    headers, root, _, _, cat, sub = setup(client)
    rule = client.post(f"{root}/recurring-rules", headers=headers, json={
        "kind": "expense", "description": "Internet", "amount_cents": 10_000,
        "day_of_month": current().day, "category_id": cat,
        "subcategory_id": sub, "payment_method": "pix",
    }).json()
    next_month = shift_month(current().replace(day=1), 1)
    before = client.get(f"{root}/projection?month={next_month:%Y-%m}", headers=headers).json()
    assert before["pending_fixed_cents"] == 10_000
    assert client.delete(f"{root}/recurring-rules/{rule['id']}", headers=headers).status_code == 204
    after = client.get(f"{root}/projection?month={next_month:%Y-%m}", headers=headers).json()
    assert after["pending_fixed_cents"] == 0
    assert after["result_cents"] == 0


def test_old_unpaid_invoice_reduces_cash_without_new_month_expense(client, monkeypatch):
    headers, root, _, _, cat, sub = setup(client)
    month = current().replace(day=1)
    card = client.post(f"{root}/cards", headers=headers, json={
        "name": "Cartão", "closing_day": 10, "due_day": 20,
        "closing_day_next_bill": False,
    }).json()["id"]
    assert client.post(f"{root}/card-purchases", headers=headers, json={
        "card_id": card, "category_id": cat, "subcategory_id": sub,
        "purchased_on": current().isoformat(), "total_cents": 60_000,
        "installment_count": 1, "legacy": True,
        "first_bill_month": month.isoformat(),
    }).status_code == 201
    import app.finance.projection as projection_module

    next_month = shift_month(month, 1)
    monkeypatch.setattr(projection_module, "today", lambda _workspace: next_month)
    body = client.get(f"{root}/projection?month={next_month:%Y-%m}", headers=headers).json()
    assert body["card_commitment_cents"] == 0
    assert body["overdue_cents"] == 60_000
    assert body["result_cents"] == 0
    assert body["projected_balance_cents"] == -60_000
