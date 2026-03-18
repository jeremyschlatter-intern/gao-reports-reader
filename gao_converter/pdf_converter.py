"""Convert GAO PDF reports to well-structured Markdown."""

import os
import re
import pymupdf4llm
import pymupdf


def pdf_to_markdown(pdf_path: str, title: str = "", report_id: str = "",
                    pub_date: str = "") -> str:
    """Convert a GAO PDF to clean, well-structured markdown.

    Args:
        pdf_path: Path to the PDF file
        title: Report title (used in header)
        report_id: GAO report ID (e.g., gao-26-108116)
        pub_date: Publication date

    Returns:
        Clean markdown string
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Extract markdown using pymupdf4llm
    raw_md = pymupdf4llm.to_markdown(pdf_path)

    # Post-process the markdown
    md = clean_gao_markdown(raw_md, title, report_id, pub_date)
    return md


def clean_gao_markdown(raw_md: str, title: str = "", report_id: str = "",
                       pub_date: str = "") -> str:
    """Clean and structure the raw markdown from PDF extraction."""
    lines = raw_md.split('\n')
    cleaned = []
    skip_next_blank = False
    prev_blank = False

    for line in lines:
        stripped = line.strip()

        # Skip page markers and artifacts
        if re.match(r'^Page \d+ of \d+$', stripped):
            continue
        if re.match(r'^-{3,}$', stripped) and not cleaned:
            continue
        # Skip repeated GAO header/footer patterns
        if re.match(r'^GAO-\d+-\d+', stripped) and len(stripped) < 30:
            continue
        if stripped in ('United States Government Accountability Office',
                        'U.S. Government Accountability Office'):
            # Keep first occurrence only
            if any('Government Accountability Office' in c for c in cleaned):
                continue

        # Normalize excessive blank lines
        if not stripped:
            if prev_blank:
                continue
            prev_blank = True
        else:
            prev_blank = False

        cleaned.append(line)

    content = '\n'.join(cleaned).strip()

    # Remove image placeholders that are just artifacts
    content = re.sub(r'!\[\]\([^)]*\)\s*\n?', '', content)

    # Build the final document with front matter
    parts = []

    # Add title and metadata header
    if title:
        parts.append(f"# {title}")
    if report_id or pub_date:
        meta = []
        if report_id:
            meta.append(f"**Report:** {report_id.upper()}")
        if pub_date:
            meta.append(f"**Published:** {pub_date}")
        meta.append(f"**Source:** [U.S. Government Accountability Office](https://www.gao.gov/products/{report_id})")
        parts.append(' | '.join(meta))

    parts.append('---')
    parts.append(content)

    return '\n\n'.join(parts)


def get_pdf_metadata(pdf_path: str) -> dict:
    """Extract metadata from a PDF file."""
    doc = pymupdf.open(pdf_path)
    meta = doc.metadata
    doc.close()
    return {
        'title': meta.get('title', ''),
        'author': meta.get('author', ''),
        'subject': meta.get('subject', ''),
        'pages': doc.page_count if hasattr(doc, 'page_count') else 0,
    }


def summary_to_markdown(report) -> str:
    """Convert a GAOReport (from RSS) to markdown using its summary content."""
    parts = []
    parts.append(f"# {report.title}")

    meta = []
    meta.append(f"**Report:** {report.report_id.upper()}")
    meta.append(f"**Published:** {report.pub_date}")
    meta.append(f"**Source:** [U.S. Government Accountability Office]({report.url})")
    parts.append(' | '.join(meta))

    parts.append('---')
    parts.append(report.summary)
    parts.append('')
    parts.append('---')
    parts.append(f'*This report summary was extracted from the [GAO RSS feed]({report.url}). '
                 f'For the complete report, visit the [GAO website]({report.url}).*')

    return '\n\n'.join(parts)


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pdf_converter.py <pdf_path> [title] [report_id] [pub_date]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else ""
    report_id = sys.argv[3] if len(sys.argv) > 3 else ""
    pub_date = sys.argv[4] if len(sys.argv) > 4 else ""

    md = pdf_to_markdown(pdf_path, title, report_id, pub_date)
    print(md)
