# GAO Reports to Markdown - Implementation Plan

## Goal
Transform GAO reports from PDFs into readable markdown, epub, and HTML formats.
Host them on a browsable website where users can search, read, and download reports
in their preferred format (including epub for Kindle).

## Architecture

### 1. Data Pipeline (`gao_converter/`)
- **RSS Parser**: Fetch GAO RSS feed for recent report metadata (title, date, summary, report ID)
- **PDF Downloader**: Download PDFs from GovInfo (works) and GAO.gov (requires workarounds)
- **PDF-to-Markdown**: Convert PDFs to clean, well-structured markdown using pymupdf4llm
- **Format Generator**: Convert markdown to epub (via pandoc) and HTML

### 2. Static Website (`site/`)
- Browse recent GAO reports with search/filter
- Read reports inline in clean HTML
- Download in multiple formats: Markdown, EPUB, PDF (original)
- Responsive design, works on mobile
- No backend needed - pure static HTML/CSS/JS

### 3. Report Sources
- **GovInfo API**: Historical reports (FY93-2008) - PDFs accessible
- **GAO RSS Feed**: Recent report metadata and summaries
- **Local PDFs**: Users can drag-and-drop or provide PDF files for conversion
- **Bundled reports**: Pre-converted selection of important recent reports

## Tech Stack
- Python 3.9+ for the conversion pipeline
- pymupdf4llm for PDF text extraction
- pandoc for epub generation
- Vanilla HTML/CSS/JS for the website (no framework needed)

## Implementation Steps
1. Set up Python environment and install dependencies
2. Build RSS feed parser
3. Build PDF-to-markdown converter
4. Build epub generator
5. Build the static website
6. Process a batch of reports
7. Polish and iterate with DC agent feedback
