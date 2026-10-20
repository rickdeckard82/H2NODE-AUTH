from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import UtcDatetime


class BackupScheduleIn(BaseModel):
    enabled: bool = False
    run_time: str = Field(default="02:30", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    timezone: str = Field(default="America/Sao_Paulo", max_length=64)
    include_accounting: bool = True
    encrypted: bool = True
    keep_count: int = Field(default=7, ge=1, le=365)
    ftp_host: str | None = Field(default=None, max_length=255)
    ftp_port: int = Field(default=21, ge=1, le=65535)
    ftp_user: str | None = Field(default=None, max_length=255)
    # Em branco = mantém a senha já guardada.
    ftp_password: str | None = Field(default=None, max_length=255)
    clear_ftp_password: bool = False
    ftp_directory: str | None = Field(default=None, max_length=500)
    ftp_tls: bool = True
    ftp_write_only: bool = False

    @field_validator("ftp_host", "ftp_user", "ftp_directory")
    @classmethod
    def _blank_to_none(cls, v: str | None) -> str | None:
        return (v or "").strip() or None

    @field_validator("timezone")
    @classmethod
    def _valid_timezone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("fuso horário inválido") from exc
        return v


class BackupScheduleOut(BaseModel):
    enabled: bool
    run_time: str
    timezone: str
    include_accounting: bool
    encrypted: bool
    keep_count: int
    ftp_host: str | None
    ftp_port: int
    ftp_user: str | None
    has_ftp_password: bool
    ftp_directory: str | None
    ftp_tls: bool
    ftp_write_only: bool
    run_requested_at: UtcDatetime | None
    last_attempt_at: UtcDatetime | None
    last_success_at: UtcDatetime | None
    last_status: str | None
    last_message: str | None
    next_run_at: UtcDatetime | None
