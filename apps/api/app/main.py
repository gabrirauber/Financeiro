import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from typing import Literal

from fastapi import FastAPI, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings
from app.database import build_engine, database_ready
from app.finance import advances, cards, categories, expenses, financing, income_plans, recurrences
from app.finance import routes as finance
from app.finance.run_recurring import run as run_recurring
from app.identity import auth, invites, recovery, workspaces
from app.validation import validation_message

logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    database: Literal["ready", "unavailable"]
    stage: Literal["E08"] = "E08"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = build_engine(settings)

    @asynccontextmanager
    async def lifespan(app):
        async def schedule_recurrences():
            while True:
                try:
                    await asyncio.to_thread(run_recurring, engine)
                except SQLAlchemyError:
                    logger.warning("Não foi possível gerar as ocorrências mensais")
                await asyncio.sleep(3600)

        task = asyncio.create_task(schedule_recurrences()) if settings.app_env != "test" else None
        try:
            yield
        finally:
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
            engine.dispose()

    app = FastAPI(
        title="Financeiro API",
        version="0.8.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.app_env != "production" else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Accept", "Content-Type", "Authorization"],
    )
    app.state.engine = engine
    app.state.settings = settings
    app.include_router(auth.router)
    app.include_router(workspaces.router)
    app.include_router(invites.router)
    app.include_router(recovery.router)
    app.include_router(finance.router)
    app.include_router(categories.router)
    app.include_router(expenses.router)
    app.include_router(cards.router)
    app.include_router(financing.router)
    app.include_router(advances.router)
    app.include_router(recurrences.router)
    app.include_router(income_plans.router)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Não devolver input (que pode conter senha) na resposta de validação.
        errors = [
            {"field": ".".join(str(x) for x in error["loc"]), "message": validation_message(error)}
            for error in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": errors})

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        logger.warning("Operação indisponível por falha no banco")
        return JSONResponse(
            status_code=503, content={"detail": "Serviço indisponível. Tente novamente."}
        )

    @app.get("/health/live")
    def live():
        return {"status": "ok", "stage": "E08"}

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
