#!/usr/bin/env python3
"""
GAO Report Converter - Command Line Tool

Convert GAO report PDFs to Markdown, EPUB, and HTML.

Usage:
    # Convert a single PDF
    python convert.py report.pdf

    # Convert with custom title
    python convert.py report.pdf --title "My Report Title"

    # Fetch latest reports from GAO RSS feed
    python convert.py --fetch

    # Fetch and build the browsable website
    python convert.py --fetch --build-site

    # Build website from existing data
    python convert.py --build-site
"""

import argparse
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def convert_pdf(args):
    """Convert a local PDF file."""
    from gao_converter.pdf_converter import pdf_to_markdown
    from gao_converter.epub_generator import markdown_to_epub, markdown_to_html

    pdf_path = args.pdf
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    basename = os.path.splitext(os.path.basename(pdf_path))[0]
    title = args.title or basename
    report_id = args.report_id or basename
    output_dir = args.output or '.'

    os.makedirs(output_dir, exist_ok=True)

    print(f"Converting: {pdf_path}")

    # Convert to markdown
    md = pdf_to_markdown(pdf_path, title, report_id, args.date or '')
    md_path = os.path.join(output_dir, f'{basename}.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md)
    print(f"  Markdown: {md_path} ({len(md):,} chars)")

    # Convert to EPUB
    epub_path = os.path.join(output_dir, f'{basename}.epub')
    markdown_to_epub(md, epub_path, title=title, date=args.date or '')
    print(f"  EPUB: {epub_path} ({os.path.getsize(epub_path):,} bytes)")

    # Convert to HTML
    html_path = os.path.join(output_dir, f'{basename}.html')
    markdown_to_html(md, html_path, title=title)
    print(f"  HTML: {html_path}")

    print("\nDone! Transfer the .epub file to your Kindle or e-reader.")


def fetch_reports(args):
    """Fetch latest reports from GAO RSS feed."""
    from gao_converter.pipeline import run_pipeline
    run_pipeline(max_reports=args.max_reports)


def build_site(args):
    """Build the browsable static website."""
    from gao_converter.site_generator import generate_site
    generate_site()
    site_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'site')
    print(f"\nTo view the site, run:")
    print(f"  python -m http.server 8080 -d {site_dir}")
    print(f"  Then open http://localhost:8080 in your browser")


def main():
    parser = argparse.ArgumentParser(
        description='GAO Report Converter - Transform GAO PDFs to Markdown, EPUB, and HTML',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('pdf', nargs='?', help='Path to a GAO PDF to convert')
    parser.add_argument('--title', '-t', help='Report title')
    parser.add_argument('--report-id', '-r', help='GAO report ID')
    parser.add_argument('--date', '-d', help='Publication date (YYYY-MM-DD)')
    parser.add_argument('--output', '-o', help='Output directory (default: current dir)')
    parser.add_argument('--fetch', action='store_true',
                       help='Fetch latest reports from GAO RSS feed')
    parser.add_argument('--max-reports', type=int, default=0,
                       help='Maximum number of reports to fetch (0=all)')
    parser.add_argument('--build-site', action='store_true',
                       help='Build the browsable static website')

    args = parser.parse_args()

    if not args.pdf and not args.fetch and not args.build_site:
        parser.print_help()
        sys.exit(0)

    if args.fetch:
        fetch_reports(args)

    if args.pdf:
        convert_pdf(args)

    if args.build_site:
        build_site(args)


if __name__ == '__main__':
    main()
