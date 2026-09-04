"""Backup e restauração lógica do banco (dump SQL em Python puro).

Gera um `.sql` restaurável só com o driver pymysql — não precisa do binário
`mysqldump`/`mysql` na imagem do backend. Cobre TODAS as tabelas do schema
(RADIUS + painel + `alembic_version`), preservando o DDL exato via
`SHOW CREATE TABLE`.

Só funciona em MySQL/MariaDB. Não inclui os segredos do `.env`
(`JWT_SECRET`, `FERNET_KEY`, senhas do MySQL): restaurar num stack com
`FERNET_KEY` diferente torna ilegíveis os segredos RADIUS dos equipamentos.
"""

from __future__ import annotations

import datetime as _dt
import struct
from collections.abc import Iterator

import pymysql.cursors
from sqlalchemy.engine import Engine

from app.core.crypto import decrypt, encrypt

# Primeira linha do arquivo — usada para validar o upload na restauração.
MARKER = "-- Pulse RADIUS backup v1"

# Cabeçalho do formato cifrado (ver encrypt_stream/decrypt_to_text). Nunca
# colide com MARKER: dumps em claro sempre começam com "--".
ENC_MAGIC = b"PULSEENC1\n"

# Separador de instruções. Os literais gerados pelo pymysql nunca contêm
# quebra de linha crua (\n vira \\n), então este sentinela só aparece nos
# limites reais de instrução — split seguro na restauração.
_STMT_SEP = "\n-- @@PULSE_STMT@@\n"

# Histórico volumoso, omitido quando o operador desmarca "incluir accounting".
_HISTORY_TABLES = {"radacct", "radpostauth"}

_ROWS_PER_INSERT = 400


class BackupError(RuntimeError):
    """Falha de backup/restauração (dialeto não suportado, arquivo inválido…)."""


def _require_mysql(engine: Engine) -> None:
    if engine.dialect.name != "mysql":
        raise BackupError("backup/restauração só é suportado em MySQL")


def _base_tables(cursor) -> list[str]:
    cursor.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
    return sorted(row[0] for row in cursor.fetchall())


def _literal(conn, value: object) -> str:
    if value is None:
        return "NULL"
    # pymysql.Connection.escape cobre str/bytes/int/float/Decimal/datetime/date
    # e devolve o valor já entre aspas quando necessário.
    return conn.escape(value)


def _dump_table(conn, raw, table: str) -> Iterator[str]:
    meta = raw.cursor()
    try:
        meta.execute(f"SHOW CREATE TABLE `{table}`")
        ddl = meta.fetchone()[1]
    finally:
        meta.close()

    yield f"DROP TABLE IF EXISTS `{table}`;{_STMT_SEP}"
    yield f"{ddl};{_STMT_SEP}"

    rows = conn.cursor(pymysql.cursors.SSCursor)  # server-side: não carrega tudo na RAM
    try:
        rows.execute(f"SELECT * FROM `{table}`")
        if rows.description is None:
            return
        collist = ",".join(f"`{d[0]}`" for d in rows.description)
        batch: list[str] = []
        for row in rows:
            batch.append("(" + ",".join(_literal(conn, v) for v in row) + ")")
            if len(batch) >= _ROWS_PER_INSERT:
                yield f"INSERT INTO `{table}` ({collist}) VALUES {','.join(batch)};{_STMT_SEP}"
                batch = []
        if batch:
            yield f"INSERT INTO `{table}` ({collist}) VALUES {','.join(batch)};{_STMT_SEP}"
    finally:
        rows.close()


def dump_sql(
    engine: Engine,
    *,
    include_accounting: bool = True,
    schema_version: str | None = None,
) -> Iterator[str]:
    """Gera o dump SQL preguiçosamente (para `StreamingResponse`)."""
    _require_mysql(engine)
    raw = engine.raw_connection()
    try:
        conn = raw.driver_connection  # pymysql.Connection
        meta = raw.cursor()
        try:
            tables = _base_tables(meta)
        finally:
            meta.close()
        if not include_accounting:
            tables = [t for t in tables if t not in _HISTORY_TABLES]

        generated = _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds")
        yield (
            f"{MARKER}\n"
            f"-- generated_at: {generated}\n"
            f"-- schema_version: {schema_version or 'unknown'}\n"
            f"-- include_accounting: {int(include_accounting)}\n"
            f"-- tables: {len(tables)}\n"
            f"SET NAMES utf8mb4;{_STMT_SEP}"
        )
        yield f"SET FOREIGN_KEY_CHECKS=0;{_STMT_SEP}"
        yield f"SET UNIQUE_CHECKS=0;{_STMT_SEP}"
        yield f"SET SESSION sql_mode='NO_AUTO_VALUE_ON_ZERO';{_STMT_SEP}"
        for table in tables:
            yield from _dump_table(conn, raw, table)
        yield f"SET UNIQUE_CHECKS=1;{_STMT_SEP}"
        yield f"SET FOREIGN_KEY_CHECKS=1;{_STMT_SEP}"
        yield "-- restore complete\n"
    finally:
        raw.close()


