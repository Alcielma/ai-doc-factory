"""Segmentação de lote em documentos, sem LLM. Função pura: lista de textos por página -> documentos."""
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass

from app import config, llm, prompts

log = logging.getLogger(__name__)

# "Página 1 de 3", tolerando caixa, espaços, "Pag."/"Pág", "1/3" e confusões comuns do OCR (l/I/|/O no lugar de 1/0).
_PAGINACAO = re.compile(r"\bp[aá4]g(?:ina|\.)?\s*([0-9lLiI|oO]{1,3})\s*(?:de|/)\s*([0-9lLiI|oO]{1,3})(?!\w)", re.IGNORECASE)
_TOKEN = re.compile(r"\w{2,}")


@dataclass(frozen=True)
class Documento:
    pagina_ini: int  # 1-based, inclusivo
    pagina_fim: int
    ambiguo: bool = False


def _num(s: str) -> int:
    return int(s.translate(str.maketrans("lLiI|oO", "1111100")))


def paginacao(texto: str) -> tuple[int, int] | None:
    """(k, N) da última ocorrência de 'Página k de N' (rodapé), ou None."""
    achados = _PAGINACAO.findall(texto)
    if not achados:
        return None
    k, n = achados[-1]
    k, n = _num(k), _num(n)
    if k < 1 or n < 1 or k > n:
        return None  # paginação impossível: cai na cascata TF-IDF
    return k, n


def em_branco(texto: str) -> bool:
    return sum(c.isalnum() for c in texto) < 3  # ruído de scanner não conta como conteúdo


def _tokens(texto: str) -> Counter:
    return Counter(_TOKEN.findall(texto.lower()))


def _vetores_tfidf(textos: list[str]) -> list[dict[str, float]]:
    contagens = [_tokens(t) for t in textos]
    df = Counter(tok for c in contagens for tok in c)
    n = len(textos)
    vetores = []
    for c in contagens:
        v = {tok: (1 + math.log(f)) * (math.log((1 + n) / (1 + df[tok])) + 1) for tok, f in c.items()}
        norma = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vetores.append({tok: x / norma for tok, x in v.items()})
    return vetores


def _cosseno(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(tok, 0.0) for tok, x in a.items())


def perguntar_llm_mesmo_documento(fim_anterior: str, inicio_atual: str) -> bool | None:
    """Faixa ambígua: 'estas duas páginas pertencem ao mesmo documento?' (Sim/Não 'noul' do Jev).

    True = continua; False = abre documento novo; None = meio da faixa ou LLM indisponível (o chamador abre
    documento novo e marca ambiguo=True). Os limiares são decididos aqui, em código (config.SEG_LLM_*).
    Nunca levanta por falha do LLM. Faz chamada de rede: não chamar dentro de transação de banco.
    """
    if config.CLASSIFICADOR == "regras":
        return None  # modo sem rede: nenhum trecho do documento sai do sistema
    estado = {"pagina_anterior": {"fim": fim_anterior}, "pagina_atual": {"inicio": inicio_atual}}
    try:
        p = llm.jev_sim_nao(estado, prompts.PERGUNTA_FRONTEIRA, prompts.CRITERIOS_FRONTEIRA)
    except llm.LLMErro as e:
        log.warning("fronteira: LLM indisponível (%s); mantendo ambíguo", e)
        return None
    if p >= config.SEG_LLM_CONTINUA:
        return True
    if p <= config.SEG_LLM_ABRE:
        return False
    return None


def segmentar(textos: list[str]) -> list[Documento]:
    """Cascata: branco herda -> 'Página k de N' -> TF-IDF -> ambíguo (LLM, hoje abre novo e marca)."""
    if not textos:
        return []
    vetores = _vetores_tfidf(textos)
    inicios: list[tuple[int, bool]] = [(0, False)]  # (índice da página, ambíguo)
    ref = None  # última página não vazia do documento corrente
    if not em_branco(textos[0]):
        ref = 0
    for i in range(1, len(textos)):
        texto = textos[i]
        if em_branco(texto):
            continue  # herda o documento anterior (também vale para verso em branco)
        if ref is None:
            # documento corrente só tem páginas em branco (início do lote): o conteúdo as absorve
            ref = i
            continue
        pag = paginacao(texto)
        if pag is not None and pag[0] == 1:
            inicios.append((i, False))
        elif pag is not None and pag[0] > 1:
            pass  # continua
        else:
            sim = _cosseno(vetores[ref], vetores[i])
            if sim < config.SEG_SIM_BAIXO:
                inicios.append((i, False))
            elif sim >= config.SEG_SIM_ALTO:
                pass
            else:
                mesmo = perguntar_llm_mesmo_documento(textos[ref][-500:], texto[:500])
                if mesmo is None:
                    inicios.append((i, True))
                elif not mesmo:
                    inicios.append((i, False))
        ref = i
    docs = []
    for j, (ini, amb) in enumerate(inicios):
        fim = inicios[j + 1][0] if j + 1 < len(inicios) else len(textos)
        docs.append(Documento(ini + 1, fim, amb))
    reconciliar(docs, len(textos))
    return docs


def reconciliar(docs: list[Documento], total: int) -> None:
    """Toda página em exatamente um documento: sem buracos e sem sobreposição."""
    esperado = 1
    for d in docs:
        assert d.pagina_ini == esperado, f"buraco ou sobreposição em {d}: esperado início {esperado}"
        assert d.pagina_fim >= d.pagina_ini, f"intervalo invertido em {d}"
        esperado = d.pagina_fim + 1
    assert esperado == total + 1, f"páginas sem documento: cobertas {esperado - 1} de {total}"
