"""Crea el modelo de embeddings y el LLM según la configuración."""
import os

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

import config


def get_embeddings() -> Embeddings:
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )


def get_llm() -> BaseChatModel:
    proveedor = config.LLM_PROVIDER
    if proveedor == "google":
        _exigir_key("GOOGLE_API_KEY")
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=config.GOOGLE_MODEL, temperature=0)
    if proveedor == "openai":
        _exigir_key("OPENAI_API_KEY")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=config.OPENAI_MODEL, temperature=0)
    if proveedor == "anthropic":
        _exigir_key("ANTHROPIC_API_KEY")
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=config.ANTHROPIC_MODEL, max_tokens=1024)
    raise ValueError(f"LLM_PROVIDER inválido: {proveedor!r} (usá google, openai o anthropic)")


def _exigir_key(nombre: str) -> None:
    if not os.getenv(nombre):
        raise RuntimeError(f"Falta {nombre} en el .env (o probá el modo offline: python main.py --demo)")
