"""Cadastro de empresas e vínculo do lote. Rodar no compose (Postgres real); a fila é neutralizada."""
import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from app import api, config
from app.routers.lotes import actions as lotes_actions


@pytest.fixture
def ctx(monkeypatch):
    monkeypatch.setattr(lotes_actions, "enfileirar", lambda *a, **k: None)
    http = TestClient(api.app)
    marca = uuid.uuid4().hex[:8]
    empresas, lotes = [], []

    def nova_empresa(nome=None):
        r = http.post("/cadastro-empresas", json={"nome": nome or f"Emp {marca} {uuid.uuid4().hex[:6]}"})
        assert r.status_code == 201, r.text
        empresas.append(r.json()["id"])
        return r.json()

    def enviar(conteudo=None, **form):
        pdf = conteudo or b"%PDF-1.4 " + uuid.uuid4().hex.encode()
        r = http.post("/lotes", files={"arquivo": ("a.pdf", pdf, "application/pdf")}, data=form)
        if r.status_code == 200:
            lotes.append(r.json()["lote_id"])
        return r, pdf

    yield http, nova_empresa, enviar, marca
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as conn:
        conn.execute("DELETE FROM lote WHERE id = ANY(%s)", (lotes,))
        conn.execute("DELETE FROM empresa WHERE id = ANY(%s)", (empresas,))


def test_criar_normaliza_e_devolve_objeto(ctx):
    http, nova, _, marca = ctx
    e = nova(f"  Alfa {marca}  ")
    assert e["nome"] == f"Alfa {marca}"
    assert e["lotes"] == [] and e["documentos"] == [] and e["n_lotes"] == 0 and e["n_documentos"] == 0
    assert e["criado_em"]


@pytest.mark.parametrize("variacao", [lambda n: n.upper(), lambda n: f"  {n.lower()}\t", lambda n: n])
def test_nome_duplicado_409(ctx, variacao):
    http, nova, _, marca = ctx
    e = nova(f"Beta {marca}")
    r = http.post("/cadastro-empresas", json={"nome": variacao(e["nome"])})
    assert r.status_code == 409


@pytest.mark.parametrize("corpo", [{"nome": ""}, {"nome": "   "}, {}])
def test_nome_vazio_422(ctx, corpo):
    assert ctx[0].post("/cadastro-empresas", json=corpo).status_code == 422


def test_listar_e_obter_com_lotes_e_documentos(ctx):
    http, nova, enviar, _ = ctx
    e, outra = nova(), nova()
    r, _ = enviar(empresa_id=e["id"])
    assert r.status_code == 200 and r.json()["empresa_id"] == e["id"]
    lote = r.json()["lote_id"]
    enviar(empresa_id=outra["id"])
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as conn:
        for ordem in (1, 2):
            conn.execute("INSERT INTO documento (lote_id, ordem, pagina_ini, pagina_fim, tipo, estado) "
                         "VALUES (%s, %s, %s, %s, 'aso', 'classificado')", (lote, ordem, ordem, ordem))
    item = http.get(f"/cadastro-empresas/{e['id']}").json()
    assert item["n_lotes"] == 1 and item["lotes"][0]["id"] == lote
    assert item["lotes"][0]["estado"] == "recebido" and item["lotes"][0]["nome_arquivo"] == "a.pdf"
    assert item["n_documentos"] == 2
    assert [d["ordem"] for d in item["documentos"]] == [1, 2]
    assert set(item["documentos"][0]) == {"id", "lote_id", "ordem", "pagina_ini", "pagina_fim", "tipo", "estado"}
    assert http.get(f"/cadastro-empresas/{outra['id']}").json()["n_documentos"] == 0
    lista = {i["id"]: i for i in http.get("/cadastro-empresas").json()}
    assert lista[e["id"]] == item
    assert http.get(f"/lotes/{lote}").json()["empresa_id"] == e["id"]


def test_obter_inexistente_404(ctx):
    assert ctx[0].get("/cadastro-empresas/999999999").status_code == 404


def test_upload_sem_empresa_e_empresa_invalida(ctx):
    http, _, enviar, _ = ctx
    r, _ = enviar()
    assert r.status_code == 200 and r.json()["empresa_id"] is None
    assert http.get(f"/lotes/{r.json()['lote_id']}").json()["empresa_id"] is None
    with psycopg.connect(config.DATABASE_URL) as conn:
        antes = conn.execute("SELECT count(*) FROM lote").fetchone()[0]
    r, _ = enviar(empresa_id=999999999)
    assert r.status_code == 404 and "999999999" in r.json()["detail"]
    with psycopg.connect(config.DATABASE_URL) as conn:
        assert conn.execute("SELECT count(*) FROM lote").fetchone()[0] == antes


def test_idempotencia_vincula_mantem_e_conflita(ctx):
    http, nova, enviar, _ = ctx
    a, b = nova(), nova()
    r, pdf = enviar()  # sem empresa
    lote = r.json()["lote_id"]
    r2, _ = enviar(pdf, empresa_id=a["id"])  # vincula
    assert r2.status_code == 200 and r2.json()["existente"] and r2.json()["lote_id"] == lote
    assert r2.json()["empresa_id"] == a["id"]
    assert http.get(f"/lotes/{lote}").json()["empresa_id"] == a["id"]
    r3, _ = enviar(pdf, empresa_id=a["id"])  # mesma empresa
    assert r3.status_code == 200 and r3.json()["empresa_id"] == a["id"]
    r4, _ = enviar(pdf, empresa_id=b["id"])  # outra: 409, nada muda
    assert r4.status_code == 409
    assert http.get(f"/lotes/{lote}").json()["empresa_id"] == a["id"]
    r5, _ = enviar(pdf)  # sem empresa_id: devolve o existente
    assert r5.status_code == 200 and r5.json()["empresa_id"] == a["id"]


def test_rotas_de_conformidade_continuam(ctx):
    http, _, enviar, _ = ctx
    assert http.get("/empresas").status_code == 200
    r, _ = enviar()
    assert http.get(f"/lotes/{r.json()['lote_id']}/conformidade").status_code == 200
