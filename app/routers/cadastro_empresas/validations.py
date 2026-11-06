def validar_nome(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("nome não pode ser vazio")
    return v
