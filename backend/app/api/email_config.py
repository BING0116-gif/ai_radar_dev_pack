"""Email SMTP configuration API (Settings page -> gitignored local file).

写一个独立页面入口，让用户在 UI 里配置 SMTP 并立即可测：
- ``GET  /api/email-config``: 当前生效配置（不回显密码）
- ``PUT  /api/email-config``: 保存到 ``<WORKSPACE>/email_settings.json``（不入库）
- ``POST /api/email-config/test``: 发一封测试邮件（未配置时落 DEMO .eml）
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.common import ApiError, ApiResponse, ok
from app.schemas.email_config import (
    EmailConfigPayload,
    EmailConfigResponse,
    EmailTestResult,
)

router = APIRouter(prefix="/api", tags=["email-config"])


def _as_response(config: dict) -> EmailConfigResponse:
    from app.services import email_settings as store

    return EmailConfigResponse(
        host=config.get("host", ""),
        port=int(config.get("port") or 465),
        user=config.get("user", ""),
        sender=config.get("from", ""),
        recipient=config.get("to", ""),
        configured=store.is_fully_configured(config),
    )


@router.get("/email-config", response_model=ApiResponse[EmailConfigResponse])
def get_email_config(db: Session = Depends(get_db)) -> ApiResponse[EmailConfigResponse]:
    from app.services import email_settings as store

    return ok(_as_response(store.load_email_config()))


@router.put("/email-config", response_model=ApiResponse[EmailConfigResponse])
def put_email_config(
    payload: EmailConfigPayload, db: Session = Depends(get_db)
) -> ApiResponse[EmailConfigResponse]:
    from app.services import email_settings as store

    stored = {
        "host": payload.host,
        "port": payload.port,
        "user": payload.user,
        "password": payload.password,
        "from": payload.sender,
        "to": payload.recipient,
    }
    try:
        store.save_email_config(stored)
    except OSError as exc:  # e.g. volume read-only
        raise ApiError(f"failed to save email config: {exc}", code=50201, status_code=500) from exc
    return ok(_as_response(stored))


@router.post("/email-config/test", response_model=ApiResponse[EmailTestResult])
def test_email_config(
    payload: EmailConfigPayload, db: Session = Depends(get_db)
) -> ApiResponse[EmailTestResult]:
    """Send a test email with the submitted settings (real SMTP or DEMO)."""
    from app.services import email_settings as store
    from app.tools.notify import EmailNotifier, NotifyError

    stored = {
        "host": payload.host,
        "port": payload.port,
        "user": payload.user,
        "password": payload.password,
        "from": payload.sender,
        "to": payload.recipient,
    }
    notifier = EmailNotifier(config=stored)
    detail = "邮件已通过 SMTP 发出，请查收"
    if not notifier.is_configured():
        imported = store.load_email_config()
        notifier = EmailNotifier(config=imported)
        if not notifier.is_configured():
            notifier = EmailNotifier()
            notifier.send("这是一封测试邮件：AI Radar 邮件自动推送已就绪。", subject="AI Radar 邮件推送测试")
            store.save_email_config(stored)  # 保留用户填写内容，用于后续配置
            return ok(EmailTestResult(
                sent=True, mode="demo",
                detail="尚未配置 SMTP：已生成演示邮件（见 workspace/emails/）。填齐发件/收件邮箱后重试即真实发送",
            ))
    try:
        notifier.send("这是一封测试邮件：AI Radar 邮件自动推送已就绪。", subject="AI Radar 邮件推送测试")
    except NotifyError as exc:
        raise ApiError(str(exc), code=50202, status_code=502) from exc
    store.save_email_config(stored)
    return ok(EmailTestResult(sent=True, mode="smtp", detail=detail))