"""Service que decide la acción final: responder / derivar / escalar."""
import logging

from app.core.config import Settings
from app.schemas.enums import AccionRouter

logger = logging.getLogger(__name__)


PALABRAS_ESCALACION = frozenset(
    {
        "fraude",
        "estafa",
        "robo",
        "demanda",
        "abogado",
        "denuncia",
        "urgente",
        "emergencia",
        "cancelar todo",
        "muy molesto",
        "inaceptable",
        "escalar",
        "supervisor",
        "gerente",
    }
)

SCORE_MINIMO_AUTO_ESCALAR = 0.3


class RoutingServiceImpl:
    """Encapsula la regla de negocio de enrutamiento."""

    def __init__(self, settings: Settings):
        self._settings = settings

    def definir_accion(
        self,
        score: float,
        tiene_info: bool,
        requiere_derivacion: bool,
        pregunta: str,
    ) -> AccionRouter:
        pregunta_lower = pregunta.lower()

        if any(p in pregunta_lower for p in PALABRAS_ESCALACION):
            logger.info("Router: ESCALAR — palabra de escalación detectada")
            return AccionRouter.ESCALAR

        if score < SCORE_MINIMO_AUTO_ESCALAR:
            logger.info("Router: ESCALAR — score muy bajo (%.2f)", score)
            return AccionRouter.ESCALAR

        if tiene_info and score > self._settings.minimum_score:
            if requiere_derivacion:
                logger.info(
                    "Router: DERIVAR — LLM determinó 2do nivel (%.2f)", score
                )
                return AccionRouter.DERIVAR
            logger.info("Router: RESPONDER — auto (%.2f)", score)
            return AccionRouter.RESPONDER

        logger.info("Router: ESCALAR — sin info suficiente (%.2f)", score)
        return AccionRouter.ESCALAR
