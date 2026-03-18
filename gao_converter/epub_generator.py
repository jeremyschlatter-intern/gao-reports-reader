"""Generate EPUB files from markdown using pandoc."""

import os
import subprocess
import tempfile


def markdown_to_epub(md_content: str, output_path: str, title: str = "",
                     author: str = "U.S. Government Accountability Office",
                     date: str = "") -> str:
    """Convert markdown content to EPUB using pandoc.

    Args:
        md_content: Markdown string
        output_path: Path for the output EPUB file
        title: Book title
        author: Book author
        date: Publication date

    Returns:
        Path to the generated EPUB file
    """
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    # Write markdown to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False,
                                      encoding='utf-8') as f:
        f.write(md_content)
        tmp_md = f.name

    try:
        cmd = [
            'pandoc',
            tmp_md,
            '-o', output_path,
            '--toc',
            '--toc-depth=3',
            '-f', 'markdown',
            '-t', 'epub3',
        ]

        if title:
            cmd.extend(['--metadata', f'title={title}'])
        if author:
            cmd.extend(['--metadata', f'author={author}'])
        if date:
            cmd.extend(['--metadata', f'date={date}'])

        # Add epub metadata
        cmd.extend(['--metadata', 'lang=en-US'])
        cmd.extend(['--metadata', 'publisher=U.S. Government Accountability Office'])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            raise RuntimeError(f"pandoc failed: {result.stderr}")

        return output_path

    finally:
        os.unlink(tmp_md)


def markdown_to_html(md_content: str, output_path: str, title: str = "") -> str:
    """Convert markdown content to standalone HTML using pandoc."""
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False,
                                      encoding='utf-8') as f:
        f.write(md_content)
        tmp_md = f.name

    try:
        cmd = [
            'pandoc',
            tmp_md,
            '-o', output_path,
            '-f', 'markdown',
            '-t', 'html5',
            '--standalone',
            '--toc',
            '--toc-depth=3',
        ]

        if title:
            cmd.extend(['--metadata', f'title={title}'])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            raise RuntimeError(f"pandoc failed: {result.stderr}")

        return output_path

    finally:
        os.unlink(tmp_md)


if __name__ == '__main__':
    # Test with sample content
    sample_md = """# Test GAO Report

**Report:** GAO-26-TEST | **Published:** 2026-03-18

---

## What GAO Found

This is a test report to verify EPUB generation works correctly.

### Key Findings

1. Finding one
2. Finding two
3. Finding three

## What GAO Recommends

GAO recommends testing EPUB generation before deploying.
"""

    epub_path = markdown_to_epub(sample_md, '/tmp/test-gao.epub',
                                 title='Test GAO Report', date='2026-03-18')
    print(f"Generated EPUB: {epub_path}")
    print(f"File size: {os.path.getsize(epub_path)} bytes")
