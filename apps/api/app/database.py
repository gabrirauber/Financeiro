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


def database_ready(engine) -> bool:
    with engine.connect() as connection:
        version = connection.scalar(select(AppMetadata.value).where(AppMetadata.key == "schema"))
        return version == "e08"
