"""Endpoint /ask — expone el pipeline RAG."""
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.dependencies import RAGServiceDep, RoutingServiceDep
from app.schemas.consulta import FuenteResponse, PreguntaRequest, PreguntaResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["consultas"])


def registrar_interaccion(
    consulta_id: str, pregunta: str, respuesta: PreguntaResponse
) -> None:
    try:
        linea = (
            f"{respuesta.timestamp} | {consulta_id} | "
            f"accion={respuesta.accion.value} | "
            f"score={respuesta.score_confianza:.2f} | "
            f"pregunta={pregunta[:80].replace('|', '-')}\n"
        )
        with open("interacciones.log", "a", encoding="utf-8") as f:
            f.write(linea)
    except Exception as e:
        logger.warning("No se pudo registrar la interacción: %s", e)


@router.post("/ask", response_model=PreguntaResponse)
async def preguntar(
    request: PreguntaRequest,
    background_tasks: BackgroundTasks,
    rag: RAGServiceDep,
    routing: RoutingServiceDep,
):
    """Procesa una pregunta y devuelve respuesta + acción recomendada."""
    consulta_id = str(uuid.uuid4())
    try:
        resultado = rag.consultar(
            pregunta=request.pregunta,
            usuario_id=request.usuario_id,
        )

        accion = routing.definir_accion(
            score=resultado.score_confianza,
            tiene_info=resultado.tiene_info,
            requiere_derivacion=resultado.requiere_derivacion,
            pregunta=request.pregunta,
        )

        respuesta = PreguntaResponse(
            consulta_id=consulta_id,
            respuesta=resultado.respuesta,
            accion=accion,
            score_confianza=resultado.score_confianza,
            tiene_info=resultado.tiene_info,
            fuentes=[
                FuenteResponse(
                    archivo=f.archivo,
                    fragmento=(
                        f.contenido[:200] + "..."
                        if len(f.contenido) > 200
                        else f.contenido
                    ),
                    pagina=f.pagina,
                    score=round(f.similitud, 3),
                )
                for f in resultado.fragmentos
            ],
            modelo=resultado.modelo,
            timestamp=datetime.now().isoformat(),
        )

        background_tasks.add_task(
            registrar_interaccion, consulta_id, request.pregunta, respuesta
        )

        return respuesta

    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Sistema no disponible: {str(e)}. "
                "Verifica que ejecutaste 'python scripts/ingest.py' primero."
            ),
        )
    except Exception as e:
        logger.error("Error procesando consulta %s: %s", consulta_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al procesar la consulta. ID: {consulta_id}",
        )
