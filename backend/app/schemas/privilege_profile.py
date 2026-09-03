from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProfileAttrIn(BaseModel):
    manufacturer_id: int
    attribute: str = Field(min_length=1, max_length=64)
    op: str = Field(default=":=", max_length=2)
    value: str = Field(min_length=1, max_length=253)


class ProfileAttrOut(ProfileAttrIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class PrivilegeProfileCreate(BaseModel):
    name: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    description: str | None = Field(default=None, max_length=255)
    attrs: list[ProfileAttrIn] = []


class PrivilegeProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    description: str | None = Field(default=None, max_length=255)
    attrs: list[ProfileAttrIn] | None = None


class PrivilegeProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    is_builtin: bool
    group_name: str
    attrs: list[ProfileAttrOut]
    created_at: datetime
    updated_at: datetime
