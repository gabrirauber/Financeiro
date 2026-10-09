from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Uuid
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
        CheckConstraint("kind IN ('income', 'transfer_out', 'transfer_in')", name="movement_kind"),
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
