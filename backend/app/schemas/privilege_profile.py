import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def cmd_allow_lines(text: str | None) -> list[tuple[int, str]]:
    """(nº da linha, regex) de tacacs_cmd_allow, sem vazias nem comentários."""
    return [
        (n, line) for n, line in enumerate((text or "").splitlines(), 1)
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _check_cmd_allow(text: str | None) -> str | None:
    for n, rx in cmd_allow_lines(text):
        # `"` e `/` sem `\` fecham o `cmd =~ /.../` do tac_plus-ng antes da hora.
        esc = False
        for ch in rx:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch in '"/':
                raise ValueError(f"linha {n}: escape o caractere {ch} como \\{ch}")
        if esc:
            raise ValueError(f"linha {n}: termina com \\ solto")
        try:
            re.compile(rx)
        except re.error as exc:
            raise ValueError(f"linha {n}: regex inválida ({exc})") from exc
    return text


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
    tacacs_priv_level: int = Field(default=1, ge=0, le=15)
    tacacs_extra_avpairs: str | None = Field(default=None, max_length=2000)
    tacacs_enable_level: int | None = Field(default=None, ge=0, le=15)
    tacacs_cmd_allow: str | None = Field(default=None, max_length=4000)

    _cmd_allow = field_validator("tacacs_cmd_allow")(_check_cmd_allow)


class PrivilegeProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    description: str | None = Field(default=None, max_length=255)
    attrs: list[ProfileAttrIn] | None = None
    tacacs_priv_level: int | None = Field(default=None, ge=0, le=15)
    tacacs_extra_avpairs: str | None = Field(default=None, max_length=2000)
    # nulo explícito volta ao padrão (igual ao priv-lvl); ausente = não mexe
    tacacs_enable_level: int | None = Field(default=None, ge=0, le=15)
    tacacs_cmd_allow: str | None = Field(default=None, max_length=4000)

    _cmd_allow = field_validator("tacacs_cmd_allow")(_check_cmd_allow)


class PrivilegeProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    is_builtin: bool
    group_name: str
    attrs: list[ProfileAttrOut]
    tacacs_priv_level: int
    tacacs_extra_avpairs: str | None
    tacacs_enable_level: int | None
    tacacs_cmd_allow: str | None
    created_at: datetime
    updated_at: datetime
