"""
Deck writer agent - writes deck with background images for pro/max modes.
Final step that combines deck content with generated images.
"""
from ai.src.state import GraphState
from ai.tools.slides_writer import write_deck
from ai.utils import AppError
from ai.utils.logger import get_logger

logger = get_logger(__name__)


def deck_writer(state: GraphState) -> dict:
    """
    Write the deck with background images.

    Args:
        state: Current graph state with "deck", "deck_id", "cover_image", and "bg_image"

    Returns:
        Partial state update with "deck_path"

    Raises:
        AppError: If deck writing fails
    """
    deck = state.get("deck")
    deck_id = state.get("deck_id")
    cover_image = state.get("cover_image")
    bg_image = state.get("bg_image")

    if not deck or not deck_id:
        raise AppError("No deck or deck_id found in state", component="deck_writer")

    logger.info(
        f"Deck writer: writing '{deck.title}' with images "
        f"(cover={cover_image}, bg={bg_image})"
    )

    try:
        # Write deck with images
        deck_path = write_deck(deck, deck_id, cover_image=cover_image, bg_image=bg_image)

        logger.info(f"Deck written with images: deck_id={deck_id}, path={deck_path}")

        return {
            "deck_path": deck_path
        }

    except Exception as e:
        logger.exception("Deck writer failed")
        raise AppError(
            f"Failed to write deck: {str(e)}",
            component="deck_writer"
        )
