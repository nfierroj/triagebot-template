import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(
        "app.classifier.classify_ticket",
        lambda title, description: {"category": "bug", "priority": "P1", "tags": ["login"]},
    )
    return TestClient(app)


def test_index_renders_form_filters_and_board(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert 'hx-post="/tickets"' in html
    assert 'name="title"' in html
    assert 'name="description"' in html
    assert "Crear ticket" in html
    assert 'hx-get="/partials/tickets"' in html


def test_table_fragment_lists_and_filters_tickets(client):
    client.post("/tickets", json={"title": "<b>Hola</b>", "description": "Desc"})

    fragment = client.get("/partials/tickets")
    assert fragment.status_code == 200
    assert "&lt;b&gt;Hola&lt;/b&gt;" in fragment.text  # escapado, sin XSS
    assert "login" in fragment.text

    empty = client.get("/partials/tickets", params={"category": "question"})
    assert "No hay tickets que mostrar." in empty.text

    # Un filtro vacío (opción «Todas») no filtra
    all_tickets = client.get("/partials/tickets", params={"category": "", "status": ""})
    assert "login" in all_tickets.text
