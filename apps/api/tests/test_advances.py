from datetime import date, timedelta

from test_finance import account, setup, today

pytest_plugins = ["test_finance"]


def open_invoice(client, amount=100000):
    headers, space = setup(client)
    root = f"/workspaces/{space}"
    bank = account(client, headers, space, "Banco", 200000)
    category = client.get(f"{root}/categories", headers=headers).json()[0]
    sub = category["subcategories"][0]
    current = date.fromisoformat(today())
    card = client.post(
        f"{root}/cards",
        headers=headers,
        json={
            "name": "Principal",
            "closing_day": current.day,
            "due_day": 31,
            "closing_day_next_bill": False,
        },
    ).json()
    payload = {
        "card_id": card["id"],
        "category_id": category["id"],
        "subcategory_id": sub["id"],
        "purchased_on": current.isoformat(),
        "total_cents": amount,
        "installment_count": 1,
        "note": "Compra atual",
    }
    purchase = client.post(f"{root}/card-purchases", headers=headers, json=payload)
    assert purchase.status_code == 201, purchase.text
    invoice_id = purchase.json()["installments"][0]["invoice_id"]
    return headers, root, bank, invoice_id, payload


def test_advance_open_invoice_then_pay_only_remainder(client, monkeypatch):
    headers, root, bank, invoice_id, purchase = open_invoice(client)
    url = f"{root}/invoices/{invoice_id}/advance"
    payload = {"account_id": bank, "amount_cents": 60000, "request_id": "advance-1"}
    first = client.post(url, headers=headers, json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "open"
    assert first.json()["advanced_cents"] == 60000
    assert first.json()["remaining_cents"] == 40000
    assert client.post(url, headers=headers, json=payload).status_code == 200
    assert (
        client.post(url, headers=headers, json={**payload, "amount_cents": 50000}).status_code
        == 409
    )
    category = client.get(f"{root}/categories", headers=headers).json()[0]
    sub = category["subcategories"][0]
    original_purchase_id = first.json()["installments"][0]["purchase_id"]
    correction = client.patch(
        f"{root}/card-purchases/{original_purchase_id}/remaining",
        headers=headers,
        json={
            "remaining_total_cents": 50000,
            "category_id": category["id"],
            "subcategory_id": sub["id"],
            "note": "Valor menor que a antecipação",
        },
    )
    assert correction.status_code == 422
    extra = client.post(
        f"{root}/card-purchases", headers=headers, json={**purchase, "total_cents": 10000}
    )
    assert extra.status_code == 201, extra.text
    current = client.get(f"{root}/invoices/{invoice_id}", headers=headers).json()
    assert current["total_cents"] == 110000
    assert current["remaining_cents"] == 50000
    assert client.get(f"{root}/accounts", headers=headers).json()[0]["balance_cents"] == 140000

    import app.finance.cards as cards

    after_close = date.fromisoformat(current["closes_on"]) + timedelta(days=1)
    monkeypatch.setattr(cards, "today", lambda _workspace: after_close)
    paid = client.post(
        f"{root}/invoices/{invoice_id}/pay", headers=headers, json={"account_id": bank}
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["remaining_cents"] == 0
    assert paid.json()["status"] == "paid"
    assert client.get(f"{root}/accounts", headers=headers).json()[0]["balance_cents"] == 90000
    statement = client.get(f"{root}/accounts/{bank}/statement", headers=headers).json()
    assert sorted(item["amount_cents"] for item in statement) == [50000, 60000]


def test_full_advance_keeps_invoice_open_until_closing(client, monkeypatch):
    headers, root, bank, invoice_id, purchase = open_invoice(client)
    url = f"{root}/invoices/{invoice_id}/advance"
    response = client.post(
        url,
        headers=headers,
        json={"account_id": bank, "amount_cents": 100000, "request_id": "whole"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "open"
    assert response.json()["remaining_cents"] == 0
    extra = client.post(
        f"{root}/card-purchases", headers=headers, json={**purchase, "total_cents": 1000}
    )
    assert extra.status_code == 201, extra.text
    invoice = client.get(f"{root}/invoices/{invoice_id}", headers=headers).json()
    assert invoice["remaining_cents"] == 1000
    assert (
        client.post(
            url,
            headers=headers,
            json={"account_id": bank, "amount_cents": 1001, "request_id": "too-much"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            url,
            headers=headers,
            json={"account_id": bank, "amount_cents": 1000, "request_id": "last"},
        ).status_code
        == 200
    )

    import app.finance.cards as cards

    after_close = date.fromisoformat(invoice["closes_on"]) + timedelta(days=1)
    monkeypatch.setattr(cards, "today", lambda _workspace: after_close)
    settled = client.get(f"{root}/invoices/{invoice_id}", headers=headers).json()
    assert settled["status"] == "settled"
    assert settled["remaining_cents"] == 0
    assert all(item["invoice_paid"] for item in settled["installments"])
    blocked = client.post(
        f"{root}/card-purchases",
        headers=headers,
        json={**purchase, "legacy": True, "first_bill_month": settled["month"]},
    )
    assert blocked.status_code == 409
    assert client.get(f"{root}/accounts", headers=headers).json()[0]["balance_cents"] == 99000


def test_financing_after_advance_uses_only_unpaid_balance(client, monkeypatch):
    headers, root, bank, invoice_id, _ = open_invoice(client)
    advance = client.post(
        f"{root}/invoices/{invoice_id}/advance",
        headers=headers,
        json={"account_id": bank, "amount_cents": 20000, "request_id": "first"},
    )
    assert advance.status_code == 200, advance.text

    import app.finance.financing as financing

    after_close = date.fromisoformat(advance.json()["closes_on"]) + timedelta(days=1)
    monkeypatch.setattr(financing, "today", lambda _workspace: after_close)
    response = client.post(
        f"{root}/invoices/{invoice_id}/pay-partial",
        headers=headers,
        json={
            "account_id": bank,
            "paid_cents": 30000,
            "fee_cents": 1000,
            "installment_count": 2,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["financing"]["principal_cents"] == 50000
    assert response.json()["advanced_cents"] == 20000
    assert response.json()["remaining_cents"] == 0
    future = [
        item
        for item in client.get(f"{root}/invoices", headers=headers).json()
        if item["id"] != invoice_id
    ]
    assert sorted(item["total_cents"] for item in future) == [25500, 25500]
    assert client.get(f"{root}/accounts", headers=headers).json()[0]["balance_cents"] == 150000
