from fastapi import APIRouter

from app.routers.cadastro_empresas import actions
from app.routers.cadastro_empresas.schemas import NovaEmpresa

router = APIRouter()


@router.post("/cadastro-empresas", status_code=201)
def criar_empresa(corpo: NovaEmpresa):
    return actions.criar_empresa(corpo.nome)


@router.get("/cadastro-empresas")
def listar_empresas():
    return actions.listar_empresas()


@router.get("/cadastro-empresas/{empresa_id}")
def obter_empresa(empresa_id: int):
    return actions.obter_empresa(empresa_id)
