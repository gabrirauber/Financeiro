"""Pagamento parcial com refinanciamento atômico da fatura."""

from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.finance.card_models import (
    CreditCard,
    FinancingInstallment,
    Invoice,
    InvoiceFinancing,
)
from app.finance.cards import (
    ensure_invoice,
    invoice_or_404,
    invoice_remaining,
    serialize_financing_installment,
    serialize_invoice,
)
from app.finance.cycles import shift_month, split_cents
from app.finance.models import Movement
from app.finance.routes import MAX_CENTS, account_or_404, require_after_opening, today
from app.identity.dependencies import CurrentUser, Db
from app.identity.workspaces import require_member

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["financing"])


class PartialPaymentInput(BaseModel):
    account_id: UUID
    paid_cents: int = Field(gt=0, le=MAX_CENTS)
    fee_cents: int = Field(ge=0, le=MAX_CENTS)
    installment_count: int = Field(ge=1, le=120)


def distribute_nonnegative(amount: int, count: int) -> list[int]:
    each, rest = divmod(amount, count)
    return [each] * (count - 1) + [each + rest]


@router.post("/invoices/{invoice_id}/pay-partial")
def pay_partial(
    workspace_id: UUID,
    invoice_id: UUID,
    data: PartialPaymentInput,
    db: Db,
    user: CurrentUser,
):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    invoice, card = invoice_or_404(db, workspace_id, invoice_id)
    existing = db.scalar(
        select(InvoiceFinancing).where(InvoiceFinancing.source_invoice_id == invoice.id)
    )
    if existing:
        movement = db.get(Movement, invoice.payment_movement_id)
        if (
            movement.account_id == data.account_id
            and existing.paid_cents == data.paid_cents
            and existing.fee_cents == data.fee_cents
            and existing.installment_count == data.installment_count
        ):
            return serialize_invoice(db, invoice, card, today(workspace))
        raise HTTPException(409, "Esta fatura já teve um pagamento parcial diferente.")
    current = today(workspace)
    if invoice.paid_on:
        raise HTTPException(409, "Esta fatura já foi paga.")
    if current <= invoice.closes_on:
        raise HTTPException(422, "A fatura ainda está aberta. Aguarde o fechamento.")
    total = invoice_remaining(db, invoice.id)
    if not 0 < data.paid_cents < total:
        raise HTTPException(422, "O pagamento parcial deve ser menor que o total da fatura.")
    principal = total - data.paid_cents
    if principal < data.installment_count:
        raise HTTPException(422, "O restante precisa cobrir ao menos um centavo por parcela.")
    if principal + data.fee_cents > MAX_CENTS:
        raise HTTPException(422, "O total financiado excede o valor permitido.")
    account = account_or_404(db, workspace_id, data.account_id)
    if account.kind != "bank":
        raise HTTPException(422, "Pague a fatura por uma conta bancária.")
    require_after_opening(account, current)
    first_month = shift_month(max(invoice.month, current.replace(day=1)), 1)
    try:
        months = [shift_month(first_month, index) for index in range(data.installment_count)]
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    movement = Movement(
        workspace_id=workspace_id,
        account_id=account.id,
        kind="bill_payment",
        amount_cents=data.paid_cents,
        occurred_on=current,
        note=f"Pagamento parcial da fatura {card.name} {invoice.month:%m/%Y}",
        created_at=datetime.now(timezone.utc),
    )
    db.add(movement)
    db.flush()
    financing = InvoiceFinancing(
        source_invoice_id=invoice.id,
        paid_cents=data.paid_cents,
        principal_cents=principal,
        fee_cents=data.fee_cents,
        installment_count=data.installment_count,
        created_at=datetime.now(timezone.utc),
    )
    db.add(financing)
    db.flush()
    principal_parts = split_cents(principal, data.installment_count)
    fee_parts = distribute_nonnegative(data.fee_cents, data.installment_count)
    for index, month in enumerate(months):
        future = ensure_invoice(db, card, month, current)
        db.add(
            FinancingInstallment(
                financing_id=financing.id,
                invoice_id=future.id,
                sequence=index + 1,
                principal_cents=principal_parts[index],
                fee_cents=fee_parts[index],
                amount_cents=principal_parts[index] + fee_parts[index],
            )
        )
    invoice.payment_movement_id = movement.id
    invoice.paid_on = current
    db.commit()
    return serialize_invoice(db, invoice, card, current)


@router.get("/invoice-financing-installments")
def list_financed_month(
    workspace_id: UUID,
    db: Db,
    user: CurrentUser,
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
):
    require_member(db, workspace_id, user.id)
    year, number = map(int, month.split("-"))
    if year < 1:
        raise HTTPException(422, "Mês inválido.")
    target = date(year, number, 1)
    rows = db.execute(
        select(FinancingInstallment, InvoiceFinancing, Invoice, CreditCard)
        .join(InvoiceFinancing, FinancingInstallment.financing_id == InvoiceFinancing.id)
        .join(Invoice, FinancingInstallment.invoice_id == Invoice.id)
        .join(CreditCard, Invoice.card_id == CreditCard.id)
        .where(CreditCard.workspace_id == workspace_id, Invoice.month == target)
        .order_by(CreditCard.name, FinancingInstallment.id)
    ).all()
    return [
        serialize_financing_installment(item, financing, invoice, card)
        for item, financing, invoice, card in rows
    ]
