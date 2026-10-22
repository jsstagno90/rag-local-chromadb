import asyncio
import sys
from pathlib import Path

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import config  # noqa: E402
from ingest import EmbeddingsDistintosError, cargar_documentos, obtener_vectorstore, trocear  # noqa: E402
from offline import KeywordEmbeddings, extractive_llm  # noqa: E402
from rag import construir_cadena, get_rag_response  # noqa: E402
from schemas import NO_LO_SE  # noqa: E402

DATA = str(RAIZ / "data")


@pytest.fixture
def vectorstore(tmp_path):
    return obtener_vectorstore(KeywordEmbeddings(), "offline-keyword", chroma_dir=str(tmp_path), data_dir=DATA)


def preguntar(vs, llm, pregunta):
    return asyncio.run(get_rag_response(pregunta, construir_cadena(vs, llm)))


# ---------- Ingesta ----------

def test_lee_los_documentos_con_su_fuente():
    docs = cargar_documentos(DATA)
    assert len(docs) == 4
    assert {d.metadata["source"] for d in docs} == {"arquitectura.md", "pagos.md", "incidentes.md", "faq-soporte.md"}


def test_trocea_en_varios_chunks_con_su_fuente():
    chunks = trocear(cargar_documentos(DATA))
    assert len(chunks) > 4  # algún documento se partió en más de un chunk
    assert all("source" in c.metadata for c in chunks)


def test_no_reindexa_si_la_base_ya_existe(tmp_path):
    vs1 = obtener_vectorstore(KeywordEmbeddings(), "offline-keyword", chroma_dir=str(tmp_path), data_dir=DATA)
    total = vs1._collection.count()
    vs2 = obtener_vectorstore(KeywordEmbeddings(), "offline-keyword", chroma_dir=str(tmp_path), data_dir=DATA)
    assert vs2._collection.count() == total


def test_frena_si_cambia_el_modelo_de_embeddings(tmp_path):
    obtener_vectorstore(KeywordEmbeddings(), "offline-keyword", chroma_dir=str(tmp_path), data_dir=DATA)
    with pytest.raises(EmbeddingsDistintosError):
        obtener_vectorstore(KeywordEmbeddings(), "otro-modelo", chroma_dir=str(tmp_path), data_dir=DATA)


# ---------- Recuperación ----------

def test_recupera_como_maximo_top_k(vectorstore):
    docs = vectorstore.similarity_search("Redis caído", k=config.TOP_K)
    assert 1 <= len(docs) <= config.TOP_K


def test_el_chunk_mas_parecido_es_el_correcto(vectorstore):
    docs = vectorstore.similarity_search("reembolso de la seña de Mercado Pago", k=1)
    assert docs[0].metadata["source"] == "pagos.md"


# ---------- Generación ----------

def test_responde_con_fuente_si_esta_en_los_documentos(vectorstore):
    r = preguntar(vectorstore, extractive_llm, "¿Qué pasa con las reservas si Redis no responde?")
    assert r.encontrada
    assert "Redis" in r.respuesta
    assert r.fuentes == ["arquitectura.md"]


def test_pregunta_trampa_responde_no_lo_se(vectorstore):
    r = preguntar(vectorstore, extractive_llm, "¿Qué lenguaje se usa para programar la app de iOS?")
    assert r.respuesta == NO_LO_SE
    assert r.fuentes == []


def test_descarta_fuentes_inventadas_por_el_llm(vectorstore):
    llm = FakeListChatModel(responses=['{"respuesta": "Se reintenta.", "fuentes": ["pagos.md", "inventado.pdf"]}'])
    r = preguntar(vectorstore, llm, "¿Qué pasa si falla el webhook de Mercado Pago?")
    assert "inventado.pdf" not in r.fuentes


def test_reintenta_si_el_llm_devuelve_json_roto(vectorstore):
    llm = FakeListChatModel(responses=["esto no es JSON", '{"respuesta": "Hasta 10 días hábiles.", "fuentes": ["pagos.md"]}'])
    r = preguntar(vectorstore, llm, "¿Cuánto tarda un reembolso de la seña?")
    assert r.respuesta == "Hasta 10 días hábiles."
