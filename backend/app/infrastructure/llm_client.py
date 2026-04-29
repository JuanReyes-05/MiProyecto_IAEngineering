"""Wrapper del cliente LLM para aislar el SDK concreto (LangChain/OpenAI)."""
from typing import Protocol

from langchain_openai import ChatOpenAI

from app.core.config import Settings


class LLMClient(Protocol):
    """Contrato mínimo que los services esperan de un LLM."""

    def invoke(self, prompt: str) -> str: ...


class OpenAILLMClient:
    """Implementación basada en ChatOpenAI de LangChain."""

    def __init__(self, settings: Settings):
        self._llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=0,
            api_key=settings.openai_api_key or "not-needed",
            base_url=settings.openai_base_url or None,
        )
        self.modelo = settings.llm_model

    def invoke(self, prompt: str) -> str:
        resultado = self._llm.invoke(prompt)
        return resultado.content

    @property
    def raw(self) -> ChatOpenAI:
        """Acceso al LLM subyacente para chains de LangChain."""
        return self._llm
