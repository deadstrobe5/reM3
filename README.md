# reM3 - reMarkable Sync Tool

**Sync your reMarkable tablet to your computer. Organize files and convert handwriting to text with AI.**

## What it does

1. **Downloads** your files from the tablet
2. **Organizes** them exactly like your tablet's folder structure  
3. **Converts handwriting to text** using AI models

## Quick Start

```bash
# Install and run
python3 -m pip install --user -r requirements.txt
python3 main.py
```

That's it! The program will:
- Guide you through setup (IP, password, etc.)
- Download your files  
- Organize them in readable folders
- Optionally convert handwriting to text

## What you get

Your tablet content organized on your computer:
```
~/reM3/data/
├── organized/          # Your exact tablet folder structure
│   ├── Notebooks/
│   ├── Work/
│   └── Personal/
├── catalog.json        # Searchable document index
└── text/              # AI-transcribed text files (optional)
```

## Commands

**Main workflow:**
```bash
python3 main.py                    # Interactive menu (recommended)
python3 main.py --auto-run         # Complete sync immediately
```

**Individual operations:**
```bash
python3 main.py sync               # Download + organize files
python3 main.py browse             # Search and view documents  
python3 main.py export-text        # Convert handwriting to text
```

## Features

- **Lightning-fast sync** - Smart detection only downloads changed files (10x faster on subsequent syncs)
- **Perfect organization** - Mirror your exact tablet folder structure with readable names - no UUIDs or mess
- **Powerful search** - Rich CLI with filters, date ranges, document types - find anything instantly
- **AI transcription** - Convert handwriting to text with multiple AI providers
- **🔥 Cracked Mode** - Advanced multi-model transcription using 3 AI models simultaneously for maximum accuracy
- **Cost optimization** - Choose from budget to premium options with real-time spending alerts
- **Universal AI support** - Works with OpenAI, OpenRouter, Claude, Qwen, or any OpenAI-compatible API
- **Production ready** - Parallel processing, retry logic, error recovery, and comprehensive logging

## AI Transcription Setup

Add to your `.env` file:

**Option 1: OpenAI (Standard)**
```bash
OPENAI_API_KEY=sk-your_key_here
```

**Option 2: OpenRouter (Budget-friendly)**
```bash
OPENAI_API_KEY=sk-or-v1-your_key_here
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=qwen/qwen2.5-vl-32b-instruct
```

**Option 3: Cracked Mode (Advanced)**
```bash
OPENAI_API_KEY=sk-or-v1-your_key_here
OPENAI_BASE_URL=https://openrouter.ai/api/v1
CRACKED_MODE=true
CRACKED_MODELS=gpt-4o,anthropic/claude-3-5-sonnet:beta,qwen/qwen2.5-vl-32b-instruct
CRACKED_MERGE_MODEL=gpt-4o
```
*Multi-model approach with intelligent merging. Higher cost but improved accuracy.*

## Tablet Setup

1. On your tablet: Settings → Help → About → Copyright → GPLv3 Compliance
2. Note the IP address, user, and password
3. Enable: Settings → General → Storage → USB Connection

---

## Detailed Documentation

### File Types Explained

- `{uuid}.metadata` - Document info (title, type, parent folder)
- `{uuid}.content` - Page count and file type info  
- `{uuid}.pdf/epub` - Imported documents
- `{uuid}/` - Notebook folder containing handwritten pages
- `{uuid}/*.rm` - Individual page files (reMarkable format)

### Advanced Usage

**Force full re-download:**
```bash
python3 main.py --auto-run --force-sync
```

**Preview without changes:**
```bash
python3 main.py --auto-run --dry-run
```

**Search and filter documents:**
```bash
python3 main.py browse --search "keyword"
python3 main.py browse --type notebook
python3 main.py browse --recent 30
```

**Transcribe specific document:**
```bash
python3 main.py export-text --uuid ABC123 --force
```

**Test transcription (single small document):**
```bash
python3 main.py export-text --test-transcribe --force
```

### Configuration

Copy `.env.example` to `.env` and customize:

```bash
# Connection
RM_HOST=10.11.99.1           # Tablet IP
RM_USER=root                 # SSH user  
RM_PASSWORD=your_password    # Tablet password

# Optional: AI transcription
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o

# Optional: Use OpenRouter instead
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=qwen/qwen2.5-vl-32b-instruct

# Optional: Cracked Mode (multi-model transcription)
CRACKED_MODE=true
CRACKED_MODELS=gpt-4o,anthropic/claude-3-5-sonnet:beta,qwen/qwen2.5-vl-32b-instruct
CRACKED_MERGE_MODEL=gpt-4o

# Optional: Processing
RM_WORKERS=3                 # Parallel transcription workers
RM_DPI=200                   # Image resolution for transcription
```

### Data Flow

1. **Pull** - Downloads files from `/home/root/.local/share/remarkable/xochitl/` to `data/raw/`
2. **Index** - Builds searchable catalog in `data/catalog.json`  
3. **Organize** - Creates readable structure in `data/organized/` 
4. **Export** - Renders pages as images, sends to AI, saves text to `data/text/`

### Troubleshooting

**Connection issues:**
- Keep tablet awake during sync
- For Wi-Fi, use tablet's Wi-Fi IP address  
- Check USB connection is enabled in tablet settings

**Transcription errors:**
- Verify API key is correct
- Check you have sufficient credits/quota
- Try with `--test-transcribe` first for small test

**Performance:**
- Subsequent syncs are much faster (only downloads changes)
- Use `--workers 1` to reduce API rate limiting
- Higher DPI = better transcription quality but larger files

### Cost Estimates

**OpenRouter Qwen-7B:** ~$0.001 per page (budget option)
**OpenRouter Qwen-32B:** ~$0.002 per page (good quality)  
**OpenAI GPT-4o:** ~$0.01 per page (high quality)
**Cracked Mode:** ~$0.021 per page (multi-model approach)

*Actual costs shown in real-time when using OpenRouter*

### Requirements

- Python 3.8+
- reMarkable tablet with SSH access
- Optional: OpenAI or OpenRouter API key for transcription

### Dependencies

- `paramiko` - SSH connection to tablet
- `pillow` - Image processing  
- `cairosvg` - SVG to image conversion
- `openai` - AI transcription API
- `rich` - Beautiful terminal interface