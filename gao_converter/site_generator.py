"""Generate a static website for browsing GAO reports."""

import json
import os
import shutil
import re
from typing import List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
SITE_DIR = os.path.join(BASE_DIR, 'site')
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')


def load_catalog() -> List[dict]:
    """Load the report catalog."""
    catalog_path = os.path.join(DATA_DIR, 'catalog.json')
    with open(catalog_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def read_markdown(report_id: str) -> str:
    """Read a markdown file for a report."""
    md_path = os.path.join(DATA_DIR, 'markdown', f'{report_id}.md')
    if os.path.exists(md_path):
        with open(md_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


def md_to_html_simple(md: str) -> str:
    """Simple markdown to HTML conversion (no external deps)."""
    html = md

    # Headers
    html = re.sub(r'^###### (.+)$', r'<h6>\1</h6>', html, flags=re.MULTILINE)
    html = re.sub(r'^##### (.+)$', r'<h5>\1</h5>', html, flags=re.MULTILINE)
    html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # Bold and italic
    html = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', html)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

    # Links
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)

    # Horizontal rules
    html = re.sub(r'^---+$', '<hr>', html, flags=re.MULTILINE)

    # Lists
    html = re.sub(r'^(\d+)\. (.+)$', r'<li>\2</li>', html, flags=re.MULTILINE)
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)

    # Paragraphs (wrap remaining text blocks)
    lines = html.split('\n')
    result = []
    in_para = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_para:
                result.append('</p>')
                in_para = False
            result.append('')
        elif stripped.startswith('<h') or stripped.startswith('<hr') or stripped.startswith('<li'):
            if in_para:
                result.append('</p>')
                in_para = False
            result.append(stripped)
        else:
            if not in_para:
                result.append('<p>')
                in_para = True
            result.append(stripped)
    if in_para:
        result.append('</p>')

    return '\n'.join(result)


def get_summary_snippet(report_id: str, max_chars: int = 250) -> str:
    """Extract a short summary snippet from the markdown file."""
    md = read_markdown(report_id)
    if not md:
        return ""

    # Look for "What GAO Found" section content
    match = re.search(r'###?\s*What GAO Found\s*\n+(.*?)(?=\n###|\n---|\Z)',
                      md, re.DOTALL)
    if match:
        text = match.group(1).strip()
    else:
        # Fall back to content after the metadata header
        parts = md.split('---', 2)
        text = parts[2].strip() if len(parts) > 2 else parts[-1].strip()

    # Clean up markdown formatting
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'#{1,6}\s+', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = text.strip()

    if len(text) > max_chars:
        text = text[:max_chars].rsplit(' ', 1)[0] + '...'

    return text


def generate_index_page(catalog: List[dict]) -> str:
    """Generate the main index HTML page."""
    report_cards = []
    for report in catalog:
        source_badge = ('Full Report' if report.get('source') == 'pdf'
                       else 'Summary')
        source_class = ('badge-pdf' if report.get('source') == 'pdf'
                       else 'badge-summary')

        downloads = []
        downloads.append(f'<a href="reports/{report["report_id"]}.html" class="btn btn-read">Read</a>')
        downloads.append(f'<a href="markdown/{report["report_id"]}.md" class="btn btn-md" download>Markdown</a>')
        if report.get('has_epub'):
            downloads.append(f'<a href="epub/{report["report_id"]}.epub" class="btn btn-epub" download>EPUB</a>')

        snippet = get_summary_snippet(report['report_id'])
        snippet_html = f'<p class="report-snippet">{snippet}</p>' if snippet else ''

        card = f'''<article class="report-card" data-date="{report['pub_date']}"
                         data-title="{report['title'].lower()}"
                         data-id="{report['report_id']}">
            <div class="report-meta">
                <time datetime="{report['pub_date']}">{report['pub_date']}</time>
                <span class="badge {source_class}">{source_badge}</span>
                <span class="report-id">{report['report_id'].upper()}</span>
            </div>
            <h2><a href="reports/{report['report_id']}.html">{report['title']}</a></h2>
            {snippet_html}
            <div class="report-actions">
                {''.join(downloads)}
                <a href="{report['url']}" class="btn btn-gao" target="_blank" rel="noopener">GAO.gov</a>
            </div>
        </article>'''
        report_cards.append(card)

    return INDEX_TEMPLATE.replace('{{REPORT_CARDS}}', '\n'.join(report_cards))


