from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from PIL import Image, ImageOps
import cairosvg
import re

from ..errors import RenderError


@dataclass(frozen=True)
class RenderSettings:
    dpi: int = 150  # Lower DPI for better OpenAI processing
    format: str = "png"  # Use PNG for better quality
    quality: int = 95  # jpeg quality if used
    stroke_width_scale: float = 3.0  # Scale up strokes for visibility
    canvas_padding: int = 50  # pixels of white space around content
    target_height: int = 2048  # OpenAI optimal size
    force_white_background: bool = True
    enhance_contrast: bool = True  # Gentle contrast enhancement only
    binarize: bool = False  # Don't binarize by default - keep grays


def _rm_to_svg(rm_file: Path, svg_out: Path) -> None:
    """Convert .rm to SVG using rmc."""
    svg_out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["rmc", "-t", "svg", str(rm_file), "-o", str(svg_out)]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise RenderError(
            f"Failed to convert .rm file to SVG: {rm_file.name}",
            f"Command: {' '.join(cmd)}\nError: {e.stderr}"
        )
    except FileNotFoundError:
        raise RenderError(
            "rmc tool not found",
            "Install rmc: https://github.com/lschwetlick/rmc"
        )


def _thicken_svg_strokes(svg_path: Path, scale: float = 3.0) -> None:
    """Scale up stroke-width attributes in SVG and ensure proper background."""
    try:
        text = svg_path.read_text(encoding="utf-8")

        # Replace stroke-width in attributes or styles
        def repl(match: re.Match) -> str:
            prefix = match.group(1)
            value = float(match.group(2))
            # Ensure minimum visible stroke width
            new_val = max(1.0, value * scale)
            return f"{prefix}{new_val:.3f}"

        text = re.sub(
            r"(stroke-width\s*[:=]\s*['\"]?)([0-9]*\.?[0-9]+)",
            repl,
            text
        )

        # Add white background rect if not present
        if '<rect' not in text or 'fill="white"' not in text:
            # Find viewBox or width/height to get dimensions
            viewbox_match = re.search(r'viewBox="0 0 (\d+\.?\d*) (\d+\.?\d*)"', text)
            width_match = re.search(r'width="(\d+\.?\d*)"', text)
            height_match = re.search(r'height="(\d+\.?\d*)"', text)

            if viewbox_match:
                width, height = viewbox_match.groups()
            elif width_match and height_match:
                width = width_match.group(1)
                height = height_match.group(1)
            else:
                # Default reMarkable dimensions
                width, height = "1404", "1872"

            # Insert white background rect right after opening svg tag
            bg_rect = f'<rect x="0" y="0" width="{width}" height="{height}" fill="white" stroke="none"/>'
            text = re.sub(r'(<svg[^>]*>)', r'\1\n' + bg_rect, text, count=1)

        svg_path.write_text(text, encoding="utf-8")
    except Exception as e:
        raise RenderError("Failed to process SVG stroke widths", str(e))


def _svg_to_png_cairo(svg_path: Path, png_out: Path, dpi: int = 150) -> None:
    """Convert SVG to PNG using cairosvg with proper settings."""
    png_out.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Read SVG content
        svg_content = svg_path.read_text(encoding="utf-8")

        # Convert with white background using DPI
        png_data = cairosvg.svg2png(
            bytestring=svg_content.encode('utf-8'),
            dpi=dpi,
            output_width=None,  # Let it calculate from DPI
            output_height=None,
            background_color="white"  # Force white background
        )

        # Write PNG data
        if png_data:
            png_out.write_bytes(png_data)

    except Exception as e:
        raise RenderError(
            f"Failed to convert SVG to PNG: {svg_path.name}",
            str(e)
        )


