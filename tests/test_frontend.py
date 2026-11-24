"""Tests del frontend HTML + HTMX (bloque 1: formulario de creación)."""

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


def test_index_renders_create_form_with_htmx(client):
    html = client.get("/").text

    assert 'hx-post="/tickets"' in html
    assert 'hx-ext="json-enc"' in html
    assert 'name="title"' in html
    assert "<textarea" in html and 'name="description"' in html
    assert "Crear ticket" in html


def test_table_refreshes_after_ticket_created_keeping_filters(client):
    html = client.get("/").text

    assert 'hx-trigger="ticket-created from:body"' in html
    assert 'hx-include="#filters"' in html


def test_ticket_created_from_form_appears_in_table_partial(client):
    created = client.post("/tickets", json={"title": "Login roto", "description": "No entra"})
    assert created.status_code == 201

    partial = client.get("/tickets/table")

    assert partial.status_code == 200
    assert "<html" not in partial.text
    assert "Login roto" in partial.text


def test_table_partial_escapes_html(client):
    client.post("/tickets", json={"title": "<script>alert(1)</script>", "description": "x"})

    partial = client.get("/tickets/table")

    assert "<script>alert(1)</script>" not in partial.text
    assert "&lt;script&gt;" in partial.text
