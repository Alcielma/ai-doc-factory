import pytest

from app import config
from app.classificador_regras import PALAVRAS_CHAVE, classificar
from app.roteamento import decidir

AUTO, MIN = config.CONF_AUTO, config.CONF_MIN


def test_faixas_e_limites_exatos():
    assert decidir(1.0, "aso")[:2] == ("classificado", "aso")
    assert decidir(AUTO, "aso") == ("classificado", "aso", None)  # == CONF_AUTO já é automático
    assert decidir(AUTO - 1e-9, "aso")[:2] == ("em_revisao", "aso")
    assert decidir(MIN, "aso")[:2] == ("em_revisao", "aso")  # == CONF_MIN ainda mantém o tipo sugerido
    d = decidir(MIN - 1e-9, "aso")
    assert d[:2] == ("em_revisao", config.TIPO_DESCONHECIDO) and d.motivo


def test_desconhecido_fora_de_tipos():
    assert config.TIPO_DESCONHECIDO not in config.TIPOS


def test_desacordo_manda_para_revisao_mesmo_com_confianca_alta():
    d = decidir(0.99, "aso", desacordo=True)
    assert d.estado == "em_revisao" and d.tipo == "aso" and d.motivo
    assert decidir(MIN - 0.01, "aso", desacordo=True).tipo == config.TIPO_DESCONHECIDO


def test_segmentacao_ambigua_preserva_tipo_exceto_abaixo_do_minimo():
    d = decidir(0.99, "holerite", segmentacao_ambigua=True)
    assert (d.estado, d.tipo) == ("em_revisao", "holerite") and d.motivo
    assert decidir(MIN - 0.01, "holerite", segmentacao_ambigua=True).tipo == config.TIPO_DESCONHECIDO


def test_limiares_lidos_do_config(monkeypatch):
    monkeypatch.setattr(config, "CONF_AUTO", 0.9)
    assert decidir(0.88, "aso").estado == "em_revisao"


def test_classificador_sem_palavra_chave():
    r = classificar("lorem ipsum dolor sit amet")
    assert r.tipo is None and r.confianca == 0.0 and r.modelo == "regras-v0" and r.versao_prompt is None
    assert set(r.probabilidades) == set(config.TIPOS) and sum(r.probabilidades.values()) == 0
    assert decidir(r.confianca, r.tipo).tipo == config.TIPO_DESCONHECIDO


def test_classificador_com_palavras_chave():
    r = classificar("HOLERITE\nProventos e Descontos\nLíquido a receber")
    assert r.tipo == "holerite" and r.confianca == 1.0 and abs(sum(r.probabilidades.values()) - 1) < 1e-9
    poucas = classificar("Atestado Médico")  # 1 ocorrência: confiança reduzida
    assert poucas.tipo == "atestado_medico" and poucas.confianca < config.CONF_MIN
    assert classificar("basal")  .tipo is None  # 'aso' só casa como palavra inteira


def test_palavras_chave_cobrem_exatamente_os_tipos():
    assert set(PALAVRAS_CHAVE) == set(config.TIPOS)
    for palavras in PALAVRAS_CHAVE.values():
        assert all(p == p.lower() and p.isascii() for p in palavras)
