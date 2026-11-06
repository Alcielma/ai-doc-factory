import psycopg
from fastapi import APIRouter

from app import config
from app.routers import r

router = APIRouter(tags=["Saúde"])


@router.get("/health")
def health():
    with psycopg.connect(config.DATABASE_URL) as conn:
        conn.execute("SELECT 1")
    r.ping()
    return {"status": "ok"}
