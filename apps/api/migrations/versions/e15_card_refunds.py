"""Créditos de estorno vinculados à parcela original."""

import sqlalchemy as sa
from alembic import op

revision = "e15_card_refunds"
down_revision = "e14_delete_revoked_users"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "card_refunds",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "source_installment_id",
            sa.Uuid(),
            sa.ForeignKey("card_installments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invoice_id",
            sa.Uuid(),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("credited_on", sa.Date(), nullable=False),
        sa.Column("note", sa.String(200), nullable=False),
        sa.Column("request_id", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount_cents > 0", name="card_refund_positive"),
        sa.UniqueConstraint("source_installment_id", "request_id", name="uq_card_refund_request"),
    )
    op.create_index("ix_card_refunds_invoice_id", "card_refunds", ["invoice_id"])
    op.execute("UPDATE app_metadata SET value = 'e15' WHERE key = 'schema'")


def downgrade():
    op.drop_table("card_refunds")
    op.execute("UPDATE app_metadata SET value = 'e14' WHERE key = 'schema'")
