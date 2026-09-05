"""Mapeamento das tabelas padrão do FreeRADIUS.

Estas tabelas são criadas por db/init/00_radius_schema.sql — o Alembic é
configurado (env.py: include_object) para NUNCA gerá-las ou alterá-las.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# SQLite só autoincrementa em INTEGER PRIMARY KEY; nos testes usamos essa variante.
_BigPK = BigInteger().with_variant(Integer, "sqlite")


class RadCheck(Base):
    __tablename__ = "radcheck"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), index=True, default="")
    attribute: Mapped[str] = mapped_column(String(64), default="")
    op: Mapped[str] = mapped_column(String(2), default=":=")
    value: Mapped[str] = mapped_column(String(253), default="")


class RadReply(Base):
    __tablename__ = "radreply"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), index=True, default="")
    attribute: Mapped[str] = mapped_column(String(64), default="")
    op: Mapped[str] = mapped_column(String(2), default="=")
    value: Mapped[str] = mapped_column(String(253), default="")


class RadGroupReply(Base):
    __tablename__ = "radgroupreply"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    groupname: Mapped[str] = mapped_column(String(64), index=True, default="")
    attribute: Mapped[str] = mapped_column(String(64), default="")
    op: Mapped[str] = mapped_column(String(2), default="=")
    value: Mapped[str] = mapped_column(String(253), default="")


class RadGroupCheck(Base):
    __tablename__ = "radgroupcheck"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    groupname: Mapped[str] = mapped_column(String(64), index=True, default="")
    attribute: Mapped[str] = mapped_column(String(64), default="")
    op: Mapped[str] = mapped_column(String(2), default="==")
    value: Mapped[str] = mapped_column(String(253), default="")


class RadUserGroup(Base):
    __tablename__ = "radusergroup"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), index=True, default="")
    groupname: Mapped[str] = mapped_column(String(64), default="")
    priority: Mapped[int] = mapped_column(Integer, default=1)


class RadAcct(Base):
    __tablename__ = "radacct"
    radacctid: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    acctsessionid: Mapped[str] = mapped_column(String(64), default="")
    acctuniqueid: Mapped[str] = mapped_column(String(32), default="")
    username: Mapped[str] = mapped_column(String(64), default="")
    realm: Mapped[str | None] = mapped_column(String(64), default="")
    nasipaddress: Mapped[str] = mapped_column(String(15), default="")
    nasportid: Mapped[str | None] = mapped_column(String(32))
    nasporttype: Mapped[str | None] = mapped_column(String(32))
    acctstarttime: Mapped[datetime | None] = mapped_column(DateTime)
    acctupdatetime: Mapped[datetime | None] = mapped_column(DateTime)
    acctstoptime: Mapped[datetime | None] = mapped_column(DateTime)
    acctinterval: Mapped[int | None] = mapped_column(Integer)
    acctsessiontime: Mapped[int | None] = mapped_column(Integer)
    acctauthentic: Mapped[str | None] = mapped_column(String(32))
    acctinputoctets: Mapped[int | None] = mapped_column(BigInteger)
    acctoutputoctets: Mapped[int | None] = mapped_column(BigInteger)
    calledstationid: Mapped[str] = mapped_column(String(50), default="")
    callingstationid: Mapped[str] = mapped_column(String(50), default="")
    acctterminatecause: Mapped[str] = mapped_column(String(32), default="")
    servicetype: Mapped[str | None] = mapped_column(String(32))
    framedipaddress: Mapped[str] = mapped_column(String(15), default="")


class RadPostAuth(Base):
    __tablename__ = "radpostauth"
    id: Mapped[int] = mapped_column(_BigPK, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), default="")
    pass_: Mapped[str] = mapped_column("pass", String(64), default="")
    reply: Mapped[str] = mapped_column(String(64), default="")
    authdate: Mapped[datetime] = mapped_column(DateTime)
    class_: Mapped[str | None] = mapped_column("class", String(64))


class CmdAcct(Base):
    """Contabilização de comandos (não é schema padrão do FreeRADIUS).

    Preenchida pelo site `default` quando um Accounting-Request traz o comando
    executado num VSA de fabricante. Criada em db/init + migração 0007.
    """

    __tablename__ = "cmd_acct"
    id: Mapped[int] = mapped_column(_BigPK, primary_key=True)
    event_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    nasipaddress: Mapped[str] = mapped_column(String(15), default="", index=True)
    username: Mapped[str] = mapped_column(String(64), default="", index=True)
    callingstationid: Mapped[str] = mapped_column(String(50), default="")
    action: Mapped[str] = mapped_column(String(32), default="")
    command: Mapped[str] = mapped_column(String(512), default="")
    acctsessionid: Mapped[str] = mapped_column(String(64), default="")


class Nas(Base):
    __tablename__ = "nas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nasname: Mapped[str] = mapped_column(String(128), index=True)
    shortname: Mapped[str | None] = mapped_column(String(32))
    type: Mapped[str | None] = mapped_column(String(30), default="other")
    ports: Mapped[int | None] = mapped_column(Integer)
    secret: Mapped[str] = mapped_column(String(60), default="secret")
    server: Mapped[str | None] = mapped_column(String(64))
    community: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(String(200), default="RADIUS Client")
    # Coluna própria do Pulse RADIUS (fora do schema padrão do FreeRADIUS):
    # False => exceção por NAS, ver Equipment.radius_require_message_authenticator.
    require_message_authenticator: Mapped[bool] = mapped_column(Boolean, default=True)
