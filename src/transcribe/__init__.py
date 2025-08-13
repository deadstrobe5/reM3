"""Transcription operations using AI vision models."""

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
        output_file = output_dir / f"{doc_uuid}.txt"
        output_file.write_text("\n\n---\n\n".join(transcriptions), encoding="utf-8")
        print(f"✅ Transcribed to: {output_file}")
        return output_file

    return None
