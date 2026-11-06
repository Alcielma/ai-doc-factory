"""Workers. Uso: python -m app.worker <fila>. Handlers são stubs (etapas seguintes)."""
import logging
import sys

import redis

from app import config
from app.filas import rodar_worker


def stub(nome: str):
    def handler(payload: dict) -> None:
        logging.getLogger(nome).info("job recebido: %s", payload)
    return handler


HANDLERS = {
    config.FILA_SEGMENTAR: stub("segmentar_lote"),
    config.FILA_CLASSIFICAR: stub("classificar_documento"),
}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    fila = sys.argv[1]
    rodar_worker(redis.Redis.from_url(config.REDIS_URL, decode_responses=True), fila, HANDLERS[fila])
