# CLAUDE.md — Helpdesk AI (RAG Soporte al Cliente)

## Propósito del proyecto

Sistema de soporte al cliente basado en RAG (Retrieval-Augmented Generation) que responde preguntas a partir de una base de conocimiento propia. El sistema clasifica cada consulta en tres acciones posibles: **responder** automáticamente, **derivar** a ticket, o **escalar** a un agente humano.

---

## Stack tecnológico

### Backend (API)

| Capa | Tecnología | Versión |
|---|---|---|
| Lenguaje | Python | 3.11 |
| Framework HTTP | FastAPI | 0.115.0 |
| ASGI Server | Uvicorn | 0.30.6 |
| Validación / DTOs | Pydantic v2 + pydantic-settings | 2.9.2 / 2.5.2 |
| Orquestación LLM | LangChain | 0.3.28 |
| Integración OpenAI | langchain-openai | 0.3.35 |
| Embeddings locales | langchain-huggingface + sentence-transformers | 0.3.1 / 5.4.1 |
| Vector store | ChromaDB (SQLite local) | 1.5.8 |
| Chunking | langchain-text-splitters | 0.3.11 |

**Modelo LLM:** `gpt-4o-mini` (OpenAI)
**Modelo de embeddings:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (multilingual, 384-dim)

### Frontend

| Capa | Tecnología | Versión |
|---|---|---|
| UI interactiva | Streamlit | 1.39.0 |

### Infraestructura

| Capa | Tecnología |
|---|---|
| Contenedores | Docker (multi-stage: builder + runtime) |
| Orquestación local | Docker Compose |
| Persistencia | Volúmenes Docker (`chroma_data`, `logs_data`) |

### Testing

| Capa | Tecnología |
|---|---|
| Framework | pytest |
| Estrategia | Unit tests con mocks via `typing.Protocol` |

---

## Arquitectura

### Patrón

**Monolito modular con capas DDD (Domain-Driven Design)** e inyección de dependencias explícita usando `typing.Protocol`.

### Capas y responsabilidades

```
backend/
  app/api/          → Endpoints HTTP, validación de I/O, inyección de servicios
  app/core/         → Configuración global (settings), logging, prompts LLM
  app/domain/       → Entidades puras sin dependencias externas (dataclasses)
  app/schemas/      → DTOs Pydantic para request/response y enums
  app/services/     → Lógica de negocio y orquestación del pipeline RAG
  app/repositories/ → Abstracción del acceso a ChromaDB (VectorStoreRepository)
  app/infrastructure/ → Clientes externos: LLM (OpenAI) y embeddings (HuggingFace)
  scripts/          → CLI de ingesta y diagnóstico (fuera del runtime API)
  tests/            → Fixtures en conftest.py + unit tests con mocks
  docs/             → Base de conocimiento a ingestar (FAQ, guías, políticas)
  data/             → Volumen de ChromaDB (no committed, generado en runtime)
  Dockerfile        → Multi-stage (builder + runtime) para la API
  requirements.txt  → Dependencias del backend (sin streamlit)

frontend/
  app.py            → UI Streamlit (chat interactivo con la API)
  Dockerfile        → Imagen ligera solo con streamlit
  requirements.txt  → streamlit + requests + python-dotenv
```

### Flujo principal de datos (POST /ask)

```
Usuario → POST /ask
  → PreguntaRequest (Pydantic validation)
  → RAGServiceImpl.consultar()
      → retrieval_service.recuperar()     [ChromaDB similarity search]
      → generation_service.generar()      [OpenAI gpt-4o-mini]
      → scoring_service.calcular()        [LLM evalúa score 0.0–1.0]
      → derivation_service.requiere()     [LLM detecta si hay que derivar]
  → RespuestaInterna (domain entity)
  → routing_service.definir_accion()     [RESPONDER | DERIVAR | ESCALAR]
  → PreguntaResponse (DTO)
  → BackgroundTask: registrar en interacciones.log
```

### Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/` | Metadata de la API |
| GET | `/health` | Estado del sistema + estadísticas del vector store |
| POST | `/ask` | Consulta principal (RAG + routing) |
| POST | `/ingest` | Re-ingesta de documentos en background |

---

## Convenciones de código

### Naming

- **Carpetas y módulos:** `snake_case` (rag_service.py, chroma_repository.py)
- **Clases:** `PascalCase` (RAGServiceImpl, PreguntaResponse)
- **Implementaciones de servicios:** sufijo `Impl` (RAGServiceImpl, RoutingServiceImpl)
- **Funciones y métodos:** `snake_case` (recuperar, generar, definir_accion)
- **Constantes y prompts:** `UPPER_SNAKE_CASE` (PROMPT_SISTEMA, PALABRAS_ESCALACION)
- **Enums:** `PascalCase.UPPER_SNAKE_CASE` (AccionRouter.RESPONDER)

### Type hints

