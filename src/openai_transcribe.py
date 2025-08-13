from __future__ import annotations

import os
import time
from dataclasses import dataclass
import base64
from io import BytesIO
from PIL import Image
from pathlib import Path


from openai import OpenAI


TRANSCRIBE_SYSTEM = (
    "You are a precise transcription engine for user-owned handwritten notes.\n"
    "Task: Transcribe exactly what is written into plain UTF-8 text.\n"
    "Preserve original line breaks and spacing. Only include bullets if they are present.\n"
    "Never invent, summarize, or paraphrase. If a word/region is unreadable, write [illegible].\n"
    "If there is no readable text, output [no-text]. Output text only."
)


@dataclass(frozen=True)
class OpenAISettings:
    model: str = "gpt-4o"
    temperature: float = 0.0
    max_retries: int = 5
    initial_backoff_s: float = 1.0


def _backoff_sleep(attempt: int, initial: float) -> None:
    time.sleep(initial * (2 ** (attempt - 1)))


def _to_data_url(image_path: Path) -> str:
    suffix = image_path.suffix.lower()
    mime = "image/png" if suffix in {".png"} else "image/jpeg"
    data = image_path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _pil_to_data_url(img: Image.Image, fmt: str = "PNG") -> str:
    mime = "image/png" if fmt.upper() == "PNG" else "image/jpeg"
    buf = BytesIO()
    save_kwargs: dict[str, int | bool] = {"optimize": True}
    if fmt.upper() == "JPEG":
        save_kwargs["quality"] = 85
    img.save(buf, format=fmt, **save_kwargs)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _transcribe_data_url(image_data_url: str, settings: OpenAISettings, attempt: int) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)

    def _looks_like_refusal(s: str) -> bool:
        s_lower = s.lower()
        triggers = [
            "i'm sorry",
            "i am sorry",
            "cannot assist",
            "can't assist",
            "i can't",
            "i cannot",
        ]
        return any(t in s_lower for t in triggers)

    for _ in range(attempt, settings.max_retries + 1):
        try:
            model_to_use = settings.model
            # On retry, escalate to gpt-4o for better compliance
            if attempt > 1 and settings.model != "gpt-4o":
                model_to_use = "gpt-4o"

            resp = client.chat.completions.create(
                model=model_to_use,
                temperature=settings.temperature,
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": TRANSCRIBE_SYSTEM},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Transcribe this page to plain text only. Preserve line breaks. No commentary."},
                            {"type": "image_url", "image_url": {"url": image_data_url, "detail": "high"}},
                        ],
                    },
                ],
            )
            text = resp.choices[0].message.content or ""
            text = text.strip()
            if not text or _looks_like_refusal(text):
                raise RuntimeError("refusal or empty response")
            return text
        except Exception:  # noqa: BLE001
            if attempt >= settings.max_retries:
                raise
            _backoff_sleep(attempt, settings.initial_backoff_s)
            attempt += 1

    return ""


def transcribe_image_to_text(image_path: Path, settings: OpenAISettings, tile_cols: int = 1) -> str:
    # If tiling is requested, split into vertical tiles with small overlaps
    if tile_cols and tile_cols > 1:
        img = Image.open(image_path).convert("RGB")
        w, h = img.size
        overlap = max(10, w // 100)  # ~1% overlap
        tile_w = w // tile_cols
        texts: list[str] = []
        for i in range(tile_cols):
            x0 = max(0, i * tile_w - (overlap if i > 0 else 0))
            x1 = min(w, (i + 1) * tile_w + (overlap if i < tile_cols - 1 else 0))
            crop = img.crop((x0, 0, x1, h))
            data_url = _pil_to_data_url(crop, fmt="PNG")
            part = _transcribe_data_url(data_url, settings, attempt=1)
            texts.append(part.strip())
        # Merge tiles with a newline to avoid concatenation artifacts
        return "\n".join(t for t in texts if t)

    # Single image
    data_url = _to_data_url(image_path)
    return _transcribe_data_url(data_url, settings, attempt=1)
