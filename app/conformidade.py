"""Score de conformidade do lote (Goal 7): função pura, sem banco e sem LLM.

Entrada: documentos do lote (id, tipo, estado) e campos extraídos por documento.
Saída: nota por critério, score, classificação, descontos com motivo e pendências.

Convenções (documentadas aqui para o teste ser determinístico):
- Nota de um critério = bons / (bons + ruins). Itens pendentes ficam fora da conta (nunca valem zero).
- Critério sem nenhum item analisável fica pendente e o peso dele é redistribuído entre os demais
  (peso efetivo = peso / soma dos pesos dos critérios calculados). Sem critério calculado, não há score.
- score_bruto = soma(peso efetivo x nota), de 0 a 100. O score inteiro arredonda o bruto para o inteiro
  mais próximo (0,5 sobe) ANTES de classificar: 84,5 vira 85 (Regular); 84,49 vira 84 (Atenção).
- Cada item ruim desconta peso_efetivo / (bons + ruins) pontos. Os descontos são arredondados a 4 casas,
  então score_bruto + soma(descontos) = 100 com tolerância de 0,0005 por desconto
  (TOLERANCIA_ARREDONDAMENTO). O score inteiro NÃO fecha em 100 com os descontos; use o score_bruto.
- Vencer na data de referência ainda conta como válido (vence ao fim do dia).
- Valor ausente em um documento NÃO é divergência: vira pendência daquele campo.
"""
import math
import re
import unicodedata
from datetime import date, datetime

from app import config

# ---------------------------------------------------------------------------------------------
# Configuração (bloco único): pesos, faixas, obrigatórios, validade e campos de consistência.
# ---------------------------------------------------------------------------------------------
PESOS = {"completude": 40, "validade": 35, "consistencia": 25}

# (nome, score inteiro mínimo, inclusivo), da melhor para a pior faixa.
FAIXAS = (("Regular", 85), ("Atenção", 65), ("Crítico", 0))

OBRIGATORIOS = ("aso", "contrato_trabalho", "holerite", "folha_pagamento", "folha_ponto")

# Estados em que o documento já foi analisado (tipo confiável). Os demais ficam pendentes.
ESTADOS_ANALISADOS = ("classificado", "revisado")

# Regras de validade por tipo.
#  - com prazo_meses: vence `prazo_meses` meses depois da data do campo.
#  - sem prazo_meses: o campo já é a data de vencimento.
# ATENÇÃO: o prazo do ASO (12 meses) é valor de partida e PRECISA ser conferido na NR-7
# (varia conforme o tipo de exame e o risco da função).
VALIDADE = {
    "aso": {"campo": "data_exame", "prazo_meses": 12},
    "contrato_trabalho": {"campo": "data_termino"},  # contrato por prazo determinado
}

# Campos comparados entre documentos e tipos em que cada um é esperado (ausente ali = pendência).
CONSISTENCIA = {
    "nome": ("aso", "folha_pagamento", "folha_ponto", "holerite", "recibo_ferias", "atestado_medico",
             "contrato_trabalho"),
    "cpf": ("aso", "holerite", "atestado_medico", "contrato_trabalho"),
    "matricula": ("holerite", "folha_ponto", "folha_pagamento", "contrato_trabalho"),
    "data_admissao": ("holerite", "contrato_trabalho"),
}

TOLERANCIA_ARREDONDAMENTO = 0.0005  # por desconto, ver docstring

# Valida a configuração contra config.TIPOS (falha ao importar se houver tipo inexistente).
_usados = set(OBRIGATORIOS) | set(VALIDADE) | {t for ts in CONSISTENCIA.values() for t in ts}
if not _usados <= set(config.TIPOS):
    raise ValueError(f"tipos fora de config.TIPOS: {sorted(_usados - set(config.TIPOS))}")


