from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional

import paramiko

from .config import Config


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

# ANSI colors
RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"


def _print_info(msg: str) -> None:
    print(f"{BLUE}ℹ️  {msg}{RESET}")


def _print_ok(msg: str) -> None:
    print(f"{GREEN}✅ {msg}{RESET}")


def _print_warn(msg: str) -> None:
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def _print_err(msg: str) -> None:
    print(f"{RED}❌ {msg}{RESET}")


def write_env(host: str, user: str, password: str) -> Path:
    # Create config with provided values
    config = Config()
    config.host = host
    config.user = user
    config.password = password

    # Save to .env file
    config.save_env(ENV_PATH)
    os.chmod(ENV_PATH, 0o600)

    # Show what was saved
    _print_info(f"RM_HOST={host}")
    _print_info(f"RM_USER={user}")
    _print_info(f"RM_PASSWORD={password if password else '(empty)'}")
    return ENV_PATH


def ensure_ssh_key(key_path: Path) -> Path:
    if key_path.exists():
        _print_ok(f"SSH key exists → {key_path}")
        return key_path
    key_path.parent.mkdir(parents=True, exist_ok=True)
    _print_info("Generating SSH key (ed25519)…")
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-f", str(key_path), "-N", ""], check=True)
    _print_ok(f"Key generated → {key_path}")
    return key_path


def install_public_key(host: str, user: str, pub_key_path: Path, timeout_s: int = 10, password: str = "") -> bool:
    if not pub_key_path.exists():
        _print_err(f"Public key not found: {pub_key_path}")
        return False
    _print_info(f"Installing SSH key on {user}@{host} (timeout {timeout_s}s)…")
    # Prefer Paramiko to avoid interactive prompts
    if password:
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=host,
                username=user,
                password=password,
                timeout=timeout_s,
                allow_agent=False,
                look_for_keys=False,
            )
            try:
                sftp = client.open_sftp()
                try:
                    # Ensure ~/.ssh
                    try:
                        sftp.stat(".ssh")
                    except FileNotFoundError:
                        sftp.mkdir(".ssh", mode=0o700)
                    # Append key
                    pub = pub_key_path.read_bytes()
                    with sftp.open(".ssh/authorized_keys", "a") as f:
                        if not pub.endswith(b"\n"):
                            pub += b"\n"
                        f.write(pub.decode("utf-8"))
                    sftp.chmod(".ssh/authorized_keys", 0o600)
                finally:
                    sftp.close()
            finally:
                client.close()
            _print_ok("SSH key installed")
            return True
        except Exception as exc:
            _print_warn(f"Paramiko install failed: {exc}")
            # fall back to ssh
    # Fallback: attempt ssh with a short timeout (will work only if agent/keys already allow it)
    pub = pub_key_path.read_bytes()
    try:
        proc = subprocess.run(
            [
                "ssh",
                "-o","BatchMode=yes",
                "-o","ConnectTimeout=8",
                "-o","StrictHostKeyChecking=no",
                "-o","UserKnownHostsFile=/dev/null",
                f"{user}@{host}",
                "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys",
            ],
            input=pub,
            timeout=timeout_s,
            check=False,
        )
        ok = proc.returncode == 0
        if ok:
            _print_ok("SSH key installed")
        else:
            _print_err(f"SSH returned code {proc.returncode}")
        return ok
    except subprocess.TimeoutExpired:
        _print_err("SSH key install timed out")
        return False


def run_setup(
    host: str,
    user: str,
    password: str,
    gen_key: bool,
    install_key: bool,
    key_path: Optional[Path] = None,
    timeout_s: int = 10,
) -> None:
    _print_info("Starting reMarkable setup…")
    write_env(host, user, password)
    if gen_key:
        key = ensure_ssh_key(key_path or (Path.home() / ".ssh" / "id_ed25519"))
        if install_key:
            install_public_key(host, user, key.with_suffix(".pub"), timeout_s=timeout_s, password=password)


def interactive():
    print(f"{BLUE}🧩 reMarkable setup wizard{RESET}")

    # Get default config
    default_config = Config()

    host = input(f"Host/IP [{default_config.host}]: ") or default_config.host
    user = input(f"User [{default_config.user}]: ") or default_config.user
    password = input("Password (leave empty if using keys): ")
    write_env(host, user, password)

    if input("Generate SSH key for passwordless login? [y/N]: ").lower().startswith("y"):
        key = ensure_ssh_key(Path.home() / ".ssh" / "id_ed25519")
        if input("Install key on device now? [y/N]: ").lower().startswith("y"):
            install_public_key(host, user, key.with_suffix(".pub"), password=password)


if __name__ == "__main__":
    interactive()
