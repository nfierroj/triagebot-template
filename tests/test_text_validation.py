"""Título y descripción solo admiten caracteres latinos: sin emojis ni otros alfabetos."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'text.db'}")
    monkeypatch.setattr(
        "app.classifier.classify_ticket",
        lambda title, description: {"category": "bug", "priority": "P1", "tags": []},
    )
    return TestClient(app)


@pytest.mark.parametrize(
    "text",
    [
        "La app no carga",
        "¿Cómo cambio la contraseña? ¡Urgente!",
        "Pingüino, cigüeña, ñandú, façade, Ærøskøbing",
        "Comillas «así», “así” y ‘así’ — con guiones – y puntos…",
        "Precio: 10 € (aprox.) 50% @usuario #123",
        "Línea 1\nLínea 2\tcon tabulador",
    ],
)
def test_latin_text_is_accepted(client, text):
    response = client.post("/tickets", json={"title": text[:200], "description": text})
    assert response.status_code == 201, response.json()


@pytest.mark.parametrize(
    "text",
    [
        "La app no carga 😀",
        "Fallo 👍🏽",
        "Bandera 🇪🇸",
        "❤️ me encanta",
        "Ошибка входа",  # cirílico
        "登录失败",  # chino
        "خطأ",  # árabe
        "Ελληνικά",  # griego
        "aprox ≈ 3",  # símbolo matemático
        "texto​invisible",  # espacio de ancho cero
    ],
)
@pytest.mark.parametrize("field", ["title", "description"])
def test_emojis_and_non_latin_text_are_rejected(client, text, field):
    payload = {"title": "Título válido", "description": "Descripción válida", field: text}
    response = client.post("/tickets", json=payload)

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["loc"][-1] == field
    assert "Solo se admiten caracteres latinos" in error["msg"]


def test_decomposed_accents_are_normalized_and_accepted(client):
    # «e» + tilde combinada (U+0301), como envían algunos teclados de macOS.
    response = client.post("/tickets", json={"title": "Café", "description": "ok"})
    assert response.status_code == 201
    assert response.json()["title"] == "Café"


def test_rejected_ticket_is_not_persisted(client):
    client.post("/tickets", json={"title": "Hola 😀", "description": "x"})
    assert client.get("/tickets").json() == []
