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
            catalog = json.load(f)
            uuid_to_pages = {doc["uuid"]: doc.get("pages", 0) for doc in catalog.get("documents", [])}

        for uuid in document_uuids:
            total_pages += uuid_to_pages.get(uuid, 0)

    except Exception:
        # Fallback estimate
        total_pages = len(document_uuids) * 5  # Assume 5 pages per document

    tm = TranscriptionManager(Console())
    return tm.estimate_cost(total_pages, model)
