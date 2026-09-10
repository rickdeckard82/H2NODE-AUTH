from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.common import UtcDatetime

# Usados quando ainda não há linha de configuração no banco.
DEFAULT_ORG_NAME = "a organização operadora deste sistema"
DEFAULT_DPO_EMAIL = "privacidade@example.com"

_Days = Field(default=0, ge=0, le=36500)  # 0 = sem exclusão automática


class LgpdSettingsIn(BaseModel):
    org_name: str = Field(min_length=1, max_length=190)
    dpo_email: EmailStr
    accounting_retention_days: int = _Days
    audit_retention_days: int = _Days
    auth_user_retention_days: int = _Days


class LgpdSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    org_name: str
    dpo_email: str
    accounting_retention_days: int
    audit_retention_days: int
    auth_user_retention_days: int
    last_purge_at: UtcDatetime | None = None
    updated_at: UtcDatetime | None = None


class LegalNoticeOut(BaseModel):
    """Campos públicos exibidos no Aviso de Privacidade (/privacidade)."""

    model_config = ConfigDict(from_attributes=True)

    org_name: str
    dpo_email: str
    accounting_retention_days: int
    audit_retention_days: int
    auth_user_retention_days: int
    updated_at: UtcDatetime | None = None
