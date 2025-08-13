"""Sync operations for pulling and organizing reMarkable content."""

from .pull import pull_from_tablet, SyncStats
from .index import build_index, load_index, find_document, list_documents
from .organize import organize_files

__all__ = [
    'pull_from_tablet',
    'SyncStats',
    'build_index',
    'load_index',
    'find_document',
    'list_documents',
    'organize_files',
]

# Convenience function that does everything
def sync_all(host: str, user: str, password: str, base_dir=None):
    """Complete sync pipeline: pull, index, and organize.

    Args:
        host: Tablet IP address
        user: SSH username
        password: SSH password
        base_dir: Optional base directory (uses config default if None)
    """
    from pathlib import Path
    from ..config import get_config

    config = get_config()
    base = Path(base_dir) if base_dir else config.base_dir

    # Ensure directories exist
    raw_dir = base / "data" / "raw"
    organized_dir = base / "data" / "organized"
    index_file = base / "data" / "index.csv"

    # Run pipeline
    pull_from_tablet(host, user, password, raw_dir)
    build_index(raw_dir, index_file)
    organize_files(raw_dir, organized_dir, clear_dest=True)

    return {
        'raw_dir': raw_dir,
        'organized_dir': organized_dir,
        'index_file': index_file
    }
