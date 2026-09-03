from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    actor_username: str | None
    action: str
    entity_type: str
    entity_id: str | None
    ip_address: str | None
    before_json: str | None
    after_json: str | None