Obligatorios en todos los métodos públicos. Usar tipos nativos Python 3.10+ (`list[X]` en lugar de `List[X]`).

### Abstracciones

Usar `typing.Protocol` (no clases base abstractas) para contratos de servicios y repositorios. Esto facilita el mocking en tests sin herencia forzada.

### Logging

```python
logger = logging.getLogger(__name__)
logger.info("Consulta de '%s': %s...", usuario_id or "anon", pregunta[:60])
```

Sin `print()` en código de aplicación. Logs estructurados por módulo.

### Comentarios

Solo donde el **por qué** no es obvio. No comentar lo que el código ya dice.

---

## Variables de entorno clave

| Variable | Default | Descripción |
|---|---|---|
| `OPENAI_API_KEY` | (requerido) | Clave de OpenAI |
| `LLM_MODEL` | `gpt-4o-mini` | Modelo de lenguaje |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Modelo de embeddings |
| `CONFIDENCE_THRESHOLD` | `0.65` | Score mínimo para considerar que hay información suficiente |
| `MINIMUM_SCORE` | `0.60` | Score mínimo para responder automáticamente |
| `TOP_K` | `4` | Fragmentos a recuperar por consulta |
| `CHUNK_SIZE` | `400` | Tamaño de chunk en caracteres |
| `CHUNK_OVERLAP` | `80` | Solapamiento entre chunks |
| `CHROMA_DIR` | `./data/chroma_db` | Directorio de persistencia del vector store |
| `DOCS_DIR` | `./docs` | Directorio de documentos para ingesta |
| `COLLECTION_NAME` | `soporte_docs` | Nombre de la colección en ChromaDB |

---

## Cómo ejecutar el proyecto

### Local (desarrollo)

```bash
# Setup — backend
python -m venv venv && source venv/bin/activate  # o venv\Scripts\activate en Windows
pip install -r backend/requirements.txt
cp .env.example .env  # rellenar OPENAI_API_KEY

# Ingestar documentos (desde backend/)
cd backend && python scripts/ingest.py

# API (con hot reload) — los imports usan 'from app.xxx', correr desde backend/
cd backend && uvicorn app.main:app --reload
# → http://localhost:8000/docs

# UI Streamlit — terminal separada, desde la raíz
pip install -r frontend/requirements.txt
streamlit run frontend/app.py
# → http://localhost:8501
```

### Docker Compose (recomendado)

```bash
# Desde la raíz del proyecto
docker compose up --build
docker compose exec api python scripts/ingest.py  # primera ingesta
docker compose logs -f
```

### Tests

```bash
pytest backend/tests/unit -v
```

---

## Prácticas establecidas en el repositorio

1. **Separación de capas estricta:** Los servicios no conocen FastAPI ni Pydantic; las schemas/DTOs no contienen lógica de negocio.
2. **Protocol para abstracciones:** Todos los contratos de servicio y repositorio se definen con `typing.Protocol`.
3. **Inyección de dependencias en `api/dependencies.py`:** Los servicios se componen en el lifespan de FastAPI y se inyectan vía `Depends()`.
4. **Background tasks para operaciones lentas:** La ingesta de documentos y el logging de interacciones usan `BackgroundTasks` de FastAPI.
5. **Multi-stage Docker:** El Dockerfile usa build multi-stage para minimizar la imagen final.
6. **Usuario no-root en contenedor:** El Dockerfile crea `appuser` sin privilegios de root.
7. **Docs en `./docs/` son la fuente de verdad:** El conocimiento del sistema proviene exclusivamente de los documentos ingestados; no hay conocimiento hardcodeado en prompts.
8. **Thresholds configurables por env:** Los umbrales de confianza y scoring son parámetros de configuración, no constantes en código.
9. **Prompts centralizados en `core/prompts.py`:** Todos los prompts al LLM están en un único módulo para facilitar ajustes.
10. **Chromadb persiste en volumen Docker:** La base vectorial no se reconstruye en cada restart; solo al ejecutar ingest.

---

## Estructura de tests esperada

- `tests/unit/services/` → tests de servicios con mocks (sin ChromaDB, sin OpenAI)
- `tests/integration/` → tests con infraestructura real (reservado para futuras etapas)
- `tests/conftest.py` → fixtures compartidas (settings, mocks de repositorio)

---

## Estado del proyecto (MVP v1.0.0)

- [x] Etapa 0: MVP RAG funcional con FastAPI
- [x] Etapa 1: Arquitectura modular + Docker + scoring
- [ ] Etapa 2: Agente completo con memoria de conversación
- [ ] Etapa 3: Hardening, autenticación, cifrado, HTTPS

---

## Notas de seguridad

- La API no tiene autenticación de clientes aún (no incluir en producción sin agregar)
- HTTPS debe configurarse en la capa de reverse proxy (nginx/traefik) en producción
- Las interacciones se loguean en `interacciones.log`; revisar si contienen PII antes de almacenar en producción
