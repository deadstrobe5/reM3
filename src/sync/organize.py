"""Clean organize operations for creating readable folder structure."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from ..utils import read_json, ensure_directory, sanitize_name


def organize_files(
    raw_dir: Path,
    dest_root: Path,
    do_copy: bool = True,
    include_trash: bool = False,
    clear_dest: bool = True
) -> Dict[str, str]:
    """Organize raw files into a clean folder structure.

    Args:
        raw_dir: Directory containing raw files from tablet
        dest_root: Destination root directory for organized structure
        do_copy: If True, copy files instead of creating symlinks
        include_trash: If True, include trashed items
        clear_dest: If True, clear destination directory first

    Returns:
        Dictionary mapping UUIDs to their organized paths
    """
    if clear_dest and dest_root.exists():
        shutil.rmtree(dest_root)
    ensure_directory(dest_root)

    # Load the catalog
    catalog_file = raw_dir.parent / "catalog.json"
    if catalog_file.exists():
        with open(catalog_file, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
        documents = catalog.get("documents", [])
        collections = catalog.get("collections", [])
    else:
        # Fallback: build from raw files
        documents, collections = _build_simple_catalog(raw_dir)

    # Build collection hierarchy map
    collection_map = {}
    collection_paths = {}
    for collection in collections:
        collection_map[collection["uuid"]] = collection

    # Resolve collection paths
    def resolve_collection_path(collection_uuid):
        path = []
        current = collection_uuid
        visited = set()

        while current and current in collection_map and current not in visited:
            visited.add(current)
            col = collection_map[current]
            if col.get("parent") == "trash":
                return None  # Skip trashed collections
            path.insert(0, sanitize_name(col["name"]))
            current = col.get("parent", "")

        return path

    # Create collection directories
    for collection in collections:
        if collection.get("parent") == "trash" and not include_trash:
            continue

        col_path = resolve_collection_path(collection["uuid"])
        if col_path:
            full_path = dest_root
            for segment in col_path:
                full_path = full_path / segment
            ensure_directory(full_path)
            collection_paths[collection["uuid"]] = full_path

    # Organize documents
    organized_paths = {}
    for doc in documents:
        if doc.get("is_trashed") and not include_trash:
            continue

        uuid = doc["uuid"]
        title = doc["title"]
        doc_type = doc.get("type", "unknown")
        parent = doc.get("parent", "")

        # Find source file
        src_path = _find_source_file(raw_dir, uuid, doc_type)
        if not src_path:
            continue

        # Determine destination based on parent
        if parent and parent in collection_paths:
            # Document belongs to a collection
            dest_dir = collection_paths[parent]
        elif parent == "trash":
            if not include_trash:
                continue
            dest_dir = dest_root / "trash"
            ensure_directory(dest_dir)
        else:
            # Root level document
            dest_dir = dest_root

        # Create final destination path
        clean_title = sanitize_name(title)
        if doc_type == "notebook":
            dest_path = dest_dir / clean_title
        else:
            ext = ".pdf" if doc_type == "pdf" else ".epub" if doc_type == "epub" else ""
            dest_path = dest_dir / f"{clean_title}{ext}"

        # Copy the file/directory
        try:
            if src_path.is_dir():
                if dest_path.exists():
                    shutil.rmtree(dest_path)
                shutil.copytree(src_path, dest_path)
            else:
                if dest_path.exists():
                    dest_path.unlink()
                shutil.copy2(src_path, dest_path)
            organized_paths[uuid] = str(dest_path)
        except Exception as e:
            print(f"Warning: Failed to organize {title}: {e}")

    # Summary
    doc_count = len([doc for doc in documents if not doc.get("is_trashed", False)])
    organized_count = len(organized_paths)

    print(f"Organized {organized_count}/{doc_count} documents")
    print(f"Destination: {dest_root}")
    print("(Files were copied for clean access)")

    return organized_paths


def _build_simple_catalog(raw_dir: Path) -> tuple[List[Dict], List[Dict]]:
    """Build simple catalog from raw files as fallback."""

    documents = []
    collections = []

    for meta_path in raw_dir.glob("*.metadata"):
        uuid = meta_path.stem
        meta = read_json(meta_path) or {}
        content = read_json(raw_dir / f"{uuid}.content") or {}

        if meta.get("type") == "CollectionType":
            collections.append({
                "uuid": uuid,
                "name": meta.get("visibleName", "Untitled Collection"),
                "is_trashed": meta.get("parent") == "trash"
            })
        else:
            documents.append({
                "uuid": uuid,
                "title": meta.get("visibleName", "Untitled Document"),
                "type": content.get("fileType", "unknown"),
                "pages": content.get("pageCount", 0),
                "is_trashed": meta.get("parent") == "trash"
            })

    return documents, collections


def _find_source_file(raw_dir: Path, uuid: str, doc_type: str) -> Optional[Path]:
    """Find the source file for a document."""
    if doc_type == "notebook":
        # Notebooks are directories
        notebook_dir = raw_dir / uuid
        if notebook_dir.is_dir():
            return notebook_dir
    else:
        # PDFs and EPUBs are files
        for ext in [".pdf", ".epub"]:
            file_path = raw_dir / f"{uuid}{ext}"
            if file_path.exists():
                return file_path

    return None
