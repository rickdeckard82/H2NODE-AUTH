"""Worker do backup automático por FTP (container `backup-worker`).

A cada BACKUP_WORKER_INTERVAL_SECONDS consulta a linha de `app_backup_schedule`
e roda o backup se estiver no horário ou se o painel pediu "Executar agora".
Também roda o expurgo diário de retenção LGPD (services/retention.py).
Uso: python -m app.backup_worker
"""

import os
import signal
import time

from sqlalchemy import inspect

from app.core.db import SessionLocal, engine
from app.core.logging import configure_logging, logger
from app.services import backup_ftp, retention

running = True


def _stop(signum, frame) -> None:
    global running
    running = False


def _sleep(seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while running and time.monotonic() < deadline:
        time.sleep(min(5, max(0, deadline - time.monotonic())))


def _wait_for_schema(interval: int) -> None:
    """O backend aplica as migrações no boot; espera a tabela existir."""
    while running:
        try:
            if "app_backup_schedule" in inspect(engine).get_table_names():
                return
            logger.info("backup_worker_waiting_schema")
        except Exception as exc:  # noqa: BLE001 - banco ainda subindo
            logger.info("backup_worker_waiting_db", error=str(exc))
        _sleep(min(interval, 10))


def main() -> None:
    configure_logging()
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    # Curto para o "Executar agora" responder logo; a rodada só lê uma linha.
    interval = int(os.getenv("BACKUP_WORKER_INTERVAL_SECONDS", "30"))

    _wait_for_schema(interval)
    leftovers = backup_ftp.clean_leftovers()
    if leftovers:
        logger.warning("backup_worker_cleaned_leftovers", count=leftovers)
    with SessionLocal() as db:
        if backup_ftp.recover_interrupted(db):
            logger.warning("backup_worker_recovered_interrupted_run")
    logger.info("backup_worker_started", interval=interval)

    while running:
        db = SessionLocal()
        try:
            backup_ftp.execute(db, engine)
            retention.run_if_due(db)  # expurgo LGPD (no-op fora da janela de 24h)
        except Exception:  # noqa: BLE001 - o loop nunca morre
            logger.exception("backup_worker_loop_failed")
            db.rollback()
        finally:
            db.close()
        _sleep(interval)
    logger.info("backup_worker_stopped")


if __name__ == "__main__":
    main()
