from pydantic import BaseModel, field_validator

from app.routers.documentos import validations


class AtualizacaoCampos(BaseModel):
    campos: dict[str, str | None]
    revisor: str

    @field_validator("campos")
    @classmethod
    def _campos_validos(cls, v: dict) -> dict:
        return validations.validar_campos(v)

    @field_validator("revisor")
    @classmethod
    def _revisor_preenchido(cls, v: str) -> str:
        return validations.validar_revisor(v)
