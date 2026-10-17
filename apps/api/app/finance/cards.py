from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select

from app.finance.card_models import (
    CardInstallment,
    CardPurchase,
    CreditCard,
    FinancingInstallment,
    Invoice,
    InvoiceAdvance,
    InvoiceFinancing,
)
from app.finance.categories import category_or_404, subcategory_or_404
from app.finance.cycles import cycle_for_due_month, first_cycle, shift_month, split_cents
from app.finance.models import Movement
from app.finance.recurrence_models import RecurringOccurrence
from app.finance.routes import MAX_CENTS, account_or_404, require_after_opening, today
from app.identity.dependencies import CurrentUser, Db
from app.identity.workspaces import require_member

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["cards"])


class CardInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    closing_day: int = Field(ge=1, le=31)
    due_day: int = Field(ge=1, le=31)
    closing_day_next_bill: bool = False

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = " ".join(value.split())
        if not value:
            raise ValueError("Informe o nome do cartão.")
        return value


class PurchaseInput(BaseModel):
    card_id: UUID
    category_id: UUID
    subcategory_id: UUID
    purchased_on: date
    total_cents: int = Field(gt=0, le=MAX_CENTS)
    installment_count: int = Field(ge=1, le=120)
    note: str = Field(default="", max_length=200)
    legacy: bool = False
    first_bill_month: date | None = None
    first_sequence: int = Field(default=1, ge=1, le=120)


class RemainingInput(BaseModel):
    remaining_total_cents: int | None = Field(default=None, gt=0, le=MAX_CENTS)
    installment_amount_cents: int | None = Field(default=None, gt=0, le=MAX_CENTS)
    remaining_installment_count: int | None = Field(default=None, ge=1, le=120)
    category_id: UUID
    subcategory_id: UUID
    note: str = Field(default="", max_length=200)


class PayInvoiceInput(BaseModel):
    account_id: UUID


def card_or_404(db, workspace_id, card_id):
    card = db.get(CreditCard, card_id)
    if card is None or card.workspace_id != workspace_id:
        raise HTTPException(404, "Cartão não encontrado.")
    return card


def invoice_or_404(db, workspace_id, invoice_id):
    row = db.get(Invoice, invoice_id)
    if row is None:
        raise HTTPException(404, "Fatura não encontrada.")
    card = card_or_404(db, workspace_id, row.card_id)
    return row, card


def serialize_card(row):
    return {
        "id": row.id,
        "name": row.name,
        "closing_day": row.closing_day,
        "due_day": row.due_day,
        "closing_day_next_bill": row.closing_day_next_bill,
        "active": row.active,
    }


def installment_rows(db, invoice_id):
    return db.execute(
        select(CardInstallment, CardPurchase)
        .join(CardPurchase, CardPurchase.id == CardInstallment.purchase_id)
        .where(CardInstallment.invoice_id == invoice_id)
        .order_by(CardInstallment.id)
    ).all()


def serialize_installment(row, purchase, invoice, card, settled=False):
    return {
        "id": row.id,
        "purchase_id": purchase.id,
        "card_id": card.id,
        "card_name": card.name,
        "invoice_id": invoice.id,
        "invoice_month": invoice.month,
        "invoice_paid": invoice.paid_on is not None or settled,
        "purchased_on": purchase.purchased_on,
        "created_at": purchase.created_at,
        "legacy": purchase.legacy,
        "sequence": row.sequence,
        "total_count": row.total_count,
        "amount_cents": row.amount_cents,
        "category_id": row.category_id,
        "subcategory_id": row.subcategory_id,
        "note": row.note,
    }


def financing_installment_rows(db, invoice_id):
    return db.execute(
        select(FinancingInstallment, InvoiceFinancing)
        .join(InvoiceFinancing, FinancingInstallment.financing_id == InvoiceFinancing.id)
        .where(FinancingInstallment.invoice_id == invoice_id)
        .order_by(FinancingInstallment.id)
    ).all()


