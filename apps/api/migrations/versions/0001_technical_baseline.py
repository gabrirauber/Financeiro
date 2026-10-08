"""Base técnica da E02, sem tabelas financeiras ou usuários."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    table = op.create_table(
        "app_metadata",
        sa.Column("key", sa.String(50), primary_key=True),
        sa.Column("value", sa.String(100), nullable=False),
    )
    op.bulk_insert(table, [{"key": "schema", "value": "e02"}])


def downgrade():
    op.drop_table("app_metadata")
