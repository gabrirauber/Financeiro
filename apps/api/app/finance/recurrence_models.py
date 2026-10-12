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


class RecurringRule(Base):
    __tablename__ = "recurring_rules"
    __table_args__ = (
        CheckConstraint("kind IN ('expense', 'card')", name="recurring_kind"),
        CheckConstraint(
            "payment_method IN ('pix', 'debit', 'cash') OR payment_method IS NULL",
            name="recurring_payment_method",
        ),
        CheckConstraint("amount_cents > 0", name="recurring_amount_positive"),
        CheckConstraint("day_of_month BETWEEN 1 AND 31", name="recurring_day"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(10))
    description: Mapped[str] = mapped_column(String(120))
    amount_cents: Mapped[int] = mapped_column(Integer)
    day_of_month: Mapped[int] = mapped_column(Integer)
    start_month: Mapped[date] = mapped_column(Date)
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id"))
    subcategory_id: Mapped[UUID] = mapped_column(ForeignKey("subcategories.id"))
    payment_method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    card_id: Mapped[UUID | None] = mapped_column(ForeignKey("credit_cards.id"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RecurringOccurrence(Base):
    __tablename__ = "recurring_occurrences"
    __table_args__ = (
        UniqueConstraint("rule_id", "month", name="uq_recurring_occurrence_month"),
        CheckConstraint("amount_cents > 0", name="recurring_occurrence_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    rule_id: Mapped[UUID] = mapped_column(
        ForeignKey("recurring_rules.id", ondelete="CASCADE"), index=True
    )
    month: Mapped[date] = mapped_column(Date)
    due_on: Mapped[date] = mapped_column(Date)
    amount_cents: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String(120))
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id"))
    subcategory_id: Mapped[UUID] = mapped_column(ForeignKey("subcategories.id"))
    payment_method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    card_id: Mapped[UUID | None] = mapped_column(ForeignKey("credit_cards.id"), nullable=True)
    expense_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("expenses.id"), unique=True, nullable=True
    )
    purchase_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("card_purchases.id"), unique=True, nullable=True
    )


class IncomePlan(Base):
    __tablename__ = "income_plans"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="income_plan_positive"),
        CheckConstraint("day_of_month BETWEEN 1 AND 31", name="income_plan_day"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    description: Mapped[str] = mapped_column(String(120))
    amount_cents: Mapped[int] = mapped_column(Integer)
    day_of_month: Mapped[int] = mapped_column(Integer)
    responsible_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    start_month: Mapped[date] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IncomeOccurrence(Base):
    __tablename__ = "income_occurrences"
    __table_args__ = (
        UniqueConstraint("plan_id", "month", name="uq_income_occurrence_month"),
        CheckConstraint("expected_cents > 0", name="income_occurrence_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("income_plans.id", ondelete="CASCADE"), index=True
    )
    month: Mapped[date] = mapped_column(Date)
    due_on: Mapped[date] = mapped_column(Date)
    expected_cents: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String(120))
    responsible_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    reminded_on: Mapped[date | None] = mapped_column(Date, nullable=True)


class IncomeReceipt(Base):
    __tablename__ = "income_receipts"
    __table_args__ = (
        UniqueConstraint("occurrence_id", "request_id", name="uq_income_receipt_request"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    occurrence_id: Mapped[UUID] = mapped_column(
        ForeignKey("income_occurrences.id", ondelete="CASCADE"), index=True
    )
    movement_id: Mapped[UUID] = mapped_column(ForeignKey("movements.id"), unique=True)
    request_id: Mapped[str] = mapped_column(String(80))
