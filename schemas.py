from pydantic import BaseModel, Field

NO_LO_SE = "No lo sé"


class RAGResponse(BaseModel):
    """Respuesta final del sistema: el texto y de qué archivos salió."""

    respuesta: str = Field(
        description=f"La respuesta, basada SOLO en el contexto. Si no está en el contexto: exactamente '{NO_LO_SE}'"
    )
    fuentes: list[str] = Field(
        default_factory=list,
        description="Nombres de los archivos del contexto usados para responder (ej: 'pagos.md'). Vacía si no se sabe",
    )

    @property
    def encontrada(self) -> bool:
        return NO_LO_SE.lower() not in self.respuesta.lower()
