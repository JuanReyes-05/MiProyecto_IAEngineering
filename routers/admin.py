"""Endpoint /ingest — re-ingesta de documentos (tarea administrativa)."""
import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Request

from dependencies import SettingsDep
from ingest import ejecutar_ingesta
from rag_chain import RAGChain
from schemas import IngestRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["administración"])


@router.post("/ingest")
async def reingestar(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    settings: SettingsDep,
):
    """Re-ingesta en background. Actualiza app.state.rag al terminar."""
    app = http_request.app

    def _ingestar():
        resultado = ejecutar_ingesta(limpiar=request.limpiar, settings=settings)
        if resultado.get("exito"):
            nuevo_rag = RAGChain(settings)
            if nuevo_rag.inicializar():
                app.state.rag = nuevo_rag
                logger.info(
                    "Re-ingesta completada: %d fragmentos",
                    resultado.get("fragmentos", 0),
                )
            else:
                logger.warning(
                    "Ingesta OK pero falló re-inicialización del RAGChain"
                )

    background_tasks.add_task(_ingestar)

    return {
        "mensaje": "Ingesta iniciada en background",
        "limpiar": request.limpiar,
        "timestamp": datetime.now().isoformat(),
        "nota": "Consulta GET /health en 30 segundos para ver el resultado",
    }
