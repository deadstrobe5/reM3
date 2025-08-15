"""Cracked mode transcription using multiple models + intelligent merge."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

from ..config import get_config
from ..errors import TranscribeError, require_openai_key
from .openai import _to_data_url, TRANSCRIBE_SYSTEM


@dataclass
class CrackedResult:
    """Result from cracked mode transcription."""
    final_text: str
    individual_results: Dict[str, str]
    individual_costs: Dict[str, float]
    merge_cost: Optional[float]
    total_cost: float
    models_used: List[str]
    merge_model: str


class CrackedTranscriber:
    """Multi-model transcription with intelligent merge."""

    def __init__(self):
        self.config = get_config()
        self.api_key = require_openai_key()

        # Default models for cracked mode
        self.models = self.config.cracked_models or [
            "gpt-4o",
            "anthropic/claude-3-5-sonnet:beta",
            "qwen/qwen2.5-vl-32b-instruct"
        ]
        self.merge_model = self.config.cracked_merge_model or "gpt-4o"

        print(f"🔥 CRACKED MODE: Using {len(self.models)} models + merge")
        print(f"   Models: {', '.join(self.models)}")
        print(f"   Merge: {self.merge_model}")

    def transcribe_image_cracked(self, image_path: Path) -> CrackedResult:
        """Transcribe image using multiple models and merge results."""
        if not image_path.exists():
            raise TranscribeError(f"Image file not found: {image_path}")

        print(f"\n🔥 Cracked transcription: {image_path.name}")

        # Step 1: Transcribe with multiple models in parallel
        individual_results = {}
        individual_costs = {}

        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all transcription tasks
            future_to_model = {
                executor.submit(self._transcribe_with_model, image_path, model): model
                for model in self.models
            }

            # Collect results as they complete
            for future in as_completed(future_to_model):
                model = future_to_model[future]
                try:
                    text, cost = future.result()
                    if text and text.strip():
                        individual_results[model] = text.strip()
                        if cost:
                            individual_costs[model] = cost
                        print(f"   ✅ {model}: {len(text)} chars" + (f" (${cost:.6f})" if cost else ""))
                    else:
                        print(f"   ❌ {model}: No text returned")
                except Exception as e:
                    print(f"   ❌ {model}: Failed - {e}")

        if not individual_results:
            raise TranscribeError("All models failed to transcribe the image")

        print(f"   📊 {len(individual_results)}/{len(self.models)} models succeeded")

        # Step 2: Merge results using merge model
        print(f"\n🧠 Merging results with {self.merge_model}...")
        merged_text, merge_cost = self._merge_transcriptions(individual_results)

        # Calculate total cost
        total_individual_cost = sum(individual_costs.values())
        total_cost = total_individual_cost + (merge_cost or 0)

        print(f"   💰 Individual costs: ${total_individual_cost:.6f}")
        if merge_cost:
            print(f"   💰 Merge cost: ${merge_cost:.6f}")
        print(f"   💰 Total cost: ${total_cost:.6f}")

        return CrackedResult(
            final_text=merged_text,
            individual_results=individual_results,
            individual_costs=individual_costs,
            merge_cost=merge_cost,
            total_cost=total_cost,
            models_used=list(individual_results.keys()),
            merge_model=self.merge_model
        )

    def _transcribe_with_model(self, image_path: Path, model: str) -> Tuple[str, Optional[float]]:
        """Transcribe image with a specific model."""
        try:
            # Set up client based on model
            if model.startswith(("anthropic/", "qwen/", "google/")):
                # OpenRouter model
                client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://openrouter.ai/api/v1"
                )
            else:
                # OpenAI model
                client = OpenAI(api_key=self.api_key)

            data_url = _to_data_url(image_path)

            resp = client.chat.completions.create(
                model=model,
                temperature=0.0,
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": TRANSCRIBE_SYSTEM},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Transcribe this page to plain text only. Preserve line breaks. No commentary."},
                            {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
                        ],
                    },
                ],
            )

            text = resp.choices[0].message.content or ""
            text = text.strip()

            # Extract cost if available (OpenRouter)
            cost = None
            if hasattr(resp, 'usage') and resp.usage and hasattr(resp.usage, 'cost'):
                cost = getattr(resp.usage, 'cost', None)

            return text, cost

        except Exception as e:
            raise TranscribeError(f"Model {model} failed: {str(e)}")

    def _merge_transcriptions(self, results: Dict[str, str]) -> Tuple[str, Optional[float]]:
        """Merge multiple transcription results using a text model."""
        if len(results) == 1:
            # Only one result, return it directly
            return list(results.values())[0], None

        # Prepare merge prompt
        merge_prompt = self._create_merge_prompt(results)

        try:
            # Use merge model (typically OpenAI for better reasoning)
            client = OpenAI(api_key=self.api_key)

            resp = client.chat.completions.create(
                model=self.merge_model,
                temperature=0.1,
                max_tokens=3000,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert at merging multiple transcriptions of handwritten text.
Your task is to analyze multiple AI transcriptions of the same document and produce the most accurate merged result.

Guidelines:
- Compare all versions and identify the most likely correct text
- Preserve the original structure, line breaks, and formatting
- When transcriptions disagree, choose the most coherent and contextually appropriate version
- Fix obvious OCR errors by comparing across versions
- Maintain the author's original writing style and intent
- Output ONLY the final merged transcription with no commentary or explanation"""
                    },
                    {"role": "user", "content": merge_prompt}
                ],
            )

            merged_text = resp.choices[0].message.content or ""
            merged_text = merged_text.strip()

            # Extract cost if available
            cost = None
            if hasattr(resp, 'usage') and resp.usage and hasattr(resp.usage, 'cost'):
                cost = getattr(resp.usage, 'cost', None)

            return merged_text, cost

        except Exception as e:
            # If merge fails, return the longest transcription as fallback
            print(f"   ⚠️  Merge failed ({e}), using longest transcription")
            longest = max(results.values(), key=len)
            return longest, None

    def _create_merge_prompt(self, results: Dict[str, str]) -> str:
        """Create prompt for merging transcriptions."""
        prompt_parts = [
            "I have multiple AI transcriptions of the same handwritten document. Please merge them into the most accurate final version.\n"
        ]

        for i, (model, text) in enumerate(results.items(), 1):
            prompt_parts.append(f"=== TRANSCRIPTION {i} ({model}) ===")
            prompt_parts.append(text)
            prompt_parts.append("")

        prompt_parts.append("=== INSTRUCTIONS ===")
        prompt_parts.append("Please provide the best merged transcription that combines the most accurate elements from all versions above.")

        return "\n".join(prompt_parts)

    def estimate_cracked_cost(self, num_pages: int) -> Dict[str, Union[float, List[str], Dict[str, float], str]]:
        """Estimate cost for cracked mode transcription."""
        # Base cost estimates per page (in USD)
        model_costs = {
            "gpt-4o": 0.01,
            "anthropic/claude-3-5-sonnet:beta": 0.008,
            "qwen/qwen2.5-vl-32b-instruct": 0.002,
            "qwen/qwen2.5-vl-7b-instruct": 0.001,
        }

        total_transcription_cost = 0
        individual_costs = {}

        for model in self.models:
            cost_per_page = model_costs.get(model, 0.005)  # Default estimate
            model_cost = num_pages * cost_per_page
            individual_costs[model] = model_cost
            total_transcription_cost += model_cost

        # Merge cost (typically much cheaper since it's text-only)
        merge_cost_per_page = model_costs.get(self.merge_model, 0.002) * 0.1  # ~10% of vision cost
        merge_cost = num_pages * merge_cost_per_page

        total_cost = total_transcription_cost + merge_cost

        return {
            "individual_costs": individual_costs,
            "merge_cost": merge_cost,
            "total_cost": total_cost,
            "cost_multiplier": total_cost / (num_pages * 0.01),  # vs single GPT-4o
            "models_used": self.models,
            "merge_model": self.merge_model
        }


def transcribe_image_cracked(image_path: Path) -> CrackedResult:
    """Convenience function for cracked mode transcription."""
    transcriber = CrackedTranscriber()
    return transcriber.transcribe_image_cracked(image_path)
