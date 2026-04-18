# MiProyecto_IAEngineering- MVP Fase 1

Sistema de soporte al cliente con RAG (Retrieval-Augmented Generation).
Responde preguntas usando tus documentos como base de conocimiento.

## Estructura del proyecto

```
rag-soporte-mvp/
├── README.md
├── requirements.txt          # Dependencias
├── .env.example              # Variables de entorno
├── ingest.py                 # Pipeline de ingesta de documentos
├── rag_chain.py              # Cadena RAG (el cerebro)
├── main.py                   # API FastAPI
└── ui.py                     # Interfaz Streamlit para pruebas
```