# ---------------------------------------------------------------------------------------------
# Normalização e datas
# ---------------------------------------------------------------------------------------------
def parse_data(valor) -> date | None:
    """Aceita date, 'AAAA-MM-DD' e 'DD/MM/AAAA'. Devolve None se ilegível."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    s = str(valor or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def normalizar(campo: str, valor) -> str:
    """Forma canônica para comparar: sem acento, caixa baixa, espaços e pontuação removidos."""
    s = "".join(c for c in unicodedata.normalize("NFKD", str(valor)) if not unicodedata.combining(c))
    s = s.lower().strip()
    if campo == "cpf":
        return re.sub(r"\D", "", s)
    if campo == "data_admissao":
        d = parse_data(valor)
        if d:
            return d.isoformat()
    if campo == "matricula":
        return re.sub(r"[^a-z0-9]", "", s)
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s)).strip()  # nome e demais


def _somar_meses(d: date, meses: int) -> date:
    m = d.month - 1 + meses
    ano, mes = d.year + m // 12, m % 12 + 1
    bissexto = ano % 4 == 0 and (ano % 100 != 0 or ano % 400 == 0)
    dias = [31, 29 if bissexto else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1]
    return date(ano, mes, min(d.day, dias))


def score_inteiro(bruto: float) -> int:
    """Arredonda para o inteiro mais próximo, 0,5 sobe. A faixa é decidida sobre este valor."""
    return math.floor(round(bruto, 6) + 0.5)


def classificar_score(score: int) -> str:
    return next(nome for nome, minimo in FAIXAS if score >= minimo)


# ---------------------------------------------------------------------------------------------
# Cálculo
# ---------------------------------------------------------------------------------------------
def calcular(documentos: list[dict], campos: dict, data_referencia: date) -> dict:
    """documentos: [{id, tipo, estado}]; campos: {documento_id: {campo: valor}}."""
    analisados = [d for d in documentos if d.get("estado") in ESTADOS_ANALISADOS and d.get("tipo") in config.TIPOS]
    nao_analisados = [d for d in documentos if d not in analisados]
    pendencias: list[dict] = []
    for d in nao_analisados:
        pendencias.append({"criterio": "geral", "documento": d["id"], "tipo": d.get("tipo"),
                           "motivo": f"documento não analisado (estado '{d.get('estado')}', tipo '{d.get('tipo')}')"})

    itens: dict[str, tuple[int, list[dict]] | None] = {}  # (bons, ruins); None = pendente

    # Completude: só é calculável se houver ao menos um documento analisado.
    if analisados:
        presentes = {d["tipo"] for d in analisados}
        faltantes = [t for t in OBRIGATORIOS if t not in presentes]
        ruins = []
        for t in faltantes:
            if nao_analisados:  # pode estar num documento de tipo não identificado
                pendencias.append({"criterio": "completude", "documento": None, "tipo": t,
                                   "motivo": "obrigatório não encontrado, mas há documento não identificado"})
            else:
                ruins.append({"documento": None, "tipo": t, "regra": "obrigatorio_ausente",
                              "detalhe": f"documento obrigatório '{t}' não foi enviado"})
        bons = len(OBRIGATORIOS) - len(faltantes)
        itens["completude"] = (bons, ruins) if bons + len(ruins) else None
    else:
        itens["completude"] = None

    # Validade
    bons, ruins = 0, []
    for d in analisados:
        regra = VALIDADE.get(d["tipo"])
        if not regra:
            continue
        base = parse_data(campos.get(d["id"], {}).get(regra["campo"]))
        if base is None:
            pendencias.append({"criterio": "validade", "documento": d["id"], "tipo": d["tipo"],
                               "motivo": f"campo '{regra['campo']}' ausente ou ilegível"})
            continue
        venc = _somar_meses(base, regra["prazo_meses"]) if "prazo_meses" in regra else base
        if data_referencia <= venc:  # vence hoje ainda vale
            bons += 1
        else:
            ruins.append({"documento": d["id"], "tipo": d["tipo"], "regra": "documento_vencido",
                          "detalhe": f"venceu em {venc.isoformat()} (referência {data_referencia.isoformat()})"})
    itens["validade"] = (bons, ruins) if bons + len(ruins) else None

    # Consistência
    bons, ruins = 0, []
    for campo, tipos in CONSISTENCIA.items():
        valores = []  # (documento, valor original, valor normalizado)
        for d in analisados:
            if d["tipo"] not in tipos:
                continue
            v = campos.get(d["id"], {}).get(campo)
            if v is None or not str(v).strip():
                pendencias.append({"criterio": "consistencia", "documento": d["id"], "tipo": d["tipo"],
                                   "motivo": f"campo '{campo}' ausente"})
            else:
                valores.append((d, v, normalizar(campo, v)))
        if len(valores) < 2:
            continue  # nada a comparar
        if len({n for _, _, n in valores}) == 1:
            bons += 1
        else:
            ruins.append({"documento": None, "tipo": None, "regra": "campo_divergente", "campo": campo,
                          "conferir": True, "detalhe": f"valores diferentes para '{campo}'",
                          "valores": [{"documento": d["id"], "tipo": d["tipo"], "valor": v}
                                      for d, v, _ in valores]})
    itens["consistencia"] = (bons, ruins) if bons + len(ruins) else None

    # Pesos efetivos, notas e descontos
    calculados = {c: v for c, v in itens.items() if v is not None}
    for c in PESOS:
        if c not in calculados:
            pendencias.append({"criterio": c, "documento": None, "tipo": None,
                               "motivo": "nada analisável neste critério; peso redistribuído"})
    soma_pesos = sum(PESOS[c] for c in calculados)
    criterios, descontos, bruto = {}, [], 0.0
    for c in PESOS:
        if c not in calculados:
            criterios[c] = {"peso": PESOS[c], "peso_efetivo": None, "nota": None, "pendente": True}
            continue
        bons, ruins = calculados[c]
        total = bons + len(ruins)
        peso_ef = PESOS[c] * 100 / soma_pesos
        nota = bons / total
        bruto += peso_ef * nota
        criterios[c] = {"peso": PESOS[c], "peso_efetivo": round(peso_ef, 4), "nota": round(nota, 4),
                        "pendente": False, "bons": bons, "ruins": len(ruins)}
        for r in ruins:
            descontos.append({"criterio": c, **r, "pontos": round(peso_ef / total, 4)})

    resultado = {"data_referencia": data_referencia.isoformat(), "score": None, "score_bruto": None,
                 "classificacao": None, "provisorio": bool(pendencias), "criterios": criterios,
                 "descontos": descontos, "pendencias": pendencias}
    if calculados:
        bruto = round(bruto, 6)  # elimina ruído de ponto flutuante antes de arredondar
        score = score_inteiro(bruto)
        resultado.update(score=score, score_bruto=round(bruto, 4), classificacao=classificar_score(score))
    return resultado
