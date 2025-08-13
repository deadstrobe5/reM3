# Render Optimization

Testing suite for finding the optimal image rendering configuration for handwriting recognition.

## Usage

```bash
python test_render.py
```

## Results

After testing 26+ configurations, the optimal settings are:

- **Stroke width**: 2.0x (thin enhancement preserves accuracy)
- **Image height**: 2000px (better for complex/mixed-language text)
- **DPI**: 200
- **Format**: JPEG 95% (60% smaller than PNG, same quality)

## What We Learned

✅ **Do**: Use thin strokes, white background, gentle contrast  
❌ **Don't**: Binarize, over-thicken strokes, use low resolution

The optimal configuration has been integrated into the main pipeline.