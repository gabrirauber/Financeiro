from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    app_env: Literal["development", "test", "production"] = "development"
    database_url: SecretStr
    cors_origins: list[str] = ["http://localhost:8081", "http://127.0.0.1:8081"]

    @field_validator("database_url")
    @classmethod
    def require_postgres(cls, value: SecretStr) -> SecretStr:
        # Não incluir a URL/credencial na mensagem de erro.
        try:
            driver = make_url(value.get_secret_value()).drivername
        except Exception:
            raise ValueError("DATABASE_URL inválida") from None
        if driver not in {"postgres", "postgresql", "postgresql+psycopg"}:
            raise ValueError("DATABASE_URL deve apontar para PostgreSQL")
        return value

    @property
    def sqlalchemy_url(self):
        return make_url(self.database_url.get_secret_value()).set(
            drivername="postgresql+psycopg"
        )
