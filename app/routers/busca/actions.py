import psycopg

from app import config


# A expressão to_tsvector('portuguese', coalesce(texto, '')) precisa ser idêntica à do índice pagina_texto_fts_idx.
def buscar(q: str, limite: int) -> list[dict]:
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
