# Instrucciones para diagrama de arquitectura — Helpdesk AI MVP

Este documento describe la arquitectura del sistema para que puedas generar un diagrama de tecnología preciso del MVP actual.

---

## Contexto general

Sistema de soporte al cliente basado en **RAG (Retrieval-Augmented Generation)** construido con Python. Recibe preguntas de usuarios, recupera fragmentos relevantes de una base de conocimiento, genera una respuesta con un LLM y decide automáticamente si responder, derivar a ticket, o escalar a un humano.

**Versión:** 1.0.0 — MVP funcional  
**Dominio:** Helpdesk / IT Support

---

## Componentes del sistema

### 1. Clientes / Puntos de entrada

| Componente | Tipo | Tecnología | URL |
|---|---|---|---|
| **Chat UI** | Frontend interactivo | Streamlit 1.39 | `http://localhost:8501` |
| **REST API** | Interfaz programática | FastAPI (OpenAPI/Swagger) | `http://localhost:8000/docs` |
| **CLI Ingest** | Herramienta de admin | Python CLI (`scripts/ingest.py`) | Terminal |

---

### 2. API Layer (Backend)

**Tecnología:** FastAPI 0.115 + Uvicorn 0.30 + Python 3.11

**Endpoints:**

| Método | Ruta | Función |
|---|---|---|
| GET | `/` | Metadata de la API |
| GET | `/health` | Estado del sistema |
| POST | `/ask` | Consulta principal (RAG + routing) |
| POST | `/ingest` | Re-ingesta de documentos |

**Responsabilidades:**
- Validación de I/O con Pydantic v2
- Inyección de dependencias (FastAPI Depends)
- Tareas en background (BackgroundTasks)

---

### 3. Pipeline RAG (Servicios)

El corazón del sistema. Cada paso es un servicio independiente con un contrato (`typing.Protocol`):

```
PreguntaRequest
      │
      ▼
┌─────────────────────────────────┐
│     RAGServiceImpl              │
│     (orquestador)               │
│                                 │
│  1. retrieval_service           │ ← Búsqueda semántica
│  2. generation_service          │ ← Generación de respuesta
│  3. scoring_service             │ ← Evaluación de confianza
│  4. derivation_service          │ ← Detección de derivación
└─────────────────────────────────┘
      │
      ▼
 routing_service ──→ RESPONDER | DERIVAR | ESCALAR
      │
      ▼
PreguntaResponse
```

**Servicios involucrados:**

| Servicio | Responsabilidad | LLM involucrado |
|---|---|---|
| `RetrievalService` | Buscar fragmentos relevantes en ChromaDB | No (solo embeddings) |
| `GenerationService` | Generar respuesta con contexto + prompt | Sí (gpt-4o-mini) |
| `ScoringService` | Calcular score de confianza 0.0–1.0 | Sí (gpt-4o-mini) |
| `DerivationService` | Detectar si la consulta requiere ticket | Sí (gpt-4o-mini) |
| `RoutingService` | Decidir acción final | No (lógica local) |
| `IngestionService` | Cargar docs → chunks → embeddings → ChromaDB | No (solo embeddings) |

---

### 4. Vector Store (Base de datos vectorial)

**Tecnología:** ChromaDB 1.5.8 (SQLite local)

**Qué almacena:** Embeddings de 384 dimensiones de fragmentos de documentos

**Proceso de ingesta:**
```
./docs/*.md, *.txt, *.pdf
      │
      ▼ LangChain TextSplitter
  Chunks (400 chars, overlap 80)
      │
      ▼ HuggingFace Embeddings
  Vectores 384-dim
      │
      ▼
  ChromaDB (colección: "soporte_docs")
  Persistido en: ./data/chroma_db/
```

**Búsqueda:**
- `similarity_search_with_score(query, k=4)` → 4 fragmentos más cercanos
- Score de similitud: `1 / (1 + distancia_L2)` → valor en [0, 1]
- Threshold de relevancia: `score > 0.10`

---

### 5. Modelos de IA utilizados

| Modelo | Proveedor | Propósito | Dónde se ejecuta |
|---|---|---|---|
| `gpt-4o-mini` | OpenAI API | Generación de respuestas, scoring, detección derivación | Nube (OpenAI) |
| `paraphrase-multilingual-MiniLM-L12-v2` | HuggingFace (sentence-transformers) | Generación de embeddings para búsqueda semántica | Local (CPU/GPU) |

**Orquestación de LLM:** LangChain 0.3.28

---

### 6. Lógica de routing

El `RoutingService` toma la decisión final basándose en tres señales:

