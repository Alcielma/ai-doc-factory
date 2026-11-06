"""Score de conformidade: função pura, datas e valores fixos."""
from datetime import date

import pytest

from app import config, conformidade
from app.conformidade import calcular, classificar_score, normalizar, score_inteiro

REF = date(2025, 6, 1)
OBRIG = ["aso", "contrato_trabalho", "holerite", "folha_pagamento", "folha_ponto"]


def docs(tipos, estado="classificado"):
    return [{"id": i, "tipo": t, "estado": estado} for i, t in enumerate(tipos, start=1)]


def campos_ok(**extra):
    """Campos coerentes para o lote completo (ids 1..5 na ordem de OBRIG)."""
    base = {
        1: {"data_exame": "2025-03-01", "nome": "Maria da Silva", "cpf": "123.456.789-09"},
        2: {"data_termino": "2026-01-01", "nome": "Maria da Silva", "cpf": "12345678909",
            "matricula": "0042", "data_admissao": "2024-02-01"},
        3: {"nome": "Maria da Silva", "cpf": "123.456.789-09", "matricula": "0042", "data_admissao": "01/02/2024"},
        4: {"nome": "Maria da Silva", "matricula": "0042"},
        5: {"nome": "Maria da Silva", "matricula": "0042"},
    }
    for k, v in extra.items():
        base[int(k[1:])] = {**base[int(k[1:])], **v}
    return base


def fecha_em_100(r):
    return abs(r["score_bruto"] + sum(d["pontos"] for d in r["descontos"]) - 100) <= \
        conformidade.TOLERANCIA_ARREDONDAMENTO * (len(r["descontos"]) + 1)


def test_config_valida_contra_tipos():
    assert set(conformidade.OBRIGATORIOS) <= set(config.TIPOS)
    assert set(conformidade.VALIDADE) <= set(config.TIPOS)
    assert sum(conformidade.PESOS.values()) == 100


def test_lote_completo_e_coerente():
    r = calcular(docs(OBRIG), campos_ok(), REF)
    assert (r["score"], r["classificacao"], r["descontos"]) == (100, "Regular", [])
    assert r["data_referencia"] == "2025-06-01"


@pytest.mark.parametrize("score,faixa", [(100, "Regular"), (85, "Regular"), (84, "Atenção"), (65, "Atenção"),
                                         (64, "Crítico"), (0, "Crítico")])
def test_limites_de_faixa(score, faixa):
    assert classificar_score(score) == faixa


def test_arredondamento_antes_de_classificar():
    assert score_inteiro(84.5) == 85 and classificar_score(score_inteiro(84.5)) == "Regular"
    assert score_inteiro(84.49) == 84 and classificar_score(score_inteiro(84.49)) == "Atenção"
    assert score_inteiro(64.5) == 65 and classificar_score(score_inteiro(64.5)) == "Atenção"
    assert score_inteiro(64.4999) == 64 and classificar_score(score_inteiro(64.4999)) == "Crítico"


def test_obrigatorio_faltante_e_ausente_sem_desconhecido():
    tipos = [t for t in OBRIG if t != "folha_ponto"]
    r = calcular(docs(tipos), campos_ok(), REF)
    assert r["criterios"]["completude"]["nota"] == 0.8
    assert [(d["criterio"], d["tipo"], d["regra"]) for d in r["descontos"]] == [
        ("completude", "folha_ponto", "obrigatorio_ausente")]
    assert r["descontos"][0]["pontos"] == 8.0
    assert (r["score"], r["classificacao"]) == (92, "Regular")
    assert fecha_em_100(r)


def test_obrigatorio_faltante_e_pendente_com_documento_desconhecido():
    tipos = [t for t in OBRIG if t != "folha_ponto"]
    d = docs(tipos) + [{"id": 9, "tipo": "desconhecido", "estado": "em_revisao"}]
    r = calcular(d, campos_ok(), REF)
    assert r["descontos"] == []
    assert r["criterios"]["completude"]["nota"] == 1.0
    assert r["score"] == 100 and r["provisorio"] is True
    assert any(p["criterio"] == "completude" and p["tipo"] == "folha_ponto" for p in r["pendencias"])
    assert any(p["documento"] == 9 for p in r["pendencias"])


@pytest.mark.parametrize("estado,tipo", [("segmentado", None), ("em_revisao", "holerite"), ("erro", None),
                                         ("classificado", "desconhecido")])
def test_documento_nao_analisado_nao_zera_a_nota(estado, tipo):
    d = docs(OBRIG) + [{"id": 9, "tipo": tipo, "estado": estado}]
    r = calcular(d, campos_ok(), REF)
    assert r["score"] == 100 and r["provisorio"] is True
    assert [p for p in r["pendencias"] if p["documento"] == 9]


def test_redistribuicao_de_pesos_sem_extracao():
    r = calcular(docs(OBRIG), {}, REF)
    c = r["criterios"]
    assert c["validade"]["pendente"] and c["consistencia"]["pendente"]
    assert c["completude"]["peso_efetivo"] == 100.0 and c["validade"]["peso_efetivo"] is None
    assert r["score"] == 100 and r["provisorio"] is True


def test_redistribuicao_parcial():
    # sem campos de consistência: validade e completude dividem 100 (40/75 e 35/75)
    campos = {1: {"data_exame": "2025-03-01"}, 2: {"data_termino": "2026-01-01"}}
    r = calcular(docs(OBRIG), campos, REF)
    assert r["criterios"]["consistencia"]["pendente"]
    assert r["criterios"]["completude"]["peso_efetivo"] == pytest.approx(53.3333, abs=1e-4)
    assert r["criterios"]["validade"]["peso_efetivo"] == pytest.approx(46.6667, abs=1e-4)


