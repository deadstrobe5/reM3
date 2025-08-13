#!/usr/bin/env python3
"""reMarkable sync and organize tool - main CLI entry point."""

import argparse
import sys
from pathlib import Path

from src.config import get_config


def cmd_pull(args: argparse.Namespace) -> None:
    """Pull raw files from tablet."""
    from src.sync import pull_from_tablet

    config = get_config()
    host = args.host or config.host
    user = args.user or config.user
    password = args.password or config.password
    dest = Path(args.dest) if args.dest else config.raw_dir

    pull_from_tablet(host, user, password or "", dest)


def cmd_index(args: argparse.Namespace) -> None:
    """Build index from raw files."""
    from src.sync import build_index

    config = get_config()
    raw_dir = Path(args.raw) if args.raw else config.raw_dir
    out_csv = Path(args.out) if args.out else config.index_file

    build_index(raw_dir, out_csv)


def cmd_organize(args: argparse.Namespace) -> None:
    """Organize raw files into collection structure."""
    from src.sync import organize_files

    config = get_config()
    raw_dir = Path(args.raw) if args.raw else config.raw_dir
    dest_root = Path(args.dest) if args.dest else config.organized_dir

    organize_files(
        raw_dir=raw_dir,
        dest_root=dest_root,
        do_copy=bool(args.copy),
        include_trash=bool(args.include_trash),
        clear_dest=bool(args.clear_dest)
    )


def cmd_all(args: argparse.Namespace) -> None:
    """Pull, index, and organize in one go."""
    # Pull
    cmd_pull(argparse.Namespace(
        host=args.host,
        user=args.user,
        password=args.password,
        dest=args.dest
    ))

    # Index
    cmd_index(argparse.Namespace(
        raw=args.dest,
        out=args.index_out
    ))

    # Organize
    cmd_organize(argparse.Namespace(
        raw=args.dest,
        dest=args.organized_dest,
        copy=args.copy,
        include_trash=args.include_trash,
        clear_dest=args.clear_dest
    ))


def cmd_go(args: argparse.Namespace) -> None:
    """One command to rule them all: setup if needed, then sync."""
    from src.setup import interactive

    print("🚀 Starting reMarkable sync…")

    # Check for .env file
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        print("No configuration found. Running first-time setup...")
        interactive()

    # Reload config after potential setup
    from src.config import reset_config
    reset_config()
    config = get_config()

    if not config.password:
        print("❌ No password configured. Run 'python3 main.py setup' to configure.")
        return

    # Ensure directories exist
    config.ensure_directories()

    # Run sync pipeline
    print(f"🔌 Connecting to {config.user}@{config.host} …")
    cmd_pull(argparse.Namespace(host=None, user=None, password=None, dest=None))

    print("📇 Building index…")
    cmd_index(argparse.Namespace(raw=None, out=None))

    print("🗂️  Organizing folders…")
    cmd_organize(argparse.Namespace(
        raw=None,
        dest=None,
        copy=False,
        include_trash=False,
        clear_dest=True
    ))

    print("✅ Sync complete!")


def cmd_setup(args: argparse.Namespace) -> None:
    """Run setup wizard."""
    from src.setup import run_setup, interactive

    if args.host or args.user or args.password or args.gen_key or args.install_key:
        # Non-interactive mode with provided arguments
        run_setup(
            host=args.host or "10.11.99.1",
            user=args.user or "root",
            password=args.password or "",
            gen_key=bool(args.gen_key),
            install_key=bool(args.install_key),
            key_path=Path(args.key_path),
            timeout_s=args.timeout,
        )
    else:
        # Interactive wizard
        interactive()


