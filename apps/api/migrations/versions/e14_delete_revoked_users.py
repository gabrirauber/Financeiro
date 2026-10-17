"""Permite excluir cadastros sem apagar o histórico de espaços compartilhados."""

import sqlalchemy as sa
from alembic import op

revision = "e14_delete_revoked_users"
down_revision = "e13_onboarding"
branch_labels = None
depends_on = None


REFERENCES = (
    ("invites", "created_by"),
    ("income_plans", "responsible_user_id"),
    ("income_occurrences", "responsible_user_id"),
)


def upgrade():
    for table, column in REFERENCES:
        op.drop_constraint(f"{table}_{column}_fkey", table, type_="foreignkey")
        op.alter_column(table, column, existing_type=sa.Uuid(), nullable=True)
        op.create_foreign_key(
            f"{table}_{column}_fkey", table, "users", [column], ["id"], ondelete="SET NULL"
        )
    op.execute("UPDATE app_metadata SET value = 'e14' WHERE key = 'schema'")


def downgrade():
    # Caso uma exclusão tenha deixado referências vazias, é necessário resolver
    # esses registros antes de voltar a exigir um usuário responsável.
    for table, column in REFERENCES:
        op.drop_constraint(f"{table}_{column}_fkey", table, type_="foreignkey")
        op.alter_column(table, column, existing_type=sa.Uuid(), nullable=False)
        op.create_foreign_key(f"{table}_{column}_fkey", table, "users", [column], ["id"])
    op.execute("UPDATE app_metadata SET value = 'e13' WHERE key = 'schema'")
