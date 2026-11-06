import psycopg
from fastapi import HTTPException

from app import config


def _consultar(conn, empresa_id: int | None = None) -> list[dict]:
    """Três consultas agregadas (empresas, lotes, documentos), montadas em memória; sem N+1."""
    if empresa_id is None:
        filtro_e, filtro_l, args = "", "WHERE l.empresa_id IS NOT NULL", ()
    else:
        filtro_e, filtro_l, args = "WHERE id = %s", "WHERE l.empresa_id = %s", (empresa_id,)
    empresas = conn.execute(f"SELECT id, nome, criado_em FROM empresa {filtro_e} ORDER BY id", args).fetchall()
    lotes = conn.execute(
        f"SELECT l.id, l.empresa_id, l.nome_arquivo, l.estado FROM lote l {filtro_l} ORDER BY l.id", args).fetchall()
    documentos = conn.execute(
        "SELECT d.id, d.lote_id, d.ordem, d.pagina_ini, d.pagina_fim, d.tipo, d.estado FROM documento d "
        f"JOIN lote l ON l.id = d.lote_id {filtro_l} ORDER BY d.lote_id, d.ordem", args).fetchall()

    dono_do_lote = {lote[0]: lote[1] for lote in lotes}
    lotes_de: dict[int, list] = {}
    docs_de: dict[int, list] = {}
    for id_, dono, nome_arquivo, estado in lotes:
        lotes_de.setdefault(dono, []).append({"id": id_, "nome_arquivo": nome_arquivo, "estado": estado})
    for id_, lote_id, ordem, ini, fim, tipo, estado in documentos:
        docs_de.setdefault(dono_do_lote[lote_id], []).append(
            {"id": id_, "lote_id": lote_id, "ordem": ordem, "pagina_ini": ini, "pagina_fim": fim,
             "tipo": tipo, "estado": estado})
    return [
        {"id": id_, "nome": nome, "criado_em": criado_em,
         "lotes": lotes_de.get(id_, []), "documentos": docs_de.get(id_, []),
         "n_lotes": len(lotes_de.get(id_, [])), "n_documentos": len(docs_de.get(id_, []))}
        for id_, nome, criado_em in empresas
    ]


def criar_empresa(nome: str) -> dict:
    try:
        with psycopg.connect(config.DATABASE_URL) as conn:
            id_ = conn.execute("INSERT INTO empresa (nome) VALUES (%s) RETURNING id", (nome,)).fetchone()[0]
            return _consultar(conn, id_)[0]
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "já existe uma empresa com esse nome")


def listar_empresas() -> list[dict]:
    with psycopg.connect(config.DATABASE_URL) as conn:
        return _consultar(conn)


def obter_empresa(empresa_id: int) -> dict:
    with psycopg.connect(config.DATABASE_URL) as conn:
        achadas = _consultar(conn, empresa_id)
    if not achadas:
        raise HTTPException(404, "empresa não encontrada")
    return achadas[0]
