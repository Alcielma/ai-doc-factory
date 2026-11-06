"""Chamadas HTTP ao Jev (OpenRouter) e ao Gemini, com nova tentativa e cache em disco.

Cache: chave = sha256(modelo + corpo da requisição), e o corpo já contém entrada e prompt. Só o corpo da
resposta (JSON) é guardado: cabeçalhos e chaves nunca entram. Respostas de erro nunca entram.
"""
import base64
import hashlib
import json
import logging
import os
import time
from pathlib import Path

import httpx

from app import config

log = logging.getLogger(__name__)

JEV_URL = "https://openrouter.ai/api/alpha/decisions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"


class LLMErro(Exception):
    """Falha definitiva da chamada (sem nova tentativa útil, ou tentativas esgotadas)."""


def _enviar(url: str, headers: dict, corpo: dict) -> httpx.Response:
    return httpx.post(url, headers=headers, json=corpo, timeout=config.LLM_TIMEOUT)


def _com_tentativas(url: str, headers: dict, corpo: dict) -> dict:
    """429, 5xx e erros de rede: espera e tenta de novo. Outros 4xx falham na hora."""
    ultimo = ""
    for tentativa in range(config.LLM_TENTATIVAS):
        if tentativa:
            time.sleep(config.LLM_ESPERA * 2 ** (tentativa - 1))
        try:
            r = _enviar(url, headers, corpo)
        except httpx.TransportError as e:
            ultimo = f"rede: {type(e).__name__}"
            log.warning("llm: %s (tentativa %s)", ultimo, tentativa + 1)
            continue
        if r.status_code == 429 or r.status_code >= 500:
            ultimo = f"HTTP {r.status_code}"
            log.warning("llm: %s (tentativa %s)", ultimo, tentativa + 1)
            continue
        if r.status_code >= 400:
            raise LLMErro(f"HTTP {r.status_code}")  # não registra o corpo: pode ecoar a requisição
        try:
            return r.json()
        except ValueError as e:
            raise LLMErro("resposta não é JSON") from e
    raise LLMErro(f"esgotadas {config.LLM_TENTATIVAS} tentativas ({ultimo})")


def _chamar_com_cache(modelo: str, url: str, headers: dict, corpo: dict, valida=None) -> dict:
    chave = hashlib.sha256(json.dumps([modelo, corpo], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    arquivo = Path(config.CACHE_DIR) / f"{chave}.json"
    try:
        return json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    resposta = _com_tentativas(url, headers, corpo)
    if valida:
        valida(resposta)  # resposta malformada vira LLMErro e não entra no cache
    log.info("llm_chamada modelo=%s usage=%s", modelo, json.dumps(_uso(resposta)))
    try:
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        tmp = arquivo.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(resposta, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, arquivo)  # escrita atômica
    except OSError:
        log.warning("llm: cache indisponível, seguindo sem gravar")
    return resposta


def _uso(resposta: dict) -> dict:
    return resposta.get("usage") or resposta.get("usageMetadata") or {}


def jev_decidir(state: str | dict, questions: dict, valida=None) -> dict:
    """POST /decisions do Jev. Devolve o JSON completo (model, answers, usage...)."""
    if not config.JEV_MODEL:
        raise LLMErro("JEV_MODEL não definido")
    corpo = {"model": config.JEV_MODEL, "state": state, "questions": questions}
    headers = {"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"}

    def valida_base(r):
        if not isinstance(r.get("answers"), dict):
            raise LLMErro("resposta do Jev sem 'answers'")
        if valida:
            valida(r)
    return _chamar_com_cache(config.JEV_MODEL, JEV_URL, headers, corpo, valida_base)


def _prob_noul(resp: dict) -> float:
    try:
        p = float(resp["answers"]["q"]["noul"])
    except (KeyError, TypeError, ValueError) as e:
        raise LLMErro("resposta noul do Jev fora do formato esperado") from e
    if not 0.0 <= p <= 1.0:
        raise LLMErro("probabilidade noul fora de [0, 1]")
    return p


def jev_sim_nao(state: dict, pergunta: str, criterios: dict | None = None) -> float:
    """Pergunta Sim/Não (tipo 'noul'): devolve P(sim), em answers.<id>.noul. Alto = sim; 0.5 = incerteza."""
    q = {"type": "noul", "instructions": pergunta}
    if criterios:
        q["criteria"] = criterios
    resp = jev_decidir(state, {"q": q}, _prob_noul)
    return _prob_noul(resp)


def gemini_gerar(prompt: str, schema: dict, imagem_png: bytes | None = None) -> dict:
    """generateContent do Gemini com resposta JSON estruturada. Devolve o JSON completo (inclui modelVersion)."""
    partes = [{"text": prompt}]
    if imagem_png:
        partes.append({"inlineData": {"mimeType": "image/png", "data": base64.b64encode(imagem_png).decode()}})
    corpo = {
        "contents": [{"parts": partes}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema},
    }
    modelo = config.GEMINI_MODEL
    headers = {"x-goog-api-key": config.GEMINI_API_KEY}
    return _chamar_com_cache(modelo, GEMINI_URL.format(modelo=modelo), headers, corpo, texto_gemini)


def texto_gemini(resposta: dict) -> dict:
    """JSON gerado pelo Gemini (candidates[0].content.parts[0].text)."""
    try:
        return json.loads(resposta["candidates"][0]["content"]["parts"][0]["text"])
    except (KeyError, IndexError, TypeError, ValueError) as e:
        raise LLMErro("resposta do Gemini fora do formato esperado") from e
