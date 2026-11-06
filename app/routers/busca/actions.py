import psycopg

from app import config


# A expressão to_tsvector('portuguese', coalesce(texto, '')) precisa ser idêntica à do índice pagina_texto_fts_idx.
def buscar(q: str, limite: int) -> list[dict]:
    with psycopg.connect(config.DATABASE_URL) as conn:
        linhas = conn.execute(
            """
            SELECT p.lote_id, p.numero, p.documento_id, d.tipo, l.nome_arquivo,
                   ts_headline('portuguese', coalesce(p.texto, ''), query,
                               'StartSel=<b>, StopSel=</b>, MaxFragments=2, MaxWords=25, MinWords=8') AS trecho
              FROM pagina p
              JOIN lote l ON l.id = p.lote_id
              LEFT JOIN documento d ON d.id = p.documento_id,
                   websearch_to_tsquery('portuguese', %s) AS query
             WHERE to_tsvector('portuguese', coalesce(p.texto, '')) @@ query
             ORDER BY ts_rank(to_tsvector('portuguese', coalesce(p.texto, '')), query) DESC, p.lote_id, p.numero
             LIMIT %s
            """,
            (q, limite),
        ).fetchall()
    return [{"lote_id": l, "pagina": n, "trecho": t, "documento_id": d, "tipo": tipo, "nome_arquivo": arq}
            for l, n, d, tipo, arq, t in linhas]
