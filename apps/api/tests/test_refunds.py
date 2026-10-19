from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session
from test_finance import account, setup, today

from app.finance.card_models import CardPurchase, Invoice
from app.finance.cycles import cycle_for_due_month, shift_month

pytest_plugins = ["test_finance"]


def prepare(client, total=10000, count=1):
    headers, space = setup(client)
    root = f"/workspaces/{space}"
    bank = account(client, headers, space, "Banco", 100000)
    category = client.get(f"{root}/categories", headers=headers).json()[0]
    card = client.post(
        f"{root}/cards",
        headers=headers,
        json={
            "name": "Principal",
            "closing_day": 1,
            "due_day": 28,
        },
    ).json()
    purchase = client.post(
        f"{root}/card-purchases",
        headers=headers,
        json={
            "card_id": card["id"],
            "category_id": category["id"],
            "subcategory_id": category["subcategories"][0]["id"],
            "purchased_on": today()[:8] + "01",
            "total_cents": total,
            "installment_count": count,
            "note": "Compra original",
        },
    )
    assert purchase.status_code == 201, purchase.text
    purchase = purchase.json()
    source = purchase["installments"][0]
    previous = shift_month(date.fromisoformat(today()).replace(day=1), -1)
    # Reproduz uma compra histórica, sem desbloquear lançamentos antigos na API.
    with Session(client.app.state.engine) as db:
        invoice = db.get(Invoice, UUID(source["invoice_id"]))
        invoice.month = previous
        invoice.closes_on = previous
        invoice.due_on = previous.replace(day=28)
        row = db.get(CardPurchase, UUID(purchase["id"]))
        row.purchased_on = previous
        db.commit()
    return headers, root, bank, card, purchase, source


def credit(client, headers, root, source, amount, request="refund-request-1", month=None):
    return client.post(
        f"{root}/card-installments/{source['id']}/refund",
        headers=headers,
        json={
            "amount_cents": amount,
            "credited_on": today(),
            "invoice_month": month or today()[:8] + "01",
            "request_id": request,
            "note": "Estorno confirmado pelo banco",
        },
    )


def test_refund_paid_history_idempotency_and_projection(client):
    headers, root, bank, card, purchase, source = prepare(client)
    paid = client.post(
        f"{root}/invoices/{source['invoice_id']}/pay", headers=headers, json={"account_id": bank}
    )
    assert paid.status_code == 200, paid.text
    before = client.get(f"{root}/invoices/{source['invoice_id']}", headers=headers).json()
    response = credit(client, headers, root, source, 10000)
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["total_cents"] == -10000
    assert result["remaining_cents"] == 0
    assert result["credit_balance_cents"] == 10000
    after = client.get(f"{root}/invoices/{source['invoice_id']}", headers=headers).json()
    assert after["paid_on"] == before["paid_on"]
    assert after["total_cents"] == before["total_cents"] == 10000
    assert after["installments"][0]["refunded_cents"] == 10000
    repeat = credit(client, headers, root, source, 10000)
    assert repeat.status_code == 201
    assert len(repeat.json()["refunds"]) == 1
    assert credit(client, headers, root, source, 1, "another-request").status_code == 422
    assert credit(client, headers, root, source, 9000).status_code == 409
    accounts = client.get(f"{root}/accounts", headers=headers).json()
    assert accounts[0]["balance_cents"] == 90000
    projection = client.get(f"{root}/projection?month={today()[:7]}", headers=headers).json()
    assert projection["received_income_cents"] == 0
    assert projection["card_commitment_cents"] == -10000
    assert projection["projected_balance_cents"] == 90000
    pdf = client.get(f"{root}/reports/monthly.pdf?month={today()[:7]}&detail=true", headers=headers)
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    assert (
        client.delete(f"{root}/card-purchases/{purchase['id']}", headers=headers).status_code == 409
    )


