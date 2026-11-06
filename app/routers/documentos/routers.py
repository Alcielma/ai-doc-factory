from fastapi import APIRouter

from app.routers.documentos import actions

router = APIRouter()


@router.get("/documentos/{documento_id}")
def obter_documento(documento_id: int):
    return actions.obter_documento(documento_id)


@router.get("/documentos/{documento_id}/analise-ponto")
def analise_ponto(documento_id: int):
    """Apoio à auditoria, não parecer jurídico; convenção coletiva e acordo de compensação podem alterar os limites."""
    return actions.obter_analise_ponto(documento_id)
