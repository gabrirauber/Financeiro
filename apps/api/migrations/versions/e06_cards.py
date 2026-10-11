"""Cartões, ciclos, parcelas e pagamento integral da fatura."""

import sqlalchemy as sa
from alembic import op

revision = "e06_cards"
down_revision = "e05_expenses"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "credit_cards",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("name_key", sa.String(80), nullable=False),
        sa.Column("closing_day", sa.Integer(), nullable=False),
        sa.Column("due_day", sa.Integer(), nullable=False),
        sa.Column("closing_day_next_bill", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.CheckConstraint("closing_day BETWEEN 1 AND 31", name="card_closing_day"),
        sa.CheckConstraint("due_day BETWEEN 1 AND 31", name="card_due_day"),
        sa.UniqueConstraint("workspace_id", "name_key", name="uq_card_name"),
    )
    op.create_index("ix_credit_cards_workspace_id", "credit_cards", ["workspace_id"])
    op.create_table(
        "invoices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "card_id",
            sa.Uuid(),
            sa.ForeignKey("credit_cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("closes_on", sa.Date(), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column(
            "payment_movement_id",
            sa.Uuid(),
            sa.ForeignKey("movements.id"),
            nullable=True,
            unique=True,
        ),
        sa.Column("paid_on", sa.Date(), nullable=True),
        sa.UniqueConstraint("card_id", "month", name="uq_invoice_month"),
    )
    op.create_index("ix_invoices_card_id", "invoices", ["card_id"])
    op.create_table(
        "card_purchases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "card_id",
            sa.Uuid(),
            sa.ForeignKey("credit_cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("purchased_on", sa.Date(), nullable=False),
        sa.Column("total_cents", sa.Integer(), nullable=False),
        sa.Column("legacy", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_card_purchases_card_id", "card_purchases", ["card_id"])
    op.create_table(
        "card_installments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "purchase_id",
            sa.Uuid(),
            sa.ForeignKey("card_purchases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invoice_id",
            sa.Uuid(),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Uuid(), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("subcategory_id", sa.Uuid(), sa.ForeignKey("subcategories.id"), nullable=False),
        sa.Column("note", sa.String(200), nullable=False),
        sa.CheckConstraint("amount_cents > 0", name="card_installment_positive"),
        sa.UniqueConstraint("purchase_id", "sequence", name="uq_purchase_sequence"),
    )
    for column in ("purchase_id", "invoice_id"):
        op.create_index(f"ix_card_installments_{column}", "card_installments", [column])
    op.drop_constraint("movement_kind", "movements", type_="check")
    op.create_check_constraint(
        "movement_kind",
        "movements",
        "kind IN ('income', 'transfer_out', 'transfer_in', 'expense', 'bill_payment')",
    )
    op.execute(sa.text("UPDATE app_metadata SET value = 'e06' WHERE key = 'schema'"))


def downgrade():
    op.execute(sa.text("UPDATE app_metadata SET value = 'e05' WHERE key = 'schema'"))
    op.drop_table("card_installments")
    op.drop_table("card_purchases")
    op.drop_table("invoices")
    op.drop_table("credit_cards")
    op.drop_constraint("movement_kind", "movements", type_="check")
    op.create_check_constraint(
        "movement_kind",
        "movements",
        "kind IN ('income', 'transfer_out', 'transfer_in', 'expense')",
    )
