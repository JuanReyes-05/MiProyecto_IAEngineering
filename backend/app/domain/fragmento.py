"""Entidad de dominio: fragmento recuperado del vector store."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Fragmento:
    """Chunk de un documento con su metadata y puntaje de similitud."""

    contenido: str
    archivo: str
    pagina: Optional[int] = None
    similitud: float = 0.0
    ruta: Optional[str] = None
    tipo: Optional[str] = None
