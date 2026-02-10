"""Configuration loading with per-repo overrides.

Config file: ~/.config/craigpy/config.json
Data dir:    ~/.local/share/craigpy/
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


CONFIG_DIR = Path.home() / ".config" / "craigpy"
CONFIG_FILE = CONFIG_DIR / "config.json"
DATA_DIR = Path.home() / ".local" / "share" / "craigpy"

DEFAULTS: dict[str, Any] = {
    "token_target": 500,
    "overlap_tokens": 64,
    "chunk_threshold": 200,
    "max_file_size_bytes": 10_485_760,  # 10 MB
}


@dataclass
class RepoConfig:
    """Resolved configuration for a specific repository."""

    token_target: int = DEFAULTS["token_target"]
    overlap_tokens: int = DEFAULTS["overlap_tokens"]
    chunk_threshold: int = DEFAULTS["chunk_threshold"]
    max_file_size_bytes: int = DEFAULTS["max_file_size_bytes"]


@dataclass
class Settings:
    """Global application settings."""

    config_dir: Path = field(default_factory=lambda: CONFIG_DIR)
    data_dir: Path = field(default_factory=lambda: DATA_DIR)
    chroma_path: Path = field(default_factory=lambda: DATA_DIR / "chroma")
    sqlite_path: Path = field(default_factory=lambda: DATA_DIR / "metadata.db")
    defaults: dict[str, Any] = field(default_factory=lambda: dict(DEFAULTS))
    repos: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get_repo_config(self, repo_path: str) -> RepoConfig:
        """Get resolved config for a repo, merging defaults with per-repo overrides."""
        merged = dict(self.defaults)
        overrides = self.repos.get(repo_path, {})
        merged.update(overrides)
        return RepoConfig(
            token_target=merged["token_target"],
            overlap_tokens=merged["overlap_tokens"],
            chunk_threshold=merged["chunk_threshold"],
            max_file_size_bytes=merged["max_file_size_bytes"],
        )

    def ensure_dirs(self) -> None:
        """Create config and data directories if they don't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_path.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    """Load settings from config file, falling back to defaults."""
    settings = Settings()

    if CONFIG_FILE.exists():
        try:
            raw = json.loads(CONFIG_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return settings

        if "data_dir" in raw:
            p = Path(raw["data_dir"]).expanduser()
            settings.data_dir = p
            settings.chroma_path = p / "chroma"
            settings.sqlite_path = p / "metadata.db"

        if "defaults" in raw and isinstance(raw["defaults"], dict):
            for key in DEFAULTS:
                if key in raw["defaults"]:
                    settings.defaults[key] = raw["defaults"][key]

        if "repos" in raw and isinstance(raw["repos"], dict):
            settings.repos = raw["repos"]

    return settings


def save_settings(settings: Settings) -> None:
    """Write current settings to config file."""
    settings.ensure_dirs()
    data: dict[str, Any] = {
        "defaults": settings.defaults,
        "repos": settings.repos,
    }
    if settings.data_dir != DATA_DIR:
        data["data_dir"] = str(settings.data_dir)

    CONFIG_FILE.write_text(json.dumps(data, indent=2) + "\n")
