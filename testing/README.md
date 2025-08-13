# reMarkable Handwriting Recognition Testing

## Overview

This directory contains test suites for optimizing handwritten note recognition from reMarkable tablets using OpenAI's vision models.

## Problem Solved

Initial rendering produced images that looked correct to humans but failed AI recognition. The issue was resolved through systematic testing of rendering configurations.

## Key Findings

### 🎯 Optimal Configuration

```python
RenderSettings(
    dpi=200,
    format="jpeg",
    quality=95,
    stroke_width_scale=2.0,  # Thin strokes preserve accuracy
    target_height=2000,       # Higher than expected optimal
    force_white_background=True,
    enhance_contrast=True,
    binarize=False           # Never binarize!
)
```

### 📊 What Works

- **Thin strokes (2.0x)**: Preserves handwriting characteristics better than thicker enhancement
- **2000px height**: Optimal for complex mixed-language text
- **White background**: Essential for recognition
- **JPEG 95%**: Saves 60% file size with no quality loss
- **Gentle processing**: Light contrast enhancement without binarization

### ❌ What Doesn't Work

- Binarization (destroys grayscale information)
- Stroke enhancement >3x (makes text blob-like)
- Images <1000px (poor recognition)
- Transparent backgrounds

## Test Results Summary

| Configuration | Accuracy | File Size | Key Insight |
|--------------|----------|-----------|-------------|
| 2.0x strokes, 2000px | 98% | 292KB | Best for mixed languages |
| 2.0x strokes, 1600px | 95% | 210KB | Good balance |
| 3.0x strokes, 2048px | 92% | 745KB | Over-processed |

## Usage

The optimal configuration has been integrated into the main pipeline (`src/export_text.py`).

## Directory Structure

```
testing/
├── render_optimization/    # Image rendering tests
│   └── results/           # Test outputs (gitignored)
└── model_comparison/      # Future: Compare different AI models
```

---

*Note: Test results and personal documents are excluded from version control.*