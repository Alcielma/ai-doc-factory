"""Converte imagens enviadas (JPEG, PNG, TIFF, inclusive multipágina) em um PDF, para o resto do fluxo não mudar."""
import io
import warnings

from PIL import Image, ImageOps

FORMATOS = {"JPEG", "PNG", "TIFF"}
# O OCR rasteriza a 150 dpi (app.ocr.DPI). Gravar o PDF com a mesma resolução faz cada página voltar
# com exatamente a largura e a altura em pixels da imagem original: nada encolhe nem é reamostrado.
DPI_PDF = 150.0
QUALIDADE_JPEG = 95


class ArquivoInvalido(ValueError):
    """Arquivo que não é PDF nem imagem suportada, ou imagem corrompida ou grande demais."""


def _para_rgb(im: Image.Image) -> Image.Image:
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        fundo = Image.new("RGB", im.size, "white")
        fundo.paste(im, mask=im.getchannel("A"))
        return fundo
    return im.convert("RGB")


def imagem_para_pdf(dados: bytes) -> bytes:
    """Devolve os bytes de um PDF com uma página por quadro da imagem. Levanta ArquivoInvalido."""
    try:
        # o aviso de "bomba de descompressão" (acima de MAX_IMAGE_PIXELS) vira erro: o limite do Pillow é mantido
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(dados)) as im:
                if im.format not in FORMATOS:
                    raise ArquivoInvalido("formato não suportado: envie PDF, JPEG, PNG ou TIFF")
                paginas = []
                for n in range(getattr(im, "n_frames", 1)):
                    im.seek(n)
                    quadro = ImageOps.exif_transpose(im)  # corrige a orientação de fotos de celular
                    paginas.append(_para_rgb(quadro))  # convert() também carrega os pixels (detecta truncamento)
        saida = io.BytesIO()
        paginas[0].save(
            saida, "PDF", resolution=DPI_PDF, quality=QUALIDADE_JPEG,
            save_all=True, append_images=paginas[1:],
        )
        return saida.getvalue()
    except ArquivoInvalido:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as e:
        raise ArquivoInvalido("imagem grande demais") from e
    except (OSError, SyntaxError, ValueError, EOFError) as e:  # inclui UnidentifiedImageError e imagem truncada
        raise ArquivoInvalido("arquivo não é PDF nem imagem válida (JPEG, PNG ou TIFF)") from e
