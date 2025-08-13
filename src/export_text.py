from __future__ import annotations

import concurrent.futures as cf
import json

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .rm_render import RenderSettings, render_document_pages
from .openai_transcribe import OpenAISettings, transcribe_image_to_text


@dataclass(frozen=True)
class ExportSettings:
    raw_dir: Path
    organized_dir: Path
    out_dir: Path
    model: str = "gpt-4o"
    dpi: int = 200  # Optimal for complex handwriting
    image_format: str = "jpeg"  # JPEG saves 60% space with no quality loss
    image_quality: int = 95  # High quality for better recognition
    workers: int = 3
    include_trash: bool = False
    force: bool = False


def _sanitize_name(name: str) -> str:
    name = (name or "").strip()
    for ch, repl in [("/", "-"), ("\\", "-"), (":", " -")]:
        name = name.replace(ch, repl)
    return name[:200] if len(name) > 200 else name


def _load_nodes(raw_dir: Path) -> Dict[str, Dict]:
    nodes: Dict[str, dict] = {}
    for meta_path in raw_dir.glob("*.metadata"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta = {}
        nodes[meta_path.stem] = meta
    return nodes


def _get_doc_name_and_parent(nodes: Dict[str, dict], uuid: str) -> Tuple[str, Optional[str]]:
    meta = nodes.get(uuid, {})
    return meta.get("visibleName", uuid), meta.get("parent")


def export_document_to_text(uuid: str, settings: ExportSettings) -> Optional[Path]:
    nodes = _load_nodes(settings.raw_dir)
    name, parent = _get_doc_name_and_parent(nodes, uuid)
    if parent == "trash" and not settings.include_trash:
        return None

    # Render pages
    images_dir = settings.out_dir / "_pages" / uuid
    rendered_pages = render_document_pages(
        uuid,
        settings.raw_dir,
        images_dir,
        settings=RenderSettings(
            dpi=settings.dpi,
            format=settings.image_format,
            quality=settings.image_quality,
            stroke_width_scale=2.0,  # Thin strokes preserve accuracy better
            target_height=2000,  # Optimal for mixed-language handwriting
            force_white_background=True,  # Ensure white background
            enhance_contrast=True,  # Gentle contrast enhancement
            binarize=False  # Keep grayscale, don't binarize
        ),
    )
    if not rendered_pages:
        return None

    # Transcribe pages
    openai_cfg = OpenAISettings(model=settings.model)
    texts: List[str] = [""] * len(rendered_pages)

    def _work(i_and_path: Tuple[int, Path]) -> Tuple[int, str]:
        i, img = i_and_path
        # Use single column for better accuracy (testing showed it works well)
        txt = transcribe_image_to_text(img, openai_cfg, tile_cols=1)
        return i, txt

    with cf.ThreadPoolExecutor(max_workers=settings.workers) as pool:
        for i, txt in pool.map(_work, list(enumerate(rendered_pages))):
            texts[i] = txt

    # Save document text
    doc_dir = settings.out_dir / _sanitize_name(name)
    doc_dir.mkdir(parents=True, exist_ok=True)
    out_txt = doc_dir / f"{_sanitize_name(name)}.txt"
    page_sep = "\n\n--- Page {n} ---\n\n"
    merged = []
    for idx, t in enumerate(texts, start=1):
        merged.append(page_sep.format(n=idx))
        merged.append(t.strip())
    out_txt.write_text("\n".join(merged).strip() + "\n", encoding="utf-8")
    return out_txt
