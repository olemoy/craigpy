# Craig2 — TypeScript Plan

## Stack

- **Runtime:** Bun
- **Language:** TypeScript
- **Embeddings:** `@huggingface/transformers` (v3.x) — ONNX WASM, all-MiniLM-L6-v2 (384 dims)
- **Vector Store:** PGlite + pgvector
- **Relational Store:** PGlite (merkle state, repo metadata, file metadata)
- **Chunking:** Hybrid — heuristic-first, tree-sitter pluggable per-language
- **MCP SDK:** `@modelcontextprotocol/sdk`
- **Packaging:** `bun build --compile` single binary

## External Dependencies

**None.** Fully embedded, single process. No Docker, no server, no Python.

## Architecture

```
craig2/
├── src/
│   ├── cli/
│   │   ├── index.ts              # CLI entry point (commands: ingest, ingest-file, status)
│   │   ├── ingest.ts             # Walk repo → chunk → embed → store
│   │   ├── ingest-file.ts        # Force-ingest specific file(s) above threshold
│   │   └── status.ts             # Show merkle diff (what changed since last index)
│   │
│   ├── mcp/
│   │   ├── server.ts             # MCP server entry point (stdio transport)
│   │   └── tools/
│   │       ├── query.ts          # Semantic search (natural language → similar chunks)
│   │       ├── similar.ts        # Find similar code to a given snippet
│   │       ├── find-symbol.ts    # Symbol search (name, type, visibility filters)
│   │       ├── repos.ts          # List all indexed repositories
│   │       ├── files.ts          # List files in a repo (with glob pattern)
│   │       ├── stats.ts          # Repo statistics (file counts, chunk counts, languages)
│   │       ├── read.ts           # Read file content from index
│   │       └── status.ts         # What's changed since last index (merkle diff)
│   │
│   ├── indexer/
│   │   ├── merkle.ts             # SHA-256 per file → directory hash rollup
│   │   ├── differ.ts             # Compare stored vs current merkle tree → changeset
│   │   ├── pipeline.ts           # Orchestrate: diff → filter → chunk → embed → upsert
│   │   └── file-filter.ts        # .gitignore, binary detection, chunk threshold check
│   │
│   ├── chunking/
│   │   ├── interface.ts          # Chunker interface (pluggable)
│   │   ├── heuristic/
│   │   │   ├── index.ts          # Dispatcher by file extension
│   │   │   ├── typescript.ts     # TS/JS: split on export, function, class, const arrow, blank lines
│   │   │   ├── python.ts         # Python: split on def, class, decorators, blank-line blocks
│   │   │   ├── java.ts           # Java: split on class/interface/method declarations
│   │   │   ├── go.ts             # Go: split on func, type struct/interface
│   │   │   └── generic.ts        # Fallback: line-based with token target
│   │   └── tree-sitter/          # Optional — add per-language when needed
│   │       ├── index.ts
│   │       └── queries/          # .scm files per language
│   │
│   ├── embeddings/
│   │   └── pipeline.ts           # @huggingface/transformers wrapper
│   │                             # - Model: all-MiniLM-L6-v2 (384 dims)
│   │                             # - Auto-downloads on first run, cached locally
│   │                             # - Batch embedding with progress
│   │
│   ├── db/
│   │   ├── client.ts             # PGlite singleton (pgvector extension loaded)
│   │   ├── schema.ts             # Migration runner
│   │   ├── migrations/
│   │   │   ├── 000_tracker.sql
│   │   │   ├── 001_repos_files.sql
│   │   │   ├── 002_chunks_embeddings.sql
│   │   │   ├── 003_merkle.sql
│   │   │   └── 004_symbols.sql
│   │   └── queries.ts            # Similarity search, symbol lookup, merkle ops
│   │
│   └── config/
│       └── index.ts              # Load/merge config from ~/.config/craig2/config.json
```

## Data Storage

- **Config:** `~/.config/craig2/config.json`
- **Database:** `~/.local/share/craig2/craig2.db` (PGlite)
- **Model cache:** `~/.local/share/craig2/models/`

Global by default so MCP agents can access repos indexed from anywhere.

## Database Schema (PGlite)

### repositories
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| name | TEXT | Unique slug |
| path | TEXT | Absolute path on disk |
| ingested_at | TIMESTAMP | Last full ingest |
| metadata | JSONB | |

### files
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL | PK |
| repository_id | UUID | FK |
| file_path | TEXT | Relative to repo root |
| content_hash | TEXT | SHA-256 of file content |
| size_bytes | INTEGER | |
| language | TEXT | File extension |
| chunk_count | INTEGER | 0 if skipped |
| skipped | BOOLEAN | True if over threshold |
| last_modified | TIMESTAMP | |

### merkle_nodes
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL | PK |
| repository_id | UUID | FK |
| node_path | TEXT | Dir path (or file path for leaves) |
| node_hash | TEXT | SHA-256 (files) or rollup (dirs) |
| is_directory | BOOLEAN | |
| updated_at | TIMESTAMP | |

