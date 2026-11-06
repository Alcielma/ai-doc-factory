"""Roteamento por confiança (Goal 5). Função pura: sem banco, sem rede, sem LLM."""
from typing import NamedTuple

from app import config

MOTIVO_CONF_BAIXA = "confianca_baixa"
MOTIVO_CONF_INTERMEDIARIA = "confianca_intermediaria"
MOTIVO_DESACORDO = "desacordo_modelos"
MOTIVO_SEG_AMBIGUA = "segmentacao_ambigua"
MOTIVO_NENHUM = "nenhum_dos_anteriores"  # o Jev disse que não é de nenhum tipo conhecido


class Decisao(NamedTuple):
    estado: str  # 'classificado' ou 'em_revisao'
    tipo: str | None  # tipo sugerido, ou config.TIPO_DESCONHECIDO
    motivo: str | None  # None quando classificado


def decidir(confianca: float, tipo_sugerido: str | None, desacordo: bool = False,
            segmentacao_ambigua: bool = False) -> Decisao:
    """Os limiares são lidos de config a cada chamada. Abaixo de CONF_MIN o tipo é sempre 'desconhecido'
    (vale também com desacordo ou segmentação ambígua); nos demais casos de revisão o tipo sugerido é mantido."""
    if tipo_sugerido == config.TIPO_DESCONHECIDO:  # "nenhum dos anteriores": revisão, qualquer que seja a confiança
        return Decisao("em_revisao", config.TIPO_DESCONHECIDO, MOTIVO_NENHUM)
    if confianca < config.CONF_MIN:
        return Decisao("em_revisao", config.TIPO_DESCONHECIDO, MOTIVO_CONF_BAIXA)
    if desacordo:
        return Decisao("em_revisao", tipo_sugerido, MOTIVO_DESACORDO)
    if segmentacao_ambigua:
        return Decisao("em_revisao", tipo_sugerido, MOTIVO_SEG_AMBIGUA)
    if confianca < config.CONF_AUTO:
        return Decisao("em_revisao", tipo_sugerido, MOTIVO_CONF_INTERMEDIARIA)
    return Decisao("classificado", tipo_sugerido, None)
