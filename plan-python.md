# CraigPy — Python Plan

## Stack

- **Runtime:** Python 3.11+ (managed via mise)
- **Package Manager:** uv
- **Embeddings:** ChromaDB built-in (ONNX, all-MiniLM-L6-v2 by default)
- **Vector Store:** ChromaDB (embedded, persistent)
- **Relational Store:** SQLite3 (stdlib, zero deps — merkle state + repo metadata)
- **Chunking:** Hybrid — heuristic-first, tree-sitter pluggable per-language
- **CLI Framework:** click
- **MCP SDK:** `mcp` (Python MCP SDK)

## External Dependencies

**None at runtime.** ChromaDB runs fully embedded in-process. SQLite is stdlib. No Docker, no server.

## Phases

### Phase 1: Project Scaffolding + Config + SQLite
- mise + uv project setup
- Directory structure with `src/craigpy/`
- Config loading (`~/.config/craigpy/config.json`) with per-repo overrides
- SQLite schema + migration runner
- Tables: repositories, files, merkle_nodes

### Phase 2: File Walking + Filtering + Merkle Tree
- Recursive file walker respecting `.gitignore`
- Binary file detection (extension allowlist + magic bytes)
- Chunk threshold estimation and skip logic
- Merkle tree: SHA-256 per file → directory hash rollup
- Differ: compare stored vs current tree → changeset (added/modified/deleted)

### Phase 3: Chunking Engine
- Chunker protocol (pluggable interface)
- Heuristic chunkers: TypeScript/JS, Python, Java, Go, generic fallback
- Token estimation (`len(text) / 4`)
- Overlap between consecutive chunks
- Chunk hash (SHA-256) for dedup

### Phase 4: ChromaDB Integration + Ingest Pipeline
- ChromaDB persistent client setup
- Per-repo collections
- Ingest pipeline: diff → filter → chunk → upsert to ChromaDB
- Incremental re-indexing (only changed files)
- Embedding dedup via chunk content hash as document ID

### Phase 5: CLI
- `craigpy ingest <path> [--name repo-name]` — full or incremental ingest
- `craigpy ingest-file <path> [--threshold N]` — force-ingest large file(s)
- `craigpy status [--repo name]` — merkle diff
- `craigpy repos` — list indexed repos
- `craigpy config` — show config

### Phase 6: MCP Server + Tools
- MCP server (stdio transport)
- Tools: query, similar, find_symbol, repos, files, stats, read, status

---

## Architecture

```
craigpy/
├── src/
│   └── craigpy/
│       ├── __init__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py               # Click CLI entry point
│       │   ├── ingest.py             # Walk repo → chunk → add to ChromaDB
│       │   ├── ingest_file.py        # Force-ingest specific file(s) above threshold
│       │   └── status.py             # Show merkle diff
│       │
│       ├── mcp/
│       │   ├── __init__.py
│       │   ├── server.py             # MCP server entry point (stdio transport)
│       │   └── tools/
│       │       ├── __init__.py
│       │       ├── query.py          # Semantic search
│       │       ├── similar.py        # Find similar code
│       │       ├── find_symbol.py    # Symbol search
│       │       ├── repos.py          # List indexed repos
│       │       ├── files.py          # List files in a repo
│       │       ├── stats.py          # Repo statistics
│       │       ├── read.py           # Read file content
│       │       └── status.py         # Merkle diff
│       │
│       ├── indexer/
│       │   ├── __init__.py
│       │   ├── merkle.py             # SHA-256 per file → directory hash rollup
│       │   ├── differ.py             # Stored vs current merkle → changeset
│       │   ├── pipeline.py           # diff → filter → chunk → upsert to ChromaDB
│       │   └── file_filter.py        # .gitignore, binary detection, chunk threshold
│       │
│       ├── chunking/
│       │   ├── __init__.py
│       │   ├── interface.py          # Chunker protocol (pluggable)
│       │   ├── heuristic/
│       │   │   ├── __init__.py
│       │   │   ├── typescript.py     # TS/JS split rules
│       │   │   ├── python_lang.py    # Python split rules
│       │   │   ├── java.py           # Java split rules
│       │   │   ├── go.py             # Go split rules
│       │   │   └── generic.py        # Line-based fallback
│       │   └── tree_sitter/          # Optional — add later
│       │       ├── __init__.py
│       │       └── queries/
│       │
│       ├── db/
│       │   ├── __init__.py
│       │   ├── client.py             # SQLite singleton connection
│       │   ├── migrations.py         # Migration runner
│       │   └── queries.py            # Repo CRUD, file CRUD, merkle ops
│       │
│       └── config/
│           ├── __init__.py
│           └── settings.py           # Load/merge ~/.config/craigpy/config.json
```

