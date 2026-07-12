# cgtips-scraper

Scrapes [sketchup.cgtips.org](https://sketchup.cgtips.org) for SketchUp 3D models. Fetches RSS feeds, downloads model files and article images, and handles Google Drive download locker links.

## Features

- **Interactive CLI** — step-by-step selection of category, subcategory, and how many items to process
- **RSS feed pagination** — iterates through feed pages (up to 50) until requested item count is met
- **Download locker extraction** — extracts the hidden locker URL from article pages
- **GDrive quota bypass** — uses Google Drive API to copy shared files to your Drive and download without quota limits
- **Two-tier download** — fast `requests` path first, Playwright fallback with signed-in Google session
- **Image downloading** — optional, with caching support (skips already-downloaded images)
- **Progress bars** — `tqdm` for model downloads
- **Session caching** — `selected_feeds.json` tracks already-downloaded models and images
- **Cloudflare bypass** — `cloudscraper` for feed and article page requests

## Prerequisites

- Python 3.12+
- [Brave Browser](https://brave.com/) (for Playwright download locker navigation)
- A Google Cloud project with Drive API enabled (for quota bypass)

## Setup

1. Clone the repo:
   ```
   git clone https://github.com/amraoui-mo7amed/cgtips-scraper.git
   cd cgtips-scraper
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   playwright install chromium
   ```

3. Create a `.env` file:
   ```
   USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36
   ```

4. **Optional — GDrive quota bypass**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a project → Enable **Google Drive API**
   - **APIs & Services → Credentials** → Create OAuth client ID (Desktop app)
   - Download JSON and save as `credentials.json` in the project root
   - In **OAuth consent screen**, add your email as a Test user

## Usage

```
python main.py
```

1. Select a category from the list
2. Select subcategory(ies) — comma-separated numbers, or `0` for all
3. Enter max items per feed to process (`0` = unlimited, capped at 50 pages)
4. Choose whether to download article images
5. The scraper fetches feeds, extracts download URLs, downloads models and images

### Output structure

```
feeds/
  <category>/
    <subcategory>/
      <article-title>/
        model/
          <filename>.zip
        image_1.jpg
        image_2.jpg
        ...
```

### Caching

- `categories.json` — cached category/subcategory list (delete to re-scrape)
- `selected_feeds.json` — download history; entries with existing model files are skipped on re-run
- `token.pickle` — Google Drive API OAuth token (re-generate by deleting the file)

## Project files

| File | Purpose |
|---|---|
| `main.py` | Interactive CLI entry point, entry processing loop |
| `utils.py` | Feed fetching, locker extraction, GDrive download logic |
| `scraper.py` | Playwright-based category/subcategory scraping |
| `gdrive_api.py` | Google Drive API copy + download (quota bypass) |
| `categories.json` | Cached category hierarchy |
| `selected_feeds.json` | Download history and cache |

## How it works

1. **Feed fetching** — `cloudscraper` requests RSS feeds with `?paged=N` pagination. Falls back to Playwright if Cloudflare blocks.
2. **Download URL extraction** — `extract_download_url()` fetches the article page and finds the hidden content locker `<code>` element.
3. **Locker navigation** — Playwright navigates to the locker URL, waits for the countdown, and extracts the GDrive link.
4. **GDrive download** — Three tiers:
   - `_download_req` — raw `requests` download (fast, but quota-limited)
   - `copy_and_download` — Drive API: copies file to your Drive → downloads the copy (bypasses quota)
   - `_download_pw` — Playwright with signed-in Google session (slowest fallback)
5. **Image download** — Playwright navigates to the article, scans `.entry-content img` elements, downloads images to disk.

## Troubleshooting

- **Feed returns 0 entries** — Cloudflare blocking. The Playwright fallback should handle it if a browser is available.
- **"Quota exceeded" on GDrive** — The `_download_req` path detects this. The Drive API fallback copies the file to your Drive first, which bypasses the quota.
- **OAuth `access_denied`** — Your email isn't added as a test user in the OAuth consent screen.
- **`TargetClosedError` / `greenlet` errors** — Ignore these; they're benign async cleanup messages from Playwright.
