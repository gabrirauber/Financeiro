import logging
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings
from app.database import build_engine, database_ready

logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    database: Literal["ready", "unavailable"]
    stage: Literal["E02"] = "E02"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = build_engine(settings)

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.dispose()

    app = FastAPI(
        title="Financeiro API",
        version="0.2.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.app_env != "production" else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept"],
    )
    app.state.engine = engine

    @app.get("/health/live")
    def live():
        return {"status": "ok", "stage": "E02"}

    @app.get("/health/ready", response_model=HealthResponse)
    def ready(response: Response):
        response.headers["Cache-Control"] = "no-store"
        try:
            healthy = database_ready(engine)
        except SQLAlchemyError:
            # Não vazar host, usuário, senha ou SQL em respostas ou logs.
            logger.warning("Banco indisponível no diagnóstico de prontidão")
            healthy = False
        if not healthy:
            response.status_code = 503
        return HealthResponse(
            status="ok" if healthy else "unavailable",
            database="ready" if healthy else "unavailable",
        )

    return app
