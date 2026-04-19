"""Service de cálculo de confianza y detección de derivación a 2do nivel."""
import logging

from app.core.prompts import FRASES_SIN_INFO, PROMPT_DERIVACION, PROMPT_SCORE
from app.infrastructure.llm_client import OpenAILLMClient

logger = logging.getLogger(__name__)


class ScoringServiceImpl:
    """Calcula un score de 0.0 a 1.0 sobre la respuesta generada."""

    def __init__(self, llm: OpenAILLMClient):
        self._llm = llm

    def calcular(self, pregunta: str, respuesta: str) -> float:
        if any(f in respuesta.lower() for f in FRASES_SIN_INFO):
            return 0.0

        try:
            prompt = PROMPT_SCORE.format(pregunta=pregunta, respuesta=respuesta)
            contenido = self._llm.invoke(prompt).strip()
            score = float(contenido)
            return max(0.0, min(1.0, score))
        except (ValueError, Exception) as e:
            logger.warning("Error calculando score: %s. Usando 0.5", e)
            return 0.5


class DerivationServiceImpl:
    """Decide si una consulta requiere derivación a 2do nivel."""

    def __init__(self, llm: OpenAILLMClient):
        self._llm = llm

    def requiere_derivacion(self, pregunta: str) -> bool:
        try:
            prompt = PROMPT_DERIVACION.format(pregunta=pregunta)
            contenido = self._llm.invoke(prompt).strip().lower()
            return contenido.startswith("si")
        except Exception as e:
            logger.warning("Error determinando derivación: %s. Default False", e)
            return False