def invoice_total(db, invoice_id):
    purchases = (
        db.scalar(
            select(func.sum(CardInstallment.amount_cents)).where(
                CardInstallment.invoice_id == invoice_id
            )
        )
        or 0
    )
    financed = (
        db.scalar(
            select(func.sum(FinancingInstallment.amount_cents)).where(
                FinancingInstallment.invoice_id == invoice_id
            )
        )
        or 0
    )
    return purchases + financed


def invoice_advance_total(db, invoice_id):
    return (
        db.scalar(
            select(func.sum(InvoiceAdvance.amount_cents)).where(
                InvoiceAdvance.invoice_id == invoice_id
            )
        )
        or 0
    )


def invoice_remaining(db, invoice_id):
    return invoice_total(db, invoice_id) - invoice_advance_total(db, invoice_id)


def invoice_settled(db, invoice, current):
    return invoice.paid_on is not None or (
        current > invoice.closes_on and invoice_remaining(db, invoice.id) == 0
    )


def serialize_financing_installment(row, financing, invoice, card, settled=False):
    return {
        "id": row.id,
        "financing_id": financing.id,
        "source_invoice_id": financing.source_invoice_id,
        "invoice_id": invoice.id,
        "invoice_month": invoice.month,
        "invoice_paid": invoice.paid_on is not None or settled,
        "card_id": card.id,
        "card_name": card.name,
        "sequence": row.sequence,
        "total_count": financing.installment_count,
        "principal_cents": row.principal_cents,
        "fee_cents": row.fee_cents,
        "amount_cents": row.amount_cents,
    }


def serialize_invoice(db, invoice, card, current):
    installments = installment_rows(db, invoice.id)
    financed_rows = financing_installment_rows(db, invoice.id)
    financing = db.scalar(
        select(InvoiceFinancing).where(InvoiceFinancing.source_invoice_id == invoice.id)
    )
    advances = db.scalars(
        select(InvoiceAdvance)
        .where(InvoiceAdvance.invoice_id == invoice.id)
        .order_by(InvoiceAdvance.id)
    ).all()
    advance_total = sum(item.amount_cents for item in advances)
    total = invoice_total(db, invoice.id)
    remaining = total - advance_total
    settled = current > invoice.closes_on and remaining == 0
    return {
        "id": invoice.id,
        "card_id": card.id,
        "card_name": card.name,
        "month": invoice.month,
        "closes_on": invoice.closes_on,
        "due_on": invoice.due_on,
        "paid_on": invoice.paid_on,
        "status": "refinanced"
        if financing
        else "paid"
        if invoice.paid_on
        else "open"
        if current <= invoice.closes_on
        else "settled"
        if settled
        else "closed",
        "purchase_total_cents": sum(item.amount_cents for item, _ in installments),
        "financed_total_cents": sum(item.amount_cents for item, _ in financed_rows),
        "total_cents": total,
        "advanced_cents": advance_total,
        "remaining_cents": 0 if invoice.paid_on else remaining,
        "advances": [{"id": item.id, "amount_cents": item.amount_cents} for item in advances],
        "installments": [
            serialize_installment(item, purchase, invoice, card, settled)
            for item, purchase in installments
        ],
        "financing_installments": [
            serialize_financing_installment(item, source, invoice, card, settled)
            for item, source in financed_rows
        ],
        "financing": None
        if financing is None
        else {
            "id": financing.id,
            "paid_cents": financing.paid_cents,
            "principal_cents": financing.principal_cents,
            "fee_cents": financing.fee_cents,
            "installment_count": financing.installment_count,
        },
    }


@router.get("/cards")
def list_cards(workspace_id: UUID, db: Db, user: CurrentUser):
    require_member(db, workspace_id, user.id)
    return [
        serialize_card(row)
        for row in db.scalars(
            select(CreditCard)
            .where(CreditCard.workspace_id == workspace_id)
            .order_by(CreditCard.name, CreditCard.id)
        )
    ]


