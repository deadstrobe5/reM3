#!/usr/bin/env python3
"""reM3 - reMarkable sync and organize tool - main CLI entry point."""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List

from src.config import get_config
from src.cli import run_enhanced_workflow, run_enhanced_transcription, show_transcription_menu


def cmd_pull(args: argparse.Namespace) -> None:
    """Pull raw files from tablet with smart sync."""
    from src.sync import pull_from_tablet
    from src.errors import handle_error

    config = get_config()
    host = args.host or config.host
    user = args.user or config.user
    password = args.password or config.password
    dest = Path(args.dest) if args.dest else config.raw_dir
    force_sync = getattr(args, 'force_sync', False)

    # Check for dry run
    if getattr(args, 'dry_run', False):
        sync_mode = "full sync" if force_sync else "smart sync"
        print(f"🔍 DRY RUN - would run {sync_mode} from {user}@{host} to {dest}")
        return

    try:
        stats = pull_from_tablet(host, user, password or "", dest, force=force_sync)
        print(f"📊 Sync stats: {stats}")
    except Exception as e:
        handle_error(e, "pull")


def cmd_index(args: argparse.Namespace) -> None:
    """Build index from raw files."""
    from src.sync import build_index
    from src.errors import handle_error

    config = get_config()
    raw_dir = Path(args.raw) if args.raw else config.raw_dir
    out_csv = Path(args.out) if args.out else config.index_file

    # Check for dry run
    if getattr(args, 'dry_run', False):
        print(f"🔍 DRY RUN - would build index from {raw_dir} to {out_csv}")
        return

    try:
        build_index(raw_dir, out_csv)
    except Exception as e:
        handle_error(e, "index building")


def cmd_organize(args: argparse.Namespace) -> None:
    """Organize raw files into collection structure."""
    from src.sync import organize_files
    from src.errors import handle_error

    config = get_config()
    raw_dir = Path(args.raw) if args.raw else config.raw_dir
    dest_root = Path(args.dest) if args.dest else config.organized_dir

    # Check for dry run
    if getattr(args, 'dry_run', False):
        print(f"🔍 DRY RUN - would organize {raw_dir} to {dest_root}")
        print(f"   Copy: {bool(args.copy)}")
        print(f"   Include trash: {bool(args.include_trash)}")
        print(f"   Clear destination: {bool(args.clear_dest)}")
        return

    try:
        organize_files(
            raw_dir=raw_dir,
            dest_root=dest_root,
            do_copy=bool(args.copy),
            include_trash=bool(args.include_trash),
            clear_dest=bool(args.clear_dest)
        )
    except Exception as e:
        handle_error(e, "organization")


def cmd_sync(args: argparse.Namespace) -> None:
    """Complete sync pipeline: pull, index, and organize."""
    from src.errors import handle_error, validate_config

    config = get_config()

    # Validate configuration first
    try:
        validate_config(config)
    except Exception as e:
        handle_error(e, "configuration validation")
        return

    # Use provided args or config defaults
    host = args.host or config.host
    user = args.user or config.user
    password = args.password or config.password
    raw_dir = Path(args.dest) if hasattr(args, 'dest') and args.dest else config.raw_dir
    organized_dir = Path(args.organized_dest) if hasattr(args, 'organized_dest') and args.organized_dest else config.organized_dir
    index_out = Path(args.index_out) if hasattr(args, 'index_out') and args.index_out else config.index_file

    # Check for dry run and force sync
    dry_run = getattr(args, 'dry_run', False)
    force_sync = getattr(args, 'force_sync', False)

    if dry_run:
        sync_mode = "full sync" if force_sync else "smart sync"
        print(f"🔍 DRY RUN - would run {sync_mode} to: {raw_dir}")
        print(f"   Host: {host}")
        print(f"   User: {user}")
        print(f"   Raw: {raw_dir}")
        print(f"   Organized: {organized_dir}")
        print(f"   Index: {index_out}")
        return

    try:
        # Pull
        sync_mode = "🔄 Smart sync" if not force_sync else "🔄 Full sync"
        print(f"🔌 {sync_mode} from {user}@{host}...")
        cmd_pull(argparse.Namespace(host=host, user=user, password=password, dest=str(raw_dir), force_sync=force_sync, dry_run=False))

        # Index
        print("📇 Building index...")
        cmd_index(argparse.Namespace(raw=str(raw_dir), out=str(index_out), dry_run=False))

        # Organize
        print("🗂️  Organizing folders...")
        cmd_organize(argparse.Namespace(
            raw=str(raw_dir),
            dest=str(organized_dir),
            copy=getattr(args, 'copy', False),
            include_trash=getattr(args, 'include_trash', False),
            clear_dest=True,
            dry_run=False
        ))

        print("✅ Sync complete!")

    except Exception as e:
        handle_error(e, "sync pipeline")


