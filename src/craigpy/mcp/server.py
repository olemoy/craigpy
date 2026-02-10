"""CraigPy MCP server — exposes indexed codebase via semantic search tools."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import chromadb
from mcp.server.fastmcp import FastMCP

from craigpy.config.settings import load_settings, Settings
from craigpy.db.client import get_connection
from craigpy.db import queries

# Logging to stderr only (stdout is reserved for MCP JSON-RPC)
logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[logging.StreamHandler()])
logger = logging.getLogger("craigpy-mcp")

mcp = FastMCP("craigpy")

# --- Shared state ---

_settings: Settings | None = None
_chroma: chromadb.PersistentClient | None = None


def _get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_settings()
        _settings.ensure_dirs()
    return _settings


def _get_chroma() -> chromadb.PersistentClient:
    global _chroma
    if _chroma is None:
        settings = _get_settings()
        _chroma = chromadb.PersistentClient(path=str(settings.chroma_path))
    return _chroma


def _resolve_repo(repo: str) -> tuple[dict, chromadb.Collection]:
    """Resolve a repo name/path to its DB row and ChromaDB collection."""
    settings = _get_settings()
    conn = get_connection(settings.sqlite_path)

    repo_row = queries.get_repo_by_name(conn, repo)
    if repo_row is None:
        repo_row = queries.get_repo_by_path(conn, repo)
    if repo_row is None:
        raise ValueError(f"Repository '{repo}' not found. Run 'craigpy repos' to see indexed repos.")

    client = _get_chroma()
    collection = client.get_collection(name=repo_row["collection_name"])
    return dict(repo_row), collection


# --- Tools ---


@mcp.tool()
def query(query: str, repository: str | None = None, limit: int = 10, language: str | None = None) -> str:
    """Search indexed code using natural language.

    Args:
        query: Natural language search query (e.g. "authentication handler", "database connection pool")
        repository: Repository name to search in (optional — searches first available if omitted)
        limit: Maximum number of results to return (default: 10)
        language: Filter by programming language (e.g. "typescript", "python")
    """
    if not query.strip():
        return "Error: query cannot be empty."

    settings = _get_settings()
    conn = get_connection(settings.sqlite_path)

    if repository:
        _, collection = _resolve_repo(repository)
    else:
        repo_list = queries.list_repos(conn)
        if not repo_list:
            return "No repositories indexed. Run 'craigpy ingest <path>' first."
        _, collection = _resolve_repo(repo_list[0]["name"])

    where_filter = None
    if language:
        where_filter = {"language": language}

    results = collection.query(
        query_texts=[query],
        n_results=min(limit, 50),
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    if not results["ids"][0]:
        return "No results found."

    output: list[dict] = []
    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        output.append({
            "file_path": meta.get("file_path", ""),
            "start_line": meta.get("start_line"),
            "end_line": meta.get("end_line"),
            "language": meta.get("language"),
            "symbol_name": meta.get("symbol_name"),
            "symbol_type": meta.get("symbol_type"),
            "similarity": round(1 - dist, 4),
            "content": doc,
        })

    return json.dumps(output, indent=2)


@mcp.tool()
def similar(code: str, repository: str | None = None, limit: int = 10) -> str:
    """Find code similar to a given snippet.

    Args:
        code: Code snippet to find similar matches for
        repository: Repository name to search in (optional)
        limit: Maximum number of results (default: 10)
    """
    if not code.strip():
        return "Error: code snippet cannot be empty."

    settings = _get_settings()
    conn = get_connection(settings.sqlite_path)

    if repository:
        _, collection = _resolve_repo(repository)
    else:
        repo_list = queries.list_repos(conn)
        if not repo_list:
            return "No repositories indexed."
        _, collection = _resolve_repo(repo_list[0]["name"])

    results = collection.query(
        query_texts=[code],
        n_results=min(limit, 50),
        include=["documents", "metadatas", "distances"],
    )

    if not results["ids"][0]:
        return "No similar code found."

    output: list[dict] = []
    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        output.append({
            "file_path": meta.get("file_path", ""),
            "start_line": meta.get("start_line"),
            "end_line": meta.get("end_line"),
            "language": meta.get("language"),
            "symbol_name": meta.get("symbol_name"),
            "symbol_type": meta.get("symbol_type"),
            "similarity": round(1 - dist, 4),
            "content": doc,
        })

    return json.dumps(output, indent=2)


@mcp.tool()
def find_symbol(
    name: str | None = None,
    name_pattern: str | None = None,
    symbol_type: str | None = None,
    repository: str | None = None,
    limit: int = 50,
) -> str:
    """Search for code symbols by name and type.

    Args:
        name: Exact symbol name to search for
        name_pattern: Pattern with wildcards (e.g. "*auth*" matches "authenticate", "authorization")
        symbol_type: Filter by type: function, class, interface, method, type, struct, enum
        repository: Repository name (optional)
        limit: Maximum results (default: 50)
    """
    if not name and not name_pattern:
        return "Error: provide either 'name' or 'name_pattern'."

    settings = _get_settings()
    conn = get_connection(settings.sqlite_path)

    if repository:
        _, collection = _resolve_repo(repository)
    else:
        repo_list = queries.list_repos(conn)
        if not repo_list:
            return "No repositories indexed."
        _, collection = _resolve_repo(repo_list[0]["name"])

    # Build ChromaDB where filter for metadata
    where_conditions: list[dict] = []
    if name:
        where_conditions.append({"symbol_name": name})
    if symbol_type:
        where_conditions.append({"symbol_type": symbol_type})

    where_filter: dict | None = None
    if len(where_conditions) == 1:
        where_filter = where_conditions[0]
    elif len(where_conditions) > 1:
        where_filter = {"$and": where_conditions}

    # For pattern matching, we need to get more results and filter client-side
    fetch_limit = min(limit * 5, 500) if name_pattern else min(limit, 200)

    try:
        results = collection.get(
            where=where_filter if where_filter else {"symbol_name": {"$ne": ""}},
            include=["metadatas", "documents"],
            limit=fetch_limit,
        )
    except Exception:
        return "No symbols found matching the criteria."

    if not results["ids"]:
        return "No symbols found."

    # Client-side pattern filtering
    import fnmatch
    output: list[dict] = []
    for meta, doc in zip(results["metadatas"], results["documents"]):
        sym_name = meta.get("symbol_name")
        if not sym_name:
            continue

        if name_pattern and not fnmatch.fnmatch(sym_name.lower(), name_pattern.lower()):
            continue

        output.append({
            "name": sym_name,
            "type": meta.get("symbol_type"),
            "file_path": meta.get("file_path", ""),
            "start_line": meta.get("start_line"),
            "end_line": meta.get("end_line"),
            "language": meta.get("language"),
            "content_preview": (doc[:200] + "...") if len(doc) > 200 else doc,
        })

        if len(output) >= limit:
            break

    if not output:
        return "No symbols found matching the criteria."

    return json.dumps(output, indent=2)


@mcp.tool()
def repos() -> str:
    """List all indexed repositories with file counts."""
    settings = _get_settings()
    conn = get_connection(settings.sqlite_path)
    repo_list = queries.list_repos(conn)

    if not repo_list:
        return "No repositories indexed. Run 'craigpy ingest <path>' to get started."

    output: list[dict] = []
    for repo in repo_list:
        file_count = queries.get_file_count(conn, repo["id"])
        output.append({
            "name": repo["name"],
            "path": repo["path"],
            "file_count": file_count,
            "last_indexed": repo["ingested_at"],
        })

    return json.dumps(output, indent=2)


@mcp.tool()
def files(repository: str, path: str | None = None, pattern: str | None = None, limit: int = 100) -> str:
    """List files in an indexed repository.

    Args:
        repository: Repository name
        path: Filter to files under this path (e.g. "src/", "tests/")
        pattern: Glob pattern filter (e.g. "*.py", "*test*")
        limit: Maximum files to return (default: 100)
    """
    settings = _get_settings()
    conn = get_connection(settings.sqlite_path)

    repo_row = queries.get_repo_by_name(conn, repository)
    if repo_row is None:
        repo_row = queries.get_repo_by_path(conn, repository)
    if repo_row is None:
        return f"Repository '{repository}' not found."

    all_files = queries.get_files_by_repo(conn, repo_row["id"])

    import fnmatch
    result: list[str] = []
    for f in all_files:
        fp = f["file_path"]
        if path and not fp.startswith(path):
            continue
        if pattern and not fnmatch.fnmatch(fp.split("/")[-1], pattern):
            continue
        result.append(fp)
        if len(result) >= limit:
            break

    return json.dumps({
        "repository": repo_row["name"],
        "total": len(result),
        "files": result,
    }, indent=2)


@mcp.tool()
def stats(repository: str) -> str:
    """Get statistics for an indexed repository.

    Args:
        repository: Repository name
    """
    settings = _get_settings()
    conn = get_connection(settings.sqlite_path)

    repo_row = queries.get_repo_by_name(conn, repository)
    if repo_row is None:
        repo_row = queries.get_repo_by_path(conn, repository)
    if repo_row is None:
        return f"Repository '{repository}' not found."

    all_files = queries.get_files_by_repo(conn, repo_row["id"])

    total_files = len(all_files)
    skipped_files = sum(1 for f in all_files if f["skipped"])
    total_chunks = sum(f["chunk_count"] for f in all_files)

    # Language distribution
    lang_counts: dict[str, int] = {}
    for f in all_files:
        lang = f["language"] or "unknown"
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

    # ChromaDB collection count
    try:
        client = _get_chroma()
        collection = client.get_collection(name=repo_row["collection_name"])
        chroma_count = collection.count()
    except Exception:
        chroma_count = 0

    return json.dumps({
        "repository": repo_row["name"],
        "path": repo_row["path"],
        "last_indexed": repo_row["ingested_at"],
        "total_files": total_files,
        "indexed_files": total_files - skipped_files,
        "skipped_files": skipped_files,
        "total_chunks_in_db": total_chunks,
        "total_chunks_in_chroma": chroma_count,
        "languages": dict(sorted(lang_counts.items(), key=lambda x: -x[1])),
    }, indent=2)


@mcp.tool()
def read(file_path: str, repository: str) -> str:
    """Read a file's content from an indexed repository.

    Args:
        file_path: Relative file path in the repository (e.g. "src/main.py")
        repository: Repository name
    """
    settings = _get_settings()
    conn = get_connection(settings.sqlite_path)

    repo_row = queries.get_repo_by_name(conn, repository)
    if repo_row is None:
        repo_row = queries.get_repo_by_path(conn, repository)
    if repo_row is None:
        return f"Repository '{repository}' not found."

    # Read from disk
    abs_path = Path(repo_row["path"]) / file_path
    if not abs_path.is_file():
        return f"File not found: {file_path}"

    try:
        content = abs_path.read_text(errors="replace")
    except OSError as e:
        return f"Error reading file: {e}"

    return json.dumps({
        "file_path": file_path,
        "repository": repo_row["name"],
        "content": content,
        "size_bytes": abs_path.stat().st_size,
    })


@mcp.tool()
def status(repository: str | None = None) -> str:
    """Show what changed since last index (merkle diff).

    Args:
        repository: Repository name (optional — shows all if omitted)
    """
    settings = _get_settings()
    conn = get_connection(settings.sqlite_path)

    from craigpy.indexer.differ import compute_changeset
    from craigpy.indexer.file_filter import FileWalker
    from craigpy.indexer.merkle import hash_file

    if repository:
        repo_list = [queries.get_repo_by_name(conn, repository)]
        if repo_list[0] is None:
            return f"Repository '{repository}' not found."
    else:
        repo_list = queries.list_repos(conn)

    if not repo_list:
        return "No repositories indexed."

    output: list[dict] = []
    for repo_row in repo_list:
        repo_path = Path(repo_row["path"])
        if not repo_path.exists():
            output.append({"repository": repo_row["name"], "error": "Path no longer exists"})
            continue

        repo_config = settings.get_repo_config(str(repo_path))
        walker = FileWalker(repo_path, repo_config)
        walked_files = walker.walk()

        file_hashes: dict[str, str] = {}
        for f in walked_files:
            rel = str(f.relative_to(repo_path))
            file_hashes[rel] = hash_file(f)

        changeset = compute_changeset(conn, repo_row["id"], file_hashes)

        output.append({
            "repository": repo_row["name"],
            "up_to_date": not changeset.has_changes,
            "added": len(changeset.added),
            "modified": len(changeset.modified),
            "deleted": len(changeset.deleted),
            "added_files": changeset.added[:20],
            "modified_files": changeset.modified[:20],
            "deleted_files": changeset.deleted[:20],
        })

    return json.dumps(output, indent=2)


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
