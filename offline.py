"""Piezas para el modo demo y los tests: funcionan sin internet y sin API keys.

- KeywordEmbeddings: embeddings simples basados en palabras (no entienden sinónimos, pero alcanzan para probar).
- extractive_llm: un "LLM" falso que copia la oración del contexto más parecida a la pregunta,
  o responde "No lo sé" si ningún fragmento tiene que ver.
"""
import hashlib
import json
import math
import re
import unicodedata

from langchain_core.embeddings import Embeddings
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from schemas import NO_LO_SE

DIMENSIONES = 512
STOPWORDS = {
    "que", "qué", "para", "como", "cómo", "cual", "cuál", "cuanto", "cuánto", "esta", "este", "esto",
    "una", "uno", "los", "las", "del", "con", "por", "sin", "son", "hay", "pasa", "puedo", "tiene",
    "cuando", "cuándo", "donde", "dónde", "sobre", "entre", "desde", "hasta", "más", "mas",
}


def palabras(texto: str) -> list[str]:
    sin_tildes = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    return [p for p in re.findall(r"[a-z0-9_]+", sin_tildes) if len(p) >= 4 and p not in STOPWORDS]


class KeywordEmbeddings(Embeddings):
    """Cada palabra suma 1 en una posición fija del vector; después se normaliza."""

    def _vector(self, texto: str) -> list[float]:
        v = [0.0] * DIMENSIONES
        for p in palabras(texto):
            v[int(hashlib.md5(p.encode()).hexdigest(), 16) % DIMENSIONES] += 1.0
        norma = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norma for x in v]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


def _responder(prompt_value) -> AIMessage:
    humano = prompt_value.to_messages()[-1].content
    contexto, pregunta = humano.split("PREGUNTA:", 1)
    clave = set(palabras(pregunta))

    # 1. El fragmento que comparte más palabras con la pregunta
    mejor_bloque, mejor_fuente, puntaje = "", "", 0
    for bloque in contexto.split("\n\n---\n\n"):
        fuente = re.search(r"\[fuente: ([^\]]+)\]", bloque)
        coincidencias = len(clave & set(palabras(bloque)))
        if fuente and coincidencias > puntaje:
            mejor_bloque, mejor_fuente, puntaje = bloque, fuente.group(1), coincidencias

    # 2. Menos de 2 palabras en común = el contexto no habla de eso
    if puntaje < 2:
        return AIMessage(content=json.dumps({"respuesta": NO_LO_SE, "fuentes": []}, ensure_ascii=False))

    # 3. Copia la oración más parecida y la siguiente
    oraciones = [o.strip(" -*") for o in re.split(r"(?<=[.!?])\s+|\n+", mejor_bloque) if o.strip(" -*") and not o.lstrip().startswith("#")]
    i = max(range(len(oraciones)), key=lambda k: len(clave & set(palabras(oraciones[k]))))
    respuesta = " ".join(oraciones[i:i + 2])
    return AIMessage(content=json.dumps({"respuesta": respuesta, "fuentes": [mejor_fuente]}, ensure_ascii=False))


extractive_llm = RunnableLambda(_responder)
