"""FastAPI app y endpoints HTTP de TriageBot."""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import classifier, db
from app.models import (
    ALLOWED_CATEGORIES,
    ALLOWED_PRIORITIES,
    Ticket,
    TicketCreate,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="TriageBot")
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")


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


@app.get("/tickets", response_model=list[Ticket])
def list_tickets(
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
) -> list[dict]:
    return db.list_tickets(category, priority, status)


@app.get("/partials/tickets", response_class=HTMLResponse)
def tickets_table(
    request: Request,
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
) -> HTMLResponse:
    """Fragmento HTML con la tabla de tickets (lo pide HTMX)."""
    return templates.TemplateResponse(
        request,
        "_tickets_table.html",
        {"tickets": db.list_tickets(category, priority, status)},
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", {})


# TODO: implementar PATCH /tickets/{ticket_id}
