"""Email SMTP configuration schemas (UI-driven, praised outside the DB)."""

from pydantic import BaseModel, Field, field_validator


class EmailConfigPayload(BaseModel):
    """PUT /api/email-config body. ``password`` 仅用于写入本地文件，绝不回显。"""

    host: str = Field(default="", description="SMTP 服务器，如 smtp.qq.com")
    port: int = Field(default=465, ge=1, le=65535)
    user: str = ""
    password: str = ""
    sender: str = Field(default="", description="发件人邮箱")
    recipient: str = Field(default="", description="收件人邮箱（可多个，逗号分隔）")

    @field_validator("host", "user", "sender", "recipient")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class EmailConfigResponse(BaseModel):
    """GET /api/email-config / after save: never includes the password."""

    host: str = ""
    port: int = 465
    user: str = ""
    sender: str = ""
    recipient: str = ""
    configured: bool = False  # True = 下次简报/测试邮件走真实 SMTP


class EmailTestResult(BaseModel):
    sent: bool
    mode: str  # smtp | demo
    detail: str