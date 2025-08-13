"""Sync operations for pulling files from reMarkable tablet."""

from __future__ import annotations

import os
import stat
import time
from pathlib import Path
from typing import TYPE_CHECKING, Tuple

from ..utils import ensure_directory
from ..errors import SyncError, ConnectionError, AuthenticationError, retry_on_failure

if TYPE_CHECKING:
    import paramiko


class SyncStats:
    """Track sync statistics."""
    def __init__(self):
        self.downloaded = 0
        self.skipped = 0
        self.errors = 0
        self.total_size = 0

    def __str__(self):
        return (f"📥 Downloaded: {self.downloaded}, "
                f"⏭️ Skipped: {self.skipped}, "
                f"❌ Errors: {self.errors}")


def test_connection(host: str, user: str, password: str) -> bool:
    """Test connectivity to the reMarkable tablet.

    Args:
        host: Tablet IP address
        user: SSH username
        password: SSH password

    Returns:
        True if connection successful, False otherwise
    """
    try:
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Try to connect with a short timeout
        client.connect(
            hostname=host,
            username=user,
            password=password,
            timeout=10,
            banner_timeout=10,
            auth_timeout=10
        )

        # Test with a simple command
        stdin, stdout, stderr = client.exec_command('echo "test"', timeout=5)
        result = stdout.read().decode().strip()

        client.close()
        return result == "test"

    except Exception:
        return False


def _sftp_is_dir(sftp: "paramiko.SFTPClient", remote_path: str) -> bool:
    """Check if a remote path is a directory."""
    try:
        st = sftp.stat(remote_path)
        return stat.S_ISDIR(st.st_mode) if st.st_mode is not None else False
    except FileNotFoundError:
        return False
    except Exception as e:
        raise SyncError(f"Cannot check remote path: {remote_path}", str(e))


def _should_download_file(sftp: "paramiko.SFTPClient", remote_path: str, local_path: Path, force: bool = False) -> Tuple[bool, str]:
    """Check if a file should be downloaded based on size and modification time.

    Returns:
        (should_download, reason)
    """
    if force:
        return True, "forced"

    if not local_path.exists():
        return True, "new file"

    try:
        remote_stat = sftp.stat(remote_path)
        local_stat = local_path.stat()

        # Compare file sizes first (quick check)
        if remote_stat.st_size != local_stat.st_size:
            return True, f"size changed ({local_stat.st_size} → {remote_stat.st_size})"

        # Compare modification times (with 1-second tolerance for filesystem differences)
        remote_mtime = remote_stat.st_mtime or 0
        local_mtime = local_stat.st_mtime

        if abs(remote_mtime - local_mtime) > 1:
            return True, f"modified ({time.ctime(local_mtime)} → {time.ctime(remote_mtime)})"

        return False, "unchanged"

    except Exception as e:
        # If we can't check, err on the side of caution and download
        return True, f"check failed: {e}"


def _format_file_size(size_bytes: float) -> str:
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes = size_bytes / 1024.0
    return f"{size_bytes:.1f}TB"


def _download_recursive_sftp(
    sftp: "paramiko.SFTPClient",
    remote_root: str,
    local_root: Path,
    stats: SyncStats,
    force: bool = False,
    verbose: bool = True
) -> None:
    """Recursively download files and directories via SFTP with smart sync."""
    ensure_directory(local_root)

    try:
        entries = sftp.listdir_attr(remote_root)
    except Exception as e:
        stats.errors += 1
        if verbose:
            print(f"❌ Cannot list {remote_root}: {e}")
        return

    for entry in entries:
        remote_item = f"{remote_root.rstrip('/')}/{entry.filename}"
        local_item = local_root / entry.filename

        try:
            if entry.st_mode is not None and stat.S_ISDIR(entry.st_mode):
                # Recursively handle directories
                _download_recursive_sftp(sftp, remote_item, local_item, stats, force, verbose)
            else:
                # Handle files with smart sync
                should_download, reason = _should_download_file(sftp, remote_item, local_item, force)

                if should_download:
                    ensure_directory(local_item.parent)
                    file_size = entry.st_size or 0

                    if verbose and reason != "forced":
                        print(f"📥 {entry.filename} ({reason}, {_format_file_size(file_size)})")
                    elif verbose:
                        print(f"📥 {entry.filename} ({_format_file_size(file_size)})")

                    sftp.get(remote_item, str(local_item))

                    # Preserve remote modification time
                    if entry.st_mtime:
                        os.utime(local_item, (entry.st_mtime, entry.st_mtime))

                    stats.downloaded += 1
                    stats.total_size += file_size
                else:
                    if verbose:
                        print(f"⏭️  {entry.filename} ({reason})")
                    stats.skipped += 1

        except Exception as e:
            stats.errors += 1
            if verbose:
                print(f"❌ Failed to sync {entry.filename}: {e}")


def pull_from_tablet(
    host: str,
    user: str,
    password: str,
    dest: Path,
    remote_path: str = "/home/root/.local/share/remarkable/xochitl/",
    force: bool = False,
    verbose: bool = True
) -> SyncStats:
    """Pull files from reMarkable tablet via SFTP with smart sync.

    Args:
        host: Tablet IP address
        user: SSH username (usually 'root')
        password: SSH password
        dest: Local destination directory
        remote_path: Remote path on tablet (default is xochitl storage)
        force: If True, download all files regardless of local state
        verbose: If True, show detailed progress output

    Returns:
        SyncStats object with download statistics
    """
    try:
        import paramiko
    except ImportError:
        raise SyncError(
            "Required dependency missing: paramiko",
            "Install with: python3 -m pip install --user -r requirements.txt"
        )

    if not password:
        raise AuthenticationError(
            "No password provided",
            "Set RM_PASSWORD environment variable or use --password"
        )

    ensure_directory(dest)
    stats = SyncStats()

    if verbose:
        sync_mode = "🔄 Smart sync" if not force else "🔄 Full sync (forced)"
        print(f"{sync_mode} from {user}@{host}")

    def _do_sync():
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            client.connect(
                hostname=host,
                username=user,
                password=password,
                timeout=20,
                allow_agent=False,
                look_for_keys=False,
            )

            sftp = client.open_sftp()
            try:
                if not _sftp_is_dir(sftp, remote_path):
                    raise SyncError(
                        f"Remote path not found: {remote_path}",
                        "Check that the tablet is accessible and xochitl directory exists"
                    )
                _download_recursive_sftp(sftp, remote_path.rstrip("/"), dest, stats, force, verbose)
            finally:
                sftp.close()
        except paramiko.AuthenticationException:
            raise AuthenticationError("SSH authentication failed", "Check username and password")
        except (paramiko.SSHException, OSError) as e:
            raise ConnectionError(host, str(e))
        finally:
            client.close()

    # Retry sync operation with backoff
    retry_on_failure(_do_sync, max_retries=3, operation="tablet sync")

    if verbose:
        total_size_str = _format_file_size(stats.total_size)
        print(f"✅ Sync complete: {stats} ({total_size_str} downloaded)")

    return stats
