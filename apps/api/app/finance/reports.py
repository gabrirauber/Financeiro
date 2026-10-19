"""Dados do relatório mensal, reunidos sob as mesmas regras do painel."""

from collections import defaultdict
from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query, Response
from sqlalchemy import select

from app.finance.card_models import (
    CardInstallment,
    CardPurchase,
    CardRefund,
    CreditCard,
    FinancingInstallment,
    Invoice,
    InvoiceFinancing,
)
from app.finance.cards import (
    invoice_advance_total,
    invoice_credit_brought,
    invoice_refund_total,
    invoice_remaining,
    invoice_total,
)
from app.finance.cycles import shift_month
from app.finance.income_plans import received_total
from app.finance.models import Account, Category, Expense, Movement, Subcategory
from app.finance.projection import build_projection, parse_month
from app.finance.recurrence_models import (
    IncomeOccurrence,
    IncomePlan,
    RecurringOccurrence,
    RecurringRule,
)
from app.finance.routes import account_balances
from app.identity.dependencies import CurrentUser, Db
from app.identity.workspaces import require_member

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["reports"])


def report_accounts(db, workspace_id, month, historical):
    if not historical:
        return account_balances(db, workspace_id)
    last_day = shift_month(month, 1) - timedelta(days=1)
    accounts = db.scalars(
        select(Account)
        .where(Account.workspace_id == workspace_id, Account.opened_on <= last_day)
        .order_by(Account.name)
    ).all()
    result = []
    for account in accounts:
        balance = account.opening_balance_cents
        movements = db.scalars(
            select(Movement).where(
                Movement.account_id == account.id, Movement.occurred_on <= last_day
            )
        ).all()
        for movement in movements:
            balance += (
                -1 if movement.kind in ("expense", "bill_payment", "transfer_out") else 1
            ) * movement.amount_cents
        result.append({"name": account.name, "kind": account.kind, "balance_cents": balance})
    return result


