from fastapi import APIRouter

from app.routers.empresas import actions

router = APIRouter(tags=["Conformidade"])


@router.get("/empresas")
def listar_empresas():
    """Empresas prestadoras (por CNPJ validado) com score geral e classificação."""
    return actions.listar_empresas()


@router.get("/empresas/{cnpj:path}/conformidade")
def conformidade_empresa(cnpj: str):
    """Três níveis (geral, por tipo, por documento). Aceita o CNPJ com ou sem pontuação."""
    return actions.conformidade_empresa(cnpj)


@router.get("/lotes/{lote_id}/conformidade")
def conformidade_lote(lote_id: int):
    """Empresas encontradas no lote (com o score geral de cada uma) e documentos sem empresa."""
    return actions.conformidade_lote(lote_id)
