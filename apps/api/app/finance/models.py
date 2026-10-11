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


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("kind IN ('bank', 'cash')", name="account_kind"),
        CheckConstraint("opening_balance_cents >= 0", name="account_opening_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(10))
    opening_balance_cents: Mapped[int] = mapped_column(Integer)
    opened_on: Mapped[date] = mapped_column(Date)


class Movement(Base):
    __tablename__ = "movements"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('income', 'transfer_out', 'transfer_in', 'expense', 'bill_payment')",
            name="movement_kind",
        ),
        CheckConstraint("amount_cents > 0", name="movement_amount_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(20))
    amount_cents: Mapped[int] = mapped_column(Integer)
    occurred_on: Mapped[date] = mapped_column(Date)
    note: Mapped[str] = mapped_column(String(200), default="")
    transfer_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("workspace_id", "name_key", name="uq_category_name"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(40))
    name_key: Mapped[str] = mapped_column(String(40))
    color: Mapped[str] = mapped_column(String(7))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Subcategory(Base):
    __tablename__ = "subcategories"
    __table_args__ = (UniqueConstraint("category_id", "name_key", name="uq_subcategory_name"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(40))
    name_key: Mapped[str] = mapped_column(String(40))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("payment_method IN ('pix', 'debit', 'cash')", name="expense_payment"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    movement_id: Mapped[UUID] = mapped_column(
        ForeignKey("movements.id", ondelete="CASCADE"), unique=True
    )
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id"))
    subcategory_id: Mapped[UUID] = mapped_column(ForeignKey("subcategories.id"))
    payment_method: Mapped[str] = mapped_column(String(10))
