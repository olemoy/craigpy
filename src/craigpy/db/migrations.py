"""SQLite schema migrations — idempotent, versioned."""

from __future__ import annotations

import sqlite3

MIGRATIONS: list[tuple[int, str, str]] = [
    (
        1,
        "Create schema_version table",
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """,
    ),
    (
        2,
        "Create repositories table",
        """
        CREATE TABLE IF NOT EXISTS repositories (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            path TEXT NOT NULL,
            collection_name TEXT NOT NULL,
            ingested_at TEXT
        );
        """,
    ),
    (
        3,
        "Create files table",
        """
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repository_id TEXT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
            file_path TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            language TEXT,
            chunk_count INTEGER NOT NULL DEFAULT 0,
            skipped INTEGER NOT NULL DEFAULT 0,
            last_modified TEXT,
            UNIQUE(repository_id, file_path)
        );
        CREATE INDEX IF NOT EXISTS idx_files_repo ON files(repository_id);
        CREATE INDEX IF NOT EXISTS idx_files_path ON files(repository_id, file_path);
        """,
    ),
    (
        4,
        "Create merkle_nodes table",
        """
        CREATE TABLE IF NOT EXISTS merkle_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repository_id TEXT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
            node_path TEXT NOT NULL,
            node_hash TEXT NOT NULL,
            is_directory INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(repository_id, node_path)
        );
        CREATE INDEX IF NOT EXISTS idx_merkle_repo ON merkle_nodes(repository_id);
        CREATE INDEX IF NOT EXISTS idx_merkle_path ON merkle_nodes(repository_id, node_path);
        """,
    ),
]


def get_current_version(conn: sqlite3.Connection) -> int:
    """Get the current schema version, 0 if no migrations applied."""
    try:
        row = conn.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()
        return row[0] or 0
    except sqlite3.OperationalError:
        return 0


def run_migrations(conn: sqlite3.Connection) -> None:
    """Apply all pending migrations."""
    current = get_current_version(conn)

    for version, _description, sql in MIGRATIONS:
        if version <= current:
            continue

        conn.executescript(sql)
        conn.execute(
            "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
            (version,),
        )
        conn.commit()