def _statements(sql_text: str) -> Iterator[str]:
    for chunk in sql_text.split(_STMT_SEP):
        body = "\n".join(
            ln for ln in chunk.splitlines() if not ln.lstrip().startswith("--")
        ).strip()
        if body:
            yield body.rstrip(";").strip() if body.endswith(";") else body


def restore_sql(engine: Engine, sql_text: str, *, current_version: str | None = None) -> dict:
    """Executa o dump. DESTRUTIVO: dropa e recria cada tabela do arquivo.

    DDL faz commit implícito no MySQL — uma falha no meio deixa o banco
    parcialmente restaurado. O chamador já exige confirmação explícita.
    """
    _require_mysql(engine)
    if not sql_text.lstrip().startswith(MARKER):
        raise BackupError("arquivo não é um backup do Pulse RADIUS")

    dump_version: str | None = None
    for ln in sql_text.splitlines()[:6]:
        if ln.startswith("-- schema_version:"):
            dump_version = ln.split(":", 1)[1].strip()
            break

    raw = engine.raw_connection()
    applied = 0
    try:
        cur = raw.cursor()
        cur.execute("SET SESSION FOREIGN_KEY_CHECKS=0")
        cur.execute("SET SESSION UNIQUE_CHECKS=0")
        for i, stmt in enumerate(_statements(sql_text), start=1):
            try:
                cur.execute(stmt)
            except Exception as exc:  # noqa: BLE001 - reembrulha com o índice
                raise BackupError(f"falha na instrução {i}: {exc}") from exc
            applied += 1
        cur.execute("SET SESSION FOREIGN_KEY_CHECKS=1")
        cur.execute("SET SESSION UNIQUE_CHECKS=1")
        raw.commit()
    finally:
        raw.close()

    result: dict = {"statements": applied, "dump_schema_version": dump_version}
    if dump_version and current_version and dump_version != current_version:
        result["warning"] = (
            f"o backup foi gerado no schema {dump_version}, mas o código atual está "
            f"em {current_version}. Rode as migrações (alembic upgrade head) após restaurar."
        )
    return result


def encrypt_stream(chunks: Iterator[str]) -> Iterator[bytes]:
    """Cifra o dump em blocos com a FERNET_KEY do servidor (streaming, sem
    carregar o arquivo inteiro em memória). Formato: ENC_MAGIC + repetição de
    (uint32 big-endian com o tamanho do token, token Fernet)."""
    yield ENC_MAGIC
    for chunk in chunks:
        if not chunk:
            continue
        token = encrypt(chunk).encode("ascii")
        yield struct.pack(">I", len(token)) + token


def is_encrypted(data: bytes) -> bool:
    return data.startswith(ENC_MAGIC)


def decrypt_to_text(data: bytes) -> str:
    if not data.startswith(ENC_MAGIC):
        raise BackupError("arquivo não está no formato cifrado esperado")
    buf = data[len(ENC_MAGIC):]
    parts: list[str] = []
    pos = 0
    while pos < len(buf):
        if pos + 4 > len(buf):
            raise BackupError("backup cifrado corrompido (cabeçalho de bloco incompleto)")
        (length,) = struct.unpack(">I", buf[pos:pos + 4])
        pos += 4
        token = buf[pos:pos + length]
        if len(token) != length:
            raise BackupError("backup cifrado corrompido (bloco truncado)")
        pos += length
        try:
            parts.append(decrypt(token.decode("ascii")))
        except Exception as exc:  # noqa: BLE001 - Fernet levanta InvalidToken/etc.
            raise BackupError(
                "não foi possível decifrar o backup — FERNET_KEY diferente da usada no export?"
            ) from exc
    return "".join(parts)
