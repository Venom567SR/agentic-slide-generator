"""
Test script to verify Notion reader works.
Phase 0 gate: Notion page text must print successfully.
"""
# Load .env first
from ai import config_env

import os
from ai.tools.notion_reader import read_page_context
from ai.utils import AppError
from ai.utils.logger import get_logger

logger = get_logger(__name__)


def test_notion():
    """Test that Notion reader can fetch and extract text from the configured page."""
    try:
        print("=" * 60)
        print("Testing Notion Reader")
        print("=" * 60)

        # Get page ID from environment (check both names for compatibility)
        page_id = os.getenv("PAGE_ID") or os.getenv("NOTION_PAGE_ID")
        if not page_id:
            print("\n✗ PAGE_ID or NOTION_PAGE_ID not set in .env")
            return False

        print(f"\nPage ID: {page_id}")
        print("\nFetching page content...")

        # Read the page
        context = read_page_context(page_id)

        print("\n" + "=" * 60)
        print("Notion Page Content:")
        print("=" * 60)
        print(context)
        print("=" * 60)

        print(f"\n✓ Successfully read {len(context)} characters from Notion page")
        print(f"✓ Number of lines: {len(context.splitlines())}")
        return True

    except AppError as e:
        print("\n" + "=" * 60)
        print("✗ Notion reader FAILED")
        print("=" * 60)
        print(f"\nError: {e}")
        print("\nPlease check:")
        print("  - NOTION_API_KEY is set correctly in .env")
        print("  - NOTION_PAGE_ID is set correctly in .env")
        print("  - The page has been shared with your Notion integration")
        print("  - The integration has read permissions")
        return False

    except Exception as e:
        print("\n" + "=" * 60)
        print("✗ Notion reader FAILED (unexpected error)")
        print("=" * 60)
        logger.exception("Notion test failed")
        print(f"\nError: {e}")
        return False


if __name__ == "__main__":
    success = test_notion()
    exit(0 if success else 1)
