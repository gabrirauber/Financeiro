from datetime import date, timedelta

from test_finance import account, setup, today

pytest_plugins = ["test_finance"]


def prepare_invoice(client, amount=100000):
    headers, space = setup(client)
    root = f"/workspaces/{space}"
    bank = account(client, headers, space, "Banco", 150000)
    category = client.get(f"{root}/categories", headers=headers).json()[0]
    sub = category["subcategories"][0]
    current = date.fromisoformat(today())
    card = client.post(
        f"{root}/cards",
        headers=headers,
        json={
            "name": "Principal",
            "closing_day": max(1, current.day - 1),
            "due_day": 31,
            "closing_day_next_bill": False,
        },
    ).json()
    result = client.post(
        f"{root}/card-purchases",
        headers=headers,
        json={
            "card_id": card["id"],
            "category_id": category["id"],
            "subcategory_id": sub["id"],
            "purchased_on": current.isoformat(),
            "total_cents": amount,
            "installment_count": 1,
            "legacy": True,
            "first_bill_month": current.replace(day=1).isoformat(),
            "note": "Compra original",
        },
    )
    assert result.status_code == 201, result.text
    invoice_id = result.json()["installments"][0]["invoice_id"]
    return headers, root, bank, invoice_id, current


def test_partial_payment_finances_exactly_and_retries_safely(client, monkeypatch):
    headers, root, bank, invoice_id, current = prepare_invoice(client)
    payload = {
        "account_id": bank,
        "paid_cents": 60000,
        "fee_cents": 4000,
        "installment_count": 2,
    }
    url = f"{root}/invoices/{invoice_id}/pay-partial"
    response = client.post(url, headers=headers, json=payload)
    assert response.status_code == 200, response.text
    source = response.json()
    assert source["status"] == "refinanced"
    assert source["total_cents"] == 100000
    assert source["purchase_total_cents"] == 100000
    assert source["financing"] == {
        "id": source["financing"]["id"],
        "paid_cents": 60000,
        "principal_cents": 40000,
        "fee_cents": 4000,
        "installment_count": 2,
    }
    assert client.post(url, headers=headers, json=payload).status_code == 200
    changed = {**payload, "fee_cents": 5000}
    assert client.post(url, headers=headers, json=changed).status_code == 409
    assert (
        client.post(
            f"{root}/invoices/{invoice_id}/pay", headers=headers, json={"account_id": bank}
        ).status_code
        == 409
    )
    accounts = client.get(f"{root}/accounts", headers=headers).json()
    assert accounts[0]["balance_cents"] == 90000
    statement = client.get(f"{root}/accounts/{bank}/statement", headers=headers).json()
    assert len(statement) == 1
    assert statement[0]["amount_cents"] == 60000

    invoices = client.get(f"{root}/invoices", headers=headers).json()
    future = sorted(
        [item for item in invoices if item["id"] != invoice_id], key=lambda item: item["month"]
    )
    assert len(future) == 2
    assert [item["total_cents"] for item in future] == [22000, 22000]
    assert [item["financing_installments"][0]["principal_cents"] for item in future] == [
        20000,
        20000,
    ]
    assert [item["financing_installments"][0]["fee_cents"] for item in future] == [2000, 2000]
    first_month = future[0]["month"][:7]
    financing_rows = client.get(
        f"{root}/invoice-financing-installments?month={first_month}", headers=headers
    ).json()
    assert len(financing_rows) == 1
    assert financing_rows[0]["amount_cents"] == 22000
    original_rows = client.get(
        f"{root}/card-installments?month={current:%Y-%m}", headers=headers
    ).json()
    assert len(original_rows) == 1
    assert original_rows[0]["amount_cents"] == 100000

    import app.finance.cards as cards

    after_closing = date.fromisoformat(future[0]["closes_on"]) + timedelta(days=1)
    monkeypatch.setattr(cards, "today", lambda _workspace: after_closing)
    paid_future = client.post(
        f"{root}/invoices/{future[0]['id']}/pay",
        headers=headers,
        json={"account_id": bank},
    )
    assert paid_future.status_code == 200, paid_future.text
    assert paid_future.json()["total_cents"] == 22000
    assert client.get(f"{root}/accounts", headers=headers).json()[0]["balance_cents"] == 68000


def test_invalid_partial_payment_does_not_touch_cash(client):
    headers, root, bank, invoice_id, _ = prepare_invoice(client)
    url = f"{root}/invoices/{invoice_id}/pay-partial"
    invalid = client.post(
        url,
        headers=headers,
        json={
            "account_id": bank,
            "paid_cents": 100000,
            "fee_cents": 4000,
            "installment_count": 2,
        },
    )
    assert invalid.status_code == 422
    assert client.get(f"{root}/accounts", headers=headers).json()[0]["balance_cents"] == 150000
    assert client.get(f"{root}/invoices/{invoice_id}", headers=headers).json()["status"] == "closed"
    assert client.get(f"{root}/invoices", headers=headers).json().__len__() == 1


def test_partial_payment_rolls_back_if_future_invoice_was_paid(client, monkeypatch):
    headers, root, bank, invoice_id, current = prepare_invoice(client)
    category = client.get(f"{root}/categories", headers=headers).json()[0]
    sub = category["subcategories"][0]
    card_id = client.get(f"{root}/invoices/{invoice_id}", headers=headers).json()["card_id"]
    next_month = date(
        current.year + (current.month == 12),
        current.month % 12 + 1,
        1,
    )
    purchase = client.post(
        f"{root}/card-purchases",
        headers=headers,
        json={
            "card_id": card_id,
            "category_id": category["id"],
            "subcategory_id": sub["id"],
            "purchased_on": current.isoformat(),
            "total_cents": 1000,
            "installment_count": 1,
            "legacy": True,
            "first_bill_month": next_month.isoformat(),
        },
    )
    assert purchase.status_code == 201, purchase.text
    future_id = purchase.json()["installments"][0]["invoice_id"]
    import app.finance.cards as cards

    after_close = date.fromisoformat(
        client.get(f"{root}/invoices/{future_id}", headers=headers).json()["closes_on"]
    ) + timedelta(days=1)
    original_today = cards.today
    monkeypatch.setattr(cards, "today", lambda _workspace: after_close)
    paid = client.post(
        f"{root}/invoices/{future_id}/pay", headers=headers, json={"account_id": bank}
    )
    assert paid.status_code == 200, paid.text
    monkeypatch.setattr(cards, "today", original_today)
    before_balance = client.get(f"{root}/accounts", headers=headers).json()[0]["balance_cents"]
    before_statement = client.get(f"{root}/accounts/{bank}/statement", headers=headers).json()
    rejected = client.post(
        f"{root}/invoices/{invoice_id}/pay-partial",
        headers=headers,
        json={
            "account_id": bank,
            "paid_cents": 60000,
            "fee_cents": 4000,
            "installment_count": 2,
        },
    )
    assert rejected.status_code == 409, rejected.text
    assert (
        client.get(f"{root}/accounts", headers=headers).json()[0]["balance_cents"] == before_balance
    )
    assert (
        client.get(f"{root}/accounts/{bank}/statement", headers=headers).json() == before_statement
    )
    source = client.get(f"{root}/invoices/{invoice_id}", headers=headers).json()
    assert source["status"] == "closed"
    assert source["financing"] is None
