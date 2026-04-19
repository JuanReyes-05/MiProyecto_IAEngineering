"""
rag_chain.py — Cadena RAG: el cerebro del sistema.

Recibe la pregunta, recupera fragmentos relevantes de ChromaDB, arma el prompt
con el contexto y llama al LLM. Devuelve una respuesta estructurada con
fuentes, score de confianza y señal de derivación.
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI

from config import Settings, get_settings

logger = logging.getLogger(__name__)


# ─── Dataclasses de dominio ──────────────────────────────────────────────────

@dataclass
class Fuente:
    archivo: str
    fragmento: str
    pagina: Optional[int] = None
    score: Optional[float] = None


@dataclass
class RespuestaRAG:
    respuesta: str
    fuentes: list[Fuente] = field(default_factory=list)
    score_confianza: float = 0.0
    tiene_info: bool = True
    pregunta: str = ""
    modelo: str = ""
    requiere_derivacion: bool = False


# ─── Prompts ─────────────────────────────────────────────────────────────────

PROMPT_SISTEMA = """Eres un asistente de soporte al cliente profesional y empático.
Tu única fuente de información es el contexto que se te proporciona a continuación.

REGLAS IMPORTANTES:
1. Responde ÚNICAMENTE basándote en el contexto proporcionado.
2. Si el contexto no contiene información suficiente para responder, di exactamente:
   "Lo siento, no tengo información suficiente sobre ese tema en mi base de conocimiento."
3. No inventes información ni uses conocimiento externo.
4. Sé conciso pero completo. Máximo 3-4 párrafos.
5. Si hay pasos a seguir, usa una lista numerada.
6. Mantén un tono amigable y profesional.

CONTEXTO DE LA BASE DE CONOCIMIENTO:
{contexto}

PREGUNTA DEL USUARIO:
{pregunta}

RESPUESTA:"""

PROMPT_SCORE = """Evalúa qué tan bien responde el siguiente texto a la pregunta dada.
Devuelve SOLO un número decimal entre 0.0 y 1.0, sin texto adicional.

0.0 = No hay información relevante / dice que no sabe
0.5 = Información parcial o poco específica
1.0 = Respuesta completa y directa

Pregunta: {pregunta}
Respuesta: {respuesta}

Score (solo el número):"""

PROMPT_DERIVACION = """Analiza el siguiente mensaje de un usuario y decide si su caso requiere derivar el ticket a 2do nivel o puede resolverse con una respuesta directa.

Devuelve SOLO "si" o "no", sin texto adicional.

"si" = El caso requiere seguimiento: reclamo, falla técnica persistente, reembolso, queja formal, situación que necesita acción por parte de un agente humano.
"no" = El caso puede resolverse con información: consulta, pregunta, duda, solicitud de instrucciones.

Mensaje del usuario: {pregunta}

