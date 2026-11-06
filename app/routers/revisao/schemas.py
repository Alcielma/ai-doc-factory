from pydantic import BaseModel, field_validator

from app.routers.revisao import validations


class Revisao(BaseModel):
    tipo: str
    revisor: str

    @field_validator("tipo")
    @classmethod
    def _tipo_valido(cls, v: str) -> str:
        return validations.validar_tipo(v)

    @field_validator("revisor")
    @classmethod
    def _revisor_preenchido(cls, v: str) -> str:
        return validations.validar_revisor(v)
