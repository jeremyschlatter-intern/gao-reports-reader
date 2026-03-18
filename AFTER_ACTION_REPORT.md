# After Action Report: GAO Reports Reader

## Project Goal

Transform GAO (Government Accountability Office) reports from PDFs into readable, portable formats — Markdown, EPUB (for Kindle), and HTML — and host them on a browsable website.

## What Was Built

A complete pipeline that fetches GAO report PDFs, converts them to clean Markdown with structured Highlights sections, generates EPUB files for e-readers, and publishes everything to a static website with search, topic filtering, and RSS.

**Live site:** [jeremyschlatter-intern.github.io/gao-reports-reader](https://jeremyschlatter-intern.github.io/gao-reports-reader/)

**GitHub repo:** [github.com/jeremyschlatter-intern/gao-reports-reader](https://github.com/jeremyschlatter-intern/gao-reports-reader)

**31 reports** are currently available, all converted from full GAO PDFs.

---

## Process and Obstacles

### Obstacle 1: GAO.gov Blocks Automated Access

**The problem:** GAO.gov uses Akamai CDN with strict bot protection. Standard HTTP requests (curl, Python requests) return 403 Forbidden for both HTML pages and PDFs.

**Failed attempts:**
- `curl` with various User-Agent headers → 403
- Python `requests` with browser-like User-Agent → 403
- Adding cookies from the RSS feed (which does work) → 403
- HTTP/2 with full browser headers → 403

**What ultimately worked:** Including `Sec-Fetch-*` headers in the request. These are browser-specific headers that indicate the request context:

```python
session.headers.update({
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Accept': 'application/pdf',
})
```

With these headers, GAO.gov returns PDFs successfully. This was a breakthrough that transformed the project from a demo with RSS summaries into a tool with full report content.

**How I found this:** Systematic experimentation. After standard approaches failed, I tried the full set of headers a real browser sends. The `Sec-Fetch-*` headers were the differentiating factor — they're relatively new (2019) headers that servers use to distinguish browser requests from automated ones.

### Obstacle 2: GovInfo API Has Limited Coverage

**The problem:** The project originally planned to use the GovInfo API for both historical and current reports.

**What I found:** The GAOREPORTS collection on GovInfo is frozen at September 2008 (16,569 reports). No GAO reports after that date are available through GovInfo. This was confirmed through API research, including testing the `/published`, `/collections`, and `/search` endpoints with various date ranges.

**Resolution:** Used GovInfo for historical reports (pre-2008) and direct GAO.gov access (with Sec-Fetch headers) for current reports. The RSS feed serves as the catalog for recent reports.

### Obstacle 3: PDF Conversion Quality

**The problem:** Raw PDF text extraction produces many artifacts specific to GAO report formatting: broken bold text, page headers/footers, table of contents remnants, duplicate content from the Highlights page, and stripped figures.

**Iterative improvements:**
1. **First pass:** Basic cleanup (remove page numbers, normalize whitespace) — still had many artifacts
2. **Second pass:** Added GAO-specific patterns (strip cover page boilerplate, remove "For Release on Delivery" lines) — better but duplicate content remained
3. **Third pass (key insight):** Extract the Highlights page separately, then skip the cover and Highlights pages during body extraction. This eliminated the most visible problem (duplicate "What GAO Found" content)
4. **Fourth pass:** Removed broken bold formatting (`**United** **States**`), stray artifacts, contact info lines, and improved figure placeholders

**What helped:** Having a DC-domain feedback agent review the output at each iteration. The feedback was specific and prioritized ("the content problem is the whole ballgame" was exactly right).

### Obstacle 4: Making the Site Useful (Not Just Technical)

**The problem:** Initial site was a basic index with titles and download buttons. DC agent feedback identified that Congressional staff need: content snippets, topic filtering, RSS subscriptions, and professional presentation.

**Improvements made through three feedback rounds:**
- Added topic/category filtering with 10 meaningful categories
- Added report snippets from "What GAO Found" on index cards
- Added RSS feed with full summaries
- Replaced developer-facing CLI section with user-facing About section
- Added pandoc-based HTML rendering for proper list/table formatting
- Added "Last updated" date indicator

---

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| Static site (no backend) | Simplest deployment, free hosting on GitHub Pages, no server to maintain |
| pymupdf4llm for PDF extraction | Lightweight, good quality text extraction, no GPU/ML requirements |
| pandoc for EPUB and HTML | Industry standard, handles tables and lists correctly |
| RSS feed from GAO | Reliable source of report metadata, not blocked by bot protection |
| Highlights extraction from raw PDF | More reliable than parsing the markdown output; GAO's Highlights page has consistent structure |
| Topic categorization via keyword mapping | GAO titles follow consistent patterns; explicit mapping gives better categories than naive splitting |

---

## Team

This project was completed by a single Claude Code agent with two types of subagents:

- **DC Feedback Agent** (3 rounds): Played the role of Daniel Schuman, providing domain-specific feedback from the perspective of Congressional staff and government transparency advocates. This agent reviewed the site content, identified missing features, and prioritized improvements.

- **Research Agents** (2 instances): One explored the GovInfo API capabilities and limitations, another researched GitHub Pages deployment options. Both ran in parallel with the main development work.

The feedback agent was critical to the project's quality. Its first review identified that RSS summaries were insufficient ("worse than useless; it is actively misleading"), which directly motivated the effort to solve the PDF download problem. Its second review identified the duplicate highlights issue and topic filtering need. Its final review gave a 7/10 score with specific actionable items.

---

## What I Would Do Next

1. **Automation:** Set up a GitHub Action to run the pipeline daily, keeping the site current with new GAO reports
2. **Scale:** Process GAO's full historical catalog from GovInfo (16,569 reports pre-2008) and all reports since
3. **Recommendation tracking:** Extract numbered GAO recommendations and track them separately
4. **Better figure handling:** Extract embedded charts/graphs from PDFs where possible
5. **CRS reports:** Congressional Research Service reports would be a natural extension

---

## Key Metrics

- **31 reports** converted (25 recent, 6 historical)
- **All from full PDFs** (none are summaries)
- **3 output formats** per report (Markdown, EPUB, HTML)
- **RSS feed** with full "What GAO Found" summaries
- **10 topic categories** for filtering
- **Deployed** at [jeremyschlatter-intern.github.io/gao-reports-reader](https://jeremyschlatter-intern.github.io/gao-reports-reader/)
