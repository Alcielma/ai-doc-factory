from fastapi import HTTPException

from app.imagem import ArquivoInvalido, imagem_para_pdf


def converter_para_pdf(dados: bytes) -> bytes:
    """PDF passa direto; imagem é convertida. Arquivo inválido vira 400 (antes de tocar no banco)."""
    if dados.startswith(b"%PDF"):
        return dados
    try:
        return imagem_para_pdf(dados)
    except ArquivoInvalido as e:
        raise HTTPException(400, str(e))
