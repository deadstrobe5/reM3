"""Sync operations for pulling files from reMarkable tablet."""

from __future__ import annotations

import stat
from pathlib import Path
from typing import TYPE_CHECKING

from ..utils import ensure_directory
from ..errors import SyncError, ConnectionError, AuthenticationError, retry_on_failure

if TYPE_CHECKING:
    import paramiko


def _sftp_is_dir(sftp: "paramiko.SFTPClient", remote_path: str) -> bool:
    """Check if a remote path is a directory."""
    try:
        st = sftp.stat(remote_path)
        return stat.S_ISDIR(st.st_mode) if st.st_mode is not None else False
    except FileNotFoundError:
        return False
    except Exception as e:
        raise SyncError(f"Cannot check remote path: {remote_path}", str(e))


def _download_recursive_sftp(
    sftp: "paramiko.SFTPClient", remote_root: str, local_root: Path
) -> None:
    """Recursively download files and directories via SFTP."""
    ensure_directory(local_root)
    for entry in sftp.listdir_attr(remote_root):
        remote_item = f"{remote_root.rstrip('/')}/{entry.filename}"
        local_item = local_root / entry.filename
        if entry.st_mode is not None and stat.S_ISDIR(entry.st_mode):
            _download_recursive_sftp(sftp, remote_item, local_item)
        else:
            ensure_directory(local_item.parent)
            sftp.get(remote_item, str(local_item))


def pull_from_tablet(
    host: str,
    user: str,
    password: str,
    dest: Path,
    remote_path: str = "/home/root/.local/share/remarkable/xochitl/"
) -> None:
    """Pull files from reMarkable tablet via SFTP.

    Args:
        host: Tablet IP address
        user: SSH username (usually 'root')
        password: SSH password
        dest: Local destination directory
        remote_path: Remote path on tablet (default is xochitl storage)
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
                _download_recursive_sftp(sftp, remote_path.rstrip("/"), dest)
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
    print(f"✅ Pulled raw files to: {dest}")
