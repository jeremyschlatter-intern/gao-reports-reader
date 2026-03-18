"""Generate an RSS/Atom feed of converted GAO reports."""

import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
SITE_DIR = os.path.join(BASE_DIR, 'docs')

SITE_URL = "https://jeremyschlatter-intern.github.io/gao-reports-reader"


def generate_feed():
    """Generate an RSS feed (feed.xml) from the catalog."""
    catalog_path = os.path.join(DATA_DIR, 'catalog.json')
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    now = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')

    items = []
    for report in catalog[:25]:  # Latest 25
        # Read the summary snippet
        md_path = os.path.join(DATA_DIR, 'markdown', f'{report["report_id"]}.md')
        snippet = ""
        if os.path.exists(md_path):
            with open(md_path, 'r', encoding='utf-8') as f:
                md = f.read()
            # Extract "What GAO Found" text
            import re
            match = re.search(r'### What GAO Found\s*\n+(.*?)(?=\n###|\n---|\Z)',
                              md, re.DOTALL)
            if match:
                snippet = match.group(1).strip()[:500]
            else:
                # First paragraph after headers
                for line in md.split('\n'):
                    line = line.strip()
                    if (len(line) > 80 and not line.startswith('#') and
                            not line.startswith('**Report') and not line.startswith('---')):
                        snippet = line[:500]
                        break

        # Escape XML
        title_esc = report['title'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        snippet_esc = snippet.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        item = f"""    <item>
      <title>{title_esc}</title>
      <link>{SITE_URL}/reports/{report['report_id']}.html</link>
      <guid isPermaLink="true">{SITE_URL}/reports/{report['report_id']}.html</guid>
      <pubDate>{report['pub_date']}T00:00:00+00:00</pubDate>
      <description>{snippet_esc}</description>
      <enclosure url="{SITE_URL}/epub/{report['report_id']}.epub" type="application/epub+zip" />
    </item>"""
        items.append(item)

    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>GAO Reports — Read Anywhere</title>
    <link>{SITE_URL}</link>
    <description>Government Accountability Office reports converted to Markdown, EPUB, and HTML for easy reading.</description>
    <language>en-us</language>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>"""

    feed_path = os.path.join(SITE_DIR, 'feed.xml')
    with open(feed_path, 'w', encoding='utf-8') as f:
        f.write(feed)
    print(f"Generated RSS feed: {feed_path}")


if __name__ == '__main__':
    generate_feed()
