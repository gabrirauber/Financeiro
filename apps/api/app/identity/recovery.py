import logging
import secrets
import smtplib
import ssl
from datetime import timedelta
from email.message import EmailMessage

from fastapi import APIRouter, HTTPException, Request
from pydantic import Field, SecretStr
from sqlalchemy import delete, select

from app.identity.auth import EmailInput, PasswordInput, normalize
from app.identity.dependencies import Db
from app.identity.models import LoginSession, PasswordReset, User
from app.identity.security import digest, now, passwords, throttle

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)
GENERIC_MESSAGE = "Se o e-mail estiver cadastrado, você receberá um link de recuperação."


class ResetInput(PasswordInput):
    # Reutiliza a validação de senha, sem exigir e-mail na confirmação.

    token: SecretStr = Field(min_length=32, max_length=128)


def smtp_sender(settings, email: str, link: str):
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = email
    message["Subject"] = "Recuperação de acesso — Rautto"
    message.set_content(
        "Use o link abaixo para definir uma nova senha. Ele expira em 15 minutos "
        "e só pode ser usado uma vez. Se não solicitou, ignore esta mensagem.\n\n" + link
    )
    with smtplib.SMTP_SSL(
        settings.smtp_host, settings.smtp_port, timeout=10, context=ssl.create_default_context()
    ) as smtp:
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password.get_secret_value())
        smtp.send_message(message)


@router.post("/password-reset/request")
def request_reset(data: EmailInput, request: Request, db: Db):
    settings = request.app.state.settings
    sender = getattr(request.app.state, "reset_sender", None)
    if sender is None and not (settings.smtp_host and settings.smtp_from):
        raise HTTPException(503, "Recuperação por e-mail ainda não configurada.")
    email = normalize(data.email)
    throttle(db, "reset-ip:", request.client.host if request.client else "unknown", 30)
    throttle(db, "reset-email:", email, 5)
    user = db.scalar(select(User).where(User.email == email).with_for_update())
    if user:
        token = secrets.token_urlsafe(32)
        db.execute(delete(PasswordReset).where(PasswordReset.user_id == user.id))
        reset = PasswordReset(
            token_hash=digest(token), user_id=user.id, expires_at=now() + timedelta(minutes=15)
        )
        db.add(reset)
        db.commit()
        link = settings.password_reset_url.rstrip("#") + "#reset=" + token
        try:
            if sender:
                sender(email, link)
            else:
                smtp_sender(settings, email, link)
        except Exception:
            # Manter resposta neutra e não registrar link, token ou endereço.
            db.execute(delete(PasswordReset).where(PasswordReset.token_hash == digest(token)))
            db.commit()
            logger.warning("Não foi possível entregar uma mensagem de recuperação")
    return {"message": GENERIC_MESSAGE}


@router.post("/password-reset/confirm", status_code=204)
def confirm_reset(data: ResetInput, db: Db):
    token_hash = digest(data.token.get_secret_value())
    candidate = db.get(PasswordReset, token_hash)
    if not candidate:
        raise HTTPException(400, "Link inválido ou expirado.")
    user = db.scalar(select(User).where(User.id == candidate.user_id).with_for_update())
    reset = db.scalar(
        select(PasswordReset)
        .where(PasswordReset.token_hash == token_hash)
        .execution_options(populate_existing=True)
        .with_for_update()
    )
    if not user or not reset or reset.expires_at <= now():
        raise HTTPException(400, "Link inválido ou expirado.")
    user.password_hash = passwords.hash(data.password.get_secret_value())
    db.execute(delete(PasswordReset).where(PasswordReset.user_id == user.id))
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    db.commit()