```
Inputs: score, tiene_info, requiere_derivacion, pregunta_texto

Reglas (en orden de prioridad):
  1. Detecta palabra de escalación → ESCALAR HUMANO
  2. score < 0.3 → ESCALAR HUMANO
  3. tiene_info + requiere_derivacion + score ≥ 0.60 → DERIVAR TICKET
  4. tiene_info + score ≥ 0.60 → RESPONDER
  5. else → ESCALAR HUMANO

Outputs: AccionRouter.RESPONDER | DERIVAR | ESCALAR
```

---

### 7. Infraestructura de contenedores

**Docker Compose — 2 servicios:**

```
┌────────────────────────────────────────────┐
│         helpdesk_net (bridge)              │
│                                            │
│  ┌─────────────┐    ┌───────────────────┐  │
│  │     api     │    │        ui         │  │
│  │  :8000      │◄───│  :8501 Streamlit  │  │
│  │  FastAPI    │    │  API_URL=api:8000 │  │
│  └──────┬──────┘    └───────────────────┘  │
│         │                                  │
│  ┌──────▼──────┐    ┌───────────────────┐  │
│  │ chroma_data │    │    logs_data      │  │
│  │  (volumen)  │    │    (volumen)      │  │
│  └─────────────┘    └───────────────────┘  │
└────────────────────────────────────────────┘
```

**Dockerfile:** Multi-stage (builder + runtime), usuario no-root (`appuser`)

---

## Flujo completo end-to-end

```
┌──────────┐     HTTP POST /ask      ┌────────────────────┐
│  Usuario  │ ──────────────────────► │   FastAPI :8000    │
│ (via UI   │                         │   (api container)  │
│ o API)   │ ◄────────────────────── │                    │
└──────────┘     PreguntaResponse     └────────┬───────────┘
                                               │
                              ┌────────────────▼────────────────────┐
                              │         RAGServiceImpl               │
                              │                                      │
                   ┌──────────▼──────────┐                          │
                   │  ChromaDB           │  ← retrieval_service     │
                   │  similarity search  │    (4 fragmentos top-k)   │
                   │  :data/chroma_db    │                          │
                   └─────────────────────┘                          │
                                               │                    │
                              ┌────────────────▼───────────────┐    │
                              │        OpenAI API              │    │
                              │        gpt-4o-mini             │    │
                              │                                │    │
                              │  ① generation_service (resp)  │    │
                              │  ② scoring_service (score)    │    │
                              │  ③ derivation_service (bool)  │    │
                              └────────────────────────────────┘    │
                                               │                    │
                              ┌────────────────▼───────────────┐    │
                              │        RoutingService           │    │
                              │  → RESPONDER / DERIVAR /        │    │
                              │    ESCALAR                      │    │
                              └─────────────────────────────────┘
```

---

## Dependencias externas del sistema

| Servicio externo | Propósito | Requerido |
|---|---|---|
| **OpenAI API** | LLM (generación, scoring, derivación) | Sí (API Key) |
| **HuggingFace Hub** | Descarga del modelo de embeddings (primer uso) | Sí (primer arranque) |

---

## Dimensiones técnicas clave para el diagrama

- **Tipo de arquitectura:** Monolito modular (una sola unidad de despliegue)
- **Comunicación interna:** In-process (llamadas directas entre capas)
- **Comunicación externa:** HTTP REST hacia OpenAI, local para ChromaDB
- **Persistencia:** Vector store local (ChromaDB/SQLite) + logs de texto plano
- **UI ↔ API:** HTTP interno Docker (`http://api:8000`)
- **Documentos de conocimiento:** Archivos .md, .txt, .pdf en `./docs/` (montados como volumen read-only)
- **Ingesta:** Proceso separado, ejecutado manualmente o vía POST /ingest

---

## Nodos sugeridos para el diagrama

1. **Usuario final** (actor externo)
2. **Streamlit UI** (contenedor Docker, puerto 8501)
3. **FastAPI API** (contenedor Docker, puerto 8000)
4. **RAG Pipeline** (componente lógico interno del API)
   - Sub-nodos: Retrieval, Generation, Scoring, Derivation, Routing
5. **ChromaDB** (vector store, SQLite local, volumen Docker)
6. **OpenAI API** (servicio externo en la nube)
7. **HuggingFace Embeddings** (proceso local dentro del contenedor)
8. **Base de conocimiento** (`./docs/` — archivos Markdown/TXT/PDF)
9. **Docker Network** (helpdesk_net — agrupa los contenedores)

---

## Tecnologías a incluir con sus logos/iconos

- Python 3.11
- FastAPI
- Streamlit
- LangChain
- ChromaDB
- OpenAI (gpt-4o-mini)
- HuggingFace / sentence-transformers
- Docker + Docker Compose
- Pydantic v2