def cmd_help(args: argparse.Namespace) -> None:
    """Show detailed help."""
    from src.cli import create_enhanced_cli
    cli = create_enhanced_cli()
    cli.show_quick_help()


def cmd_go(args: argparse.Namespace) -> None:
    """One command to rule them all: setup if needed, then sync with enhanced UI."""
    dry_run = getattr(args, 'dry_run', False)
    force_sync = getattr(args, 'force_sync', False)

    # Use enhanced workflow with progress tracking and transcription safeguards
    exit_code = run_enhanced_workflow(dry_run=dry_run, force_sync=force_sync)
    if exit_code != 0:
        sys.exit(exit_code)


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
    """Export documents to text using OpenAI vision with enhanced UI."""
    from src.cli import estimate_transcription_cost, TranscriptionManager
    from rich.console import Console

    config = get_config()
    console = Console()
    dry_run = getattr(args, 'dry_run', False)

    # Determine which UUIDs to process
    if args.uuid:
        uuids = args.uuid
    elif getattr(args, 'test_transcribe', False):
        # Test mode: automatically select a small document
        console.print("[cyan]🧪 Test mode: selecting a small document for testing[/cyan]")
        uuids = _select_test_document(config.index_file, console)
        if not uuids:
            console.print("[red]❌ No suitable test document found[/red]")
            return

        if dry_run:
            # Show enhanced dry-run preview
            console.print("[yellow]🔍 DRY RUN - Transcription Preview[/yellow]\n")

            try:
                estimate = estimate_transcription_cost(uuids, config.index_file, args.model or config.openai_model)
                tm = TranscriptionManager(console)
                tm.show_cost_warning(estimate)

                console.print("\n[dim]Documents to transcribe:[/dim]")
                for uuid in uuids:
                    doc_name = _get_document_name_from_index(uuid, config.index_file)
                    console.print(f"  • {doc_name} ({uuid[:8]}...)")

            except Exception as e:
                console.print(f"[yellow]Could not load cost estimate: {e}[/yellow]")

            console.print("\n[green]✓ Ready for transcription (remove --dry-run to execute)[/green]")
            return
    else:
        # Interactive selection
        uuids = show_transcription_menu(config.index_file)
        if not uuids:
            return

    # Get force flag
    force = getattr(args, 'force', False)

    # Use enhanced transcription with progress tracking and cost safeguards
    exit_code = run_enhanced_transcription(uuids, dry_run=dry_run, force=force)
    if exit_code != 0:
        sys.exit(exit_code)


