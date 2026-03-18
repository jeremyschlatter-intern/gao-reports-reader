# GAO Reports Reader

**Read GAO reports anywhere** — on your Kindle, in your browser, or in any app that handles Markdown.

**Live site: [jeremyschlatter-intern.github.io/gao-reports-reader](https://jeremyschlatter-intern.github.io/gao-reports-reader/)**

## What This Does

The Government Accountability Office publishes reports as PDFs. This tool converts them to open, portable formats:

- **EPUB** — for Kindle, Kobo, Apple Books, and other e-readers
- **Markdown** — for note-taking apps, text editors, and version control
- **HTML** — for clean in-browser reading

Each report surfaces the **Highlights** section (What GAO Found, Why GAO Did This Study, What GAO Recommends) at the top for quick scanning, followed by the full report text.

## Features

- **31 reports** currently available (25 recent + 6 historical), all converted from full GAO PDFs
- **Topic filtering** — browse by category (Defense, Health Care, Cybersecurity, etc.)
- **Search** — find reports by keyword, title, or report ID
- **RSS feed** — subscribe at `/feed.xml` for updates
- **One-click downloads** — Markdown, EPUB, or read online

## How It Works

1. Fetches report metadata from the [GAO RSS feed](https://www.gao.gov/rss/reports.xml)
2. Downloads PDFs from GAO.gov
3. Extracts the Highlights page summary directly from the PDF
4. Converts the full report body to Markdown using [pymupdf4llm](https://pypi.org/project/pymupdf4llm/)
5. Generates EPUB files using [pandoc](https://pandoc.org/)
6. Builds a static website deployed to GitHub Pages

## Convert Your Own GAO PDF

```bash
# Install dependencies
pip install -r requirements.txt

# Convert a single PDF
python convert.py your-report.pdf

# Fetch latest reports from the GAO RSS feed
python convert.py --fetch

# Build the static website
python convert.py --fetch --build-site
```

## Requirements

- Python 3.9+
- [pandoc](https://pandoc.org/installing.html) (for EPUB generation)
- Dependencies in `requirements.txt`

## Architecture

```
gao_converter/
  rss_parser.py       # Fetches GAO RSS feed for report metadata
  pdf_converter.py    # PDF → Markdown (with Highlights extraction)
  epub_generator.py   # Markdown → EPUB via pandoc
  site_generator.py   # Generates the static website
  feed_generator.py   # Generates RSS feed
  pipeline.py         # Orchestrates the full pipeline
  fetch_historical.py # Fetches older reports from GovInfo API

convert.py            # CLI entry point
docs/                 # Static site (served by GitHub Pages)
data/                 # Generated data (markdown, epub, catalog)
```

## License

GAO reports are public domain works of the U.S. Government. This conversion tool is provided as-is.
