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

    # Load catalog data
    documents, collections = _load_catalog_data(raw_dir)

    # Build collection paths
    collection_paths = _build_collection_paths(collections, dest_root, include_trash)

    # Organize documents into their destinations
    organized_paths = _organize_documents(documents, raw_dir, dest_root, collection_paths, include_trash)

    # Print summary
    _print_organization_summary(documents, organized_paths, dest_root)

    return organized_paths


def _load_catalog_data(raw_dir: Path) -> tuple[List[Dict], List[Dict]]:
    """Load catalog data from catalog.json or build from raw files."""
    catalog_file = raw_dir.parent / "catalog.json"
    if catalog_file.exists():
        with open(catalog_file, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
        documents = catalog.get("documents", [])
        collections = catalog.get("collections", [])
    else:
        # Fallback: build from raw files
        documents, collections = _build_simple_catalog(raw_dir)
    return documents, collections


def _build_collection_paths(collections: List[Dict], dest_root: Path, include_trash: bool) -> Dict[str, Path]:
    """Build collection hierarchy and create directory structure."""
    collection_map = {collection["uuid"]: collection for collection in collections}
    collection_paths = {}

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

    return collection_paths


def _organize_documents(
    documents: List[Dict],
    raw_dir: Path,
    dest_root: Path,
    collection_paths: Dict[str, Path],
    include_trash: bool
) -> Dict[str, str]:
    """Organize individual documents into their destination paths."""
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

        # Determine destination directory
        dest_dir = _determine_destination_dir(parent, collection_paths, dest_root, include_trash)
        if not dest_dir:
            continue

        # Create final destination path and copy file
        dest_path = _create_destination_path(dest_dir, title, doc_type)
        if _copy_document(src_path, dest_path, title):
            organized_paths[uuid] = str(dest_path)

    return organized_paths


def _determine_destination_dir(parent: str, collection_paths: Dict[str, Path], dest_root: Path, include_trash: bool) -> Optional[Path]:
    """Determine the destination directory for a document based on its parent."""
    if parent and parent in collection_paths:
        return collection_paths[parent]
    elif parent == "trash":
        if not include_trash:
            return None
        trash_dir = dest_root / "trash"
        ensure_directory(trash_dir)
        return trash_dir
    else:
        return dest_root


def _create_destination_path(dest_dir: Path, title: str, doc_type: str) -> Path:
    """Create the final destination path for a document."""
    clean_title = sanitize_name(title)
    if doc_type == "notebook":
        return dest_dir / clean_title
    else:
        ext = ".pdf" if doc_type == "pdf" else ".epub" if doc_type == "epub" else ""
        return dest_dir / f"{clean_title}{ext}"


def _copy_document(src_path: Path, dest_path: Path, title: str) -> bool:
    """Copy a document from source to destination path."""
    try:
        if src_path.is_dir():
            if dest_path.exists():
                shutil.rmtree(dest_path)
            shutil.copytree(src_path, dest_path)
        else:
            if dest_path.exists():
                dest_path.unlink()
            shutil.copy2(src_path, dest_path)
        return True
    except Exception as e:
        print(f"Warning: Failed to organize {title}: {e}")
        return False


def _print_organization_summary(documents: List[Dict], organized_paths: Dict[str, str], dest_root: Path):
    """Print summary of organization results."""
    doc_count = len([doc for doc in documents if not doc.get("is_trashed", False)])
    organized_count = len(organized_paths)

    print(f"Organized {organized_count}/{doc_count} documents")
    print(f"Destination: {dest_root}")
    print("(Files were copied for clean access)")


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
