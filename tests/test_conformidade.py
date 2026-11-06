"""Score de conformidade da empresa: funções puras, datas e valores fixos."""
from datetime import date

import pytest

from app import config, conformidade
from app.conformidade import (agrupar_empresas, calcular_empresa, classificar_score, identificar_empresa,
                              normalizar, score_inteiro, validar_cnpj, validar_cpf)

REF = date(2025, 6, 1)
CNPJ_A, CNPJ_B = "11222333000181", "11444777000161"
CPF1, CPF2 = "52998224725", "11144477735"
OBRIG = ["aso", "contrato_trabalho", "holerite", "folha_pagamento", "folha_ponto"]


def pessoa(cnpj=CNPJ_A, cpf=CPF1, nome="Maria da Silva", **extra):
    return {"cnpj_prestadora": cnpj, "razao_social_prestadora": "Alfa Serviços Ltda", "distingue_prestadora": "true",
            "nome": nome, "cpf": cpf, "matricula": "0042", "data_admissao": "2024-02-01",
            "data_exame": "2025-03-01", "data_termino": "2026-01-01", "tipo_prazo": "determinado", **extra}


def lote(tipos, campos_base, primeiro_id=1, lote_id=1, estado="classificado"):
    docs = [{"id": primeiro_id + i, "lote_id": lote_id, "tipo": t, "estado": estado} for i, t in enumerate(tipos)]
    return docs, {d["id"]: dict(campos_base) for d in docs}


def avaliar(docs, campos, cnpj=CNPJ_A, ref=REF):
    empresas, sem = agrupar_empresas(docs, campos)
    return calcular_empresa(empresas[cnpj], campos, ref, sem)


def fecha_em_100(r):
    return abs(r["score_bruto"] + sum(d["pontos"] for d in r["descontos"]) - 100) <= \
        conformidade.TOLERANCIA_ARREDONDAMENTO * (len(r["descontos"]) + 1)


def test_config_valida_contra_tipos():
    assert set(conformidade.OBRIGATORIOS) <= set(config.TIPOS) and set(conformidade.VALIDADE) <= set(config.TIPOS)
    assert sum(conformidade.PESOS.values()) == 100


def test_validacao_de_cnpj_e_cpf():
    assert validar_cnpj("11.222.333/0001-81") == CNPJ_A and validar_cnpj(CNPJ_B) == CNPJ_B
    assert validar_cnpj("11222333000182") is None and validar_cnpj("00000000000000") is None
    assert validar_cnpj("123") is None and validar_cnpj(None) is None
    assert validar_cpf("529.982.247-25") == CPF1 and validar_cpf("52998224726") is None
    assert validar_cpf("11111111111") is None


def test_identificacao_da_empresa():
    assert identificar_empresa(pessoa()) == (CNPJ_A, None)
    assert identificar_empresa(pessoa(cnpj="11.222.333/0001-81"))[0] == CNPJ_A
    assert identificar_empresa(pessoa(cnpj=""))[0] is None
    assert identificar_empresa(pessoa(cnpj="11222333000182")) == (None, "CNPJ da prestadora inválido")
    assert identificar_empresa(pessoa(distingue_prestadora="false"))[0] is None


def test_dois_cnpjs_ficam_separados_e_documento_sem_empresa_e_listado():
    da, ca = lote(OBRIG, pessoa())
    db, cb = lote(OBRIG, pessoa(cnpj=CNPJ_B, cpf=CPF2), primeiro_id=10)
    dx, cx = lote(["holerite", "aso"], pessoa(cnpj="11222333000182"), primeiro_id=20)  # CNPJ inválido
    dn, _ = lote(["holerite"], {}, primeiro_id=30, estado="em_revisao")
    docs, campos = da + db + dx + dn, {**ca, **cb, **cx}
    empresas, sem = agrupar_empresas(docs, campos)
    assert {c: len(v) for c, v in empresas.items()} == {CNPJ_A: 5, CNPJ_B: 5}
    assert {(s["id"], s["motivo"]) for s in sem if s["id"] in (20, 21)} == {
        (20, "CNPJ da prestadora inválido"), (21, "CNPJ da prestadora inválido")}
    assert [s["id"] for s in sem if s["id"] == 30] == [30] and "não analisado" in sem[-1]["motivo"]


def test_empresa_completa_tem_100_nos_tres_niveis():
    docs, campos = lote(OBRIG, pessoa())
    r = avaliar(docs, campos)
    assert (r["geral"]["score"], r["geral"]["classificacao"], r["geral"]["provisorio"]) == (100, "Regular", False)
    assert r["razao_social"] == "Alfa Serviços Ltda" and r["data_referencia"] == "2025-06-01"
    assert all(r["por_tipo"][t]["score"] == 100 for t in OBRIG)
    assert all(v["score"] == 100 for v in r["por_documento"].values())
    assert r["por_documento"][1]["criterios"]["completude"]["aplicavel"] is False


