"""Marcar prontidão do esquema completo E03."""

import sqlalchemy as sa
from alembic import op

revision = "e03_ready"
down_revision = "5cc8891f323f"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("UPDATE app_metadata SET value = 'e03' WHERE key = 'schema'"))


def downgrade():
    op.execute(sa.text("UPDATE app_metadata SET value = 'e02' WHERE key = 'schema'"))
