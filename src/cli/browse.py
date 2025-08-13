"""Document browsing functionality for CLI."""

from __future__ import annotations

import json
from datetime import datetime
from typing import List, Dict, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..config import get_config


class DocumentBrowser:
    """Handle document browsing and searching functionality."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.config = get_config()

    def browse_documents(
        self,
        search: Optional[str] = None,
        doc_type: Optional[str] = None,
        recent_days: Optional[int] = None,
        include_trash: bool = False,
        limit: int = 50
    ) -> None:
        """Browse documents with filtering options."""
        catalog_file = self.config.base_dir / "data" / "catalog.json"

        if not catalog_file.exists():
            self.console.print("[red]❌ No catalog found. Run sync first to build document index.[/red]")
            return

        # Load catalog
        try:
            with open(catalog_file, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
            documents = catalog.get("documents", [])
        except Exception as e:
            self.console.print(f"[red]❌ Failed to load catalog: {e}[/red]")
            return

        if not documents:
            self.console.print("[yellow]⚠️  No documents found in catalog.[/yellow]")
            return

        # Apply filters
        filtered_docs = self._apply_filters(
            documents, search, doc_type, recent_days, include_trash
        )

        # Show results
        self._display_results(filtered_docs, search, doc_type, recent_days, limit)

    def _apply_filters(
        self,
        documents: List[Dict],
        search: Optional[str],
        doc_type: Optional[str],
        recent_days: Optional[int],
        include_trash: bool
    ) -> List[Dict]:
        """Apply filtering criteria to documents."""
        filtered = documents.copy()

        # Filter by trash status
        if not include_trash:
            filtered = [d for d in filtered if not d.get("is_trashed", False)]

        # Filter by search term
        if search:
            search_lower = search.lower()
            filtered = [
                d for d in filtered
                if search_lower in d.get("title", "").lower()
                or search_lower in d.get("type", "").lower()
            ]

        # Filter by document type
        if doc_type:
            filtered = [d for d in filtered if d.get("type", "").lower() == doc_type.lower()]

        # Filter by recent documents
        if recent_days:
            import time
            cutoff = (time.time() - recent_days * 24 * 60 * 60) * 1000
            filtered = [
                d for d in filtered
                if (d.get("modified", 0) if isinstance(d.get("modified", 0), (int, float)) else 0) > cutoff
            ]

        return filtered

    def _display_results(
        self,
        documents: List[Dict],
        search: Optional[str],
        doc_type: Optional[str],
        recent_days: Optional[int],
        limit: int
    ) -> None:
        """Display filtered results in a formatted table."""
        # Show filter summary
        title_parts = []
        if search:
            title_parts.append(f"Search: '{search}'")
        if doc_type:
            title_parts.append(f"Type: {doc_type}")
        if recent_days:
            title_parts.append(f"Last {recent_days} days")

        if title_parts:
            title = f"🔍 {' | '.join(title_parts)}"
        else:
            title = "📚 All Documents"

        self.console.print(f"\n[bold blue]{title}[/bold blue]")

        if not documents:
            self.console.print("[yellow]No documents match your criteria.[/yellow]")
            return

        # Sort by modification time (newest first)
        sorted_docs = sorted(
            documents,
            key=lambda d: d.get("modified", 0) if isinstance(d.get("modified", 0), (int, float)) else 0,
            reverse=True
        )

        # Limit results
        if len(sorted_docs) > limit:
            sorted_docs = sorted_docs[:limit]
            self.console.print(f"[dim]Showing first {limit} results (of {len(documents)} total)[/dim]")

        # Create results table
        table = Table(show_header=True, header_style="bold magenta", title_style="bold blue")
        table.add_column("📄  Title", style="cyan", no_wrap=False, max_width=35)
        table.add_column("🔖  Type", style="green", width=12)
        table.add_column("📑  Pages", style="yellow", justify="right", width=8)
        table.add_column("📁  Location", style="white", no_wrap=False, max_width=25)
        table.add_column("📅  Modified", style="dim", width=12)

        for doc in sorted_docs:
            title = doc.get("title", "Untitled")
            doc_type = doc.get("type", "unknown")
            pages = str(doc.get("pages", 0))
            parent = doc.get("parent_name", "Root") if doc.get("parent_name") else "Root"

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

            # Add row with proper styling
            if doc.get("is_trashed"):
                title = f"[strikethrough]{title}[/strikethrough]"
                doc_type = f"[strikethrough]{doc_type}[/strikethrough]"

            table.add_row(title, doc_type, pages, parent, modified_str)

        self.console.print(table)

        # Show summary stats
        total_pages = sum(d.get("pages", 0) for d in sorted_docs if isinstance(d.get("pages", 0), int))
        notebooks = len([d for d in sorted_docs if d.get("type") == "notebook"])
        pdfs = len([d for d in sorted_docs if d.get("type") == "pdf"])

        summary = f"📊  Showing {len(sorted_docs)} documents  •  {notebooks} notebooks  •  {pdfs} PDFs  •  {total_pages} total pages"
        self.console.print(f"\n[dim]{summary}[/dim]")

    def show_document_details(self, uuid: str) -> None:
        """Show detailed information about a specific document."""
        catalog_file = self.config.base_dir / "data" / "catalog.json"

        if not catalog_file.exists():
            self.console.print("[red]❌ No catalog found.[/red]")
            return

        try:
            with open(catalog_file, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
            documents = catalog.get("documents", [])
        except Exception as e:
            self.console.print(f"[red]❌ Failed to load catalog: {e}[/red]")
            return

        # Find the document
        doc = None
        for d in documents:
            if d.get("uuid", "").startswith(uuid):
                doc = d
                break

        if not doc:
            self.console.print(f"[red]❌ Document with UUID '{uuid}' not found.[/red]")
            return

        # Show document details
        title = doc.get("title", "Untitled")
        doc_type = doc.get("type", "unknown")
        pages = doc.get("pages", 0)
        parent = doc.get("parent_name", "Root") if doc.get("parent_name") else "Root"

        modified = doc.get("modified", 0)
        if modified and isinstance(modified, (int, float)):
            try:
                dt = datetime.fromtimestamp(modified / 1000)
                modified_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                modified_str = "Unknown"
        else:
            modified_str = "Unknown"

        details = f"""
