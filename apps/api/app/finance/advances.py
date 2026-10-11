"""Pagamentos antecipados de faturas ainda abertas."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.finance.card_models import InvoiceAdvance
from app.finance.cards import invoice_or_404, invoice_remaining, serialize_invoice
from app.finance.models import Movement
from app.finance.routes import MAX_CENTS, account_or_404, require_after_opening, today
from app.identity.dependencies import CurrentUser, Db
from app.identity.workspaces import require_member

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["advances"])


class AdvanceInput(BaseModel):
    account_id: UUID
    amount_cents: int = Field(gt=0, le=MAX_CENTS)
    request_id: str = Field(min_length=1, max_length=80)


@router.post("/invoices/{invoice_id}/advance")
def advance_invoice(
    workspace_id: UUID, invoice_id: UUID, data: AdvanceInput, db: Db, user: CurrentUser
):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    invoice, card = invoice_or_404(db, workspace_id, invoice_id)
    existing = db.scalar(
        select(InvoiceAdvance).where(
            InvoiceAdvance.invoice_id == invoice.id,
            InvoiceAdvance.request_id == data.request_id,
        )
    )
    if existing:
        movement = db.get(Movement, existing.movement_id)
        if existing.amount_cents == data.amount_cents and movement.account_id == data.account_id:
            return serialize_invoice(db, invoice, card, today(workspace))
        raise HTTPException(409, "Esta antecipação já foi registrada com outros dados.")
    current = today(workspace)
    if invoice.paid_on:
        raise HTTPException(409, "Esta fatura já foi paga.")
    if current > invoice.closes_on:
        raise HTTPException(422, "A fatura já fechou. Use o pagamento da fatura.")
    remaining = invoice_remaining(db, invoice.id)
    if data.amount_cents > remaining:
        raise HTTPException(422, "A antecipação não pode superar o saldo atual da fatura.")
    account = account_or_404(db, workspace_id, data.account_id)
    if account.kind != "bank":
        raise HTTPException(422, "Pague a fatura por uma conta bancária.")
    require_after_opening(account, current)
    movement = Movement(
        workspace_id=workspace_id,
        account_id=account.id,
        kind="bill_payment",
        amount_cents=data.amount_cents,
        occurred_on=current,
        note=f"Antecipação da fatura {card.name} {invoice.month:%m/%Y}",
        created_at=datetime.now(timezone.utc),
    )
    db.add(movement)
    db.flush()
    db.add(
        InvoiceAdvance(
            invoice_id=invoice.id,
            movement_id=movement.id,
            request_id=data.request_id,
            amount_cents=data.amount_cents,
        )
    )
    db.commit()
    return serialize_invoice(db, invoice, card, current)
