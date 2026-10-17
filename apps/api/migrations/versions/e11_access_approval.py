"""Aprovação de novos usuários e administrador de acesso existente."""

import sqlalchemy as sa
from alembic import op

revision = "e11_access_approval"
down_revision = "e08_income"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("access_status", sa.String(10), nullable=False,
                                     server_default="pending"))
    op.add_column("users", sa.Column("is_access_admin", sa.Boolean(), nullable=False,
                                     server_default=sa.false()))
    op.add_column("users", sa.Column("requested_at", sa.DateTime(timezone=True),
                                     nullable=False, server_default=sa.func.now()))
    op.create_check_constraint(
        "user_access_status", "users",
        "access_status IN ('pending', 'approved', 'rejected', 'revoked')",
    )
    # Preserva o acesso de todos os usuários anteriores à regra de aprovação.
    op.execute("UPDATE users SET access_status = 'approved'")
    # Só a conta já existente no instante da migração recebe a administração.
    op.execute(
        "UPDATE users SET is_access_admin = true "
        "WHERE email = 'gabrirauber@gmail.com'"
    )
    op.execute("UPDATE app_metadata SET value = 'e11' WHERE key = 'schema'")


def downgrade():
    op.execute("UPDATE app_metadata SET value = 'e08' WHERE key = 'schema'")
    op.drop_constraint("user_access_status", "users", type_="check")
    op.drop_column("users", "requested_at")
    op.drop_column("users", "is_access_admin")
    op.drop_column("users", "access_status")
