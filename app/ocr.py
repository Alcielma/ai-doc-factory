"""Handler de segmentar_lote: rasteriza o PDF, roda Tesseract por página e grava o texto."""
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
from pdf2image import convert_from_path, pdfinfo_from_path

from app import config

log = logging.getLogger(__name__)
DPI = 150
PARALELISMO = 4


def ocr_imagem(png: Path) -> str:
    """Tesseract em português. Página em branco devolve texto vazio."""
    saida = subprocess.run(
        ["tesseract", str(png), "stdout", "-l", "por"],
        check=True, capture_output=True, text=True, encoding="utf-8",
    ).stdout
    return saida.replace("\x00", "").strip()  # Postgres não aceita NUL em TEXT


def processar_pagina(pdf: Path, pasta: Path, numero: int) -> tuple[int, str]:
    png = pasta / f"pag_{numero:04d}.png"
    imagem = convert_from_path(str(pdf), dpi=DPI, first_page=numero, last_page=numero)[0]
    imagem.save(png)
    return numero, ocr_imagem(png)


def _estado(lote_id: int, estado: str) -> None:
    with psycopg.connect(config.DATABASE_URL) as conn:
        conn.execute("UPDATE lote SET estado = %s WHERE id = %s", (estado, lote_id))


def processar_lote(payload: dict) -> None:
    lote_id = payload["lote_id"]
    pasta = Path(config.DATA_DIR) / f"lote_{lote_id}"
    pdf = pasta / "original.pdf"
    _estado(lote_id, "ocr")
    try:
        total = pdfinfo_from_path(str(pdf))["Pages"]
        with ThreadPoolExecutor(PARALELISMO) as pool:
            resultados = list(pool.map(lambda n: processar_pagina(pdf, pasta, n), range(1, total + 1)))
        with psycopg.connect(config.DATABASE_URL) as conn:
            for numero, texto in resultados:
                conn.execute(
                    "INSERT INTO pagina (lote_id, numero, texto) VALUES (%s, %s, %s) "
                    "ON CONFLICT (lote_id, numero) DO UPDATE SET texto = EXCLUDED.texto",
                    (lote_id, numero, texto),
                )
    except Exception:
        _estado(lote_id, "erro")  # o retry da fila volta o lote para 'ocr'
        raise
    log.info("lote %s: OCR de %s páginas concluído", lote_id, total)
    # PRÓXIMA ETAPA (segmentação): ler as páginas de `pagina`, criar `documento`, preencher
    # pagina.documento_id, definir lote.docs_pendentes e enfileirar classificar_documento.
    # O lote permanece em 'ocr' por enquanto.
