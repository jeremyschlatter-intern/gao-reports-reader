"""Parse the GAO RSS feed for report metadata."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import re
import requests

GAO_RSS_URL = "https://www.gao.gov/rss/reports.xml"


@dataclass
class GAOReport:
    """Metadata for a single GAO report."""
    report_id: str          # e.g., "gao-26-108116"
    title: str
    url: str                # Product page URL
    summary: str            # Full description from RSS
    pub_date: str           # ISO format date string
    pdf_url: Optional[str] = None
    topics: List[str] = field(default_factory=list)

    @property
    def slug(self) -> str:
        """URL-safe slug for file naming."""
        return self.report_id.lower()

    @property
    def pdf_filename(self) -> str:
        return f"{self.slug}.pdf"

    @property
    def markdown_filename(self) -> str:
        return f"{self.slug}.md"

    @property
    def epub_filename(self) -> str:
        return f"{self.slug}.epub"


def extract_report_id(url: str) -> str:
    """Extract report ID from a GAO product URL."""
    # https://www.gao.gov/products/gao-26-108116 -> gao-26-108116
    match = re.search(r'products/(gao-[\w-]+)', url, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    # Try GUID format: /products/gao-26-108116
    match = re.search(r'/(gao-[\w-]+)', url, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    return url.split('/')[-1].lower()


def clean_html(text: str) -> str:
    """Remove HTML tags and clean up whitespace."""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&#\d+;', '', text)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    return text.strip()


def parse_description(desc: str) -> str:
    """Parse RSS description into clean text, preserving structure."""
    if not desc:
        return ""

    # Extract sections
    sections = []
    current_section = None
    current_content = []

    for line in desc.split('\n'):
        line = clean_html(line).strip()
        if not line:
            if current_content:
                current_content.append('')
            continue

        # Check for section headers
        if line in ('What GAO Found', 'Why GAO Did This Study',
                     'What GAO Recommends', 'What GAO Found:',
                     'Why GAO Did This Study:', 'What GAO Recommends:'):
            if current_section:
                sections.append((current_section, '\n'.join(current_content).strip()))
            current_section = line.rstrip(':')
            current_content = []
        else:
            current_content.append(line)

    if current_section:
        sections.append((current_section, '\n'.join(current_content).strip()))
    elif current_content:
        sections.append(('Summary', '\n'.join(current_content).strip()))

    # Format as structured text
    parts = []
    for section_name, content in sections:
        parts.append(f"### {section_name}\n\n{content}")

    return '\n\n'.join(parts)


def fetch_reports(url: str = GAO_RSS_URL) -> List[GAOReport]:
    """Fetch and parse the GAO RSS feed."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    reports = []

    for item in root.findall('.//item'):
        title = item.findtext('title', '').strip()
        link = item.findtext('link', '').strip()
        desc = item.findtext('description', '').strip()
        pub_date_str = item.findtext('pubDate', '').strip()

        if not title or not link:
            continue

        report_id = extract_report_id(link)

        # Parse date
        try:
            dt = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
            pub_date = dt.strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            pub_date = pub_date_str

        # Construct PDF URL (GAO pattern)
        pdf_url = f"https://www.gao.gov/assets/{report_id}.pdf"

        report = GAOReport(
            report_id=report_id,
            title=title,
            url=link,
            summary=parse_description(desc),
            pub_date=pub_date,
            pdf_url=pdf_url,
        )
        reports.append(report)

    return reports


if __name__ == '__main__':
    reports = fetch_reports()
    print(f"Found {len(reports)} reports in GAO RSS feed\n")
    for r in reports[:5]:
        print(f"  [{r.pub_date}] {r.report_id}: {r.title}")
