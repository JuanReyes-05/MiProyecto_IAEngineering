"""Wrapper del cliente de embeddings."""
from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import Settings


def build_embeddings(settings: Settings) -> HuggingFaceEmbeddings:
    """Construye el cliente de embeddings según la configuración."""
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
