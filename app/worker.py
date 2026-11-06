"""Workers. Uso: python -m app.worker <fila>. A classificação ainda é stub (app/classificar.py)."""
import logging
import sys

import redis

from app import config
from app.filas import rodar_worker
from app.classificar import classificar_documento
from app.ocr import processar_lote


HANDLERS = {
    config.FILA_SEGMENTAR: processar_lote,
    config.FILA_CLASSIFICAR: classificar_documento,
}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    fila = sys.argv[1]
    rodar_worker(redis.Redis.from_url(config.REDIS_URL, decode_responses=True), fila, HANDLERS[fila])
