"""DTOs de los endpoints de sistema."""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    estado: str
    version: str
    estadisticas: dict
    timestamp: str
