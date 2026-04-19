"""Endpoint /ask + router inteligente que decide la acción final."""
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException

from dependencies import RAGDep, SettingsDep
from rag_chain import RespuestaRAG
from schemas import (
    AccionRouter,
    FuenteResponse,
    PreguntaRequest,
    PreguntaResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["consultas"])


# Palabras que siempre escalan a un humano, sin importar el score.
# TODO §1.3: reemplazar por clasificador LLM para evitar falsos positivos
# por substring (ej. "legal" matchea "términos legales").
PALABRAS_ESCALACION = {
    "fraude", "estafa", "robo", "demanda", "abogado",
    "denuncia", "urgente", "emergencia", "cancelar todo",
    "muy molesto", "inaceptable", "escalar", "supervisor", "gerente",
}


def definir_accion(
    resultado: RespuestaRAG, pregunta: str, minimum_score: float
) -> AccionRouter:
    """Decide qué hacer con la respuesta generada por el RAG."""
    pregunta_lower = pregunta.lower()

    if any(p in pregunta_lower for p in PALABRAS_ESCALACION):
        logger.info("Router: ESCALAR — palabra de escalación detectada")
        return AccionRouter.ESCALAR

    if resultado.score_confianza < 0.3:
        logger.info(
            "Router: ESCALAR — score muy bajo (%.2f)",
            resultado.score_confianza,
        )
        return AccionRouter.ESCALAR

    if resultado.tiene_info and resultado.score_confianza > minimum_score:
        if resultado.requiere_derivacion:
            logger.info(
                "Router: DERIVAR — LLM determinó 2do nivel (%.2f)",
                resultado.score_confianza,
            )
            return AccionRouter.DERIVAR
        logger.info(
            "Router: RESPONDER — auto (%.2f)", resultado.score_confianza
        )
        return AccionRouter.RESPONDER

    logger.info(
        "Router: ESCALAR — sin info suficiente (%.2f)",
        resultado.score_confianza,
    )
    return AccionRouter.ESCALAR


def registrar_interaccion(
    consulta_id: str, pregunta: str, respuesta: PreguntaResponse
) -> None:
    """Append-only a archivo plano. En §1.4 migrar a SQLite/logging handler."""
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
    rag: RAGDep,
    settings: SettingsDep,
):
    """Procesa una pregunta y devuelve respuesta + acción recomendada."""
    consulta_id = str(uuid.uuid4())
    try:
        resultado = rag.consultar(
            pregunta=request.pregunta,
            usuario_id=request.usuario_id,
        )

        accion = definir_accion(
            resultado, request.pregunta, settings.minimum_score
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
                    fragmento=f.fragmento,
                    pagina=f.pagina,
                    score=f.score,
                )
                for f in resultado.fuentes
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
                "Verifica que ejecutaste 'python ingest.py' primero."
            ),
        )
    except Exception as e:
        logger.error("Error procesando consulta %s: %s", consulta_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al procesar la consulta. ID: {consulta_id}",
        )
