"""Classificador simples por palavras-chave (modelo 'regras-v0'), para fechar o fluxo ponta a ponta.

Interface para substituir (Jev + Gemini): `classificar(texto) -> Resultado`. O restante do sistema só usa isso.
"""
import re
import unicodedata
from typing import NamedTuple

from app import config

MODELO = "regras-v0"

# Única definição das palavras-chave, em minúsculas e sem acento (o texto é normalizado antes da busca).
PALAVRAS_CHAVE = {
    "aso": ["atestado de saude ocupacional", "aso", "apto", "exame admissional", "medico do trabalho", "pcmso"],
    "folha_pagamento": ["folha de pagamento", "resumo da folha", "total geral", "competencia", "centro de custo"],
    "folha_ponto": ["folha de ponto", "cartao de ponto", "espelho de ponto", "registro de ponto",
                    "entrada", "saida", "horas extras"],
    "holerite": ["holerite", "recibo de pagamento", "contracheque", "proventos", "descontos", "liquido a receber"],
    "recibo_ferias": ["recibo de ferias", "ferias", "periodo aquisitivo", "abono pecuniario", "gozo"],
    "atestado_medico": ["atestado medico", "cid", "afastamento", "crm", "dias de repouso"],
    "contrato_trabalho": ["contrato de trabalho", "contratante", "contratado", "clausula", "empregador", "empregado"],
}
if set(PALAVRAS_CHAVE) != set(config.TIPOS):
    raise RuntimeError(f"PALAVRAS_CHAVE diverge de config.TIPOS: {set(PALAVRAS_CHAVE) ^ set(config.TIPOS)}")

_PADROES = {
    tipo: [re.compile(rf"\b{re.escape(p)}\b") for p in palavras] for tipo, palavras in PALAVRAS_CHAVE.items()
}
_ACERTOS_PARA_CONFIANCA_PLENA = 3


class Resultado(NamedTuple):
    tipo: str | None  # None quando nenhuma palavra-chave apareceu
    confianca: float
    probabilidades: dict[str, float]
    modelo: str
    versao_prompt: str | None


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


def classificar(texto: str) -> Resultado:
    norm = _normalizar(texto)
    contagens = {t: sum(len(p.findall(norm)) for p in ps) for t, ps in _PADROES.items()}
    total = sum(contagens.values())
    if total == 0:
        return Resultado(None, 0.0, {t: 0.0 for t in config.TIPOS}, MODELO, None)
    probs = {t: c / total for t, c in contagens.items()}
    tipo = max(config.TIPOS, key=lambda t: contagens[t])  # empate: o primeiro de TIPOS
    # HEURÍSTICA, SEM CALIBRAÇÃO: fração das ocorrências de palavras-chave que apontam para o tipo vencedor,
    # reduzida quando há poucas ocorrências (menos de 3). Não é probabilidade de acerto; serve só para rotear.
    confianca = probs[tipo] * min(1.0, total / _ACERTOS_PARA_CONFIANCA_PLENA)
    return Resultado(tipo, confianca, probs, MODELO, None)
