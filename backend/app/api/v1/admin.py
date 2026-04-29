"""Endpoint /ingest — re-ingesta de documentos (tarea administrativa)."""
import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Request

from app.api.dependencies import SettingsDep, ejecutar_ingesta
from app.schemas.admin import IngestRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["administración"])


@router.post("/ingest")
async def reingestar(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    settings: SettingsDep,
):
    """Re-ingesta en background. Recompone el RAGService al finalizar."""
    app = http_request.app
    rebuild_rag_service = getattr(app.state, "rebuild_rag_service", None)

    def _ingestar():
        resultado = ejecutar_ingesta(limpiar=request.limpiar, settings=settings)
        if resultado.get("exito") and rebuild_rag_service is not None:
            try:
                rebuild_rag_service()
                logger.info(
                    "Re-ingesta completada: %d fragmentos",
                    resultado.get("fragmentos", 0),
                )
            except Exception as e:
                logger.warning(
                    "Ingesta OK pero falló re-inicialización del RAGService: %s", e
                )

    background_tasks.add_task(_ingestar)

    return {
        "mensaje": "Ingesta iniciada en background",
        "limpiar": request.limpiar,
        "timestamp": datetime.now().isoformat(),
        "nota": "Consulta GET /health en 30 segundos para ver el resultado",
    }