¿Requiere ticket de seguimiento? (si/no):"""


# ─── Cadena RAG ──────────────────────────────────────────────────────────────

class RAGChain:
    """
    Encapsula la lógica de retrieval + generación.

    Recibe `Settings` por constructor (DI explícita → fácil de testear).
    Si no se pasa, hace fallback a `get_settings()` para preservar compat.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings: Settings = settings or get_settings()
        self._vectorstore: Optional[Chroma] = None
        self._llm: Optional[ChatOpenAI] = None
        self._llm_scorer: Optional[ChatOpenAI] = None
        self._embeddings = None
        self._inicializado = False

    def _build_llm(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=self.settings.llm_model,
            temperature=0,
            api_key=self.settings.openai_api_key or "not-needed",
            base_url=self.settings.openai_base_url or None,
        )

    def inicializar(self) -> bool:
        """Carga embeddings, vectorstore y LLM en memoria."""
        try:
            logger.info("Cargando embeddings: %s", self.settings.embedding_model)
            self._embeddings = HuggingFaceEmbeddings(
                model_name=self.settings.embedding_model,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )

            logger.info(
                "Conectando a ChromaDB: %s/%s",
                self.settings.chroma_dir,
                self.settings.collection_name,
            )
            self._vectorstore = Chroma(
                collection_name=self.settings.collection_name,
                embedding_function=self._embeddings,
                persist_directory=self.settings.chroma_dir,
            )

            count = self._vectorstore._collection.count()
            if count == 0:
                logger.warning(
                    "La base vectorial está vacía. Ejecuta: python ingest.py"
                )
            else:
                logger.info("Base vectorial lista: %d fragmentos indexados", count)

            logger.info("Cargando LLM: %s", self.settings.llm_model)
            self._llm = self._build_llm()
            self._llm_scorer = self._build_llm()

            self._inicializado = True
            logger.info("RAGChain inicializado correctamente")
            return True

        except Exception as e:
            logger.error("Error inicializando RAGChain: %s", e)
            return False

    def _recuperar_fragmentos(
        self, pregunta: str
    ) -> list[tuple[Document, float]]:
        resultados_raw = self._vectorstore.similarity_search_with_score(
            query=pregunta,
            k=self.settings.top_k,
        )

        # Nota: la conversión dist → score es aproximada.
        # Se mejora en la deuda técnica §1.3 (cosine vs L2).
        resultados = [(doc, 1 / (1 + dist)) for doc, dist in resultados_raw]
        resultados_filtrados = [
            (doc, score) for doc, score in resultados if score > 0.10
        ]

        if not resultados_filtrados:
            logger.info("Sin fragmentos relevantes: '%s...'", pregunta[:50])
            return []

        logger.info(
            "Recuperados %d fragmentos (scores: %s)",
            len(resultados_filtrados),
            [round(s, 2) for _, s in resultados_filtrados],
        )
        return resultados_filtrados

    def _calcular_score_confianza(self, pregunta: str, respuesta: str) -> float:
        frases_sin_info = [
            "no tengo información suficiente",
            "no tengo información sobre",
            "no encontré información",
            "no puedo responder",
        ]
        if any(f in respuesta.lower() for f in frases_sin_info):
            return 0.0

        try:
            prompt = PROMPT_SCORE.format(pregunta=pregunta, respuesta=respuesta)
            resultado = self._llm_scorer.invoke(prompt)
            score = float(resultado.content.strip())
            return max(0.0, min(1.0, score))
        except (ValueError, Exception) as e:
            logger.warning("Error calculando score: %s. Usando 0.5", e)
            return 0.5

    def _determinar_derivacion(self, pregunta: str) -> bool:
        try:
            prompt = PROMPT_DERIVACION.format(pregunta=pregunta)
            resultado = self._llm_scorer.invoke(prompt)
            return resultado.content.strip().lower().startswith("si")
        except Exception as e:
            logger.warning("Error determinando derivación: %s. Default False", e)
            return False

    def _formatear_contexto(
        self, fragmentos: list[tuple[Document, float]]
    ) -> str:
        if not fragmentos:
            return "No se encontró contexto relevante en la base de conocimiento."

        partes = []
        for i, (doc, _score) in enumerate(fragmentos, 1):
            archivo = doc.metadata.get("archivo", "Documento desconocido")
            pagina = doc.metadata.get("page", "")
            ref = f"{archivo}, p.{pagina}" if pagina else archivo
            partes.append(
                f"[Fragmento {i} — Fuente: {ref}]\n{doc.page_content.strip()}"
            )

        return "\n\n---\n\n".join(partes)

    def consultar(
        self, pregunta: str, usuario_id: Optional[str] = None
    ) -> RespuestaRAG:
        if not self._inicializado:
            raise RuntimeError(
                "RAGChain no está inicializado. Llama a .inicializar() primero."
            )

        logger.info(
            "Consulta de '%s': %s...", usuario_id or "anon", pregunta[:60]
        )

        fragmentos_con_score = self._recuperar_fragmentos(pregunta)
        contexto = self._formatear_contexto(fragmentos_con_score)

        prompt = ChatPromptTemplate.from_template(PROMPT_SISTEMA)
        chain = prompt | self._llm | StrOutputParser()
        respuesta_texto = chain.invoke(
            {"contexto": contexto, "pregunta": pregunta}
        )

        score = self._calcular_score_confianza(pregunta, respuesta_texto)
        tiene_info = score >= self.settings.confidence_threshold
        requiere_derivacion = (
            self._determinar_derivacion(pregunta) if tiene_info else False
        )

        fuentes = [
            Fuente(
                archivo=doc.metadata.get("archivo", "Desconocido"),
                fragmento=(
                    doc.page_content[:200] + "..."
                    if len(doc.page_content) > 200
                    else doc.page_content
                ),
                pagina=doc.metadata.get("page"),
                score=round(s, 3),
            )
            for doc, s in fragmentos_con_score
        ]

        respuesta = RespuestaRAG(
            respuesta=respuesta_texto,
            fuentes=fuentes,
            score_confianza=round(score, 3),
            tiene_info=tiene_info,
            pregunta=pregunta,
            modelo=self.settings.llm_model,
            requiere_derivacion=requiere_derivacion,
        )

        logger.info(
            "Respuesta — Score: %.2f | Info: %s | Deriva: %s | Fuentes: %d",
            score,
            tiene_info,
            requiere_derivacion,
            len(fuentes),
        )
        return respuesta

    def estadisticas(self) -> dict:
        if not self._inicializado or not self._vectorstore:
            return {"estado": "no inicializado"}

        try:
            count = self._vectorstore._collection.count()
            return {
                "estado": "activo",
                "fragmentos": count,
                "coleccion": self.settings.collection_name,
                "vectorstore": self.settings.chroma_dir,
                "modelo_llm": self.settings.llm_model,
                "modelo_embed": self.settings.embedding_model,
                "top_k": self.settings.top_k,
                "threshold": self.settings.confidence_threshold,
            }
        except Exception as e:
            return {"estado": "error", "detalle": str(e)}
