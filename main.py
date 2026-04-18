from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from rag_chain import rag, RespuestaRAG
from ingest import ejecutar_ingesta
from datetime import datetime
import uvicorn
from typing import Optional
import os
import uuid


load_dotenv()

app=FastAPI(
    title="Soporte AI — API de Soporte al Cliente",
    description="API REST para el sistema RAG de soporte al cliente",
    version="1.0.0",
)

MINIMUM_SCORE = float(os.getenv("MINIMUM_SCORE", "0.65"))

@app.on_event("startup")
def startup():
    """Inicializa la cadena RAG al arrancar el servidor."""
    if not rag.inicializar():
        print("ADVERTENCIA: RAGChain no se pudo inicializar. Ejecuta 'python ingest.py' primero.")

#==Validación de PYDANTIC=====

class PreguntaRequest(BaseModel):
   """Cuerpo del request para el endpoint /ask """
   pregunta: str = Field(..., min_length=5, description="La pregunta del usuario.")
   usuario_id: Optional[str] = Field(..., min_length=3, description="Nombre o ID del usuario que hace la pregunta.")

   model_config = {
      "json_schema_extra": {
            "example": {
                "pregunta": "¿Cómo puedo restablecer mi contraseña?",
                "usuario_id": "juan.reyesl"
            }
        }
   }

class FuenteResponse(BaseModel):
   """"Fragmento de docuemento para la Pregunta al LLM"""
   archivo: str
   fragmento: str
   pagina: Optional[int] = None
   score: Optional[float] = None

class AccionRouter(str):
   """"las Tres acciones del agente"""
   RESPONDER = "responder"
   DERIVAR   = "derivar_ticket"
   ESCALAR = "escalar_humano"

class PreguntaResponse(BaseModel):
   """Respuesta del endpoint /ask"""
   consulta_id: str
   respuesta: str
   accion: str = Field(..., description="La acción que el agente recomienda: responder, derivar-ticket o escalar_humano")
   score_confianza: float = Field(..., description="Nivel de confianza del agente en su respuesta (0.0 a 1.0)")
   tiene_info: bool
   fuentes: list[FuenteResponse] = []
   modelo: str
   timestamp: str
  
   model_config = {
     "json_schema_extra": {
        "example": {
           "consulta_id":"abc123",
           "respuesta": "Lamento los incovenientes, tu ticket a sido derivado al área corresondiente",
           "accion": "derivar_ticket",
           "score_confianza": 0.85,
           "tiene_info": True,
           "fuentes": [{
              "archivo":"politicas.pdf",
              "fragmento":"Según nuestras políticas de seguridad, recomendamos cambiar tu contraseña cada 2 meses.",
              "score": 0.92
           }],
           "modelo": "gpt-4o-mini",
           "timestamp": "2024-06-01T12:34:56Z"    
        }
     }
  }

class IngestRequest(BaseModel):
   """Cuerpo del request para el endpoint /ingest"""
   limpiar: bool = Field(False, description="Si es true, limpia la base vectorial antes de reingestar.")   

class HealthResponse(BaseModel):
   """Respuesta del endpoint /health"""
   estado: str
   version: str
   estadisticas: dict
   timestamp: str

# === Router inteligente =================

# Palabras que siempre derivan a un agente humano, sin importar el score
PALABRAS_ESCALACION = {
    "fraude", "estafa", "robo", "demanda", "abogado", "legal",
    "denuncia", "urgente", "emergencia", "cancelar todo",
    "muy molesto", "inaceptable", "escalar", "supervisor", "gerente",
}

def definir_accion(resultado: RespuestaRAG, pregunta: str) -> str:
    """
   El router: decide qué hacer con la respuesta generada.
    
    Lógica:
    1. Si hay palabras de escalación en la pregunta → escalar_humano
    2. Si el score es muy bajo (< 0.3) → escalar_humano
    3. Si tiene info y score > MINIMUM_SCORE:
       3a. Si el LLM marcó requiere_derivacion=True → derivar_ticket
       3b. Si el LLM marcó requiere_derivacion=False → responder
    4. Sin info suficiente → escalar_humano
    
    Returns:
        "responder" | "derivar_ticket" | "escalar_humano"
    """
    
    pregunta_lower = pregunta.lower()
    
    # Regla 1: Escalación forzada por palabras clave de urgencia/fraude
    if any(palabra in pregunta_lower for palabra in PALABRAS_ESCALACION):
        print(f"Router: ESCALAR — palabra de escalación detectada")
        return "escalar_humano"
    
    #Regla 2: Score bajo que indica falta de contexto
    if resultado.score_confianza < 0.3:
        print(f"Router: ESCALAR — score de confianza muy bajo ({resultado.score_confianza:.2f})")
        return "escalar_humano"
    
    #Regla 3: Tiene info y score OK → el LLM decidió si requiere ticket o no
    if resultado.tiene_info and resultado.score_confianza > MINIMUM_SCORE:
        if resultado.requiere_derivacion:
            print(f"Router: DERIVAR — el LLM determinó que requiere 2do nivel ({resultado.score_confianza:.2f})")
            return "derivar_ticket"
        #Regla 4: El LLM determinó que puede resolverse con respuesta directa
        print(f"Router: RESPONDER — el LLM determinó que puede resolverse automáticamente ({resultado.score_confianza:.2f})")
        return "responder"

    # Regla 5: Sin info suficiente → escalar
    print(f"Router: ESCALAR — sin información suficiente para resolver ({resultado.score_confianza:.2f})")
    return "escalar_humano"