def test_aso_vencido():
    r = calcular(docs(OBRIG), campos_ok(d1={"data_exame": "2024-03-01"}), REF)  # vence 2025-03-01
    assert r["criterios"]["validade"]["nota"] == 0.5
    d = r["descontos"]
    assert len(d) == 1 and (d[0]["criterio"], d[0]["tipo"], d[0]["documento"], d[0]["regra"]) == (
        "validade", "aso", 1, "documento_vencido")
    assert "2025-03-01" in d[0]["detalhe"]
    assert d[0]["pontos"] == 17.5  # 35 / 2 itens
    assert r["score"] == 83 and r["classificacao"] == "Atenção"  # 82,5 sobe para 83
    assert fecha_em_100(r)


def test_vencer_hoje_ainda_e_valido_e_no_dia_seguinte_vence():
    hoje = calcular(docs(OBRIG), campos_ok(d1={"data_exame": "2024-06-01"}), REF)  # vence em 2025-06-01
    assert hoje["descontos"] == []
    amanha = calcular(docs(OBRIG), campos_ok(d1={"data_exame": "2024-06-01"}), date(2025, 6, 2))
    assert [d["regra"] for d in amanha["descontos"]] == ["documento_vencido"]


def test_contrato_vencido_pelo_termino():
    r = calcular(docs(OBRIG), campos_ok(d2={"data_termino": "31/05/2025"}), REF)
    assert [(d["tipo"], d["regra"]) for d in r["descontos"]] == [("contrato_trabalho", "documento_vencido")]


def test_documento_sem_data_fica_pendente_e_nao_desconta():
    c = campos_ok()
    del c[1]["data_exame"]
    c[2]["data_termino"] = "sem leitura"
    r = calcular(docs(OBRIG), c, REF)
    assert r["criterios"]["validade"]["pendente"] is True
    assert r["descontos"] == [] and r["provisorio"] is True
    assert {p["documento"] for p in r["pendencias"] if p["criterio"] == "validade" and p["documento"]} == {1, 2}


def test_nome_divergente():
    r = calcular(docs(OBRIG), campos_ok(d3={"nome": "Mario da Silva"}), REF)
    d = r["descontos"]
    assert len(d) == 1 and (d[0]["criterio"], d[0]["regra"], d[0]["campo"], d[0]["conferir"]) == (
        "consistencia", "campo_divergente", "nome", True)
    assert {"documento": 3, "tipo": "holerite", "valor": "Mario da Silva"} in d[0]["valores"]
    assert len(d[0]["valores"]) == 5
    assert r["criterios"]["consistencia"]["nota"] == 0.75  # 3 de 4 campos coerentes
    assert d[0]["pontos"] == 6.25 and r["score"] == 94
    assert fecha_em_100(r)


def test_nome_com_acento_caixa_e_espaco_nao_diverge():
    r = calcular(docs(OBRIG), campos_ok(d3={"nome": "  MARIA   da  silva. "}, d4={"nome": "María da Silva"}), REF)
    assert r["descontos"] == []


def test_cpf_com_e_sem_pontuacao_sao_iguais():
    assert normalizar("cpf", "123.456.789-09") == normalizar("cpf", "12345678909")
    assert calcular(docs(OBRIG), campos_ok(), REF)["descontos"] == []  # ids 1,3 com pontos; 2 sem
    r = calcular(docs(OBRIG), campos_ok(d3={"cpf": "123.456.789-10"}), REF)
    assert [d["campo"] for d in r["descontos"]] == ["cpf"]


def test_data_admissao_em_formatos_diferentes_e_igual():
    assert normalizar("data_admissao", "01/02/2024") == normalizar("data_admissao", "2024-02-01")


def test_valor_ausente_nao_e_divergencia_e_vira_pendencia():
    c = campos_ok()
    del c[3]["nome"]
    r = calcular(docs(OBRIG), c, REF)
    assert r["descontos"] == []
    assert {"criterio": "consistencia", "documento": 3, "tipo": "holerite",
            "motivo": "campo 'nome' ausente"} in r["pendencias"]
    assert r["provisorio"] is True


def test_sem_documentos_analisados_nao_ha_score():
    r = calcular(docs(["holerite"], estado="segmentado"), {}, REF)
    assert (r["score"], r["classificacao"], r["score_bruto"]) == (None, None, None)
    assert r["provisorio"] is True and r["descontos"] == []
    assert all(c["pendente"] for c in r["criterios"].values())
    assert calcular([], {}, REF)["score"] is None


def test_soma_dos_descontos_fecha_em_100_com_varios_descontos():
    tipos = ["aso", "holerite", "folha_ponto"]  # faltam contrato e folha_pagamento
    c = {1: {"data_exame": "2020-01-01", "nome": "A B", "cpf": "1"},
         2: {"nome": "A C", "cpf": "2", "matricula": "7", "data_admissao": "2024-01-01"},
         3: {"nome": "A D", "matricula": "8"}}
    r = calcular(docs(tipos), c, REF)
    assert len(r["descontos"]) == 2 + 1 + 3  # 2 ausentes, 1 vencido, nome+cpf+matricula divergentes
    assert fecha_em_100(r)
