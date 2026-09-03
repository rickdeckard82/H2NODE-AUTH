from datetime import datetime
from ipaddress import ip_network

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CidrIn(BaseModel):
    cidr: str = Field(min_length=1, max_length=64)
    note: str | None = Field(default=None, max_length=120)

    @field_validator("cidr")
    @classmethod
    def _valid_cidr(cls, v: str) -> str:
        # aceita "10.0.0.5" (vira /32), "10.0.0.0/24", "2001:db8::/48"
        net = ip_network(v.strip(), strict=False)
        return str(net)


class CidrOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cidr: str
    family: int
    note: str | None


class AuthGroupCreate(BaseModel):
    name: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    description: str | None = Field(default=None, max_length=255)
    cidrs: list[CidrIn] = []


class AuthGroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    description: str | None = Field(default=None, max_length=255)
    cidrs: list[CidrIn] | None = None


class AuthGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    cidrs: list[CidrOut]
    member_count: int = 0
    created_at: datetime
    updated_at: datetime
