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


def list_tickets(
    category: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Lista tickets (más recientes primero), filtrando por los campos que no sean None."""
    clauses: list[str] = []
    params: list[str | int] = []
    for column, value in (("category", category), ("priority", priority), ("status", status)):
        if value is not None:
            clauses.append(f"{column} = ?")
            params.append(value)

    query = "SELECT * FROM tickets"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC, id DESC"
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    conn = get_connection()
    try:
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()
    return [_row_to_dict(row) for row in rows]


def update_ticket(
    ticket_id: int, status: str | None = None, priority: str | None = None
) -> dict | None:
    """Actualiza status y/o priority. Devuelve el ticket, o None si no existe."""
    changes = {"status": status, "priority": priority}
    changes = {column: value for column, value in changes.items() if value is not None}
    conn = get_connection()
    try:
        with conn:
            if changes:
                assignments = ", ".join(f"{column} = ?" for column in changes)
                conn.execute(
                    f"UPDATE tickets SET {assignments}, updated_at = ? WHERE id = ?",
                    [*changes.values(), datetime.now(UTC).isoformat(), ticket_id],
                )
            row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    finally:
        conn.close()
    return _row_to_dict(row) if row else None
