from pydantic import BaseModel, field_validator

from app.routers.cadastro_empresas import validations


class NovaEmpresa(BaseModel):
    nome: str

    @field_validator("nome")
    @classmethod
    def _nome_preenchido(cls, v: str) -> str:
        return validations.validar_nome(v)
