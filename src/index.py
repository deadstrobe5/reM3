"""Index operations for building document metadata from raw files."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Dict, Any

from .utils import read_json, ensure_directory


def build_index(raw_dir: Path, out_csv: Path) -> None:
    """Build an index CSV file from raw reMarkable files.

    Args:
        raw_dir: Directory containing raw files from tablet
        out_csv: Output CSV file path
    """
    ensure_directory(out_csv.parent)

    rows = []
    for meta_path in sorted(raw_dir.glob("*.metadata")):
        uuid = meta_path.stem
        meta = read_json(meta_path) or {}
        content = read_json(raw_dir / f"{uuid}.content") or {}
        rows.append(
            {
                "uuid": uuid,
                "name": meta.get("visibleName", ""),
                "type": meta.get("type", ""),
                "parent": meta.get("parent", ""),
                "modified": meta.get("lastModified", ""),
                "pinned": meta.get("pinned", False),
                "file_type": content.get("fileType", ""),
                "page_count": content.get("pageCount", 0),
            }
        )

    # Write CSV
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    print(f"Index created: {out_csv} ({len(rows)} entries)")


def load_index(index_csv: Path) -> List[Dict[str, Any]]:
    """Load index from CSV file.

    Args:
        index_csv: Path to index CSV file

    Returns:
        List of document metadata dictionaries
    """
    if not index_csv.exists():
        return []

    rows = []
    with index_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric fields
            if "page_count" in row:
                try:
                    row["page_count"] = int(row["page_count"])
                except (ValueError, TypeError):
                    row["page_count"] = 0

            # Convert boolean fields
            if "pinned" in row:
                row["pinned"] = row["pinned"].lower() in ("true", "1", "yes")

            rows.append(row)

    return rows


def find_document(index_csv: Path, uuid: str) -> Dict[str, Any] | None:
    """Find a document by UUID in the index.

    Args:
        index_csv: Path to index CSV file
        uuid: Document UUID to find

    Returns:
        Document metadata or None if not found
    """
    index = load_index(index_csv)
    for doc in index:
        if doc.get("uuid") == uuid:
            return doc
    return None


def list_documents(index_csv: Path, doc_type: str | None = None) -> List[Dict[str, Any]]:
    """List documents from the index, optionally filtered by type.

    Args:
        index_csv: Path to index CSV file
        doc_type: Optional document type filter (e.g., "DocumentType", "CollectionType")

    Returns:
        List of document metadata dictionaries
    """
    index = load_index(index_csv)

    if doc_type:
        return [doc for doc in index if doc.get("type") == doc_type]

    return index