def test_partial_refunds_roll_credit_forward_and_pay_only_net_amount(client, monkeypatch):
    headers, root, bank, card, purchase, source = prepare(client)
    first = credit(client, headers, root, source, 6000)
    assert first.status_code == 201, first.text
    second = credit(client, headers, root, source, 4000, "refund-request-2")
    assert second.status_code == 201, second.text
    assert second.json()["refund_total_cents"] == 10000
    next_month = shift_month(date.fromisoformat(today()).replace(day=1), 1)
    # Fatura futura com compra já existente e data de fechamento passada para testar quitação.
    with Session(client.app.state.engine) as db:
        from app.finance.card_models import CardInstallment, CreditCard

        row = db.get(CreditCard, UUID(card["id"]))
        _, closes, due = cycle_for_due_month(row, next_month)
        future = Invoice(card_id=row.id, month=next_month, closes_on=closes, due_on=due)
        db.add(future)
        db.flush()
        original = db.get(CardInstallment, UUID(source["id"]))
        other = CardPurchase(
            card_id=row.id,
            purchased_on=date.fromisoformat(today()),
            total_cents=15000,
            legacy=False,
            created_at=db.get(CardPurchase, UUID(purchase["id"])).created_at,
        )
        db.add(other)
        db.flush()
        db.add(
            CardInstallment(
                purchase_id=other.id,
                invoice_id=future.id,
                sequence=1,
                total_count=1,
                amount_cents=15000,
                category_id=original.category_id,
                subcategory_id=original.subcategory_id,
                note="Nova compra",
            )
        )
        future_id = str(future.id)
        db.commit()
    invoice = client.get(f"{root}/invoices/{future_id}", headers=headers).json()
    assert invoice["credit_brought_cents"] == 10000
    assert invoice["remaining_cents"] == 5000
    projection = client.get(f"{root}/projection?month={next_month:%Y-%m}", headers=headers).json()
    assert projection["card_pending_cents"] == 5000
    assert projection["card_through_month_cents"] == 5000
    assert projection["projected_balance_cents"] == 85000  # original unpaid + future net
    from app.finance import cards

    with monkeypatch.context() as patcher:
        patcher.setattr(cards, "today", lambda workspace: next_month.replace(day=2))
        with Session(client.app.state.engine) as db:
            db.get(Invoice, UUID(future_id)).closes_on = next_month
            db.commit()
        paid = client.post(
            f"{root}/invoices/{future_id}/pay", headers=headers, json={"account_id": bank}
        )
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "paid"
    assert client.get(f"{root}/accounts", headers=headers).json()[0]["balance_cents"] == 95000


def test_refund_rejects_foreign_workspace_and_invalid_dates(client):
    headers, root, _, _, _, source = prepare(client)
    other_headers, other_space = setup(client, email="other@example.com")
    assert (
        credit(client, other_headers, f"/workspaces/{other_space}", source, 500).status_code == 404
    )
    assert credit(client, headers, root, source, 500, month="2020-01-01").status_code == 422
    assert credit(client, headers, root, source, 10001).status_code == 422
    bad = client.post(
        f"{root}/card-installments/{source['id']}/refund",
        headers=headers,
        json={
            "amount_cents": 100,
            "credited_on": "2020-01-01",
            "invoice_month": today()[:8] + "01",
            "request_id": "invalid-date-request",
        },
    )
    assert bad.status_code == 422


def test_first_refund_cannot_change_credit_before_paid_future(client):
    headers, root, _, card, _, source = prepare(client)
    current = date.fromisoformat(today()).replace(day=1)
    with Session(client.app.state.engine) as db:
        future = Invoice(
            card_id=UUID(card["id"]),
            month=shift_month(current, 1),
            closes_on=current,
            due_on=current,
            paid_on=current,
        )
        db.add(future)
        db.commit()
    result = credit(client, headers, root, source, 5000)
    assert result.status_code == 409, result.text
    original = client.get(f"{root}/invoices/{source['invoice_id']}", headers=headers).json()
    assert original["installments"][0]["refunded_cents"] == 0


def test_refund_rejects_paid_target_and_preserves_other_installments(client):
    headers, root, _, _, purchase, source = prepare(client, total=30000, count=3)
    response = credit(client, headers, root, source, 5000)
    assert response.status_code == 201, response.text
    target = response.json()
    assert target["refund_total_cents"] == 5000
    invoices = client.get(f"{root}/invoices", headers=headers).json()
    parts = [
        part
        for invoice in invoices
        for part in invoice["installments"]
        if part["purchase_id"] == purchase["id"]
    ]
    assert sorted(part["amount_cents"] for part in parts) == [10000, 10000, 10000]
    with Session(client.app.state.engine) as db:
        db.get(Invoice, UUID(target["id"])).paid_on = date.fromisoformat(today())
        db.commit()
    assert credit(client, headers, root, source, 1000, "new-refund-request").status_code == 409
