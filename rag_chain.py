"""
rag_chain.py — Cadena RAG: el cerebro del sistema

Qué hace este archivo:
1. Recibe la pregunta del usuario
2. La convierte en vector y busca los fragmentos más similares en ChromaDB
3. Arma un prompt con la pregunta + el contexto recuperado
4. Se lo envía al LLM (GPT-4o-mini)
5. Devuelve la respuesta con metadata (fuentes, score de confianza, etc.)

Analogía: es la recepcionista inteligente que busca en el archivador,
lee las tarjetas relevantes y formula una respuesta coherente.
"""

from typing import Optional
from dataclasses import dataclass, field

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
import os
import logging

load_dotenv()
# ─── Dataclasses para respuestas tipadas ─────────────────────────────────────

@dataclass
class Fuente:
    """Representa un fragmento de documento recuperado como fuente."""
    archivo:   str
    fragmento: str          # Primeros 200 caracteres del texto
    pagina:    Optional[int] = None
    score:     Optional[float] = None


@dataclass
class RespuestaRAG:
    """Respuesta completa del sistema RAG con toda la metadata."""
    respuesta:          str
    fuentes:            list[Fuente] = field(default_factory=list)
    score_confianza:    float = 0.0
    tiene_info:         bool = True
    pregunta:           str = ""
    modelo:             str = ""
    requiere_derivacion: bool = False
# ─── Configuración ───────────────────────────────────────────────────────────

