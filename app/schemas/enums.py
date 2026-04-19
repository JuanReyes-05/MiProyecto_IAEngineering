"""Enums compartidos entre DTOs."""
from enum import Enum


class AccionRouter(str, Enum):
    """Acciones posibles del agente. Al ser str+Enum, serializa a su value."""

    RESPONDER = "responder"
    DERIVAR = "derivar_ticket"
    ESCALAR = "escalar_humano"
