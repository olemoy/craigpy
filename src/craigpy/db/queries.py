"""Database query functions — repo CRUD, file CRUD, merkle operations."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone


# --- Repositories ---


def create_repo(
    conn: sqlite3.Connection,
    name: str,
    path: str,
    collection_name: str,
) -> str:
    """Create a repository record. Returns the repo id."""
    repo_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO repositories (id, name, path, collection_name)
        VALUES (?, ?, ?, ?)
        """,
        (repo_id, name, path, collection_name),
    )
    conn.commit()
    return repo_id


def get_repo_by_name(conn: sqlite3.Connection, name: str) -> sqlite3.Row | None:
    """Look up a repository by name."""
    return conn.execute(
        "SELECT * FROM repositories WHERE name = ?", (name,)
    ).fetchone()


def get_repo_by_path(conn: sqlite3.Connection, path: str) -> sqlite3.Row | None:
    """Look up a repository by absolute path."""
    return conn.execute(
        "SELECT * FROM repositories WHERE path = ?", (path,)
    ).fetchone()


def list_repos(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """List all repositories."""
    return conn.execute(
        "SELECT * FROM repositories ORDER BY name"
    ).fetchall()


def update_repo_ingested_at(conn: sqlite3.Connection, repo_id: str) -> None:
    """Update the ingested_at timestamp for a repo."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE repositories SET ingested_at = ? WHERE id = ?",
        (now, repo_id),
    )
    conn.commit()


def delete_repo(conn: sqlite3.Connection, repo_id: str) -> None:
    """Delete a repository and all associated data (cascades)."""
    conn.execute("DELETE FROM repositories WHERE id = ?", (repo_id,))
    conn.commit()


# --- Files ---


def upsert_file(
    conn: sqlite3.Connection,
    repository_id: str,
    file_path: str,
    content_hash: str,
    size_bytes: int,
    language: str | None,
    chunk_count: int = 0,
    skipped: bool = False,
    last_modified: str | None = None,
) -> int:
    """Insert or update a file record. Returns the file id."""
    cursor = conn.execute(
        """
        INSERT INTO files (repository_id, file_path, content_hash, size_bytes,
                           language, chunk_count, skipped, last_modified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(repository_id, file_path) DO UPDATE SET
            content_hash = excluded.content_hash,
            size_bytes = excluded.size_bytes,
            language = excluded.language,
            chunk_count = excluded.chunk_count,
            skipped = excluded.skipped,
            last_modified = excluded.last_modified
        """,
        (
            repository_id,
            file_path,
            content_hash,
            size_bytes,
            language,
            chunk_count,
            1 if skipped else 0,
            last_modified,
        ),
    )
    conn.commit()
    return cursor.lastrowid or 0


def get_files_by_repo(
    conn: sqlite3.Connection,
    repository_id: str,
) -> list[sqlite3.Row]:
    """Get all files for a repository."""
    return conn.execute(
        "SELECT * FROM files WHERE repository_id = ? ORDER BY file_path",
        (repository_id,),
    ).fetchall()


def get_file(
    conn: sqlite3.Connection,
    repository_id: str,
    file_path: str,
) -> sqlite3.Row | None:
    """Get a single file by repo and path."""
    return conn.execute(
        "SELECT * FROM files WHERE repository_id = ? AND file_path = ?",
        (repository_id, file_path),
    ).fetchone()


def delete_files_by_paths(
    conn: sqlite3.Connection,
    repository_id: str,
    file_paths: list[str],
) -> int:
    """Delete file records by their paths. Returns count deleted."""
    if not file_paths:
        return 0
    placeholders = ",".join("?" for _ in file_paths)
    cursor = conn.execute(
        f"DELETE FROM files WHERE repository_id = ? AND file_path IN ({placeholders})",
        [repository_id, *file_paths],
    )
    conn.commit()
    return cursor.rowcount


def get_file_count(conn: sqlite3.Connection, repository_id: str) -> int:
    """Count files in a repository."""
    row = conn.execute(
        "SELECT COUNT(*) FROM files WHERE repository_id = ?",
        (repository_id,),
    ).fetchone()
    return row[0] if row else 0


# --- Merkle nodes ---


def upsert_merkle_node(
    conn: sqlite3.Connection,
    repository_id: str,
    node_path: str,
    node_hash: str,
    is_directory: bool,
) -> None:
    """Insert or update a merkle tree node."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO merkle_nodes (repository_id, node_path, node_hash, is_directory, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(repository_id, node_path) DO UPDATE SET
            node_hash = excluded.node_hash,
            is_directory = excluded.is_directory,
            updated_at = excluded.updated_at
        """,
        (repository_id, node_path, node_hash, 1 if is_directory else 0, now),
    )


def batch_upsert_merkle_nodes(
    conn: sqlite3.Connection,
    repository_id: str,
    nodes: list[tuple[str, str, bool]],
) -> None:
    """Batch upsert merkle nodes. Each tuple: (node_path, node_hash, is_directory)."""
    now = datetime.now(timezone.utc).isoformat()
    conn.executemany(
        """
        INSERT INTO merkle_nodes (repository_id, node_path, node_hash, is_directory, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(repository_id, node_path) DO UPDATE SET
            node_hash = excluded.node_hash,
            is_directory = excluded.is_directory,
            updated_at = excluded.updated_at
        """,
        [(repository_id, path, hash_, 1 if is_dir else 0, now) for path, hash_, is_dir in nodes],
    )
    conn.commit()


def get_merkle_nodes(
    conn: sqlite3.Connection,
    repository_id: str,
) -> list[sqlite3.Row]:
    """Get all merkle nodes for a repository."""
    return conn.execute(
        "SELECT * FROM merkle_nodes WHERE repository_id = ? ORDER BY node_path",
        (repository_id,),
    ).fetchall()


def get_merkle_node(
    conn: sqlite3.Connection,
    repository_id: str,
    node_path: str,
) -> sqlite3.Row | None:
    """Get a single merkle node."""
    return conn.execute(
        "SELECT * FROM merkle_nodes WHERE repository_id = ? AND node_path = ?",
        (repository_id, node_path),
    ).fetchone()


def delete_merkle_nodes_by_paths(
    conn: sqlite3.Connection,
    repository_id: str,
    node_paths: list[str],
) -> int:
    """Delete merkle nodes by path. Returns count deleted."""
    if not node_paths:
        return 0
    placeholders = ",".join("?" for _ in node_paths)
    cursor = conn.execute(
        f"DELETE FROM merkle_nodes WHERE repository_id = ? AND node_path IN ({placeholders})",
        [repository_id, *node_paths],
    )
    conn.commit()
    return cursor.rowcount


def clear_merkle_tree(conn: sqlite3.Connection, repository_id: str) -> None:
    """Remove all merkle nodes for a repository."""
    conn.execute(
        "DELETE FROM merkle_nodes WHERE repository_id = ?",
        (repository_id,),
    )
    conn.commit()
