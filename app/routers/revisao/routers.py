from fastapi import APIRouter

from app.routers.revisao import actions
from app.routers.revisao.schemas import Revisao

router = APIRouter()


@router.get("/revisao")
def fila_revisao():
    return actions.fila_revisao()


@router.post("/documentos/{documento_id}/revisao")
def revisar_documento(documento_id: int, revisao: Revisao):
    return actions.revisar_documento(documento_id, revisao)