@router.post("/cards", status_code=201)
def create_card(workspace_id: UUID, data: CardInput, db: Db, user: CurrentUser):
    require_member(db, workspace_id, user.id, lock=True)
    if db.scalar(
        select(CreditCard.id).where(
            CreditCard.workspace_id == workspace_id, CreditCard.name_key == data.name.casefold()
        )
    ):
        raise HTTPException(409, "Já existe um cartão com esse nome.")
    card = CreditCard(
        workspace_id=workspace_id,
        name=data.name,
        name_key=data.name.casefold(),
        closing_day=data.closing_day,
        due_day=data.due_day,
        closing_day_next_bill=data.closing_day_next_bill,
        active=True,
    )
    db.add(card)
    db.commit()
    return serialize_card(card)


@router.patch("/cards/{card_id}")
def edit_card(workspace_id: UUID, card_id: UUID, data: CardInput, db: Db, user: CurrentUser):
    require_member(db, workspace_id, user.id, lock=True)
    card = card_or_404(db, workspace_id, card_id)
    duplicate = db.scalar(
        select(CreditCard.id).where(
            CreditCard.workspace_id == workspace_id,
            CreditCard.name_key == data.name.casefold(),
            CreditCard.id != card.id,
        )
    )
    if duplicate:
        raise HTTPException(409, "Já existe um cartão com esse nome.")
    card.name = data.name
    card.name_key = data.name.casefold()
    card.closing_day = data.closing_day
    card.due_day = data.due_day
    card.closing_day_next_bill = data.closing_day_next_bill
    db.commit()
    return serialize_card(card)


def ensure_invoice(db, card, month, current=None):
    row = db.scalar(select(Invoice).where(Invoice.card_id == card.id, Invoice.month == month))
    if row:
        if row.paid_on or (current is not None and invoice_settled(db, row, current)):
            raise HTTPException(409, "Fatura paga: não é possível alterar suas compras.")
        return row
    _, closes_on, due_on = cycle_for_due_month(card, month)
    row = Invoice(card_id=card.id, month=month, closes_on=closes_on, due_on=due_on)
    db.add(row)
    db.flush()
    return row


@router.post("/card-purchases", status_code=201)
def create_purchase(workspace_id: UUID, data: PurchaseInput, db: Db, user: CurrentUser):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    card = card_or_404(db, workspace_id, data.card_id)
    if not card.active:
        raise HTTPException(422, "Escolha um cartão ativo.")
    current = today(workspace)
    if not data.legacy and (data.purchased_on.year, data.purchased_on.month) != (
        current.year,
        current.month,
    ):
        raise HTTPException(422, "Novas compras só podem ser lançadas no mês corrente.")
    if data.legacy and data.first_bill_month is None:
        raise HTTPException(422, "Informe o primeiro mês das parcelas restantes.")
    if data.first_bill_month and data.first_bill_month.day != 1:
        raise HTTPException(422, "O mês da primeira fatura deve começar no dia 1.")
    if data.legacy and data.first_sequence + data.installment_count - 1 > 120:
        raise HTTPException(422, "Número de parcelas inválido.")
    if data.total_cents < data.installment_count:
        raise HTTPException(422, "O valor precisa cobrir ao menos um centavo por parcela.")
    category = category_or_404(db, workspace_id, data.category_id)
    sub = subcategory_or_404(db, category.id, data.subcategory_id)
    if not category.active or not sub.active:
        raise HTTPException(422, "Escolha uma categoria e subcategoria ativas.")
    automatic_first = first_cycle(card, data.purchased_on)[0] if not data.legacy else None
    first = data.first_bill_month or automatic_first
    if not data.legacy and first < automatic_first:
        raise HTTPException(422, "A primeira fatura não pode ser anterior ao ciclo da compra.")
    if first < current.replace(day=1):
        raise HTTPException(422, "A primeira fatura não pode ser anterior ao mês corrente.")
    if not data.legacy:
        existing = db.scalar(
            select(Invoice).where(Invoice.card_id == card.id, Invoice.month == first)
        )
        if existing and data.purchased_on > existing.closes_on:
            first = shift_month(first, 1)
    purchase = CardPurchase(
        card_id=card.id,
        purchased_on=data.purchased_on,
        total_cents=data.total_cents,
        legacy=data.legacy,
        created_at=datetime.now(timezone.utc),
    )
    db.add(purchase)
    db.flush()
    rows = []
    for index, cents in enumerate(split_cents(data.total_cents, data.installment_count)):
        try:
            month = shift_month(first, index)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        invoice = ensure_invoice(db, card, month, current)
        row = CardInstallment(
            purchase_id=purchase.id,
            invoice_id=invoice.id,
            sequence=data.first_sequence + index,
            total_count=data.first_sequence + data.installment_count - 1,
            amount_cents=cents,
            category_id=category.id,
            subcategory_id=sub.id,
            note=data.note.strip(),
        )
        db.add(row)
        rows.append((row, invoice))
    db.commit()
    return {
        "id": purchase.id,
        "legacy": purchase.legacy,
        "installments": [
            serialize_installment(row, purchase, invoice, card) for row, invoice in rows
        ],
    }


