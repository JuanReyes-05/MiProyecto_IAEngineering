"""CLI wrapper para ejecutar el pipeline de ingesta."""
import argparse
import logging
import sys
from pathlib import Path

# Permite ejecutar `python scripts/ingest.py` desde la raíz del proyecto
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.ingestion_service import ejecutar_ingesta  # noqa: E402


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Ingesta de documentos al vector store.")
    parser.add_argument(
        "--limpiar",
        action="store_true",
        help="Elimina la base vectorial existente antes de reingestar.",
    )
    args = parser.parse_args()

    resultado = ejecutar_ingesta(limpiar=args.limpiar)
    if not resultado["exito"]:
        print(f"Ingesta fallida: {resultado['mensaje']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
