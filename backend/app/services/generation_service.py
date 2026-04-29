"""Service de generación de respuesta LLM a partir del contexto recuperado."""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.prompts import PROMPT_SISTEMA
from app.domain.fragmento import Fragmento
from app.infrastructure.llm_client import OpenAILLMClient


class GenerationServiceImpl:
    """Genera la respuesta final combinando pregunta + contexto."""

    def __init__(self, llm: OpenAILLMClient):
        self._llm = llm
        self._chain = (
            ChatPromptTemplate.from_template(PROMPT_SISTEMA)
            | llm.raw
            | StrOutputParser()
        )

    def generar(self, pregunta: str, fragmentos: list[Fragmento]) -> str:
        contexto = self._formatear_contexto(fragmentos)
        return self._chain.invoke({"contexto": contexto, "pregunta": pregunta})

    @staticmethod
    def _formatear_contexto(fragmentos: list[Fragmento]) -> str:
        if not fragmentos:
            return "No se encontró contexto relevante en la base de conocimiento."

        partes = []
        for i, frag in enumerate(fragmentos, 1):
            ref = (
                f"{frag.archivo}, p.{frag.pagina}"
                if frag.pagina
                else frag.archivo
            )
            partes.append(
                f"[Fragmento {i} — Fuente: {ref}]\n{frag.contenido.strip()}"
            )
        return "\n\n---\n\n".join(partes)
