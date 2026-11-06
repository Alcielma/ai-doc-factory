"""Testes puros da segmentação (sem banco): python -m pytest tests/test_segmentacao.py"""
import pytest

from app import segmentacao
from app.segmentacao import Documento, paginacao, segmentar

HOLERITE = "HOLERITE mensal empregador Acme Ltda competência salário base desconto INSS FGTS líquido a receber"
ATESTADO = "ATESTADO MÉDICO atesto que o paciente esteve em consulta CID afastamento dias médico CRM assinatura"
CONTRATO = "CONTRATO DE TRABALHO cláusula primeira jornada admissão empregado empregador contratação prazo"


def intervalos(docs):
    return [(d.pagina_ini, d.pagina_fim) for d in docs]


def test_paginacao_tolera_variacoes_de_ocr():
    assert paginacao("rodapé PÁGINA 1 DE 3") == (1, 3)
    assert paginacao("Pagina  2  de  3") == (2, 3)
    assert paginacao("Pág. 3/3") == (3, 3)
    assert paginacao("Página l de 2") == (1, 2)
    assert paginacao("sem paginação aqui") is None


def test_consecutivos_do_mesmo_tipo_com_pagina_k_de_n():
    textos = [
        f"{HOLERITE} Ana Silva Página 1 de 2", f"{HOLERITE} Ana Silva Página 2 de 2",
        f"{HOLERITE} Bruno Souza Página 1 de 2", f"{HOLERITE} Bruno Souza Página 2 de 2",
    ]
    assert intervalos(segmentar(textos)) == [(1, 2), (3, 4)]


def test_verso_em_branco_herdado():
    textos = [f"{HOLERITE} Página 1 de 1", "", f"{HOLERITE} outro Página 1 de 1", "  \n ."]
    assert intervalos(segmentar(textos)) == [(1, 2), (3, 4)]


def test_sem_paginacao_tipos_diferentes_abrem_documento(monkeypatch):
    monkeypatch.setattr(segmentacao.config, "SEG_SIM_BAIXO", 0.15)
    textos = [HOLERITE, HOLERITE + " continuação", ATESTADO, CONTRATO]
    docs = segmentar(textos)
    assert intervalos(docs) == [(1, 2), (3, 3), (4, 4)]
    assert not any(d.ambiguo for d in docs)


def test_faixa_ambigua_abre_documento_e_marca(monkeypatch):
    monkeypatch.setattr(segmentacao.config, "SEG_SIM_BAIXO", 0.0)
    monkeypatch.setattr(segmentacao.config, "SEG_SIM_ALTO", 1.1)
    docs = segmentar([HOLERITE, HOLERITE + " continuação"])
    assert docs == [Documento(1, 1, False), Documento(2, 2, True)]


def test_llm_pode_resolver_ambiguo(monkeypatch):
    monkeypatch.setattr(segmentacao.config, "SEG_SIM_BAIXO", 0.0)
    monkeypatch.setattr(segmentacao.config, "SEG_SIM_ALTO", 1.1)
    monkeypatch.setattr(segmentacao, "perguntar_llm_mesmo_documento", lambda a, b: True)
    assert intervalos(segmentar([HOLERITE, HOLERITE + " x"])) == [(1, 2)]


def test_texto_vazio_no_inicio_do_lote():
    textos = ["", "", f"{HOLERITE} Página 1 de 2", f"{HOLERITE} Página 2 de 2", f"{ATESTADO} Página 1 de 1"]
    assert intervalos(segmentar(textos)) == [(1, 4), (5, 5)]


def test_lote_so_de_paginas_vazias_e_lote_vazio():
    assert intervalos(segmentar(["", ""])) == [(1, 2)]
    assert segmentar([]) == []


def test_lote_de_uma_pagina():
    assert segmentar([HOLERITE]) == [Documento(1, 1, False)]


def test_intervalos_sem_buraco_nem_sobreposicao():
    textos = [HOLERITE, "", ATESTADO, ATESTADO + " dois", "", CONTRATO + " Página 1 de 2", CONTRATO + " Página 2 de 2", HOLERITE]
    docs = segmentar(textos)
    esperado = 1
    for d in docs:
        assert d.pagina_ini == esperado
        esperado = d.pagina_fim + 1
    assert esperado == len(textos) + 1


def test_reconciliar_detecta_buraco_e_sobreposicao():
    with pytest.raises(AssertionError):
        segmentacao.reconciliar([Documento(1, 1), Documento(3, 3)], 3)
    with pytest.raises(AssertionError):
        segmentacao.reconciliar([Documento(1, 2), Documento(2, 3)], 3)
    with pytest.raises(AssertionError):
        segmentacao.reconciliar([Documento(1, 2)], 3)


@pytest.mark.parametrize("texto,esperado", [
    ("Página i de 3", (1, 3)), ("Pagina L de 3", (1, 3)), ("Página 1 de o", None),
    ("Página 2 de |", None), ("Página | de 2", (1, 2)), ("Página 1 de |", (1, 1)),
    ("Página 0 de 3", None), ("Página 8 de 3", None), ("Página 2 de 3", (2, 3)),
])
def test_paginacao_ruido_e_valores_impossiveis(texto, esperado):
    assert paginacao(texto) == esperado


def test_segmentar_nao_lanca_com_pagina_i_de_2():
    docs = segmentar([f"{HOLERITE} Página i de 2", f"{HOLERITE} Página 2 de 2", f"{ATESTADO} Página 8 de 3"])
    assert docs[0].pagina_ini == 1 and docs[-1].pagina_fim == 3
