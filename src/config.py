"""Centralized configuration for reM3 - the reMarkable sync tool."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Main configuration for reM3 - the reMarkable sync tool."""

    # Connection settings
    host: str = "10.11.99.1"
    user: str = "root"
    password: str = ""

    # Base directory - all other paths derive from this
    base_dir: Path = Path(__file__).resolve().parent.parent

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
    openai_base_url: Optional[str] = None
    openai_temperature: float = 0.0
    openai_max_retries: int = 5

    # Cracked mode settings (multi-model transcription + merge)
    cracked_mode: bool = False
    cracked_models: Optional[list[str]] = None
    cracked_merge_model: str = "gpt-4o"

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
        """Catalog JSON file path."""
        return self.data_dir / "catalog.json"

    @property
    def text_dir(self) -> Path:
        """Text export directory path."""
        return self.data_dir / "text"

    @property
    def temp_dir(self) -> Path:
        """Temporary files directory path."""
        return self.data_dir / "temp"

    @property
    def images_dir(self) -> Path:
        """Rendered images directory path."""
        return self.data_dir / "images"

    @classmethod
    def load(cls, env_path: Optional[Path] = None) -> Config:
        """Load configuration from environment and .env file.

        Priority: Environment variables > .env file > auto-detected project directory
        """
        config = cls()

        # Auto-detect project directory (where this script is located)
        project_dir = Path(__file__).resolve().parent.parent
        config.base_dir = project_dir

        # Try to find .env file
        if env_path is None:
            # Look for .env in project directory
            env_path = project_dir / ".env"

        # Load .env file if it exists
        env_vars = {}
        if env_path:
            env_path = Path(env_path) if isinstance(env_path, str) else env_path
        if env_path and env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
            except Exception as e:
                print(f"Warning: Could not read .env file {env_path}: {e}")

        # Apply configuration (env vars take precedence)
        config.host = os.environ.get("RM_HOST", env_vars.get("RM_HOST", config.host))
        config.user = os.environ.get("RM_USER", env_vars.get("RM_USER", config.user))
        config.password = os.environ.get("RM_PASSWORD", env_vars.get("RM_PASSWORD", config.password))

        # Base directory override (only if explicitly set)
        if base := os.environ.get("RM_BASE_DIR", env_vars.get("RM_BASE_DIR")):
            config.base_dir = Path(base).expanduser()

        # Other settings
        if dpi := os.environ.get("RM_DPI", env_vars.get("RM_DPI")):
            config.render_dpi = int(dpi)
        if model := os.environ.get("OPENAI_MODEL", env_vars.get("OPENAI_MODEL")):
            config.openai_model = model
        if base_url := os.environ.get("OPENAI_BASE_URL", env_vars.get("OPENAI_BASE_URL")):
            config.openai_base_url = base_url

        # Cracked mode settings
        if cracked := os.environ.get("CRACKED_MODE", env_vars.get("CRACKED_MODE")):
            config.cracked_mode = cracked.lower() in ("true", "1", "yes", "on")
        if merge_model := os.environ.get("CRACKED_MERGE_MODEL", env_vars.get("CRACKED_MERGE_MODEL")):
            config.cracked_merge_model = merge_model
        if cracked_models := os.environ.get("CRACKED_MODELS", env_vars.get("CRACKED_MODELS")):
            config.cracked_models = [m.strip() for m in cracked_models.split(",")]
        elif config.cracked_models is None:
            # Set default cracked models
            config.cracked_models = [
                "gpt-4o",
                "anthropic/claude-3-5-sonnet:beta",
                "qwen/qwen2.5-vl-32b-instruct"
            ]

        if workers := os.environ.get("RM_WORKERS", env_vars.get("RM_WORKERS")):
            config.workers = int(workers)

        return config

    def save_env(self, env_path: Optional[Path] = None) -> None:
        """Save current configuration to .env file."""
        if env_path is None:
            env_path = Path(__file__).resolve().parent.parent / ".env"

        lines = [
            "# reM3 - reMarkable sync configuration",
            f"RM_HOST={self.host}",
            f"RM_USER={self.user}",
            f"RM_PASSWORD={self.password}",
            "",
            "# Optional: Change base directory (default: ~/reM3)",
            f"# RM_BASE_DIR={self.base_dir}",
            "",
            "# Optional: Rendering settings",
            f"# RM_DPI={self.render_dpi}",
            "",
            "# Optional: OpenAI settings",
            f"# OPENAI_MODEL={self.openai_model}",
            "# OPENAI_API_KEY=your_openai_or_openrouter_key_here",
            "",
            "# Optional: Use Qwen via OpenRouter (3 variables needed)",
            "# OPENAI_BASE_URL=https://openrouter.ai/api/v1",
            "# OPENAI_MODEL=qwen/qwen2.5-vl-32b-instruct",
            "",
            "# Optional: Cracked mode (multi-model transcription + merge)",
            f"# CRACKED_MODE={str(self.cracked_mode).lower()}",
            f"# CRACKED_MERGE_MODEL={self.cracked_merge_model}",
            f"# CRACKED_MODELS={','.join(self.cracked_models or [])}",
            "",
            "# Optional: Processing settings",
            f"# RM_WORKERS={self.workers}",
        ]

        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"✅ Configuration saved to {env_path}")

    def ensure_directories(self) -> None:
        """Create all necessary directories."""
        for path in [self.data_dir, self.raw_dir, self.organized_dir, self.text_dir, self.temp_dir, self.images_dir]:
            path.mkdir(parents=True, exist_ok=True)

    def cleanup_temp(self) -> None:
        """Clean up temporary files."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True)


# Global configuration instance
_config: Optional[Config] = None


def get_config(force_reload: bool = False) -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None or force_reload:
        _config = Config.load()
    return _config


def reset_config() -> None:
    """Reset the global configuration (mainly for testing)."""
    global _config
    _config = None


def reload_config() -> Config:
    """Force reload configuration from .env and environment."""
    return get_config(force_reload=True)
