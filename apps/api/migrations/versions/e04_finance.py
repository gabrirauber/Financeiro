"""Contas e movimentos financeiros da E04."""

import sqlalchemy as sa
from alembic import op

revision = "e04_finance"
down_revision = "e03_ready"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("opening_balance_cents", sa.Integer(), nullable=False),
        sa.Column("opened_on", sa.Date(), nullable=False),
        sa.CheckConstraint("kind IN ('bank', 'cash')", name="account_kind"),
        sa.CheckConstraint("opening_balance_cents >= 0", name="account_opening_nonnegative"),
    )
    op.create_index("ix_accounts_workspace_id", "accounts", ["workspace_id"])
    op.create_table(
        "movements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.Uuid(),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("note", sa.String(200), nullable=False),
        sa.Column("transfer_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind IN ('income', 'transfer_out', 'transfer_in')", name="movement_kind"
        ),
        sa.CheckConstraint("amount_cents > 0", name="movement_amount_positive"),
    )
    for column in ("workspace_id", "account_id", "transfer_id"):
        op.create_index(f"ix_movements_{column}", "movements", [column])
    op.execute(sa.text("UPDATE app_metadata SET value = 'e04' WHERE key = 'schema'"))


def downgrade():
    op.execute(sa.text("UPDATE app_metadata SET value = 'e03' WHERE key = 'schema'"))
    op.drop_table("movements")
    op.drop_table("accounts")
