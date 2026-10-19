"""Resultado por competência e projeção de caixa, sem cobrar pagamentos duas vezes."""

from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.finance.card_models import CreditCard, Invoice, InvoiceFinancing
from app.finance.cards import (
    invoice_advance_total,
    invoice_credit_brought,
    invoice_remaining,
    invoice_total,
)
from app.finance.cycles import day_in_month, first_cycle, shift_month
from app.finance.income_plans import generate_month as generate_income
from app.finance.models import Account, Movement
from app.finance.recurrence_models import (
    IncomeOccurrence,
    IncomePlan,
    IncomeReceipt,
    RecurringOccurrence,
    RecurringRule,
)
from app.finance.recurrences import generate_month as generate_recurring
from app.finance.routes import account_balances, today
from app.identity.dependencies import CurrentUser, Db
from app.identity.workspaces import require_member

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["projection"])


def historical_balance(db, workspace_id, last_day):
    openings = db.scalars(
        select(Account).where(Account.workspace_id == workspace_id, Account.opened_on <= last_day)
    ).all()
    balance = sum(account.opening_balance_cents for account in openings)
    movements = db.scalars(
        select(Movement).where(
            Movement.workspace_id == workspace_id, Movement.occurred_on <= last_day
        )
    ).all()
    for row in movements:
        direction = -1 if row.kind in ("expense", "bill_payment", "transfer_out") else 1
        balance += direction * row.amount_cents
    return balance


def movement_total(db, workspace_id, month, kind):
    return (
        db.scalar(
            select(func.sum(Movement.amount_cents)).where(
                Movement.workspace_id == workspace_id,
                Movement.kind == kind,
                Movement.occurred_on >= month,
                Movement.occurred_on < shift_month(month, 1),
            )
        )
        or 0
    )


def remaining_income(db, workspace_id, month):
    rows = db.execute(
        select(IncomeOccurrence.id, IncomeOccurrence.expected_cents, IncomeOccurrence.completed)
        .join(IncomePlan, IncomePlan.id == IncomeOccurrence.plan_id)
        .where(IncomePlan.workspace_id == workspace_id, IncomeOccurrence.month == month)
    ).all()
    if not rows:
        return 0
    received = dict(
        db.execute(
            select(IncomeReceipt.occurrence_id, func.sum(Movement.amount_cents))
            .join(Movement, Movement.id == IncomeReceipt.movement_id)
            .where(IncomeReceipt.occurrence_id.in_([row.id for row in rows]))
            .group_by(IncomeReceipt.occurrence_id)
        ).all()
    )
    return sum(
        max(0, row.expected_cents - (received.get(row.id) or 0))
        for row in rows
        if not row.completed
    )


def pending_fixed(db, workspace_id, month):
    return (
        db.scalar(
            select(func.sum(RecurringOccurrence.amount_cents))
            .join(RecurringRule, RecurringRule.id == RecurringOccurrence.rule_id)
            .where(
                RecurringRule.workspace_id == workspace_id,
                RecurringRule.kind == "expense",
                RecurringOccurrence.month == month,
                RecurringOccurrence.expense_id.is_(None),
            )
        )
        or 0
    )


def projected_card_recurring(db, workspace_id, month, current, card_id_filter=None):
    """Assinaturas ainda não lançadas contam na fatura futura prevista."""
    total = 0
    rules = db.scalars(
        select(RecurringRule).where(
            RecurringRule.workspace_id == workspace_id,
            RecurringRule.kind == "card",
            RecurringRule.active.is_(True),
        )
    ).all()
    for source_month in (shift_month(month, -1), month):
        for rule in rules:
            if rule.start_month > source_month:
                continue
            occurrence = db.scalar(
                select(RecurringOccurrence).where(
                    RecurringOccurrence.rule_id == rule.id,
                    RecurringOccurrence.month == source_month,
                )
            )
            if occurrence and occurrence.purchase_id:
                continue
            card_id = occurrence.card_id if occurrence else rule.card_id
            card = db.get(CreditCard, card_id) if card_id else None
            if card is None or not card.active or (card_id_filter and card.id != card_id_filter):
                continue
            due = occurrence.due_on if occurrence else day_in_month(source_month, rule.day_of_month)
            bill_month = first_cycle(card, due)[0]
            for _ in range(13):
                invoice = db.scalar(
                    select(Invoice).where(Invoice.card_id == card.id, Invoice.month == bill_month)
                )
                if invoice is None or (invoice.paid_on is None and invoice.closes_on >= current):
                    break
                bill_month = shift_month(bill_month, 1)
            if bill_month == month:
                total += occurrence.amount_cents if occurrence else rule.amount_cents
    return total


def invoice_amounts(db, workspace_id, month):
    invoices = db.scalars(
        select(Invoice)
        .join(CreditCard, CreditCard.id == Invoice.card_id)
        .where(CreditCard.workspace_id == workspace_id, Invoice.month == month)
    ).all()
    commitment = pending = refinanced = 0
    for invoice in invoices:
        total = invoice_total(db, invoice.id)
        financing = db.scalar(
            select(InvoiceFinancing).where(InvoiceFinancing.source_invoice_id == invoice.id)
        )
        transferred = financing.principal_cents if financing else 0
        refinanced += transferred
        commitment += total - transferred
        if invoice.paid_on is None:
            pending += invoice_remaining(db, invoice.id)
    return commitment, pending, refinanced


