"""Heuristic chunker for Java files."""

from __future__ import annotations

import re

from craigpy.chunking.interface import Chunk, estimate_tokens

JAVA_BLOCK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\s*(public|private|protected|static|\s)*\s*(class|interface|enum|record)\s+(\w+)"),
    re.compile(r"^\s*(public|private|protected|static|final|abstract|synchronized|native|\s)*\s*(<[\w<>,\s]+>\s+)?(\w+(\[\])*)\s+(\w+)\s*\("),
    re.compile(r"^\s*@\w+"),  # Annotation
    re.compile(r"^\s*import\s"),
    re.compile(r"^\s*package\s"),
]


def _is_block_start(line: str) -> bool:
    stripped = line.lstrip()
    indent = len(line) - len(stripped)
    # Only match at class level (0-8 spaces)
    if indent > 8:
        return False
    return any(p.match(line) for p in JAVA_BLOCK_PATTERNS)


def _extract_symbol(line: str) -> tuple[str | None, str | None]:
    stripped = line.lstrip()
    for keyword in ("class", "interface", "enum", "record"):
        m = re.search(rf"{keyword}\s+(\w+)", stripped)
        if m:
            return m.group(1), keyword

    # Method: return_type name(
    m = re.search(r"(\w+)\s*\(", stripped)
    if m and m.group(1) not in ("if", "while", "for", "switch", "catch"):
        return m.group(1), "method"

    return None, None


def chunk_java(
    content: str,
    file_path: str,
    token_target: int,
    overlap_tokens: int,
) -> list[Chunk]:
    """Split Java code into chunks at class/method boundaries."""
    if not content.strip():
        return []

    lines = content.splitlines(keepends=True)
    chunks: list[Chunk] = []

    # Collect package + imports
    header_lines: list[str] = []
    code_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if (
            stripped.startswith("package ")
            or stripped.startswith("import ")
            or stripped == ""
            or stripped.startswith("//")
            or stripped.startswith("/*")
            or stripped.startswith("*")
        ):
            header_lines.append(line)
            code_start = i + 1
        else:
            break

    if header_lines and estimate_tokens("".join(header_lines)) > 10:
        chunks.append(Chunk(
            content="".join(header_lines),
            start_line=1,
            end_line=code_start,
            chunk_index=0,
        ))

    current_lines: list[str] = []
    current_start = code_start + 1
    current_symbol: str | None = None
    current_symbol_type: str | None = None
    current_tokens = 0

    for i in range(code_start, len(lines)):
        line = lines[i]
        line_num = i + 1
        line_tokens = estimate_tokens(line)

        if _is_block_start(line) and current_lines and current_tokens > token_target * 0.3:
            chunk_text = "".join(current_lines)
            if chunk_text.strip():
                chunks.append(Chunk(
                    content=chunk_text,
                    start_line=current_start,
                    end_line=line_num - 1,
                    chunk_index=len(chunks),
                    symbol_name=current_symbol,
                    symbol_type=current_symbol_type,
                ))
            current_lines = [line]
            current_start = line_num
            current_symbol, current_symbol_type = _extract_symbol(line)
            current_tokens = line_tokens
            continue

        if current_tokens + line_tokens > token_target * 1.5 and current_lines:
            chunk_text = "".join(current_lines)
            if chunk_text.strip():
                chunks.append(Chunk(
                    content=chunk_text,
                    start_line=current_start,
                    end_line=line_num - 1,
                    chunk_index=len(chunks),
                    symbol_name=current_symbol,
                    symbol_type=current_symbol_type,
                ))
            current_lines = [line]
            current_start = line_num
            current_symbol = None
            current_symbol_type = None
            current_tokens = line_tokens
            continue

        if not current_lines:
            current_symbol, current_symbol_type = _extract_symbol(line)
        current_lines.append(line)
        current_tokens += line_tokens

    if current_lines:
        chunk_text = "".join(current_lines)
        if chunk_text.strip():
            chunks.append(Chunk(
                content=chunk_text,
                start_line=current_start,
                end_line=len(lines),
                chunk_index=len(chunks),
                symbol_name=current_symbol,
                symbol_type=current_symbol_type,
            ))

    return chunks
