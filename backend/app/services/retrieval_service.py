"""Service de recuperación semántica sobre la base vectorial."""
from app.core.config import Settings
from app.domain.fragmento import Fragmento
from app.repositories.interfaces import VectorStoreRepository


class RetrievalServiceImpl:
    """Recupera fragmentos relevantes usando el VectorStoreRepository."""

    def __init__(self, repository: VectorStoreRepository, settings: Settings):
        self._repository = repository
        self._settings = settings

    def recuperar(self, pregunta: str) -> list[Fragmento]:
        return self._repository.buscar(pregunta, k=self._settings.top_k)
