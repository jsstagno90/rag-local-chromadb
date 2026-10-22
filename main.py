"""Prueba del sistema RAG con dos preguntas: una que está en los documentos y una trampa.

    python main.py          → modelo de embeddings real + LLM real (necesita la API key del LLM)
    python main.py --demo   → modo offline: embeddings por palabras + LLM simulado, sin keys ni internet
"""
import asyncio
import logging
import sys

import config
from ingest import obtener_vectorstore
from rag import construir_cadena, get_rag_response

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
for ruidoso in ("httpx", "chromadb", "sentence_transformers"):
    logging.getLogger(ruidoso).setLevel(logging.WARNING)

PREGUNTAS = [
    ("En los documentos", "¿Qué pasa con las reservas si Redis no responde?"),
    ("Pregunta trampa", "¿Qué lenguaje se usa para programar la app de iOS?"),
]


def armar_cadena(demo: bool):
    if demo:
        from offline import KeywordEmbeddings, extractive_llm
        vs = obtener_vectorstore(KeywordEmbeddings(), "offline-keyword", chroma_dir="vectorstore_demo")
        return construir_cadena(vs, extractive_llm)

    from providers import get_embeddings, get_llm
    llm = get_llm()  # primero el LLM: si falta la key, avisa antes de bajar el modelo de embeddings
    vs = obtener_vectorstore(get_embeddings(), config.EMBEDDING_MODEL)
    return construir_cadena(vs, llm)


async def main():
    demo = "--demo" in sys.argv
    print(f"\n=== RAG de AgendaYa ({'modo demo offline' if demo else 'modo real'}) ===")
    try:
        cadena = armar_cadena(demo)
    except RuntimeError as e:
        print(f"\n{e}")
        return

    for titulo, pregunta in PREGUNTAS:
        print(f"\n--- {titulo} ---")
        r = await get_rag_response(pregunta, cadena)
        print(f"Pregunta:  {pregunta}")
        print(f"Respuesta: {r.respuesta}")
        print(f"Fuentes:   {', '.join(r.fuentes) or '(ninguna)'}")
        print(f"JSON:      {r.model_dump_json()}")


if __name__ == "__main__":
    asyncio.run(main())
