"""Unified error handling for reM3 - the reMarkable sync tool."""

from __future__ import annotations

import sys
from typing import Optional


class ReMarkableError(Exception):
    """Base exception for all reM3 errors."""

    def __init__(self, message: str, emoji: str = "❌", details: Optional[str] = None):
        self.message = message
        self.emoji = emoji
        self.details = details
        super().__init__(message)

    def __str__(self) -> str:
        """Format error with emoji and optional details."""
        result = f"{self.emoji} {self.message}"
        if self.details:
            result += f"\n   Details: {self.details}"
        return result


class SyncError(ReMarkableError):
    """Errors related to syncing files from tablet."""

    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message, "🔌", details)


class ConnectionError(SyncError):
    """Connection-related sync errors."""

    def __init__(self, host: str, details: Optional[str] = None):
        message = f"Cannot connect to tablet at {host}"
        super().__init__(message, details)


class AuthenticationError(SyncError):
    """Authentication-related sync errors."""

    def __init__(self, message: str = "Authentication failed", details: Optional[str] = None):
        super().__init__(message, details)


class RenderError(ReMarkableError):
    """Errors related to rendering .rm files to images."""

    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message, "🖼️", details)


class TranscribeError(ReMarkableError):
    """Errors related to AI transcription."""

    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message, "🤖", details)


class ConfigError(ReMarkableError):
    """Configuration-related errors."""

    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message, "⚙️", details)


class SetupError(ReMarkableError):
    """Setup and initialization errors."""

    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message, "🔧", details)


# Error handling utilities
def handle_error(error: Exception, operation: str = "operation") -> None:
    """Handle errors with consistent formatting and exit codes."""
    if isinstance(error, ReMarkableError):
        print(error, file=sys.stderr)
    else:
        print(f"❌ Unexpected error during {operation}: {error}", file=sys.stderr)

    # Exit with appropriate code
    if isinstance(error, (ConnectionError, AuthenticationError)):
        sys.exit(2)  # Connection/auth issues
    elif isinstance(error, ConfigError):
        sys.exit(3)  # Configuration issues
    elif isinstance(error, (RenderError, TranscribeError)):
        sys.exit(4)  # Processing issues
    else:
        sys.exit(1)  # General error


def retry_on_failure(func, max_retries: int = 3, operation: str = "operation"):
    """Retry a function with exponential backoff on failure."""
    import time

    for attempt in range(1, max_retries + 1):
        try:
            return func()
        except Exception:
            if attempt == max_retries:
                raise

            wait_time = 2 ** (attempt - 1)  # 1s, 2s, 4s...
            print(f"⚠️  {operation} failed (attempt {attempt}/{max_retries}), retrying in {wait_time}s...")
            time.sleep(wait_time)


def validate_config(config) -> None:
    """Validate configuration and raise ConfigError if invalid."""
    issues = []

    if not config.host:
        issues.append("Host IP is not configured")
    if not config.user:
        issues.append("SSH user is not configured")
    if not config.password:
        ssh_key = config.base_dir.parent / ".ssh" / "id_ed25519"
        if not ssh_key.exists():
            issues.append("Neither password nor SSH key is configured")

    if issues:
        raise ConfigError(
            "Configuration is incomplete",
            details="\n".join(f"   • {issue}" for issue in issues)
        )


def require_openai_key() -> str:
    """Ensure OpenAI API key is available for transcription."""
    import os

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise TranscribeError(
            "OpenAI API key not found",
            details="Set OPENAI_API_KEY environment variable"
        )
    return key


def safe_path(path_str: str) -> bool:
    """Check if a path is safe (no directory traversal attacks)."""
    from pathlib import Path

    try:
        path = Path(path_str).resolve()
        # Basic safety check - no parent directory traversal
        return ".." not in str(path)
    except Exception:
        return False
