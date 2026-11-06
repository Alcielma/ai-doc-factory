from app import config


def validar_tipo(v: str) -> str:
    if v not in config.TIPOS:
        raise ValueError(f"tipo inválido; use um de {list(config.TIPOS)}")
    return v


def validar_revisor(v: str) -> str:
    if not v.strip():
        raise ValueError("revisor não pode ser vazio")
    return v.strip()
