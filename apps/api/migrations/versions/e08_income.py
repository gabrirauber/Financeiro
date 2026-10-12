"""Previsões mensais de renda, ocorrências e recebimentos vinculados."""

import sqlalchemy as sa
from alembic import op

revision = "e08_income"
down_revision = "e08_recurring"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "income_plans",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("description", sa.String(120), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("day_of_month", sa.Integer(), nullable=False),
        sa.Column("responsible_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("start_month", sa.Date(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount_cents > 0", name="income_plan_positive"),
        sa.CheckConstraint("day_of_month BETWEEN 1 AND 31", name="income_plan_day"),
    )
    op.create_index("ix_income_plans_workspace_id", "income_plans", ["workspace_id"])
    op.create_table(
        "income_occurrences",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Uuid(),
            sa.ForeignKey("income_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column("expected_cents", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(120), nullable=False),
        sa.Column("responsible_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("reminded_on", sa.Date(), nullable=True),
        sa.UniqueConstraint("plan_id", "month", name="uq_income_occurrence_month"),
        sa.CheckConstraint("expected_cents > 0", name="income_occurrence_positive"),
    )
    op.create_index("ix_income_occurrences_plan_id", "income_occurrences", ["plan_id"])
    op.create_table(
        "income_receipts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "occurrence_id",
            sa.Uuid(),
            sa.ForeignKey("income_occurrences.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "movement_id", sa.Uuid(), sa.ForeignKey("movements.id"), nullable=False, unique=True
        ),
        sa.Column("request_id", sa.String(80), nullable=False),
        sa.UniqueConstraint("occurrence_id", "request_id", name="uq_income_receipt_request"),
    )
    op.create_index("ix_income_receipts_occurrence_id", "income_receipts", ["occurrence_id"])
    op.execute(sa.text("UPDATE app_metadata SET value = 'e08' WHERE key = 'schema'"))


def downgrade():
    op.execute(sa.text("UPDATE app_metadata SET value = 'e07' WHERE key = 'schema'"))
    op.drop_table("income_receipts")
    op.drop_table("income_occurrences")
    op.drop_table("income_plans")
