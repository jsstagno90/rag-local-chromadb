# RAG local de AgendaYa

Sistema de preguntas y respuestas sobre documentación técnica: busca los fragmentos relevantes en una base vectorial local (ChromaDB) y genera una respuesta basada solo en ellos. Si la respuesta no está en los documentos, contesta "No lo sé".

Pre-entrega 3 del curso de AI Engineering (Coderhouse).

## Cómo funciona

```
INGESTA (una vez):  data/*.md → chunks de 500 tokens (50 de overlap) → embeddings → ChromaDB (./vectorstore)
CONSULTA:           pregunta → embedding → top 4 chunks de ChromaDB → prompt con contexto → LLM → RAGResponse
```

- **Ingesta (`ingest.py`):** lee los `.txt` y `.md` de `data/`, los trocea con `RecursiveCharacterTextSplitter` midiendo en tokens (tiktoken) y los guarda en ChromaDB con IDs deterministas (hash del contenido). Si la base ya existe, no vuelve a indexar.
- **Mismo modelo de embeddings:** el nombre del modelo queda guardado en la colección. Si se intenta consultar con otro modelo, el sistema lo frena y pide `--reindex`.
- **Recuperación y generación (`rag.py`):** una cadena LCEL que recupera los 4 chunks más parecidos, arma el prompt y llama al LLM de forma asíncrona. La salida pasa por un `PydanticOutputParser` y se reintenta una vez si el JSON viene roto.
- **Anti-alucinación:** el prompt obliga a responder solo con el contexto o decir "No lo sé", y las fuentes que devuelve el modelo se filtran: solo quedan archivos que de verdad se recuperaron.

## Estructura

| Archivo | Contenido |
|---|---|
| `data/` | Dataset de ejemplo: 4 manuales de una app de turnos ficticia |
| `ingest.py` | Carga, chunking y persistencia en ChromaDB |
| `rag.py` | Cadena LCEL y `get_rag_response(query)` |
| `schemas.py` | Modelo Pydantic `RAGResponse` (respuesta + fuentes) |
| `providers.py` | Crea el modelo de embeddings y el LLM según el `.env` |
| `offline.py` | Embeddings por palabras y LLM simulado, para el modo demo y los tests |
| `main.py` | Prueba con una pregunta que está en los documentos y una trampa |
| `tests/test_rag.py` | Tests con pytest |

## Cómo correrlo

Requiere Python 3.12.

```bash
py -3.12 -m venv .venv          # Linux/Mac: python3.12 -m venv .venv
.venv\Scripts\activate          # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # Linux/Mac: cp .env.example .env
```

| Comando | Qué hace |
|---|---|
| `python main.py --demo` | Modo offline, sin API keys: recorre todo el flujo con embeddings por palabras y un LLM simulado |
| `python ingest.py` | Indexa `data/` en `./vectorstore` (solo si no existe). `--reindex` vuelve a indexar todo |
| `python main.py` | Modo real: embeddings de Hugging Face + el LLM del `.env` |
| `pytest` | Corre los tests (no necesitan API keys) |

La primera vez, el modo real descarga el modelo de embeddings (unos 450 MB) y tiktoken descarga su tabla de tokens.

## Variables de entorno

| Variable | Descripción |
|---|---|
| `LLM_PROVIDER` | `google` (Gemini), `openai` o `anthropic` |
| `GOOGLE_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Solo la del proveedor elegido |
| `GOOGLE_MODEL` / `OPENAI_MODEL` / `ANTHROPIC_MODEL` | Modelo de cada proveedor |
| `EMBEDDING_MODEL` | Modelo de embeddings de Hugging Face (corre local, gratis) |

## Ejemplo de salida

Pregunta que está en los documentos:

```json
{
  "respuesta": "Si Redis no responde, la API sigue funcionando: calcula la disponibilidad directamente desde PostgreSQL. El sistema se vuelve más lento, pero no se pierden reservas.",
  "fuentes": ["arquitectura.md"]
}
```

Pregunta trampa ("¿Qué lenguaje se usa para programar la app de iOS?"):

```json
{
  "respuesta": "No lo sé",
  "fuentes": []
}
```
