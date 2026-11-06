"""Handler de classificar_documento: classifica, roteia por confiança e faz o fan-in do lote.

O classificador é trocável (ver app/classificador_regras.py). A leitura e a classificação (que pode virar
chamada de rede) ficam fora da transação; só a gravação e o fan-in rodam dentro dela.
"""
import psycopg
from psycopg.types.json import Jsonb

from app import config
from app.classificador_regras import classificar
from app.roteamento import decidir

TEXTO_MAX = 6000  # caracteres das primeiras páginas enviados ao classificador


def montar_texto(textos: list[str], limite: int = TEXTO_MAX) -> str:
    return "\n".join(t or "" for t in textos)[:limite]


def classificar_documento(payload: dict) -> None:
    doc_id = payload["documento_id"]
    with psycopg.connect(config.DATABASE_URL) as conn:
        doc = conn.execute(
            "SELECT estado, segmentacao_ambigua FROM documento WHERE id = %s", (doc_id,)
        ).fetchone()
        if doc is None or doc[0] != "segmentado":
            return  # já decidido ou revisado: job repetido não faz nada
        textos = [t for (t,) in conn.execute(
            "SELECT texto FROM pagina WHERE documento_id = %s ORDER BY numero", (doc_id,))]
    resultado = classificar(montar_texto(textos))
    decisao = decidir(resultado.confianca, resultado.tipo, segmentacao_ambigua=doc[1])
    with psycopg.connect(config.DATABASE_URL) as conn:  # transação única: gravação + fan-in
        # só a transição segmentado -> (classificado | em_revisao) conta: não sobrescreve nem decrementa de novo
        row = conn.execute(
            "UPDATE documento SET estado = %s, tipo = %s, confianca = %s, modelo = %s, versao_prompt = %s, "
            "probabilidades = %s, motivo_revisao = %s WHERE id = %s AND estado = 'segmentado' RETURNING lote_id",
            (decisao.estado, decisao.tipo, resultado.confianca, resultado.modelo, resultado.versao_prompt,
             Jsonb(resultado.probabilidades), decisao.motivo, doc_id),
        ).fetchone()
        if row is None:
            return
        restantes = conn.execute(
            "UPDATE lote SET docs_pendentes = docs_pendentes - 1 WHERE id = %s RETURNING docs_pendentes",
            (row[0],),
        ).fetchone()[0]
        if restantes == 0:
            conn.execute("UPDATE lote SET estado = 'concluido' WHERE id = %s", (row[0],))
