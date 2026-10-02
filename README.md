# CGTips 3D Desktop Platform

A modern, high-performance native desktop application built with **PySide6 (Qt Quick / QML)** and Python for browsing, scraping, and managing free SketchUp 3D models from [sketchup.cgtips.org](https://sketchup.cgtips.org).

---

## 🌟 Key Features

- **Categories & Feeds**:
  - Taxonomy hierarchy picker modal with tree navigation.
  - Live RSS feed preview with publish dates and batch scrape triggers.
  - Resilient layout with zero-flicker loading states.

- **Direct URL Resolver**:
  - Bypass countdown lockers and fetch 3D model archives (`.zip`) directly.
  - Real-time resolution logs streamed directly into the desktop console.

- **Download Status**: a header button shows running downloads and imports; click it for every job's progress, size and failure reason.

- **Downloads Library**:
  - Manage locally downloaded SketchUp models with file sizes and thumbnail previews.
  - Integrated lightbox image gallery.

- **Bulk Download**:
  - In *Categories & Feeds*, tick articles (checkbox on each card) and press **Download selected**, or download a **whole sub-category** / **whole category** straight from its RSS feeds (optional per-feed limit, models and/or images).
  - One shared browser, live progress bar with cancel, and automatic skipping of anything already in the library — so an interrupted run can simply be started again.
  - Files land in `<storage>/<category>/<sub-category>/<article>/`.

- **Storage Location**: change where models are saved from *Settings* (optionally moving existing downloads). The choice is remembered in `data/settings.json`.

- **Cache Export / Import**: *Settings → Cache Backup* packs categories, feed history and thumbnails into one `.zip` and restores it on another machine, so nothing has to be fetched again.

- **Import Existing Downloads**: *Library → Import folder / Import files* adds model archives (`.zip .rar .7z .skp`) and images you already have. Folders laid out as `category/sub-category/article/model/…` keep their structure; loose archives are filed under "Imported". Files are copied (or moved).

- **Cross-Platform Native Binaries**:
  - **macOS**: Native `.app` packaged in `.dmg` and `.zip`.
  - **Windows**: Native standalone `.exe` and portable `.zip`.

---

## 🚀 Download Releases

Download precompiled standalone binaries for macOS and Windows from the [GitHub Releases](https://github.com/amraoui-mo7amed/cgtips-scraper/releases) page:

- **macOS**: `CGTips-3D-macOS.dmg` or `CGTips-3D-macOS.zip` (Apple Silicon & Intel)
- **Windows**: `CGTips-3D-Windows.zip` — unzip the whole folder and run `CGTips-3D.exe` (keep it next to its `_internal` folder; Chromium is bundled, no install needed)

---

## 💻 Running from Source

### Prerequisites
- Python 3.10+ (tested on Python 3.11, 3.12, 3.14)
- Git

### Setup
```bash
git clone https://github.com/amraoui-mo7amed/cgtips-scraper.git
cd cgtips-scraper

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run desktop application
python desktop/main.py
```

### Packaging Locally with PyInstaller
```bash
pip install pyinstaller
pyinstaller --clean -y cgtips_desktop.spec
```
The output binary will be generated in `dist/`.
