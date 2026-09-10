from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services import retention

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    # gancho oportunista do expurgo LGPD (no-op fora da janela de 24h; nunca levanta)
    retention.run_if_due(db)
    return {"status": "ok"}
