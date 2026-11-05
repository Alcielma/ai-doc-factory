import hashlib
from pathlib import Path

import psycopg
import redis
from fastapi import FastAPI, File, HTTPException, UploadFile

from app import config
from app.filas import enfileirar

app = FastAPI(title="Document AI Factory")
r = redis.Redis.from_url(config.REDIS_URL, decode_responses=True)


@app.get("/health")
def health():
    with psycopg.connect(config.DATABASE_URL) as conn:
        conn.execute("SELECT 1")
    r.ping()
    return {"status": "ok"}


@app.post("/lotes")
def criar_lote(arquivo: UploadFile = File(...)):
    dados = arquivo.file.read()
    if not dados.startswith(b"%PDF"):
        raise HTTPException(400, "o arquivo não é um PDF")
    sha = hashlib.sha256(dados).hexdigest()
    with psycopg.connect(config.DATABASE_URL) as conn:
        row = conn.execute(
            "INSERT INTO lote (sha256, nome_arquivo) VALUES (%s, %s) "
            "ON CONFLICT (sha256) DO NOTHING RETURNING id, estado",
            (sha, arquivo.filename or "lote.pdf"),
        ).fetchone()
        if row is None:  # mesmo PDF já enviado: devolve o existente
            id_, estado = conn.execute("SELECT id, estado FROM lote WHERE sha256 = %s", (sha,)).fetchone()
            return {"lote_id": id_, "estado": estado, "existente": True}
        pasta = Path(config.DATA_DIR) / f"lote_{row[0]}"
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / "original.pdf").write_bytes(dados)
    enfileirar(r, config.FILA_SEGMENTAR, {"lote_id": row[0]})
    return {"lote_id": row[0], "estado": row[1], "existente": False}
