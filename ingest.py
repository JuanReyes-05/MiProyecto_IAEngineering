"""
ingest.py — Pipeline de ingesta de documentos

Qué hace este archivo:
1. Lee todos los documentos de la carpeta /docs (PDF, DOCX, TXT)
2. Los divide en fragmentos manejables (chunking)
3. Convierte cada fragmento en un vector numérico (embedding)
4. Guarda todo en ChromaDB (base de datos vectorial local)
"""

import shutil

from dotenv import load_dotenv
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    DirectoryLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from pathlib import Path
from typing import List
import os
import sys
import logging

load_dotenv()

# ─── Configuración desde variables de entorno ───────────────────────────────
DOCS_DIR        = os.getenv("DOCS_DIR", "./docs")
CHROMA_DIR      = os.getenv("CHROMA_DIR", "./chroma_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "soporte_docs")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHUNK_SIZE      = int(os.getenv("CHUNK_SIZE", "400"))
CHUNK_OVERLAP   = int(os.getenv("CHUNK_OVERLAP", "80"))

# ─── Cargadores por tipo de archivo ─────────────────────────────────────────
LOADERS = {
    ".pdf":  PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".txt":  TextLoader,
    ".md":   TextLoader,
}

def cargar_documentos(docs_dir: str) -> List[Document]:
    """
    Lee todos los archivos de la carpeta docs/ y los convierte
    en objetos Document de LangChain.
    
    Cada Document tiene:
    - page_content: el texto del fragmento
    - metadata: origen (nombre del archivo, página, etc.)
    """
    docs_path = Path(docs_dir)
    
    if not docs_path.exists():
        print(f"Carpeta '{docs_dir}' no existe. Creándola...")
        docs_path.mkdir(parents=True)
        print("Coloca tus archivos PDF, DOCX o TXT en la carpeta 'docs/' y vuelve a ejecutar.")
        return []
    
    archivos = list(docs_path.rglob("*"))
    archivos_validos = [f for f in archivos if f.suffix.lower() in LOADERS]
    
    if not archivos_validos:
        print(f"No se encontraron documentos en '{docs_dir}'.")
        print("Formatos soportados: PDF, DOCX, TXT, MD")
        return []
    
    print(f"Encontrados {len(archivos_validos)} archivos para ingestar:")
    
    todos_los_docs: List[Document] = []
    
    for archivo in archivos_validos:
        try:
            loader_class = LOADERS[archivo.suffix.lower()]
            loader = loader_class(str(archivo))
            docs = loader.load()
            
            # Agregar metadata útil a cada documento
            for doc in docs:
                doc.metadata["archivo"] = archivo.name
                doc.metadata["ruta"]    = str(archivo)
                doc.metadata["tipo"]    = archivo.suffix.lower().replace(".", "")
            
            todos_los_docs.extend(docs)
            print(f"  ✓ {archivo.name} — {len(docs)} página(s)")
            
        except Exception as e:
            print(f"  ✗ Error cargando {archivo.name}: {e}")
    
    print(f"Total: {len(todos_los_docs)} páginas cargadas")
    return todos_los_docs

def dividir_en_fragmentos(documentos: List[Document]) -> List[Document]:
    """
    Divide los documentos en fragmentos pequeños (chunks).
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,          # Solapamiento para no perder contexto en los bordes
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],  # Prioridad de corte
    )
    
    chunks = splitter.split_documents(documentos)
    
    # Limpiar fragmentos muy cortos (menos de 50 caracteres = ruido)
    chunks = [f for f in chunks if len(f.page_content.strip()) > 50]
    
    print(f"Documentos divididos en {len(chunks)} fragmentos")
    print(f"Tamaño promedio: {sum(len(f.page_content) for f in chunks) // len(chunks) if chunks else 0} caracteres")
    
    return chunks

def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

def load_or_create_vectorstore(chunks):
    """Convierte en embeddings y guarda en ChromaDB, 
    o carga si ya existe.
    """
    embeddings = get_embeddings()

    if Path(CHROMA_DIR).exists() and any(Path(CHROMA_DIR).iterdir()):
        print("📂 Cargando vector store existente de ChromaDB...")
        vectorstore = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME
        )
        print(f"✅ Vector store cargado ({vectorstore._collection.count()} chunks)")
    else:
        print(f"🔢 Creando embeddings para {len(chunks)} chunks...")
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=CHROMA_DIR,
            collection_name=COLLECTION_NAME
        )
        print("✅ Vector store creado y guardado en ChromaDB")

    return vectorstore

def limpiar_vectorstore():
    """Elimina la base vectorial existente. Usar con precaución."""
    chroma_path = Path(CHROMA_DIR)
    if chroma_path.exists():
        shutil.rmtree(chroma_path)
        print(f"Base vectorial '{CHROMA_DIR}' eliminada")
    else:
        print("No había base vectorial previa")

def ejecutar_ingesta(limpiar: bool = False) -> dict:
    """
    Función principal del pipeline de ingesta.
    Orquesta todos los pasos y devuelve estadísticas.  
    Args:
        limpiar: Si True, elimina la base vectorial existente antes de ingestar.
                 Usar cuando actualizas documentos.
    Returns:
        Diccionario con estadísticas de la ingesta.
    """
    print("=" * 50)
    print("INICIANDO PIPELINE DE INGESTA")
    print("=" * 50)
    
    if not os.getenv("OPENAI_API_KEY"):
        print("No se encontró OPENAI_API_KEY en las variables de entorno.")
        print("Crea un archivo .env con: OPENAI_API_KEY=sk-proj-...")
        sys.exit(1)
    
    if limpiar:
        print("Limpiando base vectorial existente...")
        limpiar_vectorstore()
    
    # Paso 1: Cargar documentos
    documentos = cargar_documentos(DOCS_DIR)
    if not documentos:
        return {"exito": False, "mensaje": "No se encontraron documentos", "fragmentos": 0}
    
    # Paso 2: Dividir en fragmentos
    chunks = dividir_en_fragmentos(documentos)
    if not chunks:
        return {"exito": False, "mensaje": "No se generaron fragmentos", "fragmentos": 0}
    
    # Paso 3: Guardar en base vectorial
    load_or_create_vectorstore(chunks)
    
    stats = {
        "exito":       True,
        "documentos":  len(set(f.metadata.get("archivo", "") for f in chunks)),
        "fragmentos":  len(chunks),
        "chunk_size":  CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "vectorstore": CHROMA_DIR,
        "coleccion":   COLLECTION_NAME,
    }
    
    print("=" * 50)
    print("INGESTA COMPLETADA")
    print(f"  Documentos procesados : {stats['documentos']}")
    print(f"  Chunks generados  : {stats['fragmentos']}")
    print(f"  Base vectorial en     : {CHROMA_DIR}/")
    print("=" * 50)
    
    return stats
# ─── Ejecución directa ───────────────────────────────────────────────────────

if __name__ == "__main__":
    # Si pasas --limpiar como argumento, resetea la base vectorial
    limpiar = "--limpiar" in sys.argv
    resultado = ejecutar_ingesta(limpiar=limpiar)
    
    if not resultado["exito"]:
        print(f"Ingesta fallida: {resultado['mensaje']}")
        sys.exit(1)
