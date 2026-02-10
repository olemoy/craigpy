"""Chunker protocol — pluggable interface for different chunking strategies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from craigpy.indexer.merkle import hash_content


@dataclass
class Chunk:
    """A single chunk of code/text from a file."""

    content: str
    start_line: int
    end_line: int
    chunk_index: int
    chunk_hash: str = ""
    language: str | None = None
    symbol_name: str | None = None
    symbol_type: str | None = None

    def __post_init__(self) -> None:
        if not self.chunk_hash:
            self.chunk_hash = hash_content(self.content)


def estimate_tokens(text: str) -> int:
    """Estimate token count — ~4 chars per token."""
    return max(1, len(text) // 4)


class Chunker(Protocol):
    """Protocol for chunking strategies."""

    def chunk(
        self,
        content: str,
        file_path: str,
        token_target: int,
        overlap_tokens: int,
    ) -> list[Chunk]: ...
