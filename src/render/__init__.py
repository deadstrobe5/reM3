"""Render operations for converting reMarkable files to images."""

from .rm_to_image import (
    RenderSettings,
    render_document_pages,
    render_page_rm_to_image,
    list_rm_pages,
)

__all__ = [
    'RenderSettings',
    'render_document_pages',
    'render_page_rm_to_image',
    'list_rm_pages',
    'render_document',  # Simplified alias
]

# Simplified interface
def render_document(doc_uuid: str, raw_dir, output_dir=None, format='jpeg'):
    """Simple interface to render a document to images.

    Args:
        doc_uuid: Document UUID
        raw_dir: Path to raw files directory
        output_dir: Optional output directory (defaults to temp)
        format: Image format ('jpeg' or 'png')

    Returns:
        List of paths to rendered images
    """
    from pathlib import Path
    from ..config import get_config

    config = get_config()

    if output_dir is None:
        output_dir = Path(config.base_dir) / "data" / "temp" / doc_uuid

    settings = RenderSettings(
        dpi=config.render_dpi,
        format=format,
        quality=config.render_quality if format == 'jpeg' else 100,
        stroke_width_scale=config.stroke_width_scale,
        target_height=config.target_height,
        force_white_background=True,
        enhance_contrast=True,
    )

    return render_document_pages(
        doc_uuid=doc_uuid,
        raw_dir=Path(raw_dir),
        out_dir=Path(output_dir),
        settings=settings
    )
