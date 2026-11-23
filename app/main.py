from fastapi import FastAPI

from app import classifier, db
from app.models import (
    ALLOWED_CATEGORIES,
    ALLOWED_PRIORITIES,
    Ticket,
    TicketCreate,
)

app = FastAPI(title="TriageBot")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _safe_classify(title: str, description: str) -> dict:
    """Llama al clasificador y garantiza una salida válida; nunca propaga excepciones."""
    fallback = dict(classifier.FALLBACK_CLASSIFICATION, tags=[])
    try:
        result = classifier.classify_ticket(title, description)
    except Exception:
        return fallback

    if not isinstance(result, dict):
        return fallback
    category = result.get("category")
    priority = result.get("priority")
    tags = result.get("tags")
    if (
        category not in ALLOWED_CATEGORIES
        or priority not in ALLOWED_PRIORITIES
        or not isinstance(tags, list)
        or not all(isinstance(tag, str) for tag in tags)
    ):
        return fallback
    return {"category": category, "priority": priority, "tags": tags}


@app.post("/tickets", response_model=Ticket, status_code=201)
def create_ticket(payload: TicketCreate) -> dict:
    classification = _safe_classify(payload.title, payload.description)
    return db.create_ticket(
        title=payload.title,
        description=payload.description,
        **classification,
    )


# TODO: pendientes
# - GET /tickets
# - PATCH /tickets/{ticket_id}
# - GET /
