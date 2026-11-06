import psycopg
from fastapi import HTTPException

from app import config
from app.analise import enfileirar_analise
from app.extracao import enfileirar_extracao
from app.routers import r
from app.routers.revisao.schemas import Revisao


def fila_revisao() -> list[dict]:
    with psycopg.connect(config.DATABASE_URL) as conn:
        docs = conn.execute(
            "SELECT id, lote_id, tipo, confianca, motivo_revisao, pagina_ini FROM documento "
            "WHERE estado = 'em_revisao' ORDER BY lote_id, ordem"
        ).fetchall()
    return [
        {"id": i, "lote_id": l, "tipo_sugerido": t, "confianca": c, "motivo": m,
         "imagem_url": f"/lotes/{l}/paginas/{p}/imagem"}
        for i, l, t, c, m, p in docs
    ]


def revisar_documento(documento_id: int, revisao: Revisao) -> dict:
    with psycopg.connect(config.DATABASE_URL) as conn:
        # um único UPDATE condicional; no lado direito, tipo e tipo_original ainda são os valores antigos,
        # então tipo_original guarda o tipo sugerido na primeira revisão e não muda nas seguintes
        row = conn.execute(
            "UPDATE documento SET estado = 'revisado', tipo_original = COALESCE(tipo_original, tipo), "
            "tipo = %s, revisor = %s, revisado_em = now() "
            "WHERE id = %s AND estado IN ('em_revisao', 'revisado') "
            "RETURNING id, estado, tipo, tipo_original, revisor, revisado_em",
            (revisao.tipo, revisao.revisor, documento_id),
        ).fetchone()
        if row is None:
            estado = conn.execute("SELECT estado FROM documento WHERE id = %s", (documento_id,)).fetchone()
            if estado is None:
                raise HTTPException(404, "documento não encontrado")
            raise HTTPException(409, f"documento em estado '{estado[0]}' não aceita revisão")
    if revisao.tipo == "folha_ponto":
        enfileirar_analise(documento_id, r)  # nunca levanta: não derruba a revisão
    enfileirar_extracao(documento_id, r)  # depois do commit; nunca levanta
    return {"id": row[0], "estado": row[1], "tipo": row[2], "tipo_original": row[3],
            "revisor": row[4], "revisado_em": row[5]}
