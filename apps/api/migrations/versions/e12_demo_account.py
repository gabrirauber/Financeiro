"""Conta de demonstração pendente e lançamentos de exemplo identificados."""

from datetime import datetime
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from alembic import op

revision = "e12_demo_account"
down_revision = "e11_access_approval"
branch_labels = None
depends_on = None

DEMO_EMAIL = "teste@teste.com.br"
DEMO_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$LWO4zZenSp6BFp6Vx+Mntg$"
    "pxNJhhtE5aqAp4VUfHRNMB1hloabiWNrWnTJ9rV+NQM"
)


def identifier(name):
    return uuid5(NAMESPACE_URL, f"rautto:e12:{name}")


def upgrade():
    op.add_column("users", sa.Column("is_demo", sa.Boolean(), nullable=False,
                                     server_default=sa.false()))
    connection = op.get_bind()
    owner = connection.execute(sa.text(
        "SELECT users.id, memberships.workspace_id FROM users "
        "JOIN memberships ON memberships.user_id = users.id "
        "WHERE users.email = 'gabrirauber@gmail.com' ORDER BY memberships.workspace_id LIMIT 1"
    )).first()
    if owner:
        workspace_id = owner.workspace_id
        existing = connection.execute(sa.text(
            "SELECT id FROM users WHERE email = :email"
        ), {"email": DEMO_EMAIL}).first()
        if existing:
            raise RuntimeError(
                "O e-mail da demonstração já está cadastrado; não é seguro substituí-lo."
            )
        demo_id = identifier("user")
        connection.execute(sa.text(
            "INSERT INTO users (id, email, password_hash, access_status, is_access_admin, "
            "is_demo, requested_at) VALUES (:id, :email, :hash, 'pending', false, true, now())"
        ), {"id": demo_id, "email": DEMO_EMAIL, "hash": DEMO_HASH})
        connection.execute(sa.text(
            "INSERT INTO memberships (workspace_id, user_id, role) "
            "VALUES (:workspace, :user, 'member')"
        ), {"workspace": workspace_id, "user": demo_id})

        # Exemplos no espaço escolhido pelo proprietário, com resultado líquido zero.
        # Os nomes e observações permitem excluí-los facilmente pelo aplicativo.
        account_id = identifier(f"{workspace_id}:account")
        category_id = identifier(f"{workspace_id}:category")
        today = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
        connection.execute(sa.text(
            "INSERT INTO accounts (id, workspace_id, name, kind, opening_balance_cents, opened_on) "
            "VALUES (:id, :workspace, 'Conta de demonstração', 'cash', 0, :today)"
        ), {"id": account_id, "workspace": workspace_id, "today": today})
        connection.execute(sa.text(
            "INSERT INTO categories (id, workspace_id, name, name_key, color, active) "
            "VALUES (:id, :workspace, 'Exemplos (demonstração)', 'exemplos (demonstração)', "
            "'#E9650B', true)"
        ), {"id": category_id, "workspace": workspace_id})
        examples = (("Mercado", 12000), ("Transporte", 8000), ("Casa", 30000))
        connection.execute(sa.text(
            "INSERT INTO movements (id, workspace_id, account_id, kind, amount_cents, "
            "occurred_on, note, created_at) VALUES (:id, :workspace, :account, 'income', "
            "50000, :today, 'Receita de demonstração', now())"
        ), {"id": identifier(f"{workspace_id}:income"), "workspace": workspace_id,
            "account": account_id, "today": today})
        for index, (name, amount) in enumerate(examples):
            sub_id = identifier(f"{workspace_id}:subcategory:{index}")
            movement_id = identifier(f"{workspace_id}:expense:{index}")
            connection.execute(sa.text(
                "INSERT INTO subcategories (id, category_id, name, name_key, active) "
                "VALUES (:id, :category, :name, :key, true)"
            ), {"id": sub_id, "category": category_id, "name": name,
                "key": name.casefold()})
            connection.execute(sa.text(
                "INSERT INTO movements (id, workspace_id, account_id, kind, amount_cents, "
                "occurred_on, note, created_at) VALUES (:id, :workspace, :account, 'expense', "
                ":amount, :today, :note, now())"
            ), {"id": movement_id, "workspace": workspace_id, "account": account_id,
                "amount": amount, "today": today, "note": f"{name} · demonstração"})
            connection.execute(sa.text(
                "INSERT INTO expenses (id, workspace_id, movement_id, category_id, "
                "subcategory_id, payment_method) VALUES (:id, :workspace, :movement, "
                ":category, :subcategory, 'cash')"
            ), {"id": identifier(f"{workspace_id}:expense-row:{index}"),
                "workspace": workspace_id, "movement": movement_id,
                "category": category_id, "subcategory": sub_id})
    op.execute("UPDATE app_metadata SET value = 'e12' WHERE key = 'schema'")


def downgrade():
    connection = op.get_bind()
    owner = connection.execute(sa.text(
        "SELECT memberships.workspace_id FROM users "
        "JOIN memberships ON memberships.user_id = users.id "
        "WHERE users.email = 'gabrirauber@gmail.com' LIMIT 1"
    )).first()
    if owner:
        workspace_id = owner.workspace_id
        account_id = identifier(f"{workspace_id}:account")
        category_id = identifier(f"{workspace_id}:category")
        connection.execute(sa.text("DELETE FROM expenses WHERE workspace_id = :workspace "
                                   "AND category_id = :category"),
                           {"workspace": workspace_id, "category": category_id})
        connection.execute(sa.text("DELETE FROM movements WHERE account_id = :account"),
                           {"account": account_id})
        connection.execute(sa.text("DELETE FROM accounts WHERE id = :account"),
                           {"account": account_id})
        connection.execute(sa.text("DELETE FROM subcategories WHERE category_id = :category"),
                           {"category": category_id})
        connection.execute(sa.text("DELETE FROM categories WHERE id = :category"),
                           {"category": category_id})
    connection.execute(sa.text("DELETE FROM users WHERE id = :id AND is_demo = true"),
                       {"id": identifier("user")})
    op.execute("UPDATE app_metadata SET value = 'e11' WHERE key = 'schema'")
    op.drop_column("users", "is_demo")
