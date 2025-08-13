"""Transcription management with cost safeguards and user interaction."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Dict, Tuple, Union

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.prompt import Prompt, Confirm, IntPrompt

from ..config import get_config


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
        """Allow user to select specific documents."""
        self.console.print("\n[bold]Available Documents:[/bold]")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", width=3)
        table.add_column("Name", style="white")
        table.add_column("Pages", justify="center", style="yellow")

        for i, doc in enumerate(documents, 1):
            table.add_row(str(i), doc["name"], str(doc["pages"]))

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

                # Show selection and cost
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

    def _parse_selection(self, selection: str, max_index: int) -> List[int]:
        """Parse user selection string into list of indices."""
        indices = set()

        for part in selection.split(','):
            part = part.strip()
            if '-' in part:
                try:
                    start, end = map(int, part.split('-', 1))
                    if start < 1 or end > max_index or start > end:
                        raise ValueError(f"Range {start}-{end} is invalid")
                    indices.update(range(start, end + 1))
                except ValueError:
                    raise ValueError(f"Invalid range format: {part}")
            else:
                try:
                    idx = int(part)
                    if idx < 1 or idx > max_index:
                        raise ValueError(f"Number {idx} is out of range (1-{max_index})")
                    indices.add(idx)
                except ValueError:
                    raise ValueError(f"Invalid number: {part}")

        return sorted(list(indices))

    def _safe_confirm(self, message: str) -> bool:
        """Safe confirmation that works in both interactive and non-interactive modes."""
        try:
            return Confirm.ask(message, default=False)
        except Exception:
            # In non-interactive mode, default to False for safety
            return False
