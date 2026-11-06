"""Rodar no compose: docker compose exec api python -m pytest tests (precisa de Tesseract, só existe na imagem)."""
from PIL import Image, ImageDraw, ImageFont

from app.ocr import ocr_imagem

FONTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def test_pagina_em_branco_devolve_texto_vazio(tmp_path):
    png = tmp_path / "branco.png"
    Image.new("RGB", (1240, 1754), "white").save(png)
    assert ocr_imagem(png) == ""


def test_ocr_portugues_com_acento(tmp_path):
    png = tmp_path / "texto.png"
    im = Image.new("RGB", (1240, 400), "white")
    ImageDraw.Draw(im).text((50, 50), "Funcionário: Zeferino Tavares", fill="black", font=ImageFont.truetype(FONTE, 30))
    im.save(png)
    assert "Funcionário: Zeferino" in ocr_imagem(png)
