"""Limita cada login a um espaço financeiro por vez."""

from alembic import op

revision = "e08_single_workspace"
down_revision = "e07_invoice_advances"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        "uq_membership_one_space_per_user", "memberships", ["user_id"]
    )


def downgrade():
    op.drop_constraint("uq_membership_one_space_per_user", "memberships", type_="unique")
