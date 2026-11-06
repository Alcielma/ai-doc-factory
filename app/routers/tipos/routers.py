from fastapi import APIRouter

from app.routers.tipos import actions

router = APIRouter(tags=["Tipos"])


@router.get("/tipos")
def listar_tipos():
    """Tipos documentais na ordem da configuração (sem 'desconhecido')."""
    return actions.listar_tipos()
