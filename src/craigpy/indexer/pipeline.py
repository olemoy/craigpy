"""Ingest pipeline — diff → filter → chunk → upsert to ChromaDB."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import chromadb

from craigpy.chunking import chunk_file
from craigpy.chunking.interface import Chunk
from craigpy.config.settings import RepoConfig, Settings
from craigpy.db import queries
from craigpy.indexer.differ import Changeset, compute_changeset
from craigpy.indexer.file_filter import FileWalker, get_language
from craigpy.indexer.merkle import build_merkle_tree, hash_file


def _slugify(name: str) -> str:
    """Convert a repo name to a valid ChromaDB collection name."""
    # ChromaDB collection names: 3-63 chars, alphanumeric + underscores/hyphens
    slug = name.lower().replace(" ", "-").replace("/", "-").replace(".", "-")
    # Strip invalid chars
    slug = "".join(c for c in slug if c.isalnum() or c in "-_")
    # Ensure 3+ chars
    while len(slug) < 3:
        slug += "_"
    return slug[:63]


def _get_chroma_client(settings: Settings) -> chromadb.PersistentClient:
    """Get ChromaDB persistent client."""
    return chromadb.PersistentClient(path=str(settings.chroma_path))


def _upsert_chunks_to_chroma(
    collection: chromadb.Collection,
    chunks: list[Chunk],
    file_path: str,
    repo_path: str,
) -> int:
    """Upsert chunks into a ChromaDB collection. Returns count upserted."""
    if not chunks:
        return 0

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for chunk in chunks:
        ids.append(chunk.chunk_hash)
        documents.append(chunk.content)
        meta: dict = {
            "file_path": file_path,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "chunk_index": chunk.chunk_index,
        }
        if chunk.language:
            meta["language"] = chunk.language
        if chunk.symbol_name:
            meta["symbol_name"] = chunk.symbol_name
        if chunk.symbol_type:
            meta["symbol_type"] = chunk.symbol_type
        metadatas.append(meta)

    # Batch upsert (ChromaDB handles embedding)
    BATCH_SIZE = 500
    for i in range(0, len(ids), BATCH_SIZE):
        collection.upsert(
            ids=ids[i : i + BATCH_SIZE],
            documents=documents[i : i + BATCH_SIZE],
            metadatas=metadatas[i : i + BATCH_SIZE],
        )

    return len(ids)


def _delete_file_chunks_from_chroma(
    collection: chromadb.Collection,
    file_path: str,
) -> None:
    """Remove all chunks for a file from ChromaDB."""
    # Query for all chunks belonging to this file, then delete by IDs
    results = collection.get(
        where={"file_path": file_path},
        include=[],
    )
    if results["ids"]:
        collection.delete(ids=results["ids"])


def ingest_repo(
    conn: sqlite3.Connection,
    settings: Settings,
    repo_path: Path,
    name: str | None = None,
    force: bool = False,
    on_progress: callable | None = None,
) -> dict:
    """Ingest a repository — full or incremental.

    Args:
        conn: SQLite connection.
        settings: Application settings.
        repo_path: Absolute path to the repository.
        name: Optional repo name (defaults to directory name).
        force: If True, re-index all files regardless of changes.
        on_progress: Optional callback(message: str) for progress updates.

    Returns:
        Summary dict with counts.
    """
    repo_path = repo_path.resolve()
    if not repo_path.is_dir():
        raise ValueError(f"Not a directory: {repo_path}")

    repo_name = name or repo_path.name
    collection_name = _slugify(repo_name)

    def log(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    # Get or create repo record
    repo = queries.get_repo_by_name(conn, repo_name)
    if repo is None:
        repo_id = queries.create_repo(conn, repo_name, str(repo_path), collection_name)
        log(f"Created repository '{repo_name}'")
    else:
        repo_id = repo["id"]
        collection_name = repo["collection_name"]

    # Get repo-specific config
    repo_config = settings.get_repo_config(str(repo_path))

    # Walk the file tree
    log("Scanning files...")
    walker = FileWalker(repo_path, repo_config)
    indexable_files = walker.walk()

    if walker.skipped_files:
        log(f"Skipped {len(walker.skipped_files)} files")

    # Compute file hashes
    log("Computing file hashes...")
    file_hashes: dict[str, str] = {}
    for file_path_abs in indexable_files:
        rel_path = str(file_path_abs.relative_to(repo_path))
        file_hashes[rel_path] = hash_file(file_path_abs)

    # Compute changeset
    if force:
        changeset = Changeset(
            added=list(file_hashes.keys()),
            modified=[],
            deleted=[],
        )
        log("Force mode — re-indexing all files")
    else:
        changeset = compute_changeset(conn, repo_id, file_hashes)
        if not changeset.has_changes:
            log("No changes detected")
            queries.update_repo_ingested_at(conn, repo_id)
            return {"added": 0, "modified": 0, "deleted": 0, "chunks": 0, "skipped": len(walker.skipped_files)}
        log(f"Changes: +{len(changeset.added)} ~{len(changeset.modified)} -{len(changeset.deleted)}")

    # Initialize ChromaDB
    chroma_client = _get_chroma_client(settings)
    collection = chroma_client.get_or_create_collection(name=collection_name)

    total_chunks = 0

    # Process added + modified files
    files_to_process = changeset.added + changeset.modified
    for i, rel_path in enumerate(files_to_process):
        abs_path = repo_path / rel_path
        log(f"[{i + 1}/{len(files_to_process)}] {rel_path}")

        try:
            content = abs_path.read_text(errors="replace")
        except OSError:
            log(f"  Could not read {rel_path}, skipping")
            continue

        # Delete old chunks if modified
        if rel_path in changeset.modified:
            _delete_file_chunks_from_chroma(collection, rel_path)

        # Chunk the file
        chunks = chunk_file(
            content,
            rel_path,
            token_target=repo_config.token_target,
            overlap_tokens=repo_config.overlap_tokens,
        )

        # Upsert to ChromaDB
        count = _upsert_chunks_to_chroma(collection, chunks, rel_path, str(repo_path))
        total_chunks += count

        # Update file record in SQLite
        stat = abs_path.stat()
        queries.upsert_file(
            conn,
            repository_id=repo_id,
            file_path=rel_path,
            content_hash=file_hashes[rel_path],
            size_bytes=stat.st_size,
            language=get_language(abs_path),
            chunk_count=len(chunks),
            skipped=False,
            last_modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        )

    # Handle deleted files
    for rel_path in changeset.deleted:
        _delete_file_chunks_from_chroma(collection, rel_path)
    if changeset.deleted:
        queries.delete_files_by_paths(conn, repo_id, changeset.deleted)
        log(f"Removed {len(changeset.deleted)} deleted files")

    # Record skipped files in SQLite (so stats are accurate)
    for rel_path, reason in walker.skipped_files:
        abs_path = repo_path / rel_path
        try:
            stat = abs_path.stat()
            queries.upsert_file(
                conn,
                repository_id=repo_id,
                file_path=rel_path,
                content_hash="",
                size_bytes=stat.st_size,
                language=get_language(abs_path),
                chunk_count=0,
                skipped=True,
                last_modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            )
        except OSError:
            pass

    # Update merkle tree
    log("Updating merkle tree...")
    merkle_tree = build_merkle_tree(file_hashes)
    nodes_to_upsert = [
        (node_path, node_hash, is_dir)
        for node_path, (node_hash, is_dir) in merkle_tree.items()
    ]
    queries.batch_upsert_merkle_nodes(conn, repo_id, nodes_to_upsert)

    # Clean up deleted nodes from merkle tree
    if changeset.deleted:
        queries.delete_merkle_nodes_by_paths(conn, repo_id, changeset.deleted)

    queries.update_repo_ingested_at(conn, repo_id)

    return {
        "added": len(changeset.added),
        "modified": len(changeset.modified),
        "deleted": len(changeset.deleted),
        "chunks": total_chunks,
        "skipped": len(walker.skipped_files),
    }


def ingest_files(
    conn: sqlite3.Connection,
    settings: Settings,
    repo_name: str,
    file_paths: list[Path],
    threshold: int | None = None,
) -> dict:
    """Force-ingest specific files, ignoring threshold.

    Args:
        conn: SQLite connection.
        settings: Application settings.
        repo_name: Name of an existing indexed repository.
        file_paths: Absolute paths to files to ingest.
        threshold: Override chunk threshold for these files (or None for unlimited).

    Returns:
        Summary dict.
    """
    repo = queries.get_repo_by_name(conn, repo_name)
    if repo is None:
        raise ValueError(f"Repository '{repo_name}' not found. Run 'craigpy ingest' first.")

    repo_id = repo["id"]
    repo_path = Path(repo["path"])
    repo_config = settings.get_repo_config(str(repo_path))

    chroma_client = _get_chroma_client(settings)
    collection = chroma_client.get_or_create_collection(name=repo["collection_name"])

    total_chunks = 0
    processed = 0

    for abs_path in file_paths:
        abs_path = abs_path.resolve()
        if not abs_path.is_file():
            continue

        rel_path = str(abs_path.relative_to(repo_path))

        try:
            content = abs_path.read_text(errors="replace")
        except OSError:
            continue

        # Delete old chunks
        _delete_file_chunks_from_chroma(collection, rel_path)

        # Chunk with potentially unlimited threshold
        chunks = chunk_file(
            content,
            rel_path,
            token_target=repo_config.token_target,
            overlap_tokens=repo_config.overlap_tokens,
        )

        count = _upsert_chunks_to_chroma(collection, chunks, rel_path, str(repo_path))
        total_chunks += count

        # Update file + merkle
        file_hash = hash_file(abs_path)
        stat = abs_path.stat()
        queries.upsert_file(
            conn,
            repository_id=repo_id,
            file_path=rel_path,
            content_hash=file_hash,
            size_bytes=stat.st_size,
            language=get_language(abs_path),
            chunk_count=len(chunks),
            skipped=False,
            last_modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        )
        processed += 1

    return {"files": processed, "chunks": total_chunks}
