from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CreditCard(Base):
    __tablename__ = "credit_cards"
    __table_args__ = (
        CheckConstraint("closing_day BETWEEN 1 AND 31", name="card_closing_day"),
        CheckConstraint("due_day BETWEEN 1 AND 31", name="card_due_day"),
        UniqueConstraint("workspace_id", "name_key", name="uq_card_name"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(80))
    name_key: Mapped[str] = mapped_column(String(80))
    closing_day: Mapped[int] = mapped_column(Integer)
    due_day: Mapped[int] = mapped_column(Integer)
    closing_day_next_bill: Mapped[bool] = mapped_column(Boolean)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("card_id", "month", name="uq_invoice_month"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    card_id: Mapped[UUID] = mapped_column(
        ForeignKey("credit_cards.id", ondelete="CASCADE"), index=True
    )
    month: Mapped[date] = mapped_column(Date)
    closes_on: Mapped[date] = mapped_column(Date)
    due_on: Mapped[date] = mapped_column(Date)
    payment_movement_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("movements.id"), unique=True, nullable=True
    )
    paid_on: Mapped[date | None] = mapped_column(Date, nullable=True)


class CardPurchase(Base):
    __tablename__ = "card_purchases"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    card_id: Mapped[UUID] = mapped_column(
        ForeignKey("credit_cards.id", ondelete="CASCADE"), index=True
    )
    purchased_on: Mapped[date] = mapped_column(Date)
    total_cents: Mapped[int] = mapped_column(Integer)
    legacy: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CardInstallment(Base):
    __tablename__ = "card_installments"
    __table_args__ = (
        UniqueConstraint("purchase_id", "sequence", name="uq_purchase_sequence"),
        CheckConstraint("amount_cents > 0", name="card_installment_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    purchase_id: Mapped[UUID] = mapped_column(
        ForeignKey("card_purchases.id", ondelete="CASCADE"), index=True
    )
    invoice_id: Mapped[UUID] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    total_count: Mapped[int] = mapped_column(Integer)
    amount_cents: Mapped[int] = mapped_column(Integer)
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id"))
    subcategory_id: Mapped[UUID] = mapped_column(ForeignKey("subcategories.id"))
    note: Mapped[str] = mapped_column(String(200), default="")


class InvoiceFinancing(Base):
    __tablename__ = "invoice_financings"
    __table_args__ = (
        CheckConstraint("paid_cents > 0", name="financing_paid_positive"),
        CheckConstraint("principal_cents > 0", name="financing_principal_positive"),
        CheckConstraint("fee_cents >= 0", name="financing_fee_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source_invoice_id: Mapped[UUID] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), unique=True
    )
    paid_cents: Mapped[int] = mapped_column(Integer)
    principal_cents: Mapped[int] = mapped_column(Integer)
    fee_cents: Mapped[int] = mapped_column(Integer)
    installment_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FinancingInstallment(Base):
    __tablename__ = "financing_installments"
    __table_args__ = (
        UniqueConstraint("financing_id", "sequence", name="uq_financing_sequence"),
        CheckConstraint("amount_cents > 0", name="financing_installment_positive"),
        CheckConstraint("principal_cents >= 0", name="financing_part_principal"),
        CheckConstraint("fee_cents >= 0", name="financing_part_fee"),
        CheckConstraint(
            "amount_cents = principal_cents + fee_cents",
            name="financing_installment_parts",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    financing_id: Mapped[UUID] = mapped_column(
        ForeignKey("invoice_financings.id", ondelete="CASCADE"), index=True
    )
    invoice_id: Mapped[UUID] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    principal_cents: Mapped[int] = mapped_column(Integer)
    fee_cents: Mapped[int] = mapped_column(Integer)
    amount_cents: Mapped[int] = mapped_column(Integer)


class InvoiceAdvance(Base):
    __tablename__ = "invoice_advances"
    __table_args__ = (
        UniqueConstraint("invoice_id", "request_id", name="uq_invoice_advance_request"),
        CheckConstraint("amount_cents > 0", name="invoice_advance_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    invoice_id: Mapped[UUID] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )
    movement_id: Mapped[UUID] = mapped_column(ForeignKey("movements.id"), unique=True)
    request_id: Mapped[str] = mapped_column(String(80))
    amount_cents: Mapped[int] = mapped_column(Integer)
