"""Entidades de dominio relacionadas con una consulta RAG."""
from dataclasses import dataclass, field
from typing import Optional

from app.domain.fragmento import Fragmento


@dataclass
class RespuestaInterna:
    """Resultado interno producido por el orquestador RAG."""

    respuesta: str
    fragmentos: list[Fragmento] = field(default_factory=list)
    score_confianza: float = 0.0
    tiene_info: bool = True
    pregunta: str = ""
    modelo: str = ""
    requiere_derivacion: bool = False
    usuario_id: Optional[str] = None
