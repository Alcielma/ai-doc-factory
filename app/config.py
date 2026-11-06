"""Configuração única: tipos documentais, limiares e conexões (tudo vindo do ambiente)."""
import os

TIPOS = (
    "aso",
    "folha_pagamento",
    "folha_ponto",
    "holerite",
    "recibo_ferias",
    "atestado_medico",
    "contrato_trabalho",
)

CONF_AUTO = float(os.getenv("CONF_AUTO", "0.85"))
CONF_MIN = float(os.getenv("CONF_MIN", "0.50"))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://docfactory:docfactory@localhost:5432/docfactory")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATA_DIR = os.getenv("DATA_DIR", "/data")

FILA_SEGMENTAR = "segmentar_lote"
FILA_CLASSIFICAR = "classificar_documento"
MAX_TENTATIVAS = 3

# Segmentação: similaridade TF-IDF (cosseno) entre páginas consecutivas.
# Abaixo de SEG_SIM_BAIXO abre documento; a partir de SEG_SIM_ALTO continua; entre os dois é ambíguo.
# Valores iniciais NÃO calibrados com dados do gerador: ajustar depois com scripts/avaliar_segmentacao.py.
SEG_SIM_BAIXO = float(os.getenv("SEG_SIM_BAIXO", "0.15"))
SEG_SIM_ALTO = float(os.getenv("SEG_SIM_ALTO", "0.60"))
