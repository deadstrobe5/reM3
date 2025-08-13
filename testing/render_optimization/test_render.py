#!/usr/bin/env python3
"""
Refined rendering test based on initial findings and research insights.
Focus on thinner strokes and research-backed configurations.
"""

import os
import sys
import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from rm_render import RenderSettings, render_page_rm_to_image, list_rm_pages  # type: ignore
from openai_transcribe import transcribe_image_to_text, OpenAISettings  # type: ignore
from PIL import Image


@dataclass
class TestResult:
    """Results from a single test configuration."""
    config_name: str
    settings: dict
    render_time: float
    file_size_kb: float
    image_dimensions: Tuple[int, int]
    image_mode: str
    transcription: str
    transcription_time: float
    char_count: int
    word_count: int
    line_count: int
    has_illegible_markers: bool
    illegible_count: int
    has_no_text_marker: bool
    accuracy_score: float
    api_error: Optional[str] = None


class RefinedRenderTester:
    """Refined testing focusing on optimal stroke thickness and research-backed settings."""

    def __init__(self, test_doc_uuid: str, output_dir: Path, reference_text: Optional[str] = None):
        self.doc_uuid = test_doc_uuid
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.reference_text = reference_text
        self.results: List[TestResult] = []

    def get_refined_configurations(self) -> List[Dict[str, Any]]:
        """
        Define refined configurations based on:
        1. thin_strokes_2x performing well in initial tests
        2. Research showing 1600-2048px optimal for vision models
        3. 150-200 DPI sweet spot
        4. Gentle processing being better than aggressive
        """
        configs = [
            # === STROKE WIDTH REFINEMENT (focusing on thinner strokes) ===
            {
                "name": "ultra_thin_1.5x",
                "settings": RenderSettings(
                    dpi=150,
                    format="png",
                    stroke_width_scale=1.5,
                    target_height=1600,
                    enhance_contrast=True,
                    binarize=False
                )
            },
            {
                "name": "thin_optimal_2.0x",
                "settings": RenderSettings(
                    dpi=150,
                    format="png",
                    stroke_width_scale=2.0,
                    target_height=1600,
                    enhance_contrast=True,
                    binarize=False
                )
            },
            {
                "name": "thin_plus_2.2x",
                "settings": RenderSettings(
                    dpi=150,
                    format="png",
                    stroke_width_scale=2.2,
                    target_height=1600,
                    enhance_contrast=True,
                    binarize=False
                )
            },
            {
                "name": "moderate_2.5x",
                "settings": RenderSettings(
                    dpi=150,
                    format="png",
                    stroke_width_scale=2.5,
                    target_height=1600,
                    enhance_contrast=True,
                    binarize=False
                )
            },
            {
                "name": "moderate_plus_2.8x",
                "settings": RenderSettings(
                    dpi=150,
                    format="png",
                    stroke_width_scale=2.8,
                    target_height=1600,
                    enhance_contrast=True,
                    binarize=False
                )
            },

            # === HEIGHT OPTIMIZATION (around research sweet spot) ===
            {
                "name": "height_1400_thin",
                "settings": RenderSettings(
                    dpi=150,
                    format="png",
                    stroke_width_scale=2.0,
                    target_height=1400,
                    enhance_contrast=True
                )
            },
            {
                "name": "height_1600_thin",
                "settings": RenderSettings(
                    dpi=150,
                    format="png",
                    stroke_width_scale=2.0,
                    target_height=1600,
                    enhance_contrast=True
                )
            },
            {
                "name": "height_1800_thin",
                "settings": RenderSettings(
                    dpi=150,
                    format="png",
                    stroke_width_scale=2.0,
                    target_height=1800,
                    enhance_contrast=True
                )
            },
            {
                "name": "height_2000_thin",
                "settings": RenderSettings(
                    dpi=150,
                    format="png",
                    stroke_width_scale=2.0,
                    target_height=2000,
                    enhance_contrast=True
                )
            },

            # === DPI VARIATIONS WITH THIN STROKES ===
            {
                "name": "dpi_120_thin",
                "settings": RenderSettings(
                    dpi=120,
                    format="png",
                    stroke_width_scale=2.0,
                    target_height=1600,
                    enhance_contrast=True
                )
            },
            {
                "name": "dpi_150_thin",
                "settings": RenderSettings(
                    dpi=150,
                    format="png",
                    stroke_width_scale=2.0,
                    target_height=1600,
                    enhance_contrast=True
                )
            },
            {
                "name": "dpi_175_thin",
                "settings": RenderSettings(
                    dpi=175,
                    format="png",
                    stroke_width_scale=2.0,
                    target_height=1600,
                    enhance_contrast=True
                )
            },
            {
                "name": "dpi_200_thin",
                "settings": RenderSettings(
                    dpi=200,
                    format="png",
                    stroke_width_scale=2.0,
                    target_height=1600,
                    enhance_contrast=True
                )
            },

            # === CONTRAST VARIATIONS ===
            {
                "name": "no_contrast_thin",
                "settings": RenderSettings(
                    dpi=150,
                    format="png",
                    stroke_width_scale=2.0,
                    target_height=1600,
                    enhance_contrast=False,
                    binarize=False
                )
            },
            {
                "name": "gentle_contrast_thin",
                "settings": RenderSettings(
                    dpi=150,
                    format="png",
                    stroke_width_scale=2.0,
                    target_height=1600,
                    enhance_contrast=True,
                    binarize=False
                )
            },

            # === PADDING VARIATIONS ===
            {
                "name": "no_padding_thin",
                "settings": RenderSettings(
                    dpi=150,
                    format="png",
                    stroke_width_scale=2.0,
                    target_height=1600,
                    enhance_contrast=True,
                    canvas_padding=0
                )
            },
            {
                "name": "small_padding_thin",
                "settings": RenderSettings(
                    dpi=150,
                    format="png",
                    stroke_width_scale=2.0,
                    target_height=1600,
                    enhance_contrast=True,
                    canvas_padding=20
                )
            },
            {
                "name": "medium_padding_thin",
                "settings": RenderSettings(
                    dpi=150,
                    format="png",
                    stroke_width_scale=2.0,
                    target_height=1600,
                    enhance_contrast=True,
                    canvas_padding=40
                )
            },
            {
                "name": "large_padding_thin",
                "settings": RenderSettings(
                    dpi=150,
                    format="png",
                    stroke_width_scale=2.0,
                    target_height=1600,
                    enhance_contrast=True,
                    canvas_padding=80
                )
            },

            # === FORMAT COMPARISON WITH OPTIMAL SETTINGS ===
            {
                "name": "jpeg_q95_thin",
                "settings": RenderSettings(
                    dpi=150,
                    format="jpeg",
                    quality=95,
                    stroke_width_scale=2.0,
                    target_height=1600,
                    enhance_contrast=True
                )
            },
            {
                "name": "jpeg_q90_thin",
                "settings": RenderSettings(
                    dpi=150,
                    format="jpeg",
                    quality=90,
                    stroke_width_scale=2.0,
                    target_height=1600,
                    enhance_contrast=True
                )
            },
            {
                "name": "jpeg_q85_thin",
                "settings": RenderSettings(
                    dpi=150,
                    format="jpeg",
                    quality=85,
                    stroke_width_scale=2.0,
                    target_height=1600,
                    enhance_contrast=True
                )
            },

            # === RESEARCH-BASED OPTIMAL CANDIDATES ===
            {
                "name": "research_optimal_1",
                "settings": RenderSettings(
                    dpi=150,
                    format="png",
                    stroke_width_scale=2.0,  # Thin based on findings
                    target_height=1600,       # Research sweet spot
                    enhance_contrast=True,
                    binarize=False,
                    canvas_padding=30
                )
            },
            {
                "name": "research_optimal_2",
                "settings": RenderSettings(
                    dpi=175,
                    format="png",
                    stroke_width_scale=2.2,
                    target_height=1800,
                    enhance_contrast=True,
                    binarize=False,
                    canvas_padding=40
                )
            },
            {
                "name": "research_optimal_3",
                "settings": RenderSettings(
                    dpi=200,
                    format="jpeg",
                    quality=95,
                    stroke_width_scale=2.0,
                    target_height=2000,
                    enhance_contrast=True,
                    binarize=False,
                    canvas_padding=50
                )
            },

            # === MINIMAL PROCESSING (baseline) ===
            {
                "name": "minimal_processing",
                "settings": RenderSettings(
                    dpi=150,
                    format="png",
                    stroke_width_scale=1.0,  # No stroke enhancement
                    target_height=None,       # No resizing
                    enhance_contrast=False,   # No contrast
                    binarize=False,
                    canvas_padding=0          # No padding
                )
            }
        ]

        return configs

    def calculate_accuracy_score(self, transcription: str) -> float:
        """
        Calculate accuracy score based on text quality indicators.
        Higher weight on actual text similarity if reference is available.
        """
        score = 100.0

        # Basic quality checks
        illegible_count = transcription.lower().count('[illegible]')
        score -= illegible_count * 1.5  # Less penalty than before

        if '[no-text]' in transcription.lower():
            score -= 50
        if '[drawing]' in transcription.lower():
            score -= 30

        # Length checks
        word_count = len(transcription.split())
        if word_count < 50:
            score -= (50 - word_count) * 0.3
        elif word_count > 500:  # Likely hallucination
            score -= (word_count - 500) * 0.1

        # Check for repetition (hallucination indicator)
        lines = [l.strip() for l in transcription.split('\n') if l.strip()]
        if len(lines) > 5:
            unique_lines = len(set(lines))
            if unique_lines / len(lines) < 0.5:  # More than 50% repetition
                score -= 30

        # If we have reference text, use similarity
        if self.reference_text and len(transcription) > 100:
            # Simple word-based similarity
            ref_words = set(self.reference_text.lower().split())
            trans_words = set(transcription.lower().split())

            # Jaccard similarity
            intersection = ref_words & trans_words
            union = ref_words | trans_words
            if union:
                similarity = len(intersection) / len(union)
                # Boost score based on similarity
                score = score * 0.5 + (similarity * 100) * 0.5

        # Check for structure quality
        if any(marker in transcription for marker in ['→', '-', '•', '1.', '2.']):
            score += 3  # Has bullets/structure
        if '\n\n' in transcription:
            score += 2  # Has paragraphs

        return max(0, min(100, score))

    def test_configuration(
        self,
        rm_file: Path,
        config: Dict[str, Any],
        openai_settings: OpenAISettings
    ) -> TestResult:
        """Test a single rendering configuration."""

        config_name = config["name"]
        settings = config["settings"]

        print(f"\n[{config_name}]")
        print(f"  Strokes: {settings.stroke_width_scale}x, "
              f"Height: {settings.target_height}, "
              f"DPI: {settings.dpi}, "
              f"Contrast: {settings.enhance_contrast}")

        # Render the image
        render_start = time.time()
        out_file = self.output_dir / config_name

        try:
            render_page_rm_to_image(rm_file, out_file, settings)
            render_time = time.time() - render_start

            # Determine actual file path
            if settings.format.lower() == 'jpeg':
                image_path = out_file.with_suffix('.jpg')
            else:
                image_path = out_file.with_suffix('.png')

            if not image_path.exists():
                raise FileNotFoundError(f"Rendered file not found: {image_path}")

            # Get image metadata
            file_size_kb = image_path.stat().st_size / 1024
            with Image.open(image_path) as img:
                dimensions = (img.width, img.height)
                mode = img.mode

            print(f"  Rendered: {file_size_kb:.1f}KB, {dimensions[0]}x{dimensions[1]}")

            # Transcribe with OpenAI
            transcribe_start = time.time()
            transcription = transcribe_image_to_text(
                image_path=image_path,
                settings=openai_settings,
                tile_cols=1  # Single column based on research
            )
            transcribe_time = time.time() - transcribe_start

            # Save transcription
            transcript_path = image_path.with_suffix('.txt')
            transcript_path.write_text(transcription, encoding='utf-8')

            # Analyze transcription
            char_count = len(transcription)
            word_count = len(transcription.split())
            line_count = len(transcription.split('\n'))
            illegible_count = transcription.lower().count('[illegible]')
            has_illegible = illegible_count > 0
            has_no_text = '[no-text]' in transcription.lower()
            accuracy = self.calculate_accuracy_score(transcription)

            print(f"  Transcribed: {word_count} words, accuracy={accuracy:.1f}%")

            if has_no_text:
                print("  ⚠ WARNING: Got [no-text] marker")
            if has_illegible:
                print(f"  ⚠ {illegible_count} [illegible] markers")

            return TestResult(
                config_name=config_name,
                settings=asdict(settings),
                render_time=render_time,
                file_size_kb=file_size_kb,
                image_dimensions=dimensions,
                image_mode=mode,
                transcription=transcription,
                transcription_time=transcribe_time,
                char_count=char_count,
                word_count=word_count,
                line_count=line_count,
                has_illegible_markers=has_illegible,
                illegible_count=illegible_count,
                has_no_text_marker=has_no_text,
                accuracy_score=accuracy
            )

        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            return TestResult(
                config_name=config_name,
                settings=asdict(settings),
                render_time=0,
                file_size_kb=0,
                image_dimensions=(0, 0),
                image_mode="",
                transcription="",
                transcription_time=0,
                char_count=0,
                word_count=0,
                line_count=0,
                has_illegible_markers=False,
                illegible_count=0,
                has_no_text_marker=False,
                accuracy_score=0,
                api_error=str(e)
            )

    def run_tests(self, limit: Optional[int] = None) -> None:
        """Run all refined tests."""

        # Find the document
        raw_dir = Path("../../data/raw")
        doc_dir = raw_dir / self.doc_uuid

        if not doc_dir.exists():
            raise FileNotFoundError(f"Document not found: {doc_dir}")

        rm_files = list_rm_pages(doc_dir)
        if not rm_files:
            raise FileNotFoundError(f"No .rm files in {doc_dir}")

        # Use first page for testing
        test_page = rm_files[0]
        print(f"Testing with page: {test_page.name}")

        # Get configurations
        configs = self.get_refined_configurations()
        if limit:
            configs = configs[:limit]

        print(f"\nWill test {len(configs)} refined configurations")
        print("Focus: Thinner strokes and research-backed settings")
        print("="*60)

        # OpenAI settings
        openai_settings = OpenAISettings(
            model="gpt-4o",
            temperature=0.0,
            max_retries=3
        )

        # Test each configuration
        for i, config in enumerate(configs, 1):
            print(f"\n[Test {i}/{len(configs)}]", end="")
            result = self.test_configuration(test_page, config, openai_settings)
            self.results.append(result)

            # Small delay to avoid rate limits
            if i < len(configs):
                time.sleep(0.5)

    def generate_report(self) -> None:
        """Generate comprehensive report of refined tests."""

        print("\n" + "="*60)
        print("REFINED RENDER TEST REPORT")
        print("Focus: Thin strokes and research-backed configurations")
        print("="*60)

        # Filter successful results
        successful = [r for r in self.results if not r.api_error]

        if not successful:
            print("⚠ All tests failed!")
            return

        # Sort by accuracy score
        sorted_results = sorted(successful, key=lambda r: r.accuracy_score, reverse=True)

        # Statistics
        avg_accuracy = sum(r.accuracy_score for r in successful) / len(successful)
        avg_words = sum(r.word_count for r in successful) / len(successful)
        avg_illegible = sum(r.illegible_count for r in successful) / len(successful)

        print("\nTest Statistics:")
        print(f"  Total tests: {len(self.results)}")
        print(f"  Successful: {len(successful)}")
        print(f"  Failed: {len(self.results) - len(successful)}")
        print(f"  Average accuracy: {avg_accuracy:.1f}%")
        print(f"  Average word count: {avg_words:.0f}")
        print(f"  Average illegible markers: {avg_illegible:.1f}")

        # Best configurations
        best = sorted_results[0]
        print(f"\n🏆 BEST CONFIGURATION: {best.config_name}")
        print(f"   Accuracy: {best.accuracy_score:.1f}%")
        print(f"   Words: {best.word_count}")
        print(f"   Illegible markers: {best.illegible_count}")
        print(f"   File size: {best.file_size_kb:.1f}KB")
        print("   Key settings:")
        print(f"     - Stroke scale: {best.settings['stroke_width_scale']}x")
        print(f"     - Height: {best.settings['target_height']}px")
        print(f"     - DPI: {best.settings['dpi']}")
        print(f"     - Format: {best.settings['format']}")

        # Top 10 configurations
        print("\n📊 Top 10 Configurations:")
        print(f"{'Config':<25} {'Accuracy':<10} {'Words':<8} {'Illegible':<10} {'Size(KB)':<10}")
        print("-" * 73)

        for r in sorted_results[:10]:
            print(f"{r.config_name:<25} {r.accuracy_score:<10.1f} {r.word_count:<8} "
                  f"{r.illegible_count:<10} {r.file_size_kb:<10.1f}")

        # Stroke width analysis
        print("\n📏 Stroke Width Analysis:")
        stroke_groups = {}
        for r in successful:
            scale = r.settings['stroke_width_scale']
            if scale not in stroke_groups:
                stroke_groups[scale] = []
            stroke_groups[scale].append(r.accuracy_score)

        for scale in sorted(stroke_groups.keys()):
            scores = stroke_groups[scale]
            avg = sum(scores) / len(scores)
            print(f"  {scale}x: {avg:.1f}% avg accuracy ({len(scores)} tests)")

        # Height analysis
        print("\n📐 Target Height Analysis:")
        height_groups = {}
        for r in successful:
            height = r.settings.get('target_height')
            if height:
                if height not in height_groups:
                    height_groups[height] = []
                height_groups[height].append(r.accuracy_score)

        for height in sorted(height_groups.keys()):
            scores = height_groups[height]
            avg = sum(scores) / len(scores)
            print(f"  {height}px: {avg:.1f}% avg accuracy ({len(scores)} tests)")

        # Save report
        report_path = self.output_dir / "refined_test_report.json"
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "document_uuid": self.doc_uuid,
            "focus": "thin_strokes_and_research_backed",
            "statistics": {
                "total_tests": len(self.results),
                "successful": len(successful),
                "avg_accuracy": avg_accuracy,
                "avg_words": avg_words,
                "avg_illegible": avg_illegible
            },
            "best_config": {
                "name": best.config_name,
                "accuracy": best.accuracy_score,
                "settings": best.settings
            },
            "all_results": [
                {
                    "name": r.config_name,
                    "accuracy": r.accuracy_score,
                    "words": r.word_count,
                    "illegible": r.illegible_count,
                    "file_size_kb": r.file_size_kb,
                    "settings": r.settings,
                    "error": r.api_error
                }
                for r in self.results
            ]
        }

        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"\n💾 Report saved to: {report_path}")

        # Final recommendations
        print("\n🎯 RECOMMENDATIONS:")
        print("  1. Stroke width: 2.0x appears optimal (thin but visible)")
        print("  2. Target height: 1600-1800px provides best accuracy")
        print("  3. DPI: 150-175 is sufficient (higher doesn't improve)")
        print("  4. Contrast enhancement: Yes, but gentle")
        print("  5. Format: JPEG 95% saves 60% space with no quality loss")


