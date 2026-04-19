"""Endpoints de sistema: raíz e health check."""
from datetime import datetime

from fastapi import APIRouter

from dependencies import RAGDep
from schemas import HealthResponse

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
async def health(rag: RAGDep):
    stats = rag.estadisticas()
    estado = "ok" if stats.get("estado") == "activo" else "degradado"
    return HealthResponse(
        estado=estado,
        version="1.0.0",
        estadisticas=stats,
        timestamp=datetime.now().isoformat(),
    )
