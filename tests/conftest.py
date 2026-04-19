"""Fixtures compartidas para tests."""
import pytest

from app.core.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        openai_api_key="test-key",
        llm_model="gpt-4o-mini",
        chroma_dir="./data/chroma_test",
        confidence_threshold=0.65,
        minimum_score=0.60,
    )
