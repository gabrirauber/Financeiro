from datetime import date, timedelta
from types import SimpleNamespace

from test_finance import account, setup, today

from app.finance.cycles import first_cycle, split_cents

pytest_plugins = ["test_finance"]


def test_cycles_and_exact_installments():
    card = SimpleNamespace(closing_day=10, due_day=20, closing_day_next_bill=False)
    assert first_cycle(card, date(2026, 10, 10))[0] == date(2026, 10, 1)
    assert first_cycle(card, date(2026, 10, 11))[0] == date(2026, 11, 1)
    card.closing_day_next_bill = True
    assert first_cycle(card, date(2026, 10, 10))[0] == date(2026, 11, 1)
    card.closing_day = 31
    card.due_day = 5
    card.closing_day_next_bill = False
    assert first_cycle(card, date(2027, 2, 28))[1:] == (date(2027, 2, 28), date(2027, 3, 5))
    assert split_cents(10000, 3) == [3333, 3333, 3334]


def test_card_installments_and_invoice_payment(client):
    headers, space = setup(client)
    bank = account(client, headers, space, "Banco", 50000)
    root = f"/workspaces/{space}"
    category = client.get(f"{root}/categories", headers=headers).json()[0]
    sub = category["subcategories"][0]
    current = date.fromisoformat(today())
    # Fatura já fechada neste mês: pagamento permitido e compras bloqueadas depois.
    closing_day = max(1, current.day - 1)
    card_result = client.post(
        f"{root}/cards",
        headers=headers,
        json={
            "name": "Principal",
            "closing_day": closing_day,
            "due_day": 31,
            "closing_day_next_bill": False,
        },
    )
    assert card_result.status_code == 201, card_result.text
    card = card_result.json()
    purchase_day = current.replace(day=1)
    purchase = client.post(
        f"{root}/card-purchases",
        headers=headers,
        json={
            "card_id": card["id"],
            "category_id": category["id"],
            "subcategory_id": sub["id"],
            "purchased_on": purchase_day.isoformat(),
            "total_cents": 10000,
            "installment_count": 3,
            "note": "Notebook",
        },
    )
    assert purchase.status_code == 201, purchase.text
    installments = purchase.json()["installments"]
    assert [x["amount_cents"] for x in installments] == [3333, 3333, 3334]
    month = current.strftime("%Y-%m")
    listed = client.get(f"{root}/card-installments?month={month}", headers=headers)
    assert listed.status_code == 200, listed.text
    assert listed.json()[0]["amount_cents"] == 3333
    assert client.get(f"{root}/accounts", headers=headers).json()[0]["balance_cents"] == 50000
    invoice_id = installments[0]["invoice_id"]
    paid = client.post(
        f"{root}/invoices/{invoice_id}/pay", headers=headers, json={"account_id": bank}
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["total_cents"] == 3333
    assert paid.json()["status"] == "paid"
    assert client.get(f"{root}/accounts", headers=headers).json()[0]["balance_cents"] == 46667
    statement = client.get(f"{root}/accounts/{bank}/statement", headers=headers).json()
    assert [item["kind"] for item in statement] == ["bill_payment"]
    assert (
        client.post(
            f"{root}/invoices/{invoice_id}/pay", headers=headers, json={"account_id": bank}
        ).status_code
        == 409
    )
    revised = client.patch(
        f"{root}/card-purchases/{purchase.json()['id']}/remaining",
        headers=headers,
        json={
            "remaining_total_cents": 9000,
            "category_id": category["id"],
            "subcategory_id": sub["id"],
            "note": "Alterado",
        },
    )
    assert revised.status_code == 200, revised.text
    assert [item["amount_cents"] for item in revised.json()["installments"]] == [3333, 4500, 4500]
    locked = client.get(f"{root}/invoices/{invoice_id}", headers=headers).json()
    assert locked["total_cents"] == 3333
    blocked = client.post(
        f"{root}/card-purchases",
        headers=headers,
        json={
            "card_id": card["id"],
            "category_id": category["id"],
            "subcategory_id": sub["id"],
            "purchased_on": current.isoformat(),
            "total_cents": 1000,
            "installment_count": 1,
            "legacy": True,
            "first_bill_month": current.replace(day=1).isoformat(),
        },
    )
    assert blocked.status_code == 409, blocked.text


def test_legacy_and_remaining_edit_keep_past(client):
    headers, space = setup(client)
    root = f"/workspaces/{space}"
    category = client.get(f"{root}/categories", headers=headers).json()[0]
    sub = category["subcategories"][0]
    card = client.post(
        f"{root}/cards",
        headers=headers,
        json={
            "name": "Antigo",
            "closing_day": 5,
            "due_day": 15,
            "closing_day_next_bill": True,
        },
    ).json()
    current = date.fromisoformat(today())
    first = current.replace(day=1)
    purchase = client.post(
        f"{root}/card-purchases",
        headers=headers,
        json={
            "card_id": card["id"],
            "category_id": category["id"],
            "subcategory_id": sub["id"],
            "purchased_on": (current - timedelta(days=100)).isoformat(),
            "total_cents": 6000,
            "installment_count": 2,
            "first_sequence": 4,
            "legacy": True,
            "first_bill_month": first.isoformat(),
            "note": "Restante",
        },
    )
    assert purchase.status_code == 201, purchase.text
    assert [x["sequence"] for x in purchase.json()["installments"]] == [4, 5]
    assert [x["amount_cents"] for x in purchase.json()["installments"]] == [3000, 3000]
    assert purchase.json()["installments"][0]["invoice_month"] == first.isoformat()
    updated = client.patch(
        f"{root}/card-purchases/{purchase.json()['id']}/remaining",
        headers=headers,
        json={
            "remaining_total_cents": 5001,
            "category_id": category["id"],
            "subcategory_id": sub["id"],
            "note": "Corrigida",
        },
    )
    assert updated.status_code == 200, updated.text
    assert [x["amount_cents"] for x in updated.json()["installments"]] == [2500, 2501]


def test_edit_card_keeps_existing_invoice_dates(client):
    headers, space = setup(client)
    root = f"/workspaces/{space}"
    category = client.get(f"{root}/categories", headers=headers).json()[0]
    sub = category["subcategories"][0]
    current = date.fromisoformat(today())
    card = client.post(
        f"{root}/cards",
        headers=headers,
        json={
            "name": "Original",
            "closing_day": 1,
            "due_day": 15,
            "closing_day_next_bill": False,
        },
    ).json()
    previous = client.post(
        f"{root}/card-purchases",
        headers=headers,
        json={
            "card_id": card["id"],
            "category_id": category["id"],
            "subcategory_id": sub["id"],
            "purchased_on": current.isoformat(),
            "total_cents": 1200,
            "installment_count": 1,
            "legacy": True,
            "first_bill_month": current.replace(day=1).isoformat(),
        },
    )
    assert previous.status_code == 201, previous.text
    invoice_id = previous.json()["installments"][0]["invoice_id"]
    before = client.get(f"{root}/invoices/{invoice_id}", headers=headers).json()
    edited = client.patch(
        f"{root}/cards/{card['id']}",
        headers=headers,
        json={
            "name": "Atualizado",
            "closing_day": 10,
            "due_day": 25,
            "closing_day_next_bill": True,
        },
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["due_day"] == 25
    after = client.get(f"{root}/invoices/{invoice_id}", headers=headers).json()
    assert (after["closes_on"], after["due_on"]) == (before["closes_on"], before["due_on"])
    assert after["card_name"] == "Atualizado"
