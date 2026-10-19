from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import Settings


class Base(DeclarativeBase):
    pass


class AppMetadata(Base):
    """Metadados técnicos; nenhum cadastro financeiro é criado na E02."""

    __tablename__ = "app_metadata"
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(String(100))


def build_engine(settings: Settings):
    return create_engine(
        settings.sqlalchemy_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_timeout=3,
        connect_args={"connect_timeout": 3, "options": "-c statement_timeout=3000"},
        hide_parameters=True,
    )


def database_ready(engine, require_access_admin: bool = False) -> bool:
    with engine.connect() as connection:
        version = connection.scalar(select(AppMetadata.value).where(AppMetadata.key == "schema"))
        if version != "e15":
            return False
        if require_access_admin:
            from app.identity.models import User

            admin_id = connection.scalar(
                select(User.id).where(
                    User.email == "gabrirauber@gmail.com",
                    User.is_access_admin.is_(True),
                    User.access_status == "approved",
                ).limit(1)
            )
            return admin_id is not None
        return True
