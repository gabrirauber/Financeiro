from datetime import date, timedelta

from test_advances import open_invoice

pytest_plugins = ["test_finance"]


def statement(client, root, bank, headers):
    response = client.get(f"{root}/accounts/{bank}/statement", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_edit_and_undo_advance_recalculates_invoice_and_account(client):
    headers, root, bank, invoice_id, _ = open_invoice(client)
    response = client.post(
        f"{root}/invoices/{invoice_id}/advance",
        headers=headers,
        json={"account_id": bank, "amount_cents": 30000, "request_id": "correction"},
    )
    assert response.status_code == 200, response.text
    movement = statement(client, root, bank, headers)[0]
    changed = client.patch(
        f"{root}/bill-payments/{movement['id']}", headers=headers,
        json={"account_id": bank, "amount_cents": 50000, "occurred_on": movement["occurred_on"]},
    )
    assert changed.status_code == 200, changed.text
    invoice = client.get(f"{root}/invoices/{invoice_id}", headers=headers).json()
    assert invoice["advanced_cents"] == 50000
    assert invoice["remaining_cents"] == 50000
    assert client.get(f"{root}/accounts", headers=headers).json()[0]["balance_cents"] == 150000
    undone = client.delete(f"{root}/bill-payments/{movement['id']}", headers=headers)
    assert undone.status_code == 204, undone.text
    assert statement(client, root, bank, headers) == []
    reopened = client.get(f"{root}/invoices/{invoice_id}", headers=headers).json()
    assert reopened["remaining_cents"] == 100000


def test_undo_full_payment_reopens_invoice(client, monkeypatch):
    headers, root, bank, invoice_id, _ = open_invoice(client)
    import app.finance.cards as cards
    import app.finance.payment_corrections as corrections
    import app.finance.routes as routes

    invoice = client.get(f"{root}/invoices/{invoice_id}", headers=headers).json()
    paid_on = date.fromisoformat(invoice["closes_on"]) + timedelta(days=1)
    monkeypatch.setattr(cards, "today", lambda _workspace: paid_on)
    monkeypatch.setattr(corrections, "today", lambda _workspace: paid_on)
    monkeypatch.setattr(routes, "today", lambda _workspace: paid_on)
    paid = client.post(f"{root}/invoices/{invoice_id}/pay", headers=headers,
                       json={"account_id": bank})
    assert paid.status_code == 200, paid.text
    movement = statement(client, root, bank, headers)[0]
    wrong_amount = client.patch(
        f"{root}/bill-payments/{movement['id']}", headers=headers,
        json={"account_id": bank, "amount_cents": 1, "occurred_on": paid_on.isoformat()},
    )
    assert wrong_amount.status_code == 422
    undone = client.delete(f"{root}/bill-payments/{movement['id']}", headers=headers)
    assert undone.status_code == 204, undone.text
    assert statement(client, root, bank, headers) == []
    reopened = client.get(f"{root}/invoices/{invoice_id}", headers=headers).json()
    assert reopened["paid_on"] is None
    assert reopened["remaining_cents"] == 100000


def test_edit_and_undo_partial_payment_recalculates_future_parts(client):
    from test_financing import prepare_invoice

    headers, root, bank, invoice_id, current = prepare_invoice(client)
    paid = client.post(
        f"{root}/invoices/{invoice_id}/pay-partial", headers=headers,
        json={"account_id": bank, "paid_cents": 60000, "fee_cents": 4000,
              "installment_count": 2},
    )
    assert paid.status_code == 200, paid.text
    movement = statement(client, root, bank, headers)[0]
    changed = client.patch(
        f"{root}/bill-payments/{movement['id']}", headers=headers,
        json={"account_id": bank, "amount_cents": 70000, "occurred_on": current.isoformat()},
    )
    assert changed.status_code == 200, changed.text
    source = client.get(f"{root}/invoices/{invoice_id}", headers=headers).json()
    assert source["financing"]["paid_cents"] == 70000
    assert source["financing"]["principal_cents"] == 30000
    future = client.get(
        f"{root}/invoice-financing-installments", headers=headers,
        params={"month": source["month"][:7]},
    )
    assert future.status_code == 200
    undone = client.delete(f"{root}/bill-payments/{movement['id']}", headers=headers)
    assert undone.status_code == 204, undone.text
    source = client.get(f"{root}/invoices/{invoice_id}", headers=headers).json()
    assert source["financing"] is None
    assert source["paid_on"] is None
    assert statement(client, root, bank, headers) == []
