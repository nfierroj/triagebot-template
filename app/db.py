"""Persistencia en SQLite con sqlite3."""

import json
import os
import sqlite3
from datetime import UTC, datetime

DEFAULT_DATABASE_URL = "sqlite:///triagebot.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    description TEXT NOT NULL,
    category    TEXT NOT NULL,
    priority    TEXT NOT NULL,
    tags        TEXT NOT NULL DEFAULT '[]',
    status      TEXT NOT NULL DEFAULT 'open',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
)
"""


def get_db_path() -> str:
    """Ruta del fichero SQLite a partir de DATABASE_URL (se lee en cada llamada)."""
    url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    prefix = "sqlite:///"
    return url[len(prefix):] if url.startswith(prefix) else url


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["tags"] = json.loads(data["tags"])
    return data


def create_ticket(
    title: str, description: str, category: str, priority: str, tags: list[str]
) -> dict:
    """Inserta un ticket con status 'open' y devuelve el registro guardado."""
    now = datetime.now(UTC).isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tickets
                (title, description, category, priority, tags, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'open', ?, ?)
            """,
            (title, description, category, priority, json.dumps(tags), now, now),
        )
        row = conn.execute(
            "SELECT * FROM tickets WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    conn.close()
    return _row_to_dict(row)
