"""SQLite persistence for diary entries - one row per calendar day."""

import sqlite3

from config import DIARY_DB_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DIARY_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS diary_entries (
                date TEXT PRIMARY KEY,
                draft TEXT NOT NULL,
                corrected TEXT NOT NULL,
                explanation TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )


def save_entry(date: str, draft: str, corrected: str, explanation: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO diary_entries (date, draft, corrected, explanation, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(date) DO UPDATE SET
                draft = excluded.draft,
                corrected = excluded.corrected,
                explanation = excluded.explanation,
                updated_at = excluded.updated_at
            """,
            (date, draft, corrected, explanation),
        )


def get_entry(date: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT date, draft, corrected, explanation FROM diary_entries WHERE date = ?",
            (date,),
        ).fetchone()
    return dict(row) if row else None


def list_dates() -> list:
    with _connect() as conn:
        rows = conn.execute("SELECT date FROM diary_entries ORDER BY date").fetchall()
    return [row["date"] for row in rows]
