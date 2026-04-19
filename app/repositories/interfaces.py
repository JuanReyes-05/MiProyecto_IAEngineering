"""Contratos de la capa repository."""
from typing import Protocol

from app.domain.fragmento import Fragmento


class VectorStoreRepository(Protocol):
    """Contrato de acceso al almacén vectorial."""

    def buscar(self, query: str, k: int) -> list[Fragmento]: ...

    def contar(self) -> int: ...
