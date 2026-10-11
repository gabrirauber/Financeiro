"""Pagamento parcial e parcelas financiadas de faturas."""

import sqlalchemy as sa
from alembic import op

revision = "e07_financing"
down_revision = "e06_cards"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "invoice_financings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "source_invoice_id",
            sa.Uuid(),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("paid_cents", sa.Integer(), nullable=False),
        sa.Column("principal_cents", sa.Integer(), nullable=False),
        sa.Column("fee_cents", sa.Integer(), nullable=False),
        sa.Column("installment_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("paid_cents > 0", name="financing_paid_positive"),
        sa.CheckConstraint("principal_cents > 0", name="financing_principal_positive"),
        sa.CheckConstraint("fee_cents >= 0", name="financing_fee_nonnegative"),
    )
    op.create_table(
        "financing_installments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "financing_id",
            sa.Uuid(),
            sa.ForeignKey("invoice_financings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invoice_id",
            sa.Uuid(),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("principal_cents", sa.Integer(), nullable=False),
        sa.Column("fee_cents", sa.Integer(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.UniqueConstraint("financing_id", "sequence", name="uq_financing_sequence"),
        sa.CheckConstraint("amount_cents > 0", name="financing_installment_positive"),
        sa.CheckConstraint("principal_cents >= 0", name="financing_part_principal"),
        sa.CheckConstraint("fee_cents >= 0", name="financing_part_fee"),
        sa.CheckConstraint(
            "amount_cents = principal_cents + fee_cents",
            name="financing_installment_parts",
        ),
    )
    op.create_index(
        "ix_financing_installments_financing_id",
        "financing_installments",
        ["financing_id"],
    )
    op.create_index(
        "ix_financing_installments_invoice_id",
        "financing_installments",
        ["invoice_id"],
    )
    op.execute(sa.text("UPDATE app_metadata SET value = 'e07' WHERE key = 'schema'"))


def downgrade():
    op.execute(sa.text("UPDATE app_metadata SET value = 'e06' WHERE key = 'schema'"))
    op.drop_table("financing_installments")
    op.drop_table("invoice_financings")
