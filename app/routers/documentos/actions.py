import psycopg
from fastapi import HTTPException

from app import config

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
