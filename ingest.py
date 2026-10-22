"""Ingesta: lee /data, trocea en chunks de 500 tokens y los guarda en ChromaDB.

    python ingest.py             → indexa solo si la base no existe todavía
    python ingest.py --reindex   → borra la colección y vuelve a indexar todo
"""
import hashlib
import logging
import sys
from pathlib import Path

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config

logger = logging.getLogger("ingesta")


class EmbeddingsDistintosError(Exception):
    """La base se creó con un modelo de embeddings distinto al que se quiere usar."""


def cargar_documentos(data_dir: str = config.DATA_DIR) -> list[Document]:
    """Lee todos los .txt y .md de la carpeta y guarda el nombre del archivo como metadato."""
    docs = []
    for path in sorted(Path(data_dir).glob("*")):
        if path.suffix.lower() in (".txt", ".md"):
            texto = path.read_text(encoding="utf-8")
            docs.append(Document(page_content=texto, metadata={"source": path.name}))
    logger.info("Leídos %d documentos de %s", len(docs), data_dir)
    return docs


def crear_splitter() -> RecursiveCharacterTextSplitter:
    """Chunks de 500 tokens con 50 de overlap, medidos con tiktoken."""
    try:
        return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            encoding_name="cl100k_base",
            chunk_size=config.CHUNK_SIZE_TOKENS,
            chunk_overlap=config.CHUNK_OVERLAP_TOKENS,
        )
    except Exception as e:  # sin internet la primera vez, tiktoken no puede bajar su tabla
        logger.warning("tiktoken no disponible (%s): se estiman los tokens como caracteres / 4", e)
        return RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE_TOKENS,
            chunk_overlap=config.CHUNK_OVERLAP_TOKENS,
            length_function=lambda t: len(t) // 4,
        )


def trocear(docs: list[Document]) -> list[Document]:
    chunks = crear_splitter().split_documents(docs)
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk"] = i
    logger.info("%d documentos → %d chunks", len(docs), len(chunks))
    return chunks


def _id_de(chunk: Document) -> str:
    """ID determinista: el mismo chunk siempre tiene el mismo ID, así no se duplica."""
    base = f"{chunk.metadata['source']}::{chunk.page_content}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]


def obtener_vectorstore(
    embeddings: Embeddings,
    embedding_name: str,
    chroma_dir: str = config.CHROMA_DIR,
    data_dir: str = config.DATA_DIR,
    reindex: bool = False,
) -> Chroma:
    """Devuelve la base vectorial. Solo indexa si está vacía (o si se pide --reindex)."""
    client = chromadb.PersistentClient(path=chroma_dir)

    if reindex and config.COLLECTION_NAME in [c.name for c in client.list_collections()]:
        client.delete_collection(config.COLLECTION_NAME)
        logger.info("Colección borrada para reindexar")

    coleccion = client.get_or_create_collection(
        config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine", "embedding_model": embedding_name},
    )
    modelo_guardado = (coleccion.metadata or {}).get("embedding_model")
    if modelo_guardado != embedding_name:
        raise EmbeddingsDistintosError(
            f"La base se indexó con '{modelo_guardado}' y ahora se quiere usar '{embedding_name}'. "
            "Corré: python ingest.py --reindex"
        )

    vectorstore = Chroma(
        client=client,
        collection_name=config.COLLECTION_NAME,
        embedding_function=embeddings,
    )

    if coleccion.count() > 0:
        logger.info("La base ya existe (%d chunks): no se vuelve a indexar", coleccion.count())
        return vectorstore

    chunks = trocear(cargar_documentos(data_dir))
    vectorstore.add_documents(chunks, ids=[_id_de(c) for c in chunks])
    logger.info("Indexados %d chunks en %s", len(chunks), chroma_dir)
    return vectorstore


if __name__ == "__main__":
    from providers import get_embeddings

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    vs = obtener_vectorstore(get_embeddings(), config.EMBEDDING_MODEL, reindex="--reindex" in sys.argv)
    print(f"Listo: {vs._collection.count()} chunks en '{config.CHROMA_DIR}'")
