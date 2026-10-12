"""Regras mensais e ocorrências de despesas fixas ou compras no cartão."""

import sqlalchemy as sa
from alembic import op

revision = "e08_recurring"
down_revision = "e08_single_workspace"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "recurring_rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("description", sa.String(120), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("day_of_month", sa.Integer(), nullable=False),
        sa.Column("start_month", sa.Date(), nullable=False),
        sa.Column("category_id", sa.Uuid(), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("subcategory_id", sa.Uuid(), sa.ForeignKey("subcategories.id"), nullable=False),
        sa.Column("payment_method", sa.String(10), nullable=True),
        sa.Column("card_id", sa.Uuid(), sa.ForeignKey("credit_cards.id"), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('expense', 'card')", name="recurring_kind"),
        sa.CheckConstraint(
            "payment_method IN ('pix', 'debit', 'cash') OR payment_method IS NULL",
            name="recurring_payment_method",
        ),
        sa.CheckConstraint("amount_cents > 0", name="recurring_amount_positive"),
        sa.CheckConstraint("day_of_month BETWEEN 1 AND 31", name="recurring_day"),
    )
    op.create_index("ix_recurring_rules_workspace_id", "recurring_rules", ["workspace_id"])
    op.create_table(
        "recurring_occurrences",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "rule_id",
            sa.Uuid(),
            sa.ForeignKey("recurring_rules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(120), nullable=False),
        sa.Column("category_id", sa.Uuid(), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("subcategory_id", sa.Uuid(), sa.ForeignKey("subcategories.id"), nullable=False),
        sa.Column("payment_method", sa.String(10), nullable=True),
        sa.Column("card_id", sa.Uuid(), sa.ForeignKey("credit_cards.id"), nullable=True),
        sa.Column(
            "expense_id", sa.Uuid(), sa.ForeignKey("expenses.id"), nullable=True, unique=True
        ),
        sa.Column(
            "purchase_id", sa.Uuid(), sa.ForeignKey("card_purchases.id"), nullable=True, unique=True
        ),
        sa.UniqueConstraint("rule_id", "month", name="uq_recurring_occurrence_month"),
        sa.CheckConstraint("amount_cents > 0", name="recurring_occurrence_positive"),
    )
    op.create_index("ix_recurring_occurrences_rule_id", "recurring_occurrences", ["rule_id"])


def downgrade():
    op.drop_table("recurring_occurrences")
    op.drop_table("recurring_rules")
