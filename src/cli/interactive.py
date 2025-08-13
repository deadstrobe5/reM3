"""Interactive greeting and menu system for enhanced user experience."""

from __future__ import annotations

import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table
from rich.text import Text

from ..config import get_config
from ..errors import handle_error
from .workflows import run_enhanced_workflow, show_transcription_menu, run_enhanced_transcription
from .browse import run_browse_command, show_collection_statistics


class InteractiveGreeting:
    """Interactive greeting and menu system."""

    def __init__(self):
        self.console = Console()
        self.config = get_config()

    def show_welcome(self):
        """Show welcome message and program explanation."""
        welcome_text = Text()
        welcome_text.append("✨ Welcome to ", style="white")
        welcome_text.append("reM3", style="bold blue")
        welcome_text.append(" ✨", style="white")

        explanation = """
[bold]What is reM3?[/bold]
reM3 syncs your reMarkable tablet content to your computer, organizing it exactly like your tablet's folder structure. It can also convert handwritten notes to text using AI.

[bold]What happens during sync?[/bold]
🔌  [cyan]Pull[/cyan] - Downloads new/changed files from your tablet (smart sync)
📇  [cyan]Index[/cyan] - Builds a searchable catalog of your documents
🗂️   [cyan]Organize[/cyan] - Creates readable folder structure matching your tablet
📝  [cyan]Transcribe[/cyan] - Converts handwriting to text (optional, requires OpenAI API key)

[bold]Your data will be saved to:[/bold]
📁  [yellow]{data_dir}[/yellow]
        """.format(data_dir=self.config.base_dir)

        self.console.print(Panel.fit(
            welcome_text,
            border_style="blue"
        ))

        self.console.print(Panel(
            explanation.strip(),
            border_style="cyan",
            title="📖 About reM3"
        ))

    def check_connectivity(self) -> bool:
        """Check if tablet is accessible before proceeding."""
        self.console.print("\n[bold]🔍 Checking tablet connectivity...[/bold]")

        # Check if setup exists first
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        if not env_path.exists():
            self.console.print("[yellow]⚠️  No configuration found. Setup is required first.[/yellow]")
            return False

        try:
            from ..sync.pull import test_connection

            self.console.print(f"[dim]Connecting to {self.config.user}@{self.config.host}...[/dim]")

            if test_connection(self.config.host, self.config.user, self.config.password):
                self.console.print("[green]✅ Tablet is accessible![/green]")
                return True
            else:
                self.console.print("[red]❌ Cannot connect to tablet[/red]")
                self._show_connectivity_help()
                return False

        except Exception as e:
            self.console.print(f"[red]❌ Connection failed: {e}[/red]")
            self._show_connectivity_help()
            return False

    def _show_connectivity_help(self):
        """Show help for connectivity issues."""
        help_text = """
[bold]Connection Troubleshooting:[/bold]

[yellow]1. Check tablet settings:[/yellow]
   •  Settings → General → Storage → USB Connection: [bold]ON[/bold]
   •  Keep tablet awake and unlocked during sync

[yellow]2. Check connection method:[/yellow]
   •  USB: Use default IP 10.11.99.1
   •  Wi-Fi: Use your tablet's Wi-Fi IP address

[yellow]3. Re-run setup if needed:[/yellow]
   •  python3 main.py setup
        """

        self.console.print(Panel(
            help_text.strip(),
            border_style="yellow",
            title="🔧 Troubleshooting"
        ))

    def show_main_menu(self) -> str:
        """Show main menu and get user choice."""
        self.console.print("\n[bold]What would you like to do?[/bold]")

        options = [
            ("sync", "Complete sync workflow", "🚀  Smart sync + organize your files"),
            ("sync-force", "Force full sync", "🔄  Download ALL files (use if sync issues suspected)"),
            ("pull-only", "Download files only", "📥  Just sync files, no organizing"),
            ("browse", "Browse existing documents", "🔍  Search and view your current documents"),
            ("transcribe", "Convert handwriting to text", "📝  AI transcription (requires OpenAI API key)"),
            ("status", "Show current state", "📊  Check what you have locally"),
            ("setup", "Re-run setup wizard", "⚙️   Reconfigure connection settings"),
            ("help", "Show detailed help", "📖  Full documentation and examples"),
            ("quit", "Exit", "👋  Exit the program")
        ]

        table = Table(show_header=False, box=None, pad_edge=False)
        table.add_column("", style="cyan", width=4, justify="right")
        table.add_column("Command", style="bold white", width=28)
        table.add_column("Description", style="white")

        for i, (cmd, title, desc) in enumerate(options, 1):
            table.add_row(f"{i}.", title, desc)

        self.console.print(table)

        while True:
            try:
                choice = IntPrompt.ask(
                    "\nEnter your choice",
                    choices=[str(i) for i in range(1, len(options) + 1)],
                    default=1
                )
                return options[choice - 1][0]
            except KeyboardInterrupt:
                return "quit"
            except Exception:
                self.console.print("[red]Invalid choice. Please try again.[/red]")

    def run_interactive_session(self, auto_run: bool = False) -> int:
        """Run the complete interactive session."""
        if auto_run:
            # Skip greeting and run directly (maintains backward compatibility)
            return run_enhanced_workflow()

        # Show greeting
        self.show_welcome()

        # Check if first-time setup is needed
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        if not env_path.exists():
            self.console.print("\n[yellow]🔧 First-time setup is required[/yellow]")
            if Confirm.ask("Run setup wizard now?", default=True):
                try:
                    from ..setup import interactive
                    interactive()
                    # Reload config after setup
                    from ..config import reset_config
                    reset_config()
                    self.config = get_config()
                    self.console.print("[green]✅ Setup complete![/green]")
                except Exception as e:
                    handle_error(e, "setup")
                    return 1
            else:
                self.console.print("[yellow]Setup is required to continue. Exiting.[/yellow]")
                return 1

        # Main interaction loop
        while True:
            choice = self.show_main_menu()

            if choice == "quit":
                self.console.print("\n[cyan]👋  Thanks for using reM3![/cyan]")
                return 0

            elif choice == "sync":
                if self.check_connectivity():
                    exit_code = self._run_smart_sync()
                    if exit_code != 0:
                        self.console.print(f"[red]❌ Sync failed with exit code {exit_code}[/red]")
                else:
                    if not Confirm.ask("\nTry again?", default=True):
                        continue
                    # Loop back to connectivity check

            elif choice == "sync-force":
                if self.check_connectivity():
                    exit_code = run_enhanced_workflow(force_sync=True)
                    if exit_code != 0:
                        self.console.print(f"[red]❌ Force sync failed with exit code {exit_code}[/red]")
                else:
                    if not Confirm.ask("\nTry again?", default=True):
                        continue

            elif choice == "pull-only":
                if self.check_connectivity():
                    exit_code = self._run_pull_only()
                    if exit_code != 0:
                        self.console.print(f"[red]❌ Pull failed with exit code {exit_code}[/red]")
                else:
                    if not Confirm.ask("\nTry again?", default=True):
                        continue

            elif choice == "browse":
                self._run_browse()

            elif choice == "transcribe":
                self._run_transcription_menu()

            elif choice == "status":
                self._run_status()

            elif choice == "setup":
                try:
                    from ..setup import interactive
                    interactive()
                    # Reload config
                    from ..config import reset_config
                    reset_config()
                    self.config = get_config()
                    self.console.print("[green]✅ Setup updated![/green]")
                except Exception as e:
                    handle_error(e, "setup")

            elif choice == "help":
                from .enhanced_cli import EnhancedCLI
                cli = EnhancedCLI()
                cli.show_quick_help()

            # Show separator and ask to continue for most operations
            if choice in ["browse", "transcribe", "status", "help", "setup", "sync", "sync-force", "pull-only"]:
                self.console.print("\n" + "="*60)
                if not Confirm.ask("Return to main menu?", default=True):
                    self.console.print("\n[cyan]👋  Thanks for using reM3![/cyan]")
                    return 0
                # Continue to next iteration of while loop

    def _run_smart_sync(self) -> int:
        """Run smart sync with conditional index/organize."""
        self.console.print("\n[bold cyan]🚀 Starting Smart Sync Workflow[/bold cyan]")

        # Step 1: Pull with change detection
        self.console.print("\n[bold]Step 1: Syncing files from tablet...[/bold]")
        try:
            from ..sync import pull_from_tablet
            stats = pull_from_tablet(
                self.config.host,
                self.config.user,
                self.config.password,
                self.config.raw_dir,
                force=False,
                verbose=True
            )

            files_changed = stats.downloaded > 0

            if stats.downloaded > 0:
                self.console.print(f"[green]📥 Downloaded {stats.downloaded} new/changed files[/green]")
            if stats.skipped > 0:
                self.console.print(f"[dim]⏭️  Skipped {stats.skipped} unchanged files[/dim]")
            if stats.errors > 0:
                self.console.print(f"[red]❌ {stats.errors} files had errors[/red]")

        except Exception as e:
            handle_error(e, "sync")
            return 1

        # Step 2: Conditional index/organize
        if files_changed:
            self.console.print("\n[green]📊 Files changed - rebuilding index and organizing...[/green]")

            # Index
            self.console.print("\n[bold]Step 2: Building searchable index...[/bold]")
            try:
                from ..sync import build_index
                build_index(self.config.raw_dir, self.config.index_file)
                self.console.print("[green]✅ Index built successfully[/green]")
            except Exception as e:
                handle_error(e, "indexing")
                return 1

            # Organize
            self.console.print("\n[bold]Step 3: Organizing files...[/bold]")
            try:
                from ..sync import organize_files
                organize_files(
                    raw_dir=self.config.raw_dir,
                    dest_root=self.config.organized_dir,
                    do_copy=True,
                    include_trash=False,
                    clear_dest=True
                )
                self.console.print("[green]✅ Files organized successfully[/green]")
            except Exception as e:
                handle_error(e, "organization")
                return 1
        else:
            self.console.print("\n[dim]📊 No file changes detected - skipping index and organize[/dim]")

            # Still offer to rebuild if user wants
            if Confirm.ask("Rebuild index and organize anyway?", default=False):
                self.console.print("\n[bold]Rebuilding index and organizing...[/bold]")
                try:
                    from ..sync import build_index, organize_files
                    build_index(self.config.raw_dir, self.config.index_file)
                    organize_files(
                        raw_dir=self.config.raw_dir,
                        dest_root=self.config.organized_dir,
                        do_copy=True,
                        include_trash=False,
                        clear_dest=True
                    )
                    self.console.print("[green]✅ Rebuild complete[/green]")
                except Exception as e:
                    handle_error(e, "rebuild")
                    return 1

        # Step 3/4: Optional transcription
        self._offer_transcription()
        return 0

    def _run_pull_only(self) -> int:
        """Run pull operation only."""
        self.console.print("\n[bold cyan]📥 Downloading files from tablet...[/bold cyan]")

        try:
            from ..sync import pull_from_tablet
            stats = pull_from_tablet(
                self.config.host,
                self.config.user,
                self.config.password,
                self.config.raw_dir,
                force=False,
                verbose=True
            )

            if stats.downloaded > 0:
                self.console.print(f"[green]📥 Downloaded {stats.downloaded} new/changed files[/green]")
            if stats.skipped > 0:
                self.console.print(f"[dim]⏭️  Skipped {stats.skipped} unchanged files[/dim]")
            if stats.errors > 0:
                self.console.print(f"[red]❌ {stats.errors} files had errors[/red]")

            self.console.print("\n[green]✅ Pull completed![/green]")

            if stats.downloaded > 0:
                if Confirm.ask("Files were downloaded. Build index and organize now?", default=True):
                    return self._run_index_and_organize()

            return 0

        except Exception as e:
            handle_error(e, "pull")
            return 1

    def _run_index_and_organize(self) -> int:
        """Run index and organize operations."""
        try:
            # Index
            self.console.print("\n[bold]Building searchable index...[/bold]")
            from ..sync import build_index
            build_index(self.config.raw_dir, self.config.index_file)
            self.console.print("[green]✅ Index built[/green]")

            # Organize
            self.console.print("\n[bold]Organizing files...[/bold]")
            from ..sync import organize_files
            organize_files(
                raw_dir=self.config.raw_dir,
                dest_root=self.config.organized_dir,
                do_copy=True,
                include_trash=False,
                clear_dest=True
            )
            self.console.print("[green]✅ Files organized[/green]")

            self._offer_transcription()
            return 0

        except Exception as e:
            handle_error(e, "index/organize")
            return 1

    def _run_browse(self) -> int:
        """Run browse command."""
        if not self.config.index_file.exists():
            self.console.print("[yellow]⚠️  No index found. You need to sync first.[/yellow]")
            if Confirm.ask("Run sync now?", default=True):
                if self.check_connectivity():
                    return self._run_smart_sync()
            return 0

        return run_browse_command(
            search=None,
            doc_type=None,
            recent_days=None,
            include_trash=False,
            limit=50
        )

    def _run_transcription_menu(self) -> int:
        """Run transcription menu."""
        if not self.config.index_file.exists():
            self.console.print("[yellow]⚠️  No index found. You need to sync first.[/yellow]")
            if Confirm.ask("Run sync now?", default=True):
                if self.check_connectivity():
                    return self._run_smart_sync()
            return 0

        # Check API key
        if not os.environ.get("OPENAI_API_KEY"):
            self.console.print("\n[yellow]💡 Transcription requires an OpenAI API key[/yellow]")
            self.console.print("[dim]Set it with: export OPENAI_API_KEY=sk-...[/dim]")

            if Confirm.ask("Do you want to set the API key now?", default=False):
                api_key = Prompt.ask("Enter your OpenAI API key", password=True)
                if api_key:
                    os.environ["OPENAI_API_KEY"] = api_key
                    self.console.print("[green]✅ API key set for this session[/green]")
                    self.console.print("[dim]To make it permanent, add to your shell profile:[/dim]")
                    self.console.print(f"[dim]export OPENAI_API_KEY={api_key}[/dim]")
                else:
                    self.console.print("[yellow]No API key provided. Transcription unavailable.[/yellow]")
                    return 0
            else:
                return 0

        # Show transcription menu
        selected_uuids = show_transcription_menu(self.config.index_file)
        if selected_uuids:
            return run_enhanced_transcription(selected_uuids)

        return 0

    def _run_status(self) -> int:
        """Run status command."""
        return show_collection_statistics()

    def _offer_transcription(self):
        """Offer transcription after successful sync."""
        if not os.environ.get("OPENAI_API_KEY"):
            self.console.print("\n[dim]💡 To enable text transcription, set your OpenAI API key:[/dim]")
            self.console.print("[dim]export OPENAI_API_KEY=sk-...[/dim]")
            return

        if not self.config.index_file.exists():
            return

        self.console.print("\n[bold cyan]📝 Text Transcription Available[/bold cyan]")

        if Confirm.ask("Would you like to transcribe handwriting to text?", default=False):
            selected_uuids = show_transcription_menu(self.config.index_file)
            if selected_uuids:
                run_enhanced_transcription(selected_uuids)


def run_interactive_cli(auto_run: bool = False) -> int:
    """Main entry point for interactive CLI."""
    greeting = InteractiveGreeting()
    return greeting.run_interactive_session(auto_run=auto_run)
