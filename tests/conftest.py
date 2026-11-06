"""Testes nunca chamam a rede: _enviar é bloqueado, o cache vai para um diretório temporário e o
classificador padrão é o de regras. Testes de LLM trocam _enviar por um mock e CLASSIFICADOR por 'jev'."""
import httpx
import pytest

from app import config, llm


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch, tmp_path):
    def bloqueado(url, headers, corpo):
        raise httpx.ConnectError("rede bloqueada nos testes")
    monkeypatch.setattr(llm, "_enviar", bloqueado)
    monkeypatch.setattr(config, "CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(config, "CLASSIFICADOR", "regras")
    monkeypatch.setattr(config, "LLM_ESPERA", 0.0)
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "chave-falsa-teste")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "chave-falsa-teste")
    monkeypatch.setattr(config, "JEV_MODEL", "jev-teste")


@pytest.fixture(autouse=True)
def extracoes(monkeypatch):
    """Não enfileira extração de verdade (o worker do compose chamaria o Gemini). Devolve os ids pedidos."""
    from app import extracao
    from app.routers.revisao import actions as revisao_actions
    pedidas = []

    def registrar(documento_id, r=None):
        pedidas.append(documento_id)
    registrar.__wrapped__ = extracao.enfileirar_extracao  # a função real, para testá-la
    monkeypatch.setattr(extracao, "enfileirar_extracao", registrar)
    monkeypatch.setattr(revisao_actions, "enfileirar_extracao", registrar)
    return pedidas