@router.get("/card-installments")
def list_month_installments(
    workspace_id: UUID,
    db: Db,
    user: CurrentUser,
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
):
    workspace, _ = require_member(db, workspace_id, user.id)
    year, number = map(int, month.split("-"))
    if year < 1:
        raise HTTPException(422, "Mês inválido.")
    target = date(year, number, 1)
    rows = db.execute(
        select(CardInstallment, CardPurchase, Invoice, CreditCard)
        .join(CardPurchase, CardInstallment.purchase_id == CardPurchase.id)
        .join(Invoice, CardInstallment.invoice_id == Invoice.id)
        .join(CreditCard, Invoice.card_id == CreditCard.id)
        .where(CreditCard.workspace_id == workspace_id, Invoice.month == target)
        .order_by(CreditCard.name, CardInstallment.id)
    ).all()
    return [
        serialize_installment(
            item, purchase, invoice, card, invoice_settled(db, invoice, today(workspace))
        )
        for item, purchase, invoice, card in rows
    ]


@router.get("/invoices")
def list_invoices(
    workspace_id: UUID,
    db: Db,
    user: CurrentUser,
    card_id: UUID | None = None,
):
    workspace, _ = require_member(db, workspace_id, user.id)
    if card_id:
        card_or_404(db, workspace_id, card_id)
    rows = db.execute(
        select(Invoice, CreditCard)
        .join(CreditCard, Invoice.card_id == CreditCard.id)
        .where(CreditCard.workspace_id == workspace_id)
        .where(CreditCard.id == card_id if card_id else True)
        .order_by(Invoice.month.desc(), CreditCard.name)
    ).all()
    return [serialize_invoice(db, invoice, card, today(workspace)) for invoice, card in rows]


@router.get("/invoices/{invoice_id}")
def get_invoice(workspace_id: UUID, invoice_id: UUID, db: Db, user: CurrentUser):
    workspace, _ = require_member(db, workspace_id, user.id)
    invoice, card = invoice_or_404(db, workspace_id, invoice_id)
    return serialize_invoice(db, invoice, card, today(workspace))


@router.post("/invoices/{invoice_id}/pay")
def pay_invoice(
    workspace_id: UUID, invoice_id: UUID, data: PayInvoiceInput, db: Db, user: CurrentUser
):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    invoice, card = invoice_or_404(db, workspace_id, invoice_id)
    current = today(workspace)
    if invoice.paid_on:
        raise HTTPException(409, "Esta fatura já foi paga.")
    if current <= invoice.closes_on:
        raise HTTPException(422, "A fatura ainda está aberta. Aguarde o fechamento.")
    account = account_or_404(db, workspace_id, data.account_id)
    if account.kind != "bank":
        raise HTTPException(422, "Pague a fatura por uma conta bancária.")
    require_after_opening(account, current)
    total = invoice_remaining(db, invoice.id)
    if total == 0:
        raise HTTPException(422, "Esta fatura não tem parcelas.")
    movement = Movement(
        workspace_id=workspace_id,
        account_id=account.id,
        kind="bill_payment",
        amount_cents=total,
        occurred_on=current,
        note=f"Fatura {card.name} {invoice.month:%m/%Y}",
        created_at=datetime.now(timezone.utc),
    )
    db.add(movement)
    db.flush()
    invoice.payment_movement_id = movement.id
    invoice.paid_on = current
    db.commit()
    return serialize_invoice(db, invoice, card, current)


