"""DTOs del endpoint /ingest."""
from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    limpiar: bool = Field(
        False,
        description="Si es true, limpia la base vectorial antes de reingestar.",
    )
