# CraigPy

Local codebase indexer with semantic search. Indexes repos into ChromaDB (embedded) with SQLite-backed merkle tree for incremental updates. Exposes read-only search via MCP.

```
  CLI ingest              MCP server (stdio)
      |                        |
      v                        v
  FileWalker ──> Chunker ──> ChromaDB (embedded, ONNX all-MiniLM-L6-v2)
      |              |
      v              v
  Merkle Tree    SQLite (file state, repo metadata)
  (SHA-256)
```

**Ingest flow:** Walk files (respecting `.gitignore`) → merkle diff against stored hashes → chunk changed files at language-aware boundaries → upsert to ChromaDB (handles embedding automatically) → update SQLite state.

**Query flow:** MCP tools query ChromaDB collections via semantic similarity or metadata filters. All tools are read-only.

## Install & Build

Requires Python 3.12 (managed via [mise](https://mise.jdx.dev/)) and [uv](https://docs.astral.sh/uv/).

```sh
uv sync                # Install deps + dev editable install
uv build               # Build wheel + sdist → dist/
pip install dist/*.whl  # Install the wheel elsewhere
```

### Dev tools

```sh
craigpy-inspect        # Launch MCP Inspector (needs bunx or npx)
```

## CLI

All commands below assume a global install. For dev, prefix with `uv run`.

```sh
craigpy ingest <path> [--name NAME] [--force]   # Index a repo (incremental by default)
craigpy ingest-file <files...> --repo NAME       # Force-ingest files that exceeded chunk threshold
craigpy status [--repo NAME]                     # Show changes since last index (merkle diff)
craigpy repos                                    # List indexed repos
craigpy config                                   # Show config
craigpy init                                     # Initialize config + DB
```

Data: `~/.config/craigpy/` (config), `~/.local/share/craigpy/` (ChromaDB + SQLite).

## MCP Server

```sh
craigpy-mcp   # stdio transport
```

### Tools

| Tool | Description |
|------|-------------|
| `query` | Semantic search via natural language. Filters: `repository`, `language`, `limit` |
| `similar` | Find code similar to a given snippet |
| `find_symbol` | Search by symbol name/pattern (`*auth*`) and type (function, class, etc.) |
| `repos` | List indexed repositories with file counts |
| `files` | List files in a repo. Filters: `path` prefix, `pattern` glob |
| `stats` | Repo statistics: file counts, chunk counts, language distribution |
| `read` | Read file content from an indexed repo |
| `status` | Merkle diff — what changed since last index |

## Chunking

Heuristic per-language chunkers split at logical boundaries (function/class declarations). Falls back to line-based splitting for unknown extensions. Languages: Python, TypeScript/JavaScript, Java/Kotlin, Go.

Chunk content hash = ChromaDB document ID (natural dedup). One collection per repo.

## Config

Global `~/.config/craigpy/config.json` with per-repo overrides:

```json
{
  "defaults": { "token_target": 500, "overlap_tokens": 64, "chunk_threshold": 200 },
  "repos": { "/path/to/repo": { "token_target": 300 } }
}
```
