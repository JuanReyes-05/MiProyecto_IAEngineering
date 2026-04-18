"""
test_diagnostico.py — Diagnóstico del pipeline RAG
Ejecuta paso a paso para encontrar dónde falla.
"""
import os
import sys
from dotenv import load_dotenv

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
print(f"  CHROMA_DIR: {os.getenv('CHROMA_DIR', './chroma_db')}")
print(f"  EMBEDDING_MODEL: {os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')}")
print(f"  LLM_MODEL: {os.getenv('LLM_MODEL', 'gpt-4o-mini')}")

# ── Test 2: ChromaDB — cuántos chunks hay ────────────────────
print("\n[2/6] Base vectorial ChromaDB")
try:
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma

    CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "soporte_docs")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
    )
    count = vectorstore._collection.count()
    print(f"  Fragmentos indexados: {count}")

    if count == 0:
        print("  ERROR: La base vectorial está VACÍA.")
        print("  Ejecuta: python ingest.py --limpiar")
        sys.exit(1)
except Exception as e:
    print(f"  ERROR conectando a ChromaDB: {e}")
    sys.exit(1)

# ── Test 3: Contenido de los chunks ──────────────────────────
print("\n[3/6] Contenido de los chunks almacenados")
try:
    collection = vectorstore._collection
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
        resultados = vectorstore.similarity_search_with_score(query=pregunta, k=3)
        if not resultados:
            print("    SIN RESULTADOS")
        for doc, dist in resultados:
            score = 1 / (1 + dist)  # Misma conversión que usa rag_chain.py
            archivo = doc.metadata.get("archivo", "?")
            preview = doc.page_content[:80].replace("\n", " ")
            print(f"    dist={dist:.4f} score={score:.4f} [{archivo}] \"{preview}...\"")
    except Exception as e:
        print(f"    ERROR: {e}")

# ── Test 5: LLM responde? ───────────────────────────────────
print("\n[5/6] Test de conexión al LLM")
try:
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY", "not-needed"),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )
    resp = llm.invoke("Responde solo 'OK'")
    print(f"  LLM responde: {resp.content.strip()}")
except Exception as e:
    print(f"  ERROR con LLM: {e}")

# ── Test 6: Pipeline completo ────────────────────────────────
print("\n[6/6] Pipeline RAG completo")
try:
    from rag_chain import RAGChain
    rag_test = RAGChain()
    rag_test.inicializar()

    pregunta = "¿Cómo conecto mi laptop a la red WiFi corporativa?"
    resultado = rag_test.consultar(pregunta=pregunta, usuario_id="test")

    print(f"  Pregunta: {pregunta}")
    print(f"  Respuesta: {resultado.respuesta[:200]}...")
    print(f"  Score confianza: {resultado.score_confianza}")
    print(f"  Tiene info: {resultado.tiene_info}")
    print(f"  Requiere derivación: {resultado.requiere_derivacion}")
    print(f"  Fuentes: {len(resultado.fuentes)}")
    for f in resultado.fuentes:
        print(f"    - {f.archivo} (score={f.score}): {f.fragmento[:60]}...")
except Exception as e:
    print(f"  ERROR en pipeline: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("DIAGNÓSTICO COMPLETADO")
print("=" * 60)
