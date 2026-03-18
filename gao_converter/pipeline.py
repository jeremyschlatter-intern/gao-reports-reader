"""Main pipeline: fetch GAO reports, convert to markdown/epub, generate site."""

import json
import os
import sys
from typing import Optional
import requests

from .rss_parser import fetch_reports, GAOReport
from .pdf_converter import pdf_to_markdown, summary_to_markdown
from .epub_generator import markdown_to_epub

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
PDF_DIR = os.path.join(DATA_DIR, 'pdfs')
MD_DIR = os.path.join(DATA_DIR, 'markdown')
EPUB_DIR = os.path.join(DATA_DIR, 'epub')
CATALOG_PATH = os.path.join(DATA_DIR, 'catalog.json')

# GovInfo PDF URL template (works for historical reports)
GOVINFO_PDF_URL = "https://www.govinfo.gov/content/pkg/GAOREPORTS-{rid}/pdf/GAOREPORTS-{rid}.pdf"


def ensure_dirs():
    """Create data directories if they don't exist."""
    for d in [PDF_DIR, MD_DIR, EPUB_DIR]:
        os.makedirs(d, exist_ok=True)


def _get_gao_session() -> requests.Session:
    """Create a requests session with browser-like headers for GAO.gov."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'application/pdf',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'DNT': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://www.gao.gov/',
    })
    return session


# Module-level session (reused across downloads)
_gao_session = None


def try_download_pdf(report: GAOReport) -> Optional[str]:
    """Try to download a PDF from various sources. Returns path or None."""
    global _gao_session

    pdf_path = os.path.join(PDF_DIR, report.pdf_filename)

    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000:
        return pdf_path

    # Try GAO.gov first (with browser-like headers)
    if _gao_session is None:
        _gao_session = _get_gao_session()

    try:
        resp = _gao_session.get(report.pdf_url, timeout=30)
        if (resp.status_code == 200 and
                'pdf' in resp.headers.get('content-type', '').lower() and
                len(resp.content) > 1000):
            with open(pdf_path, 'wb') as f:
                f.write(resp.content)
            print(f"  Downloaded PDF from GAO.gov ({len(resp.content):,} bytes)")
            return pdf_path
    except Exception as e:
        pass

    # Fall back to GovInfo (works for historical reports)
    rid = report.report_id.upper()
    govinfo_url = GOVINFO_PDF_URL.format(rid=rid)
    try:
        resp = requests.get(govinfo_url, timeout=30, stream=True)
        if resp.status_code == 200 and 'pdf' in resp.headers.get('content-type', '').lower():
            with open(pdf_path, 'wb') as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            size = os.path.getsize(pdf_path)
            if size > 1000:
                print(f"  Downloaded PDF from GovInfo ({size:,} bytes)")
                return pdf_path
            else:
                os.unlink(pdf_path)
    except Exception:
        pass

    return None


def process_report(report: GAOReport, force: bool = False) -> dict:
    """Process a single report: download PDF, convert to markdown and epub.

    Returns a dict with processing results.
    """
    result = {
        'report_id': report.report_id,
        'title': report.title,
        'pub_date': report.pub_date,
        'url': report.url,
        'has_pdf': False,
        'has_markdown': True,
        'has_epub': False,
        'source': 'rss_summary',
    }

    md_path = os.path.join(MD_DIR, report.markdown_filename)
    epub_path = os.path.join(EPUB_DIR, report.epub_filename)

    # Try to get the PDF
    pdf_path = try_download_pdf(report)

    if pdf_path:
        result['has_pdf'] = True
        result['source'] = 'pdf'

        # Convert PDF to markdown
        if not os.path.exists(md_path) or force:
            try:
                md_content = pdf_to_markdown(
                    pdf_path, report.title, report.report_id, report.pub_date
                )
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                print(f"  Converted PDF to markdown: {report.markdown_filename}")
            except Exception as e:
                print(f"  PDF conversion failed ({e}), using RSS summary")
                md_content = summary_to_markdown(report)
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                result['source'] = 'rss_summary'
        else:
            with open(md_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
    else:
        # Use RSS summary as markdown
        md_content = summary_to_markdown(report)
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        result['source'] = 'rss_summary'

    # Generate EPUB
    if not os.path.exists(epub_path) or force:
        try:
            markdown_to_epub(md_content, epub_path,
                             title=report.title, date=report.pub_date)
            result['has_epub'] = True
            print(f"  Generated EPUB: {report.epub_filename}")
        except Exception as e:
            print(f"  EPUB generation failed: {e}")
    else:
        result['has_epub'] = True

    return result


def run_pipeline(max_reports: int = 0, force: bool = False):
    """Run the full pipeline: fetch RSS, process reports, update catalog."""
    ensure_dirs()

    print("Fetching GAO RSS feed...")
    reports = fetch_reports()
    print(f"Found {len(reports)} reports\n")

    if max_reports:
        reports = reports[:max_reports]

    catalog = []
    for i, report in enumerate(reports):
        print(f"[{i+1}/{len(reports)}] Processing: {report.report_id}")
        print(f"  Title: {report.title}")
        result = process_report(report, force=force)
        catalog.append(result)
        print()

    # Save catalog
    with open(CATALOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    print(f"Catalog saved to {CATALOG_PATH}")

    # Summary
    pdf_count = sum(1 for c in catalog if c['has_pdf'])
    epub_count = sum(1 for c in catalog if c['has_epub'])
    print(f"\nSummary: {len(catalog)} reports processed")
    print(f"  PDFs downloaded: {pdf_count}")
    print(f"  EPUBs generated: {epub_count}")
    print(f"  Markdown files: {len(catalog)}")

    return catalog


def process_local_pdf(pdf_path: str, title: str = "", report_id: str = "",
                       pub_date: str = "") -> dict:
    """Process a local PDF file through the pipeline."""
    ensure_dirs()

    if not report_id:
        report_id = os.path.splitext(os.path.basename(pdf_path))[0]

    md_content = pdf_to_markdown(pdf_path, title, report_id, pub_date)

    md_path = os.path.join(MD_DIR, f"{report_id}.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    epub_path = os.path.join(EPUB_DIR, f"{report_id}.epub")
    markdown_to_epub(md_content, epub_path, title=title, date=pub_date)

    return {
        'markdown_path': md_path,
        'epub_path': epub_path,
        'report_id': report_id,
    }


if __name__ == '__main__':
    max_reports = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    run_pipeline(max_reports=max_reports)
