"""Recuperación + generación: la cadena RAG con LCEL."""
import logging
from operator import itemgetter

from langchain_core.documents import Document
from langchain_core.exceptions import OutputParserException
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel, RunnablePassthrough
from langchain_core.vectorstores import VectorStore

import config
from schemas import NO_LO_SE, RAGResponse

logger = logging.getLogger("rag")

parser = PydanticOutputParser(pydantic_object=RAGResponse)

prompt = ChatPromptTemplate.from_messages([
    ("system",
     "Sos un asistente técnico de AgendaYa. Respondé SOLO con la información del CONTEXTO.\n"
     "Si la respuesta no está en el CONTEXTO, respondé exactamente '{no_lo_se}' y dejá las fuentes vacías.\n"
     "No uses conocimiento propio ni inventes datos.\n\n{format_instructions}"),
    ("human", "CONTEXTO:\n{contexto}\n\nPREGUNTA: {pregunta}"),
]).partial(no_lo_se=NO_LO_SE, format_instructions=parser.get_format_instructions())


def formatear_contexto(docs: list[Document]) -> str:
    """Une los chunks recuperados, cada uno con el nombre de su archivo."""
    return "\n\n---\n\n".join(f"[fuente: {d.metadata['source']}]\n{d.page_content}" for d in docs)


def construir_cadena(vectorstore: VectorStore, llm: Runnable) -> Runnable:
    """Pregunta → retriever (top_k chunks) → prompt → LLM → PydanticOutputParser."""
    retriever = vectorstore.as_retriever(search_kwargs={"k": config.TOP_K})

    generar = (
        RunnableLambda(lambda x: {"contexto": formatear_contexto(x["docs"]), "pregunta": x["pregunta"]})
        | prompt
        | llm
        | parser
    ).with_retry(retry_if_exception_type=(OutputParserException,), stop_after_attempt=2)

    return (
        RunnableParallel(docs=itemgetter("pregunta") | retriever, pregunta=itemgetter("pregunta"))
        | RunnablePassthrough.assign(respuesta=generar)
    )


async def get_rag_response(query: str, cadena: Runnable) -> RAGResponse:
    """Busca en ChromaDB, arma el prompt, llama al LLM de forma asíncrona y devuelve un RAGResponse."""
    logger.info("Pregunta: %s", query)
    resultado = await cadena.ainvoke({"pregunta": query})

    recuperadas = sorted({d.metadata["source"] for d in resultado["docs"]})
    logger.info("Chunks recuperados de: %s", ", ".join(recuperadas))

    respuesta: RAGResponse = resultado["respuesta"]
    # Las fuentes solo pueden ser archivos que de verdad se recuperaron (anti-alucinación)
    respuesta.fuentes = [f for f in dict.fromkeys(respuesta.fuentes) if f in recuperadas]
    if not respuesta.encontrada:
        respuesta.fuentes = []
    logger.info("Respuesta encontrada en el contexto: %s", "sí" if respuesta.encontrada else "no")
    return respuesta