@router.patch("/card-purchases/{purchase_id}/remaining")
def edit_remaining(
    workspace_id: UUID, purchase_id: UUID, data: RemainingInput, db: Db, user: CurrentUser
):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    purchase = db.get(CardPurchase, purchase_id)
    if purchase is None:
        raise HTTPException(404, "Compra não encontrada.")
    card = card_or_404(db, workspace_id, purchase.card_id)
    rows = db.execute(
        select(CardInstallment, Invoice)
        .join(Invoice, CardInstallment.invoice_id == Invoice.id)
        .where(CardInstallment.purchase_id == purchase.id)
        .order_by(CardInstallment.sequence)
    ).all()
    current_month = today(workspace).replace(day=1)
    editable = [
        (item, invoice)
        for item, invoice in rows
        if invoice.month >= current_month and not invoice_settled(db, invoice, today(workspace))
    ]
    if not editable:
        raise HTTPException(409, "Esta compra não tem parcelas atuais ou futuras não pagas.")
    changing_count = data.remaining_installment_count is not None
    if changing_count:
        if data.installment_amount_cents is None or data.remaining_total_cents is not None:
            raise HTTPException(422, "Informe o valor e a quantidade das parcelas restantes.")
        amount = data.installment_amount_cents
        count = data.remaining_installment_count
        if amount * count > MAX_CENTS:
            raise HTTPException(422, "O valor total excede o permitido.")
        if editable[0][0].sequence + count - 1 > 120:
            raise HTTPException(422, "Número de parcelas inválido.")
        if any(
            item.sequence > editable[0][0].sequence and (item, invoice) not in editable
            for item, invoice in rows
        ):
            raise HTTPException(409, "Há parcelas futuras pagas nesta compra.")
        remaining_total = amount * count
    else:
        if data.remaining_total_cents is None or data.installment_amount_cents is not None:
            raise HTTPException(422, "Informe o novo total das parcelas restantes.")
        remaining_total = data.remaining_total_cents
        count = len(editable)
        if remaining_total < count:
            raise HTTPException(422, "O valor precisa cobrir ao menos um centavo por parcela.")
    category = category_or_404(db, workspace_id, data.category_id)
    sub = subcategory_or_404(db, category.id, data.subcategory_id)
    if not category.active or not sub.active:
        raise HTTPException(422, "Escolha uma categoria e subcategoria ativas.")
    parts = [amount] * count if changing_count else split_cents(remaining_total, count)
    old_by_month = {invoice.month: item for item, invoice in editable}
    first_month = editable[0][1].month
    targets = []
    for index, cents in enumerate(parts):
        try:
            month = shift_month(first_month, index)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        invoice = ensure_invoice(db, card, month, today(workspace))
        if invoice_settled(db, invoice, today(workspace)):
            raise HTTPException(409, "Uma das novas faturas já foi paga.")
        targets.append((invoice, old_by_month.get(month), cents))
    cutoff = shift_month(first_month, count)
    removed = [(item, invoice) for item, invoice in editable if invoice.month >= cutoff]
    affected = [(invoice, item, cents) for invoice, item, cents in targets]
    affected.extend((invoice, item, 0) for item, invoice in removed)
    for invoice, item, cents in affected:
        revised_total = invoice_total(db, invoice.id) - (item.amount_cents if item else 0) + cents
        if revised_total < invoice_advance_total(db, invoice.id):
            raise HTTPException(
                422, "A correção não pode deixar a fatura abaixo do valor antecipado."
            )
    for item, _ in removed:
        db.delete(item)
    total_count = editable[0][0].sequence + count - 1
    for index, (invoice, item, cents) in enumerate(targets):
        if item is None:
            item = CardInstallment(purchase_id=purchase.id, invoice_id=invoice.id,
                                   sequence=editable[0][0].sequence + index,
                                   total_count=total_count, amount_cents=cents,
                                   category_id=category.id, subcategory_id=sub.id,
                                   note=data.note.strip())
            db.add(item)
            continue
        item.amount_cents = cents
        item.total_count = total_count
        item.category_id = category.id
        item.subcategory_id = sub.id
        item.note = data.note.strip()
    purchase.total_cents = (
        sum(item.amount_cents for item, invoice in rows if (item, invoice) not in editable)
        + remaining_total
    )
    db.flush()
    for _, invoice in removed:
        if not invoice.paid_on and invoice_total(db, invoice.id) == 0:
            db.delete(invoice)
    db.commit()
    updated = db.execute(
        select(CardInstallment, Invoice)
        .join(Invoice, CardInstallment.invoice_id == Invoice.id)
        .where(CardInstallment.purchase_id == purchase.id)
        .order_by(CardInstallment.sequence)
    ).all()
    return {
        "id": purchase.id,
        "installments": [
            serialize_installment(item, purchase, invoice, card) for item, invoice in updated
        ],
    }


