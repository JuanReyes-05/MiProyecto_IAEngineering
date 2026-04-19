"""Composición de la aplicación FastAPI — wire-up de services."""
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.api.v1 import admin, consultas, sistema
from app.core.config import Settings, get_settings
from app.core.logging import setup_logging
from app.infrastructure.embeddings_client import build_embeddings
from app.infrastructure.llm_client import OpenAILLMClient
from app.repositories.chroma_repository import ChromaRepository
from app.services.generation_service import GenerationServiceImpl
from app.services.rag_service import RAGServiceImpl
from app.services.retrieval_service import RetrievalServiceImpl
from app.services.routing_service import RoutingServiceImpl
from app.services.scoring_service import DerivationServiceImpl, ScoringServiceImpl

setup_logging()
logger = logging.getLogger(__name__)


def _build_rag_service(settings: Settings) -> tuple[RAGServiceImpl, ChromaRepository]:
    embeddings = build_embeddings(settings)
    repository = ChromaRepository(settings, embeddings)

    count = repository.contar()
    if count == 0:
        logger.warning(
            "La base vectorial está vacía. Ejecuta 'python scripts/ingest.py' primero."
        )
    else:
        logger.info("Base vectorial lista: %d fragmentos indexados", count)

    llm = OpenAILLMClient(settings)

    retrieval = RetrievalServiceImpl(repository, settings)
    generation = GenerationServiceImpl(llm)
    scoring = ScoringServiceImpl(llm)
    derivation = DerivationServiceImpl(llm)

    rag = RAGServiceImpl(
        settings=settings,
        retrieval=retrieval,
        generation=generation,
        scoring=scoring,
        derivation=derivation,
    )

    # Adjuntar método de estadísticas al RAG (antes en RAGChain.estadisticas)
    def estadisticas() -> dict:
        try:
            return {
                "estado": "activo",
                "fragmentos": repository.contar(),
                "coleccion": settings.collection_name,
                "vectorstore": settings.chroma_dir,
                "modelo_llm": settings.llm_model,
                "modelo_embed": settings.embedding_model,
                "top_k": settings.top_k,
                "threshold": settings.confidence_threshold,
            }
        except Exception as e:
            return {"estado": "error", "detalle": str(e)}

    rag.estadisticas = estadisticas  # type: ignore[attr-defined]
    return rag, repository


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    try:
        rag_service, _ = _build_rag_service(settings)
        app.state.rag_service = rag_service
        logger.info("RAGService inicializado correctamente")
    except Exception as e:
        logger.error("Error inicializando RAGService: %s", e)
        app.state.rag_service = None

    app.state.settings = settings
    app.state.routing_service = RoutingServiceImpl(settings)

    def rebuild_rag_service() -> None:
        new_rag, _ = _build_rag_service(settings)
        app.state.rag_service = new_rag

    app.state.rebuild_rag_service = rebuild_rag_service

    yield


app = FastAPI(
    title="Soporte AI — API de Soporte al Cliente",
    description="API REST para el sistema RAG de soporte al cliente",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(sistema.router)
app.include_router(consultas.router)
app.include_router(admin.router)


def main():
    settings = get_settings()
    logger.info("🚀 Iniciando Agente de helpdesk...")
    logger.info("Servidor: http://%s:%d", settings.host, settings.port)
    logger.info("Documentación: http://localhost:%d/docs", settings.port)

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
