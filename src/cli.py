"""Enhanced CLI module with progress indicators and transcription safeguards."""

from __future__ import annotations

import os

from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
import csv

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.tree import Tree





from .config import get_config
from .errors import handle_error


class ProgressTracker:
    """Enhanced progress tracking with rich console."""

    def __init__(self):
        self.console = Console()
        self.current_step = 0
        self.total_steps = 4  # pull, index, organize, transcribe
        self.step_names = ["Pull", "Index", "Organize", "Transcribe"]

    def show_welcome(self):
        """Show welcome banner."""
        self.console.print(Panel.fit(
            "[bold blue]reM3 - reMarkable Sync Tool[/bold blue]\n"
            "[dim]Sync, organize, and transcribe your reMarkable content[/dim]",
            border_style="blue"
        ))

    def show_step_overview(self):
        """Show overview of all steps."""
        table = Table(title="📋 Process Overview", show_header=True, header_style="bold magenta")
        table.add_column("Step", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Status", justify="center")

        for i, step in enumerate(self.step_names):
            if i < self.current_step:
                status = "[green]✓ Done[/green]"
            elif i == self.current_step:
                status = "[yellow]→ Current[/yellow]"
            else:
                status = "[dim]⏳ Pending[/dim]"

            descriptions = [
                "Download files from tablet via SFTP",
                "Build metadata index from raw files",
                "Create organized folder structure",
                "Convert handwriting to text (OpenAI)"
            ]

            table.add_row(f"{i+1}. {step}", descriptions[i], status)

        self.console.print(table)
        self.console.print()

    def start_step(self, step_name: str):
        """Start a new step."""
        if step_name in self.step_names:
            self.current_step = self.step_names.index(step_name)

        self.console.print(f"\n[bold cyan]🔄 Step {self.current_step + 1}: {step_name}[/bold cyan]")

    def complete_step(self, step_name: str):
        """Mark step as complete."""
        self.console.print(f"[green]✅ {step_name} complete![/green]")
        if step_name in self.step_names:
            self.current_step = self.step_names.index(step_name) + 1


class TranscriptionManager:
    """Handles transcription with cost safeguards and user interaction."""

    def __init__(self, console: Console, force: bool = False):
        self.console = console
        self.config = get_config()
        self.force = force

    def estimate_cost(self, num_pages: int, model: str = "gpt-4o") -> Dict[str, Union[int, float, str]]:
        """Estimate transcription costs."""
        # OpenAI pricing for vision (approximate)
        costs = {
            "gpt-4o": 0.01,  # $0.01 per image (high detail)
            "gpt-4o-mini": 0.00425,  # $0.00425 per image
        }

        cost_per_page = costs.get(model, 0.01)
        total_cost = num_pages * cost_per_page

        return {
            "pages": num_pages,
            "cost_per_page": cost_per_page,
            "total_cost": total_cost,
            "model": model
        }

    def show_cost_warning(self, estimate: Dict[str, Union[int, float, str]]):
        """Show cost estimation and warning."""
        panel_content = (
            f"[yellow]⚠️  Transcription Cost Estimate[/yellow]\n\n"
            f"📄 Pages to process: [bold]{estimate['pages']}[/bold]\n"
            f"🤖 Model: [bold]{estimate['model']}[/bold]\n"
            f"💰 Cost per page: [bold]${estimate['cost_per_page']:.4f}[/bold]\n"
            f"💸 Total estimated cost: [bold red]${estimate['total_cost']:.2f}[/bold red]\n\n"
            f"[dim]Note: This is an estimate. Actual costs may vary.[/dim]"
        )

        self.console.print(Panel(
            panel_content,
            border_style="yellow",
            title="💸 Cost Warning"
        ))

    def get_documents_summary(self, index_file: Path) -> Tuple[List[Dict], Dict[str, int]]:
        """Get summary of available documents for transcription."""
        documents = []
        stats = {"total": 0, "notebooks": 0, "pages": 0, "collections": 0}

        if not index_file.exists():
            return documents, stats

        with open(index_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats["total"] += 1

                if row["nodeType"] == "DocumentType" and row["fileType"] == "notebook":
                    stats["notebooks"] += 1
                    pages = int(row["pageCount"]) if row["pageCount"].isdigit() else 0
                    stats["pages"] += pages

                    documents.append({
                        "uuid": row["uuid"],
                        "name": row["visibleName"],
                        "pages": pages,
                        "parent": row["parentUuid"]
                    })
                elif row["nodeType"] == "CollectionType":
                    stats["collections"] += 1

        return documents, stats

    def show_documents_tree(self, documents: List[Dict]) -> None:
        """Show available documents in a tree structure."""
        tree = Tree("📚 Available Documents for Transcription")

        # Group by parent for tree structure
        children_by_parent = {}
        root_docs = []

        for doc in documents:
            parent = doc["parent"]
            if not parent or parent == "trash":
                root_docs.append(doc)
            else:
                if parent not in children_by_parent:
                    children_by_parent[parent] = []
                children_by_parent[parent].append(doc)

        def add_doc_to_tree(tree_node, doc):
            pages_text = f"({doc['pages']} page{'s' if doc['pages'] != 1 else ''})"
            node_text = f"[cyan]{doc['name']}[/cyan] [dim]{pages_text}[/dim]"
            doc_node = tree_node.add(node_text)

            # Add children if any
            if doc["uuid"] in children_by_parent:
                for child in children_by_parent[doc["uuid"]]:
                    add_doc_to_tree(doc_node, child)

        # Add root documents
        for doc in root_docs:
            add_doc_to_tree(tree, doc)

        self.console.print(tree)

    def select_documents(self, documents: List[Dict]) -> List[str]:
        """Interactive document selection for transcription."""
        if not documents:
            self.console.print("[red]No notebook documents found for transcription.[/red]")
            return []

        self.console.print("\n[bold]What would you like to transcribe?[/bold]")

        choices = [
            "All documents",
            "Select specific documents",
            "Test with one document only",
            "Cancel"
        ]

        table = Table(show_header=False, box=None)
        table.add_column("Option", style="cyan")
        table.add_column("Description", style="white")

        for i, choice in enumerate(choices, 1):
            if choice == "All documents":
                total_pages = sum(doc["pages"] for doc in documents)
                desc = f"Transcribe all {len(documents)} documents ({total_pages} pages)"
            elif choice == "Test with one document only":
                desc = "Transcribe just 1 document for testing (recommended first time)"
            else:
                desc = ""

            table.add_row(f"{i}.", f"{choice} {desc}")

        self.console.print(table)

        while True:
            choice = IntPrompt.ask("\nEnter your choice", default=3, choices=["1", "2", "3", "4"])

            if choice == 1:  # All documents
                total_pages = sum(doc["pages"] for doc in documents)
                estimate = self.estimate_cost(total_pages)
                self.show_cost_warning(estimate)

                if self.force or self._safe_confirm(f"\nProceed with transcribing all {len(documents)} documents?"):
                    return [doc["uuid"] for doc in documents]
                else:
                    continue

            elif choice == 2:  # Select specific
                return self._select_specific_documents(documents)

            elif choice == 3:  # Test with one
                # Find shortest document for testing
                test_doc = min(documents, key=lambda d: d["pages"])
                self.console.print(f"\n[green]Selected for testing: [bold]{test_doc['name']}[/bold] ({test_doc['pages']} page{'s' if test_doc['pages'] != 1 else ''})[/green]")

                estimate = self.estimate_cost(test_doc["pages"])
                self.show_cost_warning(estimate)

                if self.force or self._safe_confirm("\nProceed with test transcription?"):
                    return [test_doc["uuid"]]
                else:
                    continue

            else:  # Cancel
                return []

    def _select_specific_documents(self, documents: List[Dict]) -> List[str]:
        """Interactive selection of specific documents."""
        self.console.print("\n[bold]Available Documents:[/bold]")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", width=3)
        table.add_column("Name", style="white")
        table.add_column("Pages", style="yellow", justify="right")
        table.add_column("UUID", style="dim", no_wrap=True)

        for i, doc in enumerate(documents, 1):
            table.add_row(
                str(i),
                doc["name"],
                str(doc["pages"]),
                doc["uuid"][:8] + "..."
            )

        self.console.print(table)

        self.console.print("\n[dim]Enter document numbers separated by commas (e.g., 1,3,5)[/dim]")
        self.console.print("[dim]Or enter ranges (e.g., 1-3,5,7-9)[/dim]")

        while True:
            selection = Prompt.ask("Select documents").strip()

            if not selection:
                continue

            try:
                selected_indices = self._parse_selection(selection, len(documents))
                selected_docs = [documents[i-1] for i in selected_indices]

                # Show selection summary
                total_pages = sum(doc["pages"] for doc in selected_docs)
                self.console.print(f"\n[green]Selected {len(selected_docs)} documents ({total_pages} pages):[/green]")

                for doc in selected_docs:
                    self.console.print(f"  • {doc['name']} ({doc['pages']} pages)")

                estimate = self.estimate_cost(total_pages)
                self.show_cost_warning(estimate)

                if self.force or self._safe_confirm("\nProceed with transcription?"):
                    return [doc["uuid"] for doc in selected_docs]
                else:
                    continue

            except ValueError as e:
                self.console.print(f"[red]Invalid selection: {e}[/red]")
                continue

    def _parse_selection(self, selection: str, max_num: int) -> List[int]:
        """Parse user selection string into list of indices."""
        indices = set()

        for part in selection.split(","):
            part = part.strip()

            if "-" in part:
                # Range like "1-3"
                start, end = part.split("-", 1)
                start, end = int(start.strip()), int(end.strip())
                if start < 1 or end > max_num or start > end:
                    raise ValueError(f"Invalid range {part}")
                indices.update(range(start, end + 1))
            else:
                # Single number
                num = int(part)
                if num < 1 or num > max_num:
                    raise ValueError(f"Invalid number {num}")
                indices.add(num)

        return sorted(list(indices))

    def _safe_confirm(self, message: str, default: bool = False) -> bool:
        """Safely ask for confirmation with EOF handling."""
        try:
            return Confirm.ask(message, default=default)
        except (EOFError, KeyboardInterrupt):
            self.console.print(f"\n[yellow]Non-interactive mode detected, using default: {'yes' if default else 'no'}[/yellow]")
            return default


class EnhancedCLI:
    """Enhanced CLI with progress indicators and user interaction."""

    def __init__(self, force: bool = False):
        self.console = Console()
        self.progress_tracker = ProgressTracker()
        self.transcription_manager = TranscriptionManager(self.console, force=force)
        self.config = get_config()
        self.force = force

    def run_complete_workflow(self, dry_run: bool = False, force_sync: bool = False) -> int:
        """Run the complete workflow with enhanced UI."""
        self.progress_tracker.show_welcome()

        if dry_run:
            self.console.print("[yellow]🔍 DRY RUN MODE - No actual changes will be made[/yellow]\n")

        # Check if setup is needed
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if not env_path.exists():
            if not self._run_setup():
                return 1

        # Show step overview
        self.progress_tracker.show_step_overview()

        try:
            # Step 1: Pull
            if not self._run_pull(dry_run, force_sync):
                return 1

            # Step 2: Index
            if not self._run_index(dry_run):
                return 1

            # Step 3: Organize
            if not self._run_organize(dry_run):
                return 1

            # Step 4: Transcription decision point
            if not dry_run:
                return self._handle_transcription_decision()
            else:
                self.console.print("[yellow]🔍 DRY RUN - Transcription step skipped[/yellow]")
                return 0

        except KeyboardInterrupt:
            self.console.print("\n[red]⚠️  Process interrupted by user[/red]")
            return 130
        except Exception as e:
            handle_error(e, "enhanced workflow")
            return 1

    def _run_setup(self) -> bool:
        """Run initial setup."""
        self.console.print("[yellow]🔧 First-time setup required[/yellow]")

        try:
            from .setup import interactive
            interactive()

            # Reload config
            from .config import reset_config
            reset_config()
            self.config = get_config()
            return True

        except Exception as e:
            handle_error(e, "setup")
            return False

    def _run_pull(self, dry_run: bool, force_sync: bool = False) -> bool:
        """Run pull step with progress and smart sync."""
        self.progress_tracker.start_step("Pull")

        sync_mode = "🔄 Smart sync" if not force_sync else "🔄 Full sync (forced)"

        if dry_run:
            self.console.print(f"[yellow]Would run {sync_mode.lower()} from {self.config.user}@{self.config.host}[/yellow]")
            self.progress_tracker.complete_step("Pull")
            return True

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=self.console,
                transient=True
            ) as progress:
                task = progress.add_task(f"🔌 {sync_mode}...", total=None)

                from .sync import pull_from_tablet
                stats = pull_from_tablet(
                    self.config.host,
                    self.config.user,
                    self.config.password,
                    self.config.raw_dir,
                    force=force_sync,
                    verbose=False  # We'll show our own progress
                )

                # Show sync results
                if stats.downloaded > 0 or stats.skipped > 0:
                    result_text = (f"✅ {stats.downloaded} downloaded, "
                                 f"{stats.skipped} skipped")
                    if stats.errors > 0:
                        result_text += f", {stats.errors} errors"
                    progress.update(task, description=result_text)
                else:
                    progress.update(task, description="✅ No changes detected")

                # Show summary in console
                if stats.downloaded > 0:
                    self.console.print(f"[green]📥 Downloaded {stats.downloaded} new/changed files[/green]")
                if stats.skipped > 0:
                    self.console.print(f"[dim]⏭️  Skipped {stats.skipped} unchanged files[/dim]")
                if stats.errors > 0:
                    self.console.print(f"[red]❌ {stats.errors} files had errors[/red]")

            self.progress_tracker.complete_step("Pull")
            return True

        except Exception as e:
            handle_error(e, "pull")
            return False

    def _run_index(self, dry_run: bool) -> bool:
        """Run index step with progress."""
        self.progress_tracker.start_step("Index")

        if dry_run:
            self.console.print(f"[yellow]Would build index from {self.config.raw_dir}[/yellow]")
            self.progress_tracker.complete_step("Index")
            return True

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=self.console,
                transient=True
            ) as progress:
                task = progress.add_task("📇 Building document index...", total=None)

                from .sync import build_index
                build_index(self.config.raw_dir, self.config.index_file)

                progress.update(task, description="✅ Index created")

            self.progress_tracker.complete_step("Index")
            return True

        except Exception as e:
            handle_error(e, "index building")
            return False

    def _run_organize(self, dry_run: bool) -> bool:
        """Run organize step with progress."""
        self.progress_tracker.start_step("Organize")

        if dry_run:
            self.console.print(f"[yellow]Would organize files to {self.config.organized_dir}[/yellow]")
            self.progress_tracker.complete_step("Organize")
            return True

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=self.console,
                transient=True
            ) as progress:
                task = progress.add_task("🗂️  Organizing into collections...", total=None)

                from .sync import organize_files
                organize_files(
                    raw_dir=self.config.raw_dir,
                    dest_root=self.config.organized_dir,
                    do_copy=False,
                    include_trash=False,
                    clear_dest=True
                )

                progress.update(task, description="✅ Files organized")

            self.progress_tracker.complete_step("Organize")
            return True

        except Exception as e:
            handle_error(e, "organization")
            return False

    def _handle_transcription_decision(self) -> int:
        """Handle the transcription decision point with cost safeguards."""
        self.console.print("\n" + "="*60)
        self.console.print("[bold green]🎉 Sync Complete![/bold green]")

        # Get document summary
        documents, stats = self.transcription_manager.get_documents_summary(self.config.index_file)

        # Show summary
        panel_content = (
            f"📊 [bold]Extraction Summary[/bold]\n\n"
            f"📄 Total items: [bold]{stats['total']}[/bold]\n"
            f"📔 Notebooks: [bold]{stats['notebooks']}[/bold]\n"
            f"📑 Total pages: [bold]{stats['pages']}[/bold]\n"
            f"📁 Collections: [bold]{stats['collections']}[/bold]"
        )

        self.console.print(Panel(
            panel_content,
            border_style="green",
            title="📋 Summary"
        ))

        if stats["notebooks"] == 0:
            self.console.print("[yellow]No notebook documents found for transcription.[/yellow]")
            return 0

        # Check for OpenAI API key
        if not os.environ.get("OPENAI_API_KEY"):
            self.console.print("\n[yellow]💡 To enable text transcription, set your OpenAI API key:[/yellow]")
            self.console.print("[dim]export OPENAI_API_KEY=sk-...[/dim]")

            if not self.force and not self._safe_confirm("\nContinue without transcription?", default=True):
                return 1
            return 0

        # Show transcription options
        self.console.print("\n[bold cyan]📝 Text Transcription Available[/bold cyan]")
        self.console.print(f"Found [bold]{stats['notebooks']}[/bold] notebook documents with [bold]{stats['pages']}[/bold] total pages.")

        # Show documents tree
        self.transcription_manager.show_documents_tree(documents)

        # Get user selection
        selected_uuids = self.transcription_manager.select_documents(documents)

        if not selected_uuids:
            self.console.print("[cyan]👋 Transcription skipped. Your files are organized and ready![/cyan]")
            return 0

        # Run transcription
        return self._run_transcription(selected_uuids)

    def _run_transcription(self, document_uuids: List[str]) -> int:
        """Run transcription with detailed progress tracking."""
        self.progress_tracker.start_step("Transcribe")

        self.console.print(f"\n[bold]🤖 Starting transcription of {len(document_uuids)} document(s)...[/bold]")

        try:
            self.config.text_dir.mkdir(parents=True, exist_ok=True)

            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                "[progress.percentage]{task.percentage:>3.0f}%",
                "•",
                TextColumn("{task.completed}/{task.total} docs"),
                "•",
                TimeElapsedColumn(),
                "•",
                TimeRemainingColumn(),
                console=self.console
            ) as progress:

                main_task = progress.add_task(
                    "📝 Transcribing documents...",
                    total=len(document_uuids)
                )

                successes = 0
                failures = 0

                for i, uuid in enumerate(document_uuids, 1):
                    # Get document name for better progress display
                    doc_name = self._get_document_name(uuid)
                    progress.update(main_task, description=f"📝 Transcribing: {doc_name}")

                    doc_task = None
                    try:
                        # Add subtask for this document
                        doc_task = progress.add_task(
                            f"  Processing {doc_name}...",
                            total=None
                        )

                        from .transcribe import transcribe_document
                        result = transcribe_document(
                            doc_uuid=uuid,
                            raw_dir=self.config.raw_dir,
                            output_dir=self.config.text_dir,
                            model=self.config.openai_model
                        )

                        if result:
                            successes += 1
                            progress.update(doc_task, description=f"  ✅ {doc_name}")
                        else:
                            failures += 1
                            progress.update(doc_task, description=f"  ❌ {doc_name} (no content)")

                        progress.remove_task(doc_task)

                    except Exception as e:
                        failures += 1
                        if doc_task is not None:
                            try:
                                progress.update(doc_task, description=f"  ❌ {doc_name} (error)")
                                progress.remove_task(doc_task)
                            except:
                                pass
                        self.console.print(f"[red]Failed to transcribe {doc_name}: {e}[/red]")

                    progress.update(main_task, advance=1)

            # Show final results
            self._show_transcription_results(successes, failures)
            self.progress_tracker.complete_step("Transcribe")

            return 0 if failures == 0 else 1

        except Exception as e:
            handle_error(e, "transcription")
            return 1

    def _get_document_name(self, uuid: str) -> str:
        """Get document name from UUID."""
        try:
            with open(self.config.index_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["uuid"] == uuid:
                        return row["visibleName"]
        except:
            pass
        return f"Document {uuid[:8]}..."

    def _show_transcription_results(self, successes: int, failures: int):
        """Show transcription results summary."""
        self.console.print("\n" + "="*50)

        if successes > 0 and failures == 0:
            panel_content = (
                f"[bold green]🎉 Transcription Complete![/bold green]\n\n"
                f"✅ Successfully transcribed: [bold]{successes}[/bold] document{'s' if successes != 1 else ''}\n"
                f"📁 Text files saved to: [bold]{self.config.text_dir}[/bold]"
            )
            border_style = "green"
        elif successes > 0 and failures > 0:
            panel_content = (
                f"[bold yellow]⚠️  Transcription Partially Complete[/bold yellow]\n\n"
                f"✅ Successful: [bold]{successes}[/bold]\n"
                f"❌ Failed: [bold]{failures}[/bold]\n"
                f"📁 Text files saved to: [bold]{self.config.text_dir}[/bold]"
            )
            border_style = "yellow"
        else:
            panel_content = (
                "[bold red]❌ Transcription Failed[/bold red]\n\n"
                "No documents were successfully transcribed.\n"
                "Check error messages above for details."
            )
            border_style = "red"

        self.console.print(Panel(
            panel_content,
            border_style=border_style,
            title="📝 Transcription Results"
        ))

    def transcribe_specific_documents(self, document_uuids: List[str], dry_run: bool = False) -> int:
        """Transcribe specific documents (for direct CLI usage)."""
        if dry_run:
            self.console.print(f"[yellow]🔍 DRY RUN - Would transcribe {len(document_uuids)} document(s)[/yellow]")
            return 0

        # Check API key
        if not os.environ.get("OPENAI_API_KEY"):
            self.console.print("[red]❌ OPENAI_API_KEY environment variable not set[/red]")
            return 1

        # Get documents info for cost estimation
        documents = []
        total_pages = 0

        try:
            with open(self.config.index_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                uuid_to_doc = {row["uuid"]: row for row in reader}

            for uuid in document_uuids:
                if uuid in uuid_to_doc:
                    doc = uuid_to_doc[uuid]
                    pages = int(doc["pageCount"]) if doc["pageCount"].isdigit() else 0
                    documents.append({
                        "uuid": uuid,
                        "name": doc["visibleName"],
                        "pages": pages
                    })
                    total_pages += pages
                else:
                    self.console.print(f"[yellow]⚠️  Document {uuid} not found in index[/yellow]")

        except Exception as e:
            self.console.print(f"[red]Failed to read index: {e}[/red]")
            return 1

        if not documents:
            self.console.print("[red]No valid documents found for transcription[/red]")
            return 1

        # Show cost estimate and confirm
        estimate = self.transcription_manager.estimate_cost(total_pages)
        self.transcription_manager.show_cost_warning(estimate)

        if not self.force and not self._safe_confirm("\nProceed with transcription?"):
            self.console.print("[cyan]👋 Transcription cancelled by user[/cyan]")
            return 0

        # Run transcription
        return self._run_transcription(document_uuids)

    def show_quick_help(self):
        """Show quick help for the enhanced CLI."""
        help_text = """
[bold blue]reM3 - Quick Help[/bold blue]

[bold]Basic Usage:[/bold]
  python3 main.py                              # Complete workflow with smart sync
  python3 main.py --dry-run                    # Preview all operations
  python3 main.py --force-sync                 # Force full sync (all files)

[bold]Smart Sync Features:[/bold]
  🚀 Only downloads new/changed files (saves time and bandwidth)
  📊 Shows detailed sync statistics (downloaded/skipped/errors)
  🔍 Compares file sizes and modification times
  ⏭️  Skips unchanged files automatically

[bold]Transcription Commands:[/bold]
  python3 main.py export-text --test-transcribe --force    # Test with 1 small document
  python3 main.py export-text --uuid <uuid> --force        # Transcribe specific document
  python3 main.py export-text                              # Interactive document selection

[bold]Sync Commands:[/bold]
  python3 main.py pull               # Smart sync only (new/changed files)
  python3 main.py pull --force-sync  # Force full sync (all files)
  python3 main.py sync               # Smart sync + index + organize
  python3 main.py setup              # Re-run setup wizard

[bold]First Time Setup:[/bold]
1. Enable USB connection in tablet settings
2. Run: python3 main.py
3. Follow the setup wizard
4. Test transcription with: python3 main.py export-text --test-transcribe --force

[bold]Cost Safeguards:[/bold]
• 💸 Cost estimates shown before transcription
• 🧪 Test mode available for safe experimentation
• ⚠️  Confirmation prompts for expensive operations
• 🔍 Use --dry-run to preview without spending money

[bold]Tips:[/bold]
• Smart sync automatically detects changes - much faster on subsequent runs
• Use --force-sync only when you suspect sync issues
• Use --force to skip confirmation prompts for automation
• Keep tablet awake during sync operations
• Text transcription requires OPENAI_API_KEY environment variable
        """

        self.console.print(Panel(
            help_text.strip(),
            border_style="blue",
            title="📖 Help"
        ))

    def _safe_confirm(self, message: str, default: bool = False) -> bool:
        """Safely ask for confirmation with EOF handling."""
        try:
            return Confirm.ask(message, default=default)
        except (EOFError, KeyboardInterrupt):
            self.console.print(f"\n[yellow]Non-interactive mode detected, using default: {'yes' if default else 'no'}[/yellow]")
            return default


def create_enhanced_cli(force: bool = False) -> EnhancedCLI:
    """Create an enhanced CLI instance."""
    return EnhancedCLI(force=force)


def run_enhanced_workflow(dry_run: bool = False, force: bool = False, force_sync: bool = False) -> int:
    """Run the enhanced workflow with progress tracking."""
    cli = create_enhanced_cli(force=force)
    return cli.run_complete_workflow(dry_run=dry_run, force_sync=force_sync)


def run_enhanced_transcription(document_uuids: List[str], dry_run: bool = False, force: bool = False) -> int:
    """Run transcription with enhanced UI for specific documents."""
    cli = create_enhanced_cli(force=force)
    return cli.transcribe_specific_documents(document_uuids, dry_run=dry_run)


def show_transcription_menu(index_file: Path, force: bool = False) -> Optional[List[str]]:
    """Show interactive transcription menu and return selected UUIDs."""
    console = Console()
    tm = TranscriptionManager(console, force=force)

    documents, stats = tm.get_documents_summary(index_file)

    if stats["notebooks"] == 0:
        console.print("[yellow]No notebook documents found for transcription.[/yellow]")
        return None

    # Check for OpenAI API key
    if not os.environ.get("OPENAI_API_KEY"):
        console.print("\n[yellow]💡 To enable text transcription, set your OpenAI API key:[/yellow]")
        console.print("[dim]export OPENAI_API_KEY=sk-...[/dim]")
        return None

    tm.show_documents_tree(documents)
    return tm.select_documents(documents)


def estimate_transcription_cost(document_uuids: List[str], index_file: Path, model: str = "gpt-4o") -> Dict[str, Union[int, float, str]]:
    """Estimate transcription cost for given documents."""
    total_pages = 0

    try:
        with open(index_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            uuid_to_pages = {row["uuid"]: int(row["pageCount"]) if row["pageCount"].isdigit() else 0 for row in reader}

        for uuid in document_uuids:
            total_pages += uuid_to_pages.get(uuid, 0)

    except Exception:
        # Fallback estimate
        total_pages = len(document_uuids) * 5  # Assume 5 pages per document

    tm = TranscriptionManager(Console())
    return tm.estimate_cost(total_pages, model)