@pytest.mark.parametrize("score,faixa", [(100, "Regular"), (85, "Regular"), (84, "Atenção"), (65, "Atenção"),
                                         (64, "Crítico"), (0, "Crítico")])
def test_limites_de_faixa(score, faixa):
    assert classificar_score(score) == faixa


def test_arredondamento_antes_de_classificar():
    assert classificar_score(score_inteiro(84.5)) == "Regular" and classificar_score(score_inteiro(84.49)) == "Atenção"
    assert classificar_score(score_inteiro(64.5)) == "Atenção" and classificar_score(score_inteiro(64.49)) == "Crítico"


def test_obrigatorio_ausente_sem_documento_nao_identificado():
    docs, campos = lote([t for t in OBRIG if t != "folha_ponto"], pessoa())
    g = avaliar(docs, campos)["geral"]
    assert [(d["criterio"], d["tipo"], d["regra"], d["pontos"]) for d in g["descontos"]] == [
        ("completude", "folha_ponto", "obrigatorio_ausente", 8.0)]
    assert (g["score"], g["classificacao"], g["provisorio"]) == (92, "Regular", False) and fecha_em_100(g)


def test_obrigatorio_faltante_e_pendente_com_documento_nao_analisado_ou_sem_empresa():
    docs, campos = lote([t for t in OBRIG if t != "folha_ponto"], pessoa())
    nao, _ = lote(["desconhecido"], {}, primeiro_id=50, estado="em_revisao")
    g = avaliar(docs + nao, campos)["geral"]
    assert g["descontos"] == [] and g["score"] == 100 and g["provisorio"] is True
    assert any(p["criterio"] == "completude" and p["tipo"] == "folha_ponto" for p in g["pendencias"])
    # folha_ponto classificada, mas sem CNPJ válido: também pode ser a que falta
    sem, csem = lote(["folha_ponto"], pessoa(cnpj=""), primeiro_id=60)
    g = avaliar(docs + sem, {**campos, **csem})["geral"]
    assert g["descontos"] == [] and g["provisorio"] is True
    # em outro lote o documento sem empresa não interfere
    outro, coutro = lote(["folha_ponto"], pessoa(cnpj=""), primeiro_id=70, lote_id=2)
    assert [d["tipo"] for d in avaliar(docs + outro, {**campos, **coutro})["geral"]["descontos"]] == ["folha_ponto"]


def test_aso_vencido_nos_tres_niveis():
    docs, campos = lote(OBRIG, pessoa())
    campos[1]["data_exame"] = "2024-03-01"  # vence 2025-03-01
    r = avaliar(docs, campos)
    d = r["geral"]["descontos"]
    assert len(d) == 1 and (d[0]["criterio"], d[0]["tipo"], d[0]["documento"], d[0]["regra"]) == (
        "validade", "aso", 1, "documento_vencido") and "2025-03-01" in d[0]["detalhe"]
    assert d[0]["pontos"] == 17.5 and r["geral"]["score"] == 83 and fecha_em_100(r["geral"])
    assert r["por_tipo"]["aso"]["criterios"]["validade"]["nota"] == 0.0
    assert r["por_documento"][1]["criterios"]["validade"]["nota"] == 0.0
    assert r["por_documento"][1]["score"] < 100 and r["por_tipo"]["holerite"]["score"] == 100
    assert r["por_documento"][3]["criterios"]["validade"]["aplicavel"] is False  # holerite


def test_vencer_hoje_ainda_vale():
    docs, campos = lote(OBRIG, pessoa())
    campos[1]["data_exame"] = "2024-06-01"  # vence em 2025-06-01
    assert avaliar(docs, campos)["geral"]["descontos"] == []
    amanha = avaliar(docs, campos, ref=date(2025, 6, 2))["geral"]["descontos"]
    assert [x["regra"] for x in amanha] == ["documento_vencido"]


