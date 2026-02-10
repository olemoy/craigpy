"""File filtering — .gitignore, binary detection, chunk threshold estimation."""

from __future__ import annotations

import os
from pathlib import Path

import pathspec

from craigpy.config.settings import RepoConfig

# Extensions we consider text/code — everything else checked via magic bytes
TEXT_EXTENSIONS: set[str] = {
    # Code
    ".py", ".pyw", ".pyx", ".pyi",
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".java", ".kt", ".kts",
    ".go",
    ".rs",
    ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hxx",
    ".cs",
    ".rb", ".erb",
    ".php",
    ".swift",
    ".scala",
    ".lua",
    ".r", ".R",
    ".pl", ".pm",
    ".sh", ".bash", ".zsh", ".fish",
    ".ps1", ".psm1",
    ".bat", ".cmd",
    # Config / Data
    ".json", ".jsonc", ".json5",
    ".yaml", ".yml",
    ".toml",
    ".ini", ".cfg", ".conf",
    ".xml", ".xsl", ".xslt",
    ".csv", ".tsv",
    ".env",
    ".properties",
    # Web
    ".html", ".htm", ".xhtml",
    ".css", ".scss", ".sass", ".less",
    ".svg",
    # Docs
    ".md", ".mdx", ".markdown",
    ".rst", ".txt", ".text",
    ".adoc",
    ".tex", ".latex",
    # SQL
    ".sql",
    # Other
    ".graphql", ".gql",
    ".proto",
    ".tf", ".hcl",
    ".vim",
    ".el", ".lisp", ".clj", ".cljs", ".edn",
    ".ex", ".exs",
    ".erl", ".hrl",
    ".hs",
    ".ml", ".mli",
    ".nim",
    ".zig",
    ".v",
    ".dart",
    ".groovy",
    ".gradle",
    # Build / CI
    "Makefile", "Dockerfile", "Jenkinsfile", "Vagrantfile",
    ".mk",
}

# Magic bytes that indicate binary files
BINARY_MAGIC: list[bytes] = [
    b"\x89PNG",        # PNG
    b"\xff\xd8\xff",   # JPEG
    b"GIF8",           # GIF
    b"PK\x03\x04",    # ZIP / DOCX / XLSX / JAR
    b"PK\x05\x06",    # ZIP empty
    b"\x7fELF",       # ELF binary
    b"\xfe\xed\xfa",  # Mach-O
    b"\xcf\xfa\xed",  # Mach-O (reverse)
    b"\xca\xfe\xba",  # Java class / Mach-O fat
    b"\x00\x00\x01\x00",  # ICO
    b"%PDF",           # PDF
    b"\x1f\x8b",      # gzip
    b"BZ",             # bzip2
    b"\xfd7zXZ",       # xz
    b"Rar!",           # RAR
    b"\x00asm",        # WASM
]


def load_gitignore(repo_path: Path) -> pathspec.PathSpec | None:
    """Load .gitignore patterns from repo root."""
    gitignore = repo_path / ".gitignore"
    if not gitignore.exists():
        return None
    try:
        patterns = gitignore.read_text().splitlines()
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    except OSError:
        return None


def is_binary_file(file_path: Path) -> bool:
    """Check if a file is binary using extension + magic bytes."""
    # Check extension first (fast path)
    suffix = file_path.suffix.lower()
    name = file_path.name
    if suffix in TEXT_EXTENSIONS or name in TEXT_EXTENSIONS:
        return False

    # No recognized text extension — check magic bytes
    try:
        with open(file_path, "rb") as f:
            header = f.read(16)
    except OSError:
        return True  # Can't read → treat as binary

    if not header:
        return False  # Empty file is text

    for magic in BINARY_MAGIC:
        if header.startswith(magic):
            return True

    # Check for null bytes (strong binary indicator)
    if b"\x00" in header:
        return True

    return False


def estimate_chunks(file_size: int, token_target: int) -> int:
    """Estimate the number of chunks a file would produce."""
    chars_per_chunk = token_target * 4  # ~4 chars per token
    return max(1, file_size // chars_per_chunk)


def get_language(file_path: Path) -> str | None:
    """Get language identifier from file extension."""
    ext = file_path.suffix.lower()
    language_map: dict[str, str] = {
        ".py": "python", ".pyw": "python", ".pyx": "python", ".pyi": "python",
        ".ts": "typescript", ".tsx": "typescript",
        ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
        ".java": "java", ".kt": "kotlin", ".kts": "kotlin",
        ".go": "go",
        ".rs": "rust",
        ".c": "c", ".h": "c",
        ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".sql": "sql",
        ".sh": "shell", ".bash": "shell", ".zsh": "shell",
        ".md": "markdown", ".mdx": "markdown",
        ".json": "json", ".yaml": "yaml", ".yml": "yaml",
        ".toml": "toml",
        ".html": "html", ".css": "css",
        ".xml": "xml",
    }
    return language_map.get(ext)


class FileWalker:
    """Walk a repository, respecting .gitignore and filtering binary/large files."""

    def __init__(self, repo_path: Path, config: RepoConfig) -> None:
        self.repo_path = repo_path.resolve()
        self.config = config
        self.gitignore = load_gitignore(self.repo_path)
        self.skipped_files: list[tuple[str, str]] = []  # (rel_path, reason)

    def walk(self) -> list[Path]:
        """Walk repo and return list of indexable file paths (absolute)."""
        result: list[Path] = []

        for root, dirs, files in os.walk(self.repo_path):
            root_path = Path(root)
            rel_root = root_path.relative_to(self.repo_path)

            # Skip hidden directories
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".")
                and d != "node_modules"
                and d != "__pycache__"
                and d != "venv"
                and d != ".venv"
                and d != "dist"
                and d != "build"
                and d != "target"
                and d != ".git"
            ]

            # Apply .gitignore to directories
            if self.gitignore:
                dirs[:] = [
                    d for d in dirs
                    if not self.gitignore.match_file(str(rel_root / d) + "/")
                ]

            for filename in files:
                if filename.startswith("."):
                    continue

                file_path = root_path / filename
                rel_path = str(file_path.relative_to(self.repo_path))

                # .gitignore check
                if self.gitignore and self.gitignore.match_file(rel_path):
                    continue

                # Binary check
                if is_binary_file(file_path):
                    self.skipped_files.append((rel_path, "binary"))
                    continue

                # Size check
                try:
                    size = file_path.stat().st_size
                except OSError:
                    self.skipped_files.append((rel_path, "unreadable"))
                    continue

                if size > self.config.max_file_size_bytes:
                    self.skipped_files.append((rel_path, f"too large ({size} bytes)"))
                    continue

                # Chunk threshold check
                estimated = estimate_chunks(size, self.config.token_target)
                if estimated > self.config.chunk_threshold:
                    self.skipped_files.append(
                        (rel_path, f"estimated {estimated} chunks > threshold {self.config.chunk_threshold}")
                    )
                    continue

                result.append(file_path)

        return result
