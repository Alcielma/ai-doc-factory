import psycopg
from fastapi import HTTPException

from app import config
from app.analise import enfileirar_analise
from app.extracao import enfileirar_extracao
from app.routers import r
from app.routers.revisao.schemas import Revisao

_COLUNAS_ANALISE = ("estado", "erro", "perfil", "marcacoes", "intervalo_pre_assinalado", "totais", "divergencias",
                    "diferencas_gemini", "ponto_britanico", "analise", "contagens", "scores_dimensao", "score_geral",
                    "requer_revisao", "modelo_gemini", "modelo_jev", "versao_prompt_gemini", "versao_prompt_jev",
                    "custo", "atualizado_em")


def obter_documento(documento_id: int) -> dict:
    with psycopg.connect(config.DATABASE_URL) as conn:
        d = conn.execute(
            "SELECT id, lote_id, ordem, pagina_ini, pagina_fim, estado, tipo, confianca, segmentacao_ambigua, "
            "tipo_original, revisor, revisado_em, motivo_revisao, probabilidades "
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
        "tipo_original": d[9], "revisor": d[10], "revisado_em": d[11], "motivo_revisao": d[12],
        "probabilidades": d[13],
        "paginas": [
            {"numero": n, "imagem_url": f"/lotes/{d[1]}/paginas/{n}/imagem", "texto": t}
            for n, t in paginas
        ],
    }


def obter_analise_ponto(documento_id: int) -> dict:
    with psycopg.connect(config.DATABASE_URL) as conn:
        doc = conn.execute("SELECT tipo FROM documento WHERE id = %s", (documento_id,)).fetchone()
        if doc is None:
            raise HTTPException(404, "documento não encontrado")
        row = conn.execute(f"SELECT {', '.join(_COLUNAS_ANALISE)} FROM analise_ponto WHERE documento_id = %s",
                           (documento_id,)).fetchone()
    if row is None:
        if doc[0] == "folha_ponto":
            return {"documento_id": documento_id, "estado": "pendente"}
        raise HTTPException(404, "documento não é uma folha de ponto analisada")
    return {"documento_id": documento_id, **dict(zip(_COLUNAS_ANALISE, row))}


SEM_TIPO = "sem_tipo"


def listar_documentos(empresa_id: int | None = None, falhou: bool | None = None) -> dict:
    """Documentos agrupados pelo campo `tipo` (uma consulta só). Falha = estado 'erro'."""
    condicoes, args = [], []
    if empresa_id is not None:
        condicoes.append("l.empresa_id = %s")
        args.append(empresa_id)
    if falhou is True:
        condicoes.append("d.estado = 'erro'")
    elif falhou is False:
        condicoes.append("d.estado <> 'erro'")
    where = f"WHERE {' AND '.join(condicoes)}" if condicoes else ""
    with psycopg.connect(config.DATABASE_URL) as conn:
        if empresa_id is not None and conn.execute(
                "SELECT 1 FROM empresa WHERE id = %s", (empresa_id,)).fetchone() is None:
            raise HTTPException(404, "empresa não encontrada")
        rows = conn.execute(
            "SELECT d.id, d.lote_id, d.ordem, d.pagina_ini, d.pagina_fim, d.estado, d.tipo, d.confianca, "
            f"l.empresa_id FROM documento d JOIN lote l ON l.id = d.lote_id {where} ORDER BY d.lote_id, d.ordem",
            args,
        ).fetchall()
    grupos: dict[str, list] = {}
    for id_, lote_id, ordem, ini, fim, estado, tipo, conf, emp in rows:
        grupos.setdefault(tipo or SEM_TIPO, []).append(
            {"id": id_, "lote_id": lote_id, "ordem": ordem, "pagina_ini": ini, "pagina_fim": fim,
             "estado": estado, "tipo": tipo, "confianca": conf, "empresa_id": emp})
    ordem_tipos = [*config.TIPOS, config.TIPO_DESCONHECIDO, SEM_TIPO]
    # tipo fora da lista (não esperado) vai depois dos conhecidos, antes de sem_tipo
    chaves = sorted(grupos, key=lambda t: (ordem_tipos.index(t) if t in ordem_tipos else len(config.TIPOS) + 1, t))
    return {"grupos": [{"tipo": t, "total": len(grupos[t]), "documentos": grupos[t]} for t in chaves]}


def atualizar_tipo(documento_id: int, revisao: Revisao) -> dict:
    """Corrige o tipo em qualquer estado, exceto 'segmentado' e 'erro'. tipo_original só é gravado se ainda NULL."""
    with psycopg.connect(config.DATABASE_URL) as conn:
        atual = conn.execute(
            "SELECT estado, tipo FROM documento WHERE id = %s FOR UPDATE", (documento_id,)).fetchone()
        if atual is None:
            raise HTTPException(404, "documento não encontrado")
        if atual[0] in ("segmentado", "erro"):
            raise HTTPException(409, f"documento em estado '{atual[0]}' não aceita alteração de tipo")
        conn.execute(
            "UPDATE documento SET estado = 'revisado', tipo_original = COALESCE(tipo_original, tipo), "
            "tipo = %s, revisor = %s, revisado_em = now() WHERE id = %s",
            (revisao.tipo, revisao.revisor, documento_id))
    if revisao.tipo == "folha_ponto" and atual[1] != "folha_ponto":
        enfileirar_analise(documento_id, r)  # nunca levanta
    enfileirar_extracao(documento_id, r)  # depois do commit; nunca levanta
    return obter_documento(documento_id)


def excluir_documento(documento_id: int) -> None:
    """Apaga só a linha de `documento`. analise_ponto e documento_campos caem por ON DELETE CASCADE;
    `pagina.documento_id` vira NULL (páginas e texto permanecem). Arquivos em disco e `lote.docs_pendentes`
    não são tocados; por isso lote em andamento (fan-in e filas em uso) recusa com 409."""
    with psycopg.connect(config.DATABASE_URL) as conn:
        row = conn.execute(
            "SELECT l.estado FROM documento d JOIN lote l ON l.id = d.lote_id WHERE d.id = %s FOR UPDATE OF d",
            (documento_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "documento não encontrado")
        if row[0] not in ("concluido", "erro"):
            raise HTTPException(409, f"lote em andamento (estado '{row[0]}'); aguarde a conclusão para excluir")
        conn.execute("DELETE FROM documento WHERE id = %s", (documento_id,))