def generate_report_page(report: dict, md_content: str) -> str:
    """Generate an individual report HTML page."""
    # Strip the title and metadata lines from the content since
    # the report page template already shows them in the header
    stripped_md = md_content
    # Remove leading title (# Title)
    stripped_md = re.sub(r'^#\s+.+\n+', '', stripped_md)
    # Remove metadata line (**Report:** ... | **Published:** ...)
    stripped_md = re.sub(r'^\*\*Report:\*\*.*\n+', '', stripped_md)
    # Remove leading horizontal rule
    stripped_md = re.sub(r'^---+\s*\n+', '', stripped_md)

    html_content = md_to_html_simple(stripped_md)

    downloads = []
    downloads.append(f'<a href="../markdown/{report["report_id"]}.md" class="btn btn-md" download>Markdown</a>')
    if report.get('has_epub'):
        downloads.append(f'<a href="../epub/{report["report_id"]}.epub" class="btn btn-epub" download>EPUB (Kindle)</a>')
    downloads.append(f'<a href="{report["url"]}" class="btn btn-gao" target="_blank" rel="noopener">View on GAO.gov</a>')

    return REPORT_TEMPLATE.replace(
        '{{TITLE}}', report['title']
    ).replace(
        '{{REPORT_ID}}', report['report_id'].upper()
    ).replace(
        '{{PUB_DATE}}', report['pub_date']
    ).replace(
        '{{CONTENT}}', html_content
    ).replace(
        '{{DOWNLOADS}}', '\n'.join(downloads)
    ).replace(
        '{{GAO_URL}}', report['url']
    )