[bold]Title:[/bold] {title}
[bold]Type:[/bold] {doc_type}
[bold]Pages:[/bold] {pages}
[bold]Location:[/bold] {parent}
[bold]Modified:[/bold] {modified_str}
[bold]UUID:[/bold] {doc.get("uuid", "Unknown")}

[bold]File Paths:[/bold]
📁 Raw: [dim]{self.config.raw_dir / doc.get("uuid", "")}[/dim]
📁 Organized: [dim]{self.config.organized_dir}[/dim]
        """

        self.console.print(Panel(
            details.strip(),
            title="📄 Document Details",
            border_style="cyan"
        ))

    def show_statistics(self) -> None:
        """Show overall statistics about the document collection."""
        import os
        from rich.table import Table

        catalog_file = self.config.base_dir / "data" / "catalog.json"

        if not catalog_file.exists():
            self.console.print("[red]❌ No catalog found. Run sync first to build document index.[/red]")
            self._show_next_steps(has_data=False)
            return

        try:
            with open(catalog_file, 'r', encoding='utf-8') as f:
                catalog = json.load(f)

            documents = catalog.get("documents", [])
            collections = catalog.get("collections", [])

        except Exception as e:
            self.console.print(f"[red]❌ Failed to load catalog: {e}[/red]")
            return

        # Calculate statistics
        active_docs = [d for d in documents if not d.get("is_trashed", False)]
        notebooks = [d for d in active_docs if d.get("type") == "notebook"]
        pdfs = [d for d in active_docs if d.get("type") == "pdf"]

        # Check system status
        raw_exists = self.config.raw_dir.exists()
        organized_exists = self.config.organized_dir.exists()
        text_exists = self.config.text_dir.exists()
        has_api_key = bool(os.environ.get("OPENAI_API_KEY"))

        # Count files
        raw_count = len(list(self.config.raw_dir.glob("*.metadata"))) if raw_exists else 0
        organized_count = len(list(self.config.organized_dir.iterdir())) if organized_exists else 0
        text_count = len(list(self.config.text_dir.glob("*.txt"))) if text_exists else 0

        # Create status table
        table = Table(title="📊  reM3 Status", show_header=True, header_style="bold magenta")
        table.add_column("🔧  Component", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center", width=8)
        table.add_column("Details", style="white")

        # Data status
        table.add_row(
            "Raw Data",
            "[green]✓[/green]" if raw_exists else "[red]✗[/red]",
            f"{raw_count} documents" if raw_exists else "Not synced yet"
        )

        table.add_row(
            "Index/Catalog",
            "[green]✓[/green]",
            f"{len(active_docs)} documents cataloged"
        )

        table.add_row(
            "Organized Files",
            "[green]✓[/green]" if organized_exists else "[red]✗[/red]",
            f"{organized_count} items organized" if organized_exists else "Run organize step"
        )

        table.add_row(
            "Text Exports",
            "[green]✓[/green]" if text_count > 0 else "[yellow]○[/yellow]",
            f"{text_count} documents transcribed" if text_count > 0 else "Optional - requires OpenAI API key"
        )

        # Configuration status
        table.add_row(
            "Tablet Config",
            "[green]✓[/green]" if self.config.host and self.config.user else "[red]✗[/red]",
            f"{self.config.user}@{self.config.host}" if self.config.host else "Run setup wizard"
        )

        table.add_row(
            "OpenAI API",
            "[green]✓[/green]" if has_api_key else "[yellow]○[/yellow]",
            "Ready for transcription" if has_api_key else "Set OPENAI_API_KEY for text export"
        )

        self.console.print(table)

        # Show collection overview
        if documents:
            stats_content = f"""