### chunks
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL | PK |
| file_id | INTEGER | FK → files |
| chunk_index | INTEGER | Position in file |
| content | TEXT | Chunk text |
| chunk_hash | TEXT | SHA-256 of content (for dedup) |
| start_line | INTEGER | |
| end_line | INTEGER | |
| metadata | JSONB | Symbol info if available |

### embeddings
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL | PK |
| chunk_id | INTEGER | FK → chunks, UNIQUE |
| embedding | vector(384) | pgvector |
| created_at | TIMESTAMP | |

### symbols (populated when tree-sitter is used)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| repository_id | UUID | FK |
| file_id | INTEGER | FK |
| chunk_id | INTEGER | FK |
| name | TEXT | Symbol name |
| symbol_type | TEXT | function, class, interface, etc. |
| file_path | TEXT | |
| start_line | INTEGER | |
| end_line | INTEGER | |
| parameters | TEXT | JSON stringified |
| return_type | TEXT | |
| visibility | TEXT | export, public, private, etc. |
| is_async | BOOLEAN | |
| docstring | TEXT | |

## Chunking Strategy

### Hybrid approach

1. **Heuristic chunking (default):** Per-language regex/pattern-based splitting. Fast, zero deps.
2. **Tree-sitter (pluggable):** Swap in per-language for richer AST-based chunking + symbol extraction.
3. **Generic fallback:** Line-based splitting for unsupported file types.

### Heuristic split points

| Language | Split markers |
|----------|--------------|
| TypeScript/JS | `export`, `function`, `class`, `interface`, `type`, `const ... =`, blank-line-separated blocks |
| Python | `def `, `class `, `@decorator` blocks, blank-line-separated top-level |
| Java | `public/private/protected` + `class`/`interface`/`void`/type, `@Annotation` |
| Go | `func `, `type ... struct`, `type ... interface` |
| Generic | Blank-line separation, respect `tokenTarget` size |

### Configuration

```json
{
  "defaults": {
    "tokenTarget": 500,
    "overlapTokens": 64,
    "chunkThreshold": 200,
    "maxFileSizeBytes": 10485760
  }
}
```

- **chunkThreshold:** Estimated max chunks per file. `estimated = file_size / (tokenTarget * 4)`. Files exceeding this are skipped unless force-ingested.
- **Configurable per-repo** in global config.

## File Filtering

1. **Binary detection:** Extension allowlist + magic bytes check. Binary files are ignored entirely.
2. **.gitignore:** Respected. Uses patterns from repo's `.gitignore`.
3. **Chunk threshold:** Files exceeding `chunkThreshold` estimated chunks are skipped with warning.
4. **Force ingest:** `craig2 ingest-file <path> [--threshold 500]` overrides for specific files.

## Merkle Tree

Simple local-only hierarchy:

1. Walk file tree, compute SHA-256 per file
2. Roll up directory hashes: `dir_hash = SHA-256(sorted child hashes)`
3. Store in `merkle_nodes` table
4. On re-ingest: compare stored vs computed, walk only changed branches
5. Changeset: list of added/modified/deleted file paths
6. Only re-chunk and re-embed changed files

**Embedding cache by chunk hash:** If a chunk's content hash matches an existing chunk, reuse its embedding. Handles file renames and minor edits efficiently.

## MCP Tools (read-only)

| Tool | Description |
|------|-------------|
| `query` | Semantic search with natural language. Returns ranked chunks with similarity scores. |
| `similar` | Find code similar to a given snippet. Embeds input, finds nearest neighbors. |
| `find_symbol` | Search symbols by name, type, visibility. Requires tree-sitter chunking for rich results. |
| `repos` | List all indexed repositories (name, path, file count, last indexed). |
| `files` | List files in a repo with optional glob pattern. Paginated. |
| `stats` | Repository statistics: file counts by language, chunk counts, embedding counts. |
| `read` | Read file content from the index. |
| `status` | Show what changed since last index (merkle diff summary). |

## CLI Commands (write operations)

| Command | Description |
|---------|-------------|
| `craig2 ingest <path> [--name repo-name]` | Full or incremental ingest of a repository |
| `craig2 ingest-file <path> [--threshold N]` | Force-ingest specific file(s) above threshold |
| `craig2 status [--repo name]` | Show merkle diff for a repo |
| `craig2 repos` | List indexed repos |
| `craig2 config` | Show current config |

## Per-Repo Config

Global config at `~/.config/craig2/config.json`:

```json
{
  "embedding": {
    "model": "Xenova/all-MiniLM-L6-v2",
    "dimensions": 384
  },
  "defaults": {
    "tokenTarget": 500,
    "overlapTokens": 64,
    "chunkThreshold": 200
  },
  "repos": {
    "/Users/you/big-project": {
      "chunkThreshold": 500,
      "tokenTarget": 750
    },
    "/Users/you/small-lib": {
      "chunkThreshold": 50
    }
  }
}
```

Repo-specific values override defaults. Unset keys fall back to defaults.

## Packaging

```bash
bun build --compile src/cli/index.ts --outfile craig2
bun build --compile src/mcp/server.ts --outfile craig2-mcp
```

Two binaries: one for CLI (ingestion), one for MCP server (agent access).