def generate_site():
    """Generate the complete static site."""
    catalog = load_catalog()

    # Create site directories
    reports_dir = os.path.join(SITE_DIR, 'reports')
    md_dir = os.path.join(SITE_DIR, 'markdown')
    epub_dir = os.path.join(SITE_DIR, 'epub')
    for d in [reports_dir, md_dir, epub_dir]:
        os.makedirs(d, exist_ok=True)

    # Generate index
    index_html = generate_index_page(catalog)
    with open(os.path.join(SITE_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)
    print(f"Generated index.html ({len(catalog)} reports)")

    # Generate individual report pages and copy files
    for report in catalog:
        md_content = read_markdown(report['report_id'])
        if not md_content:
            continue

        # Generate report HTML page
        report_html = generate_report_page(report, md_content)
        with open(os.path.join(reports_dir, f'{report["report_id"]}.html'), 'w',
                  encoding='utf-8') as f:
            f.write(report_html)

        # Copy markdown file
        src_md = os.path.join(DATA_DIR, 'markdown', f'{report["report_id"]}.md')
        if os.path.exists(src_md):
            shutil.copy2(src_md, os.path.join(md_dir, f'{report["report_id"]}.md'))

        # Copy epub file
        src_epub = os.path.join(DATA_DIR, 'epub', f'{report["report_id"]}.epub')
        if os.path.exists(src_epub):
            shutil.copy2(src_epub, os.path.join(epub_dir, f'{report["report_id"]}.epub'))

    print(f"Generated {len(catalog)} report pages")
    print(f"Site output: {SITE_DIR}")


# ============================================================
# HTML Templates (embedded for simplicity)
# ============================================================

INDEX_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GAO Reports — Read Anywhere</title>
    <style>
        :root {
            --navy: #1a2744;
            --navy-light: #2a3f66;
            --gold: #c9a227;
            --gold-light: #e8c84a;
            --bg: #f8f9fa;
            --card-bg: #ffffff;
            --text: #2c3e50;
            --text-light: #6c757d;
            --border: #dee2e6;
            --success: #28a745;
            --info: #17a2b8;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }

        header {
            background: var(--navy);
            color: white;
            padding: 2rem 0;
            border-bottom: 4px solid var(--gold);
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 0 1.5rem;
        }

        header .container {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        header h1 {
            font-size: 1.75rem;
            font-weight: 700;
            letter-spacing: -0.01em;
        }

        header p {
            color: #b0bec5;
            font-size: 1rem;
        }

        .header-badges {
            display: flex;
            gap: 1rem;
            margin-top: 0.5rem;
            flex-wrap: wrap;
        }

        .header-badge {
            background: var(--navy-light);
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.85rem;
            color: #cfd8dc;
        }

        .search-bar {
            margin: 1.5rem 0;
        }

        .search-bar input {
            width: 100%;
            padding: 0.75rem 1rem;
            border: 2px solid var(--border);
            border-radius: 8px;
            font-size: 1rem;
            outline: none;
            transition: border-color 0.2s;
        }

        .search-bar input:focus {
            border-color: var(--navy);
        }

        .toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            flex-wrap: wrap;
            gap: 0.5rem;
        }

        .result-count {
            color: var(--text-light);
            font-size: 0.9rem;
        }

        .sort-controls button {
            background: none;
            border: 1px solid var(--border);
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.85rem;
            color: var(--text-light);
        }

        .sort-controls button.active {
            background: var(--navy);
            color: white;
            border-color: var(--navy);
        }

        .report-card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 0.75rem;
            transition: box-shadow 0.2s, border-color 0.2s;
        }

        .report-card:hover {
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-color: var(--navy-light);
        }

        .report-meta {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.5rem;
            flex-wrap: wrap;
        }

        .report-meta time {
            color: var(--text-light);
            font-size: 0.85rem;
        }

        .report-id {
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 0.8rem;
            color: var(--text-light);
        }

        .badge {
            display: inline-block;
            padding: 0.1rem 0.5rem;
            border-radius: 3px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .badge-pdf {
            background: #d4edda;
            color: #155724;
        }

        .badge-summary {
            background: #cce5ff;
            color: #004085;
        }

        .report-card h2 {
            font-size: 1.1rem;
            font-weight: 600;
            line-height: 1.4;
            margin-bottom: 0.75rem;
        }

        .report-card h2 a {
            color: var(--navy);
            text-decoration: none;
        }

        .report-card h2 a:hover {
            color: var(--gold);
        }

        .report-snippet {
            font-size: 0.9rem;
            color: var(--text-light);
            line-height: 1.5;
            margin-bottom: 0.75rem;
        }

        .report-actions {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }

        .btn {
            display: inline-block;
            padding: 0.35rem 0.75rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 500;
            text-decoration: none;
            border: 1px solid var(--border);
            color: var(--text);
            transition: all 0.15s;
        }

        .btn:hover {
            background: var(--navy);
            color: white;
            border-color: var(--navy);
        }

        .btn-read {
            background: var(--navy);
            color: white;
            border-color: var(--navy);
        }

        .btn-read:hover {
            background: var(--navy-light);
        }

        .btn-epub {
            background: var(--gold);
            color: var(--navy);
            border-color: var(--gold);
            font-weight: 600;
        }

        .btn-epub:hover {
            background: var(--gold-light);
        }

        footer {
            text-align: center;
            padding: 2rem;
            color: var(--text-light);
            font-size: 0.85rem;
            border-top: 1px solid var(--border);
            margin-top: 2rem;
        }

        footer a {
            color: var(--navy);
        }

        .convert-section {
            background: var(--card-bg);
            border: 2px dashed var(--border);
            border-radius: 8px;
            padding: 2rem;
            text-align: center;
            margin: 1.5rem 0;
        }

        .convert-section h3 {
            margin-bottom: 0.5rem;
        }

        .convert-section p {
            color: var(--text-light);
            margin-bottom: 1rem;
        }

        .drop-zone {
            border: 2px dashed var(--navy-light);
            border-radius: 8px;
            padding: 2rem;
            cursor: pointer;
            transition: all 0.2s;
            background: var(--bg);
        }

        .drop-zone:hover, .drop-zone.dragover {
            background: #e3f2fd;
            border-color: var(--navy);
        }

        .drop-zone input {
            display: none;
        }

        .no-results {
            text-align: center;
            padding: 3rem;
            color: var(--text-light);
        }

        @media (max-width: 600px) {
            header h1 { font-size: 1.3rem; }
            .report-card { padding: 1rem; }
            .report-actions { flex-direction: column; }
            .btn { text-align: center; }
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>GAO Reports &mdash; Read Anywhere</h1>
            <p>Government Accountability Office reports in Markdown, EPUB, and HTML.
               Read on your Kindle, in your browser, or anywhere else.</p>
            <div class="header-badges">
                <span class="header-badge">Markdown</span>
                <span class="header-badge">EPUB / Kindle</span>
                <span class="header-badge">HTML</span>
                <span class="header-badge">Open Formats</span>
            </div>
        </div>
    </header>

    <main class="container">
        <div class="search-bar">
            <input type="text" id="search" placeholder="Search reports by title, ID, or keyword..."
                   aria-label="Search reports">
        </div>

        <div class="toolbar">
            <span class="result-count" id="resultCount"></span>
            <div class="sort-controls">
                <button class="active" data-sort="date">Newest</button>
                <button data-sort="title">A-Z</button>
            </div>
        </div>

        <section id="reports">
            {{REPORT_CARDS}}
        </section>

        <div class="no-results" id="noResults" style="display:none">
            <h3>No reports found</h3>
            <p>Try a different search term.</p>
        </div>

        <section class="convert-section">
            <h3>Convert Your Own GAO PDF</h3>
            <p>Have a GAO PDF you want to convert? Use our command-line tool.</p>
            <code style="display:block; background: #263238; color: #aed581; padding: 1rem; border-radius: 4px; text-align: left; font-size: 0.9rem;">
                python convert.py your-report.pdf
            </code>
        </section>
    </main>

    <footer>
        <p>GAO Reports are public domain documents produced by the
           <a href="https://www.gao.gov/" target="_blank" rel="noopener">U.S. Government Accountability Office</a>.
        </p>
        <p>This tool converts them to open, portable formats for easier reading.</p>
    </footer>

    <script>
        // Search
        const searchInput = document.getElementById('search');
        const reports = document.querySelectorAll('.report-card');
        const resultCount = document.getElementById('resultCount');
        const noResults = document.getElementById('noResults');

        function updateCount() {
            const visible = document.querySelectorAll('.report-card:not([style*="display: none"])');
            resultCount.textContent = visible.length + ' report' + (visible.length !== 1 ? 's' : '');
            noResults.style.display = visible.length === 0 ? 'block' : 'none';
        }

        searchInput.addEventListener('input', function() {
            const query = this.value.toLowerCase().trim();
            reports.forEach(card => {
                const title = card.dataset.title || '';
                const id = card.dataset.id || '';
                const text = card.textContent.toLowerCase();
                const match = !query || title.includes(query) || id.includes(query) || text.includes(query);
                card.style.display = match ? '' : 'none';
            });
            updateCount();
        });

        // Sort
        document.querySelectorAll('.sort-controls button').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.sort-controls button').forEach(b => b.classList.remove('active'));
                this.classList.add('active');

                const container = document.getElementById('reports');
                const cards = Array.from(reports);

                if (this.dataset.sort === 'date') {
                    cards.sort((a, b) => (b.dataset.date || '').localeCompare(a.dataset.date || ''));
                } else {
                    cards.sort((a, b) => (a.dataset.title || '').localeCompare(b.dataset.title || ''));
                }

                cards.forEach(card => container.appendChild(card));
            });
        });

        updateCount();
    </script>