def report_data(db, workspace_id, workspace, month):
    summary = build_projection(db, workspace_id, workspace, month)
    historical = summary["kind"] == "historical"
    next_month = shift_month(month, 1)
    categories = defaultdict(int)
    details = []
    fixed = []
    invoices = []
    financings = []
    incomes = []

    for expense, movement, category, subcategory in db.execute(
        select(Expense, Movement, Category, Subcategory)
        .join(Movement, Movement.id == Expense.movement_id)
        .join(Category, Category.id == Expense.category_id)
        .join(Subcategory, Subcategory.id == Expense.subcategory_id)
        .where(
            Expense.workspace_id == workspace_id,
            Movement.occurred_on >= month,
            Movement.occurred_on < next_month,
        )
        .order_by(Movement.occurred_on, Movement.id)
    ):
        categories[category.name] += movement.amount_cents
        details.append(
            {
                "date": movement.occurred_on,
                "label": movement.note or subcategory.name,
                "category": category.name,
                "amount_cents": movement.amount_cents,
                "kind": "Despesa paga",
            }
        )

    for installment, purchase, invoice, card, category, subcategory in db.execute(
        select(CardInstallment, CardPurchase, Invoice, CreditCard, Category, Subcategory)
        .join(CardPurchase, CardPurchase.id == CardInstallment.purchase_id)
        .join(Invoice, Invoice.id == CardInstallment.invoice_id)
        .join(CreditCard, CreditCard.id == Invoice.card_id)
        .join(Category, Category.id == CardInstallment.category_id)
        .join(Subcategory, Subcategory.id == CardInstallment.subcategory_id)
        .where(CreditCard.workspace_id == workspace_id, Invoice.month == month)
        .order_by(CreditCard.name, CardPurchase.purchased_on, CardInstallment.sequence)
    ):
        categories[category.name] += installment.amount_cents
        label = installment.note or subcategory.name
        details.append(
            {
                "date": purchase.purchased_on,
                "label": (
                    f"{label} ({installment.sequence}/{installment.total_count}) - {card.name}"
                ),
                "category": category.name,
                "amount_cents": installment.amount_cents,
                "kind": "Compra no cartão",
            }
        )

    for refund, invoice, card in db.execute(
        select(CardRefund, Invoice, CreditCard)
        .join(Invoice, Invoice.id == CardRefund.invoice_id)
        .join(CreditCard, CreditCard.id == Invoice.card_id)
        .where(CreditCard.workspace_id == workspace_id, Invoice.month == month)
    ):
        details.append(
            {
                "date": refund.credited_on,
                "label": f"Estorno - {card.name}: {refund.note}",
                "category": "Crédito na fatura",
                "amount_cents": -refund.amount_cents,
                "kind": "Estorno no cartão",
            }
        )

    for occurrence, rule, category in db.execute(
        select(RecurringOccurrence, RecurringRule, Category)
        .join(RecurringRule, RecurringRule.id == RecurringOccurrence.rule_id)
        .join(Category, Category.id == RecurringOccurrence.category_id)
        .where(
            RecurringRule.workspace_id == workspace_id,
            RecurringRule.kind == "expense",
            RecurringOccurrence.month == month,
        )
        .order_by(RecurringOccurrence.due_on)
    ):
        if occurrence.expense_id:
            expense = db.get(Expense, occurrence.expense_id)
            movement = db.get(Movement, expense.movement_id) if expense else None
            if movement:
                fixed.append(
                    {
                        "description": occurrence.description,
                        "amount_cents": movement.amount_cents,
                        "status": "Paga",
                    }
                )
        elif not historical:
            categories[category.name] += occurrence.amount_cents
            fixed.append(
                {
                    "description": occurrence.description,
                    "amount_cents": occurrence.amount_cents,
                    "status": "Pendente",
                }
            )
            details.append(
                {
                    "date": occurrence.due_on,
                    "label": occurrence.description,
                    "category": category.name,
                    "amount_cents": occurrence.amount_cents,
                    "kind": "Fixa pendente",
                }
            )

    for invoice, card in db.execute(
        select(Invoice, CreditCard)
        .join(CreditCard, CreditCard.id == Invoice.card_id)
        .where(CreditCard.workspace_id == workspace_id, Invoice.month == month)
        .order_by(CreditCard.name)
    ):
        financing = db.scalar(
            select(InvoiceFinancing).where(InvoiceFinancing.source_invoice_id == invoice.id)
        )
        total = invoice_total(db, invoice.id)
        advanced = invoice_advance_total(db, invoice.id)
        invoices.append(
            {
                "name": card.name,
                "due_on": invoice.due_on,
                "total_cents": total,
                "refund_cents": invoice_refund_total(db, invoice.id),
                "credit_brought_cents": invoice_credit_brought(db, invoice),
                "credit_balance_cents": max(
                    0, -total + advanced + invoice_credit_brought(db, invoice)
                ),
                "advanced_cents": advanced,
                "refinanced_cents": financing.principal_cents if financing else 0,
                "remaining_cents": 0 if invoice.paid_on else invoice_remaining(db, invoice.id),
                "status": "Paga" if invoice.paid_on else "Pendente",
            }
        )

    for installment, financing, invoice, card in db.execute(
        select(FinancingInstallment, InvoiceFinancing, Invoice, CreditCard)
        .join(InvoiceFinancing, InvoiceFinancing.id == FinancingInstallment.financing_id)
        .join(Invoice, Invoice.id == FinancingInstallment.invoice_id)
        .join(CreditCard, CreditCard.id == Invoice.card_id)
        .where(CreditCard.workspace_id == workspace_id, Invoice.month == month)
        .order_by(CreditCard.name, FinancingInstallment.sequence)
    ):
        financings.append(
            {
                "card_name": card.name,
                "sequence": installment.sequence,
                "total_count": financing.installment_count,
                "principal_cents": installment.principal_cents,
                "fee_cents": installment.fee_cents,
                "amount_cents": installment.amount_cents,
            }
        )

    for occurrence, plan in db.execute(
        select(IncomeOccurrence, IncomePlan)
        .join(IncomePlan, IncomePlan.id == IncomeOccurrence.plan_id)
        .where(IncomePlan.workspace_id == workspace_id, IncomeOccurrence.month == month)
        .order_by(IncomeOccurrence.due_on, IncomeOccurrence.description)
    ):
        incomes.append(
            {
                "description": occurrence.description,
                "due_on": occurrence.due_on,
                "expected_cents": occurrence.expected_cents,
                "received_cents": received_total(db, occurrence.id),
                "completed": occurrence.completed,
            }
        )

    return {
        "workspace_name": workspace.name,
        "generated_at": datetime.now(ZoneInfo(workspace.timezone)),
        "summary": summary,
        "categories": sorted(categories.items(), key=lambda row: (-row[1], row[0])),
        "details": sorted(details, key=lambda row: (row["date"], row["label"])),
        "fixed": fixed,
        "invoices": invoices,
        "financings": financings,
        "incomes": incomes,
        "accounts": report_accounts(db, workspace_id, month, historical),
    }


@router.get("/reports/monthly.pdf")
def monthly_pdf(
    workspace_id: UUID,
    db: Db,
    user: CurrentUser,
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    detail: bool = False,
):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    data = report_data(db, workspace_id, workspace, parse_month(month))
    from app.finance.report_pdf import render_monthly_pdf

    pdf = render_monthly_pdf(data, detail=detail)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="financeiro-{month}.pdf"',
            "Cache-Control": "no-store",
        },
    )
