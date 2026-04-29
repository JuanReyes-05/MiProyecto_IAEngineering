"""DTOs de request/response para el endpoint /ask."""
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.enums import AccionRouter


class PreguntaRequest(BaseModel):
    pregunta: str = Field(..., min_length=3, description="La pregunta del usuario.")
    usuario_id: Optional[str] = Field(
        default=None,
        min_length=3,
        description="Nombre o ID del usuario que hace la pregunta (opcional).",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "pregunta": "¿Cómo puedo restablecer mi contraseña?",
                "usuario_id": "juan.reyesl",
            }
        }
    }


class FuenteResponse(BaseModel):
    archivo: str
    fragmento: str
    pagina: Optional[int] = None
    score: Optional[float] = None


class PreguntaResponse(BaseModel):
    consulta_id: str
    respuesta: str
    accion: AccionRouter = Field(
        ...,
        description=(
            "Acción recomendada: responder | derivar_ticket | escalar_humano"
        ),
    )
    score_confianza: float = Field(
        ..., description="Nivel de confianza del agente (0.0 a 1.0)"
    )
    tiene_info: bool
    fuentes: list[FuenteResponse] = []
    modelo: str
    timestamp: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "consulta_id": "abc123",
                "respuesta": (
                    "Lamento los inconvenientes, tu ticket ha sido derivado "
                    "al área correspondiente"
                ),
                "accion": "derivar_ticket",
                "score_confianza": 0.85,
                "tiene_info": True,
                "fuentes": [
                    {
                        "archivo": "politicas.pdf",
                        "fragmento": (
                            "Según nuestras políticas de seguridad, "
                            "recomendamos cambiar tu contraseña cada 90 días."
                        ),
                        "score": 0.92,
                    }
                ],
                "modelo": "gpt-4o-mini",
                "timestamp": "2026-04-18T12:34:56Z",
            }
        }
    }
