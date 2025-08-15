"""Workflow functions for CLI operations."""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Union

from rich.console import Console

from .enhanced_cli import EnhancedCLI
from .transcription import TranscriptionManager


def create_enhanced_cli(force: bool = False) -> EnhancedCLI:
    """Create an enhanced CLI instance."""
    return EnhancedCLI(force=force)


def run_enhanced_workflow(dry_run: bool = False, force: bool = False, force_sync: bool = False) -> int:
    """Run the enhanced workflow with progress tracking."""
    cli = create_enhanced_cli(force=force)
    return cli.run_complete_workflow(dry_run=dry_run, force_sync=force_sync)


def run_enhanced_transcription(document_uuids: List[str], dry_run: bool = False, force: bool = False, cracked_mode: bool = False) -> int:
    """Run transcription with enhanced UI for specific documents."""
    cli = create_enhanced_cli(force=force)
    return cli.transcribe_specific_documents(document_uuids, dry_run=dry_run, cracked_mode=cracked_mode)


def show_transcription_menu(index_file: Path, force: bool = False) -> Optional[tuple[List[str], bool]]:
    """Show interactive transcription menu and return selected UUIDs and cracked mode flag."""
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
    # Ask about cracked mode first
    console.print("\n[bold]Transcription Mode Selection[/bold]")
    console.print("1. [bold]Standard[/bold] - Single model (faster, cheaper)")
    console.print("2. [bold red]🔥 CRACKED[/bold red] - Multiple models + merge (best quality, more expensive)")

    try:
        mode_choice = input("\nSelect mode [1-2] (1): ").strip()
        if not mode_choice:
            mode_choice = "1"
        cracked_mode = mode_choice == "2"
    except KeyboardInterrupt:
        return None

    if cracked_mode:
        console.print("\n[red]🔥 CRACKED MODE ENABLED[/red]")
        console.print("[dim]Will use multiple models + intelligent merge for best results[/dim]")

    selected_uuids = tm.select_documents(documents, cracked_mode=cracked_mode)
    if selected_uuids:
        return selected_uuids, cracked_mode
    return None


def estimate_transcription_cost(document_uuids: List[str], index_file: Path, model: Optional[str] = None) -> Dict[str, Union[int, float, str, List[str], Dict[str, float]]]:
    """Estimate transcription cost for given documents."""
    from ..config import get_config

    # Use actual config model if not specified
    if model is None:
        config = get_config()
        model = config.openai_model

    total_pages = 0

    try:
        with open(index_file, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
            uuid_to_pages = {doc["uuid"]: doc.get("pages", 0) for doc in catalog.get("documents", [])}

        for uuid in document_uuids:
            total_pages += uuid_to_pages.get(uuid, 0)

    except Exception:
        # Fallback estimate
        total_pages = len(document_uuids) * 5  # Assume 5 pages per document

    tm = TranscriptionManager(Console())
    return tm.estimate_cost(total_pages, model)
