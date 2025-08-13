"""Organize operations for recreating collection structure from raw files."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from .utils import read_json, ensure_directory, sanitize_name, choose_unique_path


def _build_nodes(raw_dir: Path) -> Dict[str, dict]:
    """Build a dictionary of all documents and collections from raw files.

    Args:
        raw_dir: Directory containing raw files from tablet

    Returns:
        Dictionary mapping UUID to node metadata
    """
    nodes: Dict[str, dict] = {}
    for meta_path in raw_dir.glob("*.metadata"):
        uuid = meta_path.stem
        meta = read_json(meta_path) or {}
        nodes[uuid] = {
            "uuid": uuid,
            "name": meta.get("visibleName", ""),
            "type": meta.get("type", ""),
            "parent": meta.get("parent", ""),
        }
    return nodes


def _resolve_collection_path(nodes: Dict[str, dict], uuid: str) -> Tuple[List[str], bool]:
    """Resolve the full collection path for a document.

    Args:
        nodes: Dictionary of all nodes
        uuid: Document UUID

    Returns:
        Tuple of (path segments list, is_in_trash bool)
    """
    segs = []
    cur = nodes.get(uuid)
    is_trash = False

    while cur is not None:
        parent = cur.get("parent") or ""
        if parent == "trash":
            is_trash = True
            break
        segs.append(sanitize_name(cur.get("name") or cur.get("uuid") or uuid))
        if not parent:
            break
        cur = nodes.get(parent)

    return list(reversed(segs[1:])), is_trash


def _link_or_copy(src: Path, dst: Path, do_copy: bool) -> None:
    """Create a symlink or copy from source to destination.

    Args:
        src: Source path
        dst: Destination path
        do_copy: If True, copy instead of symlink
    """
    if dst.exists() or dst.is_symlink():
        return

    ensure_directory(dst.parent)

    if do_copy:
        if src.is_dir():
            # For notebooks, copy the directory structure
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    else:
        # Create relative symlink for better portability
        try:
            dst.symlink_to(src.relative_to(dst.parent))
        except ValueError:
            # Fallback to absolute if relative path fails
            dst.symlink_to(src.resolve())


def organize_files(
    raw_dir: Path,
    dest_root: Path,
    do_copy: bool = False,
    include_trash: bool = False,
    clear_dest: bool = False
) -> Dict[str, str]:
    """Organize raw files into a collection structure.

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

    nodes = _build_nodes(raw_dir)
    organized_paths = {}

    # Create folders for collections and documents
    for uuid, node in nodes.items():
        node_type = node.get("type", "")

        # Skip if in trash and not including trash
        path_segs, is_trash = _resolve_collection_path(nodes, uuid)
        if is_trash and not include_trash:
            continue

        # Build destination path
        if is_trash:
            dest_path = dest_root / "trash" / "/".join(path_segs)
        elif path_segs:
            dest_path = dest_root / "/".join(path_segs)
        else:
            dest_path = dest_root / sanitize_name(node.get("name") or uuid)

        # Make path unique if needed
        dest_path = choose_unique_path(dest_path)

        # Link or copy based on type
        if node_type == "DocumentType":
            # Handle notebooks (directories) and regular documents
            src_dir = raw_dir / uuid
            if src_dir.is_dir():
                # Notebook with .rm files
                _link_or_copy(src_dir, dest_path, do_copy)
                organized_paths[uuid] = str(dest_path)
            else:
                # Check for PDF/EPUB files
                for ext in [".pdf", ".epub"]:
                    src_file = raw_dir / f"{uuid}{ext}"
                    if src_file.exists():
                        dst_file = dest_path.with_suffix(ext)
                        dst_file = choose_unique_path(dst_file)
                        _link_or_copy(src_file, dst_file, do_copy)
                        organized_paths[uuid] = str(dst_file)
                        break

        elif node_type == "CollectionType":
            # Just create the directory for collections
            ensure_directory(dest_path)
            organized_paths[uuid] = str(dest_path)

    # Summary
    doc_count = sum(1 for n in nodes.values() if n.get("type") == "DocumentType")
    col_count = sum(1 for n in nodes.values() if n.get("type") == "CollectionType")

    print(f"Organized {doc_count} documents and {col_count} collections")
    print(f"Destination: {dest_root}")
    if do_copy:
        print("(Files were copied)")
    else:
        print("(Created symlinks)")

    return organized_paths


def _find_organized_path(raw_dir: Path, dest_root: Path, uuid: str) -> Optional[Path]:
    """Find the organized path for a document UUID.

    Args:
        raw_dir: Directory containing raw files
        dest_root: Root of organized structure
        uuid: Document UUID

    Returns:
        Path to organized document or None if not found
    """
    nodes = _build_nodes(raw_dir)
    node = nodes.get(uuid)

    if not node:
        return None

    path_segs, is_trash = _resolve_collection_path(nodes, uuid)

    if is_trash:
        base_path = dest_root / "trash" / "/".join(path_segs)
    elif path_segs:
        base_path = dest_root / "/".join(path_segs)
    else:
        base_path = dest_root / sanitize_name(node.get("name") or uuid)

    # Check if it exists (could be directory or file with extension)
    if base_path.exists():
        return base_path

    # Check for document files
    for ext in [".pdf", ".epub"]:
        doc_path = base_path.with_suffix(ext)
        if doc_path.exists():
            return doc_path

    return None
