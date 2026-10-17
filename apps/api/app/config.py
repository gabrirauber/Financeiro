from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    app_env: Literal["development", "test", "production"] = "development"
    access_approval_enabled: bool = False
    database_url: SecretStr
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_from: str = ""
    smtp_user: str = ""
    smtp_password: SecretStr = SecretStr("")
    password_reset_url: str = "http://localhost:8081/"
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

    @model_validator(mode="after")
    def recovery_config(self):
        from urllib.parse import urlsplit

        url = urlsplit(self.password_reset_url)
        if url.fragment or url.query:
            raise ValueError("PASSWORD_RESET_URL não deve conter query ou fragmento")
        if self.app_env == "production" and self.smtp_host:
            native_link = url.scheme == "financeiro" and url.netloc == "reset"
            web_link = (
                url.scheme == "https"
                and url.hostname
                and url.hostname not in {"localhost", "127.0.0.1"}
            )
            if not (native_link or web_link):
                raise ValueError("Recuperação exige HTTPS público ou financeiro://reset")
        return self

    @property
    def sqlalchemy_url(self):
        return make_url(self.database_url.get_secret_value()).set(drivername="postgresql+psycopg")

    @property
    def approval_required(self) -> bool:
        return self.app_env == "production" or self.access_approval_enabled
