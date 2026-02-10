"""SQLite database client — singleton connection for metadata + merkle state."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from craigpy.db.migrations import run_migrations

_connection: sqlite3.Connection | None = None


def get_connection(db_path: Path) -> sqlite3.Connection:
    """Get or create the singleton SQLite connection."""
    global _connection
    if _connection is not None:
        return _connection

    db_path.parent.mkdir(parents=True, exist_ok=True)
    _connection = sqlite3.connect(str(db_path))
    _connection.row_factory = sqlite3.Row
    _connection.execute("PRAGMA journal_mode=WAL")
    _connection.execute("PRAGMA foreign_keys=ON")

    run_migrations(_connection)
    return _connection


def close_connection() -> None:
    """Close the singleton connection."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