</body>
</html>'''

REPORT_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{TITLE}} — GAO Reports</title>
    <style>
        :root {
            --navy: #1a2744;
            --navy-light: #2a3f66;
            --gold: #c9a227;
            --gold-light: #e8c84a;
            --bg: #f8f9fa;
            --card-bg: #ffffff;
            --text: #2c3e50;
            --text-light: #6c757d;
            --border: #dee2e6;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: Georgia, 'Times New Roman', serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.8;
        }

        .top-bar {
            background: var(--navy);
            padding: 0.75rem 0;
            border-bottom: 3px solid var(--gold);
        }

        .top-bar .container {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .top-bar a {
            color: white;
            text-decoration: none;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 0.9rem;
        }

        .top-bar a:hover { color: var(--gold); }

        .container {
            max-width: 740px;
            margin: 0 auto;
            padding: 0 1.5rem;
        }

        .report-header {
            padding: 2.5rem 0 1.5rem;
            border-bottom: 1px solid var(--border);
            margin-bottom: 2rem;
        }

        .report-header h1 {
            font-size: 1.75rem;
            line-height: 1.3;
            color: var(--navy);
            margin-bottom: 1rem;
        }

        .report-info {
            display: flex;
            gap: 1.5rem;
            color: var(--text-light);
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 0.9rem;
            flex-wrap: wrap;
        }

        .download-bar {
            display: flex;
            gap: 0.5rem;
            padding: 1rem 0;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid var(--border);
            flex-wrap: wrap;
        }

        .btn {
            display: inline-block;
            padding: 0.4rem 0.9rem;
            border-radius: 4px;
            font-size: 0.85rem;
            font-weight: 500;
            text-decoration: none;
            border: 1px solid var(--border);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            transition: all 0.15s;
        }

        .btn:hover {
            background: var(--navy);
            color: white;
            border-color: var(--navy);
        }

        .btn-epub {
            background: var(--gold);
            color: var(--navy);
            border-color: var(--gold);
            font-weight: 600;
        }

        .btn-epub:hover {
            background: var(--gold-light);
        }

        .report-content {
            margin-bottom: 3rem;
        }

        .report-content h1 { font-size: 1.6rem; margin: 2rem 0 1rem; color: var(--navy); }
        .report-content h2 { font-size: 1.35rem; margin: 1.75rem 0 0.75rem; color: var(--navy); }
        .report-content h3 { font-size: 1.15rem; margin: 1.5rem 0 0.5rem; color: var(--navy-light); }
        .report-content h4 { font-size: 1.05rem; margin: 1.25rem 0 0.5rem; }
        .report-content h5, .report-content h6 { font-size: 1rem; margin: 1rem 0 0.5rem; }

        .report-content p {
            margin-bottom: 1rem;
        }

        .report-content li {
            margin-left: 1.5rem;
            margin-bottom: 0.25rem;
        }

        .report-content hr {
            border: none;
            border-top: 1px solid var(--border);
            margin: 1.5rem 0;
        }

        .report-content strong { font-weight: 700; }
        .report-content em { font-style: italic; }

        .report-content a {
            color: var(--navy);
            text-decoration: underline;
        }

        .report-content table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 0.9rem;
        }

        .report-content th, .report-content td {
            border: 1px solid var(--border);
            padding: 0.5rem;
            text-align: left;
        }

        .report-content th {
            background: var(--bg);
            font-weight: 600;
        }

        footer {
            text-align: center;
            padding: 2rem;
            color: var(--text-light);
            font-size: 0.85rem;
            border-top: 1px solid var(--border);
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        }

        @media (max-width: 600px) {
            .report-header h1 { font-size: 1.3rem; }
            .report-info { flex-direction: column; gap: 0.25rem; }
            .download-bar { flex-direction: column; }
        }

        @media print {
            .top-bar, .download-bar, footer { display: none; }
            body { font-size: 11pt; }
        }
    </style>
</head>
<body>
    <div class="top-bar">
        <div class="container">
            <a href="../index.html">&larr; All Reports</a>
            <a href="{{GAO_URL}}" target="_blank" rel="noopener">View on GAO.gov</a>
        </div>
    </div>

    <main class="container">
        <div class="report-header">
            <h1>{{TITLE}}</h1>
            <div class="report-info">
                <span>{{REPORT_ID}}</span>
                <span>Published {{PUB_DATE}}</span>
                <span>U.S. Government Accountability Office</span>
            </div>
        </div>

        <div class="download-bar">
            {{DOWNLOADS}}
        </div>

        <article class="report-content">
            {{CONTENT}}
        </article>
    </main>

    <footer>
        <p>This is a public domain document from the
           <a href="https://www.gao.gov/">U.S. Government Accountability Office</a>,
           converted to open formats for easier reading.</p>
        <p><a href="../index.html">&larr; Back to all reports</a></p>
    </footer>
</body>
</html>'''


if __name__ == '__main__':
    generate_site()