[bold]📚  Collection Summary[/bold]

[yellow]Documents:[/yellow]
  📄  Total active: [bold]{len(active_docs)}[/bold]
  📔  Notebooks: [bold]{len(notebooks)}[/bold] ({sum(d.get('pages', 0) for d in notebooks)} pages)
  📕  PDFs: [bold]{len(pdfs)}[/bold]
  📁  Collections: [bold]{len(collections)}[/bold]

[yellow]Storage Locations:[/yellow]
  🗄️   Raw: [dim]{self.config.raw_dir}[/dim]
  📂  Organized: [dim]{self.config.organized_dir}[/dim]
  📝  Text: [dim]{self.config.text_dir}[/dim]
            """

            self.console.print(Panel(
                stats_content.strip(),
                border_style="green",
                title="📈  Overview"
            ))

        # Show next steps
        self._show_next_steps(has_data=True, has_api_key=has_api_key, text_count=text_count)

    def _show_next_steps(self, has_data: bool = True, has_api_key: bool = False, text_count: int = 0) -> None:
        """Show recommended next steps based on current state."""
        if not has_data:
            next_steps = """
[bold yellow]🚀  Next Steps:[/bold yellow]
1.  Run the interactive menu: [cyan]python3 main.py[/cyan]
2.  Or sync directly: [cyan]python3 main.py --auto-run[/cyan]
            """
        elif not has_api_key and text_count == 0:
            next_steps = """
[bold yellow]💡  Optional Next Steps:[/bold yellow]
•  Set up transcription: [cyan]export OPENAI_API_KEY=sk-...[/cyan]
•  Test transcription: [cyan]python3 main.py export-text --test-transcribe --force[/cyan]
•  Browse documents: [cyan]python3 main.py browse[/cyan]
            """
        else:
            next_steps = """
[bold green]✅  System Ready![/bold green]
•  Browse documents: [cyan]python3 main.py browse[/cyan]
•  Interactive menu: [cyan]python3 main.py[/cyan]
•  Get help: [cyan]python3 main.py help[/cyan]
            """

        self.console.print(Panel(
            next_steps.strip(),
            border_style="blue",
            title="💡  Recommendations"
        ))


def run_browse_command(
    search: Optional[str] = None,
    doc_type: Optional[str] = None,
    recent_days: Optional[int] = None,
    include_trash: bool = False,
    limit: int = 50
) -> int:
    """Run browse command with given parameters."""
    try:
        browser = DocumentBrowser()
        browser.browse_documents(search, doc_type, recent_days, include_trash, limit)
        return 0
    except Exception as e:
        from ..errors import handle_error
        handle_error(e, "browse")
        return 1


def show_document_details(uuid: str) -> int:
    """Show details for a specific document."""
    try:
        browser = DocumentBrowser()
        browser.show_document_details(uuid)
        return 0
    except Exception as e:
        from ..errors import handle_error
        handle_error(e, "document details")
        return 1


def show_collection_statistics() -> int:
    """Show collection statistics."""
    try:
        browser = DocumentBrowser()
        browser.show_statistics()
        return 0
    except Exception as e:
        from ..errors import handle_error
        handle_error(e, "statistics")
        return 1
