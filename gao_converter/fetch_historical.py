"""Fetch historical GAO reports from GovInfo and process them."""

import json
import os
import requests

from .pdf_converter import pdf_to_markdown
from .epub_generator import markdown_to_epub

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# A curated selection of notable GAO reports available from GovInfo
HISTORICAL_REPORTS = [
    {
        'report_id': 'gao-08-137',
        'title': 'Climate Change: Agencies Should Develop Guidance for Addressing the Effects on Federal Land and Water Resources',
        'pub_date': '2007-08-01',
        'url': 'https://www.gao.gov/products/gao-08-137',
        'govinfo_id': 'GAO-08-137',
    },
    {
        'report_id': 'gao-07-1030t',
        'title': 'Cybersecurity: Federal Agencies Need to Improve Controls over Wireless Networks',
        'pub_date': '2007-07-12',
        'url': 'https://www.gao.gov/products/gao-07-1030t',
        'govinfo_id': 'GAO-07-1030T',
    },
    {
        'report_id': 'gao-08-467t',
        'title': 'Information Technology: Federal Agencies Need to Strengthen IT Capital Planning and Investment Control',
        'pub_date': '2008-02-13',
        'url': 'https://www.gao.gov/products/gao-08-467t',
        'govinfo_id': 'GAO-08-467T',
    },
    {
        'report_id': 'gao-07-106',
        'title': 'Financial Regulation: Industry Trends Continue to Challenge the Federal Regulatory Structure',
        'pub_date': '2007-10-01',
        'url': 'https://www.gao.gov/products/gao-07-106',
        'govinfo_id': 'GAO-07-106',
    },
    {
        'report_id': 'gao-08-322',
        'title': 'Health Care Transparency: Actions Needed to Improve Cost and Quality Information for Consumers',
        'pub_date': '2008-01-01',
        'url': 'https://www.gao.gov/products/gao-08-322',
        'govinfo_id': 'GAO-08-322',
    },
]


def fetch_and_process(max_reports=0):
    """Fetch historical reports from GovInfo and process them."""
    pdf_dir = os.path.join(DATA_DIR, 'pdfs')
    md_dir = os.path.join(DATA_DIR, 'markdown')
    epub_dir = os.path.join(DATA_DIR, 'epub')
    for d in [pdf_dir, md_dir, epub_dir]:
        os.makedirs(d, exist_ok=True)

    reports_to_process = HISTORICAL_REPORTS[:max_reports] if max_reports else HISTORICAL_REPORTS
    catalog_entries = []

    for info in reports_to_process:
        rid = info['govinfo_id']
        report_id = info['report_id']
        pdf_path = os.path.join(pdf_dir, f'{report_id}.pdf')

        print(f"Processing: {report_id} - {info['title'][:60]}...")

        # Download PDF
        if not os.path.exists(pdf_path):
            url = f"https://www.govinfo.gov/content/pkg/GAOREPORTS-{rid}/pdf/GAOREPORTS-{rid}.pdf"
            try:
                resp = requests.get(url, timeout=30)
                if resp.status_code == 200:
                    with open(pdf_path, 'wb') as f:
                        f.write(resp.content)
                    print(f"  Downloaded PDF ({len(resp.content):,} bytes)")
                else:
                    print(f"  PDF download failed: HTTP {resp.status_code}")
                    continue
            except Exception as e:
                print(f"  PDF download failed: {e}")
                continue

        # Convert to markdown
        md_path = os.path.join(md_dir, f'{report_id}.md')
        try:
            md = pdf_to_markdown(pdf_path, info['title'], report_id, info['pub_date'])
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md)
            print(f"  Converted to markdown ({len(md):,} chars)")
        except Exception as e:
            print(f"  Markdown conversion failed: {e}")
            continue

        # Generate EPUB
        epub_path = os.path.join(epub_dir, f'{report_id}.epub')
        try:
            markdown_to_epub(md, epub_path, title=info['title'], date=info['pub_date'])
            print(f"  Generated EPUB ({os.path.getsize(epub_path):,} bytes)")
        except Exception as e:
            print(f"  EPUB generation failed: {e}")

        catalog_entries.append({
            'report_id': report_id,
            'title': info['title'],
            'pub_date': info['pub_date'],
            'url': info['url'],
            'has_pdf': True,
            'has_markdown': True,
            'has_epub': os.path.exists(epub_path),
            'source': 'pdf',
        })

    # Merge with existing catalog
    catalog_path = os.path.join(DATA_DIR, 'catalog.json')
    if os.path.exists(catalog_path):
        with open(catalog_path, 'r') as f:
            existing = json.load(f)
        existing_ids = {e['report_id'] for e in existing}
        for entry in catalog_entries:
            if entry['report_id'] not in existing_ids:
                existing.append(entry)
        # Sort by date descending
        existing.sort(key=lambda x: x['pub_date'], reverse=True)
        catalog = existing
    else:
        catalog = catalog_entries

    with open(catalog_path, 'w') as f:
        json.dump(catalog, f, indent=2)

    print(f"\nProcessed {len(catalog_entries)} historical reports")
    return catalog_entries


if __name__ == '__main__':
    fetch_and_process()