def overdue_amount(db, workspace_id, before_month):
    fixed = (
        db.scalar(
            select(func.sum(RecurringOccurrence.amount_cents))
            .join(RecurringRule, RecurringRule.id == RecurringOccurrence.rule_id)
            .where(
                RecurringRule.workspace_id == workspace_id,
                RecurringRule.kind == "expense",
                RecurringOccurrence.month < before_month,
                RecurringOccurrence.expense_id.is_(None),
            )
        )
        or 0
    )
    invoices = db.scalars(
        select(Invoice)
        .join(CreditCard, CreditCard.id == Invoice.card_id)
        .where(
            CreditCard.workspace_id == workspace_id,
            Invoice.month < before_month,
            Invoice.paid_on.is_(None),
        )
    ).all()
    card = sum(invoice_remaining(db, invoice.id) for invoice in invoices)
    return fixed + card


def projected_card_pending(db, workspace_id, month, current):
    total = 0
    for card in db.scalars(select(CreditCard).where(CreditCard.workspace_id == workspace_id)):
        step = current.replace(day=1)
        credit = invoice_credit_brought(db, Invoice(card_id=card.id, month=step))
        while step <= month:
            invoice = db.scalar(
                select(Invoice).where(Invoice.card_id == card.id, Invoice.month == step)
            )
            virtual = projected_card_recurring(db, workspace_id, step, current, card.id)
            net = (
                (
                    (invoice_total(db, invoice.id) - invoice_advance_total(db, invoice.id))
                    if invoice
                    else 0
                )
                + virtual
                - credit
            )
            credit = max(0, -net)
            if step == month and (invoice is None or invoice.paid_on is None):
                total += max(0, net)
            step = shift_month(step, 1)
    return total


def month_values(db, workspace_id, month, current, historical):
    received = movement_total(db, workspace_id, month, "income")
    expected = 0 if historical else remaining_income(db, workspace_id, month)
    paid_expenses = movement_total(db, workspace_id, month, "expense")
    fixed = 0 if historical else pending_fixed(db, workspace_id, month)
    card, card_pending, refinanced = invoice_amounts(db, workspace_id, month)
    card_virtual = 0 if historical else projected_card_recurring(db, workspace_id, month, current)
    card += card_virtual
    card_pending = (
        card_pending if historical else projected_card_pending(db, workspace_id, month, current)
    )
    income = received + expected
    committed = paid_expenses + fixed + card
    return {
        "received_income_cents": received,
        "expected_income_cents": expected,
        "income_cents": income,
        "paid_expenses_cents": paid_expenses,
        "pending_fixed_cents": fixed,
        "card_commitment_cents": card,
        "card_pending_cents": card_pending,
        "card_refinanced_cents": refinanced,
        "committed_cents": committed,
        "result_cents": income - committed,
        "commitment_percent": round(committed * 100 / income, 1) if income else None,
    }


def parse_month(month: str):
    try:
        year, number = map(int, month.split("-"))
        return date(year, number, 1)
    except ValueError as exc:
        raise HTTPException(422, "Informe um mês válido.") from exc


def build_projection(db, workspace_id, workspace, target):
    current = today(workspace)
    current_month = current.replace(day=1)
    historical = target < current_month
    if not historical:
        if target.year * 12 + target.month - current.year * 12 - current.month > 60:
            raise HTTPException(422, "Consulte até cinco anos à frente.")
        step = current_month
        while step <= target:
            generate_income(db, workspace_id, step)
            generate_recurring(db, workspace_id, step, current)
            step = shift_month(step, 1)
        db.flush()
    values = month_values(db, workspace_id, target, current, historical)
    if historical:
        last_day = shift_month(target, 1) - timedelta(days=1)
        balance = historical_balance(db, workspace_id, last_day)
        projected = balance
        overdue = 0
        expected_through = fixed_through = card_through = 0
    else:
        balance = sum(item["balance_cents"] for item in account_balances(db, workspace_id))
        projected = balance
        expected_through = fixed_through = card_through = 0
        step = current_month
        while step <= target:
            current_values = (
                values if step == target else month_values(db, workspace_id, step, current, False)
            )
            expected_through += current_values["expected_income_cents"]
            fixed_through += current_values["pending_fixed_cents"]
            card_through += current_values["card_pending_cents"]
            step = shift_month(step, 1)
        overdue = overdue_amount(db, workspace_id, current_month)
        projected += expected_through - fixed_through - card_through - overdue
    db.commit()
    return {
        "month": target,
        "kind": "historical" if historical else "current" if target == current_month else "future",
        **values,
        "cash_balance_cents": balance,
        "expected_through_month_cents": expected_through,
        "fixed_through_month_cents": fixed_through,
        "card_through_month_cents": card_through,
        "overdue_cents": overdue,
        "projected_balance_cents": projected,
    }


@router.get("/projection")
def projection(
    workspace_id: UUID,
    db: Db,
    user: CurrentUser,
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    return build_projection(db, workspace_id, workspace, parse_month(month))
