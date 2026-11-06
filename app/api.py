import hashlib
from pathlib import Path

import psycopg
import redis
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

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
            if estado == "recebido":
                # o enfileirar pode ter falhado no envio original; job duplicado é aceitável
                # porque os handlers são idempotentes
                enfileirar(r, config.FILA_SEGMENTAR, {"lote_id": id_})
            return {"lote_id": id_, "estado": estado, "existente": True}
        pasta = Path(config.DATA_DIR) / f"lote_{row[0]}"
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / "original.pdf").write_bytes(dados)
    enfileirar(r, config.FILA_SEGMENTAR, {"lote_id": row[0]})
    return {"lote_id": row[0], "estado": row[1], "existente": False}


# A expressão to_tsvector('portuguese', coalesce(texto, '')) precisa ser idêntica à do índice pagina_texto_fts_idx.
@app.get("/busca")
def busca(q: str = Query(""), limite: int = Query(20, ge=1, le=100)):
    if not q.strip():
        raise HTTPException(400, "consulta vazia")
    with psycopg.connect(config.DATABASE_URL) as conn:
        linhas = conn.execute(
            """
            SELECT lote_id, numero,
                   ts_headline('portuguese', coalesce(texto, ''), query,
                               'StartSel=<b>, StopSel=</b>, MaxFragments=2, MaxWords=25, MinWords=8') AS trecho
              FROM pagina, websearch_to_tsquery('portuguese', %s) AS query
             WHERE to_tsvector('portuguese', coalesce(texto, '')) @@ query
             ORDER BY ts_rank(to_tsvector('portuguese', coalesce(texto, '')), query) DESC, lote_id, numero
             LIMIT %s
            """,
            (q, limite),
        ).fetchall()
    return [{"lote_id": l, "pagina": n, "trecho": t} for l, n, t in linhas]


@app.get("/lotes/{lote_id}")
def obter_lote(lote_id: int):
    with psycopg.connect(config.DATABASE_URL) as conn:
        lote = conn.execute(
            "SELECT id, nome_arquivo, estado, docs_pendentes FROM lote WHERE id = %s", (lote_id,)
        ).fetchone()
        if lote is None:
            raise HTTPException(404, "lote não encontrado")
        docs = conn.execute(
            "SELECT id, ordem, pagina_ini, pagina_fim, estado, tipo, confianca, segmentacao_ambigua "
            "FROM documento WHERE lote_id = %s ORDER BY ordem", (lote_id,)
        ).fetchall()
    return {
        "id": lote[0], "nome_arquivo": lote[1], "estado": lote[2], "docs_pendentes": lote[3],
        "documentos": [
            {"id": d[0], "ordem": d[1], "pagina_ini": d[2], "pagina_fim": d[3], "estado": d[4],
             "tipo": d[5], "confianca": d[6], "segmentacao_ambigua": d[7]}
            for d in docs
        ],
    }


@app.get("/documentos/{documento_id}")
def obter_documento(documento_id: int):
    with psycopg.connect(config.DATABASE_URL) as conn:
        d = conn.execute(
            "SELECT id, lote_id, ordem, pagina_ini, pagina_fim, estado, tipo, confianca, segmentacao_ambigua "
            "FROM documento WHERE id = %s", (documento_id,)
        ).fetchone()
        if d is None:
            raise HTTPException(404, "documento não encontrado")
        paginas = conn.execute(
            "SELECT numero, texto FROM pagina WHERE documento_id = %s ORDER BY numero", (documento_id,)
        ).fetchall()
    return {
        "id": d[0], "lote_id": d[1], "ordem": d[2], "pagina_ini": d[3], "pagina_fim": d[4], "estado": d[5],
        "tipo": d[6], "confianca": d[7], "segmentacao_ambigua": d[8],
        "paginas": [
            {"numero": n, "imagem_url": f"/lotes/{d[1]}/paginas/{n}/imagem", "texto": t}
            for n, t in paginas
        ],
    }


@app.get("/lotes/{lote_id}/paginas/{numero}/imagem")
def imagem_pagina(lote_id: int, numero: int):
    png = Path(config.DATA_DIR) / f"lote_{lote_id}" / f"pag_{numero:04d}.png"
    if not png.is_file():
        raise HTTPException(404, "imagem não encontrada")
    return FileResponse(png, media_type="image/png")
