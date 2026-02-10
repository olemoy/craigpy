"""Merkle tree — SHA-256 per file, directory hash rollup."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path


def hash_file(file_path: Path) -> str:
    """Compute SHA-256 hash of a file's contents."""
    h = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def hash_content(content: str) -> str:
    """Compute SHA-256 hash of a string."""
    return hashlib.sha256(content.encode()).hexdigest()


def build_merkle_tree(
    file_hashes: dict[str, str],
) -> dict[str, tuple[str, bool]]:
    """Build a merkle tree from file hashes.

    Args:
        file_hashes: Mapping of relative file paths to their SHA-256 hashes.

    Returns:
        Mapping of node_path → (node_hash, is_directory) for every file and
        every directory up to the root.
    """
    nodes: dict[str, tuple[str, bool]] = {}

    # Add leaf nodes (files)
    for file_path, file_hash in file_hashes.items():
        nodes[file_path] = (file_hash, False)

    # Collect all directory paths
    dir_children: dict[str, list[str]] = defaultdict(list)
    for file_path in file_hashes:
        parts = Path(file_path).parts
        # Register each file/dir under its parent
        for i in range(len(parts)):
            child = str(Path(*parts[: i + 1]))
            parent = str(Path(*parts[:i])) if i > 0 else "."
            if child not in dir_children[parent]:
                dir_children[parent].append(child)

    # Compute directory hashes bottom-up
    # Sort by depth (deepest first) to ensure children are computed before parents
    all_dirs = sorted(dir_children.keys(), key=lambda d: -d.count("/") if d != "." else 1)

    for dir_path in all_dirs:
        children = sorted(dir_children[dir_path])
        child_hashes: list[str] = []
        for child in children:
            if child in nodes:
                child_hashes.append(nodes[child][0])
            # If child isn't in nodes yet, it's a dir that will be computed
        if child_hashes:
            combined = "|".join(child_hashes)
            dir_hash = hashlib.sha256(combined.encode()).hexdigest()
            nodes[dir_path] = (dir_hash, True)

    return nodes
