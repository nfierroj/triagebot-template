import re

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'table.db'}")
    return TestClient(app)


def seed(count, category="bug", priority="P1", tags=None):
    for i in range(count):
        db.create_ticket(f"Ticket {category} {i}", "desc", category, priority, tags or [])


def body_rows(html):
    tbody = html.split('<tbody id="tickets-table-body">')[1]
    return re.findall(r'<tr class="([^"]*)">', tbody)


def test_get_tickets_filters_by_category_priority_and_status(client):
    seed(2, category="bug", priority="P1")
    seed(1, category="question", priority="P3")

    assert len(client.get("/tickets").json()) == 3
    assert len(client.get("/tickets", params={"category": "bug"}).json()) == 2
    assert len(client.get("/tickets", params={"priority": "P3"}).json()) == 1
    assert client.get("/tickets", params={"status": "closed"}).json() == []


def test_get_tickets_rejects_values_outside_the_enum(client):
    assert client.get("/tickets", params={"category": "URGENT"}).status_code == 422


def test_table_has_requested_columns_in_order(client):
    html = client.get("/tickets/table").text
    headers = re.findall(r"<th[^>]*>([^<]+)</th>", html)
    assert headers == ["Prioridad", "Título", "Categoría", "Etiquetas", "Estado", "Creado"]


def test_table_shows_10_rows_by_default_and_limit_is_selectable(client):
    seed(30)
    assert len(body_rows(client.get("/tickets/table").text)) == 10
    assert len(body_rows(client.get("/tickets/table", params={"limit": 25}).text)) == 25
    assert client.get("/tickets/table", params={"limit": 0}).status_code == 422


def test_odd_rows_are_light_red_and_even_rows_white(client):
    seed(4)
    classes = body_rows(client.get("/tickets/table").text)
    assert classes == ["bg-red-100", "bg-white", "bg-red-100", "bg-white"]


def test_priority_badge_tags_and_empty_filter_values(client):
    seed(1, priority="P2", tags=["login", "vpn"])
    html = client.get(
        "/tickets/table", params={"category": "", "priority": "", "status": "", "limit": 10}
    ).text
    assert "bg-orange-500" in html and ">P2</span>" in html
    assert ">login</span>" in html and ">vpn</span>" in html


def test_table_respects_filters_and_shows_empty_state(client):
    seed(2, category="bug")
    assert len(body_rows(client.get("/tickets/table", params={"category": "bug"}).text)) == 2
    assert "No hay tickets" in client.get("/tickets/table", params={"category": "urgent"}).text


def test_index_renders_table_and_row_selector(client):
    seed(12)
    response = client.get("/")
    assert response.status_code == 200
    assert 'name="limit"' in response.text
    assert len(body_rows(response.text)) == 10


def test_patch_updates_ticket_and_validates(client):
    ticket = db.create_ticket("Fallo", "desc", "bug", "P1", [])

    ok = client.patch(f"/tickets/{ticket['id']}", json={"status": "closed"})
    assert ok.status_code == 200
    assert ok.json()["status"] == "closed" and ok.json()["priority"] == "P1"

    assert client.patch("/tickets/999", json={"status": "closed"}).status_code == 404
    assert client.patch(f"/tickets/{ticket['id']}", json={"status": "done"}).status_code == 422
    assert client.patch(f"/tickets/{ticket['id']}", json={"priority": "P9"}).status_code == 422


def test_priority_badge_colors(client):
    for priority in ("P1", "P2", "P3"):
        seed(1, priority=priority)
    html = client.get("/tickets/table").text
    assert 'bg-red-600 text-white">P1</span>' in html
    assert 'bg-orange-500 text-white">P2</span>' in html
    assert 'bg-green-600 text-white">P3</span>' in html


def test_tickets_sorted_by_priority_then_newest_first(client):
    seed(1, category="question", priority="P3")
    seed(1, category="bug", priority="P1")
    seed(1, category="urgent", priority="P2")
    seed(1, category="feature_request", priority="P1")

    tickets = client.get("/tickets").json()
    assert [t["priority"] for t in tickets] == ["P1", "P1", "P2", "P3"]
    # Dentro de P1, el más reciente primero.
    assert [t["category"] for t in tickets[:2]] == ["feature_request", "bug"]

    html = client.get("/tickets/table").text
    assert re.findall(r">(P[123])</span>", html) == ["P1", "P1", "P2", "P3"]
