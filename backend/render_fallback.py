"""
Fallback HTML renderer for Slidev presentations.
Converts slides.md to a self-contained HTML file without Vite/Node dependencies.
"""

import re
from pathlib import Path
from typing import List, Tuple


def render_deck_html(slides_md_path: str, out_path: str = "slidev/deck.html") -> str:
    """
    Convert a Slidev slides.md file to a self-contained HTML presentation.

    Args:
        slides_md_path: Path to the slides.md file
        out_path: Path where the HTML file will be written

    Returns:
        The path to the generated HTML file
    """
    # Read the markdown file
    content = Path(slides_md_path).read_text(encoding='utf-8')

    # Strip YAML frontmatter (everything between the first pair of ---)
    content = _strip_frontmatter(content)

    # Split into individual slides
    slide_contents = _split_slides(content)

    # Convert each slide to HTML
    slides_html = [_render_slide(slide_text) for slide_text in slide_contents]

    # Generate the full HTML document
    html = _generate_html_document(slides_html)

    # Write to output file
    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(html, encoding='utf-8')

    return str(out_file)


def _strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from the beginning of the file."""
    # Match content between first pair of --- lines
    pattern = r'^---\s*\n.*?\n---\s*\n'
    return re.sub(pattern, '', content, count=1, flags=re.DOTALL)


def _split_slides(content: str) -> List[str]:
    """Split content into individual slides on --- delimiters."""
    # Split on lines that are exactly --- (with optional whitespace)
    slides = re.split(r'\n---\s*\n', content)
    # Filter out empty slides
    return [slide.strip() for slide in slides if slide.strip()]


def _render_slide(slide_text: str) -> str:
    """Convert a single slide's markdown to HTML."""
    lines = slide_text.split('\n')

    title = ""
    content_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for title (# or ##)
        if line.startswith('# '):
            title = line[2:].strip()
        elif line.startswith('## '):
            title = line[3:].strip()
        else:
            content_lines.append(line)

    # Build slide HTML
    html_parts = ['<section class="slide">']

    if title:
        html_parts.append(f'  <h2>{_escape_html(title)}</h2>')

    # Process content lines
    if content_lines:
        bullets = []
        for line in content_lines:
            if line.startswith('- '):
                bullets.append(line[2:].strip())
            elif line.startswith('* '):
                bullets.append(line[2:].strip())
            elif line and not bullets:
                # Plain text paragraph
                html_parts.append(f'  <p>{_escape_html(line)}</p>')

        if bullets:
            html_parts.append('  <ul>')
            for bullet in bullets:
                html_parts.append(f'    <li>{_escape_html(bullet)}</li>')
            html_parts.append('  </ul>')

    html_parts.append('</section>')
    return '\n'.join(html_parts)


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))


def _generate_html_document(slides_html: List[str]) -> str:
    """Generate the complete HTML document with embedded CSS."""

    css = """
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        background: #0a0a0a;
        color: #e0e0e0;
        padding: 2rem;
        line-height: 1.6;
    }

    .container {
        max-width: 1400px;
        margin: 0 auto;
    }

    .slide {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #2a2a3e;
        border-radius: 8px;
        padding: 3rem;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        aspect-ratio: 16 / 9;
        display: flex;
        flex-direction: column;
        justify-content: center;
        min-height: 500px;
    }

    .slide h2 {
        font-size: 2.5rem;
        margin-bottom: 1.5rem;
        color: #4cc9f0;
        font-weight: 600;
    }

    .slide p {
        font-size: 1.3rem;
        margin-bottom: 1rem;
        color: #d0d0d0;
    }

    .slide ul {
        list-style: none;
        margin-left: 0;
    }

    .slide li {
        font-size: 1.4rem;
        margin-bottom: 1rem;
        padding-left: 2rem;
        position: relative;
        color: #e0e0e0;
    }

    .slide li:before {
        content: '→';
        position: absolute;
        left: 0;
        color: #4cc9f0;
        font-weight: bold;
    }

    @media print {
        body {
            background: white;
            padding: 0;
        }

        .slide {
            page-break-after: always;
            page-break-inside: avoid;
            margin: 0;
            border: none;
            box-shadow: none;
            width: 100%;
            height: 100vh;
        }

        .slide:last-child {
            page-break-after: auto;
        }
    }

    @media screen and (max-width: 768px) {
        .slide {
            padding: 2rem;
            min-height: 400px;
        }

        .slide h2 {
            font-size: 2rem;
        }

        .slide p,
        .slide li {
            font-size: 1.1rem;
        }
    }
    """

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Presentation</title>
    <style>
{css}
    </style>
</head>
<body>
    <div class="container">
{''.join(slides_html)}
    </div>
</body>
</html>"""

    return html_template


if __name__ == "__main__":
    # Render slidev/slides.md to slidev/deck.html
    import sys

    slides_path = "slidev/slides.md"
    output_path = "slidev/deck.html"

    try:
        result = render_deck_html(slides_path, output_path)
        print(f"✓ Rendered presentation to: {result}")
        print(f"  Open in browser: file://{Path(result).resolve()}")
    except FileNotFoundError:
        print(f"✗ Error: {slides_path} not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
