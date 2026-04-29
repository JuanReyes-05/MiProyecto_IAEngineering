"""Configuración centralizada con pydantic-settings."""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_base_url: Optional[str] = None
    llm_model: str = "gpt-4o-mini"

    embedding_model: str = (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    docs_dir: str = "./docs"
    chroma_dir: str = "./data/chroma_db"
    collection_name: str = "soporte_docs"

    chunk_size: int = 400
    chunk_overlap: int = 80

    top_k: int = 4
    confidence_threshold: float = 0.65
    minimum_score: float = 0.60

    host: str = "0.0.0.0"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
