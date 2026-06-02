"""
Slides writer tool - converts DeckSpec to Slidev markdown.
Writes to slidev/slides.md (active) and slidev/decks/<deck_id>.md (archive).
"""
import os
import yaml
from pathlib import Path
from ai.src.schemas import DeckSpec
from ai.utils import AppError
from ai.utils.logger import get_logger

logger = get_logger(__name__)


def _sanitize_markdown_text(text: str) -> str:
    """
    Sanitize markdown text to prevent false slide separators.
    If text starts with '---', indent it to avoid breaking Slidev parsing.

    Args:
        text: The markdown text (heading or bullet)

    Returns:
        Sanitized text
    """
    if text.strip().startswith("---"):
        # Indent to prevent false slide separator
        return "  " + text
    return text


def write_deck(deck: DeckSpec, deck_id: str) -> str:
    """
    Write a DeckSpec to Slidev markdown format.

    Writes to:
    - ./slidev/slides.md (the active deck shown in Slidev)
    - ./slidev/decks/<deck_id>.md (archived copy)

    Args:
        deck: The DeckSpec to write
        deck_id: Unique identifier for this deck

    Returns:
        Path to the active slides.md file

    Raises:
        AppError: If writing fails
    """
    logger.info(f"Writing deck '{deck.title}' with {len(deck.slides)} slides (deck_id={deck_id})")

    try:
        # Get Slidev directory from env
        slidev_dir = Path(os.getenv("SLIDEV_DIR", "./slidev"))

        if not slidev_dir.exists():
            raise AppError(
                f"Slidev directory not found: {slidev_dir}. "
                "Please run 'npm create slidev@latest slidev' first.",
                component="slides_writer"
            )

        # Build Slidev markdown
        markdown_parts = []

        # 1. Frontmatter - use YAML serialization to properly escape special chars
        frontmatter = {
            "theme": "default",
            "title": deck.title
        }
        frontmatter_yaml = yaml.safe_dump(
            frontmatter,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False
        ).strip()

        markdown_parts.append("---")
        markdown_parts.append(frontmatter_yaml)
        markdown_parts.append("---")
        markdown_parts.append("")

        # 2. Cover slide (deck title)
        markdown_parts.append(f"# {_sanitize_markdown_text(deck.title)}")
        markdown_parts.append("")
        markdown_parts.append("---")
        markdown_parts.append("")

        # 3. Content slides (one per SlideSpec)
        for slide in deck.slides:
            markdown_parts.append(f"## {_sanitize_markdown_text(slide.heading)}")
            markdown_parts.append("")

            # Bullets
            for bullet in slide.bullets:
                markdown_parts.append(f"- {_sanitize_markdown_text(bullet)}")

            # Image (if present) - will be used in pro/max modes
            if slide.image_path:
                markdown_parts.append("")
                markdown_parts.append(f"![]({slide.image_path})")

            markdown_parts.append("")
            markdown_parts.append("---")
            markdown_parts.append("")

        # Join all parts
        markdown = "\n".join(markdown_parts)

        # Write to active slides.md
        active_path = slidev_dir / "slides.md"
        active_path.write_text(markdown, encoding="utf-8")
        logger.info(f"Wrote active deck to: {active_path}")

        # Write to archived copy in decks/
        decks_dir = slidev_dir / "decks"
        decks_dir.mkdir(exist_ok=True)

        archive_path = decks_dir / f"{deck_id}.md"
        archive_path.write_text(markdown, encoding="utf-8")
        logger.info(f"Wrote archived copy to: {archive_path}")

        return str(active_path)

    except AppError:
        raise
    except Exception as e:
        logger.exception(f"Failed to write deck {deck_id}")
        raise AppError(
            f"Failed to write deck: {str(e)}",
            component="slides_writer"
        )