CHROMA_DIR      = os.getenv("CHROMA_DIR", "./chroma_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "soporte_docs")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
LLM_MODEL       = os.getenv("LLM_MODEL", "gpt-4o-mini")
TOP_K           = int(os.getenv("TOP_K", "4"))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.65"))
# ─── Prompt del sistema ──────────────────────────────────────────────────────
#
# Este prompt es crítico. Define el comportamiento del asistente:
# - Solo usa el contexto proporcionado (evita alucinaciones)
# - Admite cuando no tiene información (activa el router después)
# - Mantiene tono profesional y empático
# - Cita la fuente cuando es relevante
#
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

def get_llm():
    return ChatOpenAI(
        model=LLM_MODEL,
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY", "not-needed"),
        base_url=os.getenv("OPENAI_BASE_URL") or None
    )

class RAGChain:
    """
    Encapsula toda la lógica de la cadena RAG.
    Se instancia una vez al arrancar la aplicación y se reutiliza.
    """
    
    def __init__(self):
        self._vectorstore: Optional[Chroma] = None
        self._llm: Optional[ChatOpenAI] = None
        self._llm_scorer: Optional[ChatOpenAI] = None
        self._embeddings = None
        self._inicializado = False
    
    def inicializar(self) -> bool:
        """
        Carga la base vectorial y los modelos en memoria.
        Se llama al arrancar la API, no en cada consulta.
        
        Returns:
            True si la inicialización fue exitosa.
        """
        try:    
            print(f"Cargando embeddings: {EMBEDDING_MODEL}")
            self._embeddings = HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            
            print(f"Conectando a ChromaDB: {CHROMA_DIR}/{COLLECTION_NAME}")
            self._vectorstore = Chroma(
                collection_name=COLLECTION_NAME,
                embedding_function=self._embeddings,
                persist_directory=CHROMA_DIR,
            )
            
            # Verificar que hay documentos indexados
            count = self._vectorstore._collection.count()
            if count == 0:
                print("La base vectorial está vacía. Ejecuta: python ingest.py")
            else:
                print(f"Base vectorial lista: {count} fragmentos indexados")
            
            print(f"Cargando LLM: {LLM_MODEL}")
            self._llm = get_llm()
            
            # Modelo para scoring (temperatura 0 = determinista)
            self._llm_scorer =get_llm()
            
            self._inicializado = True
            print("RAGChain inicializado correctamente")
            return True
            
        except Exception as e:
            print(f"Error inicializando RAGChain: {e}")
            return False
        
    def _recuperar_fragmentos(self, pregunta: str) -> list[Document]:
        """
        Busca los TOP_K fragmentos más relevantes para la pregunta.
        Usa similarity_search_with_score para obtener
        también el score de similitud de cada fragmento.
        """
        resultados_raw = self._vectorstore.similarity_search_with_score(
            query=pregunta,
            k=TOP_K,
        )
        
        # Convertir distancia L2 a score de similitud normalizado (0-1)
        # Menor distancia = mayor similitud
        resultados = [(doc, 1 / (1 + dist)) for doc, dist in resultados_raw]
        
        # Filtrar fragmentos con score muy bajo
        # Umbral bajo porque el LLM evalúa relevancia después
        resultados_filtrados = [(doc, score) for doc, score in resultados if score > 0.10]
        
        if not resultados_filtrados:
            print(f"No se encontraron fragmentos relevantes para: '{pregunta[:50]}...'")
            return []
        
        print(f"Recuperados {len(resultados_filtrados)} fragmentos (scores: {[round(s, 2) for _, s in resultados_filtrados]})")
        return resultados_filtrados
    
    def _calcular_score_confianza(self, pregunta: str, respuesta: str) -> float:
        """
        Pide al LLM que evalúe qué tan bien responde su propia respuesta.
        Esto es self-evaluation: el modelo califica su propia calidad.
        
        Si el score es bajo, el router en main.py decidirá escalar a humano
        o crear un ticket en lugar de enviar la respuesta al cliente.
        """
        # Atajo rápido: si la respuesta contiene la frase de "no tengo info",
        # el score es directamente 0.0 sin llamar al LLM (ahorra tokens)
        frases_sin_info = [
            "no tengo información suficiente",
            "no tengo información sobre",
            "no encontré información",
            "no puedo responder",
        ]
        if any(frase in respuesta.lower() for frase in frases_sin_info):
            return 0.0
        
        try:
            prompt = PROMPT_SCORE.format(pregunta=pregunta, respuesta=respuesta)
            resultado = self._llm_scorer.invoke(prompt)
            score = float(resultado.content.strip())
            return max(0.0, min(1.0, score))   # Clamp entre 0 y 1
        except (ValueError, Exception) as e:
            print(f"Error calculando score: {e}. Usando score neutro 0.5")
            return 0.5

    def _determinar_derivacion(self, pregunta: str) -> bool:
        """
        Pide al LLM que clasifique si la consulta requiere abrir un ticket
        de seguimiento (True) o puede resolverse con una respuesta directa (False).
        La decisión se basa en la intención del mensaje, no en palabras clave.
        """
        try:
            prompt = PROMPT_DERIVACION.format(pregunta=pregunta)
            resultado = self._llm_scorer.invoke(prompt)
            return resultado.content.strip().lower().startswith("si")
        except Exception as e:
            print(f"Error determinando derivación: {e}. Por defecto: False")
            return False

    def _formatear_contexto(self, fragmentos: list[tuple[Document, float]]) -> str:
        """
        Convierte la lista de fragmentos recuperados en un string
        formateado que se inyecta en el prompt.
        
        Incluye el nombre del archivo fuente para que el LLM pueda
        citar de dónde viene la información.
        """
        if not fragmentos:
            return "No se encontró contexto relevante en la base de conocimiento."
        
        partes = []
        for i, (doc, score) in enumerate(fragmentos, 1):
            archivo = doc.metadata.get("archivo", "Documento desconocido")
            pagina  = doc.metadata.get("page", "")
            ref     = f"{archivo}, p.{pagina}" if pagina else archivo
            
            partes.append(
                f"[Fragmento {i} — Fuente: {ref}]\n{doc.page_content.strip()}"
            )
        
        return "\n\n---\n\n".join(partes)
    
    def consultar(self, pregunta: str, usuario_id: Optional[str] = None) -> RespuestaRAG:
        """
        Método principal: procesa una pregunta y devuelve una respuesta completa.
        
        Flujo:
        1. Recuperar fragmentos relevantes
        2. Formatear contexto
        3. Llamar al LLM con el prompt ensamblado
        4. Calcular score de confianza
        5. Construir respuesta estructurada
        
        Args:
            pregunta:   La pregunta del usuario en lenguaje natural.
            usuario_id: ID opcional del usuario (para logs y trazabilidad).
        
        Returns:
            RespuestaRAG con la respuesta, fuentes y metadata.
        """
        if not self._inicializado:
            raise RuntimeError("RAGChain no está inicializado. Llama a .inicializar() primero.")
        
        print(f"Consulta de usuario '{usuario_id or 'anon'}': {pregunta[:60]}...")
        
        # ── Paso 1: Recuperar fragmentos ────────────────────────────────────
        fragmentos_con_score = self._recuperar_fragmentos(pregunta)
        
        # ── Paso 2: Formatear contexto ──────────────────────────────────────
        contexto = self._formatear_contexto(fragmentos_con_score)
        
        # ── Paso 3: Llamar al LLM ───────────────────────────────────────────
        prompt = ChatPromptTemplate.from_template(PROMPT_SISTEMA)
        chain  = prompt | self._llm | StrOutputParser()
        
        respuesta_texto = chain.invoke({
            "contexto": contexto,
            "pregunta": pregunta,
        })
        
        # ── Paso 4: Calcular score de confianza ─────────────────────────────
        score = self._calcular_score_confianza(pregunta, respuesta_texto)
        tiene_info = score >= CONFIDENCE_THRESHOLD

        # ── Paso 4b: Determinar si requiere ticket de seguimiento ────────────
        requiere_derivacion = self._determinar_derivacion(pregunta) if tiene_info else False
        
        # ── Paso 5: Construir objeto de respuesta ───────────────────────────
        fuentes = [
            Fuente(
                archivo=doc.metadata.get("archivo", "Desconocido"),
                fragmento=doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
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
            modelo=LLM_MODEL,
            requiere_derivacion=requiere_derivacion,
        )
        
        print(f"Respuesta generada — Score: {score:.2f} | Tiene info: {tiene_info} | Deriva: {requiere_derivacion} | Fuentes: {len(fuentes)}")
        return respuesta
    
    def estadisticas(self) -> dict:
        """Devuelve estadísticas de la base vectorial para el endpoint /health."""
        if not self._inicializado or not self._vectorstore:
            return {"estado": "no inicializado"}
        
        try:
            count = self._vectorstore._collection.count()
            return {
                "estado":       "activo",
                "fragmentos":   count,
                "coleccion":    COLLECTION_NAME,
                "vectorstore":  CHROMA_DIR,
                "modelo_llm":   LLM_MODEL,
                "modelo_embed": EMBEDDING_MODEL,
                "top_k":        TOP_K,
                "threshold":    CONFIDENCE_THRESHOLD,
            }
        except Exception as e:
            return {"estado": "error", "detalle": str(e)}


# ─── Instancia global (singleton) ───────────────────────────────────────────
#
# Se crea una sola vez al importar el módulo y se comparte entre requests.
# Esto evita recargar los modelos en cada consulta (sería muy lento).
#
rag = RAGChain()    

