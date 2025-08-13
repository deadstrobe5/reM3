"""Centralized configuration for the reMarkable sync tool."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Main configuration for the reMarkable sync tool."""

    # Connection settings
    host: str = "10.11.99.1"
    user: str = "root"
    password: str = ""

    # Base directory - all other paths derive from this
    base_dir: Path = Path.home() / "remarkable-sync"

    # Remote settings
    remote_path: str = "/home/root/.local/share/remarkable/xochitl/"
    ssh_timeout: int = 20

    # Rendering settings
    render_dpi: int = 200
    render_format: str = "jpeg"
    render_quality: int = 95
    stroke_width_scale: float = 2.0
    target_height: int = 2000

    # OpenAI settings
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.0
    openai_max_retries: int = 5

    # Processing settings
    workers: int = 3
    include_trash: bool = False

    @property
    def data_dir(self) -> Path:
        """Data directory path."""
        return self.base_dir / "data"

    @property
    def raw_dir(self) -> Path:
        """Raw files directory path."""
        return self.data_dir / "raw"

    @property
    def organized_dir(self) -> Path:
        """Organized files directory path."""
        return self.data_dir / "organized"

    @property
    def index_file(self) -> Path:
        """Index CSV file path."""
        return self.data_dir / "index.csv"

    @property
    def text_dir(self) -> Path:
        """Text export directory path."""
        return self.data_dir / "text" / "openai"

    @classmethod
    def load(cls, env_path: Optional[Path] = None) -> Config:
        """Load configuration from environment and .env file.

        Priority: Environment variables > .env file > defaults
        """
        config = cls()

        # Try to find .env file
        if env_path is None:
            # Look for .env in script directory
            env_path = Path(__file__).resolve().parent.parent / ".env"

        # Load .env file if it exists
        env_vars = {}
        if env_path and env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip().strip('"').strip("'")

        # Apply configuration (env vars take precedence)
        config.host = os.environ.get("RM_HOST", env_vars.get("RM_HOST", config.host))
        config.user = os.environ.get("RM_USER", env_vars.get("RM_USER", config.user))
        config.password = os.environ.get("RM_PASSWORD", env_vars.get("RM_PASSWORD", config.password))

        # Base directory override
        if base := os.environ.get("RM_BASE_DIR", env_vars.get("RM_BASE_DIR")):
            config.base_dir = Path(base).expanduser()

        # Other settings
        if dpi := os.environ.get("RM_DPI", env_vars.get("RM_DPI")):
            config.render_dpi = int(dpi)
        if model := os.environ.get("OPENAI_MODEL", env_vars.get("OPENAI_MODEL")):
            config.openai_model = model
        if workers := os.environ.get("RM_WORKERS", env_vars.get("RM_WORKERS")):
            config.workers = int(workers)

        return config

    def save_env(self, env_path: Optional[Path] = None) -> None:
        """Save current configuration to .env file."""
        if env_path is None:
            env_path = Path(__file__).resolve().parent.parent / ".env"

        lines = [
            "# reMarkable sync configuration",
            f"RM_HOST={self.host}",
            f"RM_USER={self.user}",
            f"RM_PASSWORD={self.password}",
            "",
            "# Optional: Change base directory (default: ~/remarkable-sync)",
            f"# RM_BASE_DIR={self.base_dir}",
            "",
            "# Optional: Rendering settings",
            f"# RM_DPI={self.render_dpi}",
            "",
            "# Optional: OpenAI settings",
            f"# OPENAI_MODEL={self.openai_model}",
            f"# RM_WORKERS={self.workers}",
        ]

        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"✅ Configuration saved to {env_path}")

    def ensure_directories(self) -> None:
        """Create all necessary directories."""
        for path in [self.data_dir, self.raw_dir, self.organized_dir, self.text_dir]:
            path.mkdir(parents=True, exist_ok=True)


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def reset_config() -> None:
    """Reset the global configuration (mainly for testing)."""
    global _config
    _config = None
