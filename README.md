## ✨ reM3 - reMarkable sync + organize (+ optional text export)

**reM3** mirrors your tablet's folders on your computer and gets a quick index. One simple command after install.

### 🌟 Features
- 🧩 First‑run wizard: prompts for IP/user/password, writes `.env`, can set up SSH keys
- 🔌 Pull: copies the tablet's raw storage files to `data/raw/`
- 📇 Index: builds `data/index.csv` (names, types, parents, page counts)
- 🗂️ Organize: recreates the same collection/doc structure under `data/organized/`
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
- Pull raw files into `data/raw`
- Create `data/index.csv` with document metadata
- Build `data/organized` mirroring your collections using symlinks

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

- Pull only (refresh `data/raw/` from the tablet):
```bash
python3 main.py pull
```

- Index only (rebuild `data/index.csv` from `data/raw/`):
```bash
python3 main.py index
```

- Organize only (rebuild `data/organized/` from `data/raw/` using symlinks):
```bash
python3 main.py organize --clear-dest
```

- Organize with copies (instead of symlinks) and include trash:
```bash
python3 main.py organize --copy --include-trash --clear-dest
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

- `data/raw` contains the raw files from the tablet
  - `<uuid>.metadata`: JSON with `visibleName`, `type` (DocumentType/CollectionType), parent
  - `<uuid>.content`: JSON with file type and page count
  - `<uuid>.pdf` / `.epub` / `.zip`: Imported documents
  - `<uuid>/`: Notebook pages (`.rm` files) and resources
  - `<uuid>.thumbnails/`: Preview images
- `data/index.csv`: Name/type/parent mapping for quick lookup
- `data/organized`: Reconstructed folder tree with symlinks (or copies if `--copy`)

### 💡 Tips
- Keep the tablet awake/unlocked while syncing.
- For Wi‑Fi, use the tablet's Wi‑Fi IP.
- Use `--dry-run` to preview what any command will do.
- Default data location is `~/reM3/data/` (configurable via `RM_BASE_DIR`).

### 🧪 Notes
- Sync/organize are solid and well-tested.
- Text export is experimental - requires OpenAI API key.
- Error messages include helpful emojis and recovery suggestions.


