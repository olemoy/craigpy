"""Differ — compare stored merkle tree vs current to produce a changeset."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from craigpy.db import queries


@dataclass
class Changeset:
    """Result of comparing stored vs current file state."""

    added: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.modified or self.deleted)

    @property
    def total(self) -> int:
        return len(self.added) + len(self.modified) + len(self.deleted)


def compute_changeset(
    conn: sqlite3.Connection,
    repository_id: str,
    current_file_hashes: dict[str, str],
) -> Changeset:
    """Compare current file hashes against stored merkle state.

    Args:
        conn: Database connection.
        repository_id: The repository to compare against.
        current_file_hashes: Mapping of relative file paths → SHA-256 hashes
                             for the current state on disk.

    Returns:
        Changeset with added, modified, and deleted file paths.
    """
    changeset = Changeset()

    # Get stored file nodes (non-directory only)
    stored_nodes = queries.get_merkle_nodes(conn, repository_id)
    stored_files: dict[str, str] = {
        row["node_path"]: row["node_hash"]
        for row in stored_nodes
        if not row["is_directory"]
    }

    # Find added and modified files
    for file_path, current_hash in current_file_hashes.items():
        if file_path not in stored_files:
            changeset.added.append(file_path)
        elif stored_files[file_path] != current_hash:
            changeset.modified.append(file_path)

    # Find deleted files
    for file_path in stored_files:
        if file_path not in current_file_hashes:
            changeset.deleted.append(file_path)

    # Sort for deterministic output
    changeset.added.sort()
    changeset.modified.sort()
    changeset.deleted.sort()

    return changeset