def _postprocess_image(img: Image.Image, settings: RenderSettings) -> Image.Image:
    """Post-process image with gentle enhancements."""

    # Ensure RGB mode (no alpha channel)
    if img.mode in ('RGBA', 'LA', 'P'):
        # Create white background
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        if 'A' in img.mode:
            background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
        else:
            background.paste(img)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # Apply gentle contrast enhancement if enabled
    if settings.enhance_contrast:
        # Use autocontrast with a small cutoff to avoid over-processing
        img = ImageOps.autocontrast(img, cutoff=0.5)

    # Optional: Apply binarization if explicitly requested
    if settings.binarize:
        # Convert to grayscale first
        gray = img.convert('L')
        # Threshold to black and white
        threshold = 180  # Less aggressive than before (was 200)
        bw = gray.point(lambda p: 255 if p > threshold else 0, mode='L')
        # Convert back to RGB
        img = bw.convert('RGB')

    # Resize if needed for OpenAI optimal processing
    if settings.target_height and img.height != settings.target_height:
        ratio = settings.target_height / img.height
        new_width = int(img.width * ratio)
        # Use high-quality resampling
        img = img.resize((new_width, settings.target_height), Image.Resampling.LANCZOS)

    # Add padding if specified
    if settings.canvas_padding > 0:
        p = settings.canvas_padding
        new_size = (img.width + 2*p, img.height + 2*p)
        padded = Image.new('RGB', new_size, (255, 255, 255))
        padded.paste(img, (p, p))
        img = padded

    return img


def render_page_rm_to_image(
    rm_page_file: Path,
    out_file: Path,
    settings: RenderSettings,
) -> None:
    """Render a single .rm page to an image file."""

    # Step 1: Convert .rm to SVG
    tmp_svg = out_file.with_suffix(".svg")
    _rm_to_svg(rm_page_file, tmp_svg)

    # Step 2: Process SVG (thicken strokes, add background)
    _thicken_svg_strokes(tmp_svg, scale=settings.stroke_width_scale)

    # Step 3: Convert SVG to PNG with cairosvg
    tmp_png = out_file.with_suffix(".tmp.png")
    _svg_to_png_cairo(tmp_svg, tmp_png, dpi=settings.dpi)

    # Step 4: Post-process the image
    try:
        img = Image.open(tmp_png)
        img = _postprocess_image(img, settings)

        # Step 5: Save in requested format
        out_file.parent.mkdir(parents=True, exist_ok=True)

        if settings.format.lower() == "jpeg":
            # Convert to RGB if not already (JPEG doesn't support transparency)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            final_path = out_file.with_suffix(".jpg")
            img.save(final_path, format="JPEG", quality=settings.quality, optimize=True)
        else:
            # Save as PNG
            final_path = out_file.with_suffix(".png")
            img.save(final_path, format="PNG", optimize=True)

        # Clean up temp file
        if tmp_png.exists():
            tmp_png.unlink()

    except Exception as e:
        print(f"Error processing image: {e}")
        # If processing fails, just rename the temp file
        if tmp_png.exists():
            final_path = out_file.with_suffix(".png")
            tmp_png.rename(final_path)


def list_rm_pages(doc_dir: Path) -> List[Path]:
    """List all .rm files in a document directory."""
    return sorted(p for p in doc_dir.glob("*.rm"))


def render_document_pages(
    doc_uuid: str,
    raw_dir: Path,
    out_dir: Path,
    settings: Optional[RenderSettings] = None,
) -> List[Path]:
    """Render all pages of a document."""
    settings = settings or RenderSettings()
    doc_dir = raw_dir / doc_uuid

    if not doc_dir.exists():
        raise RenderError(f"Document directory not found: {doc_dir}")

    pages = list_rm_pages(doc_dir)
    if not pages:
        raise RenderError(f"No .rm files found in document {doc_uuid}")

    rendered: List[Path] = []
    for idx, page in enumerate(pages, start=1):
        ext = ".jpg" if settings.format.lower() == "jpeg" else ".png"
        out_file = out_dir / doc_uuid / f"page_{idx:04d}{ext}"
        print(f"Rendering page {idx}/{len(pages)}: {page.name} -> {out_file.name}")

        try:
            render_page_rm_to_image(page, out_file, settings)
            rendered.append(out_file)
        except Exception as e:
            print(f"Failed to render page {idx}: {e}")

    return rendered
