"""Convert GAO PDF reports to well-structured Markdown."""

import os
import re
import pymupdf4llm
import pymupdf


def pdf_to_markdown(pdf_path: str, title: str = "", report_id: str = "",
                    pub_date: str = "") -> str:
    """Convert a GAO PDF to clean, well-structured markdown."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Extract the Highlights page summary directly from PDF
    highlights = extract_highlights(pdf_path)

    # Identify the highlights page numbers to skip in body
    highlights_pages = find_highlights_pages(pdf_path)

    # Extract markdown using pymupdf4llm, skipping cover + highlights pages
    doc = pymupdf.open(pdf_path)
    total_pages = doc.page_count
    doc.close()

    # Pages to skip: cover (page 0) and highlights page(s)
    skip_pages = {0} | highlights_pages
    # Build the page list for extraction (0-indexed)
    pages_to_extract = [i for i in range(total_pages) if i not in skip_pages]

    if pages_to_extract:
        raw_md = pymupdf4llm.to_markdown(pdf_path, pages=pages_to_extract)
    else:
        raw_md = pymupdf4llm.to_markdown(pdf_path)

    # Post-process the markdown
    md = clean_gao_markdown(raw_md, title, report_id, pub_date, highlights)
    return md


def find_highlights_pages(pdf_path: str) -> set:
    """Find which pages contain the Highlights section."""
    doc = pymupdf.open(pdf_path)
    pages = set()
    for i in range(min(4, doc.page_count)):
        text = doc[i].get_text()
        if 'What GAO Found' in text and ('Highlights' in text or 'Why GAO' in text):
            pages.add(i)
    doc.close()
    return pages


def extract_highlights(pdf_path: str) -> dict:
    """Extract the Highlights page from a GAO PDF.

    GAO reports typically have a Highlights page (page 2) with
    'What GAO Found', 'Why GAO Did This Study', and 'What GAO Recommends'.
    """
    doc = pymupdf.open(pdf_path)
    highlights = {}

    for page_num in range(min(4, doc.page_count)):
        text = doc[page_num].get_text()
        if 'What GAO Found' not in text:
            continue

        # Extract "What GAO Found"
        found_match = re.search(
            r'What GAO Found\s*\n(.*?)(?=What GAO Recommends|Why GAO Did|$)',
            text, re.DOTALL
        )
        if found_match:
            highlights['what_found'] = _clean_highlights_text(found_match.group(1))

        # Extract "Why GAO Did This Study"
        why_match = re.search(
            r'Why GAO Did This Study\s*\n(.*?)(?=What GAO|$)',
            text, re.DOTALL
        )
        if why_match:
            highlights['why_study'] = _clean_highlights_text(why_match.group(1))

        # Extract "What GAO Recommends"
        rec_match = re.search(
            r'What GAO Recommends\s*\n(.*?)(?=View GAO|For more info|$)',
            text, re.DOTALL
        )
        if rec_match:
            highlights['recommendations'] = _clean_highlights_text(rec_match.group(1))

        break

    doc.close()
    return highlights


def _clean_highlights_text(text: str) -> str:
    """Clean up extracted highlights text."""
    # Remove figure references and captions
    text = re.sub(r'(?:See )?[Ff]igure \d+[^.]*\.?', '', text)
    # Remove "View GAO-..." references
    text = re.sub(r'View GAO-[\w-]+.*$', '', text, flags=re.MULTILINE)
    # Remove page references
    text = re.sub(r'\(see [fp]\w+ \d+\)', '', text, flags=re.IGNORECASE)
    # Collapse whitespace
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    return text.strip()


def clean_gao_markdown(raw_md: str, title: str = "", report_id: str = "",
                       pub_date: str = "", highlights: dict = None) -> str:
    """Clean and structure the raw markdown from PDF extraction."""
    highlights = highlights or {}
    content = raw_md
    rid_upper = report_id.upper() if report_id else ""

    # ========== Phase 1: Remove GAO boilerplate and artifacts ==========

    # Remove broken bold formatting from cover page (e.g., "**United** **States**...")
    content = re.sub(r'\*\*United\*\*\s*\*\*States\*\*\s*\*\*Government\s*Accountability\*\*\s*\*\*Office\*\*',
                     '', content)

    # Remove page number markers
    content = re.sub(r'\*\*Page [ivxlcdm\d]+\*\*\s*\*\*GAO-[\w-]+[^*]*\*\*', '', content)
    content = re.sub(r'^[*]*Page [ivxlcdm\d]+[*]*\s*$', '', content, flags=re.MULTILINE)

    # Remove stray "A ." artifacts (common on GAO cover pages)
    content = re.sub(r'^A\s*\.\s*$', '', content, flags=re.MULTILINE)

    # Remove image placeholders
    content = re.sub(r'!\[\]\([^)]*\)\s*\n?', '', content)

    # Remove TOC entries (lines like "Letter 1", "Background 5", "Appendix I 30")
    content = re.sub(
        r'^(?:Letter|Appendix [IVX]+|Results in Brief|Background|'
        r'Contents|Table of Contents|Figures?|Tables?|'
        r'Abbreviations|Scope and Methodology|Objectives,? Scope|'
        r'Conclusions?|Recommendations?|Agency Comments?)'
        r'\s+\d+\s*$', '', content, flags=re.MULTILINE)

    # Remove standalone "Contents" headers
    content = re.sub(r'^#{1,6}\s*(?:Table of )?Contents\s*$', '', content, flags=re.MULTILINE)

    # Remove GAO report ID lines in headers
    content = re.sub(r'^#{1,6}\s*GAO-[\d]+-[\d\w]+\s*$', '', content, flags=re.MULTILINE)

    # Remove duplicate highlights content from body (we have it separately)
    if highlights.get('what_found'):
        # Remove "What GAO Found" / "Why GAO Did This Study" sections in body
        content = re.sub(r'\*\*What GAO Found\*\*.*?(?=\*\*Why GAO|\*\*What GAO Recommends|#{1,6}|$)',
                         '', content, flags=re.DOTALL, count=1)
        content = re.sub(r'\*\*Why GAO Did This Study\*\*.*?(?=\*\*What GAO|#{1,6}|$)',
                         '', content, flags=re.DOTALL, count=1)
        content = re.sub(r'\*\*What GAO Recommends\*\*.*?(?=#{1,6}|$)',
                         '', content, flags=re.DOTALL, count=1)

    # Remove repeated "Report to Congressional..." lines after the first
    gao_report_pattern = r'(?:GAO\s+)?Report to Congressional (?:Requesters?|Committees?)'
    matches = list(re.finditer(gao_report_pattern, content, re.IGNORECASE))
    if len(matches) > 1:
        for m in reversed(matches[1:]):
            content = content[:m.start()] + content[m.end():]

    # Remove "For Release on Delivery" and date/time lines
    content = re.sub(r'^For Release on Delivery.*$', '', content, flags=re.MULTILINE)
    content = re.sub(r'^Expected at \d+.*$', '', content, flags=re.MULTILINE)

    # Improve figure placeholders: keep caption context
    content = re.sub(
        r'^Figure (\d+):\s*(.+?)(?:\s+\d+)?\s*$',
        r'*[Figure \1: \2 — see original PDF]*',
        content, flags=re.MULTILINE)
    # Generic figure removal markers
    content = re.sub(r'\*\[Figure removed from text conversion\]\*',
                     '*[Figure — see original PDF]*', content)

    # ========== Phase 2: Line-by-line cleanup ==========
    lines = content.split('\n')
    cleaned = []
    prev_blank = False
    seen_gao_header = False

    for line in lines:
        stripped = line.strip()

        # Skip empty page artifacts
        if re.match(r'^Page \d+ of \d+$', stripped):
            continue

        # Skip repeated GAO organization name
        if stripped in ('United States Government Accountability Office',
                        'U.S. Government Accountability Office',
                        'Government Accountability Office'):
            if seen_gao_header:
                continue
            seen_gao_header = True

        # Skip standalone report ID lines
        if re.match(r'^(?:\*\*)?GAO-\d+-\d+\w*(?:\*\*)?$', stripped):
            continue

        # Skip month/year lines that are just date stamps
        if re.match(r'^(?:January|February|March|April|May|June|July|August|'
                     r'September|October|November|December)\s+\d{4}$', stripped):
            continue

        # Skip "report to congressional" header lines
        if re.match(r'^#{1,6}\s*(?:A\s+)?(?:Report|Testimony|Letter) to', stripped, re.IGNORECASE):
            continue

        # Skip contact info lines from highlights page
        if re.match(r'^\[?For more information,? contact:', stripped):
            continue
        if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+ at \w+@gao\.gov', stripped):
            continue

        # Skip "View GAO-..." reference lines
        if re.match(r'^View GAO-', stripped):
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

    # ========== Phase 3: Assemble final document ==========
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

    # Insert highlights summary at top
    if highlights.get('what_found'):
        parts.append('## Highlights')
        parts.append(f"### What GAO Found\n\n{highlights['what_found']}")
        if highlights.get('why_study'):
            parts.append(f"### Why GAO Did This Study\n\n{highlights['why_study']}")
        if highlights.get('recommendations'):
            parts.append(f"### What GAO Recommends\n\n{highlights['recommendations']}")
        parts.append('---')

    parts.append(content)

    return '\n\n'.join(parts)


def get_pdf_metadata(pdf_path: str) -> dict:
    """Extract metadata from a PDF file."""
    doc = pymupdf.open(pdf_path)
    meta = doc.metadata
    page_count = doc.page_count
    doc.close()
    return {
        'title': meta.get('title', ''),
        'author': meta.get('author', ''),
        'subject': meta.get('subject', ''),
        'pages': page_count,
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
