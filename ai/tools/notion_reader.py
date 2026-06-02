"""
Notion page reader - extracts text context from a Notion page.
Handles pagination and recursively processes nested blocks.
"""
# Load .env first - must be imported before any os.getenv() calls
from ai import config_env

import os
from notion_client import Client
from ai.utils import AppError
from ai.utils.logger import get_logger

logger = get_logger(__name__)


def read_page_context(page_id: str) -> str:
    """
    Read all text content from a Notion page, recursively processing nested blocks.

    Args:
        page_id: The Notion page ID to read

    Returns:
        Extracted text content joined with newlines

    Raises:
        AppError: If the page cannot be accessed (not found, permission denied, etc.)
    """
    logger.info(f"Reading Notion page: {page_id}")

    api_key = os.getenv("NOTION_API_KEY")
    if not api_key:
        raise AppError(
            "NOTION_API_KEY environment variable is not set",
            component="notion_reader"
        )

    try:
        notion = Client(auth=api_key)
        text_parts = []

        # Recursively extract text from blocks
        _extract_blocks(notion, page_id, text_parts)

        result = "\n".join(text_parts)
        logger.info(f"Extracted {len(result)} characters from Notion page {page_id}")
        return result

    except Exception as e:
        error_msg = str(e).lower()

        # Check for common permission/access errors
        if "could not find" in error_msg or "not found" in error_msg:
            raise AppError(
                f"Cannot access Notion page {page_id}. Please ensure:\n"
                "1. The page ID is correct\n"
                "2. The page has been shared with your Notion integration\n"
                "3. The integration has read permissions",
                component="notion_reader"
            )
        elif "unauthorized" in error_msg or "forbidden" in error_msg:
            raise AppError(
                f"Permission denied for Notion page {page_id}. "
                "Please share the page with your Notion integration.",
                component="notion_reader"
            )
        else:
            logger.exception(f"Unexpected error reading Notion page {page_id}")
            raise AppError(
                f"Failed to read Notion page: {str(e)}",
                component="notion_reader"
            )


def _extract_blocks(notion: Client, block_id: str, text_parts: list, level: int = 0):
    """
    Recursively extract text from blocks with pagination support.

    Args:
        notion: Notion client instance
        block_id: Block or page ID to extract from
        text_parts: List to accumulate extracted text
        level: Recursion depth (for debugging)
    """
    try:
        # Pagination handling
        has_more = True
        start_cursor = None

        while has_more:
            if start_cursor:
                response = notion.blocks.children.list(
                    block_id=block_id,
                    start_cursor=start_cursor
                )
            else:
                response = notion.blocks.children.list(block_id=block_id)

            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")

            # Process each block
            for block in response.get("results", []):
                block_type = block.get("type")

                # Extract text based on block type
                if block_type in [
                    "paragraph",
                    "heading_1",
                    "heading_2",
                    "heading_3",
                    "bulleted_list_item",
                    "numbered_list_item",
                    "quote",
                    "callout",
                    "code"
                ]:
                    # Get the rich_text array from the block type object
                    block_content = block.get(block_type, {})
                    rich_text = block_content.get("rich_text", [])

                    # Extract plain_text from each rich_text element
                    text = "".join([rt.get("plain_text", "") for rt in rich_text])

                    if text.strip():
                        text_parts.append(text.strip())

                # Recursively process children if the block has them
                if block.get("has_children", False):
                    _extract_blocks(notion, block["id"], text_parts, level + 1)

    except Exception as e:
        logger.warning(f"Error processing block {block_id} at level {level}: {e}")
        # Don't raise - continue processing other blocks
