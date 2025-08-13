"""Transcription operations using AI vision models."""

from pathlib import Path
from .openai import (
    OpenAISettings,
    transcribe_image_to_text,
)

__all__ = [
    'OpenAISettings',
    'transcribe_image_to_text',
    'transcribe_document',  # Simplified interface
]


def transcribe_document(doc_uuid: str, raw_dir, output_dir=None, model='gpt-4o'):
    """Transcribe a complete document using AI vision.

    Args:
        doc_uuid: Document UUID
        raw_dir: Path to raw files directory
        output_dir: Optional output directory for text files
        model: AI model to use (default: gpt-4o)

    Returns:
        Path to transcribed text file
    """
    from pathlib import Path
    from ..config import get_config
    from ..render import render_document

    config = get_config()
    raw_path = Path(raw_dir)

    # Set output directory
    if output_dir is None:
        output_dir = Path(config.text_dir)
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Get document name for better file organization
    doc_name = _get_document_name(doc_uuid, config.index_file)

    # First render the document to images
    image_paths = render_document(doc_uuid, raw_path)

    if not image_paths:
        print(f"No pages found for document {doc_uuid}")
        return None

    # Transcribe each image and combine
    settings = OpenAISettings(
        model=model,
        temperature=config.openai_temperature,
        max_retries=config.openai_max_retries,
    )

    transcriptions = []
    for img_path in image_paths:
        try:
            text = transcribe_image_to_text(img_path, settings)
            if text and text != "[no-text]":
                transcriptions.append(text)
        except Exception as e:
            print(f"Failed to transcribe {img_path}: {e}")

    # Save combined transcription
    if transcriptions:
        # Use document name for better organization, fallback to UUID
        filename = _sanitize_filename(doc_name) if doc_name != f"Document {doc_uuid[:8]}..." else doc_uuid
        output_file = output_dir / f"{filename}.txt"

        # Add metadata header
        header = f"# {doc_name}\n# UUID: {doc_uuid}\n# Pages: {len(transcriptions)}\n# Model: {model}\n\n"
        combined_text = header + "\n\n---\n\n".join(transcriptions)

        output_file.write_text(combined_text, encoding="utf-8")
        print(f"✅ Transcribed to: {output_file}")

        # Cleanup temp files for this document
        _cleanup_temp_files(doc_uuid, config.temp_dir)

        return output_file

    # Cleanup temp files even if transcription failed
    _cleanup_temp_files(doc_uuid, config.temp_dir)
    return None


def _get_document_name(doc_uuid: str, index_file: Path) -> str:
    """Get document name from index file."""
    try:
        import json
        with open(index_file, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
            for doc in catalog.get("documents", []):
                if doc["uuid"] == doc_uuid:
                    return doc["title"]
    except:
        pass
    return f"Document {doc_uuid[:8]}..."


def _sanitize_filename(name: str) -> str:
    """Sanitize filename by removing invalid characters."""
    import re
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Remove multiple underscores and trim
    sanitized = re.sub(r'_+', '_', sanitized).strip('_')
    # Limit length
    return sanitized[:100] if len(sanitized) > 100 else sanitized


def _cleanup_temp_files(doc_uuid: str, temp_dir: Path) -> None:
    """Clean up temporary files for a specific document."""
    import shutil
    doc_temp_dir = temp_dir / doc_uuid
    if doc_temp_dir.exists():
        try:
            shutil.rmtree(doc_temp_dir)
        except Exception as e:
            print(f"Warning: Could not cleanup temp files for {doc_uuid}: {e}")
