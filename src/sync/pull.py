"""Sync operations for pulling files from reMarkable tablet."""

from __future__ import annotations

import stat
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from ..utils import ensure_directory

if TYPE_CHECKING:
    import paramiko


def _sftp_is_dir(sftp: "paramiko.SFTPClient", remote_path: str) -> bool:
    """Check if a remote path is a directory."""
    try:
        st = sftp.stat(remote_path)
        return stat.S_ISDIR(st.st_mode) if st.st_mode is not None else False
    except FileNotFoundError:
        return False


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
        sys.stderr.write(
            "Paramiko is required. Install with: python3 -m pip install --user -r requirements.txt\n"
        )
        raise

    if not password:
        sys.exit("Missing password. Provide --password or set RM_PASSWORD env.")

    ensure_directory(dest)
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
                sys.exit(f"Remote path missing or not a directory: {remote_path}")
            _download_recursive_sftp(sftp, remote_path.rstrip("/"), dest)
        finally:
            sftp.close()
    finally:
        client.close()

    print(f"Pulled raw files to: {dest}")
