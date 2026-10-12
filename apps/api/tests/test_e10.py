"""O PDF deve repetir o painel, proteger dados e suportar relatórios longos."""

import os
from datetime import date, timedelta
from io import BytesIO
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import delete
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from test_e09 import current, setup

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


def pdf_text(response):
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "no-store"
    assert response.content.startswith(b"%PDF-")
    document = PdfReader(BytesIO(response.content))
    return document, "\n".join(page.extract_text() for page in document.pages)


def test_empty_report_and_detail_option(client):
    headers, root, _, _, _, _ = setup(client)
    period = current().strftime("%Y-%m")
    assert client.get(f"{root}/reports/monthly.pdf?month={period}").status_code == 401
    invalid = client.get(f"{root}/reports/monthly.pdf?month=2026-13", headers=headers)
    assert invalid.status_code == 422
    summary = client.get(f"{root}/projection?month={period}", headers=headers).json()
    response = client.get(f"{root}/reports/monthly.pdf?month={period}", headers=headers)
    _, text = pdf_text(response)
    assert "Nenhuma compra ou despesa" in text
    assert "Resultado do mês" in text
    assert "R$ 0,00" in text
    assert summary["result_cents"] == 0
    assert "Lançamentos detalhados" not in text
    response = client.get(f"{root}/reports/monthly.pdf?month={period}&detail=true",
                          headers=headers)
    _, text = pdf_text(response)
    assert "Lançamentos detalhados" in text
    assert "Nenhum lançamento detalhado" in text


def test_report_matches_projection_and_shows_categories_invoices_and_accounts(client):
    headers, root, user_id, account, cat, sub = setup(client)
    month = current().replace(day=1)
    period = f"{month:%Y-%m}"
    assert client.post(f"{root}/income-plans", headers=headers, json={
        "description": "Salário", "amount_cents": 300_000,
        "day_of_month": current().day, "responsible_user_id": user_id,
    }).status_code == 201
    assert client.post(f"{root}/expenses", headers=headers, json={
        "account_id": account, "category_id": cat, "subcategory_id": sub,
        "amount_cents": 10_000, "occurred_on": current().isoformat(),
        "payment_method": "pix", "note": "Almoço & café",
    }).status_code == 201
    card = client.post(f"{root}/cards", headers=headers, json={
        "name": "Cartão principal", "closing_day": 10, "due_day": 20,
        "closing_day_next_bill": False,
    }).json()["id"]
    assert client.post(f"{root}/card-purchases", headers=headers, json={
        "card_id": card, "category_id": cat, "subcategory_id": sub,
        "purchased_on": current().isoformat(), "total_cents": 60_000,
        "installment_count": 1, "legacy": True, "first_bill_month": month.isoformat(),
        "note": "Notebook",
    }).status_code == 201
    summary = client.get(f"{root}/projection?month={period}", headers=headers).json()
    assert summary["result_cents"] == 230_000
    response = client.get(f"{root}/reports/monthly.pdf?month={period}&detail=true",
                          headers=headers)
    document, text = pdf_text(response)
    assert len(document.pages) >= 1
    for fragment in ("R$ 3.000,00", "R$ 2.300,00", "R$ 600,00", "R$ 100,00",
                     "Salário", "Cartão principal", "Banco", "Almoço & café", "Notebook"):
        assert fragment in text
    assert response.headers["content-disposition"] == (
        f'attachment; filename="financeiro-{period}.pdf"'
    )


def test_historical_pdf_uses_historical_balance_and_is_scoped_to_member(client, monkeypatch):
    headers, root, _, account, _, _ = setup(client)
    month = current().replace(day=1)
    assert client.post(f"{root}/incomes", headers=headers, json={
        "account_id": account, "amount_cents": 50_000,
        "occurred_on": current().isoformat(), "note": "Extra",
    }).status_code == 201
    import app.finance.projection as projection_module

    monkeypatch.setattr(projection_module, "today", lambda _workspace: shift_month(month, 1))
    response = client.get(f"{root}/reports/monthly.pdf?month={month:%Y-%m}", headers=headers)
    _, text = pdf_text(response)
    assert "R$ 500,00" in text
    assert "Saldo histórico" in text
    assert "Mês encerrado" in text

    outsider = client.post("/auth/register", json={
        "email": f"e10-outsider-{uuid4().hex}@example.com",
        "password": "Senha-segura-123", "workspace_name": "Outra casa",
    }).json()["token"]
    denied = client.get(f"{root}/reports/monthly.pdf?month={month:%Y-%m}",
                        headers={"Authorization": f"Bearer {outsider}"})
    assert denied.status_code == 404


def test_long_detail_spans_pages_without_losing_last_item(client):
    headers, root, _, account, cat, sub = setup(client)
    period = current().strftime("%Y-%m")
    for index in range(45):
        response = client.post(f"{root}/expenses", headers=headers, json={
            "account_id": account, "category_id": cat, "subcategory_id": sub,
            "amount_cents": 100, "occurred_on": current().isoformat(),
            "payment_method": "pix", "note": f"Lançamento extenso número {index:02d} - ação & café",
        })
        assert response.status_code == 201, response.text
    response = client.get(f"{root}/reports/monthly.pdf?month={period}&detail=true",
                          headers=headers)
    document, text = pdf_text(response)
    assert len(document.pages) >= 2
    assert "Lançamento extenso número 00" in text
    assert "Lançamento extenso número 44" in text
    assert all("Página" in (page.extract_text() or "") for page in document.pages)


def test_refinancing_is_explained_without_counting_principal_twice(client, monkeypatch):
    headers, root, _, account, cat, sub = setup(client)
    month = current().replace(day=1)
    card = client.post(f"{root}/cards", headers=headers, json={
        "name": "Cartão", "closing_day": max(1, current().day - 1),
        "due_day": 31, "closing_day_next_bill": False,
    }).json()["id"]
    created = client.post(f"{root}/card-purchases", headers=headers, json={
        "card_id": card, "category_id": cat, "subcategory_id": sub,
        "purchased_on": current().isoformat(), "total_cents": 100_000,
        "installment_count": 1, "legacy": True, "first_bill_month": month.isoformat(),
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
        "fee_cents": 4_000, "installment_count": 2,
    })
    assert paid.status_code == 200, paid.text
    current_pdf = client.get(f"{root}/reports/monthly.pdf?month={month:%Y-%m}",
                             headers=headers)
    _, text = pdf_text(current_pdf)
    assert "R$ 600,00" in text
    assert "R$ 400,00" in text
    assert "principal refinanciado" in text.lower()
    future_month = shift_month(month, 1)
    future_pdf = client.get(f"{root}/reports/monthly.pdf?month={future_month:%Y-%m}",
                            headers=headers)
    _, future_text = pdf_text(future_pdf)
    assert "R$ 220,00" in future_text
    assert "R$ 200,00" in future_text
    assert "R$ 20,00" in future_text
