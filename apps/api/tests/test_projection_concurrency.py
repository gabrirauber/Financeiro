"""Real PostgreSQL regression: calculation must not retain workspace write locks."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

from test_e09 import client as client
from test_e09 import setup as setup_finance
from test_finance import account, today

from app.finance import projection


def setup(client):
    headers, root, *_ = setup_finance(client)
    return headers, root.rsplit("/", 1)[1]


def test_projection_releases_lock_and_keeps_a_consistent_snapshot(client, monkeypatch):
    headers, space = setup(client)
    account(client, headers, space, "Saldo original", 10000)
    root = f"/workspaces/{space}"
    calculating = Event()
    finish = Event()
    original = projection.month_values

    def slow_values(*args, **kwargs):
        values = original(*args, **kwargs)
        calculating.set()
        assert finish.wait(15), "Calculation was not released"
        return values

    monkeypatch.setattr(projection, "month_values", slow_values)
    with ThreadPoolExecutor(max_workers=4) as executor:
        pending = executor.submit(
            client.get, f"{root}/projection?month={today()[:7]}", headers=headers
        )
        try:
            assert calculating.wait(10), "Projection did not start calculating"
            requests = [
                executor.submit(client.get, f"{root}/income-reminders", headers=headers),
                executor.submit(
                    client.get, f"{root}/recurring-occurrences?month={today()[:7]}", headers=headers
                ),
                executor.submit(
                    client.post,
                    f"{root}/accounts",
                    headers=headers,
                    json={
                        "name": "Criada durante o cálculo",
                        "kind": "bank",
                        "opening_balance_cents": 20000,
                    },
                ),
            ]
            responses = [request.result(timeout=8) for request in requests]
            assert [response.status_code for response in responses] == [200, 200, 201], [
                response.text for response in responses
            ]
        finally:
            finish.set()
        response = pending.result(timeout=10)
    assert response.status_code == 200, response.text
    # The concurrent write succeeds but is not mixed into the calculation snapshot.
    assert response.json()["cash_balance_cents"] == 10000
    assert (
        sum(row["balance_cents"] for row in client.get(f"{root}/accounts", headers=headers).json())
        == 30000
    )


def test_simultaneous_month_generation_does_not_duplicate_occurrences(client):
    from uuid import UUID

    from sqlalchemy import delete, func, select
    from sqlalchemy.orm import Session

    from app.finance.recurrence_models import IncomeOccurrence, RecurringOccurrence

    headers, space = setup(client)
    root = f"/workspaces/{space}"
    user = client.get("/auth/me", headers=headers).json()["id"]
    category = client.get(f"{root}/categories", headers=headers).json()[0]
    plan = client.post(
        f"{root}/income-plans",
        headers=headers,
        json={
            "description": "Salário",
            "amount_cents": 100000,
            "day_of_month": 1,
            "responsible_user_id": user,
        },
    )
    assert plan.status_code == 201, plan.text
    rule = client.post(
        f"{root}/recurring-rules",
        headers=headers,
        json={
            "kind": "expense",
            "description": "Aluguel",
            "amount_cents": 50000,
            "day_of_month": 1,
            "category_id": category["id"],
            "subcategory_id": category["subcategories"][0]["id"],
            "payment_method": "pix",
        },
    )
    assert rule.status_code == 201, rule.text
    plan_id, rule_id = UUID(plan.json()["id"]), UUID(rule.json()["id"])
    with Session(client.app.state.engine) as db:
        db.execute(delete(IncomeOccurrence).where(IncomeOccurrence.plan_id == plan_id))
        db.execute(delete(RecurringOccurrence).where(RecurringOccurrence.rule_id == rule_id))
        db.commit()
    with ThreadPoolExecutor(max_workers=3) as executor:
        requests = [
            executor.submit(client.get, path, headers=headers)
            for path in [
                f"{root}/projection?month={today()[:7]}",
                f"{root}/income-reminders",
                f"{root}/recurring-occurrences?month={today()[:7]}",
            ]
        ]
        responses = [request.result(timeout=10) for request in requests]
    assert [response.status_code for response in responses] == [200, 200, 200], [
        response.text for response in responses
    ]
    with Session(client.app.state.engine) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(IncomeOccurrence)
                .where(IncomeOccurrence.plan_id == plan_id)
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(RecurringOccurrence)
                .where(RecurringOccurrence.rule_id == rule_id)
            )
            == 1
        )