@router.delete("/card-purchases/{purchase_id}", status_code=204)
def delete_purchase_remaining(
    workspace_id: UUID, purchase_id: UUID, db: Db, user: CurrentUser
):
    workspace, _ = require_member(db, workspace_id, user.id, lock=True)
    purchase = db.get(CardPurchase, purchase_id)
    if purchase is None:
        raise HTTPException(404, "Compra não encontrada.")
    card_or_404(db, workspace_id, purchase.card_id)
    rows = db.execute(
        select(CardInstallment, Invoice)
        .join(Invoice, CardInstallment.invoice_id == Invoice.id)
        .where(CardInstallment.purchase_id == purchase.id)
        .order_by(CardInstallment.sequence)
    ).all()
    current = today(workspace)
    current_month = current.replace(day=1)
    removable = [
        (item, invoice) for item, invoice in rows
        if invoice.month >= current_month and not invoice_settled(db, invoice, current)
    ]
    if not removable:
        raise HTTPException(409, "Esta compra não tem parcelas atuais ou futuras não pagas.")
    removed_by_invoice = {}
    for item, invoice in removable:
        removed_by_invoice[invoice.id] = removed_by_invoice.get(invoice.id, 0) + item.amount_cents
    affected_invoices = {invoice.id: invoice for _, invoice in removable}
    for invoice_id, amount in removed_by_invoice.items():
        if invoice_total(db, invoice_id) - amount < invoice_advance_total(db, invoice_id):
            raise HTTPException(
                422, "A exclusão não pode deixar a fatura abaixo do valor antecipado."
            )
    for item, _ in removable:
        db.delete(item)
    kept_total = sum(item.amount_cents for item, invoice in rows if
                     (item, invoice) not in removable)
    occurrence = db.scalar(select(RecurringOccurrence).where(
        RecurringOccurrence.purchase_id == purchase.id
    ))
    if kept_total or occurrence:
        # A ocorrência permanece vinculada para não lançar a mesma assinatura novamente.
        purchase.total_cents = kept_total
    else:
        db.delete(purchase)
    db.flush()
    for invoice in affected_invoices.values():
        if not invoice.paid_on and invoice_total(db, invoice.id) == 0 and not db.scalar(
            select(InvoiceFinancing.id).where(InvoiceFinancing.source_invoice_id == invoice.id)
        ):
            db.delete(invoice)
    db.commit()
