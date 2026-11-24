"""FastAPI app y endpoints HTTP de TriageBot."""

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import classifier, db
from app.models import (
    ALLOWED_CATEGORIES,
    ALLOWED_PRIORITIES,
    ALLOWED_STATUSES,
    Ticket,
    TicketCreate,
    TicketUpdate,
)

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
DEFAULT_PAGE_SIZE = 10
PAGE_SIZE_OPTIONS = (5, 10, 25, 50, 100)

app = FastAPI(title="TriageBot")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _safe_classify(title: str, description: str) -> dict:
    """Clasifica el ticket; ante cualquier fallo o salida inválida devuelve el fallback."""
    try:
        # Se accede vía módulo (no `from ... import`) para que sea parcheable en tests.
        result = classifier.classify_ticket(title, description)
        tags = result["tags"]
        if (
            result["category"] in ALLOWED_CATEGORIES
            and result["priority"] in ALLOWED_PRIORITIES
            and isinstance(tags, list)
            and all(isinstance(tag, str) for tag in tags)
        ):
            return {
                "category": result["category"],
                "priority": result["priority"],
                "tags": tags,
            }
        logger.warning("Clasificación inválida, se aplica fallback: %r", result)
    except Exception:
        logger.exception("Fallo del clasificador, se aplica fallback")
    return dict(classifier.FALLBACK_CLASSIFICATION)


@app.post("/tickets", response_model=Ticket, status_code=201)
def create_ticket(payload: TicketCreate) -> dict:
    classification = _safe_classify(payload.title, payload.description)
    return db.create_ticket(
        title=payload.title,
        description=payload.description,
        category=classification["category"],
        priority=classification["priority"],
        tags=classification["tags"],
    )


def _validated_filter(name: str, value: str | None, allowed: set[str]) -> str | None:
    """Normaliza un filtro de query: vacío o ausente = sin filtrar; fuera del enum = 422."""
    if value is None or value == "":
        return None
    if value not in allowed:
        raise HTTPException(status_code=422, detail=f"Valor no válido para '{name}': {value!r}")
    return value


def _filtered_tickets(
    category: str | None, priority: str | None, status: str | None, limit: int | None = None
) -> list[dict]:
    return db.list_tickets(
        category=_validated_filter("category", category, ALLOWED_CATEGORIES),
        priority=_validated_filter("priority", priority, ALLOWED_PRIORITIES),
        status=_validated_filter("status", status, ALLOWED_STATUSES),
        limit=limit,
    )


@app.get("/tickets", response_model=list[Ticket])
def list_tickets(
    category: str | None = None, priority: str | None = None, status: str | None = None
) -> list[dict]:
    return _filtered_tickets(category, priority, status)


def _table_context(
    request: Request,
    category: str | None,
    priority: str | None,
    status: str | None,
    limit: int,
) -> dict:
    tickets = _filtered_tickets(category, priority, status, limit)
    return {"request": request, "tickets": [Ticket(**ticket) for ticket in tickets]}


@app.get("/tickets/table", response_class=HTMLResponse)
def tickets_table(
    request: Request,
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=100),
) -> HTMLResponse:
    """Fragmento HTML de la tabla (lo pide HTMX al cambiar un filtro o el nº de filas)."""
    context = _table_context(request, category, priority, status, limit)
    return templates.TemplateResponse(request, "_tickets_table.html", context)


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    context = _table_context(request, None, None, None, DEFAULT_PAGE_SIZE)
    context.update(
        categories=sorted(ALLOWED_CATEGORIES),
        priorities=sorted(ALLOWED_PRIORITIES),
        statuses=["open", "in_progress", "closed"],
        page_size_options=PAGE_SIZE_OPTIONS,
        default_page_size=DEFAULT_PAGE_SIZE,
    )
    return templates.TemplateResponse(request, "index.html", context)


@app.patch("/tickets/{ticket_id}", response_model=Ticket)
def update_ticket(ticket_id: int, payload: TicketUpdate) -> dict:
    ticket = db.update_ticket(ticket_id, status=payload.status, priority=payload.priority)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket
