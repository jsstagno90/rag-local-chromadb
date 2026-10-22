"""Configuración leída del .env, en un solo lugar."""
import os

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = os.getenv("DATA_DIR", "data")
CHROMA_DIR = os.getenv("CHROMA_DIR", "vectorstore")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "agendaya")

# Embeddings locales y gratis (Hugging Face). El MISMO modelo se usa para indexar y para buscar.
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

# LLM: google (Gemini), openai o anthropic
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")

CHUNK_SIZE_TOKENS = 500
CHUNK_OVERLAP_TOKENS = 50
TOP_K = 4  # entre 3 y 5: más fragmentos = más ruido y "lost in the middle"
