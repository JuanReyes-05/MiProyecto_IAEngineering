"""Implementación del VectorStoreRepository sobre ChromaDB."""
import logging
from typing import Optional

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import Settings
from app.domain.fragmento import Fragmento

logger = logging.getLogger(__name__)


class ChromaRepository:
    """Encapsula las llamadas a ChromaDB vía LangChain."""

    def __init__(self, settings: Settings, embeddings: HuggingFaceEmbeddings):
        self._settings = settings
        self._store = Chroma(
            collection_name=settings.collection_name,
            embedding_function=embeddings,
            persist_directory=settings.chroma_dir,
        )

    def buscar(self, query: str, k: int) -> list[Fragmento]:
        """Similarity search con umbral mínimo de score > 0.10."""
        resultados_raw = self._store.similarity_search_with_score(
            query=query, k=k
        )
        fragmentos: list[Fragmento] = []
        for doc, dist in resultados_raw:
            score = 1 / (1 + dist)
            if score <= 0.10:
                continue
            fragmentos.append(
                Fragmento(
                    contenido=doc.page_content,
                    archivo=doc.metadata.get("archivo", "Desconocido"),
                    pagina=doc.metadata.get("page"),
                    similitud=score,
                    ruta=doc.metadata.get("ruta"),
                    tipo=doc.metadata.get("tipo"),
                )
            )

        if not fragmentos:
            logger.info("Sin fragmentos relevantes: '%s...'", query[:50])
        else:
            logger.info(
                "Recuperados %d fragmentos (scores: %s)",
                len(fragmentos),
                [round(f.similitud, 2) for f in fragmentos],
            )
        return fragmentos

    def contar(self) -> int:
        try:
            return self._store._collection.count()
        except Exception as e:
            logger.warning("No se pudo contar colección: %s", e)
            return 0

    @property
    def raw(self) -> Chroma:
        return self._store
