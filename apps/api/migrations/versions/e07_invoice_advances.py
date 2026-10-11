"""Antecipações de pagamento em faturas abertas."""

import sqlalchemy as sa
from alembic import op

revision = "e07_invoice_advances"
down_revision = "e07_financing"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "invoice_advances",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "invoice_id",
            sa.Uuid(),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "movement_id", sa.Uuid(), sa.ForeignKey("movements.id"), nullable=False, unique=True
        ),
        sa.Column("request_id", sa.String(80), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.UniqueConstraint("invoice_id", "request_id", name="uq_invoice_advance_request"),
        sa.CheckConstraint("amount_cents > 0", name="invoice_advance_positive"),
    )
    op.create_index("ix_invoice_advances_invoice_id", "invoice_advances", ["invoice_id"])


def downgrade():
    op.drop_table("invoice_advances")
