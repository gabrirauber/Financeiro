"""Categorias por espaço e despesas pagas."""

from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "e05_expenses"
down_revision = "e04_finance"
branch_labels = None
depends_on = None

DEFAULTS = (
    ("Casa", "#315F51", ("Aluguel", "Internet", "Energia")),
    ("Alimentação", "#BE6D45", ("Mercado", "Restaurantes", "Café")),
    ("Transporte", "#647CAB", ("Combustível", "Aplicativos", "Transporte público")),
    ("Lazer", "#A77EAC", ("Passeios", "Streaming", "Compras")),
)


def upgrade():
    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("name_key", sa.String(40), nullable=False),
        sa.Column("color", sa.String(7), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("workspace_id", "name_key", name="uq_category_name"),
    )
    op.create_index("ix_categories_workspace_id", "categories", ["workspace_id"])
    op.create_table(
        "subcategories",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "category_id",
            sa.Uuid(),
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(40), nullable=False),
        sa.Column("name_key", sa.String(40), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("category_id", "name_key", name="uq_subcategory_name"),
    )
    op.create_index("ix_subcategories_category_id", "subcategories", ["category_id"])
    op.create_table(
        "expenses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "movement_id",
            sa.Uuid(),
            sa.ForeignKey("movements.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("category_id", sa.Uuid(), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("subcategory_id", sa.Uuid(), sa.ForeignKey("subcategories.id"), nullable=False),
        sa.Column("payment_method", sa.String(10), nullable=False),
        sa.CheckConstraint("payment_method IN ('pix', 'debit', 'cash')", name="expense_payment"),
    )
    op.create_index("ix_expenses_workspace_id", "expenses", ["workspace_id"])
    op.drop_constraint("movement_kind", "movements", type_="check")
    op.create_check_constraint(
        "movement_kind",
        "movements",
        "kind IN ('income', 'transfer_out', 'transfer_in', 'expense')",
    )
    connection = op.get_bind()
    for (workspace_id,) in connection.execute(sa.text("SELECT id FROM workspaces")):
        for name, color, subcategories in DEFAULTS:
            category_id = uuid4()
            connection.execute(
                sa.text(
                    "INSERT INTO categories (id, workspace_id, name, name_key, color, active) "
                    "VALUES (:id, :workspace_id, :name, :name_key, :color, true)"
                ),
                dict(
                    id=category_id,
                    workspace_id=workspace_id,
                    name=name,
                    name_key=name.casefold(),
                    color=color,
                ),
            )
            for sub in subcategories:
                connection.execute(
                    sa.text(
                        "INSERT INTO subcategories (id, category_id, name, name_key, active) "
                        "VALUES (:id, :category_id, :name, :name_key, true)"
                    ),
                    dict(id=uuid4(), category_id=category_id, name=sub, name_key=sub.casefold()),
                )
    op.execute(sa.text("UPDATE app_metadata SET value = 'e05' WHERE key = 'schema'"))


def downgrade():
    op.execute(sa.text("UPDATE app_metadata SET value = 'e04' WHERE key = 'schema'"))
    op.drop_table("expenses")
    op.drop_table("subcategories")
    op.drop_table("categories")
    op.drop_constraint("movement_kind", "movements", type_="check")
    op.create_check_constraint(
        "movement_kind",
        "movements",
        "kind IN ('income', 'transfer_out', 'transfer_in')",
    )
