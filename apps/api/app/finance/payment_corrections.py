"""Correct or undo a card payment from an account statement."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.finance.card_models import FinancingInstallment, Invoice, InvoiceAdvance, InvoiceFinancing
from app.finance.cards import (
    invoice_advance_total,
    invoice_remaining,
    invoice_total,
    protect_credit_history,
)
from app.finance.cycles import split_cents
from app.finance.models import Movement
from app.finance.routes import (
    MAX_CENTS,
    account_or_404,
    require_after_opening,
    require_current_month,
    today,
)
from app.identity.dependencies import CurrentUser, Db
from app.identity.workspaces import require_member

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["payment-corrections"])


class PaymentCorrection(BaseModel):
    account_id: UUID
    amount_cents: int = Field(gt=0, le=MAX_CENTS)
    occurred_on: date


def payment_or_404(db, workspace_id, movement_id):
    movement = db.get(Movement, movement_id)
    if movement is None or movement.workspace_id != workspace_id or movement.kind != "bill_payment":
        raise HTTPException(404, "Pagamento de fatura não encontrado.")
    advance = db.scalar(select(InvoiceAdvance).where(InvoiceAdvance.movement_id == movement_id))
    invoice = db.scalar(select(Invoice).where(Invoice.payment_movement_id == movement_id))
    if not advance and not invoice:
        raise HTTPException(409, "Não foi possível identificar a fatura deste pagamento.")
    return movement, advance, invoice or db.get(Invoice, advance.invoice_id)


def financing_parts(db, invoice):
    financing = db.scalar(
        select(InvoiceFinancing).where(InvoiceFinancing.source_invoice_id == invoice.id)
    )
    parts = (
        db.scalars(
            select(FinancingInstallment)
            .where(FinancingInstallment.financing_id == financing.id)
            .order_by(FinancingInstallment.sequence)
        ).all()
        if financing
        else []
    )
    if any(db.get(Invoice, part.invoice_id).paid_on for part in parts):
        raise HTTPException(409, "Há parcelas futuras já pagas. Desfaça esses pagamentos antes.")
    return financing, parts


@router.patch("/bill-payments/{movement_id}")
def edit_payment(
    workspace_id: UUID,
    movement_id: UUID,
    data: PaymentCorrection,
    db: Db,
    user: CurrentUser,
):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    movement, advance, invoice = payment_or_404(db, workspace_id, movement_id)
    protect_credit_history(db, invoice)
    require_current_month(workspace, movement.occurred_on)
    require_current_month(workspace, data.occurred_on)
    if data.occurred_on > today(workspace):
        raise HTTPException(422, "A data do pagamento não pode estar no futuro.")
    account = account_or_404(db, workspace_id, data.account_id)
    if account.kind != "bank":
        raise HTTPException(422, "Pague a fatura por uma conta bancária.")
    require_after_opening(account, data.occurred_on)
    if advance:
        if invoice.paid_on:
            raise HTTPException(
                409, "Desfaça a quitação da fatura antes de corrigir a antecipação."
            )
        if data.occurred_on > invoice.closes_on:
            raise HTTPException(422, "Antecipações devem ocorrer antes do fechamento.")
        available = invoice_remaining(db, invoice.id) + advance.amount_cents
        previous_available = invoice_total(db, invoice.id) - sum(
            item.amount_cents
            for item in db.scalars(
                select(InvoiceAdvance).where(InvoiceAdvance.invoice_id == invoice.id)
            )
            if item.id != advance.id
        )
        if data.amount_cents > min(available, previous_available):
            raise HTTPException(422, "A antecipação não pode superar o saldo da fatura.")
        advance.amount_cents = data.amount_cents
    else:
        if data.occurred_on <= invoice.closes_on:
            raise HTTPException(422, "O pagamento integral ou parcial exige fatura fechada.")
        financing, parts = financing_parts(db, invoice)
        total = invoice_remaining(db, invoice.id)
        if financing:
            if not 0 < data.amount_cents < total:
                raise HTTPException(422, "O pagamento parcial deve ser menor que a fatura.")
            principal = total - data.amount_cents
            if principal < len(parts) or principal + financing.fee_cents > MAX_CENTS:
                raise HTTPException(422, "O valor restante não pode ser distribuído nas parcelas.")
            principal_parts = split_cents(principal, len(parts))
            for part, part_principal in zip(parts, principal_parts):
                future_total = invoice_total(db, part.invoice_id) - part.amount_cents
                future_total += part_principal + part.fee_cents
                if invoice_advance_total(db, part.invoice_id) > future_total:
                    raise HTTPException(
                        409, "Uma fatura futura já tem antecipações maiores que o novo valor."
                    )
                part.principal_cents = part_principal
                part.amount_cents = part_principal + part.fee_cents
            financing.paid_cents = data.amount_cents
            financing.principal_cents = principal
        elif data.amount_cents != total:
            raise HTTPException(422, "A quitação integral deve corresponder ao saldo da fatura.")
        invoice.paid_on = data.occurred_on
    movement.account_id = account.id
    movement.amount_cents = data.amount_cents
    movement.occurred_on = data.occurred_on
    db.commit()
    return {"id": movement.id, "amount_cents": movement.amount_cents}


@router.delete("/bill-payments/{movement_id}", status_code=204)
def undo_payment(workspace_id: UUID, movement_id: UUID, db: Db, user: CurrentUser):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    movement, advance, invoice = payment_or_404(db, workspace_id, movement_id)
    protect_credit_history(db, invoice)
    require_current_month(workspace, movement.occurred_on)
    if advance:
        if invoice.paid_on:
            raise HTTPException(409, "Desfaça a quitação da fatura antes da antecipação.")
        db.delete(advance)
        db.flush()
    else:
        financing, parts = financing_parts(db, invoice)
        for part in parts:
            if invoice_advance_total(db, part.invoice_id) > (
                invoice_total(db, part.invoice_id) - part.amount_cents
            ):
                raise HTTPException(409, "Desfaça as antecipações das faturas futuras antes.")
            db.delete(part)
        if financing:
            db.delete(financing)
        invoice.payment_movement_id = None
        invoice.paid_on = None
        db.flush()
    db.delete(movement)
    db.commit()
