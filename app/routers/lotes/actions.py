import hashlib
from pathlib import Path

import psycopg
from fastapi import HTTPException

from app import config
from app.filas import enfileirar
from app.routers import r


def criar_lote(dados: bytes, pdf: bytes, nome_arquivo: str | None) -> dict:
    sha = hashlib.sha256(dados).hexdigest()  # dos bytes originais enviados, PDF ou imagem
    with psycopg.connect(config.DATABASE_URL) as conn:
        row = conn.execute(
            "INSERT INTO lote (sha256, nome_arquivo) VALUES (%s, %s) "
            "ON CONFLICT (sha256) DO NOTHING RETURNING id, estado",
            (sha, nome_arquivo or "lote.pdf"),
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
        (pasta / "original.pdf").write_bytes(pdf)
    enfileirar(r, config.FILA_SEGMENTAR, {"lote_id": row[0]})
    return {"lote_id": row[0], "estado": row[1], "existente": False}


def obter_lote(lote_id: int) -> dict:
    with psycopg.connect(config.DATABASE_URL) as conn:
        lote = conn.execute(
            "SELECT id, nome_arquivo, estado, docs_pendentes FROM lote WHERE id = %s", (lote_id,)
        ).fetchone()
        if lote is None:
            raise HTTPException(404, "lote não encontrado")
        docs = conn.execute(
            "SELECT id, ordem, pagina_ini, pagina_fim, estado, tipo, confianca, segmentacao_ambigua, "
            "probabilidades, tipo_original FROM documento WHERE lote_id = %s ORDER BY ordem", (lote_id,)
        ).fetchall()
    return {
        "id": lote[0], "nome_arquivo": lote[1], "estado": lote[2], "docs_pendentes": lote[3],
        "documentos": [
            {"id": d[0], "ordem": d[1], "pagina_ini": d[2], "pagina_fim": d[3], "estado": d[4],
             "tipo": d[5], "confianca": d[6], "segmentacao_ambigua": d[7],
             "probabilidades": d[8], "tipo_original": d[9]}
            for d in docs
        ],
    }


def caminho_imagem_pagina(lote_id: int, numero: int) -> Path:
    png = Path(config.DATA_DIR) / f"lote_{lote_id}" / f"pag_{numero:04d}.png"
    if not png.is_file():
        raise HTTPException(404, "imagem não encontrada")
    return png
