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
    # First pass: remove GAO-specific artifacts at the text level
    content = raw_md

    # Remove page number markers (e.g., "**Page 1** **GAO-07-283**" or "Page i")
    content = re.sub(r'\*\*Page [ivxlcdm\d]+\*\*\s*\*\*GAO-[\w-]+[^*]*\*\*', '', content)
    content = re.sub(r'^[*]*Page [ivxlcdm\d]+[*]*\s*$', '', content, flags=re.MULTILINE)

    # Remove image placeholders that are just artifacts
    content = re.sub(r'!\[\]\([^)]*\)\s*\n?', '', content)

    # Remove TOC-style lines like "Letter 1" "Results in Brief 4" "Appendix I 30"
    # These are lines that end with a number and are typical TOC entries
    content = re.sub(r'^(?:Letter|Appendix [IVX]+|Results in Brief|Background|'
                     r'Contents|Table of Contents|Figures?|Tables?|'
                     r'Abbreviations|Scope and Methodology|Objectives,? Scope)'
                     r'\s+\d+\s*$', '', content, flags=re.MULTILINE)

    # Remove standalone "Contents" or "Table of Contents" headers followed by TOC
    content = re.sub(r'^#{1,6}\s*(?:Table of )?Contents\s*$', '', content, flags=re.MULTILINE)

    # Remove GAO report identifier lines that appear as headers/footers
    content = re.sub(r'^#{1,6}\s*GAO-[\d]+-[\d\w]+\s*$', '', content, flags=re.MULTILINE)

    # Remove repeated "GAO Report to..." lines after the first
    gao_report_pattern = r'(?:GAO\s+)?Report to Congressional (?:Requesters?|Committees?)'
    matches = list(re.finditer(gao_report_pattern, content, re.IGNORECASE))
    if len(matches) > 1:
        # Keep only the first occurrence
        for m in reversed(matches[1:]):
            content = content[:m.start()] + content[m.end():]

    # Strip figure/table reference lines where figures are removed
    content = re.sub(r'^Figure \d+:.*?(?:\d+\s*)?$', r'*[Figure removed from text conversion]*',
                     content, flags=re.MULTILINE)

    # Second pass: line-by-line cleanup
    lines = content.split('\n')
    cleaned = []
    prev_blank = False
    seen_gao_header = False

    for line in lines:
        stripped = line.strip()

        # Skip empty page artifacts
        if re.match(r'^Page \d+ of \d+$', stripped):
            continue

        # Skip repeated GAO organization name (keep first only)
        if stripped in ('United States Government Accountability Office',
                        'U.S. Government Accountability Office',
                        'Government Accountability Office'):
            if seen_gao_header:
                continue
            seen_gao_header = True

        # Skip standalone report ID lines
        if re.match(r'^(?:\*\*)?GAO-\d+-\d+\w*(?:\*\*)?$', stripped):
            continue

        # Skip "For Release on Delivery" type lines (keep content meaningful)
        if re.match(r'^For Release on Delivery', stripped):
            continue
        if re.match(r'^Expected at \d+', stripped):
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

    # Build the final document with front matter
    parts = []

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