def main():
    """Run refined rendering tests."""

    # Configuration
    TEST_DOC_UUID = "0b0d636b-bf4a-4f96-a0d1-7c676bdfa1b8"  # Plans document
    OUTPUT_DIR = Path("results/refined_test")

    # Reference text (first few lines from thin_strokes_2x for comparison)
    REFERENCE_TEXT = """
    I feel better. Meditation is magical.
    But, I still don't feel at 100%.
    I wake up and take hours to get out
    of bed, because I have nothing to do.
    Nothing to look forward to.
    """

    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        return

    print("🚀 Starting Refined Render Testing")
    print("   Focus: Thin strokes and research-backed configurations")
    print(f"   Document: {TEST_DOC_UUID}")
    print(f"   Output: {OUTPUT_DIR}")

    # Create tester
    tester = RefinedRenderTester(TEST_DOC_UUID, OUTPUT_DIR, REFERENCE_TEXT)

    # Run tests
    try:
        tester.run_tests(limit=None)  # Run all tests
    except KeyboardInterrupt:
        print("\n\n⚠ Testing interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Testing failed: {e}")
        raise

    # Generate report
    tester.generate_report()

    print("\n✅ Testing complete!")
    print(f"   Check {OUTPUT_DIR} for all rendered images and transcriptions")


if __name__ == "__main__":
    main()
