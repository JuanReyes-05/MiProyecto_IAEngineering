"""Contratos de la capa services."""
from typing import Optional, Protocol

from app.domain.consulta import RespuestaInterna
from app.domain.fragmento import Fragmento
from app.schemas.enums import AccionRouter


class RetrievalService(Protocol):
    def recuperar(self, pregunta: str) -> list[Fragmento]: ...


class GenerationService(Protocol):
    def generar(self, pregunta: str, fragmentos: list[Fragmento]) -> str: ...


class ScoringService(Protocol):
    def calcular(self, pregunta: str, respuesta: str) -> float: ...


class DerivationService(Protocol):
    def requiere_derivacion(self, pregunta: str) -> bool: ...


class RoutingService(Protocol):
    def definir_accion(
        self, score: float, tiene_info: bool, requiere_derivacion: bool, pregunta: str
    ) -> AccionRouter: ...


class RAGService(Protocol):
    def consultar(
        self, pregunta: str, usuario_id: Optional[str] = None
    ) -> RespuestaInterna: ...

    def estadisticas(self) -> dict: ...
