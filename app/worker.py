"""Workers. Uso: python -m app.worker <fila>. Classificação em app/classificar.py."""
import logging
import sys

import redis

from app import config
from app.filas import rodar_worker
from app.classificar import classificar_documento, marcar_erro
from app.extracao import extrair_campos
from app.ocr import processar_lote


HANDLERS = {
    config.FILA_SEGMENTAR: processar_lote,
    config.FILA_CLASSIFICAR: classificar_documento,
    config.FILA_EXTRAIR: extrair_campos,
}

AO_ESGOTAR = {config.FILA_CLASSIFICAR: marcar_erro}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    fila = sys.argv[1]
    rodar_worker(redis.Redis.from_url(config.REDIS_URL, decode_responses=True), fila, HANDLERS[fila], AO_ESGOTAR.get(fila))
