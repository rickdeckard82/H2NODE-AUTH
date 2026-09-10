"""Gera a config de equipamentos + perfis do tac_plus-ng a partir do banco.

Usuários/senha/grupo são resolvidos pelo MAVIS em tempo de request; aqui só
materializamos o que precisa viver no arquivo de config: os `host` (clientes
TACACS+) e os `profile`/`ruleset` (autorização por nível). O container tacacs
recarrega (SIGHUP) quando este arquivo muda.
"""

import contextlib
import os
import re
import tempfile

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import decrypt
from app.models import Equipment, Manufacturer, PrivilegeProfile
from app.models.manufacturer import AaaProtocol

_AVPAIR_KEY = re.compile(r"^[A-Za-z0-9:_.\-]+$")


def resolve_protocol(eq: Equipment, manufacturer: Manufacturer) -> AaaProtocol:
    return eq.aaa_protocol or manufacturer.aaa_protocol


def resolve_tacacs_key(eq: Equipment, manufacturer: Manufacturer) -> str:
    enc = eq.tacacs_key_enc or manufacturer.tacacs_key_enc
    if not enc:
        raise ValueError(
            "Sem chave TACACS+: informe uma no equipamento ou no grupo "
            f"'{manufacturer.name}'."
        )
    return decrypt(enc)


def _q(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _profile_block(p: PrivilegeProfile) -> str:
    lvl = max(0, min(15, p.tacacs_priv_level or 0))
    sets = [f"            set priv-lvl = {lvl}"]
    for raw in (p.tacacs_extra_avpairs or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        if _AVPAIR_KEY.match(k):
            sets.append(f"            set {k} = {_q(v.strip())}")
    sets_txt = "\n".join(sets)
    # priv-lvl + AV pairs (ex.: local-user-name p/ Junos) valem para a autorização
    # de login/exec — `cmd` vazio — de qualquer serviço (shell, junos-exec, …).
    # Autorização de comando (`cmd` preenchido) é apenas permitida.
    return (
        f"profile {p.name} {{\n"
        f"    script {{\n"
        f"        if (cmd == \"\") {{\n"
        f"{sets_txt}\n"
        f"            permit\n"
        f"        }}\n"
        f"        permit\n"
        f"    }}\n"
        f"}}\n"
    )


def build_config(db: Session) -> tuple[str, int]:
    """(texto da config, nº de hosts TACACS+)."""
    rows = db.execute(
        select(Equipment, Manufacturer).join(
            Manufacturer, Manufacturer.id == Equipment.manufacturer_id
        )
    ).all()

    hosts: list[str] = []
    for eq, mfr in rows:
        if resolve_protocol(eq, mfr) != AaaProtocol.tacacs:
            continue
        try:
            key = resolve_tacacs_key(eq, mfr)
        except ValueError:
            continue  # sem chave => não vira cliente (o painel bloqueia salvar assim)
        hosts.append(
            f"host eq_{eq.id} {{\n"
            f"    address = {eq.mgmt_ip}\n"
            f"    key = {_q(key)}\n"
            f"}}\n"
        )

    profiles = list(db.execute(select(PrivilegeProfile)).scalars())
    # `member == "x"` no ruleset exige `group x` declarado; o MAVIS devolve
    # TACMEMBER = nome do perfil.
    group_blocks = "".join(f"group {p.name} {{ }}\n" for p in profiles)
    profile_blocks = "\n".join(_profile_block(p) for p in profiles)
    rules = "\n".join(
        f'            if (member == "{p.name}") {{ profile = {p.name}  permit }}'
        for p in profiles
    )
    ruleset = (
        "ruleset {\n"
        "    rule pulse {\n"
        "        enabled = yes\n"
        "        script {\n"
        f"{rules}\n"
        "            deny\n"
        "        }\n"
        "    }\n"
        "}\n"
    )

    text = (
        "# GERADO pelo painel (app/services/tacacs_sync.py) — não editar à mão.\n"
        f"{''.join(hosts)}\n{group_blocks}\n{profile_blocks}\n{ruleset}"
    )
    return text, len(hosts)


def regenerate(db: Session) -> int:
    """Reescreve o arquivo de config. No-op se TACACS_HOSTS_PATH não estiver setado."""
    path = settings.tacacs_hosts_path
    if not path:
        return 0
    text, n = build_config(db)
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".pulse-tacacs-")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(text)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise
    return n
