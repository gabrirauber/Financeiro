"""Executar diariamente em um agendamento do servidor: python -m app.finance.run_recurring."""

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import build_engine
from app.finance.income_plans import generate_month as generate_income_month
from app.finance.recurrences import generate_month
from app.identity.models import Workspace


def run(engine):
    with Session(engine) as db:
        workspace_ids = db.scalars(select(Workspace.id)).all()
    for workspace_id in workspace_ids:
        with Session(engine) as db:
            workspace = db.scalar(
                select(Workspace).where(Workspace.id == workspace_id).with_for_update()
            )
            current = datetime.now(ZoneInfo(workspace.timezone)).date()
            generate_month(db, workspace_id, current.replace(day=1), current)
            generate_income_month(db, workspace_id, current.replace(day=1))
            db.commit()


def main():
    engine = build_engine(Settings())
    try:
        run(engine)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
