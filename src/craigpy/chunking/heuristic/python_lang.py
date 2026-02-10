"""Heuristic chunker for Python files."""

from __future__ import annotations

import re

from craigpy.chunking.interface import Chunk, estimate_tokens

PY_BLOCK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^(async\s+)?def\s+(\w+)"),
    re.compile(r"^class\s+(\w+)"),
    re.compile(r"^@\w+"),  # Decorator (start of a decorated block)
]


def _is_block_start(line: str) -> bool:
    stripped = line.lstrip()
    # Only match at top-level or class-level (indentation 0 or 4)
    indent = len(line) - len(line.lstrip())
    if indent > 4:
        return False
    return any(p.match(stripped) for p in PY_BLOCK_PATTERNS)


def _extract_symbol(line: str) -> tuple[str | None, str | None]:
    stripped = line.lstrip()
    m = re.match(r"(?:async\s+)?def\s+(\w+)", stripped)
    if m:
        return m.group(1), "function"
    m = re.match(r"class\s+(\w+)", stripped)
    if m:
        return m.group(1), "class"
    return None, None


def chunk_python(
    content: str,
    file_path: str,
    token_target: int,
    overlap_tokens: int,
) -> list[Chunk]:
    """Split Python code into chunks at function/class boundaries."""
    if not content.strip():
        return []

    lines = content.splitlines(keepends=True)
    chunks: list[Chunk] = []

    # Collect import block
    import_lines: list[str] = []
    code_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if (
            stripped.startswith("import ")
            or stripped.startswith("from ")
            or stripped == ""
            or stripped.startswith("#")
            or stripped.startswith('"""')
            or stripped.startswith("'''")
        ):
            import_lines.append(line)
            code_start = i + 1
        else:
            break

    if import_lines and estimate_tokens("".join(import_lines)) > 10:
        chunks.append(Chunk(
            content="".join(import_lines),
            start_line=1,
            end_line=code_start,
            chunk_index=0,
        ))

    # Split at def/class boundaries
    current_lines: list[str] = []
    current_start = code_start + 1
    current_symbol: str | None = None
    current_symbol_type: str | None = None
    current_tokens = 0
    in_decorator_block = False

    for i in range(code_start, len(lines)):
        line = lines[i]
        line_num = i + 1
        line_tokens = estimate_tokens(line)
        stripped = line.lstrip()

        # Track decorator blocks — don't split between decorator and its target
        if stripped.startswith("@") and len(line) - len(stripped) <= 4:
            if not in_decorator_block and current_lines and current_tokens > 0:
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
            else:
                current_lines.append(line)
                current_tokens += line_tokens
            in_decorator_block = True
            continue

        is_def_or_class = bool(
            re.match(r"(?:async\s+)?def\s+\w+", stripped)
            or re.match(r"class\s+\w+", stripped)
        ) and len(line) - len(stripped) <= 4

        if is_def_or_class:
            in_decorator_block = False
            if current_lines and current_tokens > 0 and not any(
                l.lstrip().startswith("@") for l in current_lines
            ):
                # Finalize only if current block isn't just decorators leading to this
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
            else:
                # Decorators are already in current_lines, add def/class to same chunk
                current_symbol, current_symbol_type = _extract_symbol(line)
                current_lines.append(line)
                current_tokens += line_tokens
                continue

        in_decorator_block = False

        # Force split if too large
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
