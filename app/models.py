"""Modelos de dominio / schemas Pydantic de TriageBot."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ALLOWED_CATEGORIES = {"bug", "feature_request", "question", "urgent"}
ALLOWED_PRIORITIES = {"P1", "P2", "P3"}
ALLOWED_STATUSES = {"open", "in_progress", "closed"}

Category = Literal["bug", "feature_request", "question", "urgent"]
Priority = Literal["P1", "P2", "P3"]
Status = Literal["open", "in_progress", "closed"]


class TicketCreate(BaseModel):
    """Payload de entrada de POST /tickets. Se aplica trim antes de validar longitudes."""

    model_config = {"str_strip_whitespace": True}

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=5000)


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