def test_contrato_indeterminado_nao_se_aplica():
    docs, campos = lote(OBRIG, pessoa())
    campos[2].update(tipo_prazo="indeterminado", data_termino="")
    r = avaliar(docs, campos)
    assert r["geral"]["criterios"]["validade"]["bons"] == 1 and r["geral"]["pendencias"] == []
    c = r["por_documento"][2]["criterios"]["validade"]
    assert c["aplicavel"] is False
    assert c["pendente"] is False and c["nota"] is None
    assert not any(p["criterio"] == "validade" for p in r["geral"]["pendencias"])
    # determinado sem data fica pendente (não zera)
    campos[2].update(tipo_prazo="determinado")
    r = avaliar(docs, campos)
    assert any(p["criterio"] == "validade" and p["documento"] == 2 for p in r["geral"]["pendencias"])
    assert r["geral"]["descontos"] == [] and r["geral"]["provisorio"] is False  # campo ausente não é provisório


def test_cpfs_diferentes_nao_divergem_e_mesmo_cpf_com_nome_divergente_sim():
    da, ca = lote(OBRIG, pessoa())
    db, cb = lote(["holerite", "aso"], pessoa(cpf=CPF2, nome="João Pereira", matricula="77"), primeiro_id=10)
    docs, campos = da + db, {**ca, **cb}
    assert avaliar(docs, campos)["geral"]["descontos"] == []  # pessoas diferentes: nada a comparar entre elas
    campos[3]["nome"] = "Mario da Silva"  # holerite da Maria, mesmo CPF
    g = avaliar(docs, campos)["geral"]
    nome = [d for d in g["descontos"] if d["campo"] == "nome"]
    assert len(nome) == 1 and nome[0]["cpf"] == CPF1 and nome[0]["conferir"] is True
    assert {"documento": 3, "tipo": "holerite", "valor": "Mario da Silva"} in nome[0]["valores"]
    assert {v["documento"] for v in nome[0]["valores"]} <= {1, 2, 3, 5}  # nunca documentos de outro CPF
    assert fecha_em_100(g) and g["score"] < 100


def test_razao_social_divergente_na_empresa():
    docs, campos = lote(OBRIG, pessoa())
    campos[4]["razao_social_prestadora"] = "Beta Comércio SA"
    g = avaliar(docs, campos)["geral"]
    assert [(d["criterio"], d["campo"]) for d in g["descontos"]] == [("consistencia", "razao_social_prestadora")]


def test_normalizacao_nome_e_cpf_formatado():
    docs, campos = lote(OBRIG, pessoa())
    campos[3]["nome"] = "  MARÍA   da silva. "
    campos[1]["cpf"] = "529.982.247-25"
    assert avaliar(docs, campos)["geral"]["descontos"] == []
    assert normalizar("data_admissao", "01/02/2024") == normalizar("data_admissao", "2024-02-01")


def test_cpf_ausente_ou_invalido_tira_o_documento_da_comparacao_com_pendencia():
    docs, campos = lote(OBRIG, pessoa())
    campos[3]["cpf"] = "52998224726"
    campos[3]["nome"] = "Outra Pessoa"  # sem CPF válido não é comparado com ninguém
    g = avaliar(docs, campos)["geral"]
    assert g["descontos"] == [] and g["provisorio"] is False
    assert {"criterio": "consistencia", "documento": 3, "tipo": "holerite",
            "motivo": "campo 'cpf' inválido"} in g["pendencias"]


def test_sem_extracao_criterios_pendentes_e_peso_redistribuido():
    docs, campos = lote(OBRIG, pessoa(data_exame="", data_termino="", nome="", cpf="", matricula="",
                                      data_admissao="", razao_social_prestadora=""))
    g = avaliar(docs, campos)["geral"]
    assert g["criterios"]["validade"]["pendente"] and g["criterios"]["consistencia"]["pendente"]
    assert g["criterios"]["completude"]["peso_efetivo"] == 100.0
    assert g["score"] == 100 and g["provisorio"] is True  # critério inteiro pendente


def test_documento_nao_analisado_nao_zera_a_nota():
    docs, campos = lote(OBRIG, pessoa())
    for estado, tipo in [("segmentado", None), ("em_revisao", "holerite"), ("erro", None), ("classificado", "desconhecido")]:
        extra, _ = lote([tipo], {}, primeiro_id=99, estado=estado)
        g = avaliar(docs + extra, campos)["geral"]
        assert g["score"] == 100 and g["provisorio"] is True and any(p["documento"] == 99 for p in g["pendencias"])


def test_soma_dos_descontos_fecha_em_100_com_varios_descontos():
    docs, campos = lote(["aso", "holerite", "folha_ponto"], pessoa(data_exame="2020-01-01"))
    campos[2]["nome"], campos[3]["matricula"] = "Ana Souza", "9"
    g = avaliar(docs, campos)["geral"]
    assert len(g["descontos"]) == 2 + 1 + 2  # 2 ausentes, 1 vencido, nome e matrícula
    assert fecha_em_100(g)
