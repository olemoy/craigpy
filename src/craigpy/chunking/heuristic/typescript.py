"""Heuristic chunker for TypeScript and JavaScript files."""

from __future__ import annotations

import re

from craigpy.chunking.interface import Chunk, estimate_tokens

# Patterns that indicate the start of a new logical block
TS_BLOCK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^export\s+(default\s+)?(async\s+)?function\s"),
    re.compile(r"^export\s+(default\s+)?class\s"),
    re.compile(r"^export\s+(default\s+)?interface\s"),
    re.compile(r"^export\s+(default\s+)?type\s"),
    re.compile(r"^export\s+(default\s+)?enum\s"),
    re.compile(r"^export\s+(default\s+)?const\s"),
    re.compile(r"^export\s+(default\s+)?let\s"),
    re.compile(r"^export\s+\{"),
    re.compile(r"^(async\s+)?function\s"),
    re.compile(r"^class\s"),
    re.compile(r"^interface\s"),
    re.compile(r"^type\s+\w+\s*="),
    re.compile(r"^enum\s"),
    re.compile(r"^const\s+\w+\s*=\s*(async\s+)?\("),  # const fn = () =>
    re.compile(r"^const\s+\w+\s*=\s*(async\s+)?function"),
    re.compile(r"^import\s"),
]


def _is_block_start(line: str) -> bool:
    """Check if a line starts a new logical code block."""
    stripped = line.lstrip()
    return any(p.match(stripped) for p in TS_BLOCK_PATTERNS)


def _extract_symbol(line: str) -> tuple[str | None, str | None]:
    """Try to extract symbol name and type from a block-starting line."""
    stripped = line.lstrip()

    # function declarations
    m = re.match(r"(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+(\w+)", stripped)
    if m:
        return m.group(1), "function"

    # class/interface/enum
    for keyword in ("class", "interface", "enum"):
        m = re.match(rf"(?:export\s+(?:default\s+)?)?{keyword}\s+(\w+)", stripped)
        if m:
            return m.group(1), keyword

    # type alias
    m = re.match(r"(?:export\s+(?:default\s+)?)?type\s+(\w+)\s*=", stripped)
    if m:
        return m.group(1), "type"

    # const arrow function
    m = re.match(r"(?:export\s+(?:default\s+)?)?(?:const|let)\s+(\w+)\s*=\s*(?:async\s+)?\(", stripped)
    if m:
        return m.group(1), "function"

    return None, None


def chunk_typescript(
    content: str,
    file_path: str,
    token_target: int,
    overlap_tokens: int,
) -> list[Chunk]:
    """Split TypeScript/JavaScript into chunks at logical boundaries."""
    if not content.strip():
        return []

    lines = content.splitlines(keepends=True)
    chunks: list[Chunk] = []

    # Collect import block as first chunk
    import_lines: list[str] = []
    code_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from ") or stripped == "" or stripped.startswith("//"):
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

    # Split remaining code at block boundaries
    current_lines: list[str] = []
    current_start = code_start + 1
    current_symbol: str | None = None
    current_symbol_type: str | None = None
    current_tokens = 0

    for i in range(code_start, len(lines)):
        line = lines[i]
        line_num = i + 1
        line_tokens = estimate_tokens(line)

        # Check if this line starts a new block
        if _is_block_start(line) and current_lines and current_tokens > 0:
            # Finalize current chunk
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

        # If we're getting too big, force a split
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

            # Overlap
            overlap_lines: list[str] = []
            overlap_tok = 0
            for prev_line in reversed(current_lines):
                lt = estimate_tokens(prev_line)
                if overlap_tok + lt > overlap_tokens:
                    break
                overlap_lines.insert(0, prev_line)
                overlap_tok += lt

            current_lines = overlap_lines + [line]
            current_start = line_num - len(overlap_lines)
            current_symbol = None
            current_symbol_type = None
            current_tokens = overlap_tok + line_tokens
            continue

        if not current_lines:
            current_symbol, current_symbol_type = _extract_symbol(line)

        current_lines.append(line)
        current_tokens += line_tokens

    # Final chunk
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
