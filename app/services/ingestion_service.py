"""Pipeline de ingesta de documentos al vector store."""
import logging
import shutil
from pathlib import Path
from typing import List, Optional

from langchain_chroma import Chroma
from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
)
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import Settings, get_settings
from app.infrastructure.embeddings_client import build_embeddings

logger = logging.getLogger(__name__)


LOADERS = {
    ".pdf": PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".txt": TextLoader,
    ".md": TextLoader,
}


def cargar_documentos(docs_dir: str) -> List[Document]:
    docs_path = Path(docs_dir)

    if not docs_path.exists():
        logger.warning("Carpeta '%s' no existe. Creándola...", docs_dir)
        docs_path.mkdir(parents=True)
        logger.info(
            "Coloca tus archivos PDF, DOCX, TXT o MD en '%s' y vuelve a ejecutar.",
            docs_dir,
        )
        return []

    archivos = list(docs_path.rglob("*"))
    archivos_validos = [f for f in archivos if f.suffix.lower() in LOADERS]

    if not archivos_validos:
        logger.warning("No se encontraron documentos en '%s'.", docs_dir)
        logger.info("Formatos soportados: PDF, DOCX, TXT, MD")
        return []

    logger.info("Encontrados %d archivos para ingestar", len(archivos_validos))

    todos: List[Document] = []
    for archivo in archivos_validos:
        try:
            loader_class = LOADERS[archivo.suffix.lower()]
            if loader_class is TextLoader:
                loader = loader_class(str(archivo), encoding="utf-8", autodetect_encoding=True)
            else:
                loader = loader_class(str(archivo))
            docs = loader.load()
            for doc in docs:
                doc.metadata["archivo"] = archivo.name
                doc.metadata["ruta"] = str(archivo)
                doc.metadata["tipo"] = archivo.suffix.lower().replace(".", "")
            todos.extend(docs)
            logger.info("  ✓ %s — %d página(s)", archivo.name, len(docs))
        except Exception as e:
            logger.error("  ✗ Error cargando %s: %s", archivo.name, e)

    logger.info("Total: %d páginas cargadas", len(todos))
    return todos


def dividir_en_fragmentos(
    documentos: List[Document],
    chunk_size: int,
    chunk_overlap: int,
) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documentos)
    chunks = [f for f in chunks if len(f.page_content.strip()) > 50]

    avg = sum(len(f.page_content) for f in chunks) // len(chunks) if chunks else 0
    logger.info(
        "Documentos divididos en %d fragmentos (avg %d chars)", len(chunks), avg
    )
    return chunks


def load_or_create_vectorstore(chunks, settings: Settings) -> Chroma:
    embeddings = build_embeddings(settings)
    chroma_path = Path(settings.chroma_dir)

    if chroma_path.exists() and any(chroma_path.iterdir()):
        logger.info("Cargando vector store existente de ChromaDB...")
        vectorstore = Chroma(
            persist_directory=settings.chroma_dir,
            embedding_function=embeddings,
            collection_name=settings.collection_name,
        )
        logger.info(
            "Vector store cargado (%d chunks)",
            vectorstore._collection.count(),
        )
    else:
        logger.info("Creando embeddings para %d chunks...", len(chunks))
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=settings.chroma_dir,
            collection_name=settings.collection_name,
        )
        logger.info("Vector store creado y guardado en ChromaDB")

    return vectorstore


def limpiar_vectorstore(chroma_dir: str) -> None:
    chroma_path = Path(chroma_dir)
    if chroma_path.exists():
        shutil.rmtree(chroma_path)
        logger.info("Base vectorial '%s' eliminada", chroma_dir)
    else:
        logger.info("No había base vectorial previa")


def ejecutar_ingesta(
    limpiar: bool = False, settings: Optional[Settings] = None
) -> dict:
    settings = settings or get_settings()

    logger.info("=" * 50)
    logger.info("INICIANDO PIPELINE DE INGESTA")
    logger.info("=" * 50)

    if limpiar:
        logger.info("Limpiando base vectorial existente...")
        limpiar_vectorstore(settings.chroma_dir)

    documentos = cargar_documentos(settings.docs_dir)
    if not documentos:
        return {
            "exito": False,
            "mensaje": "No se encontraron documentos",
            "fragmentos": 0,
        }

    chunks = dividir_en_fragmentos(
        documentos, settings.chunk_size, settings.chunk_overlap
    )
    if not chunks:
        return {
            "exito": False,
            "mensaje": "No se generaron fragmentos",
            "fragmentos": 0,
        }

    load_or_create_vectorstore(chunks, settings)

    stats = {
        "exito": True,
        "documentos": len(set(f.metadata.get("archivo", "") for f in chunks)),
        "fragmentos": len(chunks),
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "vectorstore": settings.chroma_dir,
        "coleccion": settings.collection_name,
    }

    logger.info("=" * 50)
    logger.info("INGESTA COMPLETADA")
    logger.info("  Documentos procesados : %d", stats["documentos"])
    logger.info("  Chunks generados      : %d", stats["fragmentos"])
    logger.info("  Base vectorial en     : %s/", settings.chroma_dir)
    logger.info("=" * 50)

    return stats
