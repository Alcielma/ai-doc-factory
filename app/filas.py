"""Filas Redis com ack: BLMOVE fila -> fila:proc, retry 3x, depois dlq."""
import json
import logging
from typing import Callable

import redis

from app.config import MAX_TENTATIVAS

log = logging.getLogger(__name__)
DLQ = "dlq"


def enfileirar(r: redis.Redis, fila: str, payload: dict, tentativas: int = 0) -> None:
    r.lpush(fila, json.dumps({"payload": payload, "tentativas": tentativas, "fila": fila}))


def recuperar_presos(r: redis.Redis, fila: str) -> int:
    """Devolve para a fila os jobs presos em fila:proc (chamar ao subir o worker)."""
    n = 0
    while r.lmove(f"{fila}:proc", fila, "LEFT", "RIGHT"):
        n += 1
    return n


def processar_um(r: redis.Redis, fila: str, handler: Callable[[dict], None], timeout: int = 5) -> bool:
    """Consome um job. Ack (remoção de :proc) só após sucesso. Retorna False se a fila estava vazia."""
    proc = f"{fila}:proc"
    bruto = r.blmove(fila, proc, timeout, "RIGHT", "LEFT")
    if bruto is None:
        return False
    job = json.loads(bruto)
    try:
        handler(job["payload"])
    except Exception:
        job["tentativas"] += 1
        destino = DLQ if job["tentativas"] >= MAX_TENTATIVAS else fila
        log.exception("job falhou (tentativa %s/%s) -> %s", job["tentativas"], MAX_TENTATIVAS, destino)
        # reenfileira antes de remover de :proc, para nunca perder o job
        r.lpush(destino, json.dumps(job))
    r.lrem(proc, 1, bruto)
    return True


def rodar_worker(r: redis.Redis, fila: str, handler: Callable[[dict], None]) -> None:
    n = recuperar_presos(r, fila)
    log.info("worker ouvindo %s (%s jobs recuperados de %s:proc)", fila, n, fila)
    while True:
        processar_um(r, fila, handler)
