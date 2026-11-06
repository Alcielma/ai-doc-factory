from fastapi import HTTPException


def validar_consulta(q: str) -> None:
    if not q.strip():
        raise HTTPException(400, "consulta vazia")
