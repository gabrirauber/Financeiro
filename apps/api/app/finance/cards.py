from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select

from app.finance.card_models import CardInstallment, CardPurchase, CreditCard, Invoice
from app.finance.categories import category_or_404, subcategory_or_404
from app.finance.cycles import cycle_for_due_month, first_cycle, shift_month, split_cents
from app.finance.models import Movement
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
    remaining_total_cents: int = Field(gt=0, le=MAX_CENTS)
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


def serialize_installment(row, purchase, invoice, card):
    return {
        "id": row.id,
        "purchase_id": purchase.id,
        "card_id": card.id,
        "card_name": card.name,
        "invoice_id": invoice.id,
        "invoice_month": invoice.month,
        "invoice_paid": invoice.paid_on is not None,
        "purchased_on": purchase.purchased_on,
        "legacy": purchase.legacy,
        "sequence": row.sequence,
        "total_count": row.total_count,
        "amount_cents": row.amount_cents,
        "category_id": row.category_id,
        "subcategory_id": row.subcategory_id,
        "note": row.note,
    }


def serialize_invoice(db, invoice, card, current):
    installments = installment_rows(db, invoice.id)
    return {
        "id": invoice.id,
        "card_id": card.id,
        "card_name": card.name,
        "month": invoice.month,
        "closes_on": invoice.closes_on,
        "due_on": invoice.due_on,
        "paid_on": invoice.paid_on,
        "status": "paid"
        if invoice.paid_on
        else ("open" if current <= invoice.closes_on else "closed"),
        "total_cents": sum(item.amount_cents for item, _ in installments),
        "installments": [
            serialize_installment(item, purchase, invoice, card) for item, purchase in installments
        ],
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


def ensure_invoice(db, card, month):
    row = db.scalar(select(Invoice).where(Invoice.card_id == card.id, Invoice.month == month))
    if row:
        if row.paid_on:
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
        invoice = ensure_invoice(db, card, month)
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
    require_member(db, workspace_id, user.id)
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
        serialize_installment(item, purchase, invoice, card)
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
    total = (
        db.scalar(
            select(func.sum(CardInstallment.amount_cents)).where(
                CardInstallment.invoice_id == invoice.id
            )
        )
        or 0
    )
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
        if invoice.month >= current_month and not invoice.paid_on
    ]
    if not editable:
        raise HTTPException(409, "Esta compra não tem parcelas atuais ou futuras não pagas.")
    if data.remaining_total_cents < len(editable):
        raise HTTPException(422, "O valor precisa cobrir ao menos um centavo por parcela.")
    category = category_or_404(db, workspace_id, data.category_id)
    sub = subcategory_or_404(db, category.id, data.subcategory_id)
    if not category.active or not sub.active:
        raise HTTPException(422, "Escolha uma categoria e subcategoria ativas.")
    for (item, _), cents in zip(editable, split_cents(data.remaining_total_cents, len(editable))):
        item.amount_cents = cents
        item.category_id = category.id
        item.subcategory_id = sub.id
        item.note = data.note.strip()
    purchase.total_cents = (
        sum(item.amount_cents for item, invoice in rows if (item, invoice) not in editable)
        + data.remaining_total_cents
    )
    db.commit()
    return {
        "id": purchase.id,
        "installments": [
            serialize_installment(item, purchase, invoice, card) for item, invoice in rows
        ],
    }
