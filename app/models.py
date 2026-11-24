"""Modelos de dominio / schemas Pydantic de TriageBot."""

import unicodedata
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ALLOWED_CATEGORIES = {"bug", "feature_request", "question", "urgent"}
ALLOWED_PRIORITIES = {"P1", "P2", "P3"}
ALLOWED_STATUSES = {"open", "in_progress", "closed"}

Category = Literal["bug", "feature_request", "question", "urgent"]
Priority = Literal["P1", "P2", "P3"]
Status = Literal["open", "in_progress", "closed"]

# Caracteres admitidos en título y descripción: alfabeto latino (con tildes, ñ, ç…),
# dígitos, puntuación habitual y saltos de línea. Todo lo demás (emojis, otros alfabetos,
# caracteres invisibles o de control) se rechaza con 422.
ALLOWED_TEXT_RANGES = (
    (0x0020, 0x007E),  # ASCII imprimible
    (0x00A0, 0x024F),  # Latin-1 Supplement + Latin Extended-A/B (á, ñ, ü, ç, ¿, ¡, «, »…)
    (0x1E00, 0x1EFF),  # Latin Extended Additional
    (0x2010, 0x2027),  # Guiones, comillas tipográficas, puntos suspensivos, viñetas
    (0x2030, 0x205E),  # Más puntuación (‰, ′, ″, ‹, ›…)
    (0x20AC, 0x20AC),  # €
)
ALLOWED_TEXT_CONTROLS = {"\t", "\n", "\r"}


def _first_disallowed_char(text: str) -> str | None:
    for char in text:
        if char in ALLOWED_TEXT_CONTROLS:
            continue
        code = ord(char)
        if not any(low <= code <= high for low, high in ALLOWED_TEXT_RANGES):
            return char
    return None


class TicketCreate(BaseModel):
    """Payload de entrada de POST /tickets. Se aplica trim antes de validar longitudes."""

    model_config = {"str_strip_whitespace": True}

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=5000)

    @field_validator("title", "description")
    @classmethod
    def only_latin_text(cls, value: str) -> str:
        # NFC une letra + tilde combinada (p. ej. «e» + «´») en un único carácter «é».
        value = unicodedata.normalize("NFC", value)
        char = _first_disallowed_char(value)
        if char is not None:
            raise ValueError(
                "Solo se admiten caracteres latinos: no se permiten emojis ni otros "
                f"alfabetos (carácter no válido: {char!r}, U+{ord(char):04X})"
            )
        return value


class TicketUpdate(BaseModel):
    """Payload de PATCH /tickets/{id}: solo se pueden cambiar status y priority."""

    status: Status | None = None
    priority: Priority | None = None


class Ticket(BaseModel):
    """Ticket completo tal como se devuelve por la API."""

    id: int
    title: str
    description: str
    category: Category
    priority: Priority
    tags: list[str]
    status: Status
    created_at: datetime
    updated_at: datetime
