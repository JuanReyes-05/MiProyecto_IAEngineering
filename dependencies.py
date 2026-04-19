"""
dependencies.py — Inyección de dependencias para FastAPI.

Patrón recomendado (https://fastapi.tiangolo.com/tutorial/dependencies/):
- `SettingsDep` → inyecta el singleton cacheado de Settings.
- `RAGDep`     → inyecta el RAGChain inicializado en el lifespan (via app.state).
Permite sustituir ambos en tests con `app.dependency_overrides`.
"""
from typing import Annotated

from fastapi import Depends, Request

from config import Settings, get_settings
from rag_chain import RAGChain


def get_rag(request: Request) -> RAGChain:
    rag = getattr(request.app.state, "rag", None)
    if rag is None:
        raise RuntimeError(
            "RAGChain no disponible en app.state. "
            "Verifica la inicialización en el lifespan."
        )
    return rag


SettingsDep = Annotated[Settings, Depends(get_settings)]
RAGDep = Annotated[RAGChain, Depends(get_rag)]