## Data Storage

- **Config:** `~/.config/craigpy/config.json`
- **ChromaDB:** `~/.local/share/craigpy/chroma/` (embedded persistent)
- **SQLite:** `~/.local/share/craigpy/metadata.db` (merkle + repo metadata)

## Database Schema (SQLite)

### repositories
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT | UUID, PK |
| name | TEXT | UNIQUE slug |
| path | TEXT | Absolute path on disk |
| collection_name | TEXT | ChromaDB collection name |
| ingested_at | TEXT | ISO 8601 timestamp |

### files
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PK AUTOINCREMENT |
| repository_id | TEXT | FK → repositories |
| file_path | TEXT | Relative to repo root |
| content_hash | TEXT | SHA-256 |
| size_bytes | INTEGER | |
| language | TEXT | File extension |
| chunk_count | INTEGER | 0 if skipped |
| skipped | INTEGER | 1 if over threshold |
| last_modified | TEXT | ISO 8601 |

### merkle_nodes
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PK AUTOINCREMENT |
| repository_id | TEXT | FK → repositories |
| node_path | TEXT | Dir or file path |
| node_hash | TEXT | SHA-256 (leaf) or rollup (dir) |
| is_directory | INTEGER | 0/1 |
| updated_at | TEXT | ISO 8601 |

UNIQUE constraint on `(repository_id, node_path)`.

## ChromaDB Usage

```python
import chromadb

client = chromadb.PersistentClient(path="~/.local/share/craigpy/chroma")
collection = client.get_or_create_collection("repo-slug")

# Ingest — ChromaDB embeds automatically
collection.upsert(
    ids=[chunk_hash],
    documents=[chunk_text],
    metadatas=[{
        "file_path": "src/index.ts",
        "start_line": 10,
        "end_line": 45,
        "language": "typescript",
        "symbol_name": "handleRequest",
        "symbol_type": "function",
    }],
)

# Query — semantic search with metadata filters
results = collection.query(
    query_texts=["authentication handler"],
    n_results=10,
    where={"language": "typescript"},
)
```

## Chunking Strategy

### Heuristic split points (default)

| Language | Extensions | Split markers |
|----------|-----------|--------------|
| TypeScript/JS | .ts,.tsx,.js,.jsx,.mjs,.cjs | `export`, `function`, `class`, `interface`, `type`, `const ... =`, blank lines |
| Python | .py | `def `, `class `, `@decorator`, blank-line-separated top-level |
| Java | .java | access modifiers + `class`/`interface`/method, `@Annotation` |
| Go | .go | `func `, `type ... struct`, `type ... interface` |
| Generic | everything else | Blank-line separation, respect token target |

### Configuration defaults

```json
{
  "defaults": {
    "token_target": 500,
    "overlap_tokens": 64,
    "chunk_threshold": 200,
    "max_file_size_bytes": 10485760
  }
}
```

### Tree-sitter (pluggable, later)

Same Chunker protocol, swap in per-language for AST-based chunking.

## File Filtering

1. **Binary detection:** Extension allowlist + magic bytes. Ignored entirely.
2. **.gitignore:** Respected via `pathspec` library.
3. **Chunk threshold:** `estimated_chunks = file_size / (token_target * 4)`. Skip if > threshold.
4. **Force ingest:** `craigpy ingest-file <path> [--threshold N]`.

## Per-Repo Config

```json
{
  "defaults": {
    "token_target": 500,
    "overlap_tokens": 64,
    "chunk_threshold": 200
  },
  "repos": {
    "/Users/you/big-project": {
      "chunk_threshold": 500,
      "token_target": 750
    }
  }
}
```

Repo-specific values override defaults. Unset keys fall back to defaults.