def registrar_interaccion(consulta_id: str, pregunta: str, respuesta: PreguntaResponse):
   """registra cada interacción para análisis posterior.
   En prod se cambia a una DB o PostgreSQL de logging, 
   Por ahora solo lo escribe en un archivo de texto simple.
   """
   try:
        linea = (
            f"{respuesta.timestamp} | {consulta_id} | "
            f"accion={respuesta.accion} | score={respuesta.score_confianza:.2f} | "
            f"pregunta={pregunta[:80].replace('|', '-')}\n"
        )
        with open("interacciones.log", "a", encoding="utf-8") as f:
            f.write(linea)
   except Exception as e:
        print(f"No se pudo registrar la interacción: {e}")

#=======Endpoint de salud y estadísticas======= 
@app.get("/", tags=["info"])
async def raiz():
    """Información básica de la API."""
    return {
        "nombre":    "RAG Soporte al Cliente",
        "version":   "1.0.0",
        "endpoints": {
            "preguntar":   "POST /ask",
            "ingestar":    "POST /ingest",
            "salud":       "GET /health",
            "documentacion": "GET /docs",
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["sistema"])
async def health():
    """
    Estado del sistema y estadísticas de la base vectorial.
    Útil para monitoreo y para verificar que la ingesta funcionó.
    """
    stats = rag.estadisticas()
    estado = "ok" if stats.get("estado") == "activo" else "degradado"
    
    return HealthResponse(
        estado=estado,
        version="1.0.0",
        estadisticas=stats,
        timestamp=datetime.now().isoformat(),
    )

@app.post("/ask", response_model=PreguntaResponse, tags=["consultas"])
async def preguntar(request: PreguntaRequest, background_tasks: BackgroundTasks):  
    """"
    Endpoint principal: recibe pregunta y devuelve la respuesta.
    El campo `accion` en la respuesta indica qué debe hacer tu sistema:
    - **responder**: mostrar la respuesta al usuario directamente
    - **derivar_ticket**: hay info, derivar ticket para que 2do nivel lo resuelva
    - **requiere_derivacion**: el LLM determinó que se necesita un ticket de 2do nivel, aunque haya info suficiente para responder. 
    Esto permite manejar casos donde el LLM detecta que la consulta es compleja o sensible, y prefiere que un humano revise antes de dar una respuesta automática.   
    - **escalar_humano**: urgente o sensible, conectar con agente ahora
    
    El campo `score_confianza` indica qué tan seguro está el sistema (0-1).
    El campo `tiene_info` indica si se encontró información relevante en la base de conocimiento.
    """

    consulta_id = str(uuid.uuid4())
    try:
        # Generar respuesta RAG
        resultado = rag.consultar(
            pregunta=request.pregunta,
            usuario_id=request.usuario_id,
        )
        
        # Decidir acción con el router
        accion = definir_accion(resultado, request.pregunta)
        
        # Construir respuesta
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
        
        # Registrar en background (no bloquea la respuesta)
        background_tasks.add_task(
            registrar_interaccion,
            consulta_id,
            request.pregunta,
            respuesta,
        )
        
        return respuesta
    
    except RuntimeError as e:
        # RAGChain no inicializado (base vectorial vacía o sin .env)
        raise HTTPException(
            status_code=503,
            detail=f"Sistema no disponible: {str(e)}. Verifica que ejecutaste 'python ingest.py' primero.",
        )
    except Exception as e:
        print(f"Error procesando consulta {consulta_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al procesar la consulta. ID: {consulta_id}",
        )
@app.post("/ingest", tags=["administración"])
async def reingestar(request: IngestRequest, background_tasks: BackgroundTasks):
    """
    Re-ingesta los documentos de la carpeta docs/.
    
    Usar cuando:
    - Agregas nuevos documentos
    - Modificas documentos existentes
    - Quieres limpiar y reconstruir la base vectorial
    
    Si `limpiar=true`, elimina todos los vectores existentes antes de reingestar.
    """
    def _ingestar():
        resultado = ejecutar_ingesta(limpiar=request.limpiar)
        if resultado.get("exito"):
            # Re-inicializar la cadena RAG con la nueva base vectorial
            rag.inicializar()
            print(f"Re-ingesta completada: {resultado.get('fragmentos', 0)} fragmentos")
    
    background_tasks.add_task(_ingestar)
    
    return {
        "mensaje":   "Ingesta iniciada en background",
        "limpiar":   request.limpiar,
        "timestamp": datetime.now().isoformat(),
        "nota":      "Consulta GET /health en 30 segundos para ver el resultado",
    }

def main():
    print("🚀 Iniciando Agente de helpdesk...\n")

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    print(f"Iniciando servidor en http://{host}:{port}")
    print(f"Documentación: http://localhost:{port}/docs")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,    # Auto-reload al cambiar código (desactivar en producción)
        log_level="info",
    )
if __name__ == "__main__":
    main()