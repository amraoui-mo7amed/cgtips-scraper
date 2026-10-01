# CGTips 3D Desktop Platform

A modern, high-performance native desktop application built with **PySide6 (Qt Quick / QML)** and Python for browsing, scraping, and managing free SketchUp 3D models from [sketchup.cgtips.org](https://sketchup.cgtips.org).

---

## 🌟 Key Features

- **Explore & Remote Search**:
  - Live search across thousands of SketchUp 3D models with quick keyword suggestions.
  - Responsive 3-card widescreen grid with high-resolution thumbnail previews.
  - Instant article link copy with clipboard toast notifications and direct web links.

- **Categories & Feeds**:
  - Taxonomy hierarchy picker modal with tree navigation.
  - Live RSS feed preview with publish dates and batch scrape triggers.
  - Resilient layout with zero-flicker loading states.

- **Direct URL Resolver**:
  - Bypass countdown lockers and fetch 3D model archives (`.zip`) directly.
  - Real-time resolution logs streamed directly into the desktop console.

- **Downloads Library**:
  - Manage locally downloaded SketchUp models with file sizes and thumbnail previews.
  - Integrated lightbox image gallery.

- **Cross-Platform Native Binaries**:
  - **macOS**: Native `.app` packaged in `.dmg` and `.zip`.
  - **Windows**: Native standalone `.exe` and portable `.zip`.

---

## 🚀 Download Releases

Download precompiled standalone binaries for macOS and Windows from the [GitHub Releases](https://github.com/amraoui-mo7amed/cgtips-scraper/releases) page:

- **macOS**: `CGTips-3D-macOS.dmg` or `CGTips-3D-macOS.zip` (Apple Silicon & Intel)
- **Windows**: `CGTips-3D-Windows.zip` (contains `CGTips-3D.exe`)

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