def cmd_export_text(args: argparse.Namespace) -> None:
    """Export documents to text using OpenAI vision."""
    from src.transcribe import transcribe_document

    config = get_config()

    raw_dir = Path(args.raw) if args.raw else config.raw_dir
    organized_dir = Path(args.organized) if args.organized else config.organized_dir
    out_dir = Path(args.out) if args.out else config.text_dir

    out_dir.mkdir(parents=True, exist_ok=True)

    # Determine which UUIDs to process
    if args.uuid:
        uuids = args.uuid
    else:
        # Default: all document UUIDs present as directories under raw
        uuids = [p.name for p in raw_dir.iterdir() if p.is_dir()]

    # Process documents
    model = args.model or config.openai_model

    for uuid in uuids:
        print(f"Processing {uuid}...")
        try:
            transcribe_document(
                doc_uuid=uuid,
                raw_dir=raw_dir,
                output_dir=out_dir,
                model=model
            )
        except Exception as e:
            print(f"Failed to process {uuid}: {e}")


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    config = get_config()

    p = argparse.ArgumentParser(
        description="reMarkable sync, organize, and export tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 main.py go                    # First-time setup and sync
  python3 main.py pull                  # Pull raw files from tablet
  python3 main.py index                 # Build index from raw files
  python3 main.py organize              # Organize into collections
  python3 main.py export-text --uuid X  # Export specific document to text
        """
    )

    sub = p.add_subparsers(dest="cmd", required=True, help="Command to run")

    # pull command
    sp = sub.add_parser("pull", help="Pull raw files from tablet via SFTP")
    sp.add_argument("--host", help="Tablet IP (default: from config)")
    sp.add_argument("--user", help="SSH user (default: from config)")
    sp.add_argument("--password", help="SSH password (default: from config)")
    sp.add_argument("--dest", help=f"Destination directory (default: {config.raw_dir})")
    sp.set_defaults(func=cmd_pull)

    # index command
    sp = sub.add_parser("index", help="Generate index.csv from raw files")
    sp.add_argument("--raw", help=f"Raw files directory (default: {config.raw_dir})")
    sp.add_argument("--out", help=f"Output CSV file (default: {config.index_file})")
    sp.set_defaults(func=cmd_index)

    # organize command
    sp = sub.add_parser("organize", help="Recreate collections as folders")
    sp.add_argument("--raw", help=f"Raw files directory (default: {config.raw_dir})")
    sp.add_argument("--dest", help=f"Destination directory (default: {config.organized_dir})")
    sp.add_argument("--copy", action="store_true", help="Copy files instead of symlinks")
    sp.add_argument("--include-trash", action="store_true", help="Include trashed items")
    sp.add_argument("--clear-dest", action="store_true", help="Clear destination first")
    sp.set_defaults(func=cmd_organize)

    # all command
    sp = sub.add_parser("all", help="Pull, index, and organize in one go")
    sp.add_argument("--host", help="Tablet IP")
    sp.add_argument("--user", help="SSH user")
    sp.add_argument("--password", help="SSH password")
    sp.add_argument("--dest", help="Raw files destination")
    sp.add_argument("--index-out", help="Index CSV output")
    sp.add_argument("--organized-dest", help="Organized destination")
    sp.add_argument("--copy", action="store_true", help="Copy files instead of symlinks")
    sp.add_argument("--include-trash", action="store_true", help="Include trashed items")
    sp.add_argument("--clear-dest", action="store_true", help="Clear destination first")
    sp.set_defaults(func=cmd_all)

    # go command (simplified all-in-one)
    sp = sub.add_parser("go", help="Do everything: setup (if needed) then sync")
    sp.set_defaults(func=cmd_go)

    # setup command
    sp = sub.add_parser("setup", help="Interactive setup wizard")
    sp.add_argument("--host", help="Tablet IP")
    sp.add_argument("--user", help="SSH user")
    sp.add_argument("--password", help="SSH password")
    sp.add_argument("--gen-key", action="store_true", help="Generate SSH key")
    sp.add_argument("--install-key", action="store_true", help="Install SSH key on tablet")
    sp.add_argument("--key-path", default=str(Path.home() / ".ssh" / "id_ed25519"), help="SSH key path")
    sp.add_argument("--timeout", type=int, default=10, help="Connection timeout")
    sp.set_defaults(func=cmd_setup)

    # export-text command
    sp = sub.add_parser("export-text", help="Export documents to text using AI vision")
    sp.add_argument("--raw", help=f"Raw files directory (default: {config.raw_dir})")
    sp.add_argument("--organized", help=f"Organized directory (default: {config.organized_dir})")
    sp.add_argument("--out", help=f"Output directory (default: {config.text_dir})")
    sp.add_argument("--model", help=f"OpenAI model (default: {config.openai_model})")
    sp.add_argument("--dpi", type=int, help=f"Render DPI (default: {config.render_dpi})")
    sp.add_argument("--image-format", help=f"Image format (default: {config.render_format})")
    sp.add_argument("--image-quality", type=int, help=f"JPEG quality (default: {config.render_quality})")
    sp.add_argument("--workers", type=int, help=f"Parallel workers (default: {config.workers})")
    sp.add_argument("--include-trash", action="store_true", help="Include trashed items")
    sp.add_argument("--uuid", action="append", help="Specific document UUID(s) to export")
    sp.set_defaults(func=cmd_export_text)

    return p


def main() -> int:
    """Main entry point."""
    # Parse arguments and dispatch
    parser = build_parser()
    args = parser.parse_args()

    try:
        # Call the appropriate command function
        args.func(args)
        return 0
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        return 130
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
