"""GET /lotes/{id}/conformidade + documento_campos, contra o Postgres do compose."""
import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from app import config
from app.api import app
from app.campos import campos_do_lote, gravar_campo

client = TestClient(app)


@pytest.fixture
def lote():
    """Cria lote com documentos [(tipo, estado)]; devolve (lote_id, [ids])."""
    criados = []

    def _f(docs):
        with psycopg.connect(config.DATABASE_URL) as conn:
            lote_id = conn.execute(
                "INSERT INTO lote (sha256, nome_arquivo, estado) VALUES (%s, 't.pdf', 'concluido') RETURNING id",
                (uuid.uuid4().hex + uuid.uuid4().hex,)).fetchone()[0]
            ids = [conn.execute(
                "INSERT INTO documento (lote_id, ordem, pagina_ini, pagina_fim, tipo, estado) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id", (lote_id, n, n, n, t, e)).fetchone()[0]
                for n, (t, e) in enumerate(docs, start=1)]
        criados.append(lote_id)
        return lote_id, ids
    yield _f
    with psycopg.connect(config.DATABASE_URL) as conn:
        for l in criados:
            conn.execute("DELETE FROM lote WHERE id = %s", (l,))


def test_lote_inexistente_404():
    assert client.get("/lotes/999999999/conformidade").status_code == 404


def test_lote_sem_documentos_analisados_devolve_sem_score(lote):
    lote_id, _ = lote([("holerite", "segmentado")])
    r = client.get(f"/lotes/{lote_id}/conformidade")
    assert r.status_code == 200
    j = r.json()
    assert j["score"] is None and j["provisorio"] is True and j["pendencias"]


def test_completude_calculada_e_validade_consistencia_pendentes(lote):
    lote_id, _ = lote([(t, "classificado") for t in ("aso", "holerite", "folha_ponto")])
    j = client.get(f"/lotes/{lote_id}/conformidade").json()
    assert j["criterios"]["completude"]["nota"] == 0.6
    assert j["criterios"]["validade"]["pendente"] and j["criterios"]["consistencia"]["pendente"]
    assert j["score"] == 60 and j["classificacao"] == "Crítico" and j["provisorio"] is True


def test_upsert_de_campos_e_unicidade(lote):
    lote_id, (doc,) = lote([("aso", "classificado")])
    with psycopg.connect(config.DATABASE_URL) as conn:
        gravar_campo(conn, doc, "nome", "Ana", "teste")
        gravar_campo(conn, doc, "nome", "Ana Lima", "humano")
        assert conn.execute("SELECT count(*), max(valor), max(origem) FROM documento_campos "
                            "WHERE documento_id = %s", (doc,)).fetchone() == (1, "Ana Lima", "humano")
        assert campos_do_lote(conn, lote_id) == {doc: {"nome": "Ana Lima"}}


def test_aso_vencido_e_nome_divergente_pela_api(lote):
    tipos = ["aso", "contrato_trabalho", "holerite", "folha_pagamento", "folha_ponto"]
    lote_id, ids = lote([(t, "classificado") for t in tipos])
    with psycopg.connect(config.DATABASE_URL) as conn:
        gravar_campo(conn, ids[0], "data_exame", "2000-01-01", "teste")
        gravar_campo(conn, ids[1], "data_termino", "2999-12-31", "teste")
        for i in ids:
            gravar_campo(conn, i, "nome", "Maria Silva" if i != ids[2] else "Mario Silva", "teste")
    j = client.get(f"/lotes/{lote_id}/conformidade").json()
    assert {(d["criterio"], d["regra"]) for d in j["descontos"]} == {
        ("validade", "documento_vencido"), ("consistencia", "campo_divergente")}
    assert j["classificacao"] in ("Atenção", "Crítico", "Regular") and j["score"] is not None


def test_correcao_humana_muda_o_resultado(lote):
    tipos = [("aso", "classificado"), ("contrato_trabalho", "classificado"), ("holerite", "classificado"),
             ("folha_pagamento", "classificado"), ("desconhecido", "em_revisao")]
    lote_id, ids = lote(tipos)
    antes = client.get(f"/lotes/{lote_id}/conformidade").json()
    # há documento não identificado: folha_ponto faltante é pendente, não ausente
    assert antes["descontos"] == [] and antes["score"] == 100
    assert any(p["tipo"] == "folha_ponto" for p in antes["pendencias"])
    # o revisor identifica o documento como atestado: agora folha_ponto está de fato ausente
    assert client.post(f"/documentos/{ids[4]}/revisao", json={"tipo": "atestado_medico", "revisor": "ana"}
                       ).status_code == 200
    depois = client.get(f"/lotes/{lote_id}/conformidade").json()
    assert [(d["tipo"], d["regra"]) for d in depois["descontos"]] == [("folha_ponto", "obrigatorio_ausente")]
    assert depois["score"] == 80 and depois["score"] != antes["score"]
