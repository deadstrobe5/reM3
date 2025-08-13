## ✨ reM3 - reMarkable sync + organize (+ optional text export)

**reM3** mirrors your tablet's folders on your computer and gets a quick index. One simple command after install.

### 🌟 Features
- 🧩 First‑run wizard: prompts for IP/user/password, writes `.env`, can set up SSH keys
- 🚀 Smart sync: only downloads new/changed files (preserves timestamps)
- 🔌 Pull: copies the tablet's raw storage files to `data/raw/`
- 📇 Catalog: builds `data/catalog.json` with searchable document metadata
- 🔍 Browse: search, filter and view documents with rich CLI interface
- 🗂️ Organize: recreates your exact tablet collection structure under `data/organized/`
- 📝 Optional text export: per‑document `.txt` via vision (experimental)

### 🧭 Quick start (USB or Wi‑Fi)
1) On the tablet: \
Go to Settings → Help → About → Copyright and licenses → GPLv3 Compliance. \
Check the user (usually `root`), password and IP. \
Enable “USB connection” in General → Storage settings

2) Run these commands:

### 🚀 TL;DR (two commands)
```bash
python3 -m pip install --user -r requirements.txt
python3 main.py
```

This will:

- Ask for IP/user/password once, write the `.env` and set up SSH keys for automatic access in subsequent runs.
- Smart sync: only download new/changed files to `data/raw` (much faster on subsequent runs)
- Create `data/catalog.json` with searchable document metadata
- Build `data/organized` preserving your exact tablet folder structure

Tip: next time it's even simpler — just run:
```bash
python3 main.py
```

Want to see what would happen without doing it? Add `--dry-run`:
```bash
python3 main.py --dry-run
```

### 🔧 Advanced (optional)
Only read this if you want more control.

- Sync everything (pull + index + organize):
```bash
python3 main.py sync
```

- Pull only (smart sync from tablet):
```bash
python3 main.py pull
```

- Index only (rebuild `data/catalog.json` from `data/raw/`):
```bash
python3 main.py index
```

- Organize only (rebuild `data/organized/` preserving tablet structure):
```bash
python3 main.py organize
```

- Browse and search your documents:
```bash
python3 main.py browse                          # Show recent documents
python3 main.py browse --search "keyword"       # Search by title
python3 main.py browse --type notebook          # Filter notebooks only
python3 main.py browse --recent 30              # Last 30 days
python3 main.py browse --include-trash          # Include deleted items
```

- See what any command would do without doing it:
```bash
python3 main.py sync --dry-run
```

### 📝 Export text (optional)
Single document (replace with your UUID):
```bash
export OPENAI_API_KEY=sk-...
python3 main.py export-text --uuid <uuid> --model gpt-4o --workers 1
```

### Layout and file types

- `data/raw` contains the raw files from the tablet (smart sync only downloads changed files)
  - `<uuid>.metadata`: JSON with `visibleName`, `type` (DocumentType/CollectionType), parent
  - `<uuid>.content`: JSON with file type and page count
  - `<uuid>.pdf` / `.epub` / `.zip`: Imported documents
  - `<uuid>/`: Notebook pages (`.rm` files) and resources
  - `<uuid>.thumbnails/`: Preview images
- `data/catalog.json`: Searchable document catalog with metadata and statistics
- `data/organized`: Your exact tablet folder structure with readable names (copies, not symlinks)

### 💡 Tips
- Keep the tablet awake/unlocked while syncing.
- For Wi‑Fi, use the tablet's Wi‑Fi IP.
- Smart sync makes subsequent syncs much faster (only downloads changes).
- Use `python3 main.py browse` to search and explore your documents.
- Use `--dry-run` to preview what any command will do.
- Default data location is `~/reM3/data/` (configurable via `RM_BASE_DIR`).

### 🧪 Notes
- Smart sync and organize preserve your exact tablet structure.
- Browse command provides powerful search and filtering.
- Text export is experimental - requires OpenAI API key.
- Error messages include helpful emojis and recovery suggestions.


