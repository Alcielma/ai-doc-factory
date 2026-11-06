"""Acesso a documento_campos (Goal 7): upsert e leitura dos campos extraídos."""


def gravar_campo(conn, documento_id: int, campo: str, valor: str, origem: str) -> None:
    """Upsert: um valor por (documento, campo)."""
    conn.execute(
        "INSERT INTO documento_campos (documento_id, campo, valor, origem) VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (documento_id, campo) DO UPDATE "
        "SET valor = EXCLUDED.valor, origem = EXCLUDED.origem, atualizado_em = now()",
        (documento_id, campo, valor, origem),
    )


def campos_do_lote(conn, lote_id: int) -> dict[int, dict[str, str]]:
    linhas = conn.execute(
        "SELECT c.documento_id, c.campo, c.valor FROM documento_campos c "
        "JOIN documento d ON d.id = c.documento_id WHERE d.lote_id = %s", (lote_id,)
    ).fetchall()
    campos: dict[int, dict[str, str]] = {}
    for doc, campo, valor in linhas:
        campos.setdefault(doc, {})[campo] = valor
    return campos
