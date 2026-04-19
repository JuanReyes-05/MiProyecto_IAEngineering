"""Orquestador RAG: compone retrieval + generación + scoring + derivación."""
import logging
from typing import Optional

from app.core.config import Settings
from app.domain.consulta import RespuestaInterna
from app.services.generation_service import GenerationServiceImpl
from app.services.retrieval_service import RetrievalServiceImpl
from app.services.scoring_service import DerivationServiceImpl, ScoringServiceImpl

logger = logging.getLogger(__name__)


class RAGServiceImpl:
    """Coordina los services de RAG para producir una RespuestaInterna."""

    def __init__(
        self,
        settings: Settings,
        retrieval: RetrievalServiceImpl,
        generation: GenerationServiceImpl,
        scoring: ScoringServiceImpl,
        derivation: DerivationServiceImpl,
    ):
        self._settings = settings
        self._retrieval = retrieval
        self._generation = generation
        self._scoring = scoring
        self._derivation = derivation

    def consultar(
        self, pregunta: str, usuario_id: Optional[str] = None
    ) -> RespuestaInterna:
        logger.info(
            "Consulta de '%s': %s...", usuario_id or "anon", pregunta[:60]
        )

        fragmentos = self._retrieval.recuperar(pregunta)
        respuesta_texto = self._generation.generar(pregunta, fragmentos)

        score = self._scoring.calcular(pregunta, respuesta_texto)
        tiene_info = score >= self._settings.confidence_threshold
        requiere_derivacion = (
            self._derivation.requiere_derivacion(pregunta) if tiene_info else False
        )

        respuesta = RespuestaInterna(
            respuesta=respuesta_texto,
            fragmentos=fragmentos,
            score_confianza=round(score, 3),
            tiene_info=tiene_info,
            pregunta=pregunta,
            modelo=self._settings.llm_model,
            requiere_derivacion=requiere_derivacion,
            usuario_id=usuario_id,
        )

        logger.info(
            "Respuesta — Score: %.2f | Info: %s | Deriva: %s | Fuentes: %d",
            score,
            tiene_info,
            requiere_derivacion,
            len(fragmentos),
        )
        return respuesta
