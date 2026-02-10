"""Chunking dispatcher — routes files to the appropriate chunker by language."""

from __future__ import annotations

from pathlib import Path

from craigpy.chunking.interface import Chunk
from craigpy.indexer.merkle import hash_content
from craigpy.chunking.heuristic.generic import chunk_generic
from craigpy.chunking.heuristic.typescript import chunk_typescript
from craigpy.chunking.heuristic.python_lang import chunk_python
from craigpy.chunking.heuristic.java import chunk_java
from craigpy.chunking.heuristic.go import chunk_go

# Extension → chunker function mapping
_CHUNKER_MAP: dict[str, callable] = {
    ".ts": chunk_typescript,
    ".tsx": chunk_typescript,
    ".js": chunk_typescript,
    ".jsx": chunk_typescript,
    ".mjs": chunk_typescript,
    ".cjs": chunk_typescript,
    ".py": chunk_python,
    ".pyw": chunk_python,
    ".pyx": chunk_python,
    ".pyi": chunk_python,
    ".java": chunk_java,
    ".kt": chunk_java,
    ".kts": chunk_java,
    ".go": chunk_go,
}


def chunk_file(
    content: str,
    file_path: str,
    token_target: int = 500,
    overlap_tokens: int = 64,
) -> list[Chunk]:
    """Chunk a file using the appropriate strategy based on extension.

    Returns a list of Chunk objects with content, line numbers, and metadata.
    """
    ext = Path(file_path).suffix.lower()
    chunker_fn = _CHUNKER_MAP.get(ext, chunk_generic)

    chunks = chunker_fn(content, file_path, token_target, overlap_tokens)

    # Set language and recompute hash with file context for uniqueness
    from craigpy.indexer.file_filter import get_language
    language = get_language(Path(file_path))
    for chunk in chunks:
        chunk.language = language
        chunk.chunk_hash = hash_content(f"{file_path}\x00{chunk.chunk_index}\x00{chunk.content}")

    return chunks
