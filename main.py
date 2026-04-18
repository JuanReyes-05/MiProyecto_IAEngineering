"""
main.py — Composición de la aplicación FastAPI.

Patrón "bigger applications" (https://fastapi.tiangolo.com/tutorial/bigger-applications/):
- `main.py` solo crea la instancia, configura lifespan y registra routers.
- La lógica de endpoints vive en `routers/`.
- `Settings` en `config.py`, dependencias en `dependencies.py`, schemas en `schemas.py`.

El ciclo startup/shutdown usa `lifespan` async context manager
(https://fastapi.tiangolo.com/advanced/events/) en lugar del deprecado `on_event`.
"""
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from config import get_settings
from rag_chain import RAGChain
from routers import admin, consultas, sistema

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    rag = RAGChain(settings)
    if not rag.inicializar():
        logger.warning(
            "RAGChain no se pudo inicializar. Ejecuta 'python ingest.py' primero."
        )
    app.state.rag = rag
    app.state.settings = settings

    yield

    # Shutdown: aquí iría cierre de conexiones si las hubiera.


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
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
