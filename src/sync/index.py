"""Index operations for building document metadata from raw files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from ..utils import read_json, ensure_directory


def build_index(raw_dir: Path, out_file: Path) -> None:
    """Build a readable JSON catalog from raw reMarkable files.

    Args:
        raw_dir: Directory containing raw files from tablet
        out_file: Output JSON file path
    """
    ensure_directory(out_file.parent)

    # Build document list
    documents = []
    collections = []

    for meta_path in sorted(raw_dir.glob("*.metadata")):
        uuid = meta_path.stem
        meta = read_json(meta_path) or {}
        content = read_json(raw_dir / f"{uuid}.content") or {}

        doc_type = meta.get("type", "")
        if doc_type == "CollectionType":
            collections.append({
                "uuid": uuid,
                "name": meta.get("visibleName", "Untitled Collection"),
                "parent": meta.get("parent", ""),
                "modified": int(meta.get("lastModified", 0)) if meta.get("lastModified") else 0,
                "pinned": meta.get("pinned", False),
            })
        else:
            documents.append({
                "uuid": uuid,
                "title": meta.get("visibleName", "Untitled Document"),
                "type": content.get("fileType", "unknown"),
                "parent": meta.get("parent", ""),
                "modified": int(meta.get("lastModified", 0)) if meta.get("lastModified") else 0,
                "pinned": meta.get("pinned", False),
                "pages": content.get("pageCount", 0),
                "is_trashed": meta.get("parent") == "trash",
            })

    # Build organized structure
    catalog = {
        "generated_at": datetime.now().isoformat(),
        "total_documents": len(documents),
        "total_collections": len(collections),
        "documents": documents,
        "collections": collections,
        "stats": {
            "notebooks": len([d for d in documents if d["type"] == "notebook"]),
            "pdfs": len([d for d in documents if d["type"] == "pdf"]),
            "epubs": len([d for d in documents if d["type"] == "epub"]),
            "trashed": len([d for d in documents if d["is_trashed"]]),
            "total_pages": sum(d["pages"] for d in documents),
        }
    }

    # Write JSON
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"Catalog created: {out_file} ({len(documents)} documents, {len(collections)} collections)")


def load_index(index_file: Path) -> Dict[str, Any]:
    """Load catalog from JSON file.

    Args:
        index_file: Path to catalog JSON file

    Returns:
        Catalog dictionary
    """
    if not index_file.exists():
        return {"documents": [], "collections": [], "stats": {}}

    with index_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_document(index_file: Path, uuid: str) -> Dict[str, Any] | None:
    """Find a document by UUID in the catalog.

    Args:
        index_file: Path to catalog JSON file
        uuid: Document UUID to find

    Returns:
        Document metadata or None if not found
    """
    catalog = load_index(index_file)
    for doc in catalog.get("documents", []):
        if doc.get("uuid") == uuid:
            return doc
    return None


def list_documents(index_file: Path, doc_type: str | None = None, include_trashed: bool = False) -> List[Dict[str, Any]]:
    """List documents from the catalog, optionally filtered by type.

    Args:
        index_file: Path to catalog JSON file
        doc_type: Optional document type filter (e.g., "notebook", "pdf", "epub")
        include_trashed: Whether to include trashed documents

    Returns:
        List of document metadata dictionaries
    """
    catalog = load_index(index_file)
    documents = catalog.get("documents", [])

    if not include_trashed:
        documents = [doc for doc in documents if not doc.get("is_trashed", False)]

    if doc_type:
        documents = [doc for doc in documents if doc.get("type") == doc_type]

    return documents


def get_catalog_stats(index_file: Path) -> Dict[str, Any]:
    """Get quick statistics from the catalog.

    Args:
        index_file: Path to catalog JSON file

    Returns:
        Statistics dictionary
    """
    catalog = load_index(index_file)
    return catalog.get("stats", {})


def search_documents(index_file: Path, query: str) -> List[Dict[str, Any]]:
    """Search documents by title.

    Args:
        index_file: Path to catalog JSON file
        query: Search query

    Returns:
        List of matching documents
    """
    documents = list_documents(index_file)
    query_lower = query.lower()

    matches = []
    for doc in documents:
        if query_lower in doc.get("title", "").lower():
            matches.append(doc)

    return sorted(matches, key=lambda d: d.get("modified", 0), reverse=True)
