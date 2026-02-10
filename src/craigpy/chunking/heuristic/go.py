"""Heuristic chunker for Go files."""

from __future__ import annotations

import re

from craigpy.chunking.interface import Chunk, estimate_tokens

GO_BLOCK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^func\s"),                          # func Name(
    re.compile(r"^func\s*\(\w+\s+\*?\w+\)"),         # func (r *Receiver) Method(
    re.compile(r"^type\s+\w+\s+struct\b"),            # type Foo struct
    re.compile(r"^type\s+\w+\s+interface\b"),         # type Foo interface
    re.compile(r"^type\s+\w+\s"),                     # type Foo = ...
    re.compile(r"^var\s"),                             # var block
    re.compile(r"^const\s"),                           # const block
    re.compile(r"^import\s"),
    re.compile(r"^package\s"),
]


def _is_block_start(line: str) -> bool:
    stripped = line.lstrip()
    indent = len(line) - len(stripped)
    if indent > 0:
        return False  # Go top-level only
    return any(p.match(stripped) for p in GO_BLOCK_PATTERNS)


def _extract_symbol(line: str) -> tuple[str | None, str | None]:
    stripped = line.strip()

    # Method with receiver: func (r *Type) Name(
    m = re.match(r"func\s*\(\w+\s+\*?(\w+)\)\s+(\w+)", stripped)
    if m:
        return f"{m.group(1)}.{m.group(2)}", "method"

    # Regular function: func Name(
    m = re.match(r"func\s+(\w+)", stripped)
    if m:
        return m.group(1), "function"

    # type struct/interface
    m = re.match(r"type\s+(\w+)\s+(struct|interface)", stripped)
    if m:
        return m.group(1), m.group(2)

    # type alias
    m = re.match(r"type\s+(\w+)\s", stripped)
    if m:
        return m.group(1), "type"

    return None, None


def chunk_go(
    content: str,
    file_path: str,
    token_target: int,
    overlap_tokens: int,
) -> list[Chunk]:
    """Split Go code into chunks at func/type boundaries."""
    if not content.strip():
        return []

    lines = content.splitlines(keepends=True)
    chunks: list[Chunk] = []

    # Collect package + imports as header
    header_lines: list[str] = []
    code_start = 0
    in_import_block = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("package "):
            header_lines.append(line)
            code_start = i + 1
            continue
        if stripped == "import (" or stripped.startswith("import "):
            in_import_block = stripped == "import ("
            header_lines.append(line)
            code_start = i + 1
            continue
        if in_import_block:
            header_lines.append(line)
            code_start = i + 1
            if stripped == ")":
                in_import_block = False
            continue
        if stripped == "" or stripped.startswith("//"):
            header_lines.append(line)
            code_start = i + 1
            continue
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

        if _is_block_start(line) and current_lines and current_tokens > 0:
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
