"""Progress tracking functionality for CLI operations."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


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
                status = "[green]✓[/green]"
            elif i == self.current_step:
                status = "[yellow]🔄[/yellow]"
            else:
                status = "[dim]⏳[/dim]"

            descriptions = [
                "Download files from tablet",
                "Build searchable catalog",
                "Create folder structure",
                "Convert to text (optional)"
            ]
            table.add_row(f"{i+1}. {step}", descriptions[i], status)

        self.console.print(table)

    def start_step(self, step_name: str):
        """Start a new step."""
        if step_name in self.step_names:
            self.current_step = self.step_names.index(step_name)

        self.console.print(f"\n[bold cyan]🚀 Starting: {step_name}[/bold cyan]")

    def complete_step(self, step_name: str):
        """Mark a step as completed."""
        if step_name in self.step_names:
            step_index = self.step_names.index(step_name)
            if step_index == self.current_step:
                self.current_step += 1

        self.console.print(f"[green]✅ Completed: {step_name}[/green]")

    def show_error(self, step_name: str, error: str):
        """Show error for a step."""
        self.console.print(f"[red]❌ Failed: {step_name}[/red]")
        self.console.print(f"[red]Error: {error}[/red]")

    def show_dry_run_header(self):
        """Show dry run header."""
        self.console.print(Panel.fit(
            "[bold yellow]🔍 DRY RUN MODE[/bold yellow]\n"
            "[dim]Showing what would happen without making changes[/dim]",
            border_style="yellow"
        ))

    def show_completion_summary(self, success: bool = True):
        """Show final completion summary."""
        if success:
            self.console.print(Panel.fit(
                "[bold green]✨ All operations completed successfully![/bold green]\n"
                "[dim]Your reMarkable content is now organized and ready[/dim]",
                border_style="green"
            ))
        else:
            self.console.print(Panel.fit(
                "[bold red]❌ Some operations failed[/bold red]\n"
                "[dim]Check the error messages above for details[/dim]",
                border_style="red"
            ))
