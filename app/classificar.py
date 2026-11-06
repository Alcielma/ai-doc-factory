"""Handler de classificar_documento.

STUB TEMPORÁRIO: será trocado pelo classificador real (Jev/Gemini). Hoje só fecha o fluxo e faz o fan-in:
não atribui tipo nem confiança. O fan-in (marcar + decrementar + concluir) deve ser mantido na troca.
"""
import psycopg

from app import config


def classificar_documento(payload: dict) -> None:
    doc_id = payload["documento_id"]
    with psycopg.connect(config.DATABASE_URL) as conn:  # transação única
        # só a transição segmentado -> classificado conta: job repetido não decrementa de novo
        row = conn.execute(
            "UPDATE documento SET estado = 'classificado' WHERE id = %s AND estado = 'segmentado' RETURNING lote_id",
            (doc_id,),
        ).fetchone()
        if row is None:
            return
        restantes = conn.execute(
            "UPDATE lote SET docs_pendentes = docs_pendentes - 1 WHERE id = %s RETURNING docs_pendentes",
            (row[0],),
        ).fetchone()[0]
        if restantes == 0:
            conn.execute("UPDATE lote SET estado = 'concluido' WHERE id = %s", (row[0],))