def _get_document_name_from_index(uuid: str, index_file: Path) -> str:
    """Helper to get document name from index file."""
    try:
        import csv
        with open(index_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["uuid"] == uuid:
                    return row["visibleName"]
    except:
        pass
    return f"Document {uuid[:8]}..."


def _select_test_document(index_file: Path, console) -> List[str]:
    """Select a small document for testing transcription."""
    import csv

    try:
        with open(index_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            documents = []
            for row in reader:
                if (row["nodeType"] == "DocumentType" and
                    row["fileType"] == "notebook" and
                    row["parentUuid"] != "trash" and
                    row["pageCount"].isdigit()):
                    pages = int(row["pageCount"])
                    if pages > 0 and pages <= 3:  # Small documents only
                        documents.append({
                            "uuid": row["uuid"],
                            "name": row["visibleName"],
                            "pages": pages
                        })

            if documents:
                # Select the smallest document
                test_doc = min(documents, key=lambda d: d["pages"])
                console.print(f"[green]📄 Selected: {test_doc['name']} ({test_doc['pages']} page{'s' if test_doc['pages'] != 1 else ''})[/green]")
                return [test_doc["uuid"]]

    except Exception as e:
        console.print(f"[red]Error selecting test document: {e}[/red]")

    return []


def cmd_status(args: argparse.Namespace) -> None:
    """Show current data state and sync information."""
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    import os

    console = Console()
    config = get_config()

    # Check data directories
    raw_exists = config.raw_dir.exists()
    organized_exists = config.organized_dir.exists()
    index_exists = config.index_file.exists()
    text_exists = config.text_dir.exists()

    # Count files if directories exist
    raw_count = len(list(config.raw_dir.glob("*.metadata"))) if raw_exists else 0
    organized_count = len(list(config.organized_dir.iterdir())) if organized_exists else 0
    text_count = len(list(config.text_dir.glob("*.txt"))) if text_exists else 0

    # Connection status
    has_api_key = bool(os.environ.get("OPENAI_API_KEY"))

    # Create status table
    table = Table(title="📊 reM3 Status", show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Details", style="white")

    # Data directories
    table.add_row(
        "Raw Data",
        "[green]✓[/green]" if raw_exists else "[red]✗[/red]",
        f"{raw_count} documents" if raw_exists else "Not synced yet"
    )

    table.add_row(
        "Index",
        "[green]✓[/green]" if index_exists else "[red]✗[/red]",
        f"{config.index_file}" if index_exists else "Run 'python3 main.py index'"
    )

    table.add_row(
        "Organized",
        "[green]✓[/green]" if organized_exists else "[red]✗[/red]",
        f"{organized_count} items" if organized_exists else "Run 'python3 main.py organize'"
    )

    table.add_row(
        "Text Export",
        "[green]✓[/green]" if text_count > 0 else "[yellow]○[/yellow]",
        f"{text_count} transcribed" if text_count > 0 else "Optional - requires OpenAI API key"
    )

    # Configuration
    table.add_row(
        "Tablet Config",
        "[green]✓[/green]" if config.host and config.user else "[red]✗[/red]",
        f"{config.user}@{config.host}" if config.host else "Run 'python3 main.py setup'"
    )

    table.add_row(
        "OpenAI API",
        "[green]✓[/green]" if has_api_key else "[yellow]○[/yellow]",
        "Ready for transcription" if has_api_key else "Set OPENAI_API_KEY for text export"
    )

    console.print(table)

    # Show paths
    paths_info = (
        f"[bold]📁 Data Locations:[/bold]\n"
        f"Base: [cyan]{config.base_dir}[/cyan]\n"
        f"Raw: [cyan]{config.raw_dir}[/cyan]\n"
        f"Organized: [cyan]{config.organized_dir}[/cyan]\n"
        f"Text: [cyan]{config.text_dir}[/cyan]"
    )

    console.print("\n")
    console.print(Panel(paths_info, border_style="blue", title="Configuration"))

    # Show next steps
    if not raw_exists:
        console.print("\n[yellow]🚀 Next steps: Run 'python3 main.py' to sync your tablet[/yellow]")
    elif not has_api_key and text_count == 0:
        console.print("\n[yellow]💡 Want text transcription? Set OPENAI_API_KEY and run 'python3 main.py export-text --test-transcribe --force'[/yellow]")
    else:
        console.print("\n[green]✅ All set! Use 'python3 main.py --dry-run' to preview operations or 'python3 main.py help' for more options[/green]")


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    config = get_config()

    p = argparse.ArgumentParser(
        description="reM3 - reMarkable sync, organize, and transcribe tool with enhanced UI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 main.py                              # Complete workflow with smart sync
  python3 main.py --dry-run                    # Preview all operations
  python3 main.py --force-sync                 # Force full sync (all files)
  python3 main.py export-text --test-transcribe --force  # Test transcription (1 doc)
  python3 main.py export-text --uuid ABC123 --force      # Transcribe specific document
  python3 main.py pull                         # Smart sync only (new/changed files)
  python3 main.py help                         # Show detailed help

Features:
  ✨ Visual progress indicators and step-by-step workflow
  🚀 Smart incremental sync (only downloads new/changed files)
  💸 Cost estimation and safeguards for AI transcription
  🧪 Test mode for trying transcription with small documents
  📊 Interactive document selection with tree view
  🔍 Comprehensive dry-run mode for all operations
        """
    )

    # Add global dry-run flag
    p.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")

    sub = p.add_subparsers(dest="cmd", required=False, help="Command to run")

    # help command
    sp = sub.add_parser("help", help="Show detailed help and usage examples")
    sp.set_defaults(func=cmd_help)

    # status command
    sp = sub.add_parser("status", help="Show current data state and sync information")
    sp.set_defaults(func=cmd_status)

    # go command (default - setup if needed, then sync everything)
    sp = sub.add_parser("go", help="Do everything: setup (if needed) then sync")
    sp.add_argument("--force-sync", action="store_true", help="Force full sync (download all files)")
    sp.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    sp.set_defaults(func=cmd_go)

    # sync command (pull + index + organize)
    sp = sub.add_parser("sync", help="Pull, index, and organize in one go")
    sp.add_argument("--host", help="Tablet IP (default: from config)")
    sp.add_argument("--user", help="SSH user (default: from config)")
    sp.add_argument("--password", help="SSH password (default: from config)")
    sp.add_argument("--dest", help="Raw files destination")
    sp.add_argument("--index-out", help="Index CSV output")
    sp.add_argument("--organized-dest", help="Organized destination")
    sp.add_argument("--copy", action="store_true", help="Copy files instead of symlinks")
    sp.add_argument("--include-trash", action="store_true", help="Include trashed items")
    sp.add_argument("--force-sync", action="store_true", help="Force full sync (download all files)")
    sp.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    sp.set_defaults(func=cmd_sync)

    # pull command
    sp = sub.add_parser("pull", help="Pull raw files from tablet via SFTP with smart sync")
    sp.add_argument("--host", help="Tablet IP (default: from config)")
    sp.add_argument("--user", help="SSH user (default: from config)")
    sp.add_argument("--password", help="SSH password (default: from config)")
    sp.add_argument("--dest", help=f"Destination directory (default: {config.raw_dir})")
    sp.add_argument("--force-sync", action="store_true", help="Force full sync (download all files)")
    sp.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    sp.set_defaults(func=cmd_pull)

    # index command
    sp = sub.add_parser("index", help="Generate index.csv from raw files")
    sp.add_argument("--raw", help=f"Raw files directory (default: {config.raw_dir})")
    sp.add_argument("--out", help=f"Output CSV file (default: {config.index_file})")
    sp.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    sp.set_defaults(func=cmd_index)

    # organize command
    sp = sub.add_parser("organize", help="Recreate collections as folders")
    sp.add_argument("--raw", help=f"Raw files directory (default: {config.raw_dir})")
    sp.add_argument("--dest", help=f"Destination directory (default: {config.organized_dir})")
    sp.add_argument("--copy", action="store_true", help="Copy files instead of symlinks")
    sp.add_argument("--include-trash", action="store_true", help="Include trashed items")
    sp.add_argument("--clear-dest", action="store_true", help="Clear destination first")
    sp.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    sp.set_defaults(func=cmd_organize)

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
    sp.add_argument("--test-transcribe", action="store_true", help="Test mode: automatically select a small document for transcription")
    sp.add_argument("--force", action="store_true", help="Skip confirmation prompts")
    sp.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    sp.set_defaults(func=cmd_export_text)

    # browse command
    sp = sub.add_parser("browse", help="Browse document catalog in a readable format")
    sp.add_argument("--search", help="Search documents by title")
    sp.add_argument("--type", choices=["notebook", "pdf", "epub"], help="Filter by document type")
    sp.add_argument("--recent", type=int, default=7, help="Show documents from last N days")
    sp.add_argument("--include-trash", action="store_true", help="Include trashed documents")
    sp.set_defaults(func=cmd_browse)

    return p


def main() -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()

    # Default to 'go' command if no command specified
    if not args.cmd:
        args.cmd = "go"
        args.func = cmd_go

    try:
        # Call the appropriate command function
        args.func(args)
        return 0
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        return 130
    except Exception as e:
        from src.errors import handle_error
        handle_error(e, f"command '{args.cmd}'")
        return 1




def cmd_browse(args: argparse.Namespace) -> None:
    """Browse document catalog in a readable format."""
    from rich.console import Console
    from rich.table import Table
    from src.sync.index import load_index, search_documents, list_documents

    console = Console()
    config = get_config()
    catalog_file = config.index_file

    if not catalog_file.exists():
        console.print("[red]No catalog found. Run 'python3 main.py index' first.[/red]")
        return

    # Load catalog
    catalog = load_index(catalog_file)
    documents = catalog.get("documents", [])

    if args.search:
        documents = search_documents(catalog_file, args.search)
        console.print(f"[blue]🔍 Search results for '{args.search}':[/blue]")
    elif args.type:
        documents = list_documents(catalog_file, args.type, args.include_trash)
        console.print(f"[blue]📄 {args.type.title()} documents:[/blue]")
    elif args.recent:
        # Filter recent documents
        import time
        cutoff = (time.time() - args.recent * 24 * 60 * 60) * 1000
        documents = [d for d in documents if (d.get("modified", 0) if isinstance(d.get("modified", 0), (int, float)) else 0) > cutoff]
        console.print(f"[blue]⏰ Documents from last {args.recent} days:[/blue]")
    else:
        if not args.include_trash:
            documents = [d for d in documents if not d.get("is_trashed", False)]
        console.print("[blue]📚 All documents:[/blue]")

    if not documents:
        console.print("[yellow]No documents found.[/yellow]")
        return

    # Create table
    table = Table()
    table.add_column("Title", style="cyan", no_wrap=False)
    table.add_column("Type", style="green")
    table.add_column("Pages", style="blue", justify="right")
    table.add_column("Modified", style="dim")

    for doc in sorted(documents, key=lambda d: d.get("modified", 0) if isinstance(d.get("modified", 0), (int, float)) else 0, reverse=True)[:50]:
        title = doc.get("title", "Untitled")
        doc_type = doc.get("type", "unknown")
        pages = str(doc.get("pages", 0))

        # Format modified date
        modified = doc.get("modified", 0)
        if modified and isinstance(modified, (int, float)):
            try:
                dt = datetime.fromtimestamp(modified / 1000)
                modified_str = dt.strftime("%Y-%m-%d")
            except:
                modified_str = "Unknown"
        else:
            modified_str = "Unknown"

        # Add trash indicator
        if doc.get("is_trashed"):
            title = f"🗑️ {title}"

        table.add_row(title, doc_type, pages, modified_str)

    console.print(table)

    # Show stats
    stats = catalog.get("stats", {})
    if stats:
        console.print(f"\n[dim]📊 Total: {stats.get('notebooks', 0)} notebooks, "
                     f"{stats.get('pdfs', 0)} PDFs, {stats.get('epubs', 0)} books, "
                     f"{stats.get('total_pages', 0)} pages[/dim]")


if __name__ == "__main__":
    sys.exit(main())
