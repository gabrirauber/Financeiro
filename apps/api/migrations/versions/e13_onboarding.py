"""Guia inicial persistido por usuário, inclusive após aprovação."""

import sqlalchemy as sa
from alembic import op

revision = "e13_onboarding"
down_revision = "e12_demo_account"
branch_labels = None
depends_on = None


def upgrade():
    # Preserva o administrador em uso e a demonstração. Outros participantes
    # recebem o guia uma vez, inclusive quem foi aprovado antes desta correção.
    op.add_column("users", sa.Column("onboarding_step", sa.Integer(), nullable=False,
                                     server_default="4"))
    op.execute(
        "UPDATE users SET onboarding_step = 0 "
        "WHERE is_demo = false AND email <> 'gabrirauber@gmail.com'"
    )
    op.alter_column("users", "onboarding_step", server_default="0")
    op.create_check_constraint("user_onboarding_step", "users",
                               "onboarding_step BETWEEN 0 AND 4")
    op.execute("UPDATE app_metadata SET value = 'e13' WHERE key = 'schema'")


def downgrade():
    op.execute("UPDATE app_metadata SET value = 'e12' WHERE key = 'schema'")
    op.drop_constraint("user_onboarding_step", "users", type_="check")
    op.drop_column("users", "onboarding_step")
