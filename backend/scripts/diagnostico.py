"""Diagnóstico del pipeline RAG — ejecuta paso a paso para detectar fallos."""
import os
import sys
from pathlib import Path

# Permite ejecutar `python scripts/diagnostico.py` desde la raíz del proyecto
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

print("=" * 60)
print("DIAGNÓSTICO DEL PIPELINE RAG")
print("=" * 60)

# ── Test 1: Variables de entorno ─────────────────────────────
print("\n[1/6] Variables de entorno")
api_key = os.getenv("OPENAI_API_KEY", "")
base_url = os.getenv("OPENAI_BASE_URL", "")
print(f"  OPENAI_API_KEY: {'***' + api_key[-4:] if len(api_key) > 4 else 'NO CONFIGURADA'}")
print(f"  OPENAI_BASE_URL: {base_url or '(default OpenAI)'}")
print(f"  CHROMA_DIR: {os.getenv('CHROMA_DIR', './data/chroma_db')}")
print(
    "  EMBEDDING_MODEL: "
    f"{os.getenv('EMBEDDING_MODEL', 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')}"
)
print(f"  LLM_MODEL: {os.getenv('LLM_MODEL', 'gpt-4o-mini')}")

# ── Test 2: ChromaDB ─────────────────────────────────────────
print("\n[2/6] Base vectorial ChromaDB")
try:
    from app.core.config import get_settings
    from app.infrastructure.embeddings_client import build_embeddings
    from app.repositories.chroma_repository import ChromaRepository

    settings = get_settings()
    embeddings = build_embeddings(settings)
    repo = ChromaRepository(settings, embeddings)
    count = repo.contar()
    print(f"  Fragmentos indexados: {count}")

    if count == 0:
        print("  ERROR: La base vectorial está VACÍA.")
        print("  Ejecuta: python scripts/ingest.py --limpiar")
        sys.exit(1)
except Exception as e:
    print(f"  ERROR conectando a ChromaDB: {e}")
    sys.exit(1)

# ── Test 3: Contenido de los chunks ──────────────────────────
print("\n[3/6] Contenido de los chunks almacenados")
try:
    collection = repo.raw._collection
    all_data = collection.get(include=["documents", "metadatas"])
    docs = all_data["documents"]
    metas = all_data["metadatas"]

    print(f"  Total chunks: {len(docs)}")
    for i, (doc, meta) in enumerate(zip(docs, metas)):
        archivo = meta.get("archivo", "?")
        preview = doc[:100].replace("\n", " ")
        print(f"  [{i}] {archivo}: \"{preview}...\"")
except Exception as e:
    print(f"  ERROR leyendo chunks: {e}")

# ── Test 4: Búsqueda de similitud ────────────────────────────
print("\n[4/6] Búsqueda de similitud (similarity search)")
PREGUNTAS_TEST = [
    "¿Cómo conecto mi laptop a la red WiFi corporativa?",
    "¿Cómo puedo restablecer mi contraseña?",
    "¿Cómo configuro la VPN?",
]

for pregunta in PREGUNTAS_TEST:
    print(f"\n  Pregunta: \"{pregunta}\"")
    try:
        fragmentos = repo.buscar(pregunta, k=3)
        if not fragmentos:
            print("    SIN RESULTADOS")
        for frag in fragmentos:
            preview = frag.contenido[:80].replace("\n", " ")
            print(
                f"    score={frag.similitud:.4f} [{frag.archivo}] \"{preview}...\""
            )
    except Exception as e:
        print(f"    ERROR: {e}")

# ── Test 5: LLM responde ─────────────────────────────────────
print("\n[5/6] Test de conexión al LLM")
try:
    from app.infrastructure.llm_client import OpenAILLMClient

    llm = OpenAILLMClient(settings)
    resp = llm.invoke("Responde solo 'OK'")
    print(f"  LLM responde: {resp.strip()}")
except Exception as e:
    print(f"  ERROR con LLM: {e}")

# ── Test 6: Pipeline completo ────────────────────────────────
print("\n[6/6] Pipeline RAG completo")
try:
    from app.infrastructure.llm_client import OpenAILLMClient
    from app.services.generation_service import GenerationServiceImpl
    from app.services.rag_service import RAGServiceImpl
    from app.services.retrieval_service import RetrievalServiceImpl
    from app.services.scoring_service import DerivationServiceImpl, ScoringServiceImpl

    llm = OpenAILLMClient(settings)
    rag = RAGServiceImpl(
        settings=settings,
        retrieval=RetrievalServiceImpl(repo, settings),
        generation=GenerationServiceImpl(llm),
        scoring=ScoringServiceImpl(llm),
        derivation=DerivationServiceImpl(llm),
    )

    pregunta = "¿Cómo conecto mi laptop a la red WiFi corporativa?"
    resultado = rag.consultar(pregunta=pregunta, usuario_id="test")

    print(f"  Pregunta: {pregunta}")
    print(f"  Respuesta: {resultado.respuesta[:200]}...")
    print(f"  Score confianza: {resultado.score_confianza}")
    print(f"  Tiene info: {resultado.tiene_info}")
    print(f"  Requiere derivación: {resultado.requiere_derivacion}")
    print(f"  Fuentes: {len(resultado.fragmentos)}")
    for f in resultado.fragmentos:
        print(
            f"    - {f.archivo} (score={f.similitud:.3f}): {f.contenido[:60]}..."
        )
except Exception as e:
    print(f"  ERROR en pipeline: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 60)
print("DIAGNÓSTICO COMPLETADO")
print("=" * 60)
