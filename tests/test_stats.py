import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'stats.db'}")
    return TestClient(app)


def test_stats_on_empty_database_returns_zeros(client):
    data = client.get("/tickets/stats").json()
    assert data["total"] == 0
    assert data["by_priority"] == {"P1": 0, "P2": 0, "P3": 0}
    assert data["by_status"] == {"closed": 0, "in_progress": 0, "open": 0}
    assert set(data["by_category"]) == {"bug", "feature_request", "question", "urgent"}


def test_stats_counts_by_category_priority_and_status(client):
    db.create_ticket("a", "d", "bug", "P1", [])
    db.create_ticket("b", "d", "bug", "P2", [])
    db.create_ticket("c", "d", "question", "P3", [])
    ticket = db.create_ticket("d", "d", "urgent", "P1", [])
    db.update_ticket(ticket["id"], status="closed")

    data = client.get("/tickets/stats").json()

    assert data["total"] == 4
    assert data["by_category"] == {"bug": 2, "feature_request": 0, "question": 1, "urgent": 1}
    assert data["by_priority"] == {"P1": 2, "P2": 1, "P3": 1}
    assert data["by_status"] == {"closed": 1, "in_progress": 0, "open": 3}
