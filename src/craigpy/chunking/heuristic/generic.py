"""Generic line-based chunker — fallback for unsupported file types."""

from __future__ import annotations

from craigpy.chunking.interface import Chunk, estimate_tokens


def chunk_generic(
    content: str,
    file_path: str,
    token_target: int,
    overlap_tokens: int,
) -> list[Chunk]:
    """Split text into chunks by blank-line-separated blocks, respecting token target."""
    if not content.strip():
        return []

    lines = content.splitlines(keepends=True)
    chunks: list[Chunk] = []
    current_lines: list[str] = []
    current_start = 1  # 1-indexed
    current_tokens = 0

    for i, line in enumerate(lines, start=1):
        line_tokens = estimate_tokens(line)

        # If adding this line would exceed target and we have content, finalize chunk
        if current_tokens + line_tokens > token_target * 1.2 and current_lines:
            chunk_text = "".join(current_lines)
            chunks.append(Chunk(
                content=chunk_text,
                start_line=current_start,
                end_line=i - 1,
                chunk_index=len(chunks),
            ))

            # Overlap: carry last N tokens worth of lines
            overlap_lines: list[str] = []
            overlap_tok = 0
            for prev_line in reversed(current_lines):
                lt = estimate_tokens(prev_line)
                if overlap_tok + lt > overlap_tokens:
                    break
                overlap_lines.insert(0, prev_line)
                overlap_tok += lt

            current_lines = overlap_lines + [line]
            current_start = i - len(overlap_lines)
            current_tokens = overlap_tok + line_tokens
            continue

        # Blank line as a natural break point
        if line.strip() == "" and current_tokens >= token_target * 0.6 and current_lines:
            chunk_text = "".join(current_lines)
            chunks.append(Chunk(
                content=chunk_text,
                start_line=current_start,
                end_line=i - 1,
                chunk_index=len(chunks),
            ))
            current_lines = []
            current_start = i + 1
            current_tokens = 0
            continue

        current_lines.append(line)
        current_tokens += line_tokens

    # Final chunk
    if current_lines:
        chunk_text = "".join(current_lines)
        chunks.append(Chunk(
            content=chunk_text,
            start_line=current_start,
            end_line=current_start + len(current_lines) - 1,
            chunk_index=len(chunks),
        ))

    return chunks
