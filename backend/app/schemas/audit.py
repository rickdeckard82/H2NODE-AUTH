from pydantic import BaseModel, ConfigDict

from app.schemas.common import UtcDatetime


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: UtcDatetime
    actor_username: str | None
    action: str
    entity_type: str
    entity_id: str | None
    ip_address: str | None
    before_json: str | None
    after_json: str | None


class TrustedDeviceRow(BaseModel):
    """Dispositivo confiável de 2FA (visão global, para a auditoria)."""

    id: int
    username: str | None
    user_agent: str | None
    ip_address: str | None
    created_at: UtcDatetime
    last_used_at: UtcDatetime | None
    expires_at: UtcDatetime
    expired: bool
