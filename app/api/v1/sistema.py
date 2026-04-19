"""Endpoints de sistema: raíz e health check."""
from datetime import datetime

from fastapi import APIRouter, Request

from app.schemas.sistema import HealthResponse

router = APIRouter(tags=["sistema"])


@router.get("/")
async def raiz():
    return {
        "nombre": "RAG Soporte al Cliente",
        "version": "1.0.0",
        "endpoints": {
            "preguntar": "POST /ask",
            "ingestar": "POST /ingest",
            "salud": "GET /health",
            "documentacion": "GET /docs",
        },
    }


@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    rag = getattr(request.app.state, "rag_service", None)
    stats = rag.estadisticas() if rag else {"estado": "no inicializado"}
    estado = "ok" if stats.get("estado") == "activo" else "degradado"
    return HealthResponse(
        estado=estado,
        version="1.0.0",
        estadisticas=stats,
        timestamp=datetime.now().isoformat(),
    )
