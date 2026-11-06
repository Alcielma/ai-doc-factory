from app import config


def listar_tipos() -> list[dict]:
    return [{"slug": slug, "nome": info["nome"], "icone": info["icone"]} for slug, info in config.TIPOS_INFO.items()]